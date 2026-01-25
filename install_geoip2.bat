@echo off
REM 一键安装 geoip2（需要管理员权限）

echo ========================================
echo  安装 geoip2 地理位置识别库
echo ========================================
echo.

REM 检查是否有管理员权限
net session >nul 2>&1
if %errorLevel% == 0 (
    echo ✅ 已获取管理员权限
) else (
    echo ❌ 需要管理员权限！
    echo.
    echo 请右键点击此脚本，选择"以管理员身份运行"
    pause
    exit /b 1
)

echo.
echo [1/2] 正在安装 geoip2...
conda install -c conda-forge geoip2 -y

if %errorLevel% == 0 (
    echo.
    echo ✅ geoip2 安装成功！
    echo.
    echo [2/2] 验证安装...
    python -c "import geoip2; print('✅ geoip2 版本:', geoip2.__version__)"
    echo.
    echo ========================================
    echo  安装完成！
    echo ========================================
    echo.
    echo 下一步：下载 GeoLite2 数据库
    echo 运行：python scripts\download_geoip_db.py
) else (
    echo.
    echo ❌ 安装失败
    echo.
    echo 请尝试手动安装：
    echo   conda install -c conda-forge geoip2 -y
    echo 或：
    echo   pip install geoip2
)

echo.
pause
