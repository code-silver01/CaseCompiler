"""
Agentic interviewer: given the FULL current case state, decide the
next most useful clarifying question and update state as the user responds.

Each turn feeds the COMPLETE case state to Gemini — not just chat history.
This ensures questions are driven by real gaps, not conversational context.
"""
from __future__ import annotations

import json
import logging

from google import genai
from google.genai import types

import config
from core.extractor import get_client, extract_case, self_critique, generate_content_with_fallback
from core.chronology import parse_date, deduplicate_events, sort_events
from schemas.case_schema import (
    CaseState,
    InterviewQuestion,
    MissingInfo,
    Event,
    FieldSource,
    SourceType,
    ConfidenceLevel,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_INTERVIEW_SYSTEM = """You are a careful legal intake specialist conducting an interview.
You have the COMPLETE current case state below.
Your job: identify the SINGLE most important gap, ambiguity, or missing fact 
that would most help a lawyer understand this case.

Focus priority (in order):
1. Missing dates for key events (especially notice dates, rent due dates, deposit payment)
2. Missing party details (landlord/agent contact, full names)
3. Unquantified financial claims (exact amounts for deposit, unpaid rent, damages)
4. Missing documents that were mentioned but not provided
5. Contradictions that need clarification
6. Anything flagged in missing_information

Do NOT ask about things already present in the case state.
Do NOT ask multiple questions at once.
Do NOT ask generic or procedural questions — be specific to this case.

Return a JSON object:
{
  "question": "The exact question to ask the user",
  "rationale": "Why this is the most important gap right now",
  "targets_gap": "Brief label of the gap (e.g. 'landlord contact', 'deposit amount')",
  "interview_complete": false
}

If the case state is sufficiently complete for a lawyer to work with
(all key parties identified, key events dated, main claims clear, 
at least some financial figures present), set "interview_complete": true
and set "question" to a polite closing statement.

Return ONLY valid JSON."""


_UPDATE_SYSTEM = """You are a legal intake specialist.
The user has just answered an interview question about their case.
Extract any NEW facts from their answer and return them as JSON.

Return ONLY a JSON object with these optional keys (include only what's present in the answer):
{
  "new_events": [{"date_raw": "...", "description": "...", "confidence": "high|medium|low"}],
  "new_parties": [{"name": "...", "role": "...", "contact": "...", "confidence": "high|medium|low"}],
  "new_financials": [{"label": "...", "amount_inr": 0, "confidence": "high|medium|low"}],
  "new_claims": [{"description": "...", "confidence": "high|medium|low"}],
  "resolved_gaps": ["brief description of what was clarified"]
}

If the answer contains no new structured information, return {}.
Return ONLY valid JSON."""


# ---------------------------------------------------------------------------
# Core interview functions
# ---------------------------------------------------------------------------

def generate_next_question(state: CaseState) -> tuple[InterviewQuestion, bool]:
    """
    Feed the full case state to Gemini and get the next targeted question.
    """
    client = get_client()

    state_summary = _build_state_summary(state)
    prompt = f"{_INTERVIEW_SYSTEM}\n\nCURRENT CASE STATE:\n{state_summary}"

    response = generate_content_with_fallback(
        client,
        contents=prompt,
        gen_config=types.GenerateContentConfig(
            temperature=0.3,
            response_mime_type="application/json",
            thinking_config=types.ThinkingConfig(
                thinking_level=types.ThinkingLevel.MINIMAL
            ),
        ),
    )

    raw = (response.text or "{}").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Interview question JSON parse failed: %s", raw[:200])
        data = {}

    interview_complete = data.get("interview_complete", False)

    return InterviewQuestion(
        question=data.get("question", "Can you provide any additional details about your situation?"),
        rationale=data.get("rationale", ""),
        targets_gap=data.get("targets_gap", "general"),
    ), interview_complete


def process_answer(state: CaseState, answer: str) -> CaseState:
    """
    Process the user's answer to the current interview question.
    Extract new facts and merge them into the case state.
    """
    client = get_client()

    question_text = state.current_question.question if state.current_question else "general question"

    prompt = (
        f"{_UPDATE_SYSTEM}\n\n"
        f"INTERVIEW QUESTION ASKED: {question_text}\n\n"
        f"USER'S ANSWER: {answer}"
    )

    response = generate_content_with_fallback(
        client,
        contents=prompt,
        gen_config=types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
            thinking_config=types.ThinkingConfig(
                thinking_level=types.ThinkingLevel.MINIMAL
            ),
        ),
    )

    raw = (response.text or "{}").strip()
    try:
        updates = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Answer update JSON parse failed: %s", raw[:200])
        updates = {}

    # Merge new events
    for ev_data in updates.get("new_events", []):
        date_raw = ev_data.get("date_raw")
        new_event = Event(
            date_raw=date_raw,
            date_parsed=parse_date(date_raw),
            description=ev_data.get("description", ""),
            source=FieldSource(type=SourceType.USER_STATEMENT, reference=f"answer: {answer[:80]}"),
            confidence=_parse_confidence(ev_data.get("confidence", "medium")),
        )
        state.events.append(new_event)

    state.events = sort_events(deduplicate_events(state.events))

    # Merge new parties (deduplicating against existing parties by name)
    from schemas.case_schema import Party
    for p_data in updates.get("new_parties", []):
        name = p_data.get("name", "").strip()
        if not name:
            continue
        existing = next((p for p in state.parties if p.name.strip().lower() == name.lower()), None)
        if existing:
            if not existing.contact and p_data.get("contact"):
                existing.contact = p_data.get("contact")
            if (not existing.role or existing.role.lower() == "unknown") and p_data.get("role"):
                existing.role = p_data.get("role")
        else:
            state.parties.append(
                Party(
                    name=name,
                    role=p_data.get("role", "unknown"),
                    contact=p_data.get("contact"),
                    source=FieldSource(type=SourceType.USER_STATEMENT, reference=f"answer: {answer[:80]}"),
                    confidence=_parse_confidence(p_data.get("confidence", "medium")),
                )
            )

    # Merge new financials (deduplicating identical label/amount)
    from schemas.case_schema import Financial
    for f_data in updates.get("new_financials", []):
        label = f_data.get("label", "").strip()
        amt = f_data.get("amount_inr")
        if not label:
            continue
        existing_f = next((f for f in state.financials if f.label.strip().lower() == label.lower() and f.amount_inr == amt), None)
        if not existing_f:
            state.financials.append(
                Financial(
                    label=label,
                    amount_inr=amt,
                    source=FieldSource(type=SourceType.USER_STATEMENT, reference=f"answer: {answer[:80]}"),
                    confidence=_parse_confidence(f_data.get("confidence", "medium")),
                )
            )

    # Merge new claims (deduplicating identical description)
    from schemas.case_schema import Claim
    for c_data in updates.get("new_claims", []):
        desc = c_data.get("description", "").strip()
        if not desc:
            continue
        existing_c = next((c for c in state.claims if c.description.strip().lower() == desc.lower()), None)
        if not existing_c:
            state.claims.append(
                Claim(
                    description=desc,
                    source=FieldSource(type=SourceType.USER_STATEMENT, reference=f"answer: {answer[:80]}"),
                    confidence=_parse_confidence(c_data.get("confidence", "medium")),
                )
            )

    # Remove resolved gaps from missing_information
    resolved = updates.get("resolved_gaps", [])
    if resolved:
        state.missing_information = [
            mi for mi in state.missing_information
            if not any(r.lower() in mi.description.lower() for r in resolved)
        ]

    # Add to interview history
    state.interview_history.append({"role": "assistant", "content": question_text})
    state.interview_history.append({"role": "user", "content": answer})

    return state


def _build_state_summary(state: CaseState) -> str:
    """Compact case state for the interview prompt."""
    lines = []
    lines.append(f"Original description: {state.original_description[:600]}")

    lines.append(f"\nParties ({len(state.parties)}):")
    for p in state.parties:
        lines.append(f"  - {p.name} [{p.role}] contact={p.contact} confidence={p.confidence}")

    lines.append(f"\nEvents ({len(state.events)}):")
    for e in state.events:
        lines.append(f"  - {e.date_parsed or e.date_raw or '??'}: {e.description[:100]}")

    lines.append(f"\nClaims ({len(state.claims)}):")
    for c in state.claims:
        lines.append(f"  - {c.description[:100]} (confidence={c.confidence})")

    lines.append(f"\nFinancials ({len(state.financials)}):")
    for f in state.financials:
        amt = f"₹{f.amount_inr:,.0f}" if f.amount_inr else "amount unknown"
        lines.append(f"  - {f.label}: {amt}")

    lines.append(f"\nMissing information ({len(state.missing_information)}):")
    for mi in state.missing_information:
        lines.append(f"  - [{mi.category}] {mi.description}")

    lines.append(f"\nContradictions ({len(state.contradictions)}):")
    for c in state.contradictions:
        lines.append(f"  - {c.contradiction_type}: {c.description}")

    lines.append(f"\nPrevious interview Q&A turns: {len(state.interview_history) // 2}")

    return "\n".join(lines)


def _parse_confidence(val: str) -> ConfidenceLevel:
    try:
        return ConfidenceLevel(val.lower())
    except ValueError:
        return ConfidenceLevel.MEDIUM
