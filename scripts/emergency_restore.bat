@echo off
REM 紧急恢复工具 - 快速恢复到历史版本
chcp 65001 >nul 2>&1

echo ========================================
echo 紧急历史版本恢复工具
echo ========================================
echo.

REM 显示最近的可用版本
echo 可用的历史版本（最近15个提交）:
echo.
git log --oneline -15 --pretty=format:"%%h - %%s (%%ar)"
echo.
echo.

REM 显示当前状态
echo ----------------------------------------
echo 当前状态:
echo ----------------------------------------
git log -1 --pretty=format:"当前版本: %%h - %%s%%n提交时间: %%ar%%n"
echo.
echo.

REM 显示可用的备份
echo ----------------------------------------
echo 可用的备份（最近5个）:
echo ----------------------------------------
dir /b /ad /o-d backup\auto_backup_* 2>nul | findstr /n "^" | findstr "^[1-5]:"
echo.

echo ========================================
echo 选择恢复方式:
echo ========================================
echo.
echo [1] 从Git恢复到指定提交（推荐）
echo [2] 从本地备份恢复完整项目
echo [3] 仅查看历史，不恢复
echo [0] 取消退出
echo.

set /p CHOICE="请选择 (0-3): "

if "%CHOICE%"=="0" (
    echo 已取消。
    pause
    exit /b 0
)

if "%CHOICE%"=="1" (
    goto :GIT_RESTORE
)

if "%CHOICE%"=="2" (
    goto :BACKUP_RESTORE
)

if "%CHOICE%"=="3" (
    goto :VIEW_ONLY
)

echo 无效选择！
pause
exit /b 1

:GIT_RESTORE
echo.
echo ========================================
echo Git 恢复模式
echo ========================================
echo.
set /p COMMIT_HASH="输入要恢复的提交hash (例如: 86fa933): "

if "%COMMIT_HASH%"=="" (
    echo 错误: 未输入提交hash
    pause
    exit /b 1
)

echo.
echo 警告: 这将恢复到版本 %COMMIT_HASH%
echo.
echo 选择恢复方式:
echo [1] 软恢复（创建新分支，保留当前版本）- 推荐
echo [2] 硬恢复（直接覆盖当前版本）- 危险！
echo [0] 取消
echo.

set /p RESTORE_TYPE="请选择 (0-2): "

if "%RESTORE_TYPE%"=="0" (
    echo 已取消。
    pause
    exit /b 0
)

if "%RESTORE_TYPE%"=="1" (
    REM 创建恢复分支
    set BRANCH_NAME=recovery-%date:~0,4%%date:~5,2%%date:~8,2%-%time:~0,2%%time:~3,2%
    set BRANCH_NAME=%BRANCH_NAME: =0%

    echo.
    echo 创建恢复分支: %BRANCH_NAME%
    git checkout -b %BRANCH_NAME% %COMMIT_HASH%

    if !ERRORLEVEL! EQU 0 (
        echo.
        echo ✓ 成功恢复到版本 %COMMIT_HASH%
        echo ✓ 当前分支: %BRANCH_NAME%
        echo.
        echo 建议操作:
        echo 1. 测试这个版本是否正常
        echo 2. 如果满意，执行: git checkout main ^&^& git merge %BRANCH_NAME%
        echo 3. 如果不满意，执行: git checkout main ^&^& git branch -D %BRANCH_NAME%
    ) else (
        echo.
        echo ✗ 恢复失败！请检查提交hash是否正确。
    )
    pause
    exit /b 0
)

if "%RESTORE_TYPE%"=="2" (
    echo.
    echo ⚠️  警告: 硬恢复将丢失当前未提交的更改！
    echo.
    set /p CONFIRM="确定要硬恢复吗？(输入 YES 确认): "

    if not "%CONFIRM%"=="YES" (
        echo 已取消。
        pause
        exit /b 0
    )

    echo.
    echo 执行硬恢复...
    git reset --hard %COMMIT_HASH%

    if !ERRORLEVEL! EQU 0 (
        echo.
        echo ✓ 已强制恢复到版本 %COMMIT_HASH%
        echo.
        echo 后续操作:
        echo 1. 重新安装依赖: pip install -r requirements.txt
        echo 2. 前端依赖: cd frontend-nextjs ^&^& npm install
        echo 3. 重启服务测试
    ) else (
        echo.
        echo ✗ 恢复失败！
    )
    pause
    exit /b 0
)

echo 无效选择！
pause
exit /b 1

:BACKUP_RESTORE
echo.
echo ========================================
echo 从本地备份恢复
echo ========================================
echo.
echo 调用增强版恢复脚本...
echo.
pause
call scripts\restore_backup_enhanced.bat
exit /b 0

:VIEW_ONLY
echo.
echo ========================================
echo 详细历史查看
echo ========================================
echo.
git log -20 --pretty=format:"%%C(yellow)%%h%%Creset - %%s %%C(green)(%%ar)%%Creset %%C(blue)%%an%%Creset" --graph
echo.
echo.
echo ========================================
echo.
pause
exit /b 0
