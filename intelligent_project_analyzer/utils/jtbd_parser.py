"""Utilities for parsing and transforming JTBD-style statements."""

from __future__ import annotations

import logging
import re
from typing import Iterable

logger = logging.getLogger(__name__)

_JTBD_KEYWORDS: Iterable[str] = (
    "JTBD公式",
    "JTBD公式:",
    "JTBD公式：",
    "雇佣空间",
    "雇用空间",
    "通过空间完成",
    "核心任务是"
)


def _contains_jtbd_markers(text: str) -> bool:
    """Return True if text contains any JTBD markers."""
    return any(marker in text for marker in _JTBD_KEYWORDS)


def transform_jtbd_to_natural_language(text: str) -> str:
    """Convert JTBD formula-like text into a natural language description."""
    if not text or not isinstance(text, str):
        return text or ""

    normalized = text.strip()
    if not normalized:
        return normalized

    if not _contains_jtbd_markers(normalized):
        return normalized

    normalized = re.sub(r"^JTBD公式[:：]?\s*", "", normalized)
    normalized = normalized.replace("‘", "'").replace("’", "'")
    normalized = normalized.replace("“", '"').replace("”", '"')
    normalized = re.sub(r"雇[佣用]空间来?完成", "核心设计目标是", normalized)
    normalized = re.sub(r"通过空间完成", "核心设计目标是", normalized)
    normalized = re.sub(r"核心任务是[:：]?", "", normalized)

    matches = re.findall(r"['\"]([^'\"]+)['\"]", normalized)
    if len(matches) < 2:
        return normalized

    identity = matches[0] if len(matches) > 0 else "目标用户"
    space_type = matches[1] if len(matches) > 1 else "空间"
    tasks = matches[2:] if len(matches) > 2 else []

    description = f"本项目为{identity}设计{space_type}"
    if tasks:
        if len(tasks) == 1:
            description += f"，核心设计目标是{tasks[0]}"
        else:
            task_list = "、".join(tasks[:-1]) + f"，以及{tasks[-1]}"
            description += f"。核心设计目标包括：{task_list}"

    description += "。"
    logger.debug("JTBD formula transformed to natural language: %s", description)
    return description
