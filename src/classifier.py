"""Structured ticket classifier with Jev (default), LLM Structured fallback, and Keyword baseline."""

import os
from abc import ABC, abstractmethod
from typing import Dict, Any
from src.models import ClassificationResult
from src.rules_extract import extract_deterministic_rules


CATEGORY_TO_PARENT = {
    "refund": "refund",
    "payment": "payment",
    "payment_dispute": "payment",
    "payment_invoice": "payment",
    "batch_access": "batch_access",
    "technical": "technical",
    "technical_support": "technical",
    "tech_app_crash": "technical",
    "tech_video_playback": "technical",
    "tech_login_otp": "technical",
    "account": "account",
    "academic": "academic",
    "doubt_support": "academic",
    "course_transfer": "academic",
    "exam_test_series": "academic",
    "scholarship": "academic",
    "subscription_cancellation": "refund",
    "pw_store": "other",
    "vidyapeeth_offline": "academic",
    "general": "other",
    "other": "other"
}


def to_parent_category(category: str) -> str:
    """Maps granular subcategory to the 5 standard evaluation parent categories."""
    return CATEGORY_TO_PARENT.get(category.lower().strip(), "other")


class BaseClassifier(ABC):
    @abstractmethod
    def classify(self, text: str) -> ClassificationResult:
        pass


class KeywordClassifier(BaseClassifier):
    """Fast, deterministic keyword baseline."""
    def classify(self, text: str) -> ClassificationResult:
        signals = extract_deterministic_rules(text)
        hints = signals["category_hints"]
        
        category = hints[0] if hints else "general"
        confidence = 0.85 if len(hints) == 1 else (0.60 if len(hints) > 1 else 0.40)
        
        urgency = 1
        if signals["is_legal_threat"]:
            urgency = 5
        elif signals["is_angry"] or signals["is_churn_risk"]:
            urgency = 4
        elif category in ["payment", "batch_access"]:
            urgency = 3
            
        return ClassificationResult(
            category=category,
            parent_category=to_parent_category(category),
            confidence=confidence,
            urgency=urgency,
            churn_risk=signals["is_churn_risk"],
            angry_tone=signals["is_angry"],
            legal_threat=signals["is_legal_threat"],
            multi_issue=len(hints) > 1,
            detected_entities={"order_ids": str(signals["order_ids"]), "upi_refs": str(signals["upi_refs"])},
            backend_used="keyword",
        )


class JevClassifier(BaseClassifier):
    """Jev 1.13 Structured judgment classifier using typesafe-sdk."""
    def __init__(self, model: str = "jev-1.13.0", api_key: str = None):
        self.model = model
        self.api_key = api_key or os.environ.get("TYPESAFE_API_KEY", "")

    def classify(self, text: str) -> ClassificationResult:
        if not self.api_key:
            # Fallback to keyword if API key is not yet set
            res = KeywordClassifier().classify(text)
            res.backend_used = "keyword_fallback_unconfigured_jev"
            return res
            
        from typesafe_sdk import TypeSafeClient, Choice, Score, Noul
        client = TypeSafeClient(api_key=self.api_key, model=self.model)
        
        questions = {
            "category": Choice(
                instructions="Determine the primary operational topic of this student ticket.",
                criteria={
                    "refund": "Requesting fee refund, money back, or transaction return under policy.",
                    "payment_dispute": "Payment debited but batch not assigned, transaction failure, or UPI double deductions.",
                    "payment_invoice": "Requesting fee receipts, invoices, or proof of payment.",
                    "batch_access": "Batch is not active, locked, or not showing in My Batches after payment.",
                    "tech_app_crash": "App keeps closing, crashing, black screen, or completely unresponsive.",
                    "tech_video_playback": "Video buffering, lag, streaming issues, or DRM errors.",
                    "tech_login_otp": "Cannot log in, OTP not received, or password reset issues.",
                    "course_transfer": "Requesting to change batch, language medium, or transfer enrollment.",
                    "subscription_cancellation": "Canceling recurring monthly membership or billing.",
                    "doubt_support": "Academic doubts, TA questions, homework help, or solutions.",
                    "exam_test_series": "AITS mock exams, test windows, ranks, or test portal questions.",
                    "scholarship": "Questions about PWNSAT scholarship, merit-based discounts, or fee waivers.",
                    "pw_store": "PW Store merchandise, book delivery, shipping, or physical product issues.",
                    "vidyapeeth_offline": "Offline center admission, hostel, fee structure, or center transfer queries.",
                    "general": "Other general administrative or inquiry topics."
                }
            ),
            "urgency": Score(
                instructions="Score the real-world operational urgency of this ticket from 0 to 4.",
                criteria=[
                    "Low - informational query",
                    "Moderate - minor issue, student can proceed",
                    "Elevated - block on study, requires assistance within normal SLA",
                    "High - active exam imminent or severe frustration",
                    "Critical - immediate financial loss, legal threat, or severe distress"
                ]
            ),
            "churn_risk": Noul(instructions="Is the student threatening to leave the platform, cancel subscription, or go to a competitor?"),
            "angry_tone": Noul(instructions="Is the student using distinctly furious, abusive, or hostile language?"),
            "legal_threat": Noul(instructions="Is the student threatening legal action, consumer court, police complaints, or chargebacks?"),
            "multi_issue": Noul(instructions="Does the student ask about multiple, distinct issues across different operational categories (e.g., a refund AND a tech support issue)?")
        }
        
        resp = client.system_one(state={"ticket": text}, questions=questions)
        
        det_signals = extract_deterministic_rules(text)
        
        # Jev score is 0-indexed float, map 0..4 to 1..5
        urgency_raw = resp.scores["urgency"].score
        urgency_val = min(5, max(1, int(round(urgency_raw)) + 1))
        
        # Apply deterministic overrides for safety (rule engine principle)
        if det_signals["is_legal_threat"]:
            urgency_val = 5
        elif det_signals["is_angry"] and urgency_val < 4:
            urgency_val = 4
            
        category_choice = resp.choices["category"].choice
        confidence = resp.choices["category"].confidence
        
        return ClassificationResult(
            category=category_choice,
            parent_category=to_parent_category(category_choice),
            confidence=confidence,
            urgency=urgency_val,
            churn_risk=resp.nouls["churn_risk"].noul > 0.5 or det_signals["is_churn_risk"],
            angry_tone=resp.nouls["angry_tone"].noul > 0.5 or det_signals["is_angry"],
            legal_threat=resp.nouls["legal_threat"].noul > 0.5 or det_signals["is_legal_threat"],
            multi_issue=resp.nouls["multi_issue"].noul > 0.5,
            detected_entities={"order_ids": str(det_signals["order_ids"]), "upi_refs": str(det_signals["upi_refs"])},
            backend_used="jev",
        )
