@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set DEBUG=
cd /d %~dp0
call .venv\Scripts\python.exe scripts\run_server_production.py
