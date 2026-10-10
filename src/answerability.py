"""Answerability evaluation checking Dense Cosine similarity and Jev Call B passage relevance."""

import os
from typing import List, Tuple, Dict, Any
from src.models import RetrievalResult


def check_answerability(
    ticket: str,
    retrieved_passages: List[RetrievalResult],
    retrieval_min_score: float = 0.65,
    passage_relevance_min: float = 0.50,
    typesafe_key: str = None
) -> Tuple[bool, List[RetrievalResult], Dict[str, Any]]:
    """
    Evaluates whether ticket is safely answerable from KB.
    Requires:
    1. Top dense cosine >= retrieval_min_score
    2. At least one passage judged relevant by Jev Call B (or fallback heuristic)
    """
    if not retrieved_passages:
        return False, [], {"error": "no_evidence_retrieved"}
        
    top_dense = retrieved_passages[0].dense_score
    dense_pass = top_dense >= retrieval_min_score
    
    key = typesafe_key or os.environ.get("TYPESAFE_API_KEY", "")
    jev_relevance_scores = {}
    selected_passages: List[RetrievalResult] = []
    
    if key:
        from typesafe_sdk import TypeSafeClient, Noul
        client = TypeSafeClient(api_key=key, model="jev-1.13.0")
        
        # Batch passage questions into ONE System One request (Call B)
        questions = {}
        for idx, p in enumerate(retrieved_passages):
            questions[f"passage_{idx}"] = Noul(
                instructions=f"Does this passage contain useful information relevant to answering the student's question? Passage: {p.content[:500]}"
            )
            
        resp = client.system_one(state={"student_ticket": ticket}, questions=questions)
        
        for idx, p in enumerate(retrieved_passages):
            score = resp.nouls[f"passage_{idx}"].noul
            jev_relevance_scores[p.chunk_id] = score
            if score >= passage_relevance_min and p.dense_score >= retrieval_min_score:
                selected_passages.append(p)
    else:
        # Fallback heuristic when Jev key is unconfigured
        for p in retrieved_passages:
            # Dense cosine similarity proxy
            score = p.dense_score
            jev_relevance_scores[p.chunk_id] = score
            if score >= retrieval_min_score:
                selected_passages.append(p)
                
    is_answerable = dense_pass and (len(selected_passages) > 0)
    
    meta = {
        "top_dense_score": top_dense,
        "retrieval_min_score": retrieval_min_score,
        "dense_pass": dense_pass,
        "selected_passage_count": len(selected_passages),
        "relevance_scores": jev_relevance_scores
    }
    
    return is_answerable, selected_passages, meta
