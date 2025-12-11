@echo off
chcp 65001 >nul
echo ========================================
echo   Next.js 前端快速启动
echo ========================================
echo.

REM 检查 Node.js
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误: 未找到 Node.js
    echo 请先安装 Node.js: https://nodejs.org/
    pause
    exit /b 1
)

echo ✅ Node.js 版本:
node --version
echo.

REM 检查是否已安装依赖
if not exist "node_modules" (
    echo 📦 首次运行，正在安装依赖...
    echo 这可能需要 2-5 分钟，请耐心等待...
    echo.
    call npm install
    if %errorlevel% neq 0 (
        echo.
        echo ❌ 依赖安装失败
        echo 请尝试手动运行: npm install
        pause
        exit /b 1
    )
    echo.
    echo ✅ 依赖安装完成
    echo.
)

echo 🚀 正在启动 Next.js 开发服务器...
echo.
echo 📍 前端地址: http://localhost:3000
echo 📍 按 Ctrl+C 停止服务
echo.
echo ⚠️  请确保后端服务已启动 (http://localhost:8000)
echo.

call npm run dev
