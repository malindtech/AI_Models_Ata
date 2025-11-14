# Simple Chat with Customer Support Agent
# Usage: Just run this script and start typing!

Write-Host "=== Customer Support Agent ===" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8000/health" -ErrorAction Stop
    Write-Host "Connected to Docker backend" -ForegroundColor Green
} catch {
    Write-Host "Docker not running! Run: docker-compose up -d" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Type your message (or 'exit' to quit):" -ForegroundColor Yellow
Write-Host ""

while ($true) {
    # Get user input
    $message = Read-Host "You"
    
    if ($message -eq "exit" -or $message -eq "") {
        Write-Host "Goodbye!" -ForegroundColor Cyan
        break
    }
    
    try {
        # Send message
        $body = @{ message = $message; async_mode = $true } | ConvertTo-Json
        $response = Invoke-RestMethod -Method POST -Uri "http://localhost:8000/v1/generate/reply" -ContentType "application/json" -Body $body
        
        $taskId = $response.task_id
        Write-Host "Processing..." -NoNewline -ForegroundColor Yellow
        
        # Wait for response
        $maxWait = 60
        $waited = 0
        
        while ($waited -lt $maxWait) {
            Start-Sleep -Seconds 1
            $status = Invoke-RestMethod -Uri "http://localhost:8000/v1/tasks/$taskId"
            
            if ($status.status -eq "success") {
                Write-Host " Done!" -ForegroundColor Green
                Write-Host ""
                Write-Host "Agent: " -NoNewline -ForegroundColor Cyan
                Write-Host $status.result.reply -ForegroundColor White
                Write-Host ""
                break
            }
            
            if ($status.status -eq "failure") {
                Write-Host " Failed!" -ForegroundColor Red
                Write-Host "Error: " -NoNewline -ForegroundColor Red
                Write-Host $status.result.error
                Write-Host ""
                break
            }
            
            $waited++
        }
        
        if ($waited -ge $maxWait) {
            Write-Host " Timeout!" -ForegroundColor Red
            Write-Host ""
        }
        
    } catch {
        Write-Host ""
        Write-Host "Error occurred" -ForegroundColor Red
        Write-Host $_.Exception.Message
        Write-Host ""
    }
}
