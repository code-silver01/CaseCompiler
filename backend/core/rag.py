"""
RAG module: FAISS vector store + Gemini Embeddings.
Indexes the /corpus directory at startup.
Retrieves relevant legal passages given a Gemini-generated search query.

All retrieved passages are hedged as "potentially relevant" — never legal fact.

FUTURE WORK: Add chunk-level metadata (section, act name, section number).
"""
from __future__ import annotations

import hashlib
import json
import logging
import pickle
from pathlib import Path
from typing import Optional

import numpy as np
import faiss
from google import genai
from google.genai import types

import config
from core.extractor import get_client, generate_content_with_fallback
from schemas.case_schema import CaseState, RAGResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FAISS index state (in-process singleton)
# ---------------------------------------------------------------------------

_index: Optional[faiss.IndexFlatIP] = None  # Inner Product (cosine after normalise)
_chunks: list[dict] = []  # [{"text": ..., "source_file": ..., "chunk_id": ...}]


def _embed_text(text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> np.ndarray:
    """Embed a single string using Gemini Embeddings. Returns normalised float32 array."""
    client = get_client()
    response = client.models.embed_content(
        model=config.GEMINI_EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(task_type=task_type),
    )
    vec = np.array(response.embeddings[0].values, dtype=np.float32)
    # L2-normalise so inner product == cosine similarity
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec


def _chunk_text(text: str, chunk_size: int = 600, overlap: int = 100) -> list[str]:
    """
    Split text into overlapping chunks by character count.
    Simple but effective for small corpora.
    """
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end].strip())
        start += chunk_size - overlap
    return [c for c in chunks if len(c) > 50]  # drop very short chunks


def compute_corpus_hash() -> str:
    """
    Compute a SHA-256 hash over all .txt files in the corpus directory,
    including filenames, sizes, modification times, and content.
    Returns an empty string if corpus is empty.
    """
    corpus_files = sorted(config.CORPUS_DIR.glob("*.txt"))
    if not corpus_files:
        return ""

    hasher = hashlib.sha256()
    for path in corpus_files:
        try:
            stat = path.stat()
            hasher.update(f"{path.name}:{stat.st_size}:{stat.st_mtime_ns}\n".encode("utf-8"))
            hasher.update(path.read_bytes())
        except Exception as e:
            logger.warning("Error reading %s for corpus hash: %s", path.name, e)
    return hasher.hexdigest()


# ---------------------------------------------------------------------------
# Index building
# ---------------------------------------------------------------------------

def build_index(force_rebuild: bool = False) -> int:
    """
    Read all .txt files from corpus/, embed them, and build a FAISS index.
    Compares a SHA-256 hash of the corpus directory against a stored hash
    from when the index was last built. If they differ or the hash file is missing,
    automatically rebuilds the index instead of loading a stale cache.
    Persists the index, chunk metadata, and corpus hash to FAISS_INDEX_PATH.
    Returns the number of chunks indexed.
    """
    global _index, _chunks

    index_file = config.FAISS_INDEX_PATH.with_suffix(".bin")
    meta_file = config.FAISS_INDEX_PATH.with_suffix(".pkl")
    hash_file = config.FAISS_INDEX_PATH.with_suffix(".hash")
    config.FAISS_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)

    current_hash = compute_corpus_hash()

    if not force_rebuild and index_file.exists() and meta_file.exists() and hash_file.exists():
        stored_hash = hash_file.read_text(encoding="utf-8").strip()
        if stored_hash == current_hash:
            logger.info("Corpus hash matches cache (%s). Loading FAISS index from %s", current_hash[:8] if current_hash else "empty", index_file)
            _index = faiss.read_index(str(index_file))
            with open(meta_file, "rb") as f:
                _chunks = pickle.load(f)
            logger.info("Loaded %d chunks from cache.", len(_chunks))
            return len(_chunks)
        else:
            logger.info(
                "Corpus directory changed (stored hash '%s' != current hash '%s'). Auto-rebuilding FAISS index...",
                stored_hash[:8] if stored_hash else "none",
                current_hash[:8] if current_hash else "none",
            )
    elif not force_rebuild and index_file.exists() and meta_file.exists() and not hash_file.exists():
        logger.info("No corpus hash file found alongside cached index. Auto-rebuilding to ensure fresh index...")

    corpus_files = list(config.CORPUS_DIR.glob("*.txt"))
    if not corpus_files:
        logger.warning(
            "Corpus directory '%s' is empty. RAG will return no results. "
            "Drop .txt files into the corpus/ directory and call POST /index-corpus.",
            config.CORPUS_DIR,
        )
        # Build an empty index so the app doesn't crash
        _index = faiss.IndexFlatIP(config.EMBEDDING_DIM)
        _chunks = []
        hash_file.write_text(current_hash, encoding="utf-8")
        return 0

    all_chunks: list[dict] = []
    all_vectors: list[np.ndarray] = []

    for corpus_file in sorted(corpus_files):
        text = corpus_file.read_text(encoding="utf-8", errors="replace")
        file_chunks = _chunk_text(text)
        logger.info("Indexing %s — %d chunks", corpus_file.name, len(file_chunks))

        for i, chunk in enumerate(file_chunks):
            try:
                vec = _embed_text(chunk, task_type="RETRIEVAL_DOCUMENT")
                all_chunks.append({
                    "text": chunk,
                    "source_file": corpus_file.name,
                    "chunk_id": f"{corpus_file.stem}_{i}",
                })
                all_vectors.append(vec)
            except Exception as e:
                logger.warning("Failed to embed chunk %d from %s: %s", i, corpus_file.name, e)

    if not all_vectors:
        _index = faiss.IndexFlatIP(config.EMBEDDING_DIM)
        _chunks = []
        hash_file.write_text(current_hash, encoding="utf-8")
        return 0

    matrix = np.stack(all_vectors, axis=0)
    dim = matrix.shape[1]
    _index = faiss.IndexFlatIP(dim)
    _index.add(matrix)
    _chunks = all_chunks

    # Persist
    faiss.write_index(_index, str(index_file))
    with open(meta_file, "wb") as f:
        pickle.dump(_chunks, f)
    hash_file.write_text(current_hash, encoding="utf-8")

    logger.info("Built FAISS index with %d chunks (dim=%d, hash=%s)", len(_chunks), dim, current_hash[:8] if current_hash else "none")
    return len(_chunks)


# ---------------------------------------------------------------------------
# Lazy index loader & lexical fallback
# ---------------------------------------------------------------------------

def ensure_index_loaded() -> bool:
    """
    Ensure the FAISS index and chunk metadata are loaded in memory.
    If not loaded, attempts to read from existing disk cache files (.bin and .pkl).
    If cache is missing, attempts build_index().
    """
    global _index, _chunks
    if _index is not None and len(_chunks) > 0 and _index.ntotal > 0:
        return True

    index_file = config.FAISS_INDEX_PATH.with_suffix(".bin")
    meta_file = config.FAISS_INDEX_PATH.with_suffix(".pkl")
    if index_file.exists() and meta_file.exists():
        try:
            logger.info("Auto-loading FAISS index from disk cache %s", index_file)
            _index = faiss.read_index(str(index_file))
            with open(meta_file, "rb") as f:
                _chunks = pickle.load(f)
            logger.info("Auto-loaded %d chunks from cache into memory.", len(_chunks))
            return len(_chunks) > 0
        except Exception as e:
            logger.warning("Failed to auto-load cached FAISS index: %s", e)

    # Fall back to build_index
    try:
        count = build_index(force_rebuild=False)
        return count > 0
    except Exception as e:
        logger.error("Failed to build index in ensure_index_loaded: %s", e)
        return False


def retrieve_lexical(query: str, top_k: int = 5) -> list[RAGResult]:
    """
    Local TF-IDF / keyword similarity retriever across corpus chunks.
    Acts as a resilient fallback when Gemini Embeddings API is throttled (429),
    out of daily quota, or temporarily unavailable.
    """
    global _chunks
    ensure_index_loaded()

    if not _chunks:
        # Emergency fallback: read directly from corpus directory if chunks are empty
        corpus_files = sorted(config.CORPUS_DIR.glob("*.txt"))
        fallback_chunks = []
        for cf in corpus_files:
            try:
                txt = cf.read_text(encoding="utf-8", errors="replace")
                for i, c in enumerate(_chunk_text(txt)):
                    fallback_chunks.append({
                        "text": c,
                        "source_file": cf.name,
                        "chunk_id": f"{cf.stem}_{i}",
                    })
            except Exception:
                pass
        _chunks = fallback_chunks

    if not _chunks:
        logger.warning("No corpus chunks available for lexical retrieval.")
        return []

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        corpus_texts = [c["text"] for c in _chunks]
        vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        tfidf_matrix = vectorizer.fit_transform(corpus_texts)
        q_vec = vectorizer.transform([query])
        sims = cosine_similarity(q_vec, tfidf_matrix)[0]

        top_indices = np.argsort(sims)[::-1][:top_k]
        results = []
        for idx in top_indices:
            score = float(sims[idx])
            # Scale raw TF-IDF score into intuitive relevance score (0.55 - 0.88)
            scaled_score = max(0.55, min(0.88, 0.50 + score * 0.75)) if score > 0 else 0.52
            chunk = _chunks[idx]
            results.append(
                RAGResult(
                    query=query,
                    source_file=chunk["source_file"],
                    excerpt=chunk["text"][:800],
                    relevance_score=round(scaled_score, 4),
                    legal_area="Karnataka Tenancy Law",
                )
            )
        return results
    except Exception as e:
        logger.warning("TF-IDF retrieval fallback encountered an issue (%s); using token overlap.", e)
        q_words = set(query.lower().split())
        scored = []
        for chunk in _chunks:
            text_lower = chunk["text"].lower()
            overlap = sum(1 for w in q_words if w in text_lower)
            scored.append((overlap, chunk))
        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for overlap, chunk in scored[:top_k]:
            results.append(
                RAGResult(
                    query=query,
                    source_file=chunk["source_file"],
                    excerpt=chunk["text"][:800],
                    relevance_score=0.68 if overlap > 0 else 0.50,
                    legal_area="Karnataka Tenancy Law",
                )
            )
        return results


# ---------------------------------------------------------------------------
# Query generation (Gemini generates the legal search query)
# ---------------------------------------------------------------------------

_QUERY_PROMPT = """You are a legal research assistant. 
Given the following case summary, generate ONE precise legal search query 
to find the most relevant Karnataka tenancy statute sections or procedures.
The query should name specific legal concepts (e.g. "security deposit deduction rules Karnataka Rent Control Act").
Return ONLY the search query string — no explanation, no quotes."""


def generate_rag_query(state: CaseState) -> str:
    """
    Gemini generates the search query from the current case state.
    Falls back to a tailored dynamic query if generation fails or is throttled.
    """
    client = get_client()

    # Build a concise case summary for query generation
    parties_str = ", ".join(f"{p.name} ({p.role})" for p in state.parties[:4])
    claims_str = " | ".join(c.description[:100] for c in state.claims[:3])
    events_str = " | ".join(
        f"{e.date_parsed or e.date_raw or 'unknown date'}: {e.description[:80]}"
        for e in state.events[:5]
    )

    case_summary = (
        f"Parties: {parties_str or 'unknown'}\n"
        f"Claims: {claims_str or 'none identified'}\n"
        f"Key events: {events_str or 'none identified'}\n"
        f"Original description snippet: {state.original_description[:500]}"
    )

    prompt = f"{_QUERY_PROMPT}\n\nCASE SUMMARY:\n{case_summary}"

    try:
        response = generate_content_with_fallback(
            client,
            contents=prompt,
            gen_config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=80,
                thinking_config=types.ThinkingConfig(
                    thinking_level=types.ThinkingLevel.MINIMAL
                ),
            ),
        )
        query = (response.text or "").strip().strip('"').strip("'")
        if query:
            return query
    except Exception as e:
        logger.warning("RAG query generation via LLM failed: %s; using dynamic rule-based query.", e)

    # Dynamic fallback query tailored to case facts
    text_corpus = f"{state.original_description or ''} {' '.join(c.description for c in state.claims)}"
    text_lower = text_corpus.lower()
    keywords = ["Karnataka tenancy"]
    if "deposit" in text_lower:
        keywords.append("security deposit refund deduction")
    if any(k in text_lower for k in ["evict", "vacate", "notice", "leave"]):
        keywords.append("eviction notice grounds protection")
    if "rent" in text_lower:
        keywords.append("rent receipt payment dispute")
    if any(k in text_lower for k in ["damage", "repair", "paint"]):
        keywords.append("premises maintenance repair deduction")
    if len(keywords) > 1:
        return " ".join(keywords)

    return "Karnataka tenant rights security deposit eviction notice"


# Alias for compatibility
generate_search_query = generate_rag_query


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

def retrieve(query: str, top_k: int = 5) -> list[RAGResult]:
    """
    Embed the query and retrieve top_k most relevant chunks from FAISS.
    Falls back gracefully to lexical retrieval if the embedding API is rate-limited (429) or unavailable.
    Returns RAGResult objects hedged as 'potentially relevant'.
    """
    global _index, _chunks

    ensure_index_loaded()

    if _index is None or _index.ntotal == 0 or not _chunks:
        logger.info("FAISS index not loaded in memory; serving statutory passages via lexical retriever.")
        return retrieve_lexical(query, top_k=top_k)

    try:
        q_vec = _embed_text(query, task_type="RETRIEVAL_QUERY")
        q_vec = q_vec.reshape(1, -1)

        scores, indices = _index.search(q_vec, min(top_k, _index.ntotal))

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(_chunks):
                continue
            chunk = _chunks[idx]
            results.append(
                RAGResult(
                    query=query,
                    source_file=chunk["source_file"],
                    excerpt=chunk["text"][:800],  # cap excerpt length
                    relevance_score=float(score),
                    legal_area="Karnataka Tenancy Law",
                )
            )
        if results:
            return results
    except Exception as e:
        logger.warning("FAISS vector retrieval failed (%s), falling back to lexical search.", e)

    return retrieve_lexical(query, top_k=top_k)


def run_rag(state: CaseState) -> list[RAGResult]:
    """High-level: generate query from case state, then retrieve."""
    query = generate_rag_query(state)
    logger.info("RAG query: %s", query)
    return retrieve(query, top_k=5)

