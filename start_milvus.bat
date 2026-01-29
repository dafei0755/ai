@echo off
REM Milvus服务启动脚本
REM 版本: v7.141.3
REM 日期: 2026-01-06

echo ======================================================================
echo Milvus 服务启动脚本 - v7.141.4
echo ======================================================================
echo.

REM 检查Docker是否运行
echo [步骤 1/4] 检查Docker状态...
docker version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker未运行！
    echo.
    echo 请先启动Docker Desktop，然后重新运行此脚本
    echo.
    echo 启动方法：
    echo   1. 在开始菜单搜索 "Docker Desktop"
    echo   2. 点击启动Docker Desktop
    echo   3. 等待Docker图标变为绿色
    echo   4. 重新运行此脚本
    echo.
    pause
    exit /b 1
)
echo ✅ Docker已运行

REM 检查是否已有Milvus容器
echo.
echo [步骤 2/4] 检查Milvus容器...
docker ps -a | findstr milvus-standalone >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Milvus容器不存在，开始创建...
    goto :pull_image
) else (
    echo ✅ Milvus容器已存在
    goto :check_running
)

:pull_image
echo.
echo [步骤 3/4] 拉取Milvus镜像...
echo 这可能需要2-5分钟，请耐心等待...
docker pull milvusdb/milvus:v2.4.0
if errorlevel 1 (
    echo ❌ 拉取镜像失败
    pause
    exit /b 1
)
echo ✅ 镜像拉取成功
goto :create_container

:create_container
echo.
echo [步骤 4/4] 创建并启动Milvus容器...
docker run -d ^
  --name milvus-standalone ^
  -p 19530:19530 ^
  -p 9091:9091 ^
  -v milvus_data:/var/lib/milvus ^
  -e ETCD_USE_EMBED=true ^
  -e COMMON_STORAGETYPE=local ^
  milvusdb/milvus:v2.4.0

if errorlevel 1 (
    echo ❌ 启动容器失败
    echo.
    echo 可能的原因：
    echo   - 端口19530或9091被占用
    echo   - 内存不足（Milvus需要至少4GB RAM）
    echo.
    echo 查看详细错误信息：
    echo   docker logs milvus-standalone
    echo.
    pause
    exit /b 1
)
echo ✅ 容器创建成功
goto :verify

:check_running
docker ps | findstr milvus-standalone >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Milvus容器已停止，正在启动...
    docker start milvus-standalone
    if errorlevel 1 (
        echo ❌ 启动失败
        pause
        exit /b 1
    )
    echo ✅ 容器已启动
) else (
    echo ✅ Milvus容器正在运行
)

:verify
echo.
echo ======================================================================
echo 等待Milvus服务就绪（约30-60秒）...
echo ======================================================================
timeout /t 10 /nobreak >nul

REM 检查容器是否还在运行
docker ps | findstr milvus-standalone >nul 2>&1
if errorlevel 1 (
    echo ❌ 容器启动后立即停止
    echo.
    echo 查看日志：
    docker logs milvus-standalone --tail 50
    echo.
    pause
    exit /b 1
)

echo.
echo ✅ Milvus容器运行中
echo.
echo 容器信息：
docker ps | findstr milvus-standalone
echo.

REM 测试连接
echo ======================================================================
echo 测试Milvus连接...
echo ======================================================================
echo.
python scripts/check_milvus_schema.py
if errorlevel 1 (
    echo.
    echo ⚠️  连接测试失败，但容器正在运行
    echo 可能需要等待更长时间让Milvus完全启动
    echo.
    echo 稍后可以手动测试：
    echo   python scripts/check_milvus_schema.py
    echo.
    echo 查看容器日志：
    echo   docker logs milvus-standalone
    echo.
) else (
    echo.
    echo ✅ Milvus服务就绪！
    echo.
)

echo ======================================================================
echo 下一步操作
echo ======================================================================
echo.
echo 1. 执行Schema迁移（如果需要）：
echo    python scripts/migrate_milvus_v7141.py --backup --drop-old
echo.
echo 2. 运行测试验证：
echo    pytest tests/test_quota_enforcement_e2e.py -v
echo.
echo 3. 查看Milvus日志：
echo    docker logs -f milvus-standalone
echo.
echo 4. 停止Milvus服务：
echo    docker stop milvus-standalone
echo.
echo 5. 重启Milvus服务：
echo    docker restart milvus-standalone
echo.
echo ======================================================================
pause
