"""
change_intent_detector.py — 语义变更感知检测器（v1.0，词表版）

根据用户修改描述文本，检测变更意图属于三类之一：

  VISUAL_ONLY      — 仅视觉/材质/色彩变更（仅需重跑专家任务）
  SPATIAL_ZONE     — 空间区域/功能分区变更（需强制重跑 Phase-1）
  IDENTITY_PATTERN — 居住身份/生活方式变更（需强制重跑 Phase-1）

第一版实现：关键词词表精确匹配，不引入 LLM 调用。
后续升级路径：词表版稳定后可升级为 Embedding 余弦相似度（不改接口）。

使用示例：
    from intelligent_project_analyzer.services.change_intent_detector import (
        detect_change_intent,
        ChangeIntentType,
    )

    intent = detect_change_intent("把客厅改成开放式")
    # intent == ChangeIntentType.SPATIAL_ZONE
"""

from __future__ import annotations

import json
import logging
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import FrozenSet, NamedTuple

logger = logging.getLogger(__name__)

# 词表文件路径（与 config/ 目录同级的 services/ 向上两级后进入 config/）
_CONFIG_DIR = Path(__file__).parent.parent / "config"
_SPATIAL_KEYWORDS_FILE = _CONFIG_DIR / "spatial_semantic_keywords.json"
_IDENTITY_KEYWORDS_FILE = _CONFIG_DIR / "identity_pattern_keywords.json"


# ---------------------------------------------------------------------------
# 公开类型
# ---------------------------------------------------------------------------


class ChangeIntentType(str, Enum):
    """变更意图分类。

    Attributes:
        VISUAL_ONLY: 仅视觉/材质/色彩/装饰变更，不涉及空间结构或身份模式。
        SPATIAL_ZONE: 空间类型、功能区划或墙体结构变更。
        IDENTITY_PATTERN: 居住身份、家庭结构或生活方式的根本性变更。
    """

    VISUAL_ONLY = "VISUAL_ONLY"
    SPATIAL_ZONE = "SPATIAL_ZONE"
    IDENTITY_PATTERN = "IDENTITY_PATTERN"


class DetectionResult(NamedTuple):
    """``detect_change_intent`` 的详细返回值（可选使用）。

    Attributes:
        intent: 检测到的变更意图类型。
        matched_keywords: 触发该意图的关键词集合（空集表示触发了 VISUAL_ONLY 默认分支）。
        source: 触发词来自哪个词表（"spatial" | "identity" | "none"）。
    """

    intent: ChangeIntentType
    matched_keywords: FrozenSet[str]
    source: str


# ---------------------------------------------------------------------------
# 词表加载（带 lru_cache，进程级单例）
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _load_spatial_keywords() -> FrozenSet[str]:
    """从 JSON 文件加载空间类型关键词，首次调用后缓存至进程结束。"""
    return _load_keywords_file(_SPATIAL_KEYWORDS_FILE, "spatial")


@lru_cache(maxsize=1)
def _load_identity_keywords() -> FrozenSet[str]:
    """从 JSON 文件加载身份/生活方式关键词，首次调用后缓存至进程结束。"""
    return _load_keywords_file(_IDENTITY_KEYWORDS_FILE, "identity")


def _load_keywords_file(path: Path, label: str) -> FrozenSet[str]:
    """读取关键词 JSON 文件，返回不可变集合。

    Args:
        path:  JSON 文件路径。
        label: 词表标识（用于日志）。

    Returns:
        关键词 frozenset。

    Raises:
        FileNotFoundError: 若词表文件不存在。
        ValueError:        若 JSON 格式不符合预期（顶层缺 ``keywords`` 列表）。
    """
    if not path.exists():
        raise FileNotFoundError(f"[change_intent_detector] 词表文件不存在: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"[change_intent_detector] 词表 JSON 解析失败 ({label}): {exc}") from exc

    keywords = data.get("keywords")
    if not isinstance(keywords, list):
        raise ValueError(
            f"[change_intent_detector] 词表 JSON 格式错误 ({label})：顶层须含 'keywords' 列表，" f"实际类型: {type(keywords).__name__}"
        )

    result: FrozenSet[str] = frozenset(str(k) for k in keywords if k)
    logger.debug("[change_intent_detector] 加载 %s 词表: %d 个关键词", label, len(result))
    return result


# ---------------------------------------------------------------------------
# 核心检测逻辑
# ---------------------------------------------------------------------------


def detect_change_intent(change_text: str) -> ChangeIntentType:
    """检测用户修改描述文本的变更意图类型（轻量公开 API）。

    判定优先级（从高到低）：

    1. 命中 **身份/生活方式** 关键词 → ``IDENTITY_PATTERN``
    2. 命中 **空间类型** 关键词       → ``SPATIAL_ZONE``
    3. 默认                           → ``VISUAL_ONLY``

    Args:
        change_text: 用户输入的修改描述文字（中文为主，支持中英混合）。

    Returns:
        ``ChangeIntentType`` 枚举值。

    Note:
        函数为纯同步、无副作用调用，延迟 < 1ms（词表热路径）。
    """
    return detect_change_intent_detailed(change_text).intent


def detect_change_intent_detailed(change_text: str) -> DetectionResult:
    """与 ``detect_change_intent`` 逻辑相同，但返回完整的 ``DetectionResult``。

    供调试、日志和单元测试使用。

    Args:
        change_text: 用户输入的修改描述文字。

    Returns:
        ``DetectionResult`` 命名元组，含 intent、matched_keywords、source。
    """
    if not change_text or not change_text.strip():
        return DetectionResult(
            intent=ChangeIntentType.VISUAL_ONLY,
            matched_keywords=frozenset(),
            source="none",
        )

    text = change_text.strip()
    spatial_kw = _load_spatial_keywords()
    identity_kw = _load_identity_keywords()

    # ── 优先级 1：身份/生活方式词表 ──────────────────────────────────────
    identity_hits = frozenset(kw for kw in identity_kw if kw in text)
    if identity_hits:
        logger.debug(
            "[change_intent_detector] IDENTITY_PATTERN | hits=%s | text=%r",
            identity_hits,
            text[:80],
        )
        return DetectionResult(
            intent=ChangeIntentType.IDENTITY_PATTERN,
            matched_keywords=identity_hits,
            source="identity",
        )

    # ── 优先级 2：空间类型词表 ───────────────────────────────────────────
    spatial_hits = frozenset(kw for kw in spatial_kw if kw in text)
    if spatial_hits:
        logger.debug(
            "[change_intent_detector] SPATIAL_ZONE | hits=%s | text=%r",
            spatial_hits,
            text[:80],
        )
        return DetectionResult(
            intent=ChangeIntentType.SPATIAL_ZONE,
            matched_keywords=spatial_hits,
            source="spatial",
        )

    # ── 默认分支：视觉/材质/色彩变更 ────────────────────────────────────
    logger.debug(
        "[change_intent_detector] VISUAL_ONLY (no keyword hit) | text=%r",
        text[:80],
    )
    return DetectionResult(
        intent=ChangeIntentType.VISUAL_ONLY,
        matched_keywords=frozenset(),
        source="none",
    )


def reload_keywords() -> None:
    """清除关键词缓存，强制下次调用重新从磁盘加载。

    主要用于热更新词表（测试 / 运维场景）。
    """
    _load_spatial_keywords.cache_clear()
    _load_identity_keywords.cache_clear()
    logger.info("[change_intent_detector] 关键词缓存已清除，下次调用将重新加载")
