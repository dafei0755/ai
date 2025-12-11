@echo off
chcp 65001 > nul
echo.
echo =============================================
echo   🌸 启动 Flower 监控面板
echo =============================================
echo.

REM 切换到项目目录
cd /d %~dp0

REM 激活虚拟环境（如果有）
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

echo 📌 启动 Flower (Celery 监控面板)...
echo    访问地址: http://localhost:5555
echo.
echo ⚠️  按 Ctrl+C 停止
echo.

REM 启动 Flower
celery -A intelligent_project_analyzer.services.celery_app flower ^
    --port=5555 ^
    --broker=redis://localhost:6379/0

pause
