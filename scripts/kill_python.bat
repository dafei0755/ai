@echo off
REM 强制终止所有 Python 进程的快捷脚本

echo ================================================
echo  强制终止所有 Python 进程
echo ================================================
echo.

taskkill /F /IM python.exe 2>nul
if %ERRORLEVEL% EQU 0 (
    echo ✅ Python 进程已终止
) else (
    echo ℹ️  没有运行中的 Python 进程
)

echo.
pause
