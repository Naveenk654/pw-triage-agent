"""Text cleaning, sanitization, and preprocessing pipeline."""

import re
from typing import Dict, Any


INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.I),
    re.compile(r"system\s*prompt", re.I),
    re.compile(r"reveal\s+(your\s+)?instructions", re.I),
    re.compile(r"you\s+are\s+now\s+in\s+developer\s+mode", re.I),
    re.compile(r"output\s+the\s+initial\s+prompt", re.I),
    re.compile(r"hidden\s+(policy|instructions|rules)", re.I),
]


def preprocess_ticket(raw_text: str) -> Dict[str, Any]:
    """
    Cleans raw student message and flags structural/security anomalies.
    Returns: {
        'cleaned_text': str,
        'thread_history': str,
        'is_empty_or_garbage': bool,
        'injection_detected': bool,
        'flags': list[str]
    }
    """
    if not raw_text or not isinstance(raw_text, str):
        return {
            "cleaned_text": "",
            "thread_history": "",
            "is_empty_or_garbage": True,
            "injection_detected": False,
            "flags": ["empty_input"]
        }
        
    cleaned = raw_text.strip()
    
    # Check for garbage (e.g. extremely short or repetitive non-words)
    if len(cleaned) < 5 or not re.search(r"[a-zA-Z0-9]", cleaned):
        return {
            "cleaned_text": cleaned,
            "is_empty_or_garbage": True,
            "injection_detected": False,
            "flags": ["garbage_input"]
        }
        
    # Check prompt injection
    injection = False
    flags = []
    for pat in INJECTION_PATTERNS:
        if pat.search(cleaned):
            injection = True
            flags.append("prompt_injection_pattern")
            break
            
    # Normalize excessive internal whitespace
    cleaned = re.sub(r"\s+", " ", cleaned)
    
    # Extract thread history if present
    thread_history = ""
    if "--- PREVIOUS THREAD HISTORY ---" in cleaned:
        parts = cleaned.split("--- PREVIOUS THREAD HISTORY ---", 1)
        cleaned = parts[0].strip()
        thread_history = parts[1].strip()
        
    return {
        "cleaned_text": cleaned,
        "thread_history": thread_history,
        "is_empty_or_garbage": False,
        "injection_detected": injection,
        "flags": flags
    }
