"""
Central configuration — reads from .env via python-dotenv.
All values are typed; fail fast on missing required keys.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")


def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise RuntimeError(f"Required environment variable '{key}' is not set. Check .env.")
    return val


GEMINI_API_KEY: str = _require("GEMINI_API_KEY")
# NOTE: gemini-2.5-flash is no longer available to new users (deprecated).
# Using gemini-3.8-flash as the recommended replacement.
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
# Fallback model used when the primary model's RPM (5) or RPD (20) quota is exhausted.
# gemini-3.5-flash-lite has higher rate limits and serves as an automatic fallback.
GEMINI_FALLBACK_MODEL: str = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash-lite")
GEMINI_EMBEDDING_MODEL: str = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")

CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
MAX_UPLOAD_BYTES: int = int(os.getenv("MAX_UPLOAD_MB", "20")) * 1024 * 1024

BASE_DIR: Path = Path(__file__).parent
FAISS_INDEX_PATH: Path = BASE_DIR / os.getenv("FAISS_INDEX_PATH", "data/faiss_index")
CORPUS_DIR: Path = BASE_DIR / os.getenv("CORPUS_DIR", "corpus")

SESSION_TTL_HOURS: int = int(os.getenv("SESSION_TTL_HOURS", "24"))

# Triage thresholds (deterministic rules — no LLM)
TRIAGE_COURT_DATE_HIGH_DAYS: int = 14   # court date within 14 days → HIGH
TRIAGE_COURT_DATE_MEDIUM_DAYS: int = 30  # within 30 days → MEDIUM
TRIAGE_EVICTION_NOTICE_HIGH_DAYS: int = 7  # eviction notice expiry within 7 days → HIGH
TRIAGE_HIGH_FINANCIAL_THRESHOLD_INR: float = 100_000.0  # ₹1 lakh+ → HIGH

# Embedding dimension for gemini-embedding-001
EMBEDDING_DIM: int = 3072
