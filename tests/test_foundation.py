import pytest
import os
from src.kb_loader import load_and_chunk_kb
from src.rules_extract import extract_deterministic_rules
from src.classifier import KeywordClassifier
from src.decision_engine import DecisionEngine
from src.models import ClassificationResult, RetrievalResult, DraftResponse, TriageAction


def test_kb_loader_reads_12_docs():
    kb_path = os.path.join(os.path.dirname(__file__), "..", "knowledge_base")
    chunks = load_and_chunk_kb(kb_path)
    assert len(chunks) > 20
    docs = {c.document for c in chunks}
    assert len(docs) == 18
    assert "refund" in docs
    assert "batch_access" in docs
    assert "technical_support" in docs


def test_deterministic_rules():
    text = "I want a refund for my order PW-99214 or I will file a case in consumer court!"
    sig = extract_deterministic_rules(text)
    assert sig["is_legal_threat"] is True
    assert "PW-99214" in sig["order_ids"]
    assert "refund" in sig["category_hints"]


def test_keyword_classifier():
    classifier = KeywordClassifier()
    res = classifier.classify("Payment was deducted twice via UPI-123456789012 but batch is locked.")
    assert res.category in ["payment", "batch_access"]
    assert res.multi_issue is True


def test_decision_engine_escalates_on_legal_threat():
    cfg = {"decision": {"max_urgency_for_auto_reply": 3}}
    engine = DecisionEngine(cfg)
    
    cls = ClassificationResult(
        category="refund",
        confidence=0.9,
        urgency=5,
        legal_threat=True
    )
    retrieval = [
        RetrievalResult(
            chunk_id="ref_1",
            document="refund",
            section_title="1. Window",
            content="7 days window",
            dense_score=0.88
        )
    ]
    draft = DraftResponse(reply_text="Refund policy is 7 days.", citations=["refund"], claims_verified=True)
    
    prep = {"is_empty_or_garbage": False, "injection_detected": False}
    rules = {"is_legal_threat": True, "max_amount": 0.0}
    dec = engine.decide(
        preprocess_data=prep,
        rule_signals=rules,
        classification=cls,
        retrieval_results=retrieval,
        is_answerable=True,
        draft_response=draft
    )
    assert dec.action == TriageAction.ESCALATE
    assert any("Legal" in r for r in dec.reasons)


def test_decision_engine_auto_replies_safe_query():
    cfg = {"decision": {"max_urgency_for_auto_reply": 3}}
    engine = DecisionEngine(cfg)
    
    cls = ClassificationResult(
        category="refund",
        confidence=0.92,
        urgency=2,
        legal_threat=False,
        angry_tone=False
    )
    retrieval = [
        RetrievalResult(
            chunk_id="ref_1",
            document="refund",
            section_title="1. Window",
            content="Refund within 7 days",
            dense_score=0.85
        )
    ]
    draft = DraftResponse(reply_text="You can refund within 7 days. [refund]", citations=["refund"], claims_verified=True)
    
    prep = {"is_empty_or_garbage": False, "injection_detected": False}
    rules = {"max_amount": 0.0, "is_double_charge": False, "is_urgent_refund": False, "is_legal_threat": False, "order_ids": ["PW-12345"]}
    dec = engine.decide(
        preprocess_data=prep,
        rule_signals=rules,
        classification=cls,
        retrieval_results=retrieval,
        is_answerable=True,
        draft_response=draft
    )
    assert dec.action == TriageAction.AUTO_REPLY
    assert dec.draft_reply is not None
