@echo off
chcp 65001 > nul
echo.
echo =============================================
echo   🚀 启动 Celery Worker
echo =============================================
echo.

REM 检查 Redis 是否运行
echo 📌 检查 Redis 服务...
redis-cli ping > nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ❌ Redis 未运行！请先启动 Redis 服务
    echo    运行: redis-server
    pause
    exit /b 1
)
echo ✅ Redis 已连接

echo.
echo 📌 启动 Celery Worker...
echo    队列: analysis, report, default
echo    并发: 4
echo.
echo ⚠️  按 Ctrl+C 停止 Worker
echo.

REM 切换到项目目录
cd /d %~dp0

REM 激活虚拟环境（如果有）
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM 启动 Celery Worker
celery -A intelligent_project_analyzer.services.celery_app worker ^
    --loglevel=info ^
    --concurrency=4 ^
    --queues=analysis,report,default ^
    --hostname=worker@%%h

pause
