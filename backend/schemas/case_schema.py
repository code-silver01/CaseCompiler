"""
Pydantic models for the case state.
Every extracted field carries a source and confidence indicator as required.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field
import uuid


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNVERIFIED = "unverified"


class SourceType(str, Enum):
    USER_STATEMENT = "user_statement"
    DOCUMENT = "document"
    INFERRED = "inferred"


class FieldSource(BaseModel):
    type: SourceType
    reference: Optional[str] = None  # filename or statement excerpt


class Party(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    role: str  # e.g. "landlord", "tenant", "agent"
    contact: Optional[str] = None
    address: Optional[str] = None
    source: FieldSource
    confidence: ConfidenceLevel


class Event(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    date_raw: Optional[str] = None       # as mentioned by user
    date_parsed: Optional[str] = None    # ISO 8601 if parseable, else None
    description: str
    source: FieldSource
    confidence: ConfidenceLevel


class Evidence(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    file_type: str  # "image", "pdf", "text"
    description: str
    extracted_facts: list[str] = Field(default_factory=list)
    source: FieldSource
    confidence: ConfidenceLevel
    quality_score: Optional[float] = None  # Continuous 0-100 ML evidence-quality score
    detected_type: Optional[str] = None    # e.g. "contract", "receipt", "bank_statement"
    feature_signals: Optional[dict[str, Any]] = None  # Key feature indicators for lawyer review
    raw_text: Optional[str] = None         # Cached raw text for ML feature extraction


class Claim(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    description: str
    legal_basis: Optional[str] = None
    source: FieldSource
    confidence: ConfidenceLevel
    supported_by_documents: list[str] = Field(default_factory=list)  # evidence IDs


class Financial(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    label: str          # e.g. "security deposit", "monthly rent"
    amount_inr: Optional[float] = None
    currency: str = "INR"
    date_raw: Optional[str] = None
    source: FieldSource
    confidence: ConfidenceLevel


class Contradiction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    description: str
    item_a: str         # description or ID of first item
    item_b: str         # description or ID of second item
    contradiction_type: str  # "date_mismatch" | "amount_mismatch" | "claim_mismatch"


class MissingInfo(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    description: str
    requested_by: str   # "system" | "interviewer"
    category: str       # "document", "date", "party", "financial", "other"


class RAGResult(BaseModel):
    query: str
    source_file: str
    excerpt: str
    relevance_score: float
    legal_area: Optional[str] = None


class TriageScore(BaseModel):
    level: str          # "HIGH" | "MEDIUM" | "LOW"
    reasons: list[str]
    score: int          # 0-100 numeric


class InterviewQuestion(BaseModel):
    question: str
    rationale: str      # why this question (for transparency)
    targets_gap: str    # which gap in the case state this addresses


class CritiqueFinding(BaseModel):
    finding_type: str   # "unsupported_claim" | "contradiction" | "low_confidence"
    description: str
    affected_item_id: Optional[str] = None


class CaseState(BaseModel):
    session_id: str
    created_at: str
    updated_at: str

    # Extracted entities
    parties: list[Party] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    financials: list[Financial] = Field(default_factory=list)

    # Analysis outputs
    contradictions: list[Contradiction] = Field(default_factory=list)
    missing_information: list[MissingInfo] = Field(default_factory=list)
    critique_findings: list[CritiqueFinding] = Field(default_factory=list)

    # RAG context
    rag_results: list[RAGResult] = Field(default_factory=list)

    # Interview state
    interview_history: list[dict[str, Any]] = Field(default_factory=list)  # [{role, content}]
    current_question: Optional[InterviewQuestion] = None
    interview_complete: bool = False

    # Triage
    triage: Optional[TriageScore] = None

    # Raw inputs (stored for self-critique)
    original_description: str = ""
    uploaded_filenames: list[str] = Field(default_factory=list)

    # Status
    extraction_done: bool = False
    compile_ready: bool = False
