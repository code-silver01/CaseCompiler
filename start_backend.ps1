#!/usr/bin/env powershell
# Start CaseCompiler backend
# Run from the LegalAI root: .\start_backend.ps1

Set-Location "$PSScriptRoot\backend"

if (-not (Test-Path ".\venv\Scripts\uvicorn.exe")) {
    Write-Host "[ERROR] venv not found. Run: py -3.12 -m venv venv && .\venv\Scripts\pip install -r requirements.txt" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path ".\corpus\*.txt") -and -not (Test-Path ".\data\faiss_index.bin")) {
    Write-Host "[WARN] No corpus files found in corpus/. RAG will be unavailable." -ForegroundColor Yellow
    Write-Host "       Drop .txt statute excerpts into backend/corpus/ then call POST /api/index-corpus" -ForegroundColor Yellow
}

Write-Host "[CaseCompiler] Starting backend on http://localhost:8000" -ForegroundColor Green
Write-Host "[CaseCompiler] Swagger docs: http://localhost:8000/docs" -ForegroundColor Cyan

.\venv\Scripts\uvicorn main:app --reload --port 8000
