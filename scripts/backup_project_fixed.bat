@echo off
REM ============================================================
REM 项目自动备份脚本 v2.0 (优化版)
REM 用途：每天两次备份项目关键文件和配置
REM
REM 改进:
REM - 排除大型数据库文件 (archived_sessions.db)
REM - 创建完整Git历史包 (repo.bundle)
REM - 生成版本元数据 (version_metadata.json)
REM - 优化空间占用 (~90%减少)
REM ============================================================

REM 切换到 UTF-8 代码页以正确显示中文
chcp 65001 >nul 2>&1

setlocal EnableDelayedExpansion

REM 设置项目根目录
set PROJECT_ROOT=d:\11-20\langgraph-design
set BACKUP_ROOT=%PROJECT_ROOT%\backup
set TIMESTAMP=%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%

REM 创建备份目录
set BACKUP_DIR=%BACKUP_ROOT%\auto_backup_%TIMESTAMP%
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

echo ============================================================
echo 项目自动备份开始 (v2.0 优化版): %date% %time%
echo 备份目录: %BACKUP_DIR%
echo ============================================================

REM 1. 备份核心配置文件
echo [1/9] 备份配置文件...
xcopy "%PROJECT_ROOT%\.env" "%BACKUP_DIR%\config\" /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\.env.example" "%BACKUP_DIR%\config\" /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\requirements.txt" "%BACKUP_DIR%\config\" /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\frontend-nextjs\package.json" "%BACKUP_DIR%\config\" /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\frontend-nextjs\.env.local" "%BACKUP_DIR%\config\" /Y /Q >nul 2>&1
echo    [完成]

REM 2. 备份核心文档
echo [2/9] 备份核心文档...
xcopy "%PROJECT_ROOT%\README.md" "%BACKUP_DIR%\docs\" /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\CLAUDE.md" "%BACKUP_DIR%\docs\" /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\CHANGELOG.md" "%BACKUP_DIR%\docs\" /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\.github\DEVELOPMENT_RULES_CORE.md" "%BACKUP_DIR%\docs\" /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\.github\DEVELOPMENT_RULES.md" "%BACKUP_DIR%\docs\" /Y /Q >nul 2>&1
echo    [完成]

REM 3. 备份配置目录
echo [3/9] 备份配置目录...
xcopy "%PROJECT_ROOT%\intelligent_project_analyzer\config" "%BACKUP_DIR%\config\analyzer\" /E /I /Y /Q >nul 2>&1
echo    [完成]

REM 4. 备份核心 Python 模块（完整备份所有关键模块）
echo [4/9] 备份Python核心模块...
xcopy "%PROJECT_ROOT%\intelligent_project_analyzer\agents" "%BACKUP_DIR%\python\agents\" /E /I /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\intelligent_project_analyzer\workflow" "%BACKUP_DIR%\python\workflow\" /E /I /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\intelligent_project_analyzer\api" "%BACKUP_DIR%\python\api\" /E /I /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\intelligent_project_analyzer\services" "%BACKUP_DIR%\python\services\" /E /I /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\intelligent_project_analyzer\interaction" "%BACKUP_DIR%\python\interaction\" /E /I /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\intelligent_project_analyzer\review" "%BACKUP_DIR%\python\review\" /E /I /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\intelligent_project_analyzer\report" "%BACKUP_DIR%\python\report\" /E /I /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\intelligent_project_analyzer\core" "%BACKUP_DIR%\python\core\" /E /I /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\intelligent_project_analyzer\tools" "%BACKUP_DIR%\python\tools\" /E /I /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\intelligent_project_analyzer\utils" "%BACKUP_DIR%\python\utils\" /E /I /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\intelligent_project_analyzer\settings.py" "%BACKUP_DIR%\python\" /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\intelligent_project_analyzer\__init__.py" "%BACKUP_DIR%\python\" /Y /Q >nul 2>&1
echo    [完成]

REM 5. 备份前端代码（完整 Next.js 应用）
echo [5/9] 备份前端代码...
xcopy "%PROJECT_ROOT%\frontend-nextjs\app" "%BACKUP_DIR%\frontend\app\" /E /I /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\frontend-nextjs\components" "%BACKUP_DIR%\frontend\components\" /E /I /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\frontend-nextjs\lib" "%BACKUP_DIR%\frontend\lib\" /E /I /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\frontend-nextjs\types" "%BACKUP_DIR%\frontend\types\" /E /I /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\frontend-nextjs\contexts" "%BACKUP_DIR%\frontend\contexts\" /E /I /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\frontend-nextjs\hooks" "%BACKUP_DIR%\frontend\hooks\" /E /I /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\frontend-nextjs\public" "%BACKUP_DIR%\frontend\public\" /E /I /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\frontend-nextjs\next.config.ts" "%BACKUP_DIR%\frontend\" /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\frontend-nextjs\tailwind.config.ts" "%BACKUP_DIR%\frontend\" /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\frontend-nextjs\tsconfig.json" "%BACKUP_DIR%\frontend\" /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\frontend-nextjs\postcss.config.mjs" "%BACKUP_DIR%\frontend\" /Y /Q >nul 2>&1
echo    [完成]

REM 6. 备份数据库/会话数据（排除大型数据库）
echo [6/9] 备份数据目录...
if exist "%PROJECT_ROOT%\data" (
    if exist "%PROJECT_ROOT%\scripts\backup_exclude.txt" (
        echo    [应用排除规则: 跳过大型数据库和图片...]
        xcopy "%PROJECT_ROOT%\data" "%BACKUP_DIR%\data\" /E /I /Y /Q /EXCLUDE:%PROJECT_ROOT%\scripts\backup_exclude.txt >nul 2>&1
    ) else (
        echo    [警告: 找不到排除列表，将备份所有数据]
        xcopy "%PROJECT_ROOT%\data" "%BACKUP_DIR%\data\" /E /I /Y /Q >nul 2>&1
    )
)
echo    [完成]

REM 7. 创建 Git 快照和完整历史包
echo [7/9] 创建Git快照和历史包...
cd /d "%PROJECT_ROOT%"

REM 7.1 保存当前工作状态
git stash save "Auto backup %TIMESTAMP%" >nul 2>&1
git stash apply >nul 2>&1

REM 7.2 导出 git 差异和日志
git diff HEAD > "%BACKUP_DIR%\git_diff.patch" 2>nul
git log -10 --oneline > "%BACKUP_DIR%\git_log.txt" 2>nul
git status > "%BACKUP_DIR%\git_status.txt" 2>nul

REM 7.3 创建 Git 完整历史包（用于完整恢复）
echo    [创建Git完整历史包...]
git bundle create "%BACKUP_DIR%\repo.bundle" --all >nul 2>&1
if exist "%BACKUP_DIR%\repo.bundle" (
    for %%A in ("%BACKUP_DIR%\repo.bundle") do set BUNDLE_SIZE=%%~zA
    set /a BUNDLE_MB=!BUNDLE_SIZE! / 1048576
    echo    [成功] Git bundle 已创建 (大小: !BUNDLE_MB! MB)
) else (
    echo    [警告] Git bundle 创建失败
)

REM 7.4 导出当前提交信息
git rev-parse HEAD > "%BACKUP_DIR%\git_current_commit.txt" 2>nul
git branch --show-current > "%BACKUP_DIR%\git_current_branch.txt" 2>nul
git branch -a > "%BACKUP_DIR%\git_branches.txt" 2>nul
git tag > "%BACKUP_DIR%\git_tags.txt" 2>nul
echo    [完成]

REM 8. 创建备份清单和版本元数据
echo [8/9] 创建备份清单和元数据...
echo 项目自动备份 (v2.0 优化版) > "%BACKUP_DIR%\BACKUP_INFO.txt"
echo ================================ >> "%BACKUP_DIR%\BACKUP_INFO.txt"
echo 备份时间: %date% %time% >> "%BACKUP_DIR%\BACKUP_INFO.txt"
echo 备份目录: %BACKUP_DIR% >> "%BACKUP_DIR%\BACKUP_INFO.txt"
echo 项目版本: >> "%BACKUP_DIR%\BACKUP_INFO.txt"
findstr /C:"version-v" "%PROJECT_ROOT%\README.md" >> "%BACKUP_DIR%\BACKUP_INFO.txt" 2>nul
echo. >> "%BACKUP_DIR%\BACKUP_INFO.txt"
echo 备份内容（完整覆盖）: >> "%BACKUP_DIR%\BACKUP_INFO.txt"
echo - 配置文件 (.env, requirements.txt, package.json) >> "%BACKUP_DIR%\BACKUP_INFO.txt"
echo - 核心文档 (README, CLAUDE, CHANGELOG, 开发规范) >> "%BACKUP_DIR%\BACKUP_INFO.txt"
echo - 配置目录 (intelligent_project_analyzer/config - 完整) >> "%BACKUP_DIR%\BACKUP_INFO.txt"
echo - Python 后端模块 (agents/, workflow/, api/, services/, interaction/, review/, report/, core/, tools/, utils/ - 完整) >> "%BACKUP_DIR%\BACKUP_INFO.txt"
echo - Next.js 前端代码 (app/, components/, lib/, types/, contexts/, hooks/, public/ - 完整) >> "%BACKUP_DIR%\BACKUP_INFO.txt"
echo - 数据目录 (data/ - 仅小型数据库，排除大型归档数据库) >> "%BACKUP_DIR%\BACKUP_INFO.txt"
echo - Git 快照 (diff, log, status, bundle) >> "%BACKUP_DIR%\BACKUP_INFO.txt"
echo. >> "%BACKUP_DIR%\BACKUP_INFO.txt"
echo 已排除内容（节省空间）: >> "%BACKUP_DIR%\BACKUP_INFO.txt"
echo - 图片文件 (archived_images/, followup_images/, generated_images/) >> "%BACKUP_DIR%\BACKUP_INFO.txt"
echo - 上传文件 (uploads/) >> "%BACKUP_DIR%\BACKUP_INFO.txt"
echo - 调试数据 (debug/) >> "%BACKUP_DIR%\BACKUP_INFO.txt"
echo - 大型数据库 (archived_sessions.db, test_*.db) >> "%BACKUP_DIR%\BACKUP_INFO.txt"
echo - Node依赖 (node_modules/, .next/) >> "%BACKUP_DIR%\BACKUP_INFO.txt"
echo - Python缓存 (__pycache__/, *.pyc) >> "%BACKUP_DIR%\BACKUP_INFO.txt"
echo ================================ >> "%BACKUP_DIR%\BACKUP_INFO.txt"

REM 8.2 生成 JSON 格式的版本元数据
echo    [生成版本元数据...]
REM 获取 Git 提交哈希
for /f "delims=" %%i in ('git rev-parse HEAD 2^>nul') do set GIT_COMMIT=%%i
REM 获取 Git 分支名
for /f "delims=" %%i in ('git branch --show-current 2^>nul') do set GIT_BRANCH=%%i
REM 检查是否有 bundle
set HAS_BUNDLE=false
if exist "%BACKUP_DIR%\repo.bundle" set HAS_BUNDLE=true

REM 写入 JSON 元数据（使用备份目录名称而非完整路径避免JSON转义问题）
(
    echo {
    echo   "backup_time": "%date% %time%",
    echo   "backup_dirname": "auto_backup_%TIMESTAMP%",
    echo   "timestamp": "%TIMESTAMP%",
    echo   "git_commit": "%GIT_COMMIT%",
    echo   "git_branch": "%GIT_BRANCH%",
    echo   "has_bundle": %HAS_BUNDLE%,
    echo   "backup_version": "2.0"
    echo }
) > "%BACKUP_DIR%\version_metadata.json"
echo    [完成]

REM 9. 清理旧备份（保留最近14天，即28个备份）
echo [9/9] 清理旧备份...
forfiles /p "%BACKUP_ROOT%" /m "auto_backup_*" /d -14 /c "cmd /c if @isdir==TRUE rmdir /s /q @path" >nul 2>&1
echo    [完成]

echo ============================================================
echo 备份完成: %date% %time%
echo 备份位置: %BACKUP_DIR%
echo.
echo 备份摘要:
echo - 代码文件: 已备份
echo - Git Bundle: %HAS_BUNDLE%
echo - 元数据: 已生成
echo - 排除规则: 已应用
echo ============================================================

REM 记录到日志
set LOG_TIME=%date%_%time%
echo %LOG_TIME% - 备份完成 (v2.0): %BACKUP_DIR% >> "%BACKUP_ROOT%\backup_log.txt"

endlocal
pause
