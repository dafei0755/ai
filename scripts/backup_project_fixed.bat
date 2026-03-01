@echo off
REM ============================================================
REM Project Auto Backup Script v2.1
REM Schedule: Daily 12:00 noon
REM ============================================================

setlocal EnableDelayedExpansion

set PROJECT_ROOT=d:\11-20\langgraph-design
set BACKUP_ROOT=%PROJECT_ROOT%\backup

for /f "tokens=*" %%a in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set TIMESTAMP=%%a

set BACKUP_DIR=%BACKUP_ROOT%\auto_backup_%TIMESTAMP%
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

echo ============================================================
echo Project Auto Backup v2.1 - %TIMESTAMP%
echo Backup dir: %BACKUP_DIR%
echo ============================================================

REM 1. Config files
echo [1/9] Backing up config files...
xcopy "%PROJECT_ROOT%\.env" "%BACKUP_DIR%\config\" /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\.env.example" "%BACKUP_DIR%\config\" /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\requirements.txt" "%BACKUP_DIR%\config\" /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\frontend-nextjs\package.json" "%BACKUP_DIR%\config\" /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\frontend-nextjs\.env.local" "%BACKUP_DIR%\config\" /Y /Q >nul 2>&1
echo    [done]

REM 2. Core docs
echo [2/9] Backing up docs...
xcopy "%PROJECT_ROOT%\README.md" "%BACKUP_DIR%\docs\" /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\CLAUDE.md" "%BACKUP_DIR%\docs\" /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\CHANGELOG.md" "%BACKUP_DIR%\docs\" /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\.github\DEVELOPMENT_RULES_CORE.md" "%BACKUP_DIR%\docs\" /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\.github\DEVELOPMENT_RULES.md" "%BACKUP_DIR%\docs\" /Y /Q >nul 2>&1
echo    [done]

REM 3. Analyzer config
echo [3/9] Backing up analyzer config...
xcopy "%PROJECT_ROOT%\intelligent_project_analyzer\config" "%BACKUP_DIR%\config\analyzer\" /E /I /Y /Q >nul 2>&1
echo    [done]

REM 4. Python modules
echo [4/9] Backing up Python modules...
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
echo    [done]

REM 5. Frontend
echo [5/9] Backing up frontend...
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
echo    [done]

REM 6. Data
echo [6/9] Backing up data...
if exist "%PROJECT_ROOT%\data" (
    if exist "%PROJECT_ROOT%\scripts\backup_exclude.txt" (
        xcopy "%PROJECT_ROOT%\data" "%BACKUP_DIR%\data\" /E /I /Y /Q /EXCLUDE:%PROJECT_ROOT%\scripts\backup_exclude.txt >nul 2>&1
    ) else (
        xcopy "%PROJECT_ROOT%\data" "%BACKUP_DIR%\data\" /E /I /Y /Q >nul 2>&1
    )
)
echo    [done]

REM 7. Git snapshots (fast part only)
echo [7/9] Git snapshot...
cd /d "%PROJECT_ROOT%"
git diff HEAD > "%BACKUP_DIR%\git_diff.patch" 2>nul
git log -10 --oneline > "%BACKUP_DIR%\git_log.txt" 2>nul
git status > "%BACKUP_DIR%\git_status.txt" 2>nul
git rev-parse HEAD > "%BACKUP_DIR%\git_current_commit.txt" 2>nul
git branch --show-current > "%BACKUP_DIR%\git_current_branch.txt" 2>nul
git tag > "%BACKUP_DIR%\git_tags.txt" 2>nul
echo    [done]

REM 8. Metadata
echo [8/9] Writing metadata...
for /f "delims=" %%i in ('git rev-parse HEAD 2^>nul') do set GIT_COMMIT=%%i
for /f "delims=" %%i in ('git branch --show-current 2^>nul') do set GIT_BRANCH=%%i
set HAS_BUNDLE=false
if exist "%BACKUP_DIR%\repo.bundle" set HAS_BUNDLE=true

echo Backup: auto_backup_%TIMESTAMP% > "%BACKUP_DIR%\BACKUP_INFO.txt"
echo Time: %TIMESTAMP% >> "%BACKUP_DIR%\BACKUP_INFO.txt"
echo Git: %GIT_COMMIT% (%GIT_BRANCH%) >> "%BACKUP_DIR%\BACKUP_INFO.txt"
echo Contents: config, docs, python, frontend, data, git >> "%BACKUP_DIR%\BACKUP_INFO.txt"

(
    echo {
    echo   "backup_time": "%TIMESTAMP%",
    echo   "backup_dirname": "auto_backup_%TIMESTAMP%",
    echo   "git_commit": "%GIT_COMMIT%",
    echo   "git_branch": "%GIT_BRANCH%",
    echo   "has_bundle": %HAS_BUNDLE%,
    echo   "backup_version": "2.1"
    echo }
) > "%BACKUP_DIR%\version_metadata.json"
echo    [done]

REM 9. Cleanup old backups (keep 14 days)
echo [9/9] Cleaning old backups...
forfiles /p "%BACKUP_ROOT%" /m "auto_backup_*" /d -14 /c "cmd /c if @isdir==TRUE rmdir /s /q @path" >nul 2>&1
echo    [done]

echo ============================================================
echo Backup complete: %TIMESTAMP%
echo Location: %BACKUP_DIR%
echo ============================================================

REM Log
echo %TIMESTAMP% - backup done: %BACKUP_DIR% >> "%BACKUP_ROOT%\backup_log.txt"

REM Git bundle (slow - run last, non-blocking for quick check)
echo [extra] Creating git bundle (may take a while)...
git bundle create "%BACKUP_DIR%\repo.bundle" --all >nul 2>&1
if exist "%BACKUP_DIR%\repo.bundle" (
    echo [extra] Git bundle created.
) else (
    echo [extra] Git bundle skipped.
)

endlocal
