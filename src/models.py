"""Data models for PW-Style EdTech Support Ticket Triage Agent."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class KBChunk(BaseModel):
    chunk_id: str
    document: str
    section_title: str
    section_index: int
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RetrievalResult(BaseModel):
    chunk_id: str
    document: str
    section_title: str
    content: str
    dense_score: float = 0.0
    dense_rank: int = 0
    bm25_score: float = 0.0
    bm25_rank: int = 0
    rrf_score: float = 0.0
    rrf_rank: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ClassificationResult(BaseModel):
    category: str
    parent_category: Optional[str] = None
    confidence: float
    urgency: int = Field(default=1, ge=1, le=5)  # 1 to 5 scale
    churn_risk: bool = False
    angry_tone: bool = False
    legal_threat: bool = False
    multi_issue: bool = False
    detected_entities: Dict[str, str] = Field(default_factory=dict)
    backend_used: str = "keyword"


class DraftResponse(BaseModel):
    reply_text: str
    citations: List[str] = Field(default_factory=list)
    claims_verified: bool = True
    unsupported_claims: List[str] = Field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0


from enum import Enum

class TriageAction(str, Enum):
    AUTO_REPLY = "AUTO_REPLY"
    AUTO_REPLY_WITH_REVIEW = "AUTO_REPLY_WITH_REVIEW"
    CLARIFY = "CLARIFY"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    ESCALATE = "ESCALATE"

class DecisionResult(BaseModel):
    action: TriageAction
    reasons: List[str] = Field(default_factory=list)
    draft_reply: Optional[str] = None
    citations: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    urgency: int = 1
    clarification_question: Optional[str] = None  # For CLARIFY action
    review_priority: Optional[str] = None          # "low" | "medium" | "high" for REVIEW tier
    handoff_packet: Optional[str] = None           # Structured packet for human agents
