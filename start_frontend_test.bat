@echo off
REM 测试环境启动脚本 - 前端服务
REM 使用端口 3101（避免与开发环境3001冲突）

chcp 65001 >nul

cd /d %~dp0

echo.
echo ========================================
echo   启动测试环境 - 前端服务
echo ========================================
echo.

REM 调用统一启动脚本
call .venv\Scripts\python.exe scripts\start_service.py --env test --service frontend

pause
