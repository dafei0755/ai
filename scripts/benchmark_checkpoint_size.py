#!/usr/bin/env python3
"""
MT-3 验收脚本：checkpoint 序列化大小基准测试

用法
----
::

    python scripts/benchmark_checkpoint_size.py

输出示例
--------
::

    ===== Checkpoint 大小基准测试 =====
    会话消息轮次:  10  20  50  100  200

    [ 传统无界 reducer ]
    10  轮:   12.3 KB
    20  轮:   24.1 KB
    50  轮:   60.7 KB
    100 轮:  120.4 KB
    200 轮:  240.8 KB

    [ MT-3 有界 reducer (MAX=100) ]
    10  轮:   12.3 KB
    20  轮:   24.1 KB
    50  轮:   60.7 KB
    100 轮:  120.4 KB
    200 轮:  120.4 KB  ← 封顶        节省 50.0 %

    ✅ MT-3 验收：200 轮节省 50.0% >= 50%
"""
from __future__ import annotations

import json
import os
import pickle
import sys
from typing import Any, Dict, List

# ── 确保项目根目录在 sys.path ──────────────────────────────────────────────
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from langchain_core.messages import HumanMessage, AIMessage  # noqa: E402
from langgraph.graph import add_messages  # noqa: E402

from intelligent_project_analyzer.core.state import _bounded_add_messages  # noqa: E402


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def _make_message_pair(i: int):
    """生成第 i 对对话消息（HumanMessage + AIMessage）。"""
    return [
        HumanMessage(content=f"用户问题 #{i}：请帮我分析一下这个室内装修方案的优缺点。"),
        AIMessage(content=f"AI 回复 #{i}：好的，根据您提供的方案，我将从空间规划、采光、收纳三个维度进行分析……（详细内容{i}）"),
    ]


def _checkpoint_bytes(messages: List) -> int:
    """用 pickle 模拟 LangGraph checkpoint 序列化，返回字节数。"""
    return len(pickle.dumps(messages))


def _run_scenario(turns: int, use_bounded: bool, max_history: int = 100):
    """模拟 n 轮对话后，返回 conversation_history 的 checkpoint 大小（字节）。"""
    history: List = []
    reducer = _bounded_add_messages if use_bounded else add_messages
    for i in range(turns):
        new = _make_message_pair(i)
        history = reducer(history, new)  # type: ignore[arg-type]
    return _checkpoint_bytes(history), len(history)


# ---------------------------------------------------------------------------
# 主程序
# ---------------------------------------------------------------------------


def main():
    turns_list = [10, 20, 50, 100, 200]
    max_history = int(os.getenv("CONVERSATION_HISTORY_MAX", "100"))

    print("\n===== checkpoint 大小基准测试 (MT-3) =====")
    print(f"CONVERSATION_HISTORY_MAX = {max_history}\n")

    unbounded: Dict[int, Dict[str, Any]] = {}
    bounded: Dict[int, Dict[str, Any]] = {}

    for turns in turns_list:
        size_u, count_u = _run_scenario(turns, use_bounded=False)
        size_b, count_b = _run_scenario(turns, use_bounded=True, max_history=max_history)
        unbounded[turns] = {"size": size_u, "count": count_u}
        bounded[turns] = {"size": size_b, "count": count_b}

    print(f"{'轮次':>8}  {'无界大小':>12}  {'有界大小':>12}  {'节省':>9}  {'无界条数':>8}  {'有界条数':>8}")
    print("-" * 70)
    savings_at_200 = 0.0
    for turns in turns_list:
        u = unbounded[turns]
        b = bounded[turns]
        saving_pct = (1.0 - b["size"] / u["size"]) * 100 if u["size"] > 0 else 0.0
        if turns == 200:
            savings_at_200 = saving_pct
        flag = " ← 封顶" if b["count"] < u["count"] else ""
        print(
            f"{turns:>8}  "
            f"{u['size']/1024:>10.1f}KB  "
            f"{b['size']/1024:>10.1f}KB  "
            f"{saving_pct:>8.1f}%  "
            f"{u['count']:>8}  "
            f"{b['count']:>8}{flag}"
        )

    print()
    threshold = 50.0
    if savings_at_200 >= threshold:
        print(f"✅ MT-3 验收通过：200 轮时节省 {savings_at_200:.1f}% >= {threshold}%")
    else:
        print(f"❌ MT-3 验收未通过：200 轮时节省 {savings_at_200:.1f}% < {threshold}%")
        sys.exit(1)


if __name__ == "__main__":
    main()
