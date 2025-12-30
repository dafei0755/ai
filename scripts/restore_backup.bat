@echo off
REM 项目备份还原脚本
REM 用途：从自动备份中还原项目文件

setlocal EnableDelayedExpansion

set PROJECT_ROOT=d:\11-20\langgraph-design
set BACKUP_ROOT=%PROJECT_ROOT%\backup

echo ========================================
echo 项目备份还原工具
echo ========================================
echo.

REM 列出可用的备份
echo 可用的备份：
echo.
set /a COUNT=0
for /f "delims=" %%i in ('dir /b /ad /o-d "%BACKUP_ROOT%\auto_backup_*" 2^>nul') do (
    set /a COUNT+=1
    echo !COUNT!. %%i
    set "BACKUP_!COUNT!=%%i"
)

if %COUNT%==0 (
    echo 未找到任何自动备份！
    echo.
    pause
    exit /b 1
)

echo.
set /p CHOICE="请选择要还原的备份编号 (1-%COUNT%) 或输入 0 取消: "

if "%CHOICE%"=="0" (
    echo 已取消还原。
    pause
    exit /b 0
)

if %CHOICE% LSS 1 (
    echo 无效的选择！
    pause
    exit /b 1
)

if %CHOICE% GTR %COUNT% (
    echo 无效的选择！
    pause
    exit /b 1
)

set "SELECTED_BACKUP=!BACKUP_%CHOICE%!"
set "BACKUP_DIR=%BACKUP_ROOT%\%SELECTED_BACKUP%"

echo.
echo 已选择备份: %SELECTED_BACKUP%
echo 备份路径: %BACKUP_DIR%
echo.

REM 显示备份信息
if exist "%BACKUP_DIR%\BACKUP_INFO.txt" (
    type "%BACKUP_DIR%\BACKUP_INFO.txt"
    echo.
)

echo 警告：还原将覆盖当前文件！
set /p CONFIRM="确认还原？(Y/N): "

if /i not "%CONFIRM%"=="Y" (
    echo 已取消还原。
    pause
    exit /b 0
)

echo.
echo ========================================
echo 开始还原备份...
echo ========================================
echo.

REM 1. 还原配置文件
echo [1/5] 还原配置文件...
if exist "%BACKUP_DIR%\config\.env" (
    copy /Y "%BACKUP_DIR%\config\.env" "%PROJECT_ROOT%\" >nul 2>&1
    echo   ✓ .env
)
if exist "%BACKUP_DIR%\config\requirements.txt" (
    copy /Y "%BACKUP_DIR%\config\requirements.txt" "%PROJECT_ROOT%\" >nul 2>&1
    echo   ✓ requirements.txt
)
if exist "%BACKUP_DIR%\config\package.json" (
    copy /Y "%BACKUP_DIR%\config\package.json" "%PROJECT_ROOT%\frontend-nextjs\" >nul 2>&1
    echo   ✓ package.json
)
if exist "%BACKUP_DIR%\config\.env.local" (
    copy /Y "%BACKUP_DIR%\config\.env.local" "%PROJECT_ROOT%\frontend-nextjs\" >nul 2>&1
    echo   ✓ .env.local
)

REM 2. 还原核心文档
echo [2/5] 还原核心文档...
if exist "%BACKUP_DIR%\docs\" (
    xcopy "%BACKUP_DIR%\docs\*.md" "%PROJECT_ROOT%\" /Y /Q >nul 2>&1
    xcopy "%BACKUP_DIR%\docs\DEVELOPMENT_RULES*.md" "%PROJECT_ROOT%\.github\" /Y /Q >nul 2>&1
    echo   ✓ 文档文件
)

REM 3. 还原配置目录
echo [3/5] 还原配置目录...
if exist "%BACKUP_DIR%\config\analyzer\" (
    xcopy "%BACKUP_DIR%\config\analyzer" "%PROJECT_ROOT%\intelligent_project_analyzer\config\" /E /I /Y /Q >nul 2>&1
    echo   ✓ 配置目录
)

REM 4. 还原核心模块
echo [4/5] 还原核心模块...
if exist "%BACKUP_DIR%\core\" (
    if exist "%BACKUP_DIR%\core\settings.py" (
        copy /Y "%BACKUP_DIR%\core\settings.py" "%PROJECT_ROOT%\intelligent_project_analyzer\" >nul 2>&1
    )
    if exist "%BACKUP_DIR%\core\state.py" (
        copy /Y "%BACKUP_DIR%\core\state.py" "%PROJECT_ROOT%\intelligent_project_analyzer\core\" >nul 2>&1
    )
    if exist "%BACKUP_DIR%\core\workflow_flags.py" (
        copy /Y "%BACKUP_DIR%\core\workflow_flags.py" "%PROJECT_ROOT%\intelligent_project_analyzer\core\" >nul 2>&1
    )
    if exist "%BACKUP_DIR%\core\main_workflow.py" (
        copy /Y "%BACKUP_DIR%\core\main_workflow.py" "%PROJECT_ROOT%\intelligent_project_analyzer\workflow\" >nul 2>&1
    )
    echo   ✓ 核心模块
)

REM 5. 显示 Git 差异（如果有）
echo [5/5] 检查 Git 差异...
if exist "%BACKUP_DIR%\git_diff.patch" (
    set /p APPLY_PATCH="发现 Git 差异文件，是否应用？(Y/N): "
    if /i "!APPLY_PATCH!"=="Y" (
        cd /d "%PROJECT_ROOT%"
        git apply "%BACKUP_DIR%\git_diff.patch"
        echo   ✓ Git 差异已应用
    )
)

echo.
echo ========================================
echo 还原完成！
echo ========================================
echo.
echo 建议操作：
echo 1. 检查还原的文件是否正确
echo 2. 重新安装依赖（如果 requirements.txt 或 package.json 被还原）
echo 3. 重启服务以应用更改
echo.

pause
endlocal
exit /b 0
