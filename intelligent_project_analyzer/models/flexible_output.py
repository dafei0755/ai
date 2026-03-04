"""
Flexible Output Models - V6 Chief Engineer Roles
灵活输出模型 - V6 专业总工程师角色库

实现方案D：混合架构（双模式输出）
- Targeted模式：针对性问答
- Comprehensive模式：完整报告

已实现：
- V6-1: 结构与幕墙工程师
- V6-2: 机电与智能化工程师
- V6-3: 室内工艺与材料专家
- V6-4: 成本与价值工程师
"""

from enum import Enum
from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field, model_validator


class OutputMode(str, Enum):
    """输出模式枚举"""
    TARGETED = "targeted"          # 针对性问答模式
    COMPREHENSIVE = "comprehensive"  # 完整报告模式


class TechnicalOption(BaseModel):
    """单一技术选项模型"""
    option_name: str = Field(description="方案名称，如：'钢框架-支撑体系', '单元式玻璃幕墙'")
    advantages: List[str] = Field(description="该方案的优点列表，如：'成本低', '施工速度快'")
    disadvantages: List[str] = Field(description="该方案的缺点列表，如：'对建筑形态限制大', '外观效果一般'")
    estimated_cost_level: str = Field(description="预估造价水平，使用'高', '中', '低'来描述")


class KeyNodeAnalysis(BaseModel):
    """单一关键技术节点分析模型"""
    node_name: str = Field(description="关键节点名称，如：'大跨度屋顶', '自由曲面转角', '超大玻璃肋'")
    challenge: str = Field(description="该节点的核心技术挑战")
    proposed_solution: str = Field(description="初步建议的解决方案")


class V6_1_FlexibleOutput(BaseModel):
    """
    V6-1 结构与幕墙工程师 - 灵活输出模型

    设计原则：
    1. 双模式架构：针对性问答 vs 完整报告
    2. 必需字段最小化：仅保留元数据层
    3. 灵活性与类型安全的平衡
    """

    # ===== 第一层：元数据（必需） =====
    output_mode: Literal["targeted", "comprehensive"] = Field(
        description="""
        输出模式：
        - targeted: 针对性问答模式，回答用户的单一问题
        - comprehensive: 完整报告模式，提供系统性的全面分析
        """
    )

    user_question_focus: str = Field(
        description="""
        用户问题的核心关注点，简洁明确（≤15字）

        示例（Targeted模式）:
        - "结构方案比选"
        - "幕墙成本优化"
        - "技术风险评估"

        示例（Comprehensive模式）:
        - "结构与幕墙完整技术分析"
        - "项目可行性综合评估"
        """
    )

    confidence: float = Field(
        description="分析置信度 (0.0-1.0)",
        ge=0,
        le=1
    )

    design_rationale: str = Field(
        description="""
        核心设计立场和选择依据（v3.5必填）

        Targeted模式：解释为何采用这种分析角度和方法
        Comprehensive模式：解释整体技术策略和设计思路
        """
    )

    # ===== 第二层：标准字段（完整报告模式必需，针对性模式可选） =====
    feasibility_assessment: str | None = Field(
        None,
        description="""
        【Comprehensive模式必需】对V2设计意图的综合技术可行性评估
        明确指出哪些是常规技术可实现的，哪些是具有高度挑战性的
        """
    )

    structural_system_options: List[TechnicalOption] | None = Field(
        None,
        description="""
        【Comprehensive模式必需】针对建筑主体，提出至少两种结构体系方案
        进行优缺点和经济性比较
        """
    )

    facade_system_options: List[TechnicalOption] | None = Field(
        None,
        description="""
        【Comprehensive模式必需】针对建筑外立面，提出至少两种幕墙/表皮系统方案
        进行优缺点和经济性比较
        """
    )

    key_technical_nodes: List[KeyNodeAnalysis] | None = Field(
        None,
        description="""
        【Comprehensive模式必需】识别并分析方案中最重要的2-3个关键技术节点
        及其初步解决方案
        """
    )

    risk_analysis_and_recommendations: str | None = Field(
        None,
        description="""
        【Comprehensive模式必需】对潜在的结构与幕墙风险进行分析
        （如超限、变形、漏水），并提出需要优先进行深化设计或实验验证的建议
        """
    )

    # ===== 第三层：灵活内容区（针对性模式的核心输出） =====
    targeted_analysis: Dict[str, Any] | None = Field(
        None,
        description="""
        【Targeted模式核心字段】根据user_question_focus动态生成的专项分析

        结构建议（根据问题类型选择）:

         类型1: 方案比选类（如"有哪些结构方案?"）
        {
          "comparison_matrix": [
            {
              "option_name": "方案A",
              "advantages": [...],
              "disadvantages": [...],
              "cost_level": "高/中/低",
              "applicability": "适用场景描述"
            }
          ],
          "recommendation": "基于项目特点的推荐方案",
          "decision_framework": "决策考量的关键维度"
        }

         类型2: 优化建议类（如"如何优化XX?"）
        {
          "current_state_diagnosis": "现状问题诊断",
          "optimization_proposals": [
            {
              "strategy": "优化策略名称",
              "implementation_steps": [...],
              "expected_improvement": "预期提升效果",
              "implementation_difficulty": "难度评估"
            }
          ],
          "priority_ranking": "优化行动优先级排序"
        }

        ️ 类型3: 风险评估类（如"有什么风险?"）
        {
          "risk_catalog": [
            {
              "risk_item": "风险项名称",
              "severity": "高/中/低",
              "probability": "发生概率",
              "impact": "潜在影响",
              "mitigation_strategy": "规避措施"
            }
          ],
          "critical_risks": "需优先关注的关键风险",
          "monitoring_plan": "风险监控建议"
        }

         类型4: 成本分析类（如"如何控制成本?"）
        {
          "cost_drivers": "成本主要驱动因素",
          "cost_reduction_strategies": [
            {
              "strategy": "降本策略",
              "potential_saving": "预计节省金额/比例",
              "quality_impact": "对质量的影响",
              "feasibility": "可行性评估"
            }
          ],
          "value_engineering_recommendations": "价值工程建议"
        }

        ️ 重要提示：
        - 以上模板仅为参考，可根据具体问题灵活调整
        - 关键原则：结构清晰、信息完整、针对性强
        - 避免在targeted_analysis中塞入与问题无关的内容
        """
    )

    # ===== 第四层：扩展性保障 =====
    supplementary_insights: Dict[str, Any] | None = Field(
        None,
        description="""
        补充性洞察或跨领域分析
        用于提供额外的、对决策有价值的信息
        """
    )

    # ===== v3.5 Expert Autonomy Protocol 扩展字段 =====
    expert_handoff_response: Dict[str, Any] | None = Field(
        None,
        description="对expert_handoff的结构化响应（v3.5协议）"
    )

    challenge_flags: List[Dict[str, str]] | None = Field(
        None,
        description="挑战标记列表（如有）（v3.5协议）"
    )

    @model_validator(mode='after')
    def validate_output_consistency(self):
        """
        验证输出一致性

        规则：
        1. Comprehensive模式：所有标准字段必需填充
        2. Targeted模式：targeted_analysis必需填充
        3. 两种模式不能混用
        """
        mode = self.output_mode

        if mode == 'comprehensive':
            # 完整报告模式：检查所有标准字段是否填充
            required_fields = [
                'feasibility_assessment',
                'structural_system_options',
                'facade_system_options',
                'key_technical_nodes',
                'risk_analysis_and_recommendations'
            ]

            missing = [f for f in required_fields if not getattr(self, f)]
            if missing:
                raise ValueError(
                    f"️ Comprehensive模式下必需字段缺失: {', '.join(missing)}\n"
                    f"完整报告模式要求提供系统性的全面分析，请填充所有标准字段。"
                )

        elif mode == 'targeted':
            # 针对性模式：检查targeted_analysis是否填充
            if not self.targeted_analysis:
                raise ValueError(
                    "️ Targeted模式下必须填充targeted_analysis字段\n"
                    "针对性模式要求直接回答用户的核心问题，请在targeted_analysis中提供专项分析。"
                )

            # 可选：警告如果在Targeted模式下填充了标准字段（可能是冗余）
            standard_fields_filled = [
                f for f in ['feasibility_assessment', 'structural_system_options',
                           'facade_system_options', 'key_technical_nodes',
                           'risk_analysis_and_recommendations']
                if getattr(self, f) is not None
            ]
            if standard_fields_filled:
                import warnings
                warnings.warn(
                    f"️ Targeted模式下不建议填充标准字段：{', '.join(standard_fields_filled)}\n"
                    f"这可能导致输出冗余。针对性模式应聚焦于targeted_analysis字段。",
                    UserWarning
                )

        return self

    class Config:
        """Pydantic配置"""
        # 允许字段别名（Pydantic v2）
        populate_by_name = True


# ===== 使用示例 =====
if __name__ == "__main__":
    # 示例1: Targeted模式 - 方案比选
    targeted_example = V6_1_FlexibleOutput(
        output_mode="targeted",
        user_question_focus="结构方案比选",
        confidence=0.92,
        design_rationale="基于项目的大跨度需求和成本约束，推荐钢结构和混凝土结构两种方案进行对比分析",
        targeted_analysis={
            "comparison_matrix": [
                {
                    "option_name": "空间钢桁架体系",
                    "advantages": ["能实现大跨度", "自重较轻", "施工速度快"],
                    "disadvantages": ["用钢量大", "造价偏高", "防火处理复杂"],
                    "cost_level": "高",
                    "applicability": "适用于跨度>50米的大空间建筑"
                },
                {
                    "option_name": "预应力混凝土梁",
                    "advantages": ["整体性好", "耐久性强", "防火性能好"],
                    "disadvantages": ["自重大", "施工周期长", "跨度受限"],
                    "cost_level": "中",
                    "applicability": "适用于跨度30-50米的常规建筑"
                }
            ],
            "recommendation": "综合考虑项目特点，建议采用空间钢桁架体系",
            "decision_framework": "关键决策维度：跨度能力(权重40%) > 成本(30%) > 施工周期(30%)"
        }
    )

    print("=" * 60)
    print("示例1: Targeted模式 - 方案比选")
    print("=" * 60)
    print(targeted_example.model_dump_json(indent=2))

    # 示例2: Comprehensive模式 - 完整报告
    comprehensive_example = V6_1_FlexibleOutput(
        output_mode="comprehensive",
        user_question_focus="结构与幕墙完整技术分析",
        confidence=0.95,
        design_rationale="针对本项目的复杂曲面形态，采用结构与幕墙一体化设计策略",
        feasibility_assessment="V2提出的流动的丝带建筑形态具有高度挑战性，但总体技术上是可行的...",
        structural_system_options=[
            TechnicalOption(
                option_name="空间钢桁架体系",
                advantages=["能实现大跨度", "自重较轻"],
                disadvantages=["用钢量大", "造价偏高"],
                estimated_cost_level="高"
            )
        ],
        facade_system_options=[
            TechnicalOption(
                option_name="参数化单元式幕墙",
                advantages=["工厂预制", "质量可控"],
                disadvantages=["造价极高", "深化工作量大"],
                estimated_cost_level="高"
            )
        ],
        key_technical_nodes=[
            KeyNodeAnalysis(
                node_name="屋顶无柱大跨度中庭",
                challenge="如何在不设置柱子的情况下覆盖80m x 50m的空间",
                proposed_solution="建议采用正交张弦梁结构，通过预应力钢索提供向上支撑力"
            )
        ],
        risk_analysis_and_recommendations="主要风险：1. 幕墙成本超支风险...; 2. 结构变形风险..."
    )

    print("\n" + "=" * 60)
    print("示例2: Comprehensive模式 - 完整报告")
    print("=" * 60)
    print(comprehensive_example.model_dump_json(indent=2))

    # 示例3: 错误示例 - Targeted模式缺少targeted_analysis
    try:
        invalid_example = V6_1_FlexibleOutput(
            output_mode="targeted",
            user_question_focus="成本优化",
            confidence=0.90,
            design_rationale="测试"
            # 缺少targeted_analysis - 应该报错
        )
    except ValueError as e:
        print("\n" + "=" * 60)
        print("示例3: 验证器捕获错误")
        print("=" * 60)
        print(f" 成功捕获错误: {e}")


# ===== V6-2: 机电与智能化工程师 =====

class SystemSolution(BaseModel):
    """单一机电系统解决方案模型"""
    system_name: str = Field(description="系统名称，如：'暖通空调系统 (HVAC)', '智能照明系统'")
    recommended_solution: str = Field(description="推荐的系统方案或技术选型")
    reasoning: str = Field(description="选择此方案的理由，需结合节能、舒适度、成本和与建筑的整合性")
    impact_on_architecture: str = Field(description="该系统对建筑空间产生的具体影响")


class SmartScenario(BaseModel):
    """单一智能化场景模型"""
    scenario_name: str = Field(description="智能化场景名称，如：'会议模式', '节能离场模式'")
    description: str = Field(description="该场景的用户体验描述")
    triggered_systems: List[str] = Field(description="触发此场景时，联动的机电系统列表")


class V6_2_FlexibleOutput(BaseModel):
    """
    V6-2 机电与智能化工程师 - 灵活输出模型

    设计原则：
    1. 双模式架构：针对性问答 vs 完整报告
    2. 必需字段最小化：仅保留元数据层
    3. 灵活性与类型安全的平衡
    """

    # ===== 第一层：元数据（必需） =====
    output_mode: Literal["targeted", "comprehensive"] = Field(
        description="""
        输出模式：
        - targeted: 针对性问答模式，回答用户的单一问题
        - comprehensive: 完整报告模式，提供系统性的全面分析
        """
    )

    user_question_focus: str = Field(
        description="""
        用户问题的核心关注点，简洁明确（≤15字）

        示例（Targeted模式）:
        - "HVAC系统选型"
        - "节能优化策略"
        - "智能化场景设计"

        示例（Comprehensive模式）:
        - "机电与智能化完整技术分析"
        - "MEP系统综合评估"
        """
    )

    confidence: float = Field(
        description="分析置信度 (0.0-1.0)",
        ge=0,
        le=1
    )

    design_rationale: str = Field(
        description="""
        核心设计立场和选择依据（v3.5必填）

        Targeted模式：解释为何采用这种分析角度和方法
        Comprehensive模式：解释整体机电策略和技术思路
        """
    )

    # ===== 第二层：标准字段（完整报告模式必需，针对性模式可选） =====
    mep_overall_strategy: str | None = Field(
        None,
        description="""
        【Comprehensive模式必需】机电总体策略
        阐述本次机电设计的核心目标和主要技术路径
        """
    )

    system_solutions: List[SystemSolution] | None = Field(
        None,
        description="""
        【Comprehensive模式必需】核心机电系统解决方案列表
        至少包含暖通、电气、给排水三大系统
        """
    )

    smart_building_scenarios: List[SmartScenario] | None = Field(
        None,
        description="""
        【Comprehensive模式必需】智能化解决方案
        通过具体的用户场景来描述智能化系统将如何提升空间体验和运营效率
        """
    )

    coordination_and_clash_points: str | None = Field(
        None,
        description="""
        【Comprehensive模式必需】与其他专业的协同与碰撞点
        明确指出机电系统与结构、幕墙、内装等专业最主要的矛盾点及建议的解决方案
        """
    )

    sustainability_and_energy_saving: str | None = Field(
        None,
        description="""
        【Comprehensive模式必需】可持续与节能策略
        列出本项目中采用的主要绿色建筑技术和预期节能目标
        """
    )

    # ===== 第三层：灵活内容区（针对性模式的核心输出） =====
    targeted_analysis: Dict[str, Any] | None = Field(
        None,
        description="""
        【Targeted模式核心字段】根据user_question_focus动态生成的专项分析

        结构建议（根据问题类型选择）:

         类型1: 系统比选类（如"HVAC系统有哪些方案?"）
        {
          "comparison_matrix": [
            {
              "system_name": "方案A",
              "advantages": [...],
              "disadvantages": [...],
              "energy_efficiency": "高/中/低",
              "initial_cost": "高/中/低",
              "applicability": "适用场景描述"
            }
          ],
          "recommendation": "基于项目特点的推荐方案",
          "decision_framework": "决策考量的关键维度"
        }

         类型2: 节能优化类（如"如何降低能耗?"）
        {
          "current_energy_diagnosis": "当前能耗问题诊断",
          "optimization_measures": [
            {
              "measure": "优化措施名称",
              "implementation_steps": [...],
              "expected_saving": "预期节能效果",
              "payback_period": "投资回收期",
              "implementation_difficulty": "难度评估"
            }
          ],
          "priority_ranking": "优化措施优先级排序"
        }

         类型3: 专业协调类（如"机电与结构如何协同?"）
        {
          "coordination_challenges": [
            {
              "challenge_item": "协调难点名称",
              "affected_disciplines": ["机电", "结构", "幕墙"],
              "impact": "对项目的影响",
              "proposed_solution": "协同解决方案",
              "coordination_timing": "协调时机"
            }
          ],
          "bim_collaboration_strategy": "BIM协同策略",
          "critical_coordination_nodes": "关键协同节点"
        }

         类型4: 智能化场景设计类（如"如何设计会议模式?"）
        {
          "scenario_details": {
            "scenario_name": "场景名称",
            "user_journey": "用户体验旅程描述",
            "triggered_systems": [...],
            "system_interactions": "系统联动逻辑",
            "fallback_strategy": "异常处理策略"
          },
          "hardware_requirements": "硬件需求清单",
          "software_logic": "软件逻辑描述",
          "user_interaction": "用户交互方式"
        }

        ️ 重要提示：
        - 以上模板仅为参考，可根据具体问题灵活调整
        - 关键原则：结构清晰、信息完整、针对性强
        - 避免在targeted_analysis中塞入与问题无关的内容
        """
    )

    # ===== 第四层：扩展性保障 =====
    supplementary_insights: Dict[str, Any] | None = Field(
        None,
        description="""
        补充性洞察或跨领域分析
        用于提供额外的、对决策有价值的信息
        """
    )

    # ===== v3.5 Expert Autonomy Protocol 扩展字段 =====
    expert_handoff_response: Dict[str, Any] | None = Field(
        None,
        description="对expert_handoff的结构化响应（v3.5协议）"
    )

    challenge_flags: List[Dict[str, str]] | None = Field(
        None,
        description="挑战标记列表（如有）（v3.5协议）"
    )

    @model_validator(mode='after')
    def validate_output_consistency(self):
        """
        验证输出一致性

        规则：
        1. Comprehensive模式：所有标准字段必需填充
        2. Targeted模式：targeted_analysis必需填充
        3. 两种模式不能混用
        """
        mode = self.output_mode

        if mode == 'comprehensive':
            # 完整报告模式：检查所有标准字段是否填充
            required_fields = [
                'mep_overall_strategy',
                'system_solutions',
                'smart_building_scenarios',
                'coordination_and_clash_points',
                'sustainability_and_energy_saving'
            ]

            missing = [f for f in required_fields if not getattr(self, f)]
            if missing:
                raise ValueError(
                    f"️ Comprehensive模式下必需字段缺失: {', '.join(missing)}\n"
                    f"完整报告模式要求提供系统性的全面分析，请填充所有标准字段。"
                )

        elif mode == 'targeted':
            # 针对性模式：检查targeted_analysis是否填充
            if not self.targeted_analysis:
                raise ValueError(
                    "️ Targeted模式下必须填充targeted_analysis字段\n"
                    "针对性模式要求直接回答用户的核心问题，请在targeted_analysis中提供专项分析。"
                )

            # 可选：警告如果在Targeted模式下填充了标准字段（可能是冗余）
            standard_fields_filled = [
                f for f in ['mep_overall_strategy', 'system_solutions',
                           'smart_building_scenarios', 'coordination_and_clash_points',
                           'sustainability_and_energy_saving']
                if getattr(self, f) is not None
            ]
            if standard_fields_filled:
                import warnings
                warnings.warn(
                    f"️ Targeted模式下不建议填充标准字段：{', '.join(standard_fields_filled)}\n"
                    f"这可能导致输出冗余。针对性模式应聚焦于targeted_analysis字段。",
                    UserWarning
                )

        return self

    class Config:
        """Pydantic配置"""
        # 允许字段别名（Pydantic v2）
        populate_by_name = True
    class Config:
        """Pydantic配置"""
        populate_by_name = True


# ===== V6-3: 室内工艺与材料专家 =====

class MaterialSpec(BaseModel):
    """单一关键材料规格模型"""
    material_name: str = Field(description="材料名称")
    application_area: str = Field(description="该材料主要应用的区域")
    key_specifications: List[str] = Field(description="关键技术规格列表")
    reasoning: str = Field(description="选择此材料的原因")


class NodeDetail(BaseModel):
    """单一关键节点深化方案模型"""
    node_name: str = Field(description="节点名称")
    challenge: str = Field(description="施工难点和核心挑战")
    proposed_solution: str = Field(description="建议的深化设计方案")


class V6_3_FlexibleOutput(BaseModel):
    """V6-3 室内工艺与材料专家 - 灵活输出模型"""
    output_mode: Literal["targeted", "comprehensive"]
    user_question_focus: str
    confidence: float = Field(ge=0, le=1)
    design_rationale: str
    
    craftsmanship_strategy: str | None = None
    key_material_specifications: List[MaterialSpec] | None = None
    critical_node_details: List[NodeDetail] | None = None
    quality_control_and_mockup: str | None = None
    risk_analysis: str | None = None
    
    targeted_analysis: Dict[str, Any] | None = None
    expert_handoff_response: Dict[str, Any] | None = None
    challenge_flags: List[Dict[str, str]] | None = None

    @model_validator(mode="after")
    def validate_output_consistency(self):
        mode = self.output_mode
        if mode == "comprehensive":
            required_fields = ["craftsmanship_strategy", "key_material_specifications", "critical_node_details", "quality_control_and_mockup", "risk_analysis"]
            missing = [f for f in required_fields if not getattr(self, f)]
            if missing:
                raise ValueError(f"️ Comprehensive模式下必需字段缺失: {', '.join(missing)}")
        elif mode == "targeted":
            if not self.targeted_analysis:
                raise ValueError("️ Targeted模式下必须填充targeted_analysis字段")
        return self

    class Config:
        populate_by_name = True


# ===== V6-4: 成本与价值工程师 =====

class CostBreakdown(BaseModel):
    """成本构成模型"""
    category: str
    percentage: int
    cost_drivers: List[str]


class VEOption(BaseModel):
    """价值工程选项模型"""
    area: str
    original_scheme: str
    proposed_option: str
    impact_analysis: str


class V6_4_FlexibleOutput(BaseModel):
    """V6-4 成本与价值工程师 - 灵活输出模型"""
    output_mode: Literal["targeted", "comprehensive"]
    user_question_focus: str
    confidence: float = Field(ge=0, le=1)
    design_rationale: str
    
    cost_estimation_summary: str | None = None
    cost_breakdown_analysis: List[CostBreakdown] | None = None
    value_engineering_options: List[VEOption] | None = None
    budget_control_strategy: str | None = None
    cost_overrun_risk_analysis: str | None = None
    
    targeted_analysis: Dict[str, Any] | None = None
    expert_handoff_response: Dict[str, Any] | None = None
    challenge_flags: List[Dict[str, str]] | None = None

    @model_validator(mode="after")
    def validate_output_consistency(self):
        mode = self.output_mode
        if mode == "comprehensive":
            required_fields = ["cost_estimation_summary", "cost_breakdown_analysis", "value_engineering_options", "budget_control_strategy", "cost_overrun_risk_analysis"]
            missing = [f for f in required_fields if not getattr(self, f)]
            if missing:
                raise ValueError(f"️ Comprehensive模式下必需字段缺失: {', '.join(missing)}")
        elif mode == "targeted":
            if not self.targeted_analysis:
                raise ValueError("️ Targeted模式下必须填充targeted_analysis字段")
        return self

    class Config:
        populate_by_name = True


# ===== V5-1: 居住场景与生活方式专家 =====

class FamilyMemberProfile(BaseModel):
    """单一家庭成员画像与空间需求模型"""
    member: str = Field(description="成员称谓，如：'男主人', '女主人', '长子(10岁)'")
    daily_routine: str = Field(description="该成员典型的'一日生活剧本'")
    spatial_needs: List[str] = Field(description="该成员最核心的空间需求列表")
    storage_needs: List[str] = Field(description="该成员主要的收纳需求列表（量化）")


class DesignChallenge(BaseModel):
    """单一设计挑战模型"""
    challenge: str = Field(description="一个明确的设计挑战，以'如何...(How might we...)'句式提出")
    context: str = Field(description="该挑战产生的背景和原因")
    constraints: List[str] = Field(description="设计必须遵守的约束条件列表")


class V5_1_FlexibleOutput(BaseModel):
    """V5-1 居住场景与生活方式专家 - 灵活输出模型"""
    output_mode: Literal["targeted", "comprehensive"]
    user_question_focus: str
    confidence: float = Field(ge=0, le=1)
    design_rationale: str
    
    # 标准字段（Comprehensive模式必需）
    family_profile_and_needs: List[FamilyMemberProfile] | None = None
    operational_blueprint: str | None = None
    key_performance_indicators: List[str] | None = None
    design_challenges_for_v2: List[DesignChallenge] | None = None
    
    # 灵活内容区（Targeted模式核心输出）
    targeted_analysis: Dict[str, Any] | None = None
    
    # v3.5协议字段
    expert_handoff_response: Dict[str, Any] | None = None
    challenge_flags: List[Dict[str, str]] | None = None

    @model_validator(mode="after")
    def validate_output_consistency(self):
        mode = self.output_mode
        if mode == "comprehensive":
            required_fields = ["family_profile_and_needs", "operational_blueprint", "key_performance_indicators", "design_challenges_for_v2"]
            missing = [f for f in required_fields if not getattr(self, f)]
            if missing:
                raise ValueError(f"️ Comprehensive模式下必需字段缺失: {', '.join(missing)}")
        elif mode == "targeted":
            if not self.targeted_analysis:
                raise ValueError("️ Targeted模式下必须填充targeted_analysis字段")
        return self

    class Config:
        populate_by_name = True


# ===== V5-2: 商业零售运营专家 =====

class RetailKPI(BaseModel):
    """单一零售KPI模型"""
    metric: str = Field(description="指标名称，如：'顾客平均停留时间'")
    target: str = Field(description="该指标的具体目标值")
    spatial_strategy: str = Field(description="为达成此目标，空间设计需要采取的关键策略")


class V5_2_FlexibleOutput(BaseModel):
    """V5-2 商业零售运营专家 - 灵活输出模型"""
    output_mode: Literal["targeted", "comprehensive"]
    user_question_focus: str
    confidence: float = Field(ge=0, le=1)
    design_rationale: str
    
    # 标准字段（Comprehensive模式必需）
    business_goal_analysis: str | None = None
    operational_blueprint: str | None = None
    key_performance_indicators: List[RetailKPI] | None = None
    design_challenges_for_v2: List[DesignChallenge] | None = None
    
    # 灵活内容区（Targeted模式核心输出）
    targeted_analysis: Dict[str, Any] | None = None
    
    # v3.5协议字段
    expert_handoff_response: Dict[str, Any] | None = None
    challenge_flags: List[Dict[str, str]] | None = None

    @model_validator(mode="after")
    def validate_output_consistency(self):
        mode = self.output_mode
        if mode == "comprehensive":
            required_fields = ["business_goal_analysis", "operational_blueprint", "key_performance_indicators", "design_challenges_for_v2"]
            missing = [f for f in required_fields if not getattr(self, f)]
            if missing:
                raise ValueError(f"️ Comprehensive模式下必需字段缺失: {', '.join(missing)}")
        elif mode == "targeted":
            if not self.targeted_analysis:
                raise ValueError("️ Targeted模式下必须填充targeted_analysis字段")
        return self

    class Config:
        populate_by_name = True


# ===== V2-1: 居住空间设计总监 =====

class V2_1_FlexibleOutput(BaseModel):
    """V2-1 居住空间设计总监 - 灵活输出模型"""
    output_mode: Literal["targeted", "comprehensive"]
    user_question_focus: str
    confidence: float = Field(ge=0, le=1)
    decision_rationale: str  # V2专用：设计决策权衡逻辑
    
    # 标准字段（Comprehensive模式必需）
    project_vision_summary: str | None = None
    spatial_concept: str | None = None
    narrative_translation: str | None = None
    aesthetic_framework: str | None = None
    functional_planning: str | None = None
    material_palette: str | None = None
    implementation_guidance: str | None = None
    
    # 灵活内容区（Targeted模式核心输出）
    targeted_analysis: Dict[str, Any] | None = None
    
    # v3.5协议字段
    expert_handoff_response: Dict[str, Any] | None = None
    challenge_flags: List[Dict[str, str]] | None = None

    @model_validator(mode="after")
    def validate_output_consistency(self):
        mode = self.output_mode
        if mode == "comprehensive":
            required_fields = ["project_vision_summary", "spatial_concept", "narrative_translation", 
                             "aesthetic_framework", "functional_planning", "material_palette", 
                             "implementation_guidance"]
            missing = [f for f in required_fields if not getattr(self, f)]
            if missing:
                raise ValueError(f"️ Comprehensive模式下必需字段缺失: {', '.join(missing)}")
        elif mode == "targeted":
            if not self.targeted_analysis:
                raise ValueError("️ Targeted模式下必须填充targeted_analysis字段")
        return self

    class Config:
        populate_by_name = True


# ===== V2-2: 商业空间设计总监 =====

class V2_2_FlexibleOutput(BaseModel):
    """V2-2 商业空间设计总监 - 灵活输出模型"""
    output_mode: Literal["targeted", "comprehensive"]
    user_question_focus: str
    confidence: float = Field(ge=0, le=1)
    decision_rationale: str  # V2专用：设计决策权衡逻辑
    
    # 标准字段（Comprehensive模式必需）
    project_vision_summary: str | None = None
    spatial_concept: str | None = None
    business_strategy_translation: str | None = None  # V2-2专用：商业策略转译
    aesthetic_framework: str | None = None
    functional_planning: str | None = None
    material_palette: str | None = None
    implementation_guidance: str | None = None
    
    # 灵活内容区（Targeted模式核心输出）
    targeted_analysis: Dict[str, Any] | None = None
    
    # v3.5协议字段
    expert_handoff_response: Dict[str, Any] | None = None
    challenge_flags: List[Dict[str, str]] | None = None

    @model_validator(mode="after")
    def validate_output_consistency(self):
        mode = self.output_mode
        if mode == "comprehensive":
            required_fields = ["project_vision_summary", "spatial_concept", "business_strategy_translation", 
                             "aesthetic_framework", "functional_planning", "material_palette", 
                             "implementation_guidance"]
            missing = [f for f in required_fields if not getattr(self, f)]
            if missing:
                raise ValueError(f"️ Comprehensive模式下必需字段缺失: {', '.join(missing)}")
        elif mode == "targeted":
            if not self.targeted_analysis:
                raise ValueError("️ Targeted模式下必须填充targeted_analysis字段")
        return self

    class Config:
        populate_by_name = True


# ===== V3-2: 品牌叙事与顾客体验专家 =====

class TouchpointScript(BaseModel):
    """单一体验触点脚本模型"""
    touchpoint_name: str = Field(description="触点名称")
    emotional_goal: str = Field(description="情感目标")
    sensory_script: str = Field(description="五感设计脚本")


class V3_2_FlexibleOutput(BaseModel):
    """V3-2 品牌叙事与顾客体验专家 - 灵活输出模型"""
    output_mode: Literal["targeted", "comprehensive"]
    user_question_focus: str
    confidence: float = Field(ge=0, le=1)
    design_rationale: str
    
    # 标准字段（Comprehensive模式必需）
    brand_narrative_core: str | None = None
    customer_archetype: str | None = None
    emotional_journey_map: str | None = None
    key_touchpoint_scripts: List[TouchpointScript] | None = None
    narrative_guidelines_for_v2: str | None = None
    
    # 灵活内容区（Targeted模式核心输出）
    targeted_analysis: Dict[str, Any] | None = None
    
    # v3.5协议字段
    expert_handoff_response: Dict[str, Any] | None = None
    challenge_flags: List[Dict[str, str]] | None = None

    @model_validator(mode="after")
    def validate_output_consistency(self):
        mode = self.output_mode
        if mode == "comprehensive":
            required_fields = ["brand_narrative_core", "customer_archetype", "emotional_journey_map", 
                             "key_touchpoint_scripts", "narrative_guidelines_for_v2"]
            missing = [f for f in required_fields if not getattr(self, f)]
            if missing:
                raise ValueError(f"️ Comprehensive模式下必需字段缺失: {', '.join(missing)}")
        elif mode == "targeted":
            if not self.targeted_analysis:
                raise ValueError("️ Targeted模式下必须填充targeted_analysis字段")
        return self

    class Config:
        populate_by_name = True


# ===== V4-1: 设计研究者 =====

class V4_1_FlexibleOutput(BaseModel):
    """V4-1 设计研究者 - 灵活输出模型"""
    output_mode: Literal["targeted", "comprehensive"]
    user_question_focus: str
    confidence: float = Field(ge=0, le=1)
    design_rationale: str
    
    # 标准字段（Comprehensive模式必需）
    research_focus: str | None = None
    methodology: str | None = None
    key_findings: List[str] | None = None
    design_implications: str | None = None
    evidence_base: str | None = None
    
    # 灵活内容区（Targeted模式核心输出）
    targeted_analysis: Dict[str, Any] | None = None
    
    # v3.5协议字段
    expert_handoff_response: Dict[str, Any] | None = None
    challenge_flags: List[Dict[str, str]] | None = None

    @model_validator(mode="after")
    def validate_output_consistency(self):
        mode = self.output_mode
        if mode == "comprehensive":
            required_fields = ["research_focus", "methodology", "key_findings", 
                             "design_implications", "evidence_base"]
            missing = [f for f in required_fields if not getattr(self, f)]
            if missing:
                raise ValueError(f"️ Comprehensive模式下必需字段缺失: {', '.join(missing)}")
        elif mode == "targeted":
            if not self.targeted_analysis:
                raise ValueError("️ Targeted模式下必须填充targeted_analysis字段")
        return self

    class Config:
        populate_by_name = True


# ===== V5-0: 通用场景策略师 =====

class ScenarioInsight(BaseModel):
    """场景洞察模型"""
    insight_type: str = Field(description="洞察类型")
    description: str = Field(description="洞察描述")
    design_implications: List[str] = Field(description="对设计的启示")


class V5_0_FlexibleOutput(BaseModel):
    """V5-0 通用场景策略师 - 灵活输出模型"""
    output_mode: Literal["targeted", "comprehensive"]
    user_question_focus: str
    confidence: float = Field(ge=0, le=1)
    design_rationale: str
    
    scenario_deconstruction: str | None = None
    operational_logic: str | None = None
    stakeholder_analysis: str | None = None
    key_performance_indicators: List[str] | None = None
    design_challenges_for_v2: List[DesignChallenge] | None = None
    
    targeted_analysis: Dict[str, Any] | None = None
    
    expert_handoff_response: Dict[str, Any] | None = None
    challenge_flags: List[Dict[str, str]] | None = None

    @model_validator(mode="after")
    def validate_output_consistency(self):
        mode = self.output_mode
        if mode == "comprehensive":
            required_fields = ["scenario_deconstruction", "operational_logic", "stakeholder_analysis", "key_performance_indicators", "design_challenges_for_v2"]
            missing = [f for f in required_fields if not getattr(self, f)]
            if missing:
                raise ValueError(f"Comprehensive mode missing required fields: {', '.join(missing)}")
        elif mode == "targeted":
            if not self.targeted_analysis:
                raise ValueError("Targeted mode requires targeted_analysis field")
        return self

    class Config:
        populate_by_name = True


# ===== V2-0: 项目设计总监 =====

class SubprojectBrief(BaseModel):
    """子项目简要模型"""
    subproject_name: str
    area_sqm: float | None = None
    key_requirements: List[str]
    design_priority: str


class V2_0_FlexibleOutput(BaseModel):
    """V2-0 项目设计总监 - 灵活输出模型"""
    output_mode: Literal["targeted", "comprehensive"]
    user_question_focus: str
    confidence: float = Field(ge=0, le=1)
    decision_rationale: str
    
    master_plan_strategy: str | None = None
    spatial_zoning_concept: str | None = None
    circulation_integration: str | None = None
    subproject_coordination: List[SubprojectBrief] | None = None
    design_unity_and_variation: str | None = None
    
    targeted_analysis: Dict[str, Any] | None = None
    
    expert_handoff_response: Dict[str, Any] | None = None
    challenge_flags: List[Dict[str, str]] | None = None

    @model_validator(mode="after")
    def validate_output_consistency(self):
        mode = self.output_mode
        if mode == "comprehensive":
            required_fields = ["master_plan_strategy", "spatial_zoning_concept", "circulation_integration", "subproject_coordination", "design_unity_and_variation"]
            missing = [f for f in required_fields if not getattr(self, f)]
            if missing:
                raise ValueError(f"Comprehensive mode missing required fields: {', '.join(missing)}")
        elif mode == "targeted":
            if not self.targeted_analysis:
                raise ValueError("Targeted mode requires targeted_analysis field")
        return self

    class Config:
        populate_by_name = True


# ===== V5-3: 企业办公策略专家 =====

class V5_3_FlexibleOutput(BaseModel):
    """V5-3 企业办公策略专家 - 灵活输出模型"""
    output_mode: Literal["targeted", "comprehensive"]
    user_question_focus: str
    confidence: float = Field(ge=0, le=1)
    design_rationale: str
    
    organizational_analysis: str | None = None
    collaboration_model: str | None = None
    workspace_strategy: str | None = None
    key_performance_indicators: List[str] | None = None
    design_challenges_for_v2: List[DesignChallenge] | None = None
    
    targeted_analysis: Dict[str, Any] | None = None
    
    expert_handoff_response: Dict[str, Any] | None = None
    challenge_flags: List[Dict[str, str]] | None = None

    @model_validator(mode="after")
    def validate_output_consistency(self):
        mode = self.output_mode
        if mode == "comprehensive":
            required = ["organizational_analysis", "collaboration_model", "workspace_strategy", "key_performance_indicators", "design_challenges_for_v2"]
            missing = [f for f in required if not getattr(self, f)]
            if missing:
                raise ValueError(f"Comprehensive mode missing: {', '.join(missing)}")
        elif mode == "targeted":
            if not self.targeted_analysis:
                raise ValueError("Targeted mode requires targeted_analysis")
        return self

    class Config:
        populate_by_name = True


# ===== V5-4: 酒店餐饮运营专家 =====

class V5_4_FlexibleOutput(BaseModel):
    """V5-4 酒店餐饮运营专家 - 灵活输出模型"""
    output_mode: Literal["targeted", "comprehensive"]
    user_question_focus: str
    confidence: float = Field(ge=0, le=1)
    design_rationale: str
    
    service_process_analysis: str | None = None
    operational_efficiency: str | None = None
    guest_experience_blueprint: str | None = None
    key_performance_indicators: List[RetailKPI] | None = None
    design_challenges_for_v2: List[DesignChallenge] | None = None
    
    targeted_analysis: Dict[str, Any] | None = None
    
    expert_handoff_response: Dict[str, Any] | None = None
    challenge_flags: List[Dict[str, str]] | None = None

    @model_validator(mode="after")
    def validate_output_consistency(self):
        mode = self.output_mode
        if mode == "comprehensive":
            required = ["service_process_analysis", "operational_efficiency", "guest_experience_blueprint", "key_performance_indicators", "design_challenges_for_v2"]
            missing = [f for f in required if not getattr(self, f)]
            if missing:
                raise ValueError(f"Comprehensive mode missing: {', '.join(missing)}")
        elif mode == "targeted":
            if not self.targeted_analysis:
                raise ValueError("Targeted mode requires targeted_analysis")
        return self

    class Config:
        populate_by_name = True


# ===== V5-5: 文化教育场景专家 =====

class V5_5_FlexibleOutput(BaseModel):
    """V5-5 文化教育场景专家 - 灵活输出模型"""
    output_mode: Literal["targeted", "comprehensive"]
    user_question_focus: str
    confidence: float = Field(ge=0, le=1)
    design_rationale: str
    
    visitor_journey_analysis: str | None = None
    educational_model: str | None = None
    public_service_strategy: str | None = None
    key_performance_indicators: List[str] | None = None
    design_challenges_for_v2: List[DesignChallenge] | None = None
    
    targeted_analysis: Dict[str, Any] | None = None
    
    expert_handoff_response: Dict[str, Any] | None = None
    challenge_flags: List[Dict[str, str]] | None = None

    @model_validator(mode="after")
    def validate_output_consistency(self):
        mode = self.output_mode
        if mode == "comprehensive":
            required = ["visitor_journey_analysis", "educational_model", "public_service_strategy", "key_performance_indicators", "design_challenges_for_v2"]
            missing = [f for f in required if not getattr(self, f)]
            if missing:
                raise ValueError(f"Comprehensive mode missing: {', '.join(missing)}")
        elif mode == "targeted":
            if not self.targeted_analysis:
                raise ValueError("Targeted mode requires targeted_analysis")
        return self

    class Config:
        populate_by_name = True


# ===== V5-6: 医疗康养场景专家 =====

class V5_6_FlexibleOutput(BaseModel):
    """V5-6 医疗康养场景专家 - 灵活输出模型"""
    output_mode: Literal["targeted", "comprehensive"]
    user_question_focus: str
    confidence: float = Field(ge=0, le=1)
    design_rationale: str
    
    healthcare_process_analysis: str | None = None
    patient_experience_blueprint: str | None = None
    wellness_strategy: str | None = None
    key_performance_indicators: List[str] | None = None
    design_challenges_for_v2: List[DesignChallenge] | None = None
    
    targeted_analysis: Dict[str, Any] | None = None
    
    expert_handoff_response: Dict[str, Any] | None = None
    challenge_flags: List[Dict[str, str]] | None = None

    @model_validator(mode="after")
    def validate_output_consistency(self):
        mode = self.output_mode
        if mode == "comprehensive":
            required = ["healthcare_process_analysis", "patient_experience_blueprint", "wellness_strategy", "key_performance_indicators", "design_challenges_for_v2"]
            missing = [f for f in required if not getattr(self, f)]
            if missing:
                raise ValueError(f"Comprehensive mode missing: {', '.join(missing)}")
        elif mode == "targeted":
            if not self.targeted_analysis:
                raise ValueError("Targeted mode requires targeted_analysis")
        return self

    class Config:
        populate_by_name = True


# ===== V2-3: 办公空间设计总监 =====

class V2_3_FlexibleOutput(BaseModel):
    """V2-3 办公空间设计总监 - 灵活输出模型"""
    output_mode: Literal["targeted", "comprehensive"]
    user_question_focus: str
    confidence: float = Field(ge=0, le=1)
    decision_rationale: str
    
    workspace_vision: str | None = None
    spatial_strategy: str | None = None
    collaboration_and_focus_balance: str | None = None
    brand_and_culture_expression: str | None = None
    implementation_guidance: str | None = None
    
    targeted_analysis: Dict[str, Any] | None = None
    
    expert_handoff_response: Dict[str, Any] | None = None
    challenge_flags: List[Dict[str, str]] | None = None

    @model_validator(mode="after")
    def validate_output_consistency(self):
        mode = self.output_mode
        if mode == "comprehensive":
            required = ["workspace_vision", "spatial_strategy", "collaboration_and_focus_balance", "brand_and_culture_expression", "implementation_guidance"]
            missing = [f for f in required if not getattr(self, f)]
            if missing:
                raise ValueError(f"Comprehensive mode missing: {', '.join(missing)}")
        elif mode == "targeted":
            if not self.targeted_analysis:
                raise ValueError("Targeted mode requires targeted_analysis")
        return self

    class Config:
        populate_by_name = True


# ===== V2-4: 酒店餐饮空间设计总监 =====

class V2_4_FlexibleOutput(BaseModel):
    """V2-4 酒店餐饮空间设计总监 - 灵活输出模型"""
    output_mode: Literal["targeted", "comprehensive"]
    user_question_focus: str
    confidence: float = Field(ge=0, le=1)
    decision_rationale: str
    
    experiential_vision: str | None = None
    spatial_concept: str | None = None
    sensory_design_framework: str | None = None
    guest_journey_design: str | None = None
    implementation_guidance: str | None = None
    
    targeted_analysis: Dict[str, Any] | None = None
    
    expert_handoff_response: Dict[str, Any] | None = None
    challenge_flags: List[Dict[str, str]] | None = None

    @model_validator(mode="after")
    def validate_output_consistency(self):
        mode = self.output_mode
        if mode == "comprehensive":
            required = ["experiential_vision", "spatial_concept", "sensory_design_framework", "guest_journey_design", "implementation_guidance"]
            missing = [f for f in required if not getattr(self, f)]
            if missing:
                raise ValueError(f"Comprehensive mode missing: {', '.join(missing)}")
        elif mode == "targeted":
            if not self.targeted_analysis:
                raise ValueError("Targeted mode requires targeted_analysis")
        return self

    class Config:
        populate_by_name = True


# ===== V2-5: 文化与公共建筑设计总监 =====

class V2_5_FlexibleOutput(BaseModel):
    """V2-5 文化与公共建筑设计总监 - 灵活输出模型"""
    output_mode: Literal["targeted", "comprehensive"]
    user_question_focus: str
    confidence: float = Field(ge=0, le=1)
    decision_rationale: str
    
    public_vision: str | None = None
    spatial_accessibility: str | None = None
    community_engagement: str | None = None
    cultural_expression: str | None = None
    implementation_guidance: str | None = None
    
    targeted_analysis: Dict[str, Any] | None = None
    
    expert_handoff_response: Dict[str, Any] | None = None
    challenge_flags: List[Dict[str, str]] | None = None

    @model_validator(mode="after")
    def validate_output_consistency(self):
        mode = self.output_mode
        if mode == "comprehensive":
            required = ["public_vision", "spatial_accessibility", "community_engagement", "cultural_expression", "implementation_guidance"]
            missing = [f for f in required if not getattr(self, f)]
            if missing:
                raise ValueError(f"Comprehensive mode missing: {', '.join(missing)}")
        elif mode == "targeted":
            if not self.targeted_analysis:
                raise ValueError("Targeted mode requires targeted_analysis")
        return self

    class Config:
        populate_by_name = True


# ===== V2-6: 建筑及景观设计总监 =====

class V2_6_FlexibleOutput(BaseModel):
    """V2-6 建筑及景观设计总监 - 灵活输出模型"""
    output_mode: Literal["targeted", "comprehensive"]
    user_question_focus: str
    confidence: float = Field(ge=0, le=1)
    decision_rationale: str
    
    architectural_concept: str | None = None
    facade_and_envelope: str | None = None
    landscape_integration: str | None = None
    indoor_outdoor_relationship: str | None = None
    implementation_guidance: str | None = None
    
    targeted_analysis: Dict[str, Any] | None = None
    
    expert_handoff_response: Dict[str, Any] | None = None
    challenge_flags: List[Dict[str, str]] | None = None

    @model_validator(mode="after")
    def validate_output_consistency(self):
        mode = self.output_mode
        if mode == "comprehensive":
            required = ["architectural_concept", "facade_and_envelope", "landscape_integration", "indoor_outdoor_relationship", "implementation_guidance"]
            missing = [f for f in required if not getattr(self, f)]
            if missing:
                raise ValueError(f"Comprehensive mode missing: {', '.join(missing)}")
        elif mode == "targeted":
            if not self.targeted_analysis:
                raise ValueError("Targeted mode requires targeted_analysis")
        return self

    class Config:
        populate_by_name = True


# ===== V3-1: 个体叙事与心理洞察专家 =====

class V3_1_FlexibleOutput(BaseModel):
    """V3-1 个体叙事与心理洞察专家 - 灵活输出模型"""
    output_mode: Literal["targeted", "comprehensive"]
    user_question_focus: str
    confidence: float = Field(ge=0, le=1)
    design_rationale: str
    
    individual_narrative_core: str | None = None
    psychological_profile: str | None = None
    lifestyle_blueprint: str | None = None
    key_spatial_moments: List[TouchpointScript] | None = None
    narrative_guidelines_for_v2: str | None = None
    
    targeted_analysis: Dict[str, Any] | None = None
    
    expert_handoff_response: Dict[str, Any] | None = None
    challenge_flags: List[Dict[str, str]] | None = None

    @model_validator(mode="after")
    def validate_output_consistency(self):
        mode = self.output_mode
        if mode == "comprehensive":
            required = ["individual_narrative_core", "psychological_profile", "lifestyle_blueprint", "key_spatial_moments", "narrative_guidelines_for_v2"]
            missing = [f for f in required if not getattr(self, f)]
            if missing:
                raise ValueError(f"Comprehensive mode missing: {', '.join(missing)}")
        elif mode == "targeted":
            if not self.targeted_analysis:
                raise ValueError("Targeted mode requires targeted_analysis")
        return self

    class Config:
        populate_by_name = True


# ===== V3-3: 空间叙事与情感体验专家 =====

class V3_3_FlexibleOutput(BaseModel):
    """V3-3 空间叙事与情感体验专家 - 灵活输出模型"""
    output_mode: Literal["targeted", "comprehensive"]
    user_question_focus: str
    confidence: float = Field(ge=0, le=1)
    design_rationale: str
    
    spatial_narrative_concept: str | None = None
    emotional_journey_map: str | None = None
    sensory_experience_design: str | None = None
    key_spatial_moments: List[TouchpointScript] | None = None
    narrative_guidelines_for_v2: str | None = None
    
    targeted_analysis: Dict[str, Any] | None = None
    
    expert_handoff_response: Dict[str, Any] | None = None
    challenge_flags: List[Dict[str, str]] | None = None

    @model_validator(mode="after")
    def validate_output_consistency(self):
        mode = self.output_mode
        if mode == "comprehensive":
            required = ["spatial_narrative_concept", "emotional_journey_map", "sensory_experience_design", "key_spatial_moments", "narrative_guidelines_for_v2"]
            missing = [f for f in required if not getattr(self, f)]
            if missing:
                raise ValueError(f"Comprehensive mode missing: {', '.join(missing)}")
        elif mode == "targeted":
            if not self.targeted_analysis:
                raise ValueError("Targeted mode requires targeted_analysis")
        return self

    class Config:
        populate_by_name = True


# ===== V4-2: 趋势研究与未来洞察专家 =====

class V4_2_FlexibleOutput(BaseModel):
    """V4-2 趋势研究与未来洞察专家 - 灵活输出模型"""
    output_mode: Literal["targeted", "comprehensive"]
    user_question_focus: str
    confidence: float = Field(ge=0, le=1)
    design_rationale: str
    
    trend_analysis: str | None = None
    future_scenarios: str | None = None
    opportunity_identification: str | None = None
    design_implications: str | None = None
    risk_assessment: str | None = None
    
    targeted_analysis: Dict[str, Any] | None = None
    
    expert_handoff_response: Dict[str, Any] | None = None
    challenge_flags: List[Dict[str, str]] | None = None

    @model_validator(mode="after")
    def validate_output_consistency(self):
        mode = self.output_mode
        if mode == "comprehensive":
            required = ["trend_analysis", "future_scenarios", "opportunity_identification", "design_implications", "risk_assessment"]
            missing = [f for f in required if not getattr(self, f)]
            if missing:
                raise ValueError(f"Comprehensive mode missing: {', '.join(missing)}")
        elif mode == "targeted":
            if not self.targeted_analysis:
                raise ValueError("Targeted mode requires targeted_analysis")
        return self

    class Config:
        populate_by_name = True
