@echo off
REM ============================================================
REM 会话历史清理脚本 - Windows批处理启动器
REM 用途：快速清理系统中的异常会话数据
REM ============================================================

chcp 65001 >nul 2>&1
setlocal

set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
set CLEANUP_SCRIPT=%PROJECT_ROOT%\scripts\cleanup_session_history.py

echo ============================================================
echo 会话历史清理工具
echo ============================================================
echo.

REM 检查Python脚本是否存在
if not exist "%CLEANUP_SCRIPT%" (
    echo ✗ 错误: 找不到清理脚本
    echo    路径: %CLEANUP_SCRIPT%
    pause
    exit /b 1
)

REM 显示菜单
echo 请选择操作模式:
echo.
echo   [1] 仅扫描（推荐首次使用）- 查看异常会话但不删除
echo   [2] 交互式清理 - 扫描后询问确认
echo   [3] 自动清理 - 直接删除所有异常会话（慎用！）
echo   [0] 退出
echo.

set /p CHOICE="请输入选项 [0-3]: "

if "%CHOICE%"=="0" (
    echo.
    echo 已取消
    goto :END
)

if "%CHOICE%"=="1" (
    echo.
    echo 执行模式: 仅扫描（不删除）
    echo ============================================================
    echo.
    python "%CLEANUP_SCRIPT%" --dry-run
    goto :DONE
)

if "%CHOICE%"=="2" (
    echo.
    echo 执行模式: 交互式清理
    echo ============================================================
    echo.
    python "%CLEANUP_SCRIPT%"
    goto :DONE
)

if "%CHOICE%"=="3" (
    echo.
    echo ⚠️  警告: 即将自动删除所有异常会话！
    echo.
    set /p CONFIRM="确认继续？[y/N]: "

    if /i not "%CONFIRM%"=="y" (
        echo.
        echo 已取消
        goto :END
    )

    echo.
    echo 执行模式: 自动清理
    echo ============================================================
    echo.
    python "%CLEANUP_SCRIPT%" --auto-confirm
    goto :DONE
)

echo.
echo ✗ 无效选项: %CHOICE%
goto :END

:DONE
echo.
echo ============================================================
echo 清理完成
echo ============================================================

:END
echo.
pause
endlocal
