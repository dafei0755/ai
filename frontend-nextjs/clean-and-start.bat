@echo off
echo ========================================
echo Next.js Clean Restart Script
echo ========================================
echo.

echo [1/4] Stopping all Node.js processes...
taskkill /F /IM node.exe >nul 2>&1
timeout /t 2 /nobreak >nul
echo Done.

echo [2/4] Removing .next directory...
cd /d "%~dp0"
if exist .next (
    rd /s /q .next
    timeout /t 1 /nobreak >nul
)
if exist .next (
    echo WARNING: .next still exists, trying alternative method...
    for /d %%d in (.next\*) do rd /s /q "%%d"
    del /f /q .next\* >nul 2>&1
)
echo Done.

echo [3/4] Clearing npm cache...
call npm cache clean --force >nul 2>&1
echo Done.

echo [4/4] Starting Next.js dev server...
echo.
echo ========================================
echo Server starting on http://localhost:3000
echo ========================================
echo.
call npm run dev
