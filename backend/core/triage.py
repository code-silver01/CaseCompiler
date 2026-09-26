"""
Deterministic urgency / triage scoring. NO LLM calls.
Rules are explicit, explainable, and auditable.

Score bands:
  HIGH   (score 70-100): Immediate attention required
  MEDIUM (score 40-69):  Action needed soon
  LOW    (score 0-39):   Monitor

FUTURE WORK: Add more rule categories (e.g. harassment, domestic violence flags).
"""
from __future__ import annotations

from config import (
    TRIAGE_COURT_DATE_HIGH_DAYS,
    TRIAGE_COURT_DATE_MEDIUM_DAYS,
    TRIAGE_EVICTION_NOTICE_HIGH_DAYS,
    TRIAGE_HIGH_FINANCIAL_THRESHOLD_INR,
)
from core.chronology import days_until
from schemas.case_schema import CaseState, TriageScore

# Keywords that indicate urgency in event descriptions (case-insensitive)
_COURT_KEYWORDS = ["court", "hearing", "tribunal", "summons", "writ", "order"]
_EVICTION_KEYWORDS = ["eviction", "vacate", "vacating", "notice to quit", "quit notice"]
_POLICE_KEYWORDS = ["fir", "police", "arrest", "complaint filed"]


def _contains_any(text: str, keywords: list[str]) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in keywords)


def compute_triage(state: CaseState) -> TriageScore:
    """
    Evaluate the case state and return a TriageScore.
    All logic is rule-based; no GenAI calls.
    """
    score = 0
    reasons: list[str] = []

    # --- Rule 1: Upcoming court/tribunal dates ---
    for event in state.events:
        if _contains_any(event.description, _COURT_KEYWORDS) and event.date_parsed:
            days = days_until(event.date_parsed)
            if days is not None:
                if 0 <= days <= TRIAGE_COURT_DATE_HIGH_DAYS:
                    score = max(score, 85)
                    reasons.append(
                        f"Court/tribunal date in {days} day(s) "
                        f"({event.date_parsed}) — HIGH urgency threshold is {TRIAGE_COURT_DATE_HIGH_DAYS} days."
                    )
                elif 0 <= days <= TRIAGE_COURT_DATE_MEDIUM_DAYS:
                    score = max(score, 55)
                    reasons.append(
                        f"Court/tribunal date in {days} day(s) ({event.date_parsed})."
                    )

    # --- Rule 2: Eviction notice expiry ---
    for event in state.events:
        if _contains_any(event.description, _EVICTION_KEYWORDS) and event.date_parsed:
            days = days_until(event.date_parsed)
            if days is not None and 0 <= days <= TRIAGE_EVICTION_NOTICE_HIGH_DAYS:
                score = max(score, 90)
                reasons.append(
                    f"Eviction notice expires in {days} day(s) ({event.date_parsed}). "
                    f"Immediate legal action may be required."
                )

    # --- Rule 3: High financial amount ---
    for fin in state.financials:
        if fin.amount_inr and fin.amount_inr >= TRIAGE_HIGH_FINANCIAL_THRESHOLD_INR:
            score = max(score, 60)
            reasons.append(
                f"High financial stake: ₹{fin.amount_inr:,.0f} ({fin.label}). "
                f"Threshold for elevated urgency: ₹{TRIAGE_HIGH_FINANCIAL_THRESHOLD_INR:,.0f}."
            )

    # --- Rule 4: Police/FIR mentions ---
    for event in state.events:
        if _contains_any(event.description, _POLICE_KEYWORDS):
            score = max(score, 75)
            reasons.append(
                f"Criminal/police action mentioned: '{event.description[:80]}'. "
                f"Legal representation may be urgently required."
            )

    # --- Rule 5: Missing critical information penalty ---
    if len(state.missing_information) >= 5:
        score = max(score, 35)
        reasons.append(
            f"{len(state.missing_information)} critical information gaps identified. "
            f"Case cannot proceed without clarification."
        )

    # --- Determine band ---
    if score >= 70:
        level = "HIGH"
    elif score >= 40:
        level = "MEDIUM"
    else:
        level = "LOW"
        if not reasons:
            reasons.append("No immediate urgency indicators found. Standard review timeline applies.")

    return TriageScore(level=level, reasons=reasons, score=score)
