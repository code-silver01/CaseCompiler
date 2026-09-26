"""
FastAPI routes for CaseCompiler.
All endpoints return JSON. File uploads are multipart/form-data.

Endpoints:
  POST   /api/session                  — create session
  GET    /api/session/{id}             — get current state
  DELETE /api/session/{id}             — delete session
  POST   /api/session/{id}/extract     — extract from description + files
  POST   /api/session/{id}/answer      — post interview answer
  GET    /api/session/{id}/compile     — compile final case file
  POST   /api/index-corpus             — rebuild FAISS index (admin)
  GET    /api/health                   — health check

FUTURE WORK: Add authentication middleware before any endpoint that
reads or writes case data (currently no auth — local demo only).
"""
from __future__ import annotations

import asyncio
import logging
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import JSONResponse

import config
from core.case_state import create_session, delete_session, get_session, save_session
from core.compiler import compile_case_file
from core.evidence_scorer import score_evidence_document
from core.extractor import describe_evidence, extract_case, self_critique
from core.interviewer import generate_next_question, process_answer
from core.pdf_generator import generate_case_pdf
from core.rag import build_index, generate_search_query, retrieve, run_rag
from core.triage import compute_triage

logger = logging.getLogger(__name__)
router = APIRouter()

_session_phases: dict[str, str] = {}


# ---------------------------------------------------------------------------
# Health & Status
# ---------------------------------------------------------------------------

@router.get("/health")
async def health():
    return {
        "status": "ok",
        "model": config.GEMINI_MODEL,
        "fallback_model": config.GEMINI_FALLBACK_MODEL,
    }


@router.get("/session/{session_id}/phase")
async def get_session_phase(session_id: str):
    """Return the active extraction phase for live stepper checklist."""
    return {"phase": _session_phases.get(session_id, "idle")}


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

@router.post("/session")
async def new_session():
    state = create_session()
    return {"session_id": state.session_id, "created_at": state.created_at}


@router.get("/session/{session_id}")
async def get_state(session_id: str):
    state = _require_session(session_id)
    return state.model_dump()


@router.delete("/session/{session_id}")
async def remove_session(session_id: str):
    ok = delete_session(session_id)
    if not ok:
        raise HTTPException(404, "Session not found")
    return {"deleted": True}


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

@router.post("/session/{session_id}/extract")
async def extract(
    session_id: str,
    description: str = Form(...),
    files: list[UploadFile] = File(default=[]),
):
    """
    Accept a free-text description and optional file uploads.
    Runs extraction, self-critique, RAG, and interview priming with optimized parallelism.
    Phase 1: extract_case and describe_evidence (for each file) run concurrently.
    Phase 2: self_critique, run_rag, and generate_next_question run concurrently.
    Returns the updated session state.
    """
    state = _require_session(session_id)

    # Save description
    state.original_description = description

    # Write uploads to a temp dir so we can pass paths to Gemini
    tmp_dir = Path(tempfile.mkdtemp())
    uploaded: list[tuple[Path, str]] = []
    try:
        for uf in files:
            if uf.filename:
                _validate_upload(uf)
                dest = tmp_dir / uf.filename
                with open(dest, "wb") as f:
                    shutil.copyfileobj(uf.file, f)
                uploaded.append((dest, uf.filename))
                state.uploaded_filenames.append(uf.filename)

        # -------------------------------------------------------------------
        # Phase 1: Parallel extraction & evidence description
        # extract_case and describe_evidence (for each file) are independent
        # and can execute concurrently via asyncio.gather.
        # -------------------------------------------------------------------
        _session_phases[session_id] = "extraction"
        logger.info(
            "[%s] Phase 1: Running parallel extraction and evidence processing on %d files",
            session_id,
            len(uploaded),
        )
        task_extract = asyncio.to_thread(extract_case, description, uploaded)
        task_evidence = [
            asyncio.to_thread(describe_evidence, file_path, orig_name)
            for file_path, orig_name in uploaded
        ]

        phase1_results = await asyncio.gather(task_extract, *task_evidence, return_exceptions=True)

        extracted_res = phase1_results[0]
        if isinstance(extracted_res, Exception):
            logger.error("[%s] Extraction failed: %s", session_id, extracted_res, exc_info=True)
            raise HTTPException(500, f"Extraction failed: {extracted_res}")
        extracted = extracted_res

        # Merge extracted entities into state
        state.parties.extend(extracted.get("parties", []))
        state.events.extend(extracted.get("events", []))
        state.claims.extend(extracted.get("claims", []))
        state.financials.extend(extracted.get("financials", []))
        state.contradictions.extend(extracted.get("contradictions", []))
        state.missing_information.extend(extracted.get("missing_information", []))

        # Merge evidence descriptions from Phase 1
        for i, ev_res in enumerate(phase1_results[1:]):
            orig_name = uploaded[i][1]
            if isinstance(ev_res, Exception):
                logger.warning("[%s] describe_evidence failed for %s: %s", session_id, orig_name, ev_res)
            else:
                state.evidence.append(ev_res)

        # Score evidence quality with trained XGBoost model (continuous 0-100 score)
        if state.evidence:
            all_doc_texts = [getattr(ev, "raw_text", "") or ev.description for ev in state.evidence]
            for ev in state.evidence:
                try:
                    score, conf, doc_type, signals = score_evidence_document(
                        filename=ev.filename,
                        text=getattr(ev, "raw_text", "") or ev.description,
                        file_type=ev.file_type,
                        state=state,
                        all_uploaded_texts=all_doc_texts,
                    )
                    ev.quality_score = score
                    ev.confidence = conf
                    ev.detected_type = doc_type
                    ev.feature_signals = signals
                    logger.info(
                        "[%s] ML Evidence Scorer for '%s': score=%.1f (%s), type=%s",
                        session_id,
                        ev.filename,
                        score,
                        conf.value,
                        doc_type,
                    )
                except Exception as e:
                    logger.warning("[%s] Evidence scoring failed for %s: %s", session_id, ev.filename, e)

        # Compute triage immediately (deterministic, instant)
        try:
            state.triage = compute_triage(state)
        except Exception as e:
            logger.warning("[%s] Triage failed (non-fatal): %s", session_id, e)

        state.extraction_done = True

        # -------------------------------------------------------------------
        # Phase 2: Parallel self-critique, RAG, and first interview question
        # self_critique needs `extracted`, RAG needs case facts, interview needs gaps.
        # None of these 3 depend on each other, so they execute in parallel!
        # -------------------------------------------------------------------
        _session_phases[session_id] = "self_critique"
        logger.info(
            "[%s] Phase 2: Running self-critique, RAG, and interview priming in parallel",
            session_id,
        )

        def _rag_with_phases(st: CaseState):
            _session_phases[session_id] = "rag_query"
            q = generate_search_query(st)
            _session_phases[session_id] = "retrieval"
            return retrieve(q, top_k=5)

        task_critique = asyncio.to_thread(
            self_critique, description, state.uploaded_filenames, extracted
        )
        task_rag = asyncio.to_thread(_rag_with_phases, state)
        task_question = asyncio.to_thread(generate_next_question, state)

        critique_res, rag_res, question_res = await asyncio.gather(
            task_critique, task_rag, task_question, return_exceptions=True
        )

        # Merge critique findings
        if isinstance(critique_res, Exception):
            logger.warning("[%s] Self-critique failed (non-fatal): %s", session_id, critique_res)
        else:
            state.critique_findings.extend(critique_res)

        # Merge RAG results
        if isinstance(rag_res, Exception) or not rag_res:
            logger.warning(
                "[%s] Initial RAG pass returned empty or failed: %s. Running fallback statutory retrieval.",
                session_id,
                rag_res,
            )
            try:
                state.rag_results = run_rag(state)
            except Exception as e:
                logger.error("[%s] Statutory RAG fallback failed: %s", session_id, e)
                state.rag_results = []
        else:
            state.rag_results = rag_res

        # Merge prime interview question
        if isinstance(question_res, Exception):
            logger.warning(
                "[%s] Interview question generation failed (non-fatal): %s", session_id, question_res
            )
            state.interview_complete = False
        else:
            question, complete = question_res
            state.current_question = question
            state.interview_complete = complete

        _session_phases[session_id] = "complete"

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    save_session(state)
    return state.model_dump()


# ---------------------------------------------------------------------------
# Interview
# ---------------------------------------------------------------------------

@router.post("/session/{session_id}/answer")
async def post_answer(session_id: str, body: dict):
    """
    Accept an answer to the current interview question.
    Updates case state and generates the next question.
    """
    state = _require_session(session_id)
    answer: str = body.get("answer", "").strip()
    if not answer:
        raise HTTPException(400, "Answer cannot be empty")

    if state.interview_complete:
        return {"message": "Interview already complete", "state": state.model_dump()}

    # Process the answer and merge new facts
    try:
        state = await asyncio.to_thread(process_answer, state, answer)
    except Exception as e:
        logger.error("[%s] process_answer failed: %s", session_id, e, exc_info=True)
        raise HTTPException(500, f"Failed to process answer: {e}")

    # Refresh triage after new facts
    try:
        state.triage = compute_triage(state)
    except Exception as e:
        logger.warning("[%s] Triage refresh failed: %s", session_id, e)

    # Generate next question
    try:
        question, complete = await asyncio.to_thread(generate_next_question, state)
        state.current_question = question
        state.interview_complete = complete
    except Exception as e:
        logger.warning("[%s] Next question generation failed: %s", session_id, e)
        complete = False

    # After 3 user responses, report is ready to compile at any time
    user_turns = len([m for m in state.interview_history if m.get("role") == "user"])
    state.compile_ready = complete or (user_turns >= 3)
    save_session(state)
    return state.model_dump()


# ---------------------------------------------------------------------------
# Compile
# ---------------------------------------------------------------------------

@router.get("/session/{session_id}/compile")
def compile_case(session_id: str):
    """
    Compile the final 11-section case file from the current session state.
    Can be called at any time — does not require interview completion.
    """
    state = _require_session(session_id)

    if not state.extraction_done:
        raise HTTPException(400, "Extraction has not been run yet. POST to /extract first.")

    # Refresh triage
    try:
        state.triage = compute_triage(state)
    except Exception as e:
        logger.warning("[%s] Triage refresh failed: %s", session_id, e)

    # Ensure statutory RAG results are present before compiling
    if not state.rag_results:
        try:
            logger.info("[%s] No prior RAG results found; running statutory retrieval...", session_id)
            state.rag_results = run_rag(state)
            logger.info("[%s] Retrieved %d statutory RAG results.", session_id, len(state.rag_results))
        except Exception as e:
            logger.warning("[%s] Statutory RAG retrieval during compile failed: %s", session_id, e)

    save_session(state)

    try:
        case_file = compile_case_file(state)
    except Exception as e:
        logger.error("[%s] Compile failed: %s", session_id, e, exc_info=True)
        raise HTTPException(500, f"Compile failed: {e}")
    return case_file


@router.get("/session/{session_id}/pdf")
def export_pdf(session_id: str):
    """
    Compile and export the final 11-section case file as a downloadable PDF document.
    """
    state = _require_session(session_id)

    if not state.extraction_done:
        raise HTTPException(400, "Extraction has not been run yet. POST to /extract first.")

    # Refresh triage
    try:
        state.triage = compute_triage(state)
    except Exception as e:
        logger.warning("[%s] Triage refresh failed: %s", session_id, e)

    # Ensure statutory RAG results are present before generating PDF
    if not state.rag_results:
        try:
            logger.info("[%s] No prior RAG results found; running statutory retrieval for PDF...", session_id)
            state.rag_results = run_rag(state)
        except Exception as e:
            logger.warning("[%s] Statutory RAG retrieval during pdf compile failed: %s", session_id, e)

    save_session(state)

    try:
        case_file = compile_case_file(state)
        pdf_bytes = generate_case_pdf(case_file)
    except Exception as e:
        logger.error("[%s] PDF generation failed: %s", session_id, e, exc_info=True)
        raise HTTPException(500, f"PDF generation failed: {e}")

    filename = f"case-file-{session_id[:8]}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


# ---------------------------------------------------------------------------
# Corpus indexing (admin)
# ---------------------------------------------------------------------------

@router.post("/index-corpus")
def index_corpus(force_rebuild: bool = False):
    """
    Trigger a rebuild of the FAISS index from the corpus/ directory.
    Call this after dropping new .txt files into corpus/.
    """
    try:
        count = build_index(force_rebuild=force_rebuild)
        return {
            "status": "ok",
            "chunks_indexed": count,
            "corpus_dir": str(config.CORPUS_DIR),
        }
    except Exception as e:
        logger.error("Index build failed: %s", e)
        raise HTTPException(500, f"Index build failed: {e}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_session(session_id: str):
    state = get_session(session_id)
    if not state:
        raise HTTPException(404, f"Session '{session_id}' not found or expired.")
    return state


def _validate_upload(upload: UploadFile) -> None:
    allowed = {".pdf", ".txt", ".jpg", ".jpeg", ".png", ".webp", ".gif", ".md"}
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in allowed:
        raise HTTPException(
            400,
            f"File type '{suffix}' not supported. Allowed: {', '.join(sorted(allowed))}",
        )
    # Size check is done at the FastAPI app level via max_upload_size middleware
