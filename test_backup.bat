@echo off
chcp 65001 >nul 2>&1
echo ========================================
echo 测试备份系统优化
echo ========================================
echo.
echo 正在运行备份...
echo.
call scripts\backup_project.bat
echo.
echo ========================================
echo 验证备份结果...
echo ========================================
echo.
python scripts\verify_backup_optimization.py
pause
