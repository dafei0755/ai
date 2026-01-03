@echo off
chcp 65001 > nul
echo ====================================
echo 问卷第一步完整重启和测试流程
echo ====================================
echo.

echo [1/5] 停止所有Python进程...
taskkill /F /IM python.exe 2>nul
if %errorlevel%==0 (
    echo    ✅ Python进程已停止
    timeout /t 2 /nobreak >nul
) else (
    echo    ⚠️ 没有运行中的Python进程
)
echo.

echo [2/5] 清除Python缓存...
powershell -Command "Get-ChildItem -Path 'intelligent_project_analyzer' -Recurse -Include '__pycache__' | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue"
powershell -Command "Get-ChildItem -Path 'intelligent_project_analyzer' -Recurse -Filter '*.pyc' | Remove-Item -Force -ErrorAction SilentlyContinue"
echo    ✅ Python缓存已清除
echo.

echo [3/5] 启动后端服务器...
cd /d "%~dp0.."
start "后端服务器" cmd /k "python -B scripts\run_server_production.py"
echo    ⏳ 等待服务器启动...
timeout /t 5 /nobreak >nul
echo    ✅ 后端服务器已启动
echo.

echo [4/5] 运行集成测试...
python test_questionnaire_step1.py 2>nul
if %errorlevel%==0 (
    echo    ✅ 测试通过！
) else (
    echo    ⚠️ 测试失败，请查看详细日志
    echo.
    echo 运行以下命令查看详细信息：
    echo    python test_questionnaire_step1.py
    pause
    exit /b 1
)
echo.

echo [5/5] 验证服务器健康状态...
curl -s http://127.0.0.1:8000/health >nul 2>&1
if %errorlevel%==0 (
    echo    ✅ 后端健康检查通过
) else (
    echo    ⚠️ 后端健康检查失败
    echo    请等待几秒后手动访问: http://127.0.0.1:8000/health
)
echo.

echo ====================================
echo ✅ 重启和测试完成！
echo ====================================
echo.
echo 下一步操作：
echo 1. 启动前端: cd frontend-nextjs ^&^& npm run dev
echo 2. 访问系统: http://localhost:3000
echo 3. 测试问卷第一步的动机识别功能
echo.
echo 如果问题仍存在，运行以下命令查看详细日志：
echo    Get-Content logs\server.log -Wait -Tail 50 -Encoding UTF8
echo.
pause
