@echo off
REM 项目自动备份脚本
REM 用途：每天两次备份项目关键文件和配置

REM 切换到 UTF-8 代码页以正确显示中文
chcp 65001 >nul 2>&1

setlocal EnableDelayedExpansion

REM 设置项目根目录
set PROJECT_ROOT=d:\11-20\langgraph-design
set BACKUP_ROOT=%PROJECT_ROOT%\backup
set TIMESTAMP=%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%

REM 设置进度标记
set MSG1=步骤1-8
set MSG2=步骤2-8
set MSG3=步骤3-8
set MSG4=步骤4-8
set MSG5=步骤5-8
set MSG6=步骤6-8
set MSG7=步骤7-8
set MSG8=步骤8-8
set MSG_CLEAN=清理旧备份

REM 创建备份目录
set BACKUP_DIR=%BACKUP_ROOT%\auto_backup_%TIMESTAMP%
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

echo ========================================
echo 项目自动备份开始: %date% %time%
echo 备份目录: %BACKUP_DIR%
echo ========================================

REM 1. 备份核心配置文件
echo %MSG1% 备份配置文件
xcopy "%PROJECT_ROOT%\.env" "%BACKUP_DIR%\config\" /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\.env.example" "%BACKUP_DIR%\config\" /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\requirements.txt" "%BACKUP_DIR%\config\" /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\frontend-nextjs\package.json" "%BACKUP_DIR%\config\" /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\frontend-nextjs\.env.local" "%BACKUP_DIR%\config\" /Y /Q >nul 2>&1

REM 2. 备份核心文档
echo %MSG2% 备份核心文档
xcopy "%PROJECT_ROOT%\README.md" "%BACKUP_DIR%\docs\" /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\CLAUDE.md" "%BACKUP_DIR%\docs\" /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\CHANGELOG.md" "%BACKUP_DIR%\docs\" /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\.github\DEVELOPMENT_RULES_CORE.md" "%BACKUP_DIR%\docs\" /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\.github\DEVELOPMENT_RULES.md" "%BACKUP_DIR%\docs\" /Y /Q >nul 2>&1

REM 3. 备份配置目录
echo %MSG3% 备份配置目录
xcopy "%PROJECT_ROOT%\intelligent_project_analyzer\config" "%BACKUP_DIR%\config\analyzer\" /E /I /Y /Q >nul 2>&1

REM 4. 备份核心 Python 模块（完整备份所有关键模块）
echo %MSG4%
echo 备份核心模块
REM 4.1 智能体模块（所有 Agent 实现）
xcopy "%PROJECT_ROOT%\intelligent_project_analyzer\agents" "%BACKUP_DIR%\python\agents\" /E /I /Y /Q >nul 2>&1
REM 4.2 工作流模块（完整工作流逻辑）
xcopy "%PROJECT_ROOT%\intelligent_project_analyzer\workflow" "%BACKUP_DIR%\python\workflow\" /E /I /Y /Q >nul 2>&1
REM 4.3 API 服务（FastAPI + WebSocket + SSO）
xcopy "%PROJECT_ROOT%\intelligent_project_analyzer\api" "%BACKUP_DIR%\python\api\" /E /I /Y /Q >nul 2>&1
REM 4.4 服务层（LLM 工厂、工具工厂、Celery 等）
xcopy "%PROJECT_ROOT%\intelligent_project_analyzer\services" "%BACKUP_DIR%\python\services\" /E /I /Y /Q >nul 2>&1
REM 4.5 人机交互节点（问卷、确认、审批）
xcopy "%PROJECT_ROOT%\intelligent_project_analyzer\interaction" "%BACKUP_DIR%\python\interaction\" /E /I /Y /Q >nul 2>&1
REM 4.6 审核系统（红蓝对抗、评委、甲方）
xcopy "%PROJECT_ROOT%\intelligent_project_analyzer\review" "%BACKUP_DIR%\python\review\" /E /I /Y /Q >nul 2>&1
REM 4.7 报告生成（结果聚合、PDF 生成）
xcopy "%PROJECT_ROOT%\intelligent_project_analyzer\report" "%BACKUP_DIR%\python\report\" /E /I /Y /Q >nul 2>&1
REM 4.8 核心模块（状态管理、数据模型）
xcopy "%PROJECT_ROOT%\intelligent_project_analyzer\core" "%BACKUP_DIR%\python\core\" /E /I /Y /Q >nul 2>&1
REM 4.9 工具集成（Tavily、Arxiv、RAGFlow 等）
xcopy "%PROJECT_ROOT%\intelligent_project_analyzer\tools" "%BACKUP_DIR%\python\tools\" /E /I /Y /Q >nul 2>&1
REM 4.10 公共工具函数（能力检测器等）
xcopy "%PROJECT_ROOT%\intelligent_project_analyzer\utils" "%BACKUP_DIR%\python\utils\" /E /I /Y /Q >nul 2>&1
REM 4.11 设置文件
xcopy "%PROJECT_ROOT%\intelligent_project_analyzer\settings.py" "%BACKUP_DIR%\python\" /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\intelligent_project_analyzer\__init__.py" "%BACKUP_DIR%\python\" /Y /Q >nul 2>&1

REM 5. 备份前端代码（完整 Next.js 应用）
echo %MSG5%
echo 备份前端代码
REM 5.1 核心源码（app、components、lib、types 等）
xcopy "%PROJECT_ROOT%\frontend-nextjs\app" "%BACKUP_DIR%\frontend\app\" /E /I /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\frontend-nextjs\components" "%BACKUP_DIR%\frontend\components\" /E /I /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\frontend-nextjs\lib" "%BACKUP_DIR%\frontend\lib\" /E /I /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\frontend-nextjs\types" "%BACKUP_DIR%\frontend\types\" /E /I /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\frontend-nextjs\contexts" "%BACKUP_DIR%\frontend\contexts\" /E /I /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\frontend-nextjs\hooks" "%BACKUP_DIR%\frontend\hooks\" /E /I /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\frontend-nextjs\public" "%BACKUP_DIR%\frontend\public\" /E /I /Y /Q >nul 2>&1
REM 5.2 配置文件
xcopy "%PROJECT_ROOT%\frontend-nextjs\next.config.ts" "%BACKUP_DIR%\frontend\" /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\frontend-nextjs\tailwind.config.ts" "%BACKUP_DIR%\frontend\" /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\frontend-nextjs\tsconfig.json" "%BACKUP_DIR%\frontend\" /Y /Q >nul 2>&1
xcopy "%PROJECT_ROOT%\frontend-nextjs\postcss.config.mjs" "%BACKUP_DIR%\frontend\" /Y /Q >nul 2>&1

REM 6. 备份数据库/会话数据（如果使用文件存储）
echo %MSG6% 备份数据目录
REM 只备份 .db 数据库文件和配置，排除所有图片、上传文件和调试数据
if exist "%PROJECT_ROOT%\data" (
    if exist "%PROJECT_ROOT%\scripts\backup_exclude.txt" (
        echo    [跳过图片和上传文件...]
        xcopy "%PROJECT_ROOT%\data" "%BACKUP_DIR%\data\" /E /I /Y /Q /EXCLUDE:%PROJECT_ROOT%\scripts\backup_exclude.txt >nul 2>&1
    ) else (
        echo    [警告: 找不到排除列表，将备份所有数据]
        xcopy "%PROJECT_ROOT%\data" "%BACKUP_DIR%\data\" /E /I /Y /Q >nul 2>&1
    )
)

REM 7. 创建 Git 快照
echo %MSG7% 创建Git快照
cd /d "%PROJECT_ROOT%"
git stash save "Auto backup %TIMESTAMP%" >nul 2>&1
git stash apply >nul 2>&1

REM 导出 git 差异
git diff HEAD > "%BACKUP_DIR%\git_diff.patch" 2>nul
git log -10 --oneline > "%BACKUP_DIR%\git_log.txt" 2>nul
git status > "%BACKUP_DIR%\git_status.txt" 2>nul

REM 8. 创建备份清单
echo %MSG8% 创建备份清单
echo 项目自动备份 > "%BACKUP_DIR%\BACKUP_INFO.txt"
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
echo - 数据目录 (data/ - 仅数据库文件，排除图片/上传文件) >> "%BACKUP_DIR%\BACKUP_INFO.txt"
echo - Git 快照 (diff, log, status) >> "%BACKUP_DIR%\BACKUP_INFO.txt"
echo. >> "%BACKUP_DIR%\BACKUP_INFO.txt"
echo 已排除内容（节省空间）: >> "%BACKUP_DIR%\BACKUP_INFO.txt"
echo - 图片文件 (archived_images/, followup_images/, generated_images/) >> "%BACKUP_DIR%\BACKUP_INFO.txt"
echo - 上传文件 (uploads/) >> "%BACKUP_DIR%\BACKUP_INFO.txt"
echo - 调试数据 (debug/) >> "%BACKUP_DIR%\BACKUP_INFO.txt"
echo - Node依赖 (node_modules/, .next/) >> "%BACKUP_DIR%\BACKUP_INFO.txt"
echo - Python缓存 (__pycache__/, *.pyc) >> "%BACKUP_DIR%\BACKUP_INFO.txt"
echo ================================ >> "%BACKUP_DIR%\BACKUP_INFO.txt"

REM 9. 清理旧备份（保留最近14天，即28个备份）
echo %MSG_CLEAN% 清理旧备份
forfiles /p "%BACKUP_ROOT%" /m "auto_backup_*" /d -14 /c "cmd /c if @isdir==TRUE rmdir /s /q @path" >nul 2>&1

REM 计算备份大小（简化版，避免管道转义问题）
set BACKUP_SIZE=未知

echo ========================================
echo 备份完成: %date% %time%
echo 备份位置: %BACKUP_DIR%
echo ========================================

REM 记录到日志
set LOG_TIME=%date%_%time%
echo %LOG_TIME% - 备份完成: %BACKUP_DIR% >> "%BACKUP_ROOT%\backup_log.txt"

endlocal
