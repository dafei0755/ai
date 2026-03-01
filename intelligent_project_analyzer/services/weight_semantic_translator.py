"""
权重语义翻译器 v14.0

将雷达图数字权重转译为设计驱动信号。
纯规则引擎，零 LLM 调用，确保"同值同响应"的确定性翻译。

原则：凡有调整，必有响应

输入：radar_dimension_values + selected_radar_dimensions
输出：weight_interpretations 字典 + weight_response_manifest 基线
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from loguru import logger

# ============================================================================
# 常量
# ============================================================================

_TEMPLATES_PATH = Path(__file__).resolve().parent.parent / "config" / "prompts" / "weight_interpretation_templates.yaml"


# ============================================================================
# WeightSemanticTranslator
# ============================================================================


class WeightSemanticTranslator:
    """
    将雷达图滑块值(0-100)翻译为设计驱动信号。

    核心输出结构 (weight_interpretations):
    {
        "<dimension_id>": {
            "dimension_name": str,
            "raw_value": int,
            "default_value": int,
            "delta": int,               # 用户值 - 默认值
            "tier": str,                 # core_driver / important / background / de_emphasized
            "tier_label": str,           # "核心驱动力" / "重要考量" / ...
            "tier_icon": str,            # 🔴 / 🟡 / ⚪ / ⬇
            "emphasis_level": float,     # 0.0 ~ 1.0 (raw_value / 100)
            "tendency_label": str,       # "强烈倾向「极致实用」"
            "design_intent": str,        # 设计意图自然语言
            "expert_instruction": str,   # 注入专家的指引
            "de_emphasis_note": str,     # 弱化提示（仅 de_emphasized 有值）
            "category": str,             # aesthetic / functional / ...
            "left_label": str,
            "right_label": str,
            "adjusted": bool,            # delta != 0
        },
        "_summary": {
            "core_drivers": [dim_id, ...],
            "important": [dim_id, ...],
            "background": [dim_id, ...],
            "de_emphasized": [dim_id, ...],
            "adjusted_count": int,
            "total_count": int,
        }
    }
    """

    def __init__(self, templates_path: Optional[str] = None):
        path = Path(templates_path) if templates_path else _TEMPLATES_PATH
        self._templates = self._load_templates(path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def translate(
        self,
        radar_dimension_values: Dict[str, Any],
        selected_radar_dimensions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        主入口：将雷达维度值翻译为设计驱动信号。

        Args:
            radar_dimension_values: {dim_id: int_value, ...}  用户滑块值
            selected_radar_dimensions: [{id, name, left_label, right_label, category, default_value, ...}, ...]

        Returns:
            weight_interpretations 字典
        """
        if not radar_dimension_values or not selected_radar_dimensions:
            logger.warning("[WeightSemanticTranslator] 输入为空，返回空翻译结果")
            return self._empty_result()

        # 构建维度配置索引
        dim_configs = {}
        for dim in selected_radar_dimensions:
            dim_id = dim.get("id") or dim.get("dimension_id", "")
            if dim_id:
                dim_configs[dim_id] = dim

        result: Dict[str, Any] = {}
        summary: Dict[str, List[str]] = {
            "core_drivers": [],
            "important": [],
            "background": [],
            "de_emphasized": [],
        }
        adjusted_count = 0

        for dim_id, raw_value in radar_dimension_values.items():
            try:
                value = int(raw_value) if not isinstance(raw_value, (int, float)) else int(raw_value)
            except (ValueError, TypeError):
                continue

            config = dim_configs.get(dim_id, {})
            default_value = int(config.get("default_value", 50))
            delta = value - default_value
            adjusted = delta != 0

            if adjusted:
                adjusted_count += 1

            # 分层
            tier, tier_meta = self._classify_tier(value)

            # 倾向标签
            tendency_label = self._generate_tendency_label(value, config)

            # 设计意图
            category = config.get("category", "functional")
            design_intent = self._generate_design_intent(value, tier, tendency_label, category, config)

            # 专家指引
            expert_instruction = self._generate_expert_instruction(value, tier_meta, config)

            # 弱化备注
            de_emphasis_note = tier_meta.get("de_emphasis_note", "") if tier == "de_emphasized" else ""
            if tier == "de_emphasized" and not de_emphasis_note:
                de_emphasis_note = f"用户明确弱化此维度（{value}/100），避免过度投入"

            interpretation = {
                "dimension_name": config.get("name", dim_id),
                "dimension_label": config.get("name", dim_id),
                "raw_value": value,
                "default_value": default_value,
                "delta": delta,
                "tier": tier,
                "tier_label": tier_meta.get("label", tier),
                "tier_icon": tier_meta.get("icon", ""),
                "emphasis_level": round(value / 100.0, 2),
                "tendency_label": tendency_label,
                "design_intent": design_intent,
                "expert_instruction": expert_instruction,
                "de_emphasis_note": de_emphasis_note,
                "category": category,
                "left_label": config.get("left_label", ""),
                "right_label": config.get("right_label", ""),
                "adjusted": adjusted,
            }

            result[dim_id] = interpretation
            # core_driver → core_drivers (tier name maps to summary key)
            summary_key = "core_drivers" if tier == "core_driver" else tier
            summary[summary_key].append(dim_id)

        result["_summary"] = {
            **summary,
            "adjusted_count": adjusted_count,
            "total_count": len(radar_dimension_values),
        }

        logger.info(
            f"[WeightSemanticTranslator] 翻译完成: "
            f"🔴core={len(summary['core_drivers'])} "
            f"🟡important={len(summary['important'])} "
            f"⚪background={len(summary['background'])} "
            f"⬇de_emph={len(summary['de_emphasized'])} "
            f"| adjusted={adjusted_count}/{len(radar_dimension_values)}"
        )

        return result

    @staticmethod
    def build_initial_manifest(weight_interpretations: Dict[str, Any]) -> Dict[str, Any]:
        """
        构建 weight_response_manifest 的初始记录（tier 分配阶段）。

        后续管线节点可增量追加 responses。
        """
        manifest: Dict[str, Any] = {}
        for dim_id, interp in weight_interpretations.items():
            if dim_id.startswith("_"):
                continue
            manifest[dim_id] = {
                "value": interp["raw_value"],
                "tier": interp["tier"],
                "tier_label": interp["tier_label"],
                "tendency_label": interp["tendency_label"],
                "design_intent": interp["design_intent"],
                "adjusted": interp["adjusted"],
                "responses": [
                    {
                        "stage": "weight_translation",
                        "action": "tier_assigned",
                        "detail": f"分层为{interp['tier_label']}（{interp['raw_value']}/100）→ {interp['tendency_label']}",
                    }
                ],
            }
        return manifest

    # ------------------------------------------------------------------
    # 分层逻辑
    # ------------------------------------------------------------------

    def _classify_tier(self, value: int) -> Tuple[str, Dict[str, Any]]:
        """根据值将维度分到 core_driver / important / background / de_emphasized。"""
        tiers = self._templates.get("tiers", {})

        # 按 min_value 降序匹配
        for tier_name in ("core_driver", "important", "background", "de_emphasized"):
            tier_meta = tiers.get(tier_name, {})
            min_val = tier_meta.get("min_value", 0)
            if value >= min_val:
                return tier_name, tier_meta

        # fallback
        return "background", tiers.get("background", {"label": "背景参考"})

    # ------------------------------------------------------------------
    # 倾向标签
    # ------------------------------------------------------------------

    def _generate_tendency_label(self, value: int, config: Dict[str, Any]) -> str:
        """根据值和维度的 left_label / right_label 生成倾向标签。"""
        left = config.get("left_label", "低")
        right = config.get("right_label", "高")

        templates = self._templates.get("tendency_templates", {})

        # 按 threshold 降序匹配
        ordered = [
            ("extreme_right", 80),
            ("moderate_right", 60),
            ("balanced", 40),
            ("moderate_left", 20),
            ("extreme_left", 0),
        ]
        for key, default_thresh in ordered:
            tmpl = templates.get(key, {})
            thresh = tmpl.get("threshold", default_thresh)
            if value >= thresh:
                pattern = tmpl.get("template", "")
                return pattern.format(left_label=left, right_label=right)

        return f"「{left}」与「{right}」之间"

    # ------------------------------------------------------------------
    # 设计意图
    # ------------------------------------------------------------------

    def _generate_design_intent(
        self, value: int, tier: str, tendency: str, category: str, config: Dict[str, Any]
    ) -> str:
        """生成设计意图自然语言。"""
        dim_id = config.get("id") or config.get("dimension_id", "")

        # 1. 检查维度特殊覆盖
        overrides = self._templates.get("dimension_overrides", {}).get(dim_id, {})
        if tier == "core_driver" and overrides.get("high_override"):
            return overrides["high_override"]
        if tier == "de_emphasized" and overrides.get("low_override"):
            return overrides["low_override"]
        if value >= 80 and overrides.get("extreme_right_action"):
            return overrides["extreme_right_action"]
        if value <= 20 and overrides.get("extreme_left_action"):
            return overrides["extreme_left_action"]

        # 2. 按 category 模板生成
        cat_templates = self._templates.get("design_intent_templates", {}).get(category, {})
        if tier == "core_driver":
            template = cat_templates.get("high_template", "{tendency}是本项目的核心驱动力")
        elif tier in ("important",):
            template = cat_templates.get("mid_template", "{tendency}需在设计中适当体现")
        else:
            template = cat_templates.get("low_template", "{tendency}仅作为背景参考")

        return template.format(tendency=tendency)

    # ------------------------------------------------------------------
    # 专家指引
    # ------------------------------------------------------------------

    def _generate_expert_instruction(self, value: int, tier_meta: Dict[str, Any], config: Dict[str, Any]) -> str:
        """生成注入专家 prompt 的指引文本。"""
        template = tier_meta.get("expert_instruction_template", "")
        if not template:
            return ""
        return template.strip().format(
            value=value,
            dimension_name=config.get("name", ""),
            left_label=config.get("left_label", ""),
            right_label=config.get("right_label", ""),
        )

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------

    @staticmethod
    def _load_templates(path: Path) -> Dict[str, Any]:
        """加载 YAML 模板。"""
        if not path.exists():
            logger.warning(f"[WeightSemanticTranslator] 模板文件不存在: {path}，使用内置默认值")
            return _DEFAULT_TEMPLATES

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            logger.debug(f"[WeightSemanticTranslator] 加载模板: {path}")
            return data
        except Exception as e:
            logger.error(f"[WeightSemanticTranslator] 加载模板失败: {e}，使用内置默认值")
            return _DEFAULT_TEMPLATES

    @staticmethod
    def _empty_result() -> Dict[str, Any]:
        return {
            "_summary": {
                "core_drivers": [],
                "important": [],
                "background": [],
                "de_emphasized": [],
                "adjusted_count": 0,
                "total_count": 0,
            }
        }


# ============================================================================
# 内置容错默认模板（YAML 加载失败时使用）
# ============================================================================

_DEFAULT_TEMPLATES: Dict[str, Any] = {
    "tiers": {
        "core_driver": {
            "min_value": 75,
            "label": "核心驱动力",
            "icon": "🔴",
            "analysis_depth": "方案级",
            "expert_instruction_template": "此维度为核心驱动力（{value}/100），需提供方案级深度分析。",
            "de_emphasis_note": "",
        },
        "important": {
            "min_value": 50,
            "label": "重要考量",
            "icon": "🟡",
            "analysis_depth": "策略级",
            "expert_instruction_template": "此维度为重要考量（{value}/100），需清晰方向指引。",
            "de_emphasis_note": "",
        },
        "background": {
            "min_value": 25,
            "label": "背景参考",
            "icon": "⚪",
            "analysis_depth": "概述级",
            "expert_instruction_template": "此维度为背景参考（{value}/100），简要提及即可。",
            "de_emphasis_note": "",
        },
        "de_emphasized": {
            "min_value": 0,
            "label": "明确弱化",
            "icon": "⬇",
            "analysis_depth": "提及级",
            "expert_instruction_template": "此维度被弱化（{value}/100），避免过度投入。",
            "de_emphasis_note": "用户明确弱化此维度，避免过度投入",
        },
    },
    "tendency_templates": {
        "extreme_right": {"threshold": 80, "template": "强烈倾向「{right_label}」"},
        "moderate_right": {"threshold": 60, "template": "偏向「{right_label}」"},
        "balanced": {"threshold": 40, "template": "「{left_label}」与「{right_label}」融合"},
        "moderate_left": {"threshold": 20, "template": "偏向「{left_label}」"},
        "extreme_left": {"threshold": 0, "template": "强烈倾向「{left_label}」"},
    },
    "design_intent_templates": {
        "aesthetic": {
            "high_template": "{tendency}是本项目的核心美学定位",
            "mid_template": "{tendency}需在设计中体现",
            "low_template": "{tendency}仅作为美学背景参考",
        },
        "functional": {
            "high_template": "{tendency}是本项目的核心功能驱动",
            "mid_template": "{tendency}需在空间规划中体现",
            "low_template": "{tendency}仅作为功能配置的次要参考",
        },
        "technology": {
            "high_template": "{tendency}是本项目的核心技术策略",
            "mid_template": "{tendency}需在技术方案中体现",
            "low_template": "{tendency}仅作为技术方向的背景参考",
        },
        "resource": {
            "high_template": "{tendency}是本项目的核心资源策略",
            "mid_template": "{tendency}需在资源分配中考量",
            "low_template": "{tendency}仅作为资源规划的次要参考",
        },
        "experience": {
            "high_template": "{tendency}是本项目的核心体验目标",
            "mid_template": "{tendency}需在空间体验中体现",
            "low_template": "{tendency}仅作为体验设计的背景参考",
        },
    },
    "dimension_overrides": {},
    "task_correction_rules": {
        "core_driver": {
            "action": "reprioritize",
            "new_priority": "high",
            "reason_template": "设计驱动力「{dim_label}」→ {tendency}，需提升关联任务优先级",
        },
        "de_emphasized": {
            "action": "reprioritize",
            "new_priority": "low",
            "reason_template": "维度「{dim_label}」被弱化 → {tendency}，降低关联任务优先级",
        },
    },
}
