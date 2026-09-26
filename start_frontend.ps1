#!/usr/bin/env powershell
# Start CaseCompiler frontend
# Run from the LegalAI root: .\start_frontend.ps1

Set-Location "$PSScriptRoot\frontend"

if (-not (Test-Path ".\node_modules")) {
    Write-Host "[INFO] node_modules not found. Running npm install..." -ForegroundColor Yellow
    npm install
}

Write-Host "[CaseCompiler] Starting frontend on http://localhost:5173" -ForegroundColor Green
npm run dev
