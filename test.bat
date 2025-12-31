@echo off
REM 测试自动化批处理脚本 - Windows版本

if "%1"=="" goto help
if "%1"=="help" goto help
if "%1"=="test" goto test
if "%1"=="test-fast" goto test-fast
if "%1"=="test-coverage" goto test-coverage
if "%1"=="test-agents" goto test-agents
if "%1"=="test-workflow" goto test-workflow
if "%1"=="test-interaction" goto test-interaction
if "%1"=="test-security" goto test-security
if "%1"=="check" goto check
if "%1"=="report" goto report
if "%1"=="clean" goto clean
if "%1"=="install" goto install

:help
echo.
echo 可用的测试命令:
echo   test.bat test              - 运行所有测试
echo   test.bat test-fast         - 快速测试(跳过慢速测试)
echo   test.bat test-coverage     - 运行覆盖率测试
echo   test.bat test-agents       - Agents模块测试
echo   test.bat test-workflow     - Workflow模块测试
echo   test.bat test-interaction  - Interaction模块测试
echo   test.bat test-security     - Security模块测试
echo   test.bat check             - 检查测试前置条件
echo   test.bat report            - 生成测试报告
echo   test.bat clean             - 清理测试文件
echo   test.bat install           - 安装测试依赖
echo.
goto end

:test
echo 🚀 运行所有测试...
python -m pytest tests/ -v
goto end

:test-fast
echo ⚡ 运行快速测试...
python -m pytest tests/ -m "not slow" -v --tb=line
goto end

:test-coverage
echo 📊 运行覆盖率测试...
python -m pytest tests/ --cov=intelligent_project_analyzer --cov-report=html --cov-report=term-missing --cov-report=json --cov-fail-under=14
echo.
echo 📁 HTML报告: htmlcov\index.html
goto end

:test-agents
echo 🤖 运行Agents模块测试...
python -m pytest tests/agents/ -v
goto end

:test-workflow
echo 🔄 运行Workflow模块测试...
python -m pytest tests/workflow/ -v
goto end

:test-interaction
echo 💬 运行Interaction模块测试...
python -m pytest tests/interaction/ -v
goto end

:test-security
echo 🔒 运行Security模块测试...
python -m pytest tests/security/ -v
goto end

:check
echo 🔍 检查测试环境...
python scripts/test_automation.py --check
goto end

:report
echo 📄 生成测试报告...
python scripts/test_automation.py --report
goto end

:clean
echo 🧹 清理测试文件...
if exist htmlcov rmdir /s /q htmlcov
if exist .pytest_cache rmdir /s /q .pytest_cache
if exist .coverage del /q .coverage
if exist coverage.xml del /q coverage.xml
if exist coverage.json del /q coverage.json
if exist test_reports rmdir /s /q test_reports
for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"
del /s /q *.pyc 2>nul
echo ✅ 清理完成
goto end

:install
echo 📦 安装测试依赖...
pip install -r requirements.txt
pip install pytest pytest-cov pytest-asyncio pytest-benchmark
echo ✅ 依赖安装完成
goto end

:end
