"""
能力声明 Schema 定义（Ability Declaration Schemas）
=================================================

本模块定义了 12 Ability Core 能力声明的数据结构，用于：
1. 在专家配置文件中显式声明能力
2. 实现能力覆盖度追踪
3. 支持能力验证系统

创建日期: 2026-02-12
版本: v1.0
作者: Ability Core P1 Implementation
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


# ============================================================================
# 能力成熟度等级定义
# ============================================================================

AbilityMaturityLevel = Literal["L1", "L2", "L3", "L4", "L5"]

MATURITY_LEVEL_DESCRIPTIONS = {
    "L1": "基础应用 - 基本理解，能完成简单任务",
    "L2": "熟练掌握 - 独立应用，处理中等复杂度",
    "L3": "高级整合 - 系统化运用，跨能力协同",
    "L4": "创新突破 - 创造新方法，拓展边界",
    "L5": "大师级 - 定义标准，影响行业",
}


# ============================================================================
# 12 Ability Core 能力 ID 定义
# ============================================================================

AbilityID = Literal[
    "A1",  # 概念建构能力 (Concept Architecture)
    "A2",  # 空间结构能力 (Spatial Structuring)
    "A3",  # 叙事节奏能力 (Narrative Orchestration)
    "A4",  # 材料系统能力 (Material Intelligence)
    "A5",  # 灯光系统能力 (Lighting Architecture)
    "A6",  # 功能效率能力 (Functional Optimization)
    "A7",  # 资本策略能力 (Capital Strategy Intelligence)
    "A8",  # 技术整合能力 (Technology Integration)
    "A9",  # 社会关系建模能力 (Social Structure Modeling)
    "A10",  # 环境适应能力 (Environmental Adaptation)
    "A11",  # 运营与产品化能力 (Operation & Productization)
    "A12",  # 文明表达与跨学科整合能力 (Civilizational Expression)
]

ABILITY_NAMES = {
    "A1": "Concept Architecture (概念建构能力)",
    "A2": "Spatial Structuring (空间结构能力)",
    "A3": "Narrative Orchestration (叙事节奏能力)",
    "A4": "Material Intelligence (材料系统能力)",
    "A5": "Lighting Architecture (灯光系统能力)",
    "A6": "Functional Optimization (功能效率能力)",
    "A7": "Capital Strategy Intelligence (资本策略能力)",
    "A8": "Technology Integration (技术整合能力)",
    "A9": "Social Structure Modeling (社会关系建模能力)",
    "A10": "Environmental Adaptation (环境适应能力)",
    "A11": "Operation & Productization (运营与产品化能力)",
    "A12": "Civilizational Expression (文明表达与跨学科整合能力)",
}


# ============================================================================
# 能力声明数据模型
# ============================================================================


class AbilityDeclaration(BaseModel):
    """
    能力声明模型

    用于在专家配置文件中显式声明某个能力的：
    - 能力ID（A1-A12）
    - 能力名称（英文+中文）
    - 成熟度等级（L1-L5）
    - 子能力清单（可选）
    - 置信度（0.0-1.0）
    - 备注说明（可选）
    """

    id: AbilityID = Field(description="能力ID（A1-A12）")

    name: str = Field(description="能力英文名称（如 'Concept Architecture'）")

    maturity_level: AbilityMaturityLevel = Field(description="成熟度等级（L1基础/L2熟练/L3高级/L4创新/L5大师）")

    sub_abilities: List[str] = Field(
        default_factory=list, description="子能力ID列表（如 ['A9-1_power_distance', 'A9-2_privacy_hierarchy']）"
    )

    confidence: float = Field(default=0.9, ge=0.0, le=1.0, description="专家对该能力的置信度（0.0-1.0）")

    focus: Optional[str] = Field(default=None, description="能力聚焦方向（如 '住宅类项目'、'技术系统整合' 等）")

    note: Optional[str] = Field(default=None, description="备注说明")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "A9",
                "name": "Social Structure Modeling",
                "maturity_level": "L4",
                "sub_abilities": [
                    "A9-1_power_distance",
                    "A9-2_privacy_hierarchy",
                    "A9-3_conflict_buffer",
                    "A9-4_evolution_adaptability",
                ],
                "confidence": 0.9,
                "focus": "多代同堂住宅、复杂家庭关系",
                "note": "V7专家核心能力，填补A9系统性缺口",
            }
        }


class ExpertAbilityProfile(BaseModel):
    """
    专家能力档案模型

    用于完整描述一个专家所拥有的所有能力：
    - 主要能力（primary）：专家核心擅长的能力
    - 辅助能力（secondary）：专家可以提供支持的能力
    """

    primary: List[AbilityDeclaration] = Field(default_factory=list, description="主要能力列表（专家核心擅长的能力）")

    secondary: List[AbilityDeclaration] = Field(default_factory=list, description="辅助能力列表（专家可以提供支持的能力）")

    class Config:
        json_schema_extra = {
            "example": {
                "primary": [
                    {"id": "A9", "name": "Social Structure Modeling", "maturity_level": "L4", "confidence": 0.9},
                    {"id": "A3", "name": "Narrative Orchestration", "maturity_level": "L3", "confidence": 0.8},
                ],
                "secondary": [{"id": "A1", "name": "Concept Architecture", "maturity_level": "L2", "confidence": 0.6}],
            }
        }


# ============================================================================
# 能力覆盖分析模型
# ============================================================================


class AbilityCoverageReport(BaseModel):
    """
    能力覆盖报告模型

    用于分析整个专家系统中各能力的覆盖情况
    """

    ability_id: AbilityID
    ability_name: str
    expert_count: int = Field(description="拥有该能力的专家数量（主能力+辅助能力）")
    primary_experts: List[str] = Field(description="主要能力专家列表")
    secondary_experts: List[str] = Field(description="辅助能力专家列表")
    average_maturity_level: float = Field(description="平均成熟度（1.0-5.0）")
    coverage_rate: float = Field(ge=0.0, le=1.0, description="覆盖率（实际专家数 / 预期专家数）")
    coverage_status: Literal["excellent", "good", "fair", "weak", "critical"] = Field(description="覆盖状态评级")

    class Config:
        json_schema_extra = {
            "example": {
                "ability_id": "A9",
                "ability_name": "Social Structure Modeling (社会关系建模能力)",
                "expert_count": 2,
                "primary_experts": ["V7"],
                "secondary_experts": ["V3-1"],
                "average_maturity_level": 3.5,
                "coverage_rate": 0.7,
                "coverage_status": "good",
            }
        }


class SystemAbilityCoverageReport(BaseModel):
    """
    系统能力覆盖总报告

    包含所有12个能力的覆盖情况分析
    """

    report_date: str
    total_experts: int
    abilities: List[AbilityCoverageReport]
    overall_coverage_rate: float = Field(ge=0.0, le=1.0, description="整体覆盖率（所有能力的平均覆盖率）")
    weak_abilities: List[str] = Field(description="覆盖不足的能力ID列表（coverage_rate < 0.7）")
    critical_abilities: List[str] = Field(description="严重缺口的能力ID列表（coverage_rate < 0.5）")

    class Config:
        json_schema_extra = {
            "example": {
                "report_date": "2026-02-12",
                "total_experts": 25,
                "abilities": [],
                "overall_coverage_rate": 0.75,
                "weak_abilities": ["A10", "A12"],
                "critical_abilities": [],
            }
        }


# ============================================================================
# 辅助函数
# ============================================================================


def maturity_level_to_numeric(level: AbilityMaturityLevel) -> float:
    """将成熟度等级转换为数值（L1=1.0, L2=2.0, ..., L5=5.0）"""
    mapping = {"L1": 1.0, "L2": 2.0, "L3": 3.0, "L4": 4.0, "L5": 5.0}
    return mapping[level]


def numeric_to_maturity_level(value: float) -> AbilityMaturityLevel:
    """将数值转换为成熟度等级（四舍五入）"""
    rounded = round(value)
    mapping = {1: "L1", 2: "L2", 3: "L3", 4: "L4", 5: "L5"}
    return mapping.get(rounded, "L3")


def get_coverage_status(coverage_rate: float) -> str:
    """根据覆盖率返回状态评级"""
    if coverage_rate >= 0.9:
        return "excellent"
    elif coverage_rate >= 0.8:
        return "good"
    elif coverage_rate >= 0.7:
        return "fair"
    elif coverage_rate >= 0.5:
        return "weak"
    else:
        return "critical"
