# Launch Day 8 Review System with Python 3.11
# This script starts both backend and Streamlit UI using Python 3.11 environment

Write-Host "`n╔═══════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║           Day 8 Review System - Python 3.11 Launcher         ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

$workspaceRoot = "D:\Malind Tech\AI_Models_Ata"
$venvPath = "$workspaceRoot\venv311"

# Check if Python 3.11 venv exists
if (-not (Test-Path "$venvPath\Scripts\Activate.ps1")) {
    Write-Host "❌ Python 3.11 virtual environment not found!" -ForegroundColor Red
    Write-Host "`n📋 Please run setup first:" -ForegroundColor Yellow
    Write-Host "   .\scripts\setup_python311.ps1`n" -ForegroundColor Cyan
    exit 1
}

# Check if backend is already running
Write-Host "🔍 Checking if backend is running..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "✅ Backend already running on port 8000" -ForegroundColor Green
    $startBackend = $false
} catch {
    Write-Host "⚠️  Backend not running" -ForegroundColor Yellow
    $startBackend = $true
}

# Check if Streamlit is already running
Write-Host "🔍 Checking if Streamlit is running..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8501" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "✅ Streamlit already running on port 8501" -ForegroundColor Green
    $startStreamlit = $false
} catch {
    Write-Host "⚠️  Streamlit not running" -ForegroundColor Yellow
    $startStreamlit = $true
}

# Start backend if needed
if ($startBackend) {
    Write-Host "`n🚀 Starting FastAPI backend..." -ForegroundColor Cyan
    Write-Host "   Opening new terminal window...`n" -ForegroundColor Gray
    
    $backendCmd = "cd '$workspaceRoot'; & '$venvPath\Scripts\Activate.ps1'; Write-Host '═══════════════════════════════════════════════════' -ForegroundColor Cyan; Write-Host '  FastAPI Backend - Port 8000' -ForegroundColor Green; Write-Host '═══════════════════════════════════════════════════' -ForegroundColor Cyan; Write-Host ''; Write-Host '📡 API Docs: http://localhost:8000/docs' -ForegroundColor Yellow; Write-Host '💚 Health: http://localhost:8000/health' -ForegroundColor Yellow; Write-Host ''; uvicorn backend.main:app --reload"
    
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd
    
    Write-Host "⏳ Waiting for backend to start..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    
    # Verify backend started
    $backendReady = $false
    for ($i = 1; $i -le 6; $i++) {
        try {
            $health = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 2 -ErrorAction Stop
            Write-Host "✅ Backend is ready!" -ForegroundColor Green
            $backendReady = $true
            break
        } catch {
            Write-Host "   Attempt $i/6: Backend starting..." -ForegroundColor Gray
            Start-Sleep -Seconds 2
        }
    }
    
    if (-not $backendReady) {
        Write-Host "❌ Backend failed to start. Check the backend terminal for errors." -ForegroundColor Red
        exit 1
    }
}

# Start Streamlit if needed
if ($startStreamlit) {
    Write-Host "`n🎨 Starting Streamlit UI..." -ForegroundColor Cyan
    Write-Host "   Opening in your default browser...`n" -ForegroundColor Gray
    
    # Activate venv and start Streamlit
    & "$venvPath\Scripts\Activate.ps1"
    
    Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Magenta
    Write-Host "  Streamlit Review UI - Port 8501" -ForegroundColor Green
    Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Magenta
    Write-Host ""
    Write-Host "🌐 Opening: http://localhost:8501" -ForegroundColor Yellow
    Write-Host "📊 Dashboard: Review, approve, and edit generated content" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Press Ctrl+C to stop" -ForegroundColor Gray
    Write-Host ""
    
    streamlit run ui/review_app.py
} else {
    Write-Host "`n✅ Both services are already running!" -ForegroundColor Green
    Write-Host "`n🌐 Access URLs:" -ForegroundColor Cyan
    Write-Host "   • Streamlit UI: http://localhost:8501" -ForegroundColor White
    Write-Host "   • Backend API: http://localhost:8000/docs" -ForegroundColor White
    Write-Host "   • Health Check: http://localhost:8000/health`n" -ForegroundColor White
}
