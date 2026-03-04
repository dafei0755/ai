"""
项目类型自动检测器 — 单一权威注册表 (Single Source of Truth)
v7.200: 统一分类定义、中文标签映射、关键词推断、LLM Prompt 类型列表

所有与项目类型相关的设置，只在此文件中维护：
  - PROJECT_TYPE_REGISTRY：类型定义（ID、标签、优先级、关键词）
  - LEGACY_TYPE_ALIASES  ：旧 ID → 新 ID 向后兼容映射
  - get_type_label()      ：ID → 中文标签（全局唯一出处）
  - get_all_type_ids()    ：返回全部类型 ID 列表（供 YAML/Prompt 注入）

规则：
  - 新增/修改分类 → 只改本文件 PROJECT_TYPE_REGISTRY
  - 下游代码 shared_agent_utils / query_builder / requirements_analyst
    等均从本模块读取，禁止自行维护字典
"""

from pathlib import Path
from typing import Any, Dict, List, Tuple

from loguru import logger

# 扩展类型文件路径（管理员审批后由 project_type_expansion.py 写入）
_EXTENSIONS_FILE = Path(__file__).parent.parent.parent / "data" / "project_type_extensions.json"


from ._type_registry import (
    _load_extension_registry,
    get_type_label,
    get_type_name_en,
    get_all_type_ids,
    normalize_type_id,
    _build_exclusivity_weights,
    PROJECT_TYPE_KEYWORDS,
)  # noqa: F401

class ProjectTypeDetector:
    """
    项目类型自动检测器 — 所有关键词逻辑从 PROJECT_TYPE_REGISTRY 读取。

    v7.200: 统一注册表驱动，消除重复逻辑
    v7.210: 支持扩展类型热重载（data/project_type_extensions.json）
    """

    # 类级别合并注册表（静态 + 扩展）
    _merged_registry: Dict[str, Any] | None = None

    def __init__(self):
        self.registry = self._get_registry()
        # Step 14: 预计算排他性权重（基于合并注册表）
        self._excl_weights = _build_exclusivity_weights(self.registry)
        logger.info(
            f"[v8.1] 项目类型检测器初始化，共 {len(self.registry)} 种类型（含 {len(self.registry) - len(PROJECT_TYPE_REGISTRY)} 个扩展）"
        )

    @classmethod
    def _get_registry(cls) -> Dict[str, Any]:
        """获取合并注册表（静态 + 扩展），带缓存"""
        if cls._merged_registry is None:
            cls._merged_registry = {**PROJECT_TYPE_REGISTRY, **_load_extension_registry()}
        return cls._merged_registry

    @classmethod
    def reload_extensions(cls) -> int:
        """
        热重载扩展类型（管理员审批新类型后调用）。

        Returns:
            当前扩展类型数量
        """
        extensions = _load_extension_registry()
        cls._merged_registry = {**PROJECT_TYPE_REGISTRY, **extensions}
        logger.info(f"[TypeRegistry] 热重载完成，共 {len(cls._merged_registry)} 种类型，{len(extensions)} 个扩展")
        return len(extensions)

    @staticmethod
    def _get_specialty_tag(combined_text: str) -> str | None:
        """Step 11: 从合并文本中提取最精确的专项标签（SPECIALTY_TAG_MAP 按序首次命中）"""
        for trigger, tag in SPECIALTY_TAG_MAP:
            if trigger in combined_text:
                return tag
        return None

    @staticmethod
    def _get_parent_type(type_id: str) -> str | None:
        """Step 9: 返回 type_id 对应的宽泛业态父分类"""
        return PARENT_TYPE_MAP.get(type_id)

    def detect(
        self,
        user_input: str,
        confirmed_tasks: List[Dict[str, Any]] | None = None,
    ) -> Tuple[str | None, float, str]:
        """
        检测项目类型。

        Args:
            user_input: 用户原始输入（或预处理后的合并文本）
            confirmed_tasks: 确认的任务列表（可选）

        Returns:
            (project_type, confidence, reason)
            - project_type : 类型 ID；若完全无匹配，返回 None（触发通用框架）
            - confidence   : 0.0–1.0
            - reason       : 人类可读的匹配说明
        """
        # ── Step 6: 别名预处理 ─────────────────────────────────────────────
        try:
            from .type_alias_normalizer import normalize_input

            preprocessed = normalize_input(user_input)
        except Exception:
            preprocessed = user_input

        # 合并文本
        combined_text = preprocessed.lower()
        if confirmed_tasks:
            for task in confirmed_tasks:
                combined_text += " " + task.get("title", "").lower()
                combined_text += " " + task.get("description", "").lower()

        # ── Step 13: 预计算否定区间 ───────────────────────────────────────────
        try:
            from .type_alias_normalizer import extract_negated_spans, is_negated

            negated_spans = extract_negated_spans(combined_text)
        except Exception:
            negated_spans = []
            is_negated = lambda kw, txt, spans: False  # noqa: E731

        scores: Dict[str, Dict[str, Any]] = {}

        for type_id, config in self.registry.items():
            # hybrid_residential_commercial 只在外部逻辑合成，不参与关键词匹配
            if not config.get("keywords"):
                continue

            # ── Step 13: 否定词过滤 ───────────────────────────────────────────
            def _hits_with_negation(keywords: List[str]) -> Tuple[int, float, List[str]]:
                """返回 (命中数, 加权分, 命中词列表)，否定词语境下的命中不计"""
                count = 0
                weighted = 0.0
                matched: List[str] = []
                for kw in keywords:
                    if kw not in combined_text:
                        continue
                    if negated_spans and is_negated(kw, combined_text, negated_spans):
                        continue  # 否定语境，跳过
                    # ── Step 14: 排他性权重 ───────────────────────────────────
                    w = self._excl_weights.get(kw, 1.0)
                    count += 1
                    weighted += w
                    matched.append(kw)
                return count, weighted, matched

            primary_count, primary_weighted, primary_matched = _hits_with_negation(config["keywords"])
            secondary_count, secondary_weighted, secondary_matched = _hits_with_negation(
                config.get("secondary_keywords", [])
            )

            # min_secondary_hits：primary=0 时的次要命中阈值
            min_sec = config.get("min_secondary_hits", 0)
            if primary_count == 0:
                if min_sec > 0 and secondary_count < min_sec:
                    continue
                elif min_sec == 0 and secondary_count == 0:
                    continue

            # ── Step 14: 带权重的得分（排他性关键词贡献更高）────────────────
            score = primary_weighted * 2 + secondary_weighted

            scores[type_id] = {
                "score": score,
                "priority": config["priority"],
                "primary_hits": primary_count,
                "secondary_hits": secondary_count,
                "matched": primary_matched + secondary_matched,
                "name": config["name"],
            }

        if not scores:
            # 完全无匹配 → 返回 None，上层可决定走通用框架
            logger.info("[v8.1] 项目类型未匹配，建议触发通用框架")
            return None, 0.0, "无关键词命中"

        # 按 score × priority 降序
        sorted_types = sorted(
            scores.items(),
            key=lambda x: x[1]["score"] * x[1]["priority"],
            reverse=True,
        )

        best_type_id, best_info = sorted_types[0]
        confidence = min(0.95, 0.4 + best_info["score"] * 0.1)
        reason = "匹配关键词: " + ", ".join(best_info["matched"][:4])

        # ── Step 15: top-2 融合提示 ───────────────────────────────────────────
        if len(sorted_types) >= 2:
            second_type_id, second_info = sorted_types[1]
            best_score_val = best_info["score"] * best_info["priority"]
            second_score_val = second_info["score"] * second_info["priority"]
            if best_score_val > 0 and second_score_val / best_score_val >= 0.8:
                # 第二名得分 ≥80% 第一名 → 附加弱提示（不影响主结果）
                reason += f" | 次选: {second_info['name']} ({second_type_id})"

        logger.info(f"[v8.1] 检测结果: {best_info['name']} ({best_type_id}), " f"置信度: {confidence:.0%}, {reason}")
        return best_type_id, confidence, reason

    def detect_with_details(
        self,
        user_input: str,
        confirmed_tasks: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:
        """
        检测项目类型（返回详细信息）。

        v8.1 新增字段：
          parent_type   : 宽泛业态桶（Steps 9-10）
          specialty_tag : 细粒度子类型（Steps 11-12）
          secondary_type: 第二候选类型（Step 15），得分差 ≤20% 时非空
          is_ambiguous  : True 表示主次候选得分接近，建议追问确认
        """
        project_type, confidence, reason = self.detect(user_input, confirmed_tasks)

        # ── Step 10: 提取 parent_type ─────────────────────────────────────────
        parent_type = self._get_parent_type(project_type) if project_type else None

        # ── Step 11: 提取 specialty_tag ──────────────────────────────────────
        try:
            from .type_alias_normalizer import normalize_input

            combined = normalize_input(user_input).lower()
        except Exception:
            combined = user_input.lower()
        if confirmed_tasks:
            for t in confirmed_tasks:
                combined += " " + t.get("title", "").lower()
        specialty_tag = self._get_specialty_tag(combined)

        # ── Step 15: 解析 reason 中的次选 ────────────────────────────────────
        secondary_type: str | None = None
        secondary_name: str | None = None
        is_ambiguous = False
        if " | 次选: " in reason:
            try:
                secondary_part = reason.split(" | 次选: ")[1]
                # 格式: "名称 (type_id)"
                secondary_type = secondary_part.split("(")[1].rstrip(")")
                secondary_name = secondary_part.split("(")[0].strip()
                is_ambiguous = True
            except Exception:
                pass

        if project_type is None:
            return {
                "project_type": None,
                "project_type_name": "未识别",
                "confidence": 0.0,
                "reason": reason,
                "parent_type": None,
                "specialty_tag": specialty_tag,
                "secondary_type": None,
                "secondary_type_name": None,
                "is_ambiguous": False,
                "all_matches": [],
            }

        return {
            "project_type": project_type,
            "project_type_name": get_type_label(project_type),
            "confidence": confidence,
            "reason": reason,
            "parent_type": parent_type,
            "specialty_tag": specialty_tag,
            "secondary_type": secondary_type,
            "secondary_type_name": secondary_name,
            "is_ambiguous": is_ambiguous,
            "all_matches": [],
        }


# =============================================================================
# 便捷函数
# =============================================================================


def detect_project_type(
    user_input: str,
    confirmed_tasks: List[Dict[str, Any]] | None = None,
    default: str = "personal_residential",
) -> str:
    """
    便捷函数：检测项目类型，无匹配时返回 default。

    Args:
        user_input: 用户原始输入
        confirmed_tasks: 确认的任务列表（可选）
        default: 无匹配时的默认类型 ID

    Returns:
        项目类型 ID
    """
    detector = ProjectTypeDetector()
    project_type, _, _ = detector.detect(user_input, confirmed_tasks)
    return project_type if project_type is not None else default


def detect_project_type_with_confidence(
    user_input: str,
    confirmed_tasks: List[Dict[str, Any]] | None = None,
) -> Tuple[str | None, float]:
    """
    便捷函数：检测项目类型（带置信度）。

    Returns:
        (项目类型ID或None, 置信度)
    """
    detector = ProjectTypeDetector()
    project_type, confidence, _ = detector.detect(user_input, confirmed_tasks)
    return project_type, confidence
