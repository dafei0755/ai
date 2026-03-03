@echo off
REM 测试环境启动脚本 - 全套服务
REM 后端: 8100, 前端: 3101

chcp 65001 >nul
set PYTHONIOENCODING=utf-8

cd /d %~dp0

echo.
echo ============================================================
echo   启动测试环境 - 全套服务（后端 8100, 前端 3101）
echo ============================================================
echo.
echo   开发环境（8000/3001）将继续运行，互不干扰
echo   按 Ctrl+C 可停止测试环境
echo.
echo ============================================================
echo.

REM 调用统一启动脚本（将在后台启动后端，前台启动前端）
call .venv\Scripts\python.exe scripts\start_service.py --env test --service all

pause
