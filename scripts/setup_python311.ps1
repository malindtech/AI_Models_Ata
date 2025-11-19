# Setup Python 3.11 Environment for Streamlit UI
# This script creates a Python 3.11 virtual environment and installs all dependencies

Write-Host "`n=====================================================================" -ForegroundColor Cyan
Write-Host "     Python 3.11 Setup for Day 8 Review System" -ForegroundColor Cyan
Write-Host "=====================================================================`n" -ForegroundColor Cyan

# Check if Python 3.11 is installed
Write-Host "Checking for Python 3.11..." -ForegroundColor Yellow

$python311 = $null
$pythonCommands = @("py -3.11", "python3.11", "python")

foreach ($cmd in $pythonCommands) {
    try {
        $version = & { $ErrorActionPreference = 'SilentlyContinue'; Invoke-Expression "$cmd --version" } 2>$null
        if ($version -match "Python 3\.11") {
            $python311 = $cmd
            Write-Host "[OK] Found: $version using command '$cmd'" -ForegroundColor Green
            break
        }
    } catch {
        # Command not found, try next
    }
}

if (-not $python311) {
    Write-Host "X Python 3.11 not found!`n" -ForegroundColor Red
    Write-Host "Please install Python 3.11.9 from:" -ForegroundColor Yellow
    Write-Host "   https://www.python.org/downloads/release/python-3119/`n" -ForegroundColor Cyan
    Write-Host "Installation tips:" -ForegroundColor Yellow
    Write-Host "   - Download 'Windows installer (64-bit)'" -ForegroundColor White
    Write-Host "   - Check 'Add Python to PATH' during installation" -ForegroundColor White
    Write-Host "   - You can keep Python 3.13 installed" -ForegroundColor White
    Write-Host "`nRun this script again after installing Python 3.11`n" -ForegroundColor Cyan
    
    # Offer to open download page
    $openBrowser = Read-Host "Open download page in browser? (y/n)"
    if ($openBrowser -eq 'y') {
        Start-Process "https://www.python.org/downloads/release/python-3119/"
    }
    
    exit 1
}

# Create Python 3.11 virtual environment
Write-Host "\nCreating Python 3.11 virtual environment..." -ForegroundColor Yellow

$venvPath = "venv311"

if (Test-Path $venvPath) {
    Write-Host "[WARNING] Directory '$venvPath' already exists." -ForegroundColor Yellow
    $overwrite = Read-Host "Delete and recreate? (y/n)"
    if ($overwrite -eq 'y') {
        Write-Host "Removing existing venv..." -ForegroundColor Yellow
        Remove-Item $venvPath -Recurse -Force
    } else {
        Write-Host "Using existing venv..." -ForegroundColor Cyan
        & "$venvPath\Scripts\Activate.ps1"
        Write-Host "[OK] Virtual environment activated" -ForegroundColor Green
        exit 0
    }
}

Write-Host "Creating new virtual environment..." -ForegroundColor Cyan
Invoke-Expression "$python311 -m venv $venvPath"

if (-not (Test-Path "$venvPath\Scripts\Activate.ps1")) {
    Write-Host "[ERROR] Failed to create virtual environment!" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Virtual environment created: $venvPath" -ForegroundColor Green

# Activate the environment
Write-Host "\nActivating virtual environment..." -ForegroundColor Yellow
& "$venvPath\Scripts\Activate.ps1"

# Upgrade pip
Write-Host "\nUpgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet

# Install dependencies
Write-Host "\nInstalling dependencies from requirements.txt..." -ForegroundColor Yellow
Write-Host "   This may take 5-10 minutes...`n" -ForegroundColor Gray

pip install -r requirements.txt

if ($LASTEXITCODE -ne 0) {
    Write-Host "\n[ERROR] Failed to install some dependencies" -ForegroundColor Red
    Write-Host "   You may need to install them individually`n" -ForegroundColor Yellow
    exit 1
}

Write-Host "\n[OK] All dependencies installed successfully!" -ForegroundColor Green

# Verify key packages
Write-Host "\nVerifying installations..." -ForegroundColor Yellow

$packagesToCheck = @("streamlit", "pandas", "fastapi", "chromadb", "torch", "transformers")
$allInstalled = $true

foreach ($package in $packagesToCheck) {
    $installed = pip show $package 2>$null
    if ($installed) {
        Write-Host "   [OK] $package" -ForegroundColor Green
    } else {
        Write-Host "   [MISSING] $package - NOT INSTALLED" -ForegroundColor Red
        $allInstalled = $false
    }
}

if (-not $allInstalled) {
    Write-Host "\n[WARNING] Some packages missing. Installing individually..." -ForegroundColor Yellow
    pip install streamlit pandas
}

# Display completion message
Write-Host "\n====================================================================" -ForegroundColor Green
Write-Host "           Python 3.11 Setup Complete!" -ForegroundColor Green
Write-Host "====================================================================\n" -ForegroundColor Green

Write-Host "`nNext Steps:" -ForegroundColor Cyan
Write-Host "`n   1. Keep this terminal open (venv311 is activated)" -ForegroundColor White
Write-Host "`n   2. Start backend (in another terminal):" -ForegroundColor White
Write-Host "      cd 'D:\Malind Tech\AI_Models_Ata'" -ForegroundColor Gray
Write-Host "      .\venv311\Scripts\Activate.ps1" -ForegroundColor Gray
Write-Host "      uvicorn backend.main:app --reload" -ForegroundColor Gray
Write-Host "`n   3. Start Streamlit UI (in this terminal):" -ForegroundColor White
Write-Host "      streamlit run ui/review_app.py" -ForegroundColor Gray
Write-Host "`n   Or use the launcher:" -ForegroundColor White
Write-Host "      .\scripts\start_review_ui_py311.ps1" -ForegroundColor Gray

Write-Host "`nTips:" -ForegroundColor Yellow
Write-Host "   - Always activate venv311 before running commands:" -ForegroundColor White
Write-Host "     .\venv311\Scripts\Activate.ps1" -ForegroundColor Gray
Write-Host "   - Your old venv (Python 3.13) is still available" -ForegroundColor White
Write-Host "   - You can switch between them as needed`n" -ForegroundColor White

# Offer to start services
Write-Host "=====================================================================" -ForegroundColor Magenta
$startNow = Read-Host "Start the review system now? (y/n)"

if ($startNow -eq 'y') {
    Write-Host "`nLaunching services...`n" -ForegroundColor Cyan
    
    # Start backend in new window
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'D:\Malind Tech\AI_Models_Ata'; .\venv311\Scripts\Activate.ps1; Write-Host 'Starting Backend...' -ForegroundColor Green; uvicorn backend.main:app --reload"
    
    Start-Sleep -Seconds 3
    
    # Start Streamlit UI
    Write-Host "Starting Streamlit UI..." -ForegroundColor Cyan
    streamlit run ui/review_app.py
} else {
    Write-Host "`nSetup complete. Run the commands above when ready!`n" -ForegroundColor Green
}
