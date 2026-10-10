"""Citation and claim verification combining deterministic checks and Jev Call C."""

import os
import re
from typing import List, Dict, Any, Tuple
from src.models import RetrievalResult, DraftResponse


def split_sentences(text: str) -> List[str]:
    """Splits text into discrete sentences."""
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def verify_numeric_grounding(sentence: str, evidence_text: str) -> List[str]:
    """Ensures every number, percentage, amount, or duration mentioned exists in cited text."""
    issues = []
    
    # 1. Percentages
    pcts = re.findall(r"\b\d+%", sentence)
    for p in pcts:
        if p not in evidence_text:
            issues.append(f"Percentage '{p}' not found in cited evidence.")
            
    # 2. Amounts / Currency
    amounts = re.findall(r"(?:rs\.?|₹)\s*(\d+(?:,\d+)*(?:\.\d+)?)", sentence, re.I)
    for a in amounts:
        clean_a = a.replace(",", "")
        if clean_a not in evidence_text.replace(",", ""):
            issues.append(f"Amount 'Rs. {a}' not found in cited evidence.")
            
    # 3. Durations (e.g. 7 days, 48 hours, 30 days)
    durations = re.findall(r"\b(\d+)\s*(days?|hours?|weeks?|months?)\b", sentence, re.I)
    for d_num, d_unit in durations:
        pattern = rf"\b{d_num}\s*{d_unit[:4]}"
        if not re.search(pattern, evidence_text, re.I):
            issues.append(f"Duration '{d_num} {d_unit}' not found in cited evidence.")
            
    return issues


def verify_citations_and_claims(
    reply_text: str,
    evidence: List[RetrievalResult],
    typesafe_key: str = None
) -> Tuple[bool, List[str]]:
    """
    Performs deterministic verification and optional Jev Call C sentence choice judgments.
    """
    if not reply_text:
        return False, ["Empty reply text."]
        
    sentences = split_sentences(reply_text)
    evidence_by_doc = {r.document.lower(): r.content for r in evidence}
    
    unsupported_claims = []
    
    # Deterministic verification per sentence
    for sent in sentences:
        citations = re.findall(r"\[([a-zA-Z0-9_\-]+)\]", sent)
        if not citations:
            continue
            
        for doc_name in citations:
            doc_key = doc_name.lower()
            if doc_key not in evidence_by_doc:
                unsupported_claims.append(f"Cited document [{doc_name}] was not in retrieved evidence.")
            else:
                cited_content = evidence_by_doc[doc_key]
                num_issues = verify_numeric_grounding(sent, cited_content)
                unsupported_claims.extend(num_issues)
                
    # Jev Call C judgment (if key provided and citations exist)
    key = typesafe_key or os.environ.get("TYPESAFE_API_KEY", "")
    if key and sentences:
        from typesafe_sdk import TypeSafeClient, Choice
        client = TypeSafeClient(api_key=key, model="jev-1.13.0")
        
        jev_questions = {}
        for idx, sent in enumerate(sentences):
            citations = re.findall(r"\[([a-zA-Z0-9_\-]+)\]", sent)
            if citations and citations[0].lower() in evidence_by_doc:
                doc_key = citations[0].lower()
                evidence_chunk = evidence_by_doc[doc_key][:400]
                jev_questions[f"sent_{idx}"] = Choice(
                    instructions=f"Does the following cited chunk support or contradict the claim?\nChunk: {evidence_chunk}\nClaim: {sent}",
                    criteria={
                        "supported": "The claim is fully supported and confirmed by the chunk.",
                        "contradicted": "The claim is contradictory to what the chunk says.",
                        "not_stated": "The claim is not stated in or supported by the chunk."
                    }
                )
                
        if jev_questions:
            try:
                resp = client.system_one(state="verify_citations", questions=jev_questions)
                for q_name in jev_questions:
                    ans = resp.choices[q_name].choice
                    if ans != "supported":
                        unsupported_claims.append(f"Sentence verification failed ({ans}) on: {jev_questions[q_name].instructions.split('Claim: ')[-1][:50]}")
            except Exception as e:
                # Do not crash; record error
                unsupported_claims.append(f"Jev Call C verification error: {str(e)}")
                
    is_verified = (len(unsupported_claims) == 0)
    return is_verified, unsupported_claims
