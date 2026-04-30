"""
execution/actions/delta_actions.py — 增量修订原子动作

Copilot 生成（2026-03-22）

原子动作：
  - regenerate_delta_action  ：对指定交付物字段执行局部重新生成
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional


def regenerate_delta_action(
    target_ref: str,
    delta_spec: Dict[str, Any],
    original_deliverable: Optional[Dict[str, Any]] = None,
    llm_client: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    增量重新生成原子动作。

    参数:
      target_ref           — 目标交付物引用 ID（如 "delivery_v1.facade"）
      delta_spec           — 增量修改规格 {"field": ..., "instruction": ..., "context": ...}
      original_deliverable — 原始交付物内容（用于增量重写）；None 时全量重生成
      llm_client           — LLM 客户端；None 时返回占位结果（测试模式）

    返回:
      {
        "target_ref": ...,
        "delta_spec": ...,
        "status": "ok" | "error",
        "result": {...},
        "generated_at": ...,
      }
    """
    if llm_client is None:
        # 测试模式：模拟成功
        return {
            "target_ref": target_ref,
            "delta_spec": delta_spec,
            "status": "ok",
            "result": {
                "content": f"（增量重生成占位）target={target_ref}",
                "delta_fields": list(delta_spec.keys()),
            },
            "generated_at": datetime.now().isoformat(),
        }

    try:
        instruction = delta_spec.get("instruction", "")
        context = delta_spec.get("context", {})
        original = original_deliverable.get("content", "") if original_deliverable else ""

        raw = llm_client.regenerate(
            original=original,
            instruction=instruction,
            context=context,
        )
        return {
            "target_ref": target_ref,
            "delta_spec": delta_spec,
            "status": "ok",
            "result": raw,
            "generated_at": datetime.now().isoformat(),
        }
    except Exception as exc:
        return {
            "target_ref": target_ref,
            "delta_spec": delta_spec,
            "status": "error",
            "result": {},
            "error": str(exc)[:200],
            "generated_at": datetime.now().isoformat(),
        }
