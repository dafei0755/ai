"""
生产环境启动器 - Python 3.13 Windows 兼容性修复（无热重载）

禁用 reload 模式以确保事件循环策略正确传递

v7.113 重大修复：
- 使用 WindowsProactorEventLoopPolicy 而非 SelectorEventLoopPolicy
- Proactor 支持子进程（Playwright需要），Selector 不支持

v2.0 修复：
- 添加项目根目录到 sys.path，支持从 scripts/ 目录运行

v7.122 修复：
- 添加 UTF-8 编码设置，解决 Windows 控制台 Emoji 输出问题

v7.141 增强：
- 集成 Milvus 服务自动启动
- 添加 Docker 服务健康检查
- 确保服务依赖正确启动顺序
"""
import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path

# ============================================================================
# 🔧 v7.122: UTF-8 编码设置（必须在任何输出之前）
# ============================================================================
os.environ["PYTHONIOENCODING"] = "utf-8"

if sys.platform == "win32":
    if hasattr(sys.stdout, "buffer"):
        import io

        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleCP(65001)
        kernel32.SetConsoleOutputCP(65001)
    except Exception:
        pass

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 🔧 v7.148: 强制加载 .env 文件（确保动态维度配置生效）
from dotenv import load_dotenv

env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path, override=True)
    print(f"✅ [生产启动器] 已加载环境变量: {env_path}")
    # 验证关键配置
    use_dynamic = os.getenv("USE_DYNAMIC_GENERATION", "未设置")
    enable_learning = os.getenv("ENABLE_DIMENSION_LEARNING", "未设置")
    print(f"   - USE_DYNAMIC_GENERATION={use_dynamic}")
    print(f"   - ENABLE_DIMENSION_LEARNING={enable_learning}")
else:
    print(f"⚠️ [生产启动器] .env 文件不存在: {env_path}")

# 必须在 uvicorn 导入之前设置
if sys.platform == "win32" and sys.version_info >= (3, 13):
    # ⚠️ 关键修复: 使用 Proactor 而非 Selector
    # Playwright 需要创建浏览器子进程，Proactor 才支持
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    print("✅ [生产启动器] 已设置 WindowsProactorEventLoopPolicy（支持子进程，修复 Playwright）")
elif sys.platform == "win32":
    # Python 3.12 及以下，默认就是 Proactor
    print("✅ [生产启动器] Python < 3.13，使用默认事件循环策略")


# ============================================================================
# 🆕 v7.141: Docker 服务管理
# ============================================================================


def check_docker_installed() -> bool:
    """检查 Docker 是否已安装"""
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def check_docker_compose_installed() -> bool:
    """检查 docker-compose 是否已安装"""
    try:
        result = subprocess.run(["docker-compose", "--version"], capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def is_milvus_container_running() -> bool:
    """检查 Milvus 容器是否正在运行"""
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=milvus-standalone", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return "milvus-standalone" in result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def start_milvus_service() -> bool:
    """启动 Milvus Docker 服务"""
    try:
        print("🚀 [Milvus] 正在启动 Milvus 向量数据库服务...")

        docker_compose_file = project_root / "docker-compose.milvus.yml"

        if not docker_compose_file.exists():
            print(f"❌ [Milvus] Docker Compose 文件不存在: {docker_compose_file}")
            return False

        # 启动 Milvus 服务（后台模式）
        result = subprocess.run(
            ["docker-compose", "-f", str(docker_compose_file), "up", "-d"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            print(f"❌ [Milvus] 服务启动失败: {result.stderr}")
            return False

        print("⏳ [Milvus] 等待服务就绪...")

        # 等待 Milvus 容器健康检查通过（最多等待 90 秒）
        max_wait_time = 90
        check_interval = 5
        elapsed_time = 0

        while elapsed_time < max_wait_time:
            try:
                # 检查容器健康状态
                health_result = subprocess.run(
                    ["docker", "inspect", "--format", "{{.State.Health.Status}}", "milvus-standalone"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                health_status = health_result.stdout.strip()

                if health_status == "healthy":
                    print(f"✅ [Milvus] 服务已就绪 (耗时 {elapsed_time}s)")
                    return True
                elif health_status == "unhealthy":
                    print("❌ [Milvus] 服务健康检查失败")
                    return False
                else:
                    # starting 状态，继续等待
                    print(f"⏳ [Milvus] 服务启动中... ({elapsed_time}s / {max_wait_time}s)")
                    time.sleep(check_interval)
                    elapsed_time += check_interval

            except (subprocess.TimeoutExpired, Exception) as e:
                print(f"⚠️ [Milvus] 健康检查异常: {e}")
                time.sleep(check_interval)
                elapsed_time += check_interval

        print(f"⚠️ [Milvus] 服务启动超时 ({max_wait_time}s)，但将继续启动应用")
        return True  # 即使超时也返回 True，因为服务可能已启动但健康检查延迟

    except Exception as e:
        print(f"❌ [Milvus] 启动服务时发生错误: {e}")
        return False


def ensure_milvus_running() -> bool:
    """确保 Milvus 服务正在运行"""
    print("\n" + "=" * 70)
    print("🔍 [Milvus] 检查 Milvus 向量数据库服务状态...")
    print("=" * 70)

    # 1. 检查 Docker 是否安装
    if not check_docker_installed():
        print("⚠️ [Milvus] Docker 未安装，Milvus 服务将不可用")
        print("   提示: 请安装 Docker Desktop 以启用 Milvus 功能")
        return False

    # 2. 检查 docker-compose 是否安装
    if not check_docker_compose_installed():
        print("⚠️ [Milvus] docker-compose 未安装，Milvus 服务将不可用")
        print("   提示: 请安装 docker-compose 以启用 Milvus 功能")
        return False

    # 3. 检查 Milvus 容器是否已运行
    if is_milvus_container_running():
        print("✅ [Milvus] 服务已在运行")
        return True

    # 4. 启动 Milvus 服务
    print("⚠️ [Milvus] 服务未运行，正在启动...")
    return start_milvus_service()


if __name__ == "__main__":
    import uvicorn

    # 🆕 v7.141: 启动前确保 Milvus 服务运行
    milvus_status = ensure_milvus_running()

    if milvus_status:
        print("\n✅ [Milvus] Milvus 服务检查完成，准备启动应用服务器\n")
    else:
        print("\n⚠️ [Milvus] Milvus 服务不可用，应用将使用占位符模式运行\n")
        print("   注意: 知识库查询功能将受限\n")

    print("=" * 70)
    print("🚀 启动 FastAPI 应用服务器...")
    print("=" * 70 + "\n")

    uvicorn.run(
        "intelligent_project_analyzer.api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # 禁用热重载，确保策略生效
        log_level="info",
        workers=1,  # 单worker模式
    )
