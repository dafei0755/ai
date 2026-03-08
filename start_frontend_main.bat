@echo off
chcp 65001 >nul
cd /d %~dp0frontend-nextjs
set NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
set NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
call npm run dev -- -p 3001
