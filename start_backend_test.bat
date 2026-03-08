@echo off
REM 测试环境启动脚本 - 后端服务
REM 使用端口 8100（避免与开发环境8000冲突）

chcp 65001 >nul
set PYTHONIOENCODING=utf-8

cd /d %~dp0

echo.
echo ========================================
echo   启动测试环境 - 后端服务
echo ========================================
echo.

REM 调用统一启动脚本
call .venv\Scripts\python.exe scripts\start_service.py --env test --service backend

pause
