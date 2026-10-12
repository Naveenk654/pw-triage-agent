import pytest
from src.decision_engine import DecisionEngine
from src.models import ClassificationResult, RetrievalResult, DraftResponse, TriageAction

def test_clarify_on_missing_order_id():
    cfg = {"decision": {"min_category_confidence": 0.60}}
    engine = DecisionEngine(cfg)
    
    prep = {"is_empty_or_garbage": False, "injection_detected": False, "cleaned_text": "payment deducted but no batch"}
    rules = {"order_ids": [], "max_amount": 0.0}
    cls = ClassificationResult(category="payment", confidence=0.9, urgency=2)
    
    draft = DraftResponse(reply_text="dummy", citations=[], claims_verified=True)
    dec = engine.decide(prep, rules, cls, [], is_answerable=True, draft_response=draft)
    assert dec.action == TriageAction.CLARIFY
    assert dec.clarification_question is not None

def test_approval_required_for_refund_with_amount():
    cfg = {"decision": {"approval_categories": ["refund"]}}
    engine = DecisionEngine(cfg)
    
    prep = {"is_empty_or_garbage": False, "injection_detected": False, "cleaned_text": "refund my 5000 rs"}
    rules = {"max_amount": 5000.0}
    cls = ClassificationResult(category="refund", confidence=0.9, urgency=2)
    retrieval = [RetrievalResult(chunk_id="c1", document="refund", section_title="s1", content="refund policy", dense_score=0.88)]
    draft = DraftResponse(reply_text="You can refund", citations=["refund"], claims_verified=True)
    
    dec = engine.decide(prep, rules, cls, retrieval, is_answerable=True, draft_response=draft)
    assert dec.action == TriageAction.APPROVAL_REQUIRED

def test_auto_reply_with_review_medium_confidence():
    cfg = {"decision": {"min_category_confidence": 0.60, "review_confidence_min": 0.75}}
    engine = DecisionEngine(cfg)
    
    prep = {"is_empty_or_garbage": False, "injection_detected": False, "cleaned_text": "general question"}
    rules = {"max_amount": 0.0}
    cls = ClassificationResult(category="technical", confidence=0.68, urgency=1)
    retrieval = [RetrievalResult(chunk_id="c1", document="technical", section_title="s1", content="tech info", dense_score=0.8)]
    draft = DraftResponse(reply_text="Try this", citations=["technical"], claims_verified=True)
    
    dec = engine.decide(prep, rules, cls, retrieval, is_answerable=True, draft_response=draft)
    assert dec.action == TriageAction.AUTO_REPLY_WITH_REVIEW
    assert dec.review_priority == "medium"

def test_explicit_human_request_escalates():
    engine = DecisionEngine({})
    
    prep = {"is_empty_or_garbage": False, "injection_detected": False, "cleaned_text": "I want to talk to a person"}
    rules = {"max_amount": 0.0}
    cls = ClassificationResult(category="general", confidence=0.9, urgency=2)
    
    draft = DraftResponse(reply_text="dummy", citations=[], claims_verified=True)
    dec = engine.decide(prep, rules, cls, [], is_answerable=True, draft_response=draft)
    assert dec.action == TriageAction.ESCALATE
    assert any("human agent" in r for r in dec.reasons)

def test_escalate_still_takes_precedence():
    engine = DecisionEngine({})
    
    prep = {"is_empty_or_garbage": False, "injection_detected": False, "cleaned_text": "refund or I sue you"}
    rules = {"max_amount": 5000.0, "is_legal_threat": True}
    cls = ClassificationResult(category="refund", confidence=0.9, urgency=5, legal_threat=True)
    
    draft = DraftResponse(reply_text="dummy", citations=[], claims_verified=True)
    dec = engine.decide(prep, rules, cls, [], is_answerable=True, draft_response=draft)
    assert dec.action == TriageAction.ESCALATE

def test_missing_draft_response_escalates_instead_of_auto_reply_with_review():
    cfg = {"decision": {"min_category_confidence": 0.60, "review_confidence_min": 0.75}}
    engine = DecisionEngine(cfg)
    
    prep = {"is_empty_or_garbage": False, "injection_detected": False, "cleaned_text": "technical issue buffering"}
    rules = {"max_amount": 0.0}
    cls = ClassificationResult(category="technical", confidence=0.68, urgency=1)
    retrieval = [RetrievalResult(chunk_id="c1", document="technical", section_title="s1", content="tech info", dense_score=0.5)]
    
    # draft_response is None (e.g. unanswerable / draft generation skipped)
    dec = engine.decide(prep, rules, cls, retrieval, is_answerable=False, draft_response=None)
    assert dec.action == TriageAction.ESCALATE
    assert dec.draft_reply is None
    assert dec.handoff_packet is not None
    assert "Escalation Handoff Packet" in dec.handoff_packet

def test_missing_draft_response_in_approval_category_escalates():
    cfg = {"decision": {"approval_categories": ["refund"]}}
    engine = DecisionEngine(cfg)
    
    prep = {"is_empty_or_garbage": False, "injection_detected": False, "cleaned_text": "refund my 5000 rs"}
    rules = {"max_amount": 5000.0}
    cls = ClassificationResult(category="refund", confidence=0.9, urgency=2)
    
    # draft_response is None
    dec = engine.decide(prep, rules, cls, [], is_answerable=False, draft_response=None)
    assert dec.action == TriageAction.ESCALATE
    assert dec.draft_reply is None
    assert dec.handoff_packet is not None

