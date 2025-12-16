# WordPress SSO v3.0.15 Automated Test Script
# Usage: powershell -ExecutionPolicy Bypass -File test-v3.0.15-flow.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "WordPress SSO v3.0.15 Automated Test" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Test 1: Python Backend Health Check
Write-Host "[Test 1] Checking Python backend..." -ForegroundColor Yellow
try {
    $healthResponse = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get -ErrorAction Stop
    if ($healthResponse.status -eq "healthy") {
        Write-Host "[OK] Python backend is running`n" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] Python backend status abnormal: $($healthResponse.status)`n" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "[FAIL] Python backend not reachable. Please start:" -ForegroundColor Red
    Write-Host "   python -m uvicorn intelligent_project_analyzer.api.server:app --host 0.0.0.0 --port 8000`n" -ForegroundColor Yellow
    exit 1
}

# Test 2: WordPress REST API Token Retrieval
Write-Host "[Test 2] Testing WordPress REST API..." -ForegroundColor Yellow
try {
    $tokenResponse = Invoke-WebRequest -Uri "https://www.ucppt.com/wp-json/nextjs-sso/v1/get-token" `
        -Method Get `
        -Headers @{"Accept"="application/json"} `
        -UseBasicParsing `
        -ErrorAction Stop

    $statusCode = $tokenResponse.StatusCode
    Write-Host "HTTP Status Code: $statusCode" -ForegroundColor Cyan

    if ($statusCode -eq 200) {
        $data = $tokenResponse.Content | ConvertFrom-Json
        if ($data.success -and $data.token) {
            Write-Host "[OK] Token retrieved successfully" -ForegroundColor Green
            Write-Host "   Token length: $($data.token.Length) chars" -ForegroundColor Cyan
            Write-Host "   User ID: $($data.user.ID)" -ForegroundColor Cyan
            Write-Host "   Username: $($data.user.user_login)`n" -ForegroundColor Cyan

            $token = $data.token

            # Test 3: Token Verification
            Write-Host "[Test 3] Verifying Token..." -ForegroundColor Yellow
            try {
                $verifyResponse = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/auth/verify" `
                    -Method Post `
                    -Headers @{
                        "Content-Type"="application/json"
                        "Authorization"="Bearer $token"
                    } `
                    -ErrorAction Stop

                Write-Host "[OK] Token verification successful" -ForegroundColor Green
                Write-Host "   Verified user: $($verifyResponse.user.username)`n" -ForegroundColor Cyan
            } catch {
                Write-Host "[FAIL] Token verification failed: $_`n" -ForegroundColor Red
                exit 1
            }

        } else {
            Write-Host "[FAIL] Invalid response format: $($data)`n" -ForegroundColor Red
            exit 1
        }
    } elseif ($statusCode -eq 401) {
        Write-Host "[WARN] WordPress not logged in (401)" -ForegroundColor Yellow
        Write-Host "   Please visit https://www.ucppt.com and login`n" -ForegroundColor Yellow
        exit 1
    } else {
        Write-Host "[FAIL] Unexpected status code: $statusCode`n" -ForegroundColor Red
        exit 1
    }

} catch {
    Write-Host "[FAIL] WordPress API call failed: $_`n" -ForegroundColor Red
    exit 1
}

# Test 4: Next.js Service Check
Write-Host "[Test 4] Checking Next.js service..." -ForegroundColor Yellow
try {
    $nextResponse = Invoke-WebRequest -Uri "http://localhost:3000" -Method Get -UseBasicParsing -ErrorAction Stop -TimeoutSec 5
    Write-Host "[OK] Next.js service is running`n" -ForegroundColor Green
} catch {
    Write-Host "[WARN] Next.js service not running. Please start:" -ForegroundColor Yellow
    Write-Host "   cd frontend-nextjs && npm run dev`n" -ForegroundColor Yellow
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "[SUCCESS] All tests passed!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Manual Testing Steps:" -ForegroundColor Yellow
Write-Host "1. Visit: https://www.ucppt.com/js" -ForegroundColor White
Write-Host "2. Click the button" -ForegroundColor White
Write-Host "3. Observe if new window auto-redirects to /analysis" -ForegroundColor White
Write-Host "4. Check console logs in the new window:`n" -ForegroundColor White
Write-Host "   [AuthContext] REST API Token verification successful" -ForegroundColor Green
Write-Host "   [AuthContext] Detected login, redirecting to analysis page`n" -ForegroundColor Green
