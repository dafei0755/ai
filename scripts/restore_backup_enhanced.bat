@echo off
REM 增强版项目备份还原脚本
REM 用途：从Git bundle完整恢复项目，包括代码、配置和依赖

chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

set PROJECT_ROOT=d:\11-20\langgraph-design
set BACKUP_ROOT=%PROJECT_ROOT%\backup

echo ========================================
echo 项目完整还原工具 v2.0
echo ========================================
echo.

REM 检查版本索引文件
if exist "%BACKUP_ROOT%\VERSION_INDEX.json" (
    echo 从版本索引加载备份列表...
    echo.
) else (
    echo 警告: 未找到VERSION_INDEX.json，使用目录扫描...
    echo.
)

REM 列出可用的备份（按时间倒序）
echo 可用的备份版本（最近10个）：
echo.
set /a COUNT=0
for /f "delims=" %%i in ('dir /b /ad /o-d "%BACKUP_ROOT%\auto_backup_*" 2^>nul') do (
    set /a COUNT+=1
    if !COUNT! LEQ 10 (
        REM 显示备份信息
        set "BACKUP_NAME=%%i"
        echo [!COUNT!] %%i

        REM 尝试显示Git提交信息
        if exist "%BACKUP_ROOT%\%%i\git_current_commit.txt" (
            for /f "delims=" %%c in ('type "%BACKUP_ROOT%\%%i\git_current_commit.txt"') do (
                echo     提交: %%c
            )
        )

        REM 显示备份时间
        if exist "%BACKUP_ROOT%\%%i\version_metadata.json" (
            findstr "backup_time" "%BACKUP_ROOT%\%%i\version_metadata.json"
        )

        echo.
        set "BACKUP_!COUNT!=%%i"
    )
)

if %COUNT%==0 (
    echo 错误: 未找到任何备份！
    echo 请先运行 backup_project.bat 创建备份。
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
    echo 错误: 无效的选择！
    pause
    exit /b 1
)

if %CHOICE% GTR %COUNT% (
    echo 错误: 无效的选择！
    pause
    exit /b 1
)

set "SELECTED_BACKUP=!BACKUP_%CHOICE%!"
set "BACKUP_DIR=%BACKUP_ROOT%\%SELECTED_BACKUP%"

echo.
echo ========================================
echo 已选择备份: %SELECTED_BACKUP%
echo ========================================
echo.

REM 显示完整备份信息
if exist "%BACKUP_DIR%\BACKUP_INFO.txt" (
    type "%BACKUP_DIR%\BACKUP_INFO.txt"
    echo.
)

echo 警告：此操作将：
echo   1. 从Git bundle完整恢复代码历史
echo   2. 覆盖当前项目文件
echo   3. 重新安装Python和Node.js依赖
echo.
set /p CONFIRM="确认执行完整还原？(Y/N): "

if /i not "%CONFIRM%"=="Y" (
    echo 已取消还原。
    pause
    exit /b 0
)

echo.
echo ========================================
echo 开始完整还原流程...
echo ========================================
echo.

REM ========================================
REM 步骤 1: 从Git bundle恢复完整历史
REM ========================================
echo [1/8] 从Git bundle恢复完整仓库历史...

if exist "%BACKUP_DIR%\repo.bundle" (
    echo   检测到Git bundle文件
    echo.

    set /p RESTORE_GIT="是否恢复Git完整历史？(Y/N): "
    if /i "!RESTORE_GIT!"=="Y" (
        REM 创建临时恢复目录
        set RESTORE_TEMP=%PROJECT_ROOT%_restored_%RANDOM%
        echo   → 创建临时目录: !RESTORE_TEMP!

        REM 从bundle克隆仓库
        echo   → 从bundle克隆仓库（包含所有分支和标签）...
        git clone "%BACKUP_DIR%\repo.bundle" "!RESTORE_TEMP!" 2>&1 | findstr /V "Cloning"

        if exist "!RESTORE_TEMP!\.git" (
            echo   ✓ Git仓库恢复成功
            echo.
            echo   提示: 完整Git历史已恢复到: !RESTORE_TEMP!
            echo   您可以手动检查该目录，然后决定是否替换当前项目。
            echo.
            set /p REPLACE_PROJECT="是否用恢复的项目替换当前项目？(Y/N): "
            if /i "!REPLACE_PROJECT!"=="Y" (
                echo   → 备份当前项目到: %PROJECT_ROOT%_old
                move "%PROJECT_ROOT%" "%PROJECT_ROOT%_old" >nul 2>&1
                move "!RESTORE_TEMP!" "%PROJECT_ROOT%" >nul 2>&1
                echo   ✓ 项目已替换
            )
        ) else (
            echo   ✗ Git bundle恢复失败
        )
    )
) else (
    echo   ✗ 未找到Git bundle文件，跳过Git历史恢复
)

echo.

REM ========================================
REM 步骤 2: 恢复配置文件
REM ========================================
echo [2/8] 恢复配置文件...

cd /d "%PROJECT_ROOT%"

if exist "%BACKUP_DIR%\config\.env" (
    copy /Y "%BACKUP_DIR%\config\.env" "%PROJECT_ROOT%\" >nul 2>&1
    echo   ✓ .env
)
if exist "%BACKUP_DIR%\config\.env.example" (
    copy /Y "%BACKUP_DIR%\config\.env.example" "%PROJECT_ROOT%\" >nul 2>&1
    echo   ✓ .env.example
)
if exist "%BACKUP_DIR%\config\requirements.txt" (
    copy /Y "%BACKUP_DIR%\config\requirements.txt" "%PROJECT_ROOT%\" >nul 2>&1
    echo   ✓ requirements.txt
)
if exist "%BACKUP_DIR%\config\package.json" (
    copy /Y "%BACKUP_DIR%\config\package.json" "%PROJECT_ROOT%\frontend-nextjs\" >nul 2>&1
    echo   ✓ frontend-nextjs\package.json
)
if exist "%BACKUP_DIR%\config\.env.local" (
    copy /Y "%BACKUP_DIR%\config\.env.local" "%PROJECT_ROOT%\frontend-nextjs\" >nul 2>&1
    echo   ✓ frontend-nextjs\.env.local
)

echo.

REM ========================================
REM 步骤 3: 恢复后端代码
REM ========================================
echo [3/8] 恢复后端Python代码...

if exist "%BACKUP_DIR%\python\" (
    xcopy "%BACKUP_DIR%\python" "%PROJECT_ROOT%\intelligent_project_analyzer\" /E /I /Y /Q >nul 2>&1
    echo   ✓ 所有Python模块已恢复
) else (
    echo   ✗ 未找到Python备份
)

echo.

REM ========================================
REM 步骤 4: 恢复前端代码
REM ========================================
echo [4/8] 恢复前端Next.js代码...

if exist "%BACKUP_DIR%\frontend\" (
    xcopy "%BACKUP_DIR%\frontend" "%PROJECT_ROOT%\frontend-nextjs\" /E /I /Y /Q >nul 2>&1
    echo   ✓ 所有前端文件已恢复
) else (
    echo   ✗ 未找到前端备份
)

echo.

REM ========================================
REM 步骤 5: 恢复配置目录
REM ========================================
echo [5/8] 恢复配置目录...

if exist "%BACKUP_DIR%\config\analyzer\" (
    xcopy "%BACKUP_DIR%\config\analyzer" "%PROJECT_ROOT%\intelligent_project_analyzer\config\" /E /I /Y /Q >nul 2>&1
    echo   ✓ intelligent_project_analyzer\config
)

echo.

REM ========================================
REM 步骤 6: 恢复数据库文件
REM ========================================
echo [6/8] 恢复数据库文件...

if exist "%BACKUP_DIR%\data\" (
    set /p RESTORE_DB="是否恢复数据库文件？(Y/N): "
    if /i "!RESTORE_DB!"=="Y" (
        xcopy "%BACKUP_DIR%\data" "%PROJECT_ROOT%\data\" /E /I /Y /Q >nul 2>&1
        echo   ✓ 数据文件已恢复
    ) else (
        echo   - 跳过数据库恢复
    )
) else (
    echo   - 未找到数据库备份
)

echo.

REM ========================================
REM 步骤 7: 重新安装依赖
REM ========================================
echo [7/8] 重新安装依赖...

set /p INSTALL_DEPS="是否自动安装Python和Node.js依赖？(Y/N): "
if /i "%INSTALL_DEPS%"=="Y" (
    echo.
    echo   → 安装Python依赖...

    REM 检查虚拟环境
    if exist "%PROJECT_ROOT%\venv\Scripts\activate.bat" (
        call "%PROJECT_ROOT%\venv\Scripts\activate.bat"
        pip install -r requirements.txt
    ) else (
        echo   警告: 未找到虚拟环境，使用全局Python
        pip install -r requirements.txt
    )

    echo.
    echo   → 安装Node.js依赖...
    cd /d "%PROJECT_ROOT%\frontend-nextjs"
    call npm install

    cd /d "%PROJECT_ROOT%"
    echo   ✓ 依赖安装完成
) else (
    echo   - 跳过依赖安装
)

echo.

REM ========================================
REM 步骤 8: 应用Git差异（可选）
REM ========================================
echo [8/8] 检查Git差异...

if exist "%BACKUP_DIR%\git_diff.patch" (
    set /p APPLY_PATCH="发现Git差异文件，是否应用？(Y/N): "
    if /i "!APPLY_PATCH!"=="Y" (
        cd /d "%PROJECT_ROOT%"
        git apply "%BACKUP_DIR%\git_diff.patch" 2>&1
        if !ERRORLEVEL! EQU 0 (
            echo   ✓ Git差异已应用
        ) else (
            echo   ✗ Git差异应用失败（可能已经包含在代码中）
        )
    )
) else (
    echo   - 无Git差异需要应用
)

echo.
echo ========================================
echo 还原完成！
echo ========================================
echo.

REM 显示Git状态
if exist "%BACKUP_DIR%\git_branches.txt" (
    echo 原始Git分支：
    type "%BACKUP_DIR%\git_branches.txt" | findstr /V "^$"
    echo.
)

echo 后续操作建议：
echo.
echo 1. 验证还原的文件是否正确
echo    → cd %PROJECT_ROOT%
echo    → git status
echo.
echo 2. 检查配置文件
echo    → .env 文件
echo    → frontend-nextjs\.env.local
echo.
echo 3. 启动服务测试
echo    → start_backend_enhanced.bat
echo    → cd frontend-nextjs ^&^& npm run dev
echo.
echo 4. 如果Git历史已恢复，检查分支和提交
echo    → git log -10
echo    → git branch -a
echo.

pause
endlocal
exit /b 0
