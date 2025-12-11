# Integration test script for LangGraph Design
# Usage: run this in PowerShell (Admin not required). It starts the API server and Streamlit frontend,
# sends a test analysis request, polls the session status, writes logs, and then tears down processes.

param(
    [int]$ApiPort = 8000,
    [int]$FrontendPort = 8501,
    [int]$PollIntervalSec = 5,
    [int]$TimeoutSec = 300
)

$timestamp = (Get-Date).ToString('yyyyMMdd_HHmmss')
$logDir = Join-Path -Path $PSScriptRoot -ChildPath "logs"
if (-not (Test-Path $logDir)) { New-Item -Path $logDir -ItemType Directory | Out-Null }
$logFile = Join-Path $logDir "integration_$timestamp.log"

function Log($s) {
    $line = (Get-Date -Format 's') + "`t" + $s
    $line | Tee-Object -FilePath $logFile -Append
}

Log "Starting integration test: timestamp=$timestamp"

# Start API server
$serverScript = "intelligent_project_analyzer\api\server.py"
if (-not (Test-Path $serverScript)) { Log "ERROR: server script not found: $serverScript"; exit 2 }

$serverOut = Join-Path $logDir "server_out_$timestamp.txt"
$serverErr = Join-Path $logDir "server_err_$timestamp.txt"

Log "Starting API server (python $serverScript)..."
$serverProc = Start-Process -FilePath "python" -ArgumentList "$serverScript" -NoNewWindow -PassThru -RedirectStandardOutput $serverOut -RedirectStandardError $serverErr
Start-Sleep -Seconds 2
Log "API server started, PID=$($serverProc.Id)"
param(
    [int]$ApiPort = 8000,
    [int]$FrontendPort = 8501,
    [int]$PollIntervalSec = 5,
    [int]$TimeoutSec = 300
)

# Minimal ASCII-only integration test to avoid encoding issues
$timestamp = (Get-Date).ToString('yyyyMMdd_HHmmss')
$logDir = Join-Path -Path $PSScriptROOT -ChildPath "logs"
if (-not (Test-Path $logDir)) { New-Item -Path $logDir -ItemType Directory | Out-Null }
$logFile = Join-Path $logDir "integration_$timestamp.log"

function Log($s) {
    $line = (Get-Date -Format 's') + "`t" + $s
    $line | Tee-Object -FilePath $logFile -Append
}

Log "Starting integration test (ASCII payload): $timestamp"

# Start API server (python script path)
$serverScript = "intelligent_project_analyzer\api\server.py"
if (-not (Test-Path $serverScript)) { Log "ERROR: server script not found: $serverScript"; exit 2 }

$serverOut = Join-Path $logDir "server_out_$timestamp.txt"
$serverErr = Join-Path $logDir "server_err_$timestamp.txt"

Log "Starting API server (python $serverScript)..."
$serverProc = Start-Process -FilePath "python" -ArgumentList "$serverScript" -NoNewWindow -PassThru -RedirectStandardOutput $serverOut -RedirectStandardError $serverErr
Start-Sleep -Seconds 2
Log "API server started, PID=$($serverProc.Id)"

# Optionally start frontend if present
$frontendScript = "intelligent_project_analyzer\frontend\app.py"
if (-not (Test-Path $frontendScript)) {
    Log "WARN: frontend script not found: $frontendScript (skipping frontend)"
    $frontendProc = $null
} else {
    $frontendOut = Join-Path $logDir "frontend_out_$timestamp.txt"
    $frontendErr = Join-Path $logDir "frontend_err_$timestamp.txt"
    Log "Starting Streamlit frontend..."
    $frontendProc = Start-Process -FilePath "python" -ArgumentList "-m streamlit run $frontendScript --server.port $FrontendPort" -NoNewWindow -PassThru -RedirectStandardOutput $frontendOut -RedirectStandardError $frontendErr
    Start-Sleep -Seconds 2
    Log "Frontend started, PID=$($frontendProc.Id)"
}

# Wait for API to become responsive
$apiUrl = "http://127.0.0.1:$ApiPort"
$healthOk = $false
for ($i=0; $i -lt 30; $i++) {
    try {
        $r = Invoke-RestMethod -Method Get -Uri "$apiUrl/" -TimeoutSec 2 -ErrorAction Stop
        Log "API responded to root GET"
        $healthOk = $true
        break
    } catch {
        Start-Sleep -Seconds 1
    }
}
if (-not $healthOk) { Log "ERROR: API did not respond in time. Check $serverOut / $serverErr"; goto TEARDOWN }

# Send a simple ASCII test payload
$startUrl = "$apiUrl/api/analysis/start"
$bodyObj = @{ user_id = 'integration_test'; user_input = 'ASCII test payload - please ignore' }
$body = $bodyObj | ConvertTo-Json
Log ("POST {0} with test payload" -f $startUrl)
try {
    $resp = Invoke-RestMethod -Method Post -Uri $startUrl -Body $body -ContentType "application/json" -ErrorAction Stop
    $sessionId = $resp.session_id
    Log ("Received response: session_id={0}" -f $sessionId)
} catch {
    Log ("ERROR: Failed to POST test request: {0}" -f $_)
    goto TEARDOWN
}

# Poll status until complete or timeout
$statusUrl = "$apiUrl/api/analysis/status/$sessionId"
$startTime = Get-Date
while ((Get-Date) - $startTime -lt (New-TimeSpan -Seconds $TimeoutSec)) {
    try {
        $stat = Invoke-RestMethod -Method Get -Uri $statusUrl -ErrorAction Stop
        $sjson = $stat | ConvertTo-Json -Depth 10
        Log ("Status: {0}" -f $sjson)
        if ($stat.status -eq "completed" -or $stat.status -eq "finished" -or $stat.status -eq "success") {
            Log ("Analysis finished for session {0}" -f $sessionId)
            break
        }
    } catch {
        Log ("WARN: error polling status: {0}" -f $_)
    }
    Start-Sleep -Seconds $PollIntervalSec
}

if ((Get-Date) - $startTime -ge (New-TimeSpan -Seconds $TimeoutSec)) { Log "ERROR: Timeout waiting for analysis to complete." }

:TEARDOWN
Log "--- BEGIN captured logs ---"
if (Test-Path $serverOut) { Log "--- server stdout ---"; Get-Content $serverOut -Tail 200 | ForEach-Object { Log ("[server] {0}" -f $_) } }
if (Test-Path $serverErr) { Log "--- server stderr ---"; Get-Content $serverErr -Tail 200 | ForEach-Object { Log ("[server-err] {0}" -f $_) } }
if ($frontendProc -ne $null) { if (Test-Path $frontendOut) { Log "--- frontend stdout ---"; Get-Content $frontendOut -Tail 200 | ForEach-Object { Log ("[frontend] {0}" -f $_) } } }
Log "--- END captured logs ---"

# Teardown processes
try {
    if ($frontendProc -ne $null) { Log ("Stopping frontend PID={0}" -f $frontendProc.Id); Stop-Process -Id $frontendProc.Id -Force -ErrorAction SilentlyContinue }
} catch {}
try {
    if ($serverProc -ne $null) { Log ("Stopping server PID={0}" -f $serverProc.Id); Stop-Process -Id $serverProc.Id -Force -ErrorAction SilentlyContinue }
} catch {}

Log "Integration test finished. See $logFile for details."

# output path for user convenience
Write-Output $logFile
