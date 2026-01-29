@echo off
REM 测试备份优化脚本
chcp 65001 >nul 2>&1

echo ========================================
echo 测试备份系统优化
echo ========================================
echo.

echo [1/4] 运行优化后的备份脚本...
call scripts\backup_project.bat
echo.

echo [2/4] 检查最新备份目录...
for /f "delims=" %%i in ('dir /b /ad /o-d backup\auto_backup_* 2^>nul ^| findstr /n "^" ^| findstr "^1:"') do (
    set LATEST_BACKUP=%%i
)
set LATEST_BACKUP=%LATEST_BACKUP:~2%
echo 最新备份: %LATEST_BACKUP%
echo.

echo [3/4] 验证Git bundle是否存在...
if exist "backup\%LATEST_BACKUP%\repo.bundle" (
    echo [✓] Git bundle 已创建
    for %%A in ("backup\%LATEST_BACKUP%\repo.bundle") do echo    大小: %%~zA 字节
) else (
    echo [✗] Git bundle 未找到
)
echo.

echo [4/4] 验证其他Git文件...
if exist "backup\%LATEST_BACKUP%\git_current_commit.txt" (
    echo [✓] git_current_commit.txt 已创建
) else (
    echo [✗] git_current_commit.txt 未找到
)

if exist "backup\%LATEST_BACKUP%\git_current_branch.txt" (
    echo [✓] git_current_branch.txt 已创建
) else (
    echo [✗] git_current_branch.txt 未找到
)

if exist "backup\%LATEST_BACKUP%\git_branches.txt" (
    echo [✓] git_branches.txt 已创建
) else (
    echo [✗] git_branches.txt 未找到
)

if exist "backup\%LATEST_BACKUP%\git_tags.txt" (
    echo [✓] git_tags.txt 已创建
) else (
    echo [✗] git_tags.txt 未找到
)
echo.

echo ========================================
echo 测试完成
echo ========================================
pause
