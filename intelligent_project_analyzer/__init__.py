"""
智能项目分析系统

基于LangGraph的多智能体协作项目分析平台
"""

import os

# ============================================================================
# 🔧 v7.122: 全局 UTF-8 编码设置（解决 Windows 控制台 Emoji 编码错误）
# ============================================================================
import sys

# 设置环境变量强制 UTF-8 编码
os.environ["PYTHONIOENCODING"] = "utf-8"

# Windows 平台特殊处理
if sys.platform == "win32":
    # 强制标准输出和标准错误使用 UTF-8（优先使用 reconfigure，避免替换底层流被提前关闭）
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue

        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
                continue
            except Exception:
                pass

        if hasattr(stream, "buffer"):
            import io

            setattr(
                sys,
                stream_name,
                io.TextIOWrapper(stream.buffer, encoding="utf-8", errors="replace"),
            )

    # 尝试设置 Windows 控制台代码页为 UTF-8 (65001)
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleCP(65001)
        kernel32.SetConsoleOutputCP(65001)
    except Exception:
        # 如果设置失败，降级处理（已有 TextIOWrapper 兜底）
        pass

__version__ = "1.0.0"
__author__ = "AI Assistant"
__description__ = "Intelligent Project Analysis System based on LangGraph"
