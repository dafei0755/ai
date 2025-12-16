# WordPress SSO v3.0.16 Diagnostic Tool
# This script helps collect debug information from WordPress

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "WordPress SSO v3.0.16 Diagnostic Tool" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check if WP_DEBUG is enabled
Write-Host "[Step 1/4] Checking WordPress debug configuration..." -ForegroundColor Yellow
Write-Host ""
Write-Host "Please verify wp-config.php contains:" -ForegroundColor White
Write-Host "  define('WP_DEBUG', true);" -ForegroundColor Green
Write-Host "  define('WP_DEBUG_LOG', true);" -ForegroundColor Green
Write-Host "  define('WP_DEBUG_DISPLAY', false);" -ForegroundColor Green
Write-Host ""
$debugEnabled = Read-Host "Is WP_DEBUG enabled? (y/n)"

if ($debugEnabled -ne 'y') {
    Write-Host ""
    Write-Host "Please enable WordPress debugging first:" -ForegroundColor Red
    Write-Host "1. Edit wp-config.php" -ForegroundColor Yellow
    Write-Host "2. Add the debug configuration lines above" -ForegroundColor Yellow
    Write-Host "3. Save and run this script again" -ForegroundColor Yellow
    Write-Host ""
    exit
}

# Step 2: Locate debug.log file
Write-Host ""
Write-Host "[Step 2/4] Locating WordPress debug log..." -ForegroundColor Yellow
Write-Host ""
Write-Host "Typical location: /wp-content/debug.log" -ForegroundColor White
Write-Host "Please enter the full path to debug.log file:" -ForegroundColor White
$debugLogPath = Read-Host "Path"

if (-not (Test-Path $debugLogPath)) {
    Write-Host ""
    Write-Host "Error: File not found at $debugLogPath" -ForegroundColor Red
    Write-Host ""
    Write-Host "Common locations:" -ForegroundColor Yellow
    Write-Host "  - C:\xampp\htdocs\wordpress\wp-content\debug.log" -ForegroundColor Gray
    Write-Host "  - /var/www/html/wp-content/debug.log" -ForegroundColor Gray
    Write-Host "  - On remote server: Use FTP/SSH to download it" -ForegroundColor Gray
    Write-Host ""
    exit
}

# Step 3: Extract v3.0.16 logs
Write-Host ""
Write-Host "[Step 3/4] Extracting v3.0.16 logs..." -ForegroundColor Yellow
Write-Host ""

$logContent = Get-Content $debugLogPath -Encoding UTF8 -ErrorAction SilentlyContinue
$v316Logs = $logContent | Where-Object { $_ -match '\[Next\.js SSO v3\.0\.16\]' }

if ($v316Logs.Count -eq 0) {
    Write-Host "No v3.0.16 logs found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "This means either:" -ForegroundColor Yellow
    Write-Host "  1. v3.0.16 is not installed (check WordPress Plugins page)" -ForegroundColor White
    Write-Host "  2. The plugin has not been called yet (visit localhost:3000 first)" -ForegroundColor White
    Write-Host "  3. Debug logging is not working properly" -ForegroundColor White
    Write-Host ""

    Write-Host "Last 10 lines of debug.log:" -ForegroundColor Yellow
    $logContent | Select-Object -Last 10 | ForEach-Object { Write-Host $_ -ForegroundColor Gray }
    Write-Host ""
    exit
}

# Step 4: Analyze logs
Write-Host ""
Write-Host "[Step 4/4] Analyzing logs..." -ForegroundColor Yellow
Write-Host ""
Write-Host "Found $($v316Logs.Count) v3.0.16 log entries" -ForegroundColor Green
Write-Host ""
Write-Host "==================== v3.0.16 Logs ====================" -ForegroundColor Cyan

foreach ($log in $v316Logs) {
    if ($log -match '✅') {
        Write-Host $log -ForegroundColor Green
    } elseif ($log -match '❌') {
        Write-Host $log -ForegroundColor Red
    } elseif ($log -match '⚠️') {
        Write-Host $log -ForegroundColor Yellow
    } elseif ($log -match '🔍') {
        Write-Host $log -ForegroundColor Cyan
    } else {
        Write-Host $log -ForegroundColor White
    }
}

Write-Host "======================================================" -ForegroundColor Cyan
Write-Host ""

# Save to file
$outputFile = "v3.0.16-diagnostic-report.txt"
$v316Logs | Out-File -FilePath $outputFile -Encoding UTF8
Write-Host "Full report saved to: $outputFile" -ForegroundColor Green
Write-Host ""

# Analyze patterns
Write-Host "==================== Analysis ====================" -ForegroundColor Cyan
Write-Host ""

$hasWpcomPlugin = $v316Logs | Where-Object { $_ -match '检测到WPCOM Member Pro插件' }
$hasWpcomSuccess = $v316Logs | Where-Object { $_ -match '通过WPCOM API获取到会员' }
$hasWpcomCookie = $v316Logs | Where-Object { $_ -match '检测到WPCOM Cookie' }
$hasCookieList = $v316Logs | Where-Object { $_ -match '当前所有Cookies:' }
$hasFailure = $v316Logs | Where-Object { $_ -match '所有方式都无法获取用户' }

if ($hasWpcomPlugin.Count -gt 0) {
    Write-Host "[DETECTED] WPCOM Member Pro plugin found" -ForegroundColor Green
    if ($hasWpcomSuccess.Count -gt 0) {
        Write-Host "[SUCCESS] User detected via WPCOM API" -ForegroundColor Green
        Write-Host ""
        Write-Host "Result: v3.0.16 is working correctly!" -ForegroundColor Green
        Write-Host "If you still see 401 errors, the issue may be:" -ForegroundColor Yellow
        Write-Host "  - Browser cache (clear cache and cookies)" -ForegroundColor White
        Write-Host "  - Next.js cache (restart npm run dev)" -ForegroundColor White
    } else {
        Write-Host "[FAILED] WPCOM API did not return user" -ForegroundColor Red
        Write-Host ""
        Write-Host "This indicates:" -ForegroundColor Yellow
        Write-Host "  - WPCOM Member Pro uses a different function name" -ForegroundColor White
        Write-Host "  - Or the user is not actually logged in" -ForegroundColor White
    }
} else {
    Write-Host "[NOT DETECTED] WPCOM Member Pro plugin not found" -ForegroundColor Yellow
    Write-Host ""
}

if ($hasWpcomCookie.Count -gt 0) {
    Write-Host "[DETECTED] WPCOM custom cookies found" -ForegroundColor Green
} else {
    Write-Host "[NOT DETECTED] No WPCOM custom cookies" -ForegroundColor Yellow
}

if ($hasCookieList.Count -gt 0) {
    Write-Host ""
    Write-Host "Available cookies:" -ForegroundColor Cyan
    $cookieLine = $hasCookieList | Select-Object -First 1
    if ($cookieLine -match '当前所有Cookies: (.+)') {
        $cookies = $matches[1] -split ', '
        foreach ($cookie in $cookies) {
            if ($cookie -match 'wpcom|wordpress|memberpress') {
                Write-Host "  - $cookie" -ForegroundColor Green
            } else {
                Write-Host "  - $cookie" -ForegroundColor Gray
            }
        }
    }
}

if ($hasFailure.Count -gt 0) {
    Write-Host ""
    Write-Host "[FAILURE] All detection methods failed" -ForegroundColor Red
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "  1. Share this report with developer" -ForegroundColor White
    Write-Host "  2. Test with WordPress standard login (/wp-login.php)" -ForegroundColor White
    Write-Host "  3. Check WPCOM Member Pro documentation for API" -ForegroundColor White
}

Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Diagnostic complete!" -ForegroundColor Green
Write-Host "Report saved to: $outputFile" -ForegroundColor Cyan
Write-Host ""
