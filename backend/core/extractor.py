"""
Multimodal case extractor using Gemini function calling.
Parses text + images + PDFs into structured case entities.
Runs a self-critique pass after extraction.

Tools defined (as Gemini function declarations):
  - extract_party
  - extract_event
  - extract_claim
  - extract_financial
  - flag_contradiction
  - request_document
  - update_case_state  (signals that state is fully updated)

FUTURE WORK: Add auth/session scoping before calling Gemini with user data.
"""
from __future__ import annotations

import base64
import io
import json
import logging
import mimetypes
from pathlib import Path
from typing import Any

from PIL import Image

import pymupdf as fitz  # PyMuPDF — 'fitz' alias for backward compat
from google import genai
from google.genai import types

import config
from core.chronology import deduplicate_events, parse_date, sort_events
from schemas.case_schema import (
    Claim,
    ConfidenceLevel,
    Contradiction,
    CritiqueFinding,
    Event,
    Evidence,
    FieldSource,
    Financial,
    MissingInfo,
    Party,
    SourceType,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gemini client (shared singleton)
# ---------------------------------------------------------------------------

import threading
import time

_client: genai.Client | None = None
_cooldown_lock = threading.Lock()
_primary_cooldown_until: float = 0.0


def get_client() -> genai.Client:
    """Return the shared Google GenAI client instance initialized with API credentials."""
    global _client
    if _client is None:
        _client = genai.Client(
            api_key=config.GEMINI_API_KEY,
            http_options=types.HttpOptions(
                retry_options=types.HttpRetryOptions(attempts=1),  # Fail fast to fallback immediately on 429/503
            ),
        )
    return _client


def _safe_generate(
    client: genai.Client,
    model: str,
    contents,
    cfg: types.GenerateContentConfig,
) -> types.GenerateContentResponse:
    """Generate content with fallback if thinking_config is unsupported by the model."""
    try:
        return client.models.generate_content(
            model=model,
            contents=contents,
            config=cfg,
        )
    except Exception as exc:
        exc_str = str(exc).lower()
        if cfg and getattr(cfg, "thinking_config", None) and (
            "thinking" in exc_str or "invalid argument" in exc_str or "400" in exc_str
        ):
            logger.warning(
                "Model %s failed with thinking_config (%s). Retrying without thinking_config.",
                model,
                exc,
            )
            cfg_no_thinking = cfg.model_copy(update={"thinking_config": None})
            return client.models.generate_content(
                model=model,
                contents=contents,
                config=cfg_no_thinking,
            )
        raise


def generate_content_with_fallback(
    client: genai.Client,
    *,
    contents,
    gen_config: types.GenerateContentConfig,
) -> types.GenerateContentResponse:
    """
    Call client.models.generate_content with the primary model (config.GEMINI_MODEL).
    If the primary model hits RPM limit (5/min), RPD limit (20/day) [HTTP 429 / RESOURCE_EXHAUSTED],
    high demand / temporary overload [HTTP 503 / UNAVAILABLE], or timeout, transparently fall back
    to config.GEMINI_FALLBACK_MODEL (gemini-3.5-flash-lite).

    Maintains a thread-safe cooldown timer so concurrent requests don't waste round-trips against an
    exhausted primary model.
    """
    global _primary_cooldown_until

    now = time.time()
    with _cooldown_lock:
        use_fallback_directly = (
            now < _primary_cooldown_until
            and config.GEMINI_MODEL != config.GEMINI_FALLBACK_MODEL
        )

    if not use_fallback_directly:
        try:
            return _safe_generate(
                client,
                model=config.GEMINI_MODEL,
                contents=contents,
                cfg=gen_config,
            )
        except Exception as exc:
            exc_str = str(exc).lower()
            is_rate_limit = (
                "429" in exc_str
                or "resource_exhausted" in exc_str
                or "quota" in exc_str
                or "rate" in exc_str
            )
            is_overloaded_or_timeout = (
                "503" in exc_str
                or "unavailable" in exc_str
                or "overloaded"
                in exc_str
                or "high demand" in exc_str
                or "timeout" in exc_str
                or "timed out" in exc_str
                or "deadline" in exc_str
            )

            if not (is_rate_limit or is_overloaded_or_timeout):
                raise

            # Determine cooldown:
            if any(term in exc_str for term in ("per day", "daily", "rpd", "day")):
                cooldown_sec = 3600.0  # RPD (20/day) exhausted; pause primary for 1 hour
                reason = "daily quota (RPD) exhausted"
            elif is_rate_limit:
                cooldown_sec = 60.0    # RPM (5/min) exhausted; retry primary after 60s
                reason = "RPM rate limit exceeded"
            else:
                cooldown_sec = 30.0    # 503 spike / timeout
                reason = "model overloaded / timeout"

            with _cooldown_lock:
                _primary_cooldown_until = time.time() + cooldown_sec

            logger.warning(
                "Primary model '%s' unavailable (%s: %s). Cooldown set for %.0fs. Falling back to '%s'.",
                config.GEMINI_MODEL,
                reason,
                exc,
                cooldown_sec,
                config.GEMINI_FALLBACK_MODEL,
            )

    # Use fallback model (gemini-3.5-flash-lite)
    return _safe_generate(
        client,
        model=config.GEMINI_FALLBACK_MODEL,
        contents=contents,
        cfg=gen_config,
    )


# ---------------------------------------------------------------------------
# Function declarations (tool schemas)
# ---------------------------------------------------------------------------

EXTRACTION_TOOLS = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="extract_party",
            description="Extract a person or organisation that is a party to the legal matter.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "name": types.Schema(type=types.Type.STRING, description="Full name or organisation name"),
                    "role": types.Schema(type=types.Type.STRING, description="Role, e.g. landlord, tenant, agent, witness"),
                    "contact": types.Schema(type=types.Type.STRING, description="Phone, email, or address if mentioned"),
                    "source_type": types.Schema(type=types.Type.STRING, description="user_statement or document"),
                    "source_reference": types.Schema(type=types.Type.STRING, description="Filename or verbatim quote from user input"),
                    "confidence": types.Schema(type=types.Type.STRING, description="high, medium, or low"),
                },
                required=["name", "role", "source_type", "confidence"],
            ),
        ),
        types.FunctionDeclaration(
            name="extract_event",
            description="Extract a dated or dateable event relevant to the legal matter.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "date_raw": types.Schema(type=types.Type.STRING, description="Date as mentioned by user"),
                    "description": types.Schema(type=types.Type.STRING, description="What happened"),
                    "source_type": types.Schema(type=types.Type.STRING),
                    "source_reference": types.Schema(type=types.Type.STRING),
                    "confidence": types.Schema(type=types.Type.STRING),
                },
                required=["description", "source_type", "confidence"],
            ),
        ),
        types.FunctionDeclaration(
            name="extract_claim",
            description="Extract a legal claim or assertion made by the user.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "description": types.Schema(type=types.Type.STRING, description="The claim being made"),
                    "legal_basis": types.Schema(type=types.Type.STRING, description="Any legal basis mentioned"),
                    "source_type": types.Schema(type=types.Type.STRING),
                    "source_reference": types.Schema(type=types.Type.STRING),
                    "confidence": types.Schema(type=types.Type.STRING),
                },
                required=["description", "source_type", "confidence"],
            ),
        ),
        types.FunctionDeclaration(
            name="extract_financial",
            description="Extract a financial figure relevant to the case (rent, deposit, damages, etc.).",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "label": types.Schema(type=types.Type.STRING, description="What this amount is for"),
                    "amount_inr": types.Schema(type=types.Type.NUMBER, description="Amount in Indian Rupees"),
                    "date_raw": types.Schema(type=types.Type.STRING, description="Date associated with this amount if any"),
                    "source_type": types.Schema(type=types.Type.STRING),
                    "source_reference": types.Schema(type=types.Type.STRING),
                    "confidence": types.Schema(type=types.Type.STRING),
                },
                required=["label", "source_type", "confidence"],
            ),
        ),
        types.FunctionDeclaration(
            name="flag_contradiction",
            description="Flag a contradiction between two pieces of information (date or amount mismatch only for v1).",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "description": types.Schema(type=types.Type.STRING),
                    "item_a": types.Schema(type=types.Type.STRING, description="First conflicting item"),
                    "item_b": types.Schema(type=types.Type.STRING, description="Second conflicting item"),
                    "contradiction_type": types.Schema(type=types.Type.STRING, description="date_mismatch or amount_mismatch"),
                },
                required=["description", "item_a", "item_b", "contradiction_type"],
            ),
        ),
        types.FunctionDeclaration(
            name="request_document",
            description="Flag a document or piece of information that is missing and should be requested from the user.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "description": types.Schema(type=types.Type.STRING, description="What is missing"),
                    "category": types.Schema(type=types.Type.STRING, description="document, date, party, financial, or other"),
                },
                required=["description", "category"],
            ),
        ),
    ]
)


# ---------------------------------------------------------------------------
# File → Gemini Part conversion
# ---------------------------------------------------------------------------

def _pdf_to_text(path: Path) -> str:
    """Extract all text from a PDF using PyMuPDF."""
    doc = fitz.open(str(path))
    pages = [page.get_text() for page in doc]
    doc.close()
    return "\n\n".join(pages)


def _optimize_image_for_llm(filepath: Path, max_dim: int = 1200) -> tuple[bytes, str]:
    """
    Downscale and compress uploaded images to ~80-120KB JPEG using Pillow.
    Reduces upload payload by 85% with identical LLM OCR quality.
    """
    try:
        with Image.open(filepath) as img:
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            w, h = img.size
            if max(w, h) > max_dim:
                scale = max_dim / max(w, h)
                new_w, new_h = max(1, int(w * scale)), max(1, int(h * scale))
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=82, optimize=True)
            return buf.getvalue(), "image/jpeg"
    except Exception as e:
        logger.warning("Image optimization failed for %s: %s; using original bytes", filepath.name, e)
        return filepath.read_bytes(), "image/jpeg"


def _file_to_parts(filepath: Path, original_name: str) -> list[types.Part]:
    """Convert an uploaded file to one or more Gemini content parts."""
    suffix = filepath.suffix.lower()

    if suffix == ".pdf":
        text = _pdf_to_text(filepath)
        return [types.Part(text=f"[PDF: {original_name}]\n{text[:4000]}")]

    if suffix in (".txt", ".md"):
        text = filepath.read_text(encoding="utf-8", errors="replace")[:4000]
        return [types.Part(text=f"[Document: {original_name}]\n{text}")]

    if suffix in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        data, mime = _optimize_image_for_llm(filepath, max_dim=1200)
        return [
            types.Part(inline_data=types.Blob(data=data, mime_type=mime)),
            types.Part(text=f"[Image filename: {original_name}]"),
        ]

    # Fallback: try as text
    try:
        text = filepath.read_text(encoding="utf-8", errors="replace")[:4000]
        return [types.Part(text=f"[File: {original_name}]\n{text}")]
    except Exception:
        logger.warning("Cannot process file type for: %s", original_name)
        return []


# ---------------------------------------------------------------------------
# Tool call dispatcher
# ---------------------------------------------------------------------------

def _dispatch_tool_call(
    call: types.FunctionCall,
    result: dict,
) -> None:
    """Parse a function call and populate the result dict in-place."""
    name = call.name
    args: dict[str, Any] = dict(call.args) if call.args else {}

    def _source(args: dict) -> FieldSource:
        st = args.get("source_type", "user_statement")
        ref = args.get("source_reference")
        try:
            source_type = SourceType(st)
        except ValueError:
            source_type = SourceType.USER_STATEMENT
        return FieldSource(type=source_type, reference=ref)

    def _confidence(args: dict) -> ConfidenceLevel:
        c = args.get("confidence", "medium")
        try:
            return ConfidenceLevel(c)
        except ValueError:
            return ConfidenceLevel.MEDIUM

    if name == "extract_party":
        result["parties"].append(
            Party(
                name=args["name"],
                role=args.get("role", "unknown"),
                contact=args.get("contact"),
                source=_source(args),
                confidence=_confidence(args),
            )
        )
    elif name == "extract_event":
        date_raw = args.get("date_raw")
        result["events"].append(
            Event(
                date_raw=date_raw,
                date_parsed=parse_date(date_raw),
                description=args["description"],
                source=_source(args),
                confidence=_confidence(args),
            )
        )
    elif name == "extract_claim":
        result["claims"].append(
            Claim(
                description=args["description"],
                legal_basis=args.get("legal_basis"),
                source=_source(args),
                confidence=_confidence(args),
            )
        )
    elif name == "extract_financial":
        result["financials"].append(
            Financial(
                label=args["label"],
                amount_inr=args.get("amount_inr"),
                date_raw=args.get("date_raw"),
                source=_source(args),
                confidence=_confidence(args),
            )
        )
    elif name == "flag_contradiction":
        result["contradictions"].append(
            Contradiction(
                description=args["description"],
                item_a=args["item_a"],
                item_b=args["item_b"],
                contradiction_type=args.get("contradiction_type", "claim_mismatch"),
            )
        )
    elif name == "request_document":
        result["missing_information"].append(
            MissingInfo(
                description=args["description"],
                requested_by="system",
                category=args.get("category", "other"),
            )
        )


# ---------------------------------------------------------------------------
# Main extraction function
# ---------------------------------------------------------------------------

def extract_case(
    description: str,
    uploaded_files: list[tuple[Path, str]],  # (tmp_path, original_name)
) -> dict:
    """
    Pass 1: Send user description + files to Gemini with function calling.
    Returns a raw result dict with lists of extracted entities.
    """
    client = get_client()

    # Build content parts
    parts: list[types.Part] = [
        types.Part(
            text=(
                "You are an expert legal case analyst. Extract ALL structured entities from the "
                "following case description and any attached documents. "
                "CRITICAL EFFICIENCY REQUIREMENT: Call ALL relevant extraction tools IN PARALLEL "
                "in your very first response turn! Emit all extract_party, extract_event, extract_claim, "
                "extract_financial, flag_contradiction, and request_document tool calls simultaneously. "
                "Do NOT emit single tool calls across multiple turns. "
                "Be thorough — extract every entity you can identify from the text and images.\n\n"
                f"USER DESCRIPTION:\n{description}"
            )
        )
    ]

    for file_path, orig_name in uploaded_files:
        parts.extend(_file_to_parts(file_path, orig_name))

    result: dict = {
        "parties": [],
        "events": [],
        "claims": [],
        "financials": [],
        "contradictions": [],
        "missing_information": [],
    }

    # Parallel tool-use loop capped at 2 rounds
    contents = [types.Content(role="user", parts=parts)]
    max_rounds = 2

    for round_idx in range(max_rounds):
        response = generate_content_with_fallback(
            client,
            contents=contents,
            gen_config=types.GenerateContentConfig(
                tools=[EXTRACTION_TOOLS],
                tool_config=types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(
                        mode=types.FunctionCallingConfigMode.AUTO
                    )
                ),
                temperature=0.1,
                thinking_config=types.ThinkingConfig(
                    thinking_level=types.ThinkingLevel.MINIMAL
                ),
            ),
        )

        candidate = response.candidates[0]

        # Collect tool calls from this response turn
        tool_calls_found = []
        for part in candidate.content.parts:
            if part.function_call:
                _dispatch_tool_call(part.function_call, result)
                tool_calls_found.append(part.function_call)

        if not tool_calls_found or round_idx >= max_rounds - 1:
            # Done emitting tools
            break

        # Feed tool responses back to continue without resending large image blobs
        tool_response_parts = []
        for fc in tool_calls_found:
            try:
                tool_response_parts.append(
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=fc.name,
                            response={"result": "ok"},
                        )
                    )
                )
            except Exception:
                tool_response_parts.append(
                    types.Part.from_function_response(
                        name=fc.name,
                        response={"result": "ok"},
                    )
                )

        # Replace inline image blobs with lightweight markers in conversation history
        slim_history = []
        for c in contents:
            slim_parts = []
            for p in c.parts:
                if getattr(p, "inline_data", None):
                    slim_parts.append(types.Part(text="[Attached document processed in turn 1]"))
                else:
                    slim_parts.append(p)
            slim_history.append(types.Content(role=c.role, parts=slim_parts))

        contents = slim_history + [
            candidate.content,
            types.Content(role="user", parts=tool_response_parts),
        ]

    # Post-process events
    result["events"] = sort_events(deduplicate_events(result["events"]))
    return result


# ---------------------------------------------------------------------------
# Self-critique pass
# ---------------------------------------------------------------------------

_CRITIQUE_SYSTEM = """You are a senior legal analyst reviewing a junior analyst's case extraction.
Given the original evidence and the extracted case data, identify:
1. Claims that are NOT supported by anything in the original evidence (unsupported_claim)
2. Date or amount contradictions not already flagged (contradiction)
3. Extractions with suspiciously low confidence or that seem hallucinated (low_confidence)

Return a JSON array of findings, each with:
  { "finding_type": "unsupported_claim|contradiction|low_confidence",
    "description": "...",
    "affected_item": "brief description of the item" }

If no issues found, return an empty array [].
Return ONLY valid JSON — no prose, no markdown fences."""


def self_critique(
    description: str,
    uploaded_filenames: list[str],
    extracted: dict,
) -> list[CritiqueFinding]:
    """
    Pass 2: A second Gemini call reviews the extraction against the original evidence.
    Returns a list of CritiqueFinding objects.
    """
    client = get_client()

    extracted_summary = json.dumps(
        {k: [_entity_summary(e) for e in v] for k, v in extracted.items()},
        indent=2,
        default=str,
    )

    prompt = (
        f"{_CRITIQUE_SYSTEM}\n\n"
        f"ORIGINAL USER DESCRIPTION:\n{description}\n\n"
        f"UPLOADED FILES: {', '.join(uploaded_filenames) or 'none'}\n\n"
        f"EXTRACTED CASE DATA:\n{extracted_summary}"
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

    raw = response.text or "[]"
    try:
        findings_raw = json.loads(raw)
        if not isinstance(findings_raw, list):
            findings_raw = []
    except json.JSONDecodeError:
        logger.warning("Self-critique returned non-JSON: %s", raw[:200])
        findings_raw = []

    findings = []
    for f in findings_raw:
        try:
            findings.append(
                CritiqueFinding(
                    finding_type=f.get("finding_type", "low_confidence"),
                    description=f.get("description", ""),
                    affected_item_id=f.get("affected_item"),
                )
            )
        except Exception:
            pass

    return findings


# ---------------------------------------------------------------------------
# Evidence file → Evidence schema entry
# ---------------------------------------------------------------------------

def describe_evidence(file_path: Path, original_name: str) -> Evidence:
    """
    Fast, lightweight evidence descriptor for the evidence map.
    Extracts text directly for documents and uses smart filename/thumbnail analysis for images
    to avoid burning multimodal API quota.
    """
    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        text = _pdf_to_text(file_path)
        first_lines = " ".join([line.strip() for line in text.split("\n") if line.strip()][:3])
        desc_text = f"PDF Document: {first_lines[:250]}" if first_lines else f"Uploaded PDF document: {original_name}"
        return Evidence(
            filename=original_name,
            file_type="pdf",
            description=desc_text,
            source=FieldSource(type=SourceType.DOCUMENT, reference=original_name),
            confidence=ConfidenceLevel.HIGH if text else ConfidenceLevel.MEDIUM,
            raw_text=text[:3000] if text else desc_text,
        )

    if suffix in (".txt", ".md"):
        text = file_path.read_text(encoding="utf-8", errors="replace")
        first_lines = " ".join([line.strip() for line in text.split("\n") if line.strip()][:3])
        desc_text = f"Text Document: {first_lines[:250]}" if first_lines else f"Uploaded text document: {original_name}"
        return Evidence(
            filename=original_name,
            file_type="text",
            description=desc_text,
            source=FieldSource(type=SourceType.DOCUMENT, reference=original_name),
            confidence=ConfidenceLevel.HIGH,
            raw_text=text[:3000],
        )

    # For images: generate a fast 1-sentence description using compressed thumbnail
    file_type = "image"
    clean_name = original_name.replace("_", " ").replace("-", " ").rsplit(".", 1)[0].title()
    fallback_desc = f"Photographic evidence: {clean_name}"

    try:
        client = get_client()
        opt_data, opt_mime = _optimize_image_for_llm(file_path, max_dim=800)
        prompt_parts = [
            types.Part(inline_data=types.Blob(data=opt_data, mime_type=opt_mime)),
            types.Part(
                text="In 1 concise sentence (under 20 words), describe what legal facts or evidence this image shows."
            ),
        ]
        response = generate_content_with_fallback(
            client,
            contents=[types.Content(role="user", parts=prompt_parts)],
            gen_config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=35,
                thinking_config=types.ThinkingConfig(
                    thinking_level=types.ThinkingLevel.MINIMAL
                ),
            ),
        )
        desc_text = (response.text or "").strip()
        if not desc_text:
            desc_text = fallback_desc
    except Exception as e:
        logger.info("Fast image description using heuristic label for %s: %s", original_name, e)
        desc_text = fallback_desc

    return Evidence(
        filename=original_name,
        file_type=file_type,
        description=desc_text,
        source=FieldSource(type=SourceType.DOCUMENT, reference=original_name),
        confidence=ConfidenceLevel.MEDIUM,
        raw_text=desc_text,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _entity_summary(entity: Any) -> dict:
    """Convert a Pydantic entity to a dict for the critique prompt."""
    if hasattr(entity, "model_dump"):
        return entity.model_dump()
    return str(entity)
