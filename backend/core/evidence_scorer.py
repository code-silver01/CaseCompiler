"""
Evidence Quality Scorer: Machine Learning Integration
Uses a trained XGBoost regression model (evidence_quality_model.pkl) to evaluate
the quality, reliability, and corroboration level of uploaded legal evidence.

Features evaluated in exact order:
 1. ocr_quality
 2. has_date
 3. has_sender
 4. has_recipient
 5. has_timestamp
 6. contains_names
 7. contains_amount
 8. contains_event
 9. timeline_match
10. claim_similarity
11. contradiction_score
12. duplicate_score
13. text_length
14. document_type_bank_statement
15. document_type_contract
16. document_type_email
17. document_type_handwritten
18. document_type_photo
19. document_type_receipt
20. document_type_scanned_document
21. document_type_whatsapp

Score Mapping:
  >= 75.0       -> ConfidenceLevel.HIGH
  50.0 - 74.99  -> ConfidenceLevel.MEDIUM
  < 50.0        -> ConfidenceLevel.LOW
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Optional

import joblib
import numpy as np
import pandas as pd

from schemas.case_schema import CaseState, ConfidenceLevel

logger = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).parent.parent / "models" / "evidence_quality_model.pkl"
_model = None

FEATURE_COLUMNS: list[str] = [
    "ocr_quality",
    "has_date",
    "has_sender",
    "has_recipient",
    "has_timestamp",
    "contains_names",
    "contains_amount",
    "contains_event",
    "timeline_match",
    "claim_similarity",
    "contradiction_score",
    "duplicate_score",
    "text_length",
    "document_type_bank_statement",
    "document_type_contract",
    "document_type_email",
    "document_type_handwritten",
    "document_type_photo",
    "document_type_receipt",
    "document_type_scanned_document",
    "document_type_whatsapp",
]

DOCUMENT_TYPES: list[str] = [
    "bank_statement",
    "contract",
    "email",
    "handwritten",
    "photo",
    "receipt",
    "scanned_document",
    "whatsapp",
]

_DATE_PATTERNS = [
    re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"),
    re.compile(r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b"),
    re.compile(
        r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s*,?\s*\d{2,4}\b",
        re.IGNORECASE,
    ),
]

_TIMESTAMP_PATTERNS = [
    re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\s*(?:am|pm|hrs|hours)?\b", re.IGNORECASE),
    re.compile(r"\b\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}", re.IGNORECASE),
    re.compile(r"\b(?:ist|gmt|utc)\b", re.IGNORECASE),
]

_SENDER_KEYWORDS = [
    "from:", "sender:", "landlord:", "lessor:", "licensor:", "issued by", "first party",
    "authorized signatory", "authorized signature", "sub-registrar", "bank branch",
]

_RECIPIENT_KEYWORDS = [
    "to:", "tenant:", "recipient:", "lessee:", "licensee:", "second party",
    "in favour of", "received from", "client name", "account holder",
]

_EVENT_KEYWORDS = [
    "agreement", "tenancy", "lease", "rent", "deposit", "vacate", "vacating",
    "eviction", "notice", "handover", "possession", "cheque", "transfer", "paid",
    "payment", "painting", "maintenance", "deduction", "damage", "hearing", "order",
]


def load_model():
    """Load the trained XGBoost model singleton."""
    global _model
    if _model is None:
        if MODEL_PATH.exists():
            try:
                _model = joblib.load(MODEL_PATH)
                logger.info("Loaded evidence quality ML model from %s", MODEL_PATH)
            except Exception as e:
                logger.error("Failed to load evidence quality model: %s", e)
        else:
            logger.warning("Evidence quality model not found at %s", MODEL_PATH)
    return _model


def detect_document_type(filename: str, text: str, file_type: str) -> str:
    """Classify the document into one of the 8 trained document types."""
    name_lower = filename.lower()
    text_lower = text.lower()

    if any(k in name_lower or k in text_lower for k in ("bank", "statement", "passbook", "ifsc", "transaction", "debit", "credit balance")):
        return "bank_statement"
    if any(k in name_lower or k in text_lower for k in ("rent agreement", "lease agreement", "contract", "deed", "terms and conditions", "lessor", "lessee", "stamp paper")):
        return "contract"
    if any(k in name_lower or k in text_lower for k in ("receipt", "voucher", "bill", "invoice", "payment acknowledgement")):
        return "receipt"
    if any(k in name_lower or k in text_lower for k in ("whatsapp", "chat", "messages and calls are end-to-end encrypted")):
        return "whatsapp"
    if any(k in name_lower or k in text_lower for k in ("email", "mail", "gmail", "outlook", "subject:", "re:")):
        return "email"
    if file_type == "image":
        if len(text.strip()) < 80:
            return "photo"
        return "handwritten" if any(k in name_lower for k in ("note", "hand", "rough")) else "scanned_document"
    if file_type == "pdf":
        return "scanned_document"

    return "contract"


def compute_ocr_quality(text: str, file_type: str) -> float:
    """Estimate OCR/text clarity between 0.0 and 1.0."""
    if not text or len(text.strip()) == 0:
        return 0.2 if file_type == "image" else 0.1
    clean_chars = sum(1 for c in text if c.isalnum() or c.isspace() or c in ".,!?;:'\"-₹$%/()[]@#")
    ratio = clean_chars / max(len(text), 1)
    if len(text) > 200:
        return min(1.0, max(0.2, ratio))
    return min(1.0, max(0.2, ratio * 0.8))


def extract_features(
    filename: str,
    text: str,
    file_type: str,
    state: CaseState,
    all_uploaded_texts: list[str],
) -> tuple[dict[str, float], str, dict[str, Any]]:
    """
    Extract the exact 21 features required by the trained model.
    Returns (features_dict, detected_doc_type, display_signals).
    """
    text_lower = text.lower()
    detected_type = detect_document_type(filename, text, file_type)

    # 1. ocr_quality
    ocr_quality = round(compute_ocr_quality(text, file_type), 3)

    # 2. has_date
    has_date = 1.0 if any(p.search(text) for p in _DATE_PATTERNS) else 0.0

    # 3. has_sender
    has_sender = 0.0
    if any(k in text_lower for k in _SENDER_KEYWORDS):
        has_sender = 1.0
    elif any(p.role.lower() in ("landlord", "owner", "agent") and p.name.lower() in text_lower for p in state.parties):
        has_sender = 1.0

    # 4. has_recipient
    has_recipient = 0.0
    if any(k in text_lower for k in _RECIPIENT_KEYWORDS):
        has_recipient = 1.0
    elif any(p.role.lower() in ("tenant", "occupant", "licensee") and p.name.lower() in text_lower for p in state.parties):
        has_recipient = 1.0

    # 5. has_timestamp
    has_timestamp = 1.0 if any(p.search(text) for p in _TIMESTAMP_PATTERNS) else 0.0

    # 6. contains_names
    contains_names = 0.0
    if any(len(p.name) >= 3 and p.name.lower() in text_lower for p in state.parties):
        contains_names = 1.0
    elif re.search(r"\b(?:mr|mrs|ms|shri|smt|dr)\.?\s+[A-Z][a-z]+", text):
        contains_names = 1.0

    # 7. contains_amount
    contains_amount = 0.0
    if any(k in text_lower for k in ("₹", "rs", "inr", "rupees")):
        contains_amount = 1.0
    elif any(f.amount_inr and f"{f.amount_inr:,.0f}" in text for f in state.financials):
        contains_amount = 1.0
    elif re.search(r"\b\d{4,7}\b", text):
        contains_amount = 1.0

    # 8. contains_event
    contains_event = 1.0 if any(k in text_lower for k in _EVENT_KEYWORDS) else 0.0

    # 9. timeline_match
    timeline_match = 0.0
    if has_date:
        event_dates = [e.date_parsed for e in state.events if e.date_parsed]
        if event_dates:
            timeline_match = 1.0 if any(ed in text for ed in event_dates) else 0.7
        else:
            timeline_match = 0.5

    # 10. claim_similarity
    claim_similarity = 0.0
    claim_words = set(re.findall(r"\w+", " ".join(c.description for c in state.claims).lower()))
    doc_words = set(re.findall(r"\w+", text_lower))
    if claim_words and doc_words:
        overlap = len(claim_words.intersection(doc_words))
        claim_similarity = round(min(1.0, overlap / max(len(claim_words), 5)), 3)
    elif doc_words:
        claim_similarity = 0.4

    # 11. contradiction_score
    contradiction_score = 0.0
    for c in state.contradictions:
        if filename.lower() in c.description.lower() or c.item_a.lower() in text_lower or c.item_b.lower() in text_lower:
            contradiction_score = 1.0
            break

    # 12. duplicate_score
    duplicate_score = 0.0
    if len(all_uploaded_texts) > 1 and doc_words:
        for other_text in all_uploaded_texts:
            if other_text != text and other_text.strip():
                other_words = set(re.findall(r"\w+", other_text.lower()))
                if other_words:
                    jaccard = len(doc_words.intersection(other_words)) / len(doc_words.union(other_words))
                    if jaccard > duplicate_score:
                        duplicate_score = round(jaccard, 3)

    # 13. text_length
    text_length = float(len(text))

    # 14-21. One-hot document types
    doc_type_features: dict[str, float] = {}
    for dt in DOCUMENT_TYPES:
        doc_type_features[f"document_type_{dt}"] = 1.0 if dt == detected_type else 0.0

    features = {
        "ocr_quality": ocr_quality,
        "has_date": has_date,
        "has_sender": has_sender,
        "has_recipient": has_recipient,
        "has_timestamp": has_timestamp,
        "contains_names": contains_names,
        "contains_amount": contains_amount,
        "contains_event": contains_event,
        "timeline_match": timeline_match,
        "claim_similarity": claim_similarity,
        "contradiction_score": contradiction_score,
        "duplicate_score": duplicate_score,
        "text_length": text_length,
        **doc_type_features,
    }

    display_signals = {
        "ocr_quality": f"{int(ocr_quality * 100)}%",
        "has_date": bool(has_date),
        "has_parties": bool(has_sender or has_recipient or contains_names),
        "has_financials": bool(contains_amount),
        "has_events": bool(contains_event),
        "timeline_aligned": bool(timeline_match >= 0.5),
        "contradiction_flagged": bool(contradiction_score > 0.5),
        "detected_type": detected_type.replace("_", " ").title(),
    }

    return features, detected_type, display_signals


def score_evidence_document(
    filename: str,
    text: str,
    file_type: str,
    state: CaseState,
    all_uploaded_texts: Optional[list[str]] = None,
) -> tuple[float, ConfidenceLevel, str, dict[str, Any]]:
    """
    Score a single evidence document using the trained XGBoost model.
    Returns (quality_score_0_to_100, confidence_level, detected_type, display_signals).
    """
    if all_uploaded_texts is None:
        all_uploaded_texts = [text]

    features, detected_type, display_signals = extract_features(
        filename=filename,
        text=text,
        file_type=file_type,
        state=state,
        all_uploaded_texts=all_uploaded_texts,
    )

    model = load_model()
    if model is not None:
        try:
            # Build 1-row DataFrame in exact feature order
            row_data = {col: features.get(col, 0.0) for col in FEATURE_COLUMNS}
            df = pd.DataFrame([row_data], columns=FEATURE_COLUMNS)
            raw_pred = model.predict(df)
            score = float(raw_pred[0])
            score = max(0.0, min(100.0, score))  # Clamp to 0-100 range
        except Exception as e:
            logger.error("Error predicting evidence quality score for %s: %s", filename, e)
            score = 65.0  # Safe fallback
    else:
        # Heuristic fallback if model file is not present
        score = 60.0
        if features["has_date"]:
            score += 10.0
        if features["has_sender"] and features["has_recipient"]:
            score += 15.0
        if features["contains_amount"]:
            score += 10.0
        score = min(100.0, score)

    # Convert continuous score to ConfidenceLevel according to user specifications:
    # >= 75.0      -> HIGH
    # 50.0 - 74.99 -> MEDIUM
    # < 50.0       -> LOW
    if score >= 75.0:
        confidence = ConfidenceLevel.HIGH
    elif score >= 50.0:
        confidence = ConfidenceLevel.MEDIUM
    else:
        confidence = ConfidenceLevel.LOW

    return round(score, 1), confidence, detected_type, display_signals
