# Day 8: Review UI Quick Start Script
# Launches backend and Streamlit UI in separate terminals

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "  DAY 8: Human-in-the-Loop Review System - Quick Start" -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment is activated
if (-not $env:VIRTUAL_ENV) {
    Write-Host "❌ Virtual environment not activated!" -ForegroundColor Red
    Write-Host "Please run: .\venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Virtual environment detected: $env:VIRTUAL_ENV" -ForegroundColor Green
Write-Host ""

# Check if backend dependencies are installed
Write-Host "🔍 Checking dependencies..." -ForegroundColor Yellow

$packages = @("streamlit", "pandas", "fastapi", "httpx")
$missing = @()

foreach ($package in $packages) {
    $result = pip show $package 2>$null
    if (-not $result) {
        $missing += $package
    }
}

if ($missing.Count -gt 0) {
    Write-Host "⚠️  Missing packages: $($missing -join ', ')" -ForegroundColor Yellow
    Write-Host "Installing missing dependencies..." -ForegroundColor Yellow
    pip install streamlit pandas
    Write-Host "✅ Dependencies installed" -ForegroundColor Green
} else {
    Write-Host "✅ All dependencies installed" -ForegroundColor Green
}

Write-Host ""

# Check if backend is already running
Write-Host "🔍 Checking if backend is running..." -ForegroundColor Yellow

try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "✅ Backend is already running" -ForegroundColor Green
    $backendRunning = $true
} catch {
    Write-Host "⚠️  Backend not detected" -ForegroundColor Yellow
    $backendRunning = $false
}

Write-Host ""

# Start backend if not running
if (-not $backendRunning) {
    Write-Host "🚀 Starting FastAPI backend..." -ForegroundColor Cyan
    Write-Host "   URL: http://localhost:8000" -ForegroundColor Gray
    Write-Host ""
    
    # Start backend in new terminal
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; .\venv\Scripts\Activate.ps1; Write-Host '🚀 Starting Backend...' -ForegroundColor Cyan; uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000"
    
    # Wait for backend to start
    Write-Host "⏳ Waiting for backend to start..." -ForegroundColor Yellow
    $attempts = 0
    $maxAttempts = 20
    
    while ($attempts -lt $maxAttempts) {
        Start-Sleep -Seconds 1
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 2 -ErrorAction Stop
            Write-Host "✅ Backend is ready!" -ForegroundColor Green
            break
        } catch {
            $attempts++
            Write-Host "." -NoNewline
        }
    }
    
    if ($attempts -eq $maxAttempts) {
        Write-Host ""
        Write-Host "❌ Backend failed to start within timeout" -ForegroundColor Red
        Write-Host "Please check the backend terminal for errors" -ForegroundColor Yellow
        exit 1
    }
    
    Write-Host ""
}

# Start Streamlit UI
Write-Host ""
Write-Host "🎨 Starting Streamlit Review UI..." -ForegroundColor Cyan
Write-Host "   URL: http://localhost:8501" -ForegroundColor Gray
Write-Host ""

Write-Host "==================================================================" -ForegroundColor Green
Write-Host "  ✅ Review System Ready!" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "📖 Instructions:" -ForegroundColor Yellow
Write-Host "   1. The Streamlit UI will open in your browser automatically" -ForegroundColor White
Write-Host "   2. Configure content settings in the left sidebar" -ForegroundColor White
Write-Host "   3. Click 'Generate Content' to create a review task" -ForegroundColor White
Write-Host "   4. Use Approve/Reject/Edit buttons to review content" -ForegroundColor White
Write-Host "   5. Feedback is saved to: data/human_feedback.csv" -ForegroundColor White
Write-Host ""
Write-Host "🧪 Run tests: python scripts/test_review_ui.py" -ForegroundColor Cyan
Write-Host "📚 Documentation: DAY8_REVIEW_SYSTEM_GUIDE.md" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop (you may need to close terminals manually)" -ForegroundColor Gray
Write-Host ""

# Start Streamlit
streamlit run ui/review_app.py
