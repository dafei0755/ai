@echo off
REM 雷达图智能维度生成测试脚本（Windows版）
REM v7.106

echo 🧪 雷达图智能维度生成器测试套件
echo ================================
echo.

REM 运行快速测试（不包含LLM调用）
echo 📋 1. 运行快速单元测试（跳过LLM）...
pytest tests/test_dynamic_dimension_generator_v105.py -v -m "not llm"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ 快速测试全部通过！
    echo.

    REM 询问是否运行LLM测试
    set /p RUN_LLM="是否运行LLM集成测试？这需要OpenAI API Key并会产生少量费用（y/n）: "

    if /i "%RUN_LLM%"=="y" (
        echo 🤖 2. 运行LLM集成测试...
        pytest tests/test_dynamic_dimension_generator_v105.py -v -m "llm"

        if %ERRORLEVEL% EQU 0 (
            echo.
            echo ✅ 所有测试全部通过！
        ) else (
            echo.
            echo ❌ LLM测试失败，请检查：
            echo    1. OPENAI_API_KEY 是否已配置
            echo    2. 网络连接是否正常
            echo    3. API额度是否充足
        )
    ) else (
        echo ⏭️  跳过LLM测试
    )
) else (
    echo.
    echo ❌ 快速测试失败，请检查代码
)

echo.
echo ================================
echo 测试完成
pause
