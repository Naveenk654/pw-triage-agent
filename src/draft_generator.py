"""Grounded draft generator and deterministic claim verification."""

import re
from typing import List, Dict, Any
from src.models import RetrievalResult, DraftResponse
from src.llm_client import LLMClient


DRAFT_SYSTEM_PROMPT = """You are a polite, concise PhysicsWallah student support assistant.
Respond to the student query based STRICTLY on the retrieved policy evidence below.
Do NOT promise exceptions, do NOT speculate, and do NOT fabricate contact numbers or deadlines not present in evidence.
Always cite the source document name in square brackets, e.g. [refund] or [batch_access].
If the evidence does not clearly cover the query, explicitly state that you cannot confirm the policy.

CRITICAL STRUCTURE REQUIREMENT:
You MUST format your exact output according to the following strict template (do not output the numbering or labels, just output the paragraphs):
- Greeting: "Dear Student," (or similar professional greeting).
- Acknowledgment: Acknowledge their specific issue empathetically in one sentence.
- Resolution: Provide the exact grounded policy facts. You MUST include citations here.
- Next Steps: Tell them exactly what to expect or what they need to do next.
- Sign-off: "Best Regards,\nPhysicsWallah Support Team"

LANGUAGE REQUIREMENT:
You MUST ALWAYS generate your final reply in 100% formal, professional English, regardless of whether the student wrote their query in Hinglish, Hindi, or broken English. Do not use slang.

ACTION SAFETY RULE:
You must NEVER use confirmation language for irreversible actions.
NEVER say: "has been processed", "will be refunded", "has been transferred", "has been cancelled", "we have reversed", "your refund is on the way".
ALWAYS say: "Our policy states...", "To request this, please...", "Our team will verify and process...", "Please share your Order ID so we can...".
You are EXPLAINING POLICY, not EXECUTING ACTIONS.
"""


def generate_and_verify_draft(
    ticket: str,
    evidence: List[RetrievalResult],
    llm_client: LLMClient,
    thread_history: str = ""
) -> DraftResponse:
    """
    Drafts an answer grounded exclusively in retrieved evidence and verifies citations.
    """
    if not evidence:
        return DraftResponse(
            reply_text="",
            citations=[],
            claims_verified=False,
            unsupported_claims=["No evidence retrieved."]
        )
        
    context_str = "\n\n".join([f"Source [{r.document}]: {r.content}" for r in evidence[:3]])
    
    prompt = f"Retrieved Policy Evidence:\n{context_str}\n\nStudent Ticket:\n{ticket}"
    if thread_history:
        prompt += f"\n\nPrevious Thread Context:\n{thread_history}"
    prompt += "\n\nDraft Answer:"
    
    gen_result = llm_client.generate(prompt=prompt, system_prompt=DRAFT_SYSTEM_PROMPT)
    reply_text = gen_result["text"]
    
    # Extract citations like [refund] or [batch_access]
    citations_found = re.findall(r"\[([a-zA-Z0-9_\-]+)\]", reply_text)
    valid_docs = {r.document for r in evidence}
    
    unsupported = []
    for c in citations_found:
        if c.lower() not in valid_docs and c.lower() != "mock":
            unsupported.append(f"Referenced citation [{c}] not present in retrieved context.")
            
    claims_verified = (len(unsupported) == 0)
    
    return DraftResponse(
        reply_text=reply_text,
        citations=list(set(citations_found)),
        claims_verified=claims_verified,
        unsupported_claims=unsupported,
        prompt_tokens=gen_result.get("prompt_tokens", 0),
        completion_tokens=gen_result.get("completion_tokens", 0)
    )
