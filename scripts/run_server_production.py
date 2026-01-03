"""
生产环境启动器 - Python 3.13 Windows 兼容性修复（无热重载）

禁用 reload 模式以确保事件循环策略正确传递

v7.113 重大修复：
- 使用 WindowsProactorEventLoopPolicy 而非 SelectorEventLoopPolicy
- Proactor 支持子进程（Playwright需要），Selector 不支持

v2.0 修复：
- 添加项目根目录到 sys.path，支持从 scripts/ 目录运行
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 必须在 uvicorn 导入之前设置
if sys.platform == "win32" and sys.version_info >= (3, 13):
    # ⚠️ 关键修复: 使用 Proactor 而非 Selector
    # Playwright 需要创建浏览器子进程，Proactor 才支持
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    print("✅ [生产启动器] 已设置 WindowsProactorEventLoopPolicy（支持子进程，修复 Playwright）")
elif sys.platform == "win32":
    # Python 3.12 及以下，默认就是 Proactor
    print("✅ [生产启动器] Python < 3.13，使用默认事件循环策略")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "intelligent_project_analyzer.api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # 禁用热重载，确保策略生效
        log_level="info",
        workers=1,  # 单worker模式
    )
