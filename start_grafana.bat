@echo off
chcp 65001 >nul
echo ====================================
echo 启动 Grafana 日志监控服务
echo ====================================
echo.

cd /d "%~dp0docker"

echo [1/3] 检查 Docker 服务状态...
docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker 服务未运行，请先启动 Docker Desktop
    pause
    exit /b 1
)
echo ✅ Docker 服务正常

echo.
echo [2/3] 启动 Loki + Promtail + Grafana...
docker-compose -f docker-compose.logging.yml up -d

if errorlevel 1 (
    echo ❌ 启动失败
    pause
    exit /b 1
)

echo.
echo [3/3] 检查服务状态...
timeout /t 5 /nobreak >nul
docker-compose -f docker-compose.logging.yml ps

echo.
echo ====================================
echo ✅ 服务启动成功！
echo ====================================
echo.
echo 📍 Grafana UI: http://localhost:3200
echo 📍 默认账号: admin / admin123
echo 📍 Loki API: http://localhost:3100
echo.
echo 💡 提示: 现在可以访问管理后台的 "系统监控" 页面查看 Grafana 面板
echo.
pause
