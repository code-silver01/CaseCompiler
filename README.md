# CaseCompiler

**AI-powered legal case organiser. Converts informal descriptions into structured case files for lawyer review.**

> ⚠️ This tool organises information for a qualified legal practitioner. It does NOT provide legal advice.

---

## Architecture

```
backend/          FastAPI + Python
  core/
    extractor.py  Gemini multimodal extraction + function calling
    rag.py        FAISS + Gemini embeddings RAG
    interviewer.py Agentic interview loop
    compiler.py   11-section case file compiler
    triage.py     Deterministic urgency scoring (no LLM)
    chronology.py Deterministic date parsing + deduplication
  corpus/         Drop your .txt legal excerpts here
  data/           FAISS index (auto-generated)

frontend/         React + Tailwind + Vite
  src/
    App.jsx       4-step flow orchestration
    components/   CaseInput, InterviewPanel, CaseFileOutput, ProgressStepper
```

---

## Quick Start

### 1. Install backend dependencies

```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Add your legal corpus

Drop 6–8 plain `.txt` files into `backend/corpus/`. Each file should be an excerpt from a statute (e.g. Karnataka Rent Control Act sections). The RAG index will be built automatically at startup.

### 3. Start the backend

```powershell
# From backend/
uvicorn main:app --reload --port 8000
```

The first startup will embed your corpus files and build the FAISS index. This takes ~30–60 seconds depending on corpus size.

To force a rebuild after adding new corpus files:
```
POST http://localhost:8000/api/index-corpus?force_rebuild=true
```

### 4. Install frontend dependencies

```powershell
cd frontend
npm install
```

### 5. Start the frontend

```powershell
npm run dev
```

Open [http://localhost:5173](http://localhost:5173)

---

## User Flow

1. **Describe** — Type your situation (and optionally upload images/PDFs/text as evidence)
2. **Extract** — Gemini uses function calling to extract parties, events, claims, financials, contradictions
3. **Interview** — AI asks targeted follow-up questions based on case state gaps
4. **Compile** — Download a structured 11-section case file (JSON + rendered UI)

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/session` | Create session |
| GET | `/api/session/{id}` | Get case state |
| POST | `/api/session/{id}/extract` | Extract from text + files |
| POST | `/api/session/{id}/answer` | Post interview answer |
| GET | `/api/session/{id}/compile` | Compile case file |
| POST | `/api/index-corpus` | Rebuild FAISS index |

Interactive docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Corpus File Format

Each `.txt` file in `backend/corpus/` should contain one or more statute sections in plain text.
Suggested naming: `karnataka_rent_act_s<section>.txt`

Example:
```
Section 5 — Deposit of advance rent and security
(1) No landlord shall demand or receive any premium or pugree or any other 
amount by whatever name called, in addition to the rent agreed upon.
(2) A landlord may, however, require a tenant to pay a sum not exceeding 
three months rent as security deposit...
```

---

## Configuration (.env)

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | required | Your Gemini API key |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Model ID (update if needed) |
| `GEMINI_EMBEDDING_MODEL` | `gemini-embedding-001` | Embedding model |
| `MAX_UPLOAD_MB` | `20` | Max upload size per file |
| `TRIAGE_COURT_DATE_HIGH_DAYS` | `14` | Court date HIGH urgency threshold |
| `TRIAGE_HIGH_FINANCIAL_THRESHOLD_INR` | `100000` | Financial HIGH urgency threshold |

---

## Out of Scope (Future Work)

- Production auth & session encryption
- Knowledge graph (Neo4j)
- Trained ML classifiers
- Multi-jurisdiction support
- Deployment (Vercel/Render)
- Persistent storage (MongoDB)
