import pytest
from src.rules_extract import extract_deterministic_rules
from src.classifier import KeywordClassifier

def test_hinglish_refund_detection():
    text = "bhai mera paisa wapas karo"
    sig = extract_deterministic_rules(text)
    assert "refund" in sig["category_hints"]

def test_hinglish_anger_detection():
    text = "yeh toh dhoka hai, ghatiya service"
    sig = extract_deterministic_rules(text)
    assert sig["is_angry"] is True

def test_hinglish_payment_batch_access():
    text = "paisa kat gaya lekin batch nahi dikh raha"
    sig = extract_deterministic_rules(text)
    assert "payment" in sig["category_hints"]
    assert "batch_access" in sig["category_hints"]

def test_hinglish_legal_threat():
    text = "court mein case karunga"
    sig = extract_deterministic_rules(text)
    assert sig["is_legal_threat"] is True

def test_hinglish_churn_detection():
    text = "allen ja raha hoon band karo"
    sig = extract_deterministic_rules(text)
    assert sig["is_churn_risk"] is True
