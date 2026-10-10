"""End-to-end Support Ticket Triage Pipeline with full Phase 2 architecture and failure simulation."""

import os
import time
import yaml
from typing import Dict, Any, List, Optional
from src.preprocess import preprocess_ticket
from src.rules_extract import extract_deterministic_rules
from src.kb_loader import load_and_chunk_kb
from src.embedder import GeminiEmbedder, LocalEmbedder
from src.retriever import HybridRetriever
from src.classifier import JevClassifier, KeywordClassifier
from src.answerability import check_answerability
from src.llm_client import LLMClient
from src.draft_generator import generate_and_verify_draft
from src.verification import verify_citations_and_claims
from src.decision_engine import DecisionEngine
from src.cost import CostTracker
from src.logger import TriageLogger


class TriagePipeline:
    def __init__(
        self,
        config_path: str = "config.yaml",
        kb_dir: str = "knowledge_base",
        simulate_failure: Optional[str] = None  # 'jev', 'llm', 'retriever'
    ):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
            
        self.simulate_failure = simulate_failure
        self.chunks = load_and_chunk_kb(kb_dir)
        
        # Configure Embedder
        emb_cfg = self.config.get("embedding", {})
        backend = emb_cfg.get("backend", "local")
        gemini_key = os.environ.get("GEMINI_API_KEY", "")
        
        if backend == "gemini" and gemini_key and self.simulate_failure != "retriever":
            self.embedder = GeminiEmbedder(model_name=emb_cfg.get("gemini_model", "gemini-embedding-001"))
        else:
            self.embedder = LocalEmbedder(model_name=emb_cfg.get("local_model", "intfloat/multilingual-e5-small"))
            
        self.retriever = HybridRetriever(
            chunks=self.chunks,
            embedder=self.embedder,
            rrf_k=self.config.get("retrieval", {}).get("rrf_k", 60)
        )
        
        # Classifier
        typesafe_key = os.environ.get("TYPESAFE_API_KEY", "")
        if typesafe_key and self.simulate_failure != "jev":
            self.classifier = JevClassifier(model=self.config.get("jev", {}).get("model", "jev-1.13.0"))
        else:
            self.classifier = KeywordClassifier()
            
        self.llm_client = LLMClient(config=self.config)
        self.decision_engine = DecisionEngine(config=self.config)
        self.cost_tracker = CostTracker(config=self.config)
        self.logger = TriageLogger()

    def process_ticket(self, raw_ticket_text: str, images: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        start_time = time.time()
        component_failures = []
        
        # Check simulated failures
        if self.simulate_failure == "retriever":
            component_failures.append("Simulated retriever failure")
        if self.simulate_failure == "jev":
            component_failures.append("Simulated Jev classification failure")
        if self.simulate_failure == "llm":
            component_failures.append("Simulated LLM generation failure")

        # 1. Preprocessing
        prep = preprocess_ticket(raw_ticket_text)
        ticket_text = prep["cleaned_text"]
        
        # 2. Deterministic Rule Extraction
        rule_signals = extract_deterministic_rules(ticket_text)
        
        # 3. Classification
        cls_result = self.classifier.classify(ticket_text)
        if self.simulate_failure == "jev":
            cls_result.confidence = 0.1  # simulate failure degradation
            
        # 3.5 Query Rewriting (Pre-Retrieval)
        rewrite_prompt = f"Rewrite the following student ticket into a concise, formal English search query for a knowledge base. Remove all slang, anger, or conversational filler. If the student provided screenshots, extract any relevant error codes, text, or context from the images and include it in the query. Only output the rewritten search query.\n\nTicket: {prep['cleaned_text']}"
        rewrite_result = self.llm_client.generate(
            prompt=rewrite_prompt,
            system_prompt="You are an expert search query formalizer and image reader.",
            images=images
        )
        search_query = rewrite_result["text"].strip()
        prep["search_query"] = search_query
        
        gen_tokens = {
            "in": rewrite_result.get("prompt_tokens", 0), 
            "out": rewrite_result.get("completion_tokens", 0)
        }
        
        # 4. Retrieval (with pre-filtering based on classification)
        retrieval_results = []
        if self.simulate_failure != "retriever":
            top_k = self.config.get("retrieval", {}).get("top_k_candidates", 5)
            # Map Jev category to metadata category (if they differ, could use a dict, but they are 1:1 mostly)
            filter_cat = cls_result.category
            
            # Since some Jev categories like 'payment_dispute' map to 'payment.md', we can just pass the first part
            if "_" in filter_cat and filter_cat not in ["batch_access", "technical_support", "course_transfer", "doubt_support", "exam_test_series", "pw_store_shipping", "vidyapeeth_offline", "subscription_cancellation"]:
                filter_cat = filter_cat.split("_")[0]
                
            retrieval_results = self.retriever.retrieve(search_query, top_k=top_k, filter_category=filter_cat)
            
        # 5. Answerability Check
        retrieval_min_score = self.config.get("retrieval", {}).get("retrieval_min_score", 0.65)
        passage_relevance_min = self.config.get("retrieval", {}).get("passage_relevance_min", 0.50)
        is_answerable, selected_passages, ans_meta = check_answerability(
            ticket=ticket_text,
            retrieved_passages=retrieval_results,
            retrieval_min_score=retrieval_min_score,
            passage_relevance_min=passage_relevance_min
        )
        
        # 6. Draft Generation
        draft_response = None
        
        if is_answerable and self.simulate_failure != "llm":
            draft_response = generate_and_verify_draft(
                ticket=prep["cleaned_text"],
                thread_history=prep["thread_history"],
                evidence=selected_passages,
                llm_client=self.llm_client
            )
            gen_tokens["in"] += draft_response.prompt_tokens
            gen_tokens["out"] += draft_response.completion_tokens
            
            # 7. Verification (Deterministic + Jev Call C)
            if self.config.get("decision", {}).get("require_claim_verification", True):
                claims_ok, claim_issues = verify_citations_and_claims(
                    reply_text=draft_response.reply_text,
                    evidence=selected_passages
                )
                draft_response.claims_verified = claims_ok
                draft_response.unsupported_claims.extend(claim_issues)
                
                # Regeneration once if unsupported
                if not claims_ok:
                    draft_response = generate_and_verify_draft(
                        ticket=prep["cleaned_text"],
                        thread_history=prep["thread_history"],
                        evidence=selected_passages,
                        llm_client=self.llm_client
                    )
                    gen_tokens["in"] += draft_response.prompt_tokens
                    gen_tokens["out"] += draft_response.completion_tokens
                    
                    claims_ok, claim_issues = verify_citations_and_claims(
                        reply_text=draft_response.reply_text,
                        evidence=selected_passages
                    )
                    draft_response.claims_verified = claims_ok
                    draft_response.unsupported_claims.extend(claim_issues)
            else:
                # Bypass verification when disabled for speed
                draft_response.claims_verified = True

        # 8. Deterministic Decision Engine
        decision = self.decision_engine.decide(
            preprocess_data=prep,
            rule_signals=rule_signals,
            classification=cls_result,
            retrieval_results=retrieval_results,
            is_answerable=is_answerable,
            draft_response=draft_response,
            component_failures=component_failures
        )
        
        total_latency = time.time() - start_time
        cost_info = self.cost_tracker.calculate_cost("gemini", gen_tokens["in"], gen_tokens["out"])
        
        # 9. SQLite Logging
        top_dense = retrieval_results[0].dense_score if retrieval_results else 0.0
        log_entry = {
            "ticket_text": raw_ticket_text,
            "backend_used": cls_result.backend_used,
            "category": cls_result.category,
            "category_confidence": cls_result.confidence,
            "urgency": cls_result.urgency,
            "rule_flags": rule_signals,
            "top_dense_score": top_dense,
            "is_answerable": is_answerable,
            "verification_status": draft_response.claims_verified if draft_response else False,
            "decision": decision.action,
            "reasons": decision.reasons,
            "total_latency_s": total_latency,
            "input_tokens": gen_tokens["in"],
            "output_tokens": gen_tokens["out"],
            "estimated_cost_usd": cost_info["estimated_cost_usd"],
            "actual_spend_usd": cost_info["actual_spend_usd"],
            "provider": self.llm_client.primary_provider,
            "errors": component_failures
        }
        self.logger.log_ticket(log_entry)
        
        return {
            "raw_ticket": raw_ticket_text,
            "cleaned_ticket": ticket_text,
            "search_query": search_query,
            "preprocess": prep,
            "rule_signals": rule_signals,
            "classification": cls_result.model_dump(),
            "retrieval": [r.model_dump() for r in retrieval_results],
            "answerability": ans_meta,
            "draft": draft_response.model_dump() if draft_response else None,
            "decision": decision.model_dump(),
            "clarification_question": decision.clarification_question,
            "cost": cost_info,
            "latency_s": total_latency
        }
