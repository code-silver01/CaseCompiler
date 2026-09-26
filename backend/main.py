"""
FastAPI application entry point for CaseCompiler backend.
Starts FAISS index build on startup.

Run with:
  uvicorn main:app --reload --port 8000

FUTURE WORK: Add rate limiting, auth middleware, and HTTPS for production.
"""
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import config
from api.routes import router
from core.rag import build_index

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: build FAISS index from corpus/."""
    logger.info("CaseCompiler backend starting…")
    logger.info("Gemini model: %s", config.GEMINI_MODEL)
    logger.info("Corpus dir: %s", config.CORPUS_DIR)
    try:
        n = build_index(force_rebuild=False)
        logger.info("FAISS index ready with %d chunks.", n)
    except Exception as e:
        logger.warning("FAISS index build failed at startup: %s. RAG will be unavailable.", e)
    yield
    logger.info("CaseCompiler backend shutting down.")


app = FastAPI(
    title="CaseCompiler API",
    description=(
        "AI-powered legal case organisation tool. "
        "Converts informal case descriptions into structured case files for lawyer review. "
        "NOT legal advice."
    ),
    version="0.1.0-mvp",
    lifespan=lifespan,
)

# CORS — allow Vite dev server, Render static frontend & all production origins
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request, call_next):
    """Inject OWASP defensive security headers on all responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc: Exception):
    """Sanitize internal errors to prevent leaking server paths or tracebacks."""
    logger.error("Unhandled exception at %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again or check the server logs."},
    )


app.include_router(router, prefix="/api")


@app.get("/")
def root():
    return {
        "status": "online",
        "service": "CaseCompiler API",
        "version": "0.1.0-mvp",
        "health": "/api/health",
        "docs": "/docs",
        "note": "Open your casecompiler-frontend service URL to interact with the full web app."
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
