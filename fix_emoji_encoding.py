"""
fix_emoji_encoding.py
Windows 环境下 OpenAI API emoji 编码修复补丁

问题背景：
  Windows 控制台默认 cp936/gbk 编码，stdout 无法输出 emoji（如 ✅ ⚠️），
  导致 OpenAI API 返回含 emoji 的响应写入 stdout/stderr 时抛出 UnicodeEncodeError。

修复策略：
  1. 强制将 stdout/stderr 的编码设为 utf-8（使用 reconfigure，Python 3.7+）
  2. 设置 PYTHONIOENCODING 环境变量为 utf-8 供子进程继承
  3. 为 json.dumps 注入 ensure_ascii=False 的全局默认值

使用方式：
  from fix_emoji_encoding import apply_all_patches
  apply_all_patches()
"""

import sys
import os
import json
from typing import Any


def patch_stdio_encoding() -> bool:
    """将 stdout/stderr 强制设为 utf-8，解决 Windows cp936 的 UnicodeEncodeError"""
    patched = False
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        try:
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")
                patched = True
            elif hasattr(stream, "buffer"):
                import io

                new_stream = io.TextIOWrapper(
                    stream.buffer,
                    encoding="utf-8",
                    errors="replace",
                    line_buffering=stream.line_buffering,
                )
                setattr(sys, stream_name, new_stream)
                patched = True
        except Exception:
            pass
    return patched


def patch_env_encoding() -> None:
    """设置 PYTHONIOENCODING，让子进程（如 subprocess）也继承 utf-8"""
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")


def patch_json_dumps() -> None:
    """
    让内置 json.dumps 默认使用 ensure_ascii=False，
    避免将 emoji 转义为 \\uXXXX 序列（影响可读性和部分下游解析器）
    """
    _original_dumps = json.dumps

    def _patched_dumps(obj: Any, **kwargs) -> str:
        kwargs.setdefault("ensure_ascii", False)
        return _original_dumps(obj, **kwargs)

    json.dumps = _patched_dumps  # type: ignore[assignment]


def apply_all_patches() -> None:
    """应用全部 emoji/编码修复补丁（幂等，可重复调用）"""
    patch_env_encoding()
    patch_stdio_encoding()
    patch_json_dumps()
