@echo off
REM Windows 启动脚本 - Python 3.13 兼容版
REM 使用 run_server.py 包装器启动，确保事件循环策略在 uvicorn 之前设置

echo ================================================
echo  启动 Intelligent Project Analyzer 后端服务
echo  Python 3.13+ Windows 兼容模式
echo ================================================
echo.

cd /d "%~dp0.."
python -B scripts\run_server.py

pause
