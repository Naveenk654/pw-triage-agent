"""Deterministic Decision Engine strictly implementing the Answer First, Escalate Only If Stuck policy."""

from typing import List, Dict, Any, Optional
from src.models import ClassificationResult, RetrievalResult, DraftResponse, DecisionResult, TriageAction


class DecisionEngine:
    def __init__(self, config: Dict[str, Any]):
        self.cfg = config.get("decision", {})
        self.high_value_threshold = float(self.cfg.get("high_value_threshold", 10000.0))
        self.urgency_threshold = int(self.cfg.get("urgency_threshold", 5))
        self.min_category_confidence = float(self.cfg.get("min_category_confidence", 0.30))
        self.soft_confidence_threshold = float(self.cfg.get("soft_confidence_threshold", 0.55))
        self.review_confidence_min = float(self.cfg.get("review_confidence_min", 0.0))
        self.require_verification = self.cfg.get("require_claim_verification", True)
        self.approval_categories = self.cfg.get("approval_categories", [])
        
    def decide(
        self,
        preprocess_data: Dict[str, Any],
        rule_signals: Dict[str, Any],
        classification: ClassificationResult,
        retrieval_results: List[RetrievalResult],
        is_answerable: bool,
        draft_response: Optional[DraftResponse],
        component_failures: Optional[List[str]] = None
    ) -> DecisionResult:
        reasons: List[str] = []
        triggered_rules: List[str] = []
        component_failures = component_failures or []
        
        hard_escalate = False
        needs_review = False
        needs_approval = False
        needs_clarification = False
        clarification_question = None
        review_priority = "high"
        
        # Check thread history for Strike 2 (safety footer was already sent)
        thread_history = preprocess_data.get("thread_history", "")
        if "If this does not fully resolve your concern, simply reply to this email" in thread_history:
            hard_escalate = True
            triggered_rules.append("STRIKE_2_ESCALATION")
            reasons.append("Student replied after AI's first attempt. Escalate to human with full context.")

        # ==========================================
        # TIER 1: HARD BLOCK (Skip AI Entirely)
        # ==========================================
        
        # 1. Prompt Injection
        if preprocess_data.get("injection_detected", False):
            hard_escalate = True
            triggered_rules.append("RULE_2_PROMPT_INJECTION")
            reasons.append("Potential prompt injection pattern detected in ticket.")

        # 2. Legal Threat
        if rule_signals.get("is_legal_threat", False):
            hard_escalate = True
            triggered_rules.append("RULE_4_LEGAL_THREAT")
            reasons.append("Legal action, consumer court, or formal complaint threatened.")

        # 3. High Value Money
        if rule_signals.get("max_amount", 0.0) >= self.high_value_threshold:
            hard_escalate = True
            triggered_rules.append("RULE_3_HIGH_VALUE_MONEY")
            reasons.append(f"High monetary value transaction (Rs. {rule_signals.get('max_amount', 0.0):.2f} >= {self.high_value_threshold:.2f}).")
            
        # 4. Out of KB Topic / Third-party Transfer
        if rule_signals.get("is_out_of_kb_topic", False):
            hard_escalate = True
            triggered_rules.append("RULE_10_OUT_OF_KB")
            reasons.append("Ticket topic is out of knowledge base scope or third-party transfer is forbidden.")

        # 5. Academic Subject Matter Doubt (escalate to Teaching Assistant)
        if classification.category == "academic":
            hard_escalate = True
            triggered_rules.append("RULE_ACADEMIC_SUBJECT_MATTER")
            reasons.append("Academic question must be escalated to a Teaching Assistant (TA) for resolution.")

        # 6. Explicit Human Request
        human_request_patterns = ["talk to", "speak to", "connect me", "real person", "human agent", "manager"]
        if any(p in preprocess_data.get("cleaned_text", "").lower() for p in human_request_patterns):
            hard_escalate = True
            triggered_rules.append("RULE_14_EXPLICIT_HUMAN_REQUEST")
            reasons.append("Student explicitly requested a human agent.")

        # 7. Component Failure
        if component_failures:
            hard_escalate = True
            triggered_rules.append("RULE_12_COMPONENT_FAILURE")
            reasons.append(f"Critical upstream component failure occurred: {', '.join(component_failures)}")

        # ==========================================
        # TIER 2: APPROVAL REQUIRED (Irreversible Actions)
        # ==========================================
        
        if not hard_escalate and classification.category in self.approval_categories:
            if rule_signals.get("max_amount", 0.0) > 0 or classification.category in ["course_transfer", "subscription_cancellation"]:
                needs_approval = True
                triggered_rules.append("APPROVAL_REQUIRED_CATEGORY")
                reasons.append(f"Category '{classification.category}' involves irreversible actions (refund/transfer). Human must verify and send.")

        # ==========================================
        # TIER 3: CLARIFY (Need more info)
        # ==========================================
        
        if not hard_escalate and not needs_approval:
            if preprocess_data.get("is_empty_or_garbage", False):
                needs_clarification = True
                clarification_question = "Could you please elaborate on your concern?"
                triggered_rules.append("RULE_1_EMPTY_GARBAGE")
                reasons.append("Empty or unparseable input message.")
            elif classification.category in ["payment", "payment_dispute"] and not rule_signals.get("order_ids") and not rule_signals.get("upi_refs"):
                cleaned = preprocess_data.get("cleaned_text", "").lower()
                if any(w in cleaned for w in ["deducted", "debited", "paid", "payment", "kat gaya"]):
                    needs_clarification = True
                    clarification_question = "Could you please provide your Order ID (e.g., PW-12345) or UPI reference number so we can look up your payment details?"
                    triggered_rules.append("RULE_MISSING_TRANSACTION_ID")
                    reasons.append("Transaction reference ID missing for payment enquiry.")

        # ==========================================
        # TIER 4: SOFT ESCALATE (Auto-reply + Review)
        # ==========================================
        
        if not hard_escalate and not needs_approval and not needs_clarification:
            
            # Review confidence check
            if self.review_confidence_min > 0 and classification.confidence < self.review_confidence_min:
                needs_review = True
                review_priority = "medium"
                triggered_rules.append("RULE_8_MEDIUM_CONFIDENCE")
                reasons.append(f"Confidence ({classification.confidence:.2f}) below review threshold ({self.review_confidence_min:.2f}). Flagged for review.")

            # 1. Angry / Frustrated / Churn
            if (classification.angry_tone or classification.churn_risk or 
                rule_signals.get("is_angry", False) or rule_signals.get("is_churn_risk", False) or
                rule_signals.get("is_repeated_contact", False)):
                needs_review = True
                triggered_rules.append("RULE_5_AT_RISK_STUDENT")
                reasons.append("At-risk customer signal detected (frustration, repeated unresolved contacts, or churn threat). Flagged for review.")

            # 2. Multi-Issue
            if classification.multi_issue or len(rule_signals.get("category_hints", [])) > 1:
                needs_review = True
                triggered_rules.append("RULE_6_MULTI_ISSUE")
                reasons.append("Multi-issue ticket. Auto-replied on primary, flagged for review.")

            # 3. Urgency
            if classification.urgency >= self.urgency_threshold:
                hard_escalate = True
                triggered_rules.append("RULE_7_CRITICAL_URGENCY")
                reasons.append(f"Ticket urgency level ({classification.urgency}) meets critical threshold.")
            elif classification.urgency == self.urgency_threshold - 1:
                needs_review = True
                triggered_rules.append("RULE_7_HIGH_URGENCY")
                reasons.append(f"Ticket urgency level ({classification.urgency}) flagged for review.")

            # 4. Low Confidence
            if classification.confidence < self.min_category_confidence or classification.category in ["other", "general"]:
                hard_escalate = True
                triggered_rules.append("RULE_8_VERY_LOW_CONFIDENCE")
                reasons.append(f"Category classification highly uncertain (confidence {classification.confidence:.2f} < {self.min_category_confidence}).")
            elif classification.confidence < self.soft_confidence_threshold:
                needs_review = True
                triggered_rules.append("RULE_8_LOW_CONFIDENCE")
                reasons.append(f"Category classification moderately uncertain (confidence {classification.confidence:.2f} < {self.soft_confidence_threshold}). Flagged for review.")

            # 5. Not Answerable (or verification failed)
            top_dense = retrieval_results[0].dense_score if retrieval_results else 0.0
            if not is_answerable:
                if top_dense > 0.40:
                    needs_review = True
                    triggered_rules.append("RULE_10_PARTIALLY_ANSWERABLE")
                    reasons.append(f"KB answerability low, but partial match found (score {top_dense:.2f}). Sent best effort + review flag.")
                else:
                    hard_escalate = True
                    triggered_rules.append("RULE_10_NOT_ANSWERABLE")
                    reasons.append(f"Ticket topic is out-of-scope or unanswerable (score {top_dense:.2f} < 0.40).")

            if draft_response is None or not draft_response.claims_verified:
                needs_review = True
                triggered_rules.append("RULE_11_VERIFICATION_FAILED")
                unsupp = draft_response.unsupported_claims if draft_response else ["Draft unavailable"]
                reasons.append(f"Grounded claim verification failed: {'; '.join(unsupp)}. Sent best effort + review flag.")

        # ==========================================
        # FINAL ROUTING DECISION
        # ==========================================
        
        if hard_escalate:
            packet = f"**Escalation Handoff Packet**\n\n"
            packet += f"**Student Intent:** {preprocess_data.get('search_query', 'N/A')}\n\n"
            packet += f"**Category:** {classification.category.upper()}\n"
            packet += f"**Urgency:** {classification.urgency}/5\n"
            packet += f"**Action Required:** Please review the following reasons:\n"
            for r in reasons:
                packet += f"- {r}\n"
            
            return DecisionResult(
                action=TriageAction.ESCALATE,
                reasons=reasons,
                draft_reply=None,
                citations=[],
                confidence=classification.confidence,
                urgency=classification.urgency,
                handoff_packet=packet
            )
            
        if needs_clarification:
            return DecisionResult(
                action=TriageAction.CLARIFY,
                reasons=reasons,
                draft_reply=None,
                citations=[],
                confidence=classification.confidence,
                urgency=classification.urgency,
                clarification_question=clarification_question,
            )
            
        if needs_approval:
            if not draft_response or not draft_response.reply_text:
                packet = f"**Escalation Handoff Packet (Approval Category - No Draft)**\n\n"
                packet += f"**Student Intent:** {preprocess_data.get('search_query', 'N/A')}\n\n"
                packet += f"**Category:** {classification.category.upper()}\n"
                packet += f"**Urgency:** {classification.urgency}/5\n"
                packet += f"**Action Required:** Category requires approval, but no draft response was generated from KB.\n"
                for r in reasons:
                    packet += f"- {r}\n"
                return DecisionResult(
                    action=TriageAction.ESCALATE,
                    reasons=reasons + ["Approval required category but draft generation was unavailable; escalated for manual handling."],
                    draft_reply=None,
                    citations=[],
                    confidence=classification.confidence,
                    urgency=classification.urgency,
                    handoff_packet=packet
                )

            return DecisionResult(
                action=TriageAction.APPROVAL_REQUIRED,
                reasons=reasons,
                draft_reply=draft_response.reply_text,
                citations=draft_response.citations if draft_response else [],
                confidence=classification.confidence,
                urgency=classification.urgency,
            )
            
        if needs_review:
            if not draft_response or not draft_response.reply_text:
                packet = f"**Escalation Handoff Packet (Unanswerable / Review Flagged)**\n\n"
                packet += f"**Student Intent:** {preprocess_data.get('search_query', 'N/A')}\n\n"
                packet += f"**Category:** {classification.category.upper()}\n"
                packet += f"**Urgency:** {classification.urgency}/5\n"
                packet += f"**Action Required:** Auto-reply review triggered but draft response was unavailable from Knowledge Base.\n"
                for r in reasons:
                    packet += f"- {r}\n"
                return DecisionResult(
                    action=TriageAction.ESCALATE,
                    reasons=reasons + ["Draft response unavailable for auto-reply; escalated for manual triage."],
                    draft_reply=None,
                    citations=[],
                    confidence=classification.confidence,
                    urgency=classification.urgency,
                    handoff_packet=packet
                )

            return DecisionResult(
                action=TriageAction.AUTO_REPLY_WITH_REVIEW,
                reasons=reasons,
                draft_reply=draft_response.reply_text,
                citations=draft_response.citations if draft_response else [],
                confidence=classification.confidence,
                urgency=classification.urgency,
                review_priority=review_priority
            )
            
        # Default completely clean auto-reply
        if draft_response is None:
            # Fallback if somehow draft generation completely failed but no hard escalate was triggered
            return DecisionResult(
                action=TriageAction.ESCALATE,
                reasons=["Draft generation returned None unexpectedly."],
                draft_reply=None,
                citations=[],
                confidence=classification.confidence,
                urgency=classification.urgency,
                handoff_packet="Draft generation failed unexpectedly."
            )
            
        return DecisionResult(
            action=TriageAction.AUTO_REPLY,
            reasons=["Fully grounded answer verified against knowledge base policy. No risk flags detected."],
            draft_reply=draft_response.reply_text,
            citations=draft_response.citations,
            confidence=classification.confidence,
            urgency=classification.urgency,
        )
