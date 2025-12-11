@echo off
chcp 65001 >nul
echo ========================================
echo 启动 LangGraph 设计系统服务
echo ========================================

echo.
echo [1/4] 检查 Redis 服务...
redis-cli ping >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ⚠️  Redis 未运行，请先启动 Redis
    echo    运行: redis-server
) else (
    echo ✅ Redis 已连接
)

echo.
echo [2/4] 启动 API 服务器...
start "API Server" cmd /k "cd /d D:\11-20\langgraph-design && conda activate base && python -m uvicorn intelligent_project_analyzer.api.server:app --host 0.0.0.0 --port 8000"

echo.
echo [3/4] 启动 Celery Worker (可选，支持多用户并发)...
start "Celery Worker" cmd /k "cd /d D:\11-20\langgraph-design && conda activate base && celery -A intelligent_project_analyzer.services.celery_app worker --loglevel=info --concurrency=4"

echo.
echo [4/4] 等待 3 秒后启动前端（Next.js 生产版本）...
timeout /t 3 /nobreak >nul

start "Next.js Frontend" cmd /k "cd /d D:\11-20\langgraph-design\frontend-nextjs && npm run dev"

echo.
echo ========================================
echo ✅ 服务启动完成！
echo ========================================
echo.
echo API 服务器: http://0.0.0.0:8000
echo Next.js 前端: http://localhost:3000
echo Celery 监控: 运行 start_celery_flower.bat 后访问 http://localhost:5555
echo.
echo 🔥 v3.9 新特性：Celery 任务队列（多用户并发支持）
echo    - 原有 API 不变：/api/analysis/start
echo    - Celery API：/api/celery/analysis/start
echo.
echo 按任意键关闭此窗口...
pause >nul
