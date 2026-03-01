@echo off
setlocal
python "%~dp0ci_doctor.py"
exit /b %ERRORLEVEL%
