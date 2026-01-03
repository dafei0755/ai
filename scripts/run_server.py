"""
Uvicorn 启动包装器 - Python 3.13 Windows 兼容性修复

必须在 uvicorn 创建事件循环之前设置策略！

注意：reload=True 会创建子进程，需要通过环境变量传递策略设置

v2.0 修复：
- 添加项目根目录到 sys.path，支持从 scripts/ 目录运行
"""
import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# ============================================================
# 🔧 关键：在 uvicorn 导入之前设置事件循环策略
# ============================================================
if sys.platform == "win32" and sys.version_info >= (3, 13):
    # 设置环境变量，让子进程也使用相同的策略
    os.environ["PYTHONASYNCIODEBUG"] = "1"
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    print("✅ [启动器] 已设置 WindowsSelectorEventLoopPolicy（Python 3.13+ Windows 兼容）")

# ============================================================
# 现在可以安全导入 uvicorn 并启动
# ============================================================
if __name__ == "__main__":
    import uvicorn

    # 方案1：禁用 reload（确保策略生效，生产环境推荐）
    # uvicorn.run(
    #     "intelligent_project_analyzer.api.server:app",
    #     host="0.0.0.0",
    #     port=8000,
    #     reload=False,  # ❌ 禁用热重载以确保策略生效
    #     log_level="info"
    # )
    # 方案2：使用 reload（开发方便，但需要额外配置）
    # 注意：reload 模式下子进程会重新导入 server.py，策略会在那里再次设置
    uvicorn.run(
        "intelligent_project_analyzer.api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # ⚠️ 开发模式，依赖 server.py 中的策略设置
        log_level="info",
        reload_dirs=["intelligent_project_analyzer"],  # 只监控代码目录
        reload_excludes=["*.pyc", "__pycache__", "*.log"],
    )
