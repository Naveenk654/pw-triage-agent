"""Deterministic rule and entity extraction."""

import re
from typing import Dict, Any, List


REFUND_REGEX = re.compile(r"\b(refund|money\s+back|return\s+fee|cancel.*purchase|chargeback)\b", re.I)
PAYMENT_REGEX = re.compile(r"\b(deducted|debited|payment\s+failed|upi|double\s+deduction|bank\s+statement|transaction)\b", re.I)
ACCESS_REGEX = re.compile(r"\b(my\s+batches|batch.*locked|course\s+not\s+showing|access\s+denied|not\s+activated|batch.*access)\b", re.I)
TECH_REGEX = re.compile(r"\b(buffering|lag|video.*play|error\s+drm|black\s+screen|crash|app\s+not\s+opening)\b", re.I)
TRANSFER_REGEX = re.compile(r"\b(transfer.*batch|switch.*batch|change.*course|another\s+student|give.*friend)\b", re.I)
DOUBT_REGEX = re.compile(r"\b(doubt|ta|solution|answer\s+key|homework|question\s+explanation|how\s+to\s+solve)\b", re.I)
TEST_REGEX = re.compile(r"\b(aits|test\s+series|mock\s+test|rank|percentile|exam\s+window)\b", re.I)

ANGRY_REGEX = re.compile(r"\b(cheat|scam|fraud|worst|sue|court|lawyer|police|consumer\s+court|pathetic|harassment|useless)\b", re.I)
CHURN_REGEX = re.compile(r"\b(leaving|quitting|unsubscribe|switch\s+to\s+allen|switch\s+to\s+unacademy|delete\s+account|cancel\s+my\s+subscription)\b", re.I)
LEGAL_REGEX = re.compile(r"\b(consumer\s+court|legal\s+notice|police|fir|lawyer|sue\s+you)\b", re.I)

# Hinglish patterns (add alongside existing English patterns)
REFUND_REGEX_HI = re.compile(r"\b(paisa\s+wapas|paise\s+wapas|refund\s+karo|refund\s+do|paisa\s+laut|rupaye\s+wapas)\b", re.I)
PAYMENT_REGEX_HI = re.compile(r"\b(paisa\s+kat|paise\s+kate|payment\s+ho\s+gaya|upi\s+se|paisa\s+gaya|deduct\s+ho\s+gaya)\b", re.I)
ACCESS_REGEX_HI = re.compile(r"\b(batch\s+nahi\s+dikh|course\s+nahi\s+mil|batch\s+lock|show\s+nahi\s+ho|dikhai\s+nahi\s+de)\b", re.I)
TECH_REGEX_HI = re.compile(r"\b(video\s+nahi\s+chal|app\s+band\s+ho|screen\s+black|ruk\s+ruk\s+ke|lag\s+ho\s+raha)\b", re.I)
ANGRY_REGEX_HI = re.compile(r"\b(dhoka|loot|bakwas|bekar|ghatiya|pagal|bewakoof|chori)\b", re.I)
CHURN_REGEX_HI = re.compile(r"\b(allen\s+ja|unacademy\s+ja|chhod\s+raha|band\s+karo|delete\s+karo)\b", re.I)
LEGAL_REGEX_HI = re.compile(r"\b(court\s+mein|thana|fir\s+karunga|vakil|case\s+karunga)\b", re.I)

SCHOLARSHIP_REGEX = re.compile(r"\b(scholarship|nsat|fee\s+waiver|merit\s+discount)\b", re.I)
PW_STORE_REGEX = re.compile(r"\b(book\s+order|merchandise|delivery|shipping|store\.pw|pw\s+store)\b", re.I)
VIDYAPEETH_REGEX = re.compile(r"\b(vidyapeeth|pathshala|offline\s+center|hostel|kota\s+center)\b", re.I)

REPEATED_CONTACT_REGEX = re.compile(r"\b(already\s+(called|emailed|contacted|raised|told)|3rd\s+time|no\s+reply\s+since|waiting\s+for\s+\d+\s+days)\b", re.I)
URGENT_REFUND_REGEX = re.compile(r"\b(refund|money\s+back).*\b(immediately|right\s+now|urgent|today\s+itself)\b", re.I)
DOUBLE_CHARGE_REGEX = re.compile(r"\b(double\s+(deduction|charge|debited)|debited\s+twice|charged\s+two\s+times|dispute)\b", re.I)
THIRD_PARTY_TRANSFER_REGEX = re.compile(r"\b(transfer.*(another|other|brother|sister|friend|cousin|someone\s+else)|give.*(friend|brother|sister|cousin))\b", re.I)
HARDWARE_REGEX = re.compile(r"\b(laptop.*(repair|display|battery|broken)|headphone|mic|tablet.*screen)\b", re.I)

ORDER_ID_REGEX = re.compile(r"\b(PW-?\d{5,12}|ORDER[-_]?\d{4,10})\b", re.I)
UPI_REF_REGEX = re.compile(r"\b(UPI[-_]?\d{8,14}|\d{12})\b")
AMOUNT_REGEX = re.compile(r"(?:rs\.?|inr|₹)\s*(\d+(?:,\d+)*(?:\.\d+)?)|(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:rs|inr|rupees)", re.I)


def extract_amounts(text: str) -> List[float]:
    """Extracts currency monetary values from ticket."""
    matches = AMOUNT_REGEX.findall(text)
    amounts = []
    for m in matches:
        val_str = (m[0] or m[1]).replace(",", "")
        try:
            amounts.append(float(val_str))
        except ValueError:
            pass
    return amounts


def extract_deterministic_rules(text: str) -> Dict[str, Any]:
    """
    Deterministically extracts rule flags, entities, and category hints.
    """
    amounts = extract_amounts(text)
    max_amount = max(amounts) if amounts else 0.0
    
    signals = {
        "order_ids": ORDER_ID_REGEX.findall(text),
        "upi_refs": UPI_REF_REGEX.findall(text),
        "amounts": amounts,
        "max_amount": max_amount,
        "is_angry": bool(ANGRY_REGEX.search(text) or ANGRY_REGEX_HI.search(text)),
        "is_churn_risk": bool(CHURN_REGEX.search(text) or CHURN_REGEX_HI.search(text)),
        "is_legal_threat": bool(LEGAL_REGEX.search(text) or LEGAL_REGEX_HI.search(text)),
        "is_repeated_contact": bool(REPEATED_CONTACT_REGEX.search(text)),
        "is_urgent_refund": bool(URGENT_REFUND_REGEX.search(text)),
        "is_double_charge": bool(DOUBLE_CHARGE_REGEX.search(text)),
        "is_out_of_kb_topic": bool(THIRD_PARTY_TRANSFER_REGEX.search(text) or HARDWARE_REGEX.search(text)),
        "category_hints": []
    }
    
    if REFUND_REGEX.search(text) or REFUND_REGEX_HI.search(text):
        signals["category_hints"].append("refund")
    if PAYMENT_REGEX.search(text) or PAYMENT_REGEX_HI.search(text):
        signals["category_hints"].append("payment")
    if ACCESS_REGEX.search(text) or ACCESS_REGEX_HI.search(text):
        signals["category_hints"].append("batch_access")
    if TECH_REGEX.search(text) or TECH_REGEX_HI.search(text):
        signals["category_hints"].append("technical")
    if TRANSFER_REGEX.search(text):
        signals["category_hints"].append("course_transfer")
    if DOUBT_REGEX.search(text):
        signals["category_hints"].append("academic")
    if TEST_REGEX.search(text):
        signals["category_hints"].append("exam_test_series")
    if SCHOLARSHIP_REGEX.search(text):
        signals["category_hints"].append("scholarship")
    if PW_STORE_REGEX.search(text):
        signals["category_hints"].append("pw_store")
    if VIDYAPEETH_REGEX.search(text):
        signals["category_hints"].append("vidyapeeth_offline")
        
    return signals
