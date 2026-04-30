"""
execution/actions/generation_actions.py — 生成类原子动作

Copilot 生成（2026-03-22）

原子动作：
  - generate_image_action          ：调用图像生成 API
  - generate_text_package_action   ：基于模板生成文字交付物
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional


def generate_image_action(
    prompt: str,
    style: str = "写实",
    resolution: str = "1024x768",
    count: int = 1,
    image_client: Optional[Any] = None,
) -> List[str]:
    """
    图像生成原子动作。

    参数:
      prompt       — 图像描述提示词
      style        — 渲染风格（如 "写实", "概念草图"）
      resolution   — 输出分辨率
      count        — 生成数量
      image_client — 图像生成客户端（如 DALL-E / Stable Diffusion），None 时返回 []

    返回:
      生成图像的 URL 列表
    """
    if image_client is None:
        return []

    try:
        results = image_client.generate(
            prompt=prompt,
            style=style,
            resolution=resolution,
            n=count,
        )
        return [r.get("url", "") for r in results if r.get("url")]
    except Exception as exc:
        return []


def generate_text_package_action(
    template_id: str,
    context: Dict[str, Any],
    llm_client: Optional[Any] = None,
) -> List[Dict[str, str]]:
    """
    文字交付物包生成原子动作。

    参数:
      template_id — 模板标识（如 "design_statement_v1", "review_report"）
      context     — 用于填充模板的上下文数据
      llm_client  — LLM 客户端；None 时返回占位结构（测试模式）

    返回:
      [{"section_title": ..., "content": ...}]
    """
    if llm_client is None:
        # 测试模式：返回占位章节
        return [
            {"section_title": "一、项目概述", "content": "（待生成）"},
            {"section_title": "二、设计策略", "content": "（待生成）"},
            {"section_title": "三、执行计划", "content": "（待生成）"},
        ]

    try:
        raw = llm_client.generate_document(template_id=template_id, context=context)
        return raw if isinstance(raw, list) else []
    except Exception as exc:
        return [{"section_title": "生成错误", "content": str(exc)[:200]}]
