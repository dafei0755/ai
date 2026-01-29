@echo off
REM UCPPT v7.270 测试运行脚本
REM
REM 运行所有测试套件：单元测试、集成测试、端到端测试、回归测试

echo ========================================
echo UCPPT v7.270 测试套件
echo ========================================
echo.

REM 设置 Python 路径
set PYTHONPATH=%CD%

REM 检查 pytest 是否安装
python -m pytest --version >nul 2>&1
if errorlevel 1 (
    echo [错误] pytest 未安装
    echo 请运行: pip install pytest pytest-asyncio
    pause
    exit /b 1
)

echo [信息] 开始运行测试...
echo.

REM ========================================
REM 1. 单元测试
REM ========================================
echo ========================================
echo 1. 单元测试
echo ========================================
echo.

python -m pytest tests/test_ucppt_v7270_unit.py -v --tb=short
if errorlevel 1 (
    echo.
    echo [警告] 单元测试失败
    set UNIT_TEST_FAILED=1
) else (
    echo.
    echo [成功] 单元测试通过
    set UNIT_TEST_FAILED=0
)

echo.
pause

REM ========================================
REM 2. 集成测试
REM ========================================
echo ========================================
echo 2. 集成测试
echo ========================================
echo.

python -m pytest tests/test_ucppt_v7270_integration.py -v --tb=short
if errorlevel 1 (
    echo.
    echo [警告] 集成测试失败
    set INTEGRATION_TEST_FAILED=1
) else (
    echo.
    echo [成功] 集成测试通过
    set INTEGRATION_TEST_FAILED=0
)

echo.
pause

REM ========================================
REM 3. 端到端测试（快速模式）
REM ========================================
echo ========================================
echo 3. 端到端测试 (快速模式)
echo ========================================
echo.
echo [信息] 跳过慢速测试 (使用 -m "not slow")
echo.

python -m pytest tests/test_ucppt_v7270_e2e.py -v --tb=short -m "not slow"
if errorlevel 1 (
    echo.
    echo [警告] 端到端测试失败
    set E2E_TEST_FAILED=1
) else (
    echo.
    echo [成功] 端到端测试通过
    set E2E_TEST_FAILED=0
)

echo.
pause

REM ========================================
REM 4. 回归测试
REM ========================================
echo ========================================
echo 4. 回归测试
echo ========================================
echo.

python -m pytest tests/test_ucppt_v7270_regression.py -v --tb=short
if errorlevel 1 (
    echo.
    echo [警告] 回归测试失败
    set REGRESSION_TEST_FAILED=1
) else (
    echo.
    echo [成功] 回归测试通过
    set REGRESSION_TEST_FAILED=0
)

echo.
pause

REM ========================================
REM 测试总结
REM ========================================
echo.
echo ========================================
echo 测试总结
echo ========================================
echo.

if %UNIT_TEST_FAILED%==0 (
    echo [✓] 单元测试: 通过
) else (
    echo [✗] 单元测试: 失败
)

if %INTEGRATION_TEST_FAILED%==0 (
    echo [✓] 集成测试: 通过
) else (
    echo [✗] 集成测试: 失败
)

if %E2E_TEST_FAILED%==0 (
    echo [✓] 端到端测试: 通过
) else (
    echo [✗] 端到端测试: 失败
)

if %REGRESSION_TEST_FAILED%==0 (
    echo [✓] 回归测试: 通过
) else (
    echo [✗] 回归测试: 失败
)

echo.

REM 计算总体结果
set /a TOTAL_FAILED=%UNIT_TEST_FAILED%+%INTEGRATION_TEST_FAILED%+%E2E_TEST_FAILED%+%REGRESSION_TEST_FAILED%

if %TOTAL_FAILED%==0 (
    echo ========================================
    echo 🎉 所有测试通过！
    echo ========================================
    exit /b 0
) else (
    echo ========================================
    echo ⚠️  有 %TOTAL_FAILED% 个测试套件失败
    echo ========================================
    exit /b 1
)

pause
