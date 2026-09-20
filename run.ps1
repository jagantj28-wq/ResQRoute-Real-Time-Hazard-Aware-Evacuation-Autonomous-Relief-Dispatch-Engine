Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host " ResQRoute: Real-Time Hazard-Aware Evacuation & Dispatch Engine" -ForegroundColor Yellow
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

$pythonExe = ".venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    $pythonExe = "python"
}

Write-Host "Starting ResQRoute FastAPI Server on http://127.0.0.1:8000 ..." -ForegroundColor Green
Write-Host "Access Points:" -ForegroundColor White
Write-Host "  - Landing Hub:      http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "  - Citizen PWA:      http://127.0.0.1:8000/citizen" -ForegroundColor Cyan
Write-Host "  - Command Center:   http://127.0.0.1:8000/dispatcher" -ForegroundColor Cyan
Write-Host "  - API Swagger Docs: http://127.0.0.1:8000/docs" -ForegroundColor Cyan
Write-Host ""

& $pythonExe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
