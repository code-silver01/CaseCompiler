"""
Case compiler: assembles the final structured case file from a complete CaseState.
Output is a structured dict with 11 sections as specified.

IMPORTANT: Every section that contains RAG-grounded content is explicitly hedged
as "potentially relevant" — never presented as legal fact or advice.
This tool organises information for lawyer review, NOT legal advice.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import config
from core.chronology import sort_events
from core.triage import compute_triage
from schemas.case_schema import CaseState, ConfidenceLevel


def compile_case_file(state: CaseState) -> dict:
    """
    Assemble and return the final case file as a structured dict.
    Sections are numbered 1-11 as per the spec.
    """
    # Ensure triage is current
    if not state.triage:
        state.triage = compute_triage(state)

    # Sort events for chronology
    sorted_events = sort_events(state.events)
    unique_parties = _deduplicate_parties(state.parties)

    # Separate user-reported vs document-supported facts
    user_facts = _user_facts(state)
    doc_facts = _document_facts(state)

    compiled_at = datetime.now(timezone.utc).isoformat()

    return {
        "meta": {
            "compiled_at": compiled_at,
            "session_id": state.session_id,
            "model_used": config.GEMINI_MODEL,
            "disclaimer": (
                "⚠️ This document is produced by an AI case organisation tool for the purpose "
                "of helping a qualified legal practitioner review a client matter. "
                "Nothing in this document constitutes legal advice. All extracted facts "
                "are unverified and require professional validation. "
                "RAG-grounded references are marked 'potentially relevant' and must be "
                "independently verified against authoritative legal sources."
            ),
        },

        # Section 1: Executive Summary
        "section_1_executive_summary": {
            "title": "Executive Summary",
            "triage_level": state.triage.level if state.triage else "UNKNOWN",
            "triage_score": state.triage.score if state.triage else 0,
            "triage_reasons": state.triage.reasons if state.triage else [],
            "parties_count": len(unique_parties),
            "events_count": len(sorted_events),
            "claims_count": len(state.claims),
            "evidence_count": len(state.evidence),
            "missing_info_count": len(state.missing_information),
            "contradictions_count": len(state.contradictions),
            "summary_note": (
                f"Case involves {len(unique_parties)} identified parties, "
                f"{len(state.claims)} claim(s), and {len(state.evidence)} piece(s) of evidence. "
                f"Urgency: {state.triage.level if state.triage else 'unscored'}."
            ),
        },

        # Section 2: Parties
        "section_2_parties": {
            "title": "Parties",
            "parties": [
                {
                    "name": p.name,
                    "role": p.role,
                    "contact": p.contact,
                    "address": p.address,
                    "source": p.source.model_dump(),
                    "confidence": p.confidence,
                }
                for p in unique_parties
            ],
        },

        # Section 3: Chronology
        "section_3_chronology": {
            "title": "Chronology",
            "note": "Events sorted chronologically. Dates without a parseable format are placed at end.",
            "events": [
                {
                    "date": ev.date_parsed or ev.date_raw or "Unknown date",
                    "date_parsed": ev.date_parsed,
                    "date_raw": ev.date_raw,
                    "description": ev.description,
                    "source": ev.source.model_dump(),
                    "confidence": ev.confidence,
                }
                for ev in sorted_events
            ],
        },

        # Section 4: Facts reported by user (unverified)
        "section_4_user_reported_facts": {
            "title": "Facts Reported by User (Unverified)",
            "note": "These facts come solely from the user's statements and have not been verified against documents.",
            "facts": user_facts,
        },

        # Section 5: Document-supported facts
        "section_5_document_supported_facts": {
            "title": "Document-Supported Facts",
            "note": "These facts are drawn from or corroborated by uploaded documents.",
            "facts": doc_facts,
        },

        # Section 6: Claims / assertions
        "section_6_claims": {
            "title": "Claims and Assertions",
            "note": "Unverified claims as stated. Require legal assessment by a qualified practitioner.",
            "claims": [
                {
                    "description": c.description,
                    "legal_basis_mentioned": c.legal_basis,
                    "supported_by_documents": c.supported_by_documents,
                    "source": c.source.model_dump(),
                    "confidence": c.confidence,
                }
                for c in state.claims
            ],
        },

        # Section 7: Evidence map
        "section_7_evidence_map": {
            "title": "Evidence Map",
            "evidence": [
                {
                    "filename": ev.filename,
                    "type": ev.file_type,
                    "detected_type": ev.detected_type or ev.file_type,
                    "description": ev.description,
                    "extracted_facts": ev.extracted_facts,
                    "source": ev.source.model_dump(),
                    "confidence": ev.confidence,
                    "quality_score": ev.quality_score,
                    "feature_signals": ev.feature_signals,
                }
                for ev in state.evidence
            ],
            "financials": [
                {
                    "label": f.label,
                    "amount_inr": f.amount_inr,
                    "date": f.date_raw,
                    "source": f.source.model_dump(),
                    "confidence": f.confidence,
                }
                for f in state.financials
            ],
        },

        # Section 8: Potential inconsistencies (date/amount mismatches only, v1)
        "section_8_inconsistencies": {
            "title": "Potential Inconsistencies",
            "scope_note": (
                "v1 scope: date mismatches and amount mismatches only. "
                "Broader inconsistency analysis requires human review."
            ),
            "inconsistencies": [
                {
                    "type": c.contradiction_type,
                    "description": c.description,
                    "item_a": c.item_a,
                    "item_b": c.item_b,
                }
                for c in state.contradictions
            ],
            "critique_findings": [
                {
                    "type": cf.finding_type,
                    "description": cf.description,
                    "affected_item": cf.affected_item_id,
                }
                for cf in state.critique_findings
            ],
        },

        # Section 9: Missing information
        "section_9_missing_information": {
            "title": "Missing Information",
            "missing": [
                {
                    "description": mi.description,
                    "category": mi.category,
                    "requested_by": mi.requested_by,
                }
                for mi in state.missing_information
            ],
        },

        # Section 10: Potentially relevant legal areas (RAG-grounded, hedged)
        "section_10_legal_areas": {
            "title": "Potentially Relevant Legal Areas",
            "disclaimer": (
                "The following are potentially relevant legal provisions retrieved from a "
                "curated knowledge base. They are provided for organisational purposes only "
                "and do NOT constitute legal advice. A qualified practitioner must verify "
                "applicability and current validity of any statute or procedure."
            ),
            "rag_results": [
                {
                    "potentially_relevant_query": r.query,
                    "source_document": r.source_file,
                    "excerpt": r.excerpt,
                    "relevance_score": round(r.relevance_score, 4),
                    "legal_area": r.legal_area,
                    "hedging_note": "Potentially relevant — requires verification by a legal practitioner.",
                }
                for r in state.rag_results
            ],
        },

        # Section 11: Questions for human legal practitioner
        "section_11_lawyer_questions": {
            "title": "Questions for a Human Legal Practitioner",
            "note": (
                "These questions are generated from identified gaps and contradictions. "
                "They are organisational prompts, not legal advice."
            ),
            "questions": _generate_lawyer_questions(state),
        },
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user_facts(state: CaseState) -> list[dict]:
    """Extract facts sourced from user_statement."""
    from schemas.case_schema import SourceType
    facts = []
    for ev in state.events:
        if ev.source.type == SourceType.USER_STATEMENT:
            facts.append({
                "fact": ev.description,
                "date": ev.date_parsed or ev.date_raw,
                "source": "User statement",
                "confidence": ev.confidence,
            })
    for c in state.claims:
        if c.source.type == SourceType.USER_STATEMENT:
            facts.append({
                "fact": c.description,
                "date": None,
                "source": "User statement",
                "confidence": c.confidence,
            })
    return facts


def _document_facts(state: CaseState) -> list[dict]:
    """Extract facts sourced from documents."""
    from schemas.case_schema import SourceType
    facts = []
    for ev in state.evidence:
        for fact in ev.extracted_facts:
            facts.append({
                "fact": fact,
                "source_document": ev.filename,
                "confidence": ev.confidence,
            })
    for ev in state.events:
        if ev.source.type == SourceType.DOCUMENT:
            facts.append({
                "fact": ev.description,
                "date": ev.date_parsed or ev.date_raw,
                "source_document": ev.source.reference,
                "confidence": ev.confidence,
            })
    return facts


def _generate_lawyer_questions(state: CaseState) -> list[str]:
    """
    Deterministically generate review questions for the lawyer from the case state.
    NOT an LLM call — derived purely from what's missing/contradictory.
    """
    questions = []

    # From missing information
    for mi in state.missing_information[:6]:
        questions.append(f"Can the client provide: {mi.description}?")

    # From low-confidence parties
    for p in state.parties:
        if p.confidence == ConfidenceLevel.LOW:
            questions.append(
                f"The identity/role of '{p.name}' as '{p.role}' is low-confidence — "
                f"can this be verified?"
            )

    # From contradictions
    for c in state.contradictions:
        questions.append(
            f"Potential {c.contradiction_type.replace('_', ' ')}: {c.description} — "
            f"which version is correct?"
        )

    # From critique findings
    for cf in state.critique_findings:
        if cf.finding_type == "unsupported_claim":
            questions.append(
                f"The following claim appears unsupported by available evidence: "
                f"{cf.description} — what evidence exists?"
            )

    # From low-quality evidence
    for ev in state.evidence:
        if ev.confidence == ConfidenceLevel.LOW or (ev.quality_score is not None and ev.quality_score < 50.0):
            score_str = f"{ev.quality_score:.0f}/100" if ev.quality_score is not None else "low confidence"
            questions.append(
                f"Evidence '{ev.filename}' scored low quality ({score_str}) — can clearer or authenticated proof be obtained?"
            )

    # Generic fallback if empty
    if not questions:
        questions.append(
            "Please review the chronology for completeness and verify all party identities."
        )

    return questions[:12]  # cap at 12 questions


def _deduplicate_parties(parties: list[Party]) -> list[Party]:
    """
    Deduplicate parties by normalizing honorifics (Mr., Ms., Mrs., Dr., Shri, Smt.) and whitespace/case.
    Merges contact info and prefers title-cased names.
    """
    import re
    seen: dict[str, Party] = {}
    for p in parties:
        # Strip honorifics and non-alphanumeric for matching key
        norm = re.sub(r'^(mr|ms|mrs|dr|shri|smt)\.?\s+', '', p.name.strip(), flags=re.IGNORECASE)
        norm = re.sub(r'\s+', ' ', norm).lower().strip()
        if not norm:
            norm = p.name.strip().lower()

        if norm in seen:
            existing = seen[norm]
            # Merge contact/address if missing
            if not existing.contact and p.contact:
                existing.contact = p.contact
            if not existing.address and p.address:
                existing.address = p.address
            if (not existing.role or existing.role.lower() == "unknown") and p.role:
                existing.role = p.role
            # If current existing is uppercase and incoming has Title Case, prefer Title Case
            if existing.name.isupper() and not p.name.isupper():
                existing.name = p.name
        else:
            seen[norm] = p.model_copy() if hasattr(p, "model_copy") else p

    return list(seen.values())
