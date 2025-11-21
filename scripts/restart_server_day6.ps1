# Restart the FastAPI uvicorn server to load Day 6 changes
Write-Host "`n===================================================================" -ForegroundColor Cyan
Write-Host "Restarting FastAPI Server with Day 6 Integration" -ForegroundColor Cyan
Write-Host "===================================================================" -ForegroundColor Cyan

# Kill existing uvicorn processes
$uvicornProcesses = Get-Process | Where-Object { $_.ProcessName -like "*python*" -and $_.CommandLine -like "*uvicorn*backend.main:app*" }

if ($uvicornProcesses) {
    Write-Host "`nStopping existing uvicorn server..." -ForegroundColor Yellow
    $uvicornProcesses | Stop-Process -Force
    Start-Sleep -Seconds 2
    Write-Host "✅ Server stopped" -ForegroundColor Green
} else {
    Write-Host "`nℹ️  No existing uvicorn server found" -ForegroundColor Yellow
}

# Activate virtual environment and start server
Write-Host "`nStarting uvicorn server with Day 6 features..." -ForegroundColor Yellow

# Change to project directory
Set-Location "D:\Malind Tech\AI_Models_Ata"

# Activate venv and start server
& "D:\Malind Tech\AI_Models_Ata\venv\Scripts\Activate.ps1"

Write-Host "✅ Starting uvicorn on http://0.0.0.0:8000..." -ForegroundColor Green
Write-Host "   Day 6 Features: Query Expansion, Personalization, Hybrid Retrieval" -ForegroundColor Cyan
Write-Host "   Press Ctrl+C to stop the server`n" -ForegroundColor Gray

# Start uvicorn
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
