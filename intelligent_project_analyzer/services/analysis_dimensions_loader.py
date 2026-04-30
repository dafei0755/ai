"""
分析维度配置加载器

v7.280 - 2026-01-25
配置驱动的分析维度管理，支持：
- 从YAML加载维度定义
- 动机→视角映射
- 维度完整性校验
- 热更新支持
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from loguru import logger


@dataclass
class EntityType:
    """实体类型定义"""

    id: str
    label: str
    icon: str
    required_fields: List[Dict[str, str]]
    extraction_hints: List[str] = field(default_factory=list)


@dataclass
class Perspective:
    """视角定义"""

    id: str
    label: str
    description: str
    prompt_hint: str


@dataclass
class MotivationMapping:
    """动机到视角的映射"""

    motivation_id: str
    priority: str
    label_zh: str
    mandatory_perspectives: List[str]
    recommended_perspectives: List[str]
    boost_keywords: List[str]
    analysis_focus: List[str]


@dataclass
class DimensionValidation:
    """维度校验结果"""

    is_valid: bool
    missing_mandatory: List[str]
    missing_important: List[str]
    quality_score: float
    suggestions: List[str]


class AnalysisDimensionsConfig:
    """分析维度配置管理器"""

    _instance = None
    _config: Dict[str, Any] = {}
    _motivation_mapping: Dict[str, MotivationMapping] = {}
    _loaded = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._loaded:
            self.load_config()

    def load_config(self, config_dir: Optional[str] = None) -> bool:
        """
        加载分析维度配置

        Args:
            config_dir: 配置目录路径，默认使用模块相对路径

        Returns:
            是否加载成功
        """
        if config_dir is None:
            config_dir = Path(__file__).parent
        else:
            config_dir = Path(config_dir)

        # 加载维度配置
        dimensions_path = config_dir / "analysis_dimensions.yaml"
        if dimensions_path.exists():
            try:
                with open(dimensions_path, "r", encoding="utf-8") as f:
                    self._config = yaml.safe_load(f) or {}
                logger.info(f" [DimensionsConfig] 加载维度配置: {dimensions_path}")
            except Exception as e:
                logger.error(f" [DimensionsConfig] 加载维度配置失败: {e}")
                self._config = {}

        # 加载动机映射配置
        mapping_path = config_dir / "motivation_perspective_mapping.yaml"
        if mapping_path.exists():
            try:
                with open(mapping_path, "r", encoding="utf-8") as f:
                    mapping_config = yaml.safe_load(f) or {}
                self._load_motivation_mappings(mapping_config)
                logger.info(f" [DimensionsConfig] 加载动机映射: {mapping_path}")
            except Exception as e:
                logger.error(f" [DimensionsConfig] 加载动机映射失败: {e}")

        self._loaded = True
        return bool(self._config)

    def _load_motivation_mappings(self, config: Dict[str, Any]) -> None:
        """解析动机映射配置"""
        mappings = config.get("motivation_perspective_mapping", {})
        for motivation_id, mapping_data in mappings.items():
            self._motivation_mapping[motivation_id] = MotivationMapping(
                motivation_id=motivation_id,
                priority=mapping_data.get("priority", "BASELINE"),
                label_zh=mapping_data.get("label_zh", motivation_id),
                mandatory_perspectives=mapping_data.get("mandatory_perspectives", []),
                recommended_perspectives=mapping_data.get("recommended_perspectives", []),
                boost_keywords=mapping_data.get("boost_keywords", []),
                analysis_focus=mapping_data.get("analysis_focus", []),
            )

    def reload(self, config_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        热更新配置

        Returns:
            更新结果
        """
        self._config.clear()
        self._motivation_mapping.clear()
        self._loaded = False

        success = self.load_config(config_dir)

        return {
            "success": success,
            "dimensions_count": len(self.get_all_dimension_ids()),
            "motivation_mappings_count": len(self._motivation_mapping),
        }

    # ========================================================================
    # 维度定义访问
    # ========================================================================

    def get_all_dimension_ids(self) -> List[str]:
        """获取所有维度ID"""
        dimension_keys = [
            "user_profile",
            "entity_extraction",
            "l2_perspective_modeling",
            "l3_core_tension",
            "l4_user_task",
            "l5_sharpness",
            "human_dimensions",
            "problem_solving_approach",
        ]
        return [k for k in dimension_keys if k in self._config]

    def get_dimension(self, dimension_id: str) -> Optional[Dict[str, Any]]:
        """获取指定维度的配置"""
        return self._config.get(dimension_id)

    def get_entity_types(self) -> List[EntityType]:
        """获取所有实体类型定义"""
        entity_config = self._config.get("entity_extraction", {})
        entity_types_data = entity_config.get("entity_types", [])

        result = []
        for et in entity_types_data:
            result.append(
                EntityType(
                    id=et.get("id", ""),
                    label=et.get("label", ""),
                    icon=et.get("icon", ""),
                    required_fields=et.get("required_fields", []),
                    extraction_hints=et.get("extraction_hints", []),
                )
            )
        return result

    def get_base_perspectives(self) -> List[Perspective]:
        """获取基础视角列表"""
        l2_config = self._config.get("l2_perspective_modeling", {})
        perspectives_data = l2_config.get("base_perspectives", [])

        return [
            Perspective(
                id=p.get("id", ""),
                label=p.get("label", ""),
                description=p.get("description", ""),
                prompt_hint=p.get("prompt_hint", ""),
            )
            for p in perspectives_data
        ]

    def get_extended_perspectives(self) -> List[Perspective]:
        """获取扩展视角列表"""
        l2_config = self._config.get("l2_perspective_modeling", {})
        perspectives_data = l2_config.get("extended_perspectives", [])

        return [
            Perspective(
                id=p.get("id", ""),
                label=p.get("label", ""),
                description=p.get("description", ""),
                prompt_hint=p.get("prompt_hint", ""),
            )
            for p in perspectives_data
        ]

    def get_human_dimensions(self) -> List[Dict[str, Any]]:
        """获取人性化维度定义"""
        human_config = self._config.get("human_dimensions", {})
        return human_config.get("dimensions", [])

    def get_solution_step_structure(self) -> Dict[str, Any]:
        """获取解题步骤结构定义"""
        psa_config = self._config.get("problem_solving_approach", {})
        fields = psa_config.get("fields", [])
        for f in fields:
            if f.get("id") == "solution_steps":
                return f.get("step_structure", [])
        return []

    # ========================================================================
    # 动机→视角映射
    # ========================================================================

    def get_motivation_mapping(self, motivation_id: str) -> Optional[MotivationMapping]:
        """获取指定动机类型的视角映射"""
        return self._motivation_mapping.get(motivation_id)

    def get_perspectives_for_motivation(
        self,
        primary_motivation: str,
        secondary_motivations: Optional[List[str]] = None,
        user_input: Optional[str] = None,
    ) -> Tuple[List[str], List[str]]:
        """
        根据动机类型获取应激活的视角

        Args:
            primary_motivation: 主导动机类型
            secondary_motivations: 次要动机类型列表
            user_input: 用户原始输入（用于关键词匹配）

        Returns:
            (激活的视角列表, 激活原因列表)
        """
        # 基础视角始终激活
        base_perspectives = ["psychological", "sociological", "aesthetic", "emotional", "ritual"]
        activated = set(base_perspectives)
        reasons = ["基础视角默认激活"]

        # 主导动机映射
        primary_mapping = self._motivation_mapping.get(primary_motivation)
        if primary_mapping:
            for p in primary_mapping.mandatory_perspectives:
                if p not in activated:
                    activated.add(p)
                    reasons.append(f"主导动机[{primary_motivation}]强制激活")

            for p in primary_mapping.recommended_perspectives:
                if p not in activated:
                    activated.add(p)
                    reasons.append(f"主导动机[{primary_motivation}]推荐激活")

        # 次要动机映射
        if secondary_motivations:
            for sec_motivation in secondary_motivations:
                sec_mapping = self._motivation_mapping.get(sec_motivation)
                if sec_mapping:
                    for p in sec_mapping.mandatory_perspectives:
                        if p not in activated:
                            activated.add(p)
                            reasons.append(f"次要动机[{sec_motivation}]强制激活")

        # 关键词匹配增强
        if user_input and primary_mapping:
            keyword_matches = 0
            for keyword in primary_mapping.boost_keywords:
                if keyword.lower() in user_input.lower():
                    keyword_matches += 1

            if keyword_matches >= 2:
                reasons.append(f"关键词匹配增强（{keyword_matches}个关键词）")

        return list(activated), reasons

    def get_analysis_focus_for_motivation(self, motivation_id: str) -> List[str]:
        """获取指定动机类型的分析侧重点"""
        mapping = self._motivation_mapping.get(motivation_id)
        if mapping:
            return mapping.analysis_focus
        return []

    # ========================================================================
    # 维度完整性校验
    # ========================================================================

    def validate_analysis_result(
        self,
        analysis_data: Dict[str, Any],
    ) -> DimensionValidation:
        """
        校验分析结果的维度完整性

        Args:
            analysis_data: 分析结果数据

        Returns:
            校验结果
        """
        validation_config = self._config.get("validation", {})
        mandatory = validation_config.get("mandatory_dimensions", [])
        important = validation_config.get("important_dimensions", [])

        missing_mandatory = []
        missing_important = []
        suggestions = []

        # 检查强制维度
        for dim in mandatory:
            if not self._check_dimension_exists(dim, analysis_data):
                missing_mandatory.append(dim)
                suggestions.append(f"缺失强制维度: {dim}，需要重试")

        # 检查重要维度
        for dim in important:
            if not self._check_dimension_exists(dim, analysis_data):
                missing_important.append(dim)
                suggestions.append(f"缺失重要维度: {dim}，建议补充")

        # 计算质量分数
        total_dims = len(mandatory) + len(important)
        missing_count = len(missing_mandatory) + len(missing_important) * 0.5
        quality_score = max(0, (total_dims - missing_count) / total_dims) if total_dims > 0 else 1.0

        is_valid = len(missing_mandatory) == 0

        return DimensionValidation(
            is_valid=is_valid,
            missing_mandatory=missing_mandatory,
            missing_important=missing_important,
            quality_score=quality_score,
            suggestions=suggestions,
        )

    def _check_dimension_exists(self, dimension_id: str, data: Dict[str, Any]) -> bool:
        """检查维度是否存在且有效"""
        # 维度ID到数据字段的映射
        field_mapping = {
            "user_profile": "user_profile",
            "l1_facts": "analysis.l1_facts",
            "l2_models": "analysis.l2_models",
            "l3_tension": "analysis.l3_tension",
            "l4_jtbd": "analysis.l4_jtbd",
            "l5_sharpness": "analysis.l5_sharpness",
            "problem_solving_approach": "problem_solving_approach",
            "entity_extraction": "analysis.l1_facts",  # 别名
        }

        field_path = field_mapping.get(dimension_id, dimension_id)

        # 解析嵌套路径
        value = data
        for key in field_path.split("."):
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return False
            if value is None:
                return False

        # 检查值是否有效（非空字符串、非空列表、非空字典）
        if isinstance(value, str):
            return len(value.strip()) > 0
        if isinstance(value, (list, dict)):
            return len(value) > 0
        return value is not None

    def get_retry_config(self) -> Dict[str, Any]:
        """获取重试配置"""
        validation_config = self._config.get("validation", {})
        return validation_config.get(
            "retry",
            {
                "max_retries": 2,
                "retry_delay_seconds": 1,
                "retry_on_missing_mandatory": True,
                "retry_on_low_quality": True,
                "quality_threshold": 0.6,
            },
        )

    # ========================================================================
    # Prompt 生成辅助
    # ========================================================================

    def build_entity_extraction_prompt_section(self) -> str:
        """构建实体提取的 Prompt 片段"""
        entity_types = self.get_entity_types()

        lines = ["2. **实体提取**（配置驱动，必须识别以下6类实体）：\n"]
        lines.append("   | 类型 | 定义 | 必填字段 |")
        lines.append("   |------|------|----------|")

        for et in entity_types:
            fields_str = ", ".join([list(f.keys())[0] if isinstance(f, dict) else str(f) for f in et.required_fields])
            lines.append(f"   | {et.icon} {et.label} | {et.id} | {fields_str} |")

        lines.append("\n   ️ 提取要求：")
        for et in entity_types:
            for hint in et.extraction_hints:
                lines.append(f"   - {hint}")

        return "\n".join(lines)

    def build_perspective_selection_prompt_section(
        self,
        motivation_id: Optional[str] = None,
    ) -> str:
        """构建视角选择的 Prompt 片段"""
        base_perspectives = self.get_base_perspectives()
        extended_perspectives = self.get_extended_perspectives()

        lines = ["6. **L2 多视角建模**（配置驱动）\n"]

        # 基础视角
        lines.append("   基础视角（始终激活）：")
        for p in base_perspectives:
            lines.append(f"   - {p.id}: {p.description}")

        # 扩展视角
        lines.append("\n   扩展视角（条件激活）：")
        for p in extended_perspectives:
            lines.append(f"   - {p.id}: {p.description}")

        # 如果有动机类型，添加激活提示
        if motivation_id:
            mapping = self.get_motivation_mapping(motivation_id)
            if mapping and mapping.mandatory_perspectives:
                lines.append(f"\n   ️ 动机类型[{motivation_id}]强制激活视角：{', '.join(mapping.mandatory_perspectives)}")
                if mapping.analysis_focus:
                    lines.append("   分析侧重点：")
                    for focus in mapping.analysis_focus:
                        lines.append(f"   - {focus}")

        return "\n".join(lines)

    def build_human_dimensions_prompt_section(self) -> str:
        """构建人性化维度的 Prompt 片段"""
        dimensions = self.get_human_dimensions()

        if not dimensions:
            return ""

        lines = ["\n### 第四部分：人性化维度（可选，深层心理分析）\n"]

        for dim in dimensions:
            lines.append(f"**{dim.get('icon', '')} {dim.get('label', dim.get('id', ''))}**")
            lines.append(f"   描述：{dim.get('description', '')}")
            fields = dim.get("fields", [])
            if fields:
                lines.append("   字段：")
                for f in fields:
                    if isinstance(f, dict):
                        for k, v in f.items():
                            lines.append(f"   - {k}: {v}")
                    else:
                        lines.append(f"   - {f}")
            lines.append("")

        return "\n".join(lines)

    # ========================================================================
    # 前端展示配置
    # ========================================================================

    def get_display_config(self) -> Dict[str, Any]:
        """获取前端展示配置"""
        return self._config.get(
            "display",
            {
                "default_expanded": ["l3_tension", "problem_solving_approach"],
                "collapsed_by_default": ["l1_facts", "l2_models", "l5_sharpness", "human_dimensions"],
                "summary_fields": {},
            },
        )


# 全局单例
_dimensions_config: Optional[AnalysisDimensionsConfig] = None


def get_dimensions_config() -> AnalysisDimensionsConfig:
    """获取维度配置单例"""
    global _dimensions_config
    if _dimensions_config is None:
        _dimensions_config = AnalysisDimensionsConfig()
    return _dimensions_config


def reload_dimensions_config(config_dir: Optional[str] = None) -> Dict[str, Any]:
    """热更新维度配置"""
    config = get_dimensions_config()
    return config.reload(config_dir)
