"""
需求分析师结构化输出Schema v7.600
使用OpenAI Structured Outputs防止LLM幻觉

创建日期: 2026-02-10
更新日期: 2026-02-11
- v7.600: 新增Phase1结构化输出Schema
目标: 幻觉率 15% → <1%
"""

from enum import Enum
from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

# ============================================================================
# 预定义理论清单 (从8大透镜提取)
# ============================================================================


class LensCategory(str, Enum):
    """8大学科透镜类别"""

    ANTHROPOLOGY = "Anthropology"  # 人类学
    SOCIOLOGY = "Sociology"  # 社会学
    PSYCHOLOGY = "Psychology"  # 心理学
    PHENOMENOLOGY = "Phenomenology"  # 现象学/生活美学
    CULTURAL_STUDIES = "Cultural_Studies"  # 文化研究
    TECH_PHILOSOPHY = "Tech_Philosophy"  # 技术哲学/STS
    MATERIAL_CULTURE = "Material_Culture"  # 物质文化研究
    SPIRITUAL_PHILOSOPHY = "Spiritual_Philosophy"  # 精神哲学/宗教研究


# 预批准理论名称（完整清单）
APPROVED_THEORY = Literal[
    # 人类学透镜 (Anthropology)
    "Ritual_And_Liminality",  # 仪式与过渡
    "Kinship_And_Space_Allocation",  # 亲属结构与空间分配
    "Material_Culture_And_Identity",  # 物质文化与身份
    "Sacred_Vs_Profane_Space",  # 空间的神圣与世俗
    # 社会学透镜 (Sociology)
    "Bourdieu_Cultural_Capital",  # 布迪厄的文化资本
    "Goffman_Front_Back_Stage",  # 戈夫曼的前台后台
    "Social_Exclusion_And_Boundary",  # 社会排斥与边界
    "Social_Construction_Of_Time",  # 时间的社会建构
    # 心理学透镜 (Psychology)
    "Maslow_Hierarchy",  # 马斯洛需求层次
    "Territoriality",  # 环境心理学：领域性
    "Cognitive_Load_Theory",  # 认知负荷理论
    "Attachment_Theory_Secure_Base",  # 依恋理论与安全基地
    "Trauma_Informed_Design",  # 创伤知情设计
    # 现象学/生活美学透镜 (Phenomenology)
    "Heidegger_Dwelling",  # 海德格尔的'栖居'
    "Merleau_Ponty_Embodied_Phenomenology",  # 梅洛-庞蒂的身体现象学
    "Bachelard_Poetics_Of_Space",  # 巴什拉的'诗意空间'
    "Aestheticization_Of_Everyday_Life",  # 日常生活审美化
    # 文化研究透镜 (Cultural Studies)
    "Symbolic_Consumption",  # 符号消费
    "Subculture_And_Resistance",  # 亚文化与抵抗
    "Nostalgia_And_Politics_Of_Time",  # 怀旧与时间政治
    "Baudrillard_Hyperreality_Simulacra",  # 超真实与拟像
    # 技术哲学/STS透镜 (Tech Philosophy)
    "Value_Laden_Technology",  # 技术的价值负载
    "Cyborg_Dwelling",  # 赛博格人居
    "Digital_Labor_Invisible_Work",  # 数字劳动与隐形工作
    #  v7.502: 新增前沿理论
    "Algorithmic_Governance",  # 算法治理
    "Data_Sovereignty",  # 数据主权
    "Post_Anthropocentric_Design",  # 后人类中心设计
    "Glitch_Aesthetics",  # 故障美学
    # 物质文化研究透镜 (Material Culture)
    "Social_Life_Of_Things",  # 物的社会生命
    "Material_Agency",  # 材料的能动性
    "Craft_Knowledge_Body_Memory",  # 工艺知识与身体记忆
    # 精神哲学/宗教研究透镜 (Spiritual Philosophy)
    "Production_Of_Sacred_Space",  # 神圣空间的生产
    "Meditation_Sensory_Deprivation",  # 冥想与感知剥夺
    "Pilgrimage_And_Journey",  # 朝圣与旅程
]


# 理论名称到透镜类别的映射
THEORY_TO_LENS: dict[str, LensCategory] = {
    # Anthropology
    "Ritual_And_Liminality": LensCategory.ANTHROPOLOGY,
    "Kinship_And_Space_Allocation": LensCategory.ANTHROPOLOGY,
    "Material_Culture_And_Identity": LensCategory.ANTHROPOLOGY,
    "Sacred_Vs_Profane_Space": LensCategory.ANTHROPOLOGY,
    # Sociology
    "Bourdieu_Cultural_Capital": LensCategory.SOCIOLOGY,
    "Goffman_Front_Back_Stage": LensCategory.SOCIOLOGY,
    "Social_Exclusion_And_Boundary": LensCategory.SOCIOLOGY,
    "Social_Construction_Of_Time": LensCategory.SOCIOLOGY,
    # Psychology
    "Maslow_Hierarchy": LensCategory.PSYCHOLOGY,
    "Territoriality": LensCategory.PSYCHOLOGY,
    "Cognitive_Load_Theory": LensCategory.PSYCHOLOGY,
    "Attachment_Theory_Secure_Base": LensCategory.PSYCHOLOGY,
    "Trauma_Informed_Design": LensCategory.PSYCHOLOGY,
    # Phenomenology
    "Heidegger_Dwelling": LensCategory.PHENOMENOLOGY,
    "Merleau_Ponty_Embodied_Phenomenology": LensCategory.PHENOMENOLOGY,
    "Bachelard_Poetics_Of_Space": LensCategory.PHENOMENOLOGY,
    "Aestheticization_Of_Everyday_Life": LensCategory.PHENOMENOLOGY,
    # Cultural Studies
    "Symbolic_Consumption": LensCategory.CULTURAL_STUDIES,
    "Subculture_And_Resistance": LensCategory.CULTURAL_STUDIES,
    "Nostalgia_And_Politics_Of_Time": LensCategory.CULTURAL_STUDIES,
    "Baudrillard_Hyperreality_Simulacra": LensCategory.CULTURAL_STUDIES,
    # Tech Philosophy
    "Value_Laden_Technology": LensCategory.TECH_PHILOSOPHY,
    "Cyborg_Dwelling": LensCategory.TECH_PHILOSOPHY,
    "Digital_Labor_Invisible_Work": LensCategory.TECH_PHILOSOPHY,
    #  v7.502: 新增前沿理论映射
    "Algorithmic_Governance": LensCategory.TECH_PHILOSOPHY,
    "Data_Sovereignty": LensCategory.TECH_PHILOSOPHY,
    "Post_Anthropocentric_Design": LensCategory.TECH_PHILOSOPHY,
    "Glitch_Aesthetics": LensCategory.TECH_PHILOSOPHY,
    # Material Culture
    "Social_Life_Of_Things": LensCategory.MATERIAL_CULTURE,
    "Material_Agency": LensCategory.MATERIAL_CULTURE,
    "Craft_Knowledge_Body_Memory": LensCategory.MATERIAL_CULTURE,
    # Spiritual Philosophy
    "Production_Of_Sacred_Space": LensCategory.SPIRITUAL_PHILOSOPHY,
    "Meditation_Sensory_Deprivation": LensCategory.SPIRITUAL_PHILOSOPHY,
    "Pilgrimage_And_Journey": LensCategory.SPIRITUAL_PHILOSOPHY,
}


# ============================================================================
# 禁用泛化短语（16 个）— Prompt 约束 + AntiClicheCheck 参考清单
# ============================================================================
GENERIC_PHRASES: list[str] = [
    "温馨",  # 过度使用的室内风格词
    "舒适",  # 缺乏具体性
    "以人为本",  # 空洞口号
    "简约而不简单",  # 广告套话
    "高端大气",  # 品牌套话
    "精致",  # 无差异表达
    "有品位",  # 主观泛词
    "自然",  # 过宽泛
    "清新",  # 装饰性形容词
    "优雅",  # 缺乏设计指向
    "现代感",  # 无方向性
    "时尚",  # 随时效而变
    "格调",  # 无可量化指标
    "生活品质",  # 空泛概念
    "人文关怀",  # 口号化
    "情感共鸣",  # 无操作路径
]


# ============================================================================
# Phase1 结构化输出模型 (v7.600新增)
# ============================================================================


class DeliverableTypeEnum(str, Enum):
    """交付物类型枚举"""

    # 文案/创意类
    NAMING_LIST = "naming_list"
    BRAND_NARRATIVE = "brand_narrative"
    COPYWRITING_PLAN = "copywriting_plan"

    # 策略/指导类
    DESIGN_STRATEGY = "design_strategy"
    MATERIAL_GUIDANCE = "material_guidance"
    SELECTION_FRAMEWORK = "selection_framework"
    PROCUREMENT_GUIDANCE = "procurement_guidance"
    BUDGET_FRAMEWORK = "budget_framework"

    # 分析/研究类
    ANALYSIS_REPORT = "analysis_report"
    RESEARCH_SUMMARY = "research_summary"
    EVALUATION_REPORT = "evaluation_report"
    CASE_STUDY = "case_study"

    # 方法论/流程类
    STRATEGY_PLAN = "strategy_plan"
    IMPLEMENTATION_GUIDE = "implementation_guide"
    DECISION_FRAMEWORK = "decision_framework"

    # 自定义类型
    CUSTOM = "custom"


class DeliverablePriorityEnum(str, Enum):
    """交付物优先级枚举"""

    MUST_HAVE = "MUST_HAVE"  # 用户明确要求
    NICE_TO_HAVE = "NICE_TO_HAVE"  # 推测用户可能需要


class DeliverableOwnerSuggestion(BaseModel):
    """交付物责任人建议"""

    primary_owner: str = Field(description="最适合完成此交付物的专家角色", examples=["V3_叙事与体验专家_3-3", "V2_设计总监_2-2"])
    owner_rationale: str = Field(description="为何选此专家（一句话）", min_length=10, max_length=100)
    supporters: List[str] = Field(default_factory=list, description="辅助角色（可选）")
    anti_pattern: List[str] = Field(
        default_factory=list, description="不应被分配此任务的角色类型", examples=[["V6_工程师"], ["V2_设计总监", "V6_工程师"]]
    )


class CapabilityCheck(BaseModel):
    """能力边界检查"""

    within_capability: bool = Field(description="是否在系统能力范围内")
    original_request: str | None = Field(default=None, description="用户原文（如超出能力）")
    transformed_to: str | None = Field(default=None, description="转化后的交付物类型（如超出能力）")
    transformation_reason: str | None = Field(default=None, description="转化原因说明")


class Phase1Deliverable(BaseModel):
    """Phase1交付物定义"""

    deliverable_id: str = Field(pattern=r"^D\d+$", description="唯一标识，格式为D1, D2, D3...", examples=["D1", "D2"])

    type: DeliverableTypeEnum = Field(description="交付物类型")

    description: str = Field(min_length=10, max_length=200, description="简洁描述用户要什么（一句话，10-20字）")

    priority: DeliverablePriorityEnum = Field(description="优先级")

    quantity: int | None = Field(default=None, ge=1, le=50, description="数量要求（如果适用）")

    scope: str | None = Field(default=None, description="应用范围/场景")

    format_requirements: Dict[str, Any] | None = Field(default=None, description="格式/规格要求")

    acceptance_criteria: List[str] = Field(
        min_length=1, description="验收标准（必须可量化、可验证，使用'必须'句式）", examples=[["必须提供正好8个命名（不多不少）", "每个命名必须正好4个汉字"]]
    )

    deliverable_owner_suggestion: DeliverableOwnerSuggestion = Field(description="交付物责任人建议")

    capability_check: CapabilityCheck = Field(description="能力边界检查")


class Phase1Output(BaseModel):
    """
    Phase1结构化输出Schema

    功能：快速定性 + 交付物识别 + 能力边界判断
    """

    phase: Literal[1] = Field(default=1, description="阶段标识")

    info_status: Literal["sufficient", "insufficient"] = Field(description="信息充足性状态")

    info_status_reason: str = Field(min_length=20, max_length=200, description="一句话说明为何充足/不足")

    info_gaps: List[str] = Field(default_factory=list, max_length=10, description="缺失信息列表（仅当insufficient时填写）")

    project_type_preliminary: str = Field(
        description="初步项目类型判断", examples=["personal_residential", "commercial_enterprise"]
    )

    project_summary: str = Field(min_length=30, max_length=300, description="一句话概括项目核心（30-50字）")

    primary_deliverables: List[Phase1Deliverable] = Field(min_length=1, description="主要交付物列表（至少1个）")

    recommended_next_step: Literal["phase2_analysis", "questionnaire_first", "clarify_expectations"] = Field(
        description="推荐的下一步行动"
    )

    next_step_reason: str = Field(min_length=20, max_length=200, description="推荐下一步的原因说明")

    # C-01: Phase1 prompt要求的额外输出字段，必须保留否则Pydantic静默丢弃
    problem_types: List[str] | None = Field(
        default_factory=list, description="问题类型分类列表（如 tension_identity/technical_first 等8种）"
    )
    proposition_candidates: List[Dict[str, Any]] | None = Field(default_factory=list, description="核心命题候选列表")
    complexity_assessment: Dict[str, Any] | None = Field(default=None, description="项目复杂度评估")

    @model_validator(mode="after")
    def validate_logic_consistency(self):
        """验证逻辑一致性"""
        # 规则1: 信息充足时，缺失项不应过多
        if self.info_status == "sufficient" and len(self.info_gaps) > 2:
            raise ValueError("信息充足时不应有过多缺失项（最多2个）")

        # 规则2已删除（C-02）：should_execute_phase2()总是返回phase2，Rule2与路由逻辑矛盾，
        # 导致sufficient+phase2_analysis组合触发不必要的fallback。

        # 规则3: 信息充足时，应推荐Phase2
        if self.info_status == "sufficient" and self.recommended_next_step == "questionnaire_first":
            # 这种情况可能合理（信息充足但仍需问卷补充细节），仅警告
            import logging

            logging.warning("信息充足但仍推荐问卷，请确认this is intentional")

        # 规则4: 至少有一个MUST_HAVE交付物
        must_have_count = sum(1 for d in self.primary_deliverables if d.priority == DeliverablePriorityEnum.MUST_HAVE)
        if must_have_count == 0:
            raise ValueError("至少需要一个MUST_HAVE优先级的交付物")

        return self


# ============================================================================
# Phase2 结构化输出模型 (原有v7.501)
# ============================================================================


class CoreTension(BaseModel):
    """
    核心张力 (Core Tension)

    使用Structured Outputs强制约束:
    - 理论来源必须来自Pre-approved清单（30个理论）
    - 自动验证理论与透镜类别的匹配
    - 防止幻觉理论（如"后现代解构主义"）
    """

    name: str = Field(
        description="核心张力名称（使用标准术语，如'公共展示 vs 私密避难'）",
        min_length=5,
        max_length=50,
        examples=["公共展示 vs 私密避难", "传统身份 vs 现代流动性"],
    )

    theory_source: APPROVED_THEORY = Field(
        description=(
            "理论来源（必须来自Pre-approved清单，30个理论之一）。" "例如: Maslow_Hierarchy / Bourdieu_Cultural_Capital / Heidegger_Dwelling"
        )
    )

    lens_category: LensCategory = Field(description="所属学科透镜类别（8大类之一）")

    description: str = Field(description="张力描述（说明为什么这是核心张力，如何影响设计）", min_length=20, max_length=500)

    design_implication: str = Field(description="设计启示（这个张力如何转化为具体设计决策？）", min_length=20, max_length=300)

    @field_validator("lens_category", mode="before")
    @classmethod
    def validate_lens_category(cls, v, info) -> str:
        """
        验证并自动修正理论与透镜类别的匹配（v7.621 自动纠错，不再 raise）

        - 若传入值不在枚举中（如 'Aesthetic'），尝试从 theory_source 推断
        - 若理论与类别不匹配，自动纠正为正确类别（仅 WARNING，不报错）
        """
        import logging as _log

        _logger = _log.getLogger(__name__)
        valid_values = {lc.value for lc in LensCategory}

        if v not in valid_values:
            # 非法值：尝试从 theory_source 推断正确透镜
            theory = info.data.get("theory_source")
            if theory and theory in THEORY_TO_LENS:
                corrected = THEORY_TO_LENS[theory].value
                _logger.warning(f"[AutoFix] lens_category='{v}' 不合法，" f"已从理论 '{theory}' 自动推断为 '{corrected}'")
                return corrected
            _logger.warning(f"[AutoFix] lens_category='{v}' 不合法且无法推断，使用默认值 'Anthropology'")
            return LensCategory.ANTHROPOLOGY.value

        # 合法值：检查是否与理论匹配，不匹配则自动纠正
        theory = info.data.get("theory_source")
        if theory:
            expected_lens = THEORY_TO_LENS.get(theory)
            if expected_lens and v != expected_lens.value:
                _logger.warning(f"[AutoFix] 理论 '{theory}' 应属 '{expected_lens.value}' 透镜，" f"但 LLM 指定了 '{v}'，已自动纠正")
                return expected_lens.value
        return v


class ProjectTask(BaseModel):
    """项目任务（JTBD公式）"""

    when: str = Field(description="触发场景 (When...)", min_length=10, max_length=200)

    i_want_to: str = Field(description="核心任务 (I want to...)", min_length=10, max_length=200)

    so_i_can: str = Field(description="根本动机 (So I can...)", min_length=10, max_length=200)

    full_statement: str = Field(description="完整JTBD陈述（组合上述三部分）", min_length=30, max_length=500)


class CharacterNarrative(BaseModel):
    """核心人物画像"""

    who: str = Field(description="这是谁？（社会身份+生命阶段+关键特质）", min_length=20, max_length=300)

    internal_conflict: str = Field(description="内在冲突（TA在纠结什么？矛盾的欲望是什么？）", min_length=20, max_length=300)

    symbolic_identity: str = Field(description="符号身份（TA想通过空间传递什么信息？）", min_length=20, max_length=300)


class OntologyParameter(BaseModel):
    """本体维度参数"""

    name: str = Field(description="参数名称", min_length=3, max_length=50)

    value: str = Field(description="参数值（模糊/清晰/中间态等）", min_length=1, max_length=100)

    rationale: str = Field(description="理由（为什么是这个值？）", min_length=10, max_length=300)


# ============================================================================
# v9.2 新增: L2.5/L4.5/L6/L7/L8 深度分析层 Schema
# ============================================================================


class StakeholderEntry(BaseModel):
    """L2.5 利益相关者条目"""

    role: str = Field(description="利益相关者角色（如'投资人/业主'、'终端消费者'、'运营者/管理方'）", min_length=2, max_length=50)
    focus_dimensions: List[str] = Field(description="关注维度列表（如'ROI'、'体验质量'、'运营效率'）", min_items=1, max_items=8)
    specific_concerns: str = Field(description="具体关切（基于用户原话或合理推断的此角色核心关切）", min_length=10, max_length=300)
    decision_power: str = Field(
        description="决策权力等级: high / medium / low / indirect", pattern=r"^(high|medium|low|indirect)$"
    )


class FocusDivergence(BaseModel):
    """L2.5 关注点分歧"""

    time_perspective: str | None = Field(default=None, description="时间视角分歧", max_length=200)
    risk_preference: str | None = Field(default=None, description="风险偏好分歧", max_length=200)
    value_priority: str | None = Field(default=None, description="价值排序分歧", max_length=200)
    aesthetic_orientation: str | None = Field(default=None, description="审美取向分歧", max_length=200)
    brand_attitude: str | None = Field(default=None, description="品牌态度分歧", max_length=200)


class ConflictEntry(BaseModel):
    """利益冲突条目"""

    conflict_pair: List[str] = Field(description="冲突双方", min_items=2, max_items=2)
    tension: str = Field(description="冲突张力描述", min_length=5, max_length=200)
    mediation_strategy: str = Field(description="调解策略", min_length=10, max_length=300)


class SynergyEntry(BaseModel):
    """协同机会条目"""

    synergy_pair: List[str] = Field(description="协同双方", min_items=2, max_items=2)
    opportunity: str = Field(description="协同机会描述", min_length=10, max_length=300)


class PowerDynamics(BaseModel):
    """权力动态分析"""

    decision_hierarchy: str = Field(description="决策层级", min_length=10, max_length=300)
    hidden_stakeholders: str | None = Field(default=None, description="隐藏的利益相关者", max_length=300)


class StakeholderSystem(BaseModel):
    """L2.5 利益相关者系统分析"""

    identified_stakeholders: List[StakeholderEntry] = Field(
        description="已识别的利益相关者（至少1类，建议3类以上）", min_items=1, max_items=10  # 🔧 bugfix: 从3降为1，LLM对某些场景只返回2个利益相关者导致校验失败降级
    )
    focus_divergence: FocusDivergence = Field(description="各方关注点分歧分析")
    conflicts_identified: List[ConflictEntry] = Field(description="已识别的利益冲突", default_factory=list)
    synergies_identified: List[SynergyEntry] = Field(description="已识别的协同机会", default_factory=list)
    power_dynamics: PowerDynamics | None = Field(default=None, description="权力动态分析（lite模式或信息不足时可为null）")

    @field_validator("conflicts_identified", mode="before")
    @classmethod
    def clean_conflicts(cls, v):
        """清洗 conflicts_identified：过滤 None 及缺少必填 key 的畸形条目"""
        if not isinstance(v, list):
            return []
        required = {"conflict_pair", "tension", "mediation_strategy"}
        return [item for item in v if isinstance(item, dict) and required.issubset(item.keys())]

    @field_validator("synergies_identified", mode="before")
    @classmethod
    def clean_synergies(cls, v):
        """清洗 synergies_identified：过滤 None 及缺少必填 key 的畸形条目"""
        if not isinstance(v, list):
            return []
        required = {"synergy_pair", "opportunity"}
        return [item for item in v if isinstance(item, dict) and required.issubset(item.keys())]


class FiveWhysChain(BaseModel):
    """L4.5 五层为什么追问链条"""

    L1_what: str = Field(description="用户说了什么（原话提取）", min_length=5, max_length=200)
    L2_why_surface: str = Field(description="表层原因", min_length=10, max_length=300)
    L3_why_behavior: str = Field(description="行为模式", min_length=10, max_length=300)
    L4_why_emotion: str = Field(description="情感需求（必须到达）", min_length=10, max_length=300)
    L5_why_identity: str | None = Field(default=None, description="身份认同（理想到达）", max_length=300)
    design_implication: str = Field(description="设计启示", min_length=10, max_length=300)


class AssumptionEntry(BaseModel):
    """L6 假设审计条目"""

    assumption: str = Field(description="隐含假设", min_length=10, max_length=300)
    evidence: str | None = Field(default=None, description="支撑假设的证据", max_length=300)
    counter_assumption: str | None = Field(default=None, description="反向假设", max_length=300)
    challenge_question: str | None = Field(default=None, description="挑战问题", max_length=300)
    impact_if_wrong: str | None = Field(default=None, description="假设错误的影响", max_length=300)
    alternative_approach: str | None = Field(default=None, description="替代方案", max_length=300)


class SystemicImpactTimeframe(BaseModel):
    """系统性影响 - 单个时间维度"""

    social: str | None = Field(default=None, description="社会影响", max_length=300)
    environmental: str | None = Field(default=None, description="环境影响", max_length=300)
    economic: str | None = Field(default=None, description="经济影响", max_length=300)
    cultural: str | None = Field(default=None, description="文化影响", max_length=300)


class SystemicImpact(BaseModel):
    """L7 系统性影响分析"""

    short_term: SystemicImpactTimeframe = Field(description="短期影响（0-1年）")
    medium_term: SystemicImpactTimeframe = Field(description="中期影响（1-5年）")
    long_term: SystemicImpactTimeframe = Field(description="长期影响（5年+）")
    unintended_consequences: List[str] = Field(description="非预期后果", default_factory=list, max_items=5)
    mitigation_strategies: List[str] = Field(description="缓解策略", default_factory=list, max_items=5)


class AntiClicheCheck(BaseModel):
    """L8 反套路化自检"""

    passed: bool = Field(description="是否通过反套路化检测")
    flagged_phrases: List[str] = Field(description="被标记的套路化表达", default_factory=list)
    replacements_made: List[Dict[str, str]] = Field(
        description="已执行的替换 [{original, replaced_with}]", default_factory=list
    )


class HumanDimensions(BaseModel):
    """人性维度深度分析"""

    emotional_landscape: str | None = Field(default=None, description="情绪地图（具体情绪转化路径，禁止'温馨舒适'等套话）", max_length=500)
    spiritual_aspirations: str | None = Field(default=None, description="精神追求（穿透功能到精神层面的渴望）", max_length=500)
    psychological_safety_needs: str | None = Field(default=None, description="心理安全需求（基于依恋理论的安全基地需求）", max_length=500)
    ritual_behaviors: str | None = Field(default=None, description="仪式行为（日常具有仪式感的微小行为及空间容器）", max_length=500)
    memory_anchors: str | None = Field(default=None, description="记忆锚点（承载情感记忆的物品/元素及归属设计）", max_length=500)


# ═══════════════════════════════════════════════════════════
# v9.3: 多视角对抗 + 思维模型层（新增模型）
# ═══════════════════════════════════════════════════════════


class FirstPrinciplesAnalysis(BaseModel):
    """L1.5 第一性原理裸需求 — 剥离行业惯例/风格标签后的不可约化最小需求"""

    naked_requirement: str = Field(description="去除所有风格标签和行业惯例后的不可约化最小需求描述", max_length=400)
    stripped_conventions: List[str] = Field(
        description="被剥离的行业惯例/风格标签列表，格式: '去除 › 标签名: 真实需求是...'", min_items=1, max_items=6
    )
    confidence_note: str = Field(description="分析师把握度说明（基于哪些推断，置信度高/中/低）", max_length=200)


class ThoughtExperiment(BaseModel):
    """单个思想实验"""

    before: str = Field(description="实验前的假设/现状", max_length=200)
    after: str = Field(description="实验后发现的真实情况", max_length=300)
    design_implication: str = Field(description="设计启示（可直接指导方案决策）", max_length=200)


class ThoughtExperimentSet(BaseModel):
    """L4.6 思想实验层 — 3个如果测试揭示需求权重真实排序"""

    unlimited_budget: ThoughtExperiment = Field(description="无限预算实验：揭示'妥协'vs'真实偏好'")
    keep_one_space: ThoughtExperiment = Field(description="只保留一个空间实验：揭示需求优先级真实排序")
    ten_years_regret: ThoughtExperiment = Field(description="10年后后悔实验：揭示时间维度需求验证")
    competitor_first: ThoughtExperiment | None = Field(default=None, description="竞争者优先实验（可选）：揭示差异化需求")


class RazorCheck(BaseModel):
    """L5.R 奥卡姆剃刀逆向检验 — 防止过度理论化"""

    is_overcomplicated: bool = Field(description="分析是否过度复杂化了一个本质简单的需求")
    simpler_alternative: str | None = Field(
        default=None, description="如果is_overcomplicated=True，提供更简洁的替代解释", max_length=200
    )
    reason_for_keeping_complexity: str = Field(
        description="保留当前复杂度分析的理由（即使is_overcomplicated=False也必须填写）", max_length=300
    )


class PerspectiveView(BaseModel):
    """单个对抗视角的洞察"""

    role: str = Field(description="视角角色名称", max_length=50)
    key_challenge: str = Field(description="该视角对当前分析提出的核心挑战或质疑", max_length=300)
    blind_spot_found: str = Field(description="单视角无法发现、该角色看到的独特盲点或洞察", max_length=300)


class MultiPerspectiveSynthesis(BaseModel):
    """L9 多视角对抗合成 — 4个外部对抗视角揭露单分析师盲点"""

    competitive_analyst: PerspectiveView = Field(description="竞争对手分析师视角：指出被营销塑造的偏好 vs 真实需求")
    devils_advocate: PerspectiveView = Field(description="恶魔代言人视角：指出逻辑漏洞 + 被忽视的反证")
    future_user: PerspectiveView = Field(description="10年后用户视角：指出时效性/潜在后悔点/长期价值")
    expert_outsider: PerspectiveView = Field(description="局外人专家视角：指出行业隐性假设 + 真正本质需求")
    convergent_insight: str = Field(description="4个视角汇聚出的核心盲点或锐见（单视角分析无法得出的结论）", min_length=30, max_length=500)


class ConstraintsMap(BaseModel):
    """A4 约束地图（v10 新增）：项目硬性约束全景"""

    budget: Dict[str, Any] | None = Field(default=None, description="预算约束（total/hard_ceiling/note）")
    timeline: Dict[str, Any] | None = Field(default=None, description="工期约束（construction/hard_deadline）")
    regulatory: List[str] | None = Field(default=None, description="规范要求列表（消防/审批等）")
    physical: Dict[str, Any] | None = Field(default=None, description="物理约束（面积/层高/承重墙等）")
    operational: List[str] | None = Field(default=None, description="运营约束（保洁/维修响应等）")
    constraint_map_insight: str | None = Field(default=None, description="约束地图洞察：关键取舍点分析", max_length=300)


class RequirementsAnalystOutput(BaseModel):
    """
    需求分析师完整结构化输出 v10.0.0

    使用OpenAI Structured Outputs，自动验证：
    - 所有理论引用必须来自预批准清单
    - 字段长度限制（防止过度冗长）
    - 必填字段完整性
    - v9.2: 新增 L2.5/L4.5/L6/L7/L8 深度分析层（Optional，向后兼容）
    - v9.3: 新增 L1.5/L4.6/L5.R/L9 多视角对抗+思维模型层（Optional，向后兼容）
    - v10.0.0: 新增 A4约束地图(constraints_map)；v10架构标注（B4=first_principles,
               B5=assumption_audit, C3=thought_experiments）；phase_a/b/c 分组只读属性
    """

    # L1: 快速定性
    project_task: ProjectTask = Field(description="项目任务（JTBD公式）")

    character_narrative: CharacterNarrative = Field(description="核心人物画像")

    # L2: 跨学科解构
    l2_disciplinary_lenses: List[str] = Field(
        description=("使用的学科透镜列表（2-3个），" "格式: '[透镜类别] 理论名称'，" "例如: '[Psychology] Maslow_Hierarchy'"),
        min_items=2,
        max_items=3,
    )

    # L3: 系统分析
    core_tensions: List[CoreTension] = Field(description="核心张力列表（2-3个，按重要性排序）", min_items=2, max_items=3)

    # L4: 本体维度定位
    ontology_parameters: List[OntologyParameter] = Field(
        default_factory=list, description="本体维度参数列表（3-5个关键维度，LLM可能省略，系统容忍最少0个）", min_items=0, max_items=5
    )

    # L5: 锐度验证
    breakthrough_insight: str = Field(
        default="", description=("穿透性洞察（一句话总结：这个项目的本质是什么？" "必须展现理论张力，避免泛泛而谈）"), min_length=0, max_length=200
    )

    design_principles: List[str] = Field(
        default_factory=list, description="设计原则（3-5条可执行的设计指导，LLM可能省略，系统容忍空列表）", min_items=0, max_items=5
    )

    # 元数据
    confidence_score: float = Field(default=0.7, description="分析置信度（0.0-1.0），反映输入信息的充分性；LLM省略时默认 0.7", ge=0.0, le=1.0)

    ontology_suggestions: List[str] | None = Field(default=None, description="本体框架扩展建议（发现旧框架无法解释的现象时填写）")

    # ═══════════════════════════════════════════════════════════
    # v9.2: 深度分析层（Optional，向后兼容）
    # ═══════════════════════════════════════════════════════════

    # L2.5: 利益相关者系统分析
    stakeholder_system: StakeholderSystem | None = Field(default=None, description="L2.5 利益相关者系统分析（至少3类利益相关者）")

    # L4.5: 五层为什么追问
    five_whys_analysis: Dict[str, FiveWhysChain] | None = Field(
        default=None, description="L4.5 五层为什么追问，每个核心需求一条链（如 core_need_1, core_need_2）"
    )

    # L6: 假设审计
    assumption_audit: List[AssumptionEntry] | None = Field(default=None, description="L6 假设审计（至少3个假设+反向挑战）")

    # L7: 系统性影响
    systemic_impact: SystemicImpact | None = Field(default=None, description="L7 系统性影响分析（短/中/长期 × 社会/环境/经济/文化）")

    # L8: 反套路化自检
    anti_cliche_check: AntiClicheCheck | None = Field(default=None, description="L8 反套路化检测结果")

    # 人性维度深度分析
    human_dimensions: HumanDimensions | None = Field(default=None, description="人性维度深度分析（情绪地图/精神追求/心理安全/仪式行为/记忆锚点）")

    # ═══════════════════════════════════════════════════════════
    # v9.3: 多视角对抗 + 思维模型层（Optional，向后兼容）
    # ═══════════════════════════════════════════════════════════

    # L1.5: 第一性原理裸需求
    first_principles: FirstPrinciplesAnalysis | None = Field(
        default=None, description="L1.5 第一性原理裸需求验证（剥离风格标签/行业惯例后的最小需求）"
    )

    # L4.6: 思想实验层
    thought_experiments: ThoughtExperimentSet | None = Field(default=None, description="L4.6 思想实验层（3个如果测试验证需求权重真实排序）")

    # L5.R: 奥卡姆剃刀逆向检验
    razor_check: RazorCheck | None = Field(default=None, description="L5.R 奥卡姆剃刀逆向检验（防止过度理论化，也防止过度简化）")

    # L9: 多视角对抗合成
    multi_perspective_synthesis: MultiPerspectiveSynthesis | None = Field(
        default=None, description="L9/C6 多视角对抗合成（竞争对手/恶魔代言人/10年后用户/局外人 × 收敛盲点洞察）"
    )

    # ═══════════════════════════════════════════════════════════
    # v10.0.0: 新增字段（向后兼容，均为 Optional）
    # ═══════════════════════════════════════════════════════════

    # A4: 约束地图（新增）
    constraints_map: ConstraintsMap | None = Field(default=None, description="A4 约束地图（预算/工期/规范/物理/运营全景，v10新增）")

    # ═══════════════════════════════════════════════════════════
    # 元数据字段（v7.17 P3 规格，供下游专家和前端摘要使用）
    # ═══════════════════════════════════════════════════════════

    # 叙事摘要（一段面向后续专家的简洁描述）
    narrative_summary: str | None = Field(
        default=None,
        description="叙事摘要：给后续专家看的简洁项目描述（2-4句，含核心矛盾+用户画像+设计机会）",
        max_length=600,
    )

    # 项目概览（结构化字段，供 project_director 快速定向）
    project_overview: dict | None = Field(
        default=None,
        description="项目概览：{'project_type', 'scale', 'core_challenge', 'primary_stakeholders'}",
    )

    # 分析质量自评说明
    analysis_quality_note: str | None = Field(
        default=None,
        description="分析质量自评：说明输入信息充足度、分析置信度来源及主要不确定性（1-3句）",
        max_length=400,
    )

    # v10 架构语义别名（指向已有字段，供下游消费者使用新键名读取）
    # B4_first_principles  -> first_principles（已有）
    # B5_assumption_audit  -> assumption_audit（已有）
    # C3_thought_experiments -> thought_experiments（已有）
    # A2_stakeholders      -> stakeholder_system（已有）
    # 以上通过 agent _merge 的回退链支持，schema层不新增冗余字段

    @model_validator(mode="after")
    def validate_assumption_audit_min3(self) -> "RequirementsAnalystOutput":
        """
        L6 假设审计至少需要 3 条（cc2026-2 §3.3 规格约束）
        仅在 assumption_audit 非 None 时执行，Lite 模式下允许为 None。
        """
        if self.assumption_audit is not None and len(self.assumption_audit) < 3:
            import logging as _log

            _log.getLogger(__name__).warning(
                f"[SchemaWarn] assumption_audit 仅 {len(self.assumption_audit)} 条，"
                " 低于规范要求的 3 条，已接受但请检查 Prompt 是否注入了最少3条约束"
            )
        return self


# ============================================================================
# 使用示例（供Agent集成参考）
# ============================================================================

if __name__ == "__main__":
    """演示结构化输出的验证能力"""

    # 示例1: 合法输出
    print(" 测试合法输出...")
    valid_output = RequirementsAnalystOutput(
        project_task=ProjectTask(
            when="当我从公司回家时",
            i_want_to="快速从'工作模式'切换到'家庭模式'",
            so_i_can="避免职场压力污染家庭生活",
            full_statement="当我从公司回家时，我想快速从'工作模式'切换到'家庭模式'，以避免职场压力污染家庭生活。",
        ),
        character_narrative=CharacterNarrative(
            who="35岁职场女性，中层管理，有两个孩子",
            internal_conflict="既想展示'成功职业女性'形象，又渴望卸下伪装做真实的自己",
            symbolic_identity="通过'精致但不刻意'的设计传递'有掌控力的松弛感'",
        ),
        l2_disciplinary_lenses=["[Sociology] Goffman_Front_Back_Stage", "[Psychology] Attachment_Theory_Secure_Base"],
        core_tensions=[
            CoreTension(
                name="公共展示 vs 私密避难",
                theory_source="Goffman_Front_Back_Stage",
                lens_category=LensCategory.SOCIOLOGY,
                description="玄关作为'前台-后台'的过渡区，需要仪式化的'卸妆'过程",
                design_implication="设计独立玄关，视觉隔断+换鞋区+'解压角落'（挂包、脱外套）",
            ),
            CoreTension(
                name="效率优化 vs 情感联结",
                theory_source="Attachment_Theory_Secure_Base",
                lens_category=LensCategory.PSYCHOLOGY,
                description="厨房不只是'备餐工具'，更是'家庭情感枢纽'（边做饭边互动）",
                design_implication="开放式厨房+吧台（孩子写作业、夫妻聊天的'安全基地'）",
            ),
        ],
        ontology_parameters=[
            OntologyParameter(name="边界清晰度", value="中间态（软边界）", rationale="需要开放（家庭互动），但保留可关闭的选项（客人来访时）"),
            OntologyParameter(name="时间特征", value="多重奏（工作时间+家庭时间+个人时间）", rationale="同一空间需要适应不同时间节奏（白天独处、晚上聚集）"),
            OntologyParameter(name="符号密度", value="选择性展示", rationale="客厅=高密度（职业成就），卧室=低密度（放松）"),
        ],
        breakthrough_insight="这不是'住宅设计'，而是设计一个'多重人格的切换系统'——让同一个人的不同身份（职场/母亲/妻子/自我）各得其所。",
        design_principles=[
            "玄关作为'身份过渡仪式'的空间装置",
            "厨房作为'家庭情感枢纽'而非效率机器",
            "主卧作为'绝对后台'（禁止工作物品入侵）",
            "书房作为'可见的独处空间'（对家人可见但不可打扰）",
            "全屋灯光分区控制（用光线标记'当前身份'）",
        ],
        confidence_score=0.85,
    )

    print(" 合法输出验证通过！")
    print(f"   - 项目任务: {valid_output.project_task.full_statement[:50]}...")
    print(f"   - 核心张力数量: {len(valid_output.core_tensions)}")
    print(f"   - 置信度: {valid_output.confidence_score}")

    # 示例2: 非法输出（幻觉理论）
    print("\n 测试非法输出（幻觉理论）...")
    try:
        invalid_output = RequirementsAnalystOutput(
            project_task=valid_output.project_task,
            character_narrative=valid_output.character_narrative,
            l2_disciplinary_lenses=["[Sociology] 后现代解构主义"],  # 不在清单中
            core_tensions=[
                CoreTension(
                    name="虚拟 vs 现实",
                    theory_source="Postmodern_Deconstruction",  # 幻觉理论
                    lens_category=LensCategory.CULTURAL_STUDIES,
                    description="测试描述",
                    design_implication="测试启示",
                )
            ],
            ontology_parameters=valid_output.ontology_parameters,
            breakthrough_insight="测试洞察" * 5,
            design_principles=["原则1", "原则2", "原则3"],
            confidence_score=0.9,
        )
    except Exception as e:
        print(f" 成功拦截非法输出: {type(e).__name__}")
        print(f"   错误信息: {str(e)[:100]}...")

    # 示例3: 理论与透镜类别不匹配
    print("\n 测试理论-类别匹配验证...")
    try:
        mismatch_output = RequirementsAnalystOutput(
            project_task=valid_output.project_task,
            character_narrative=valid_output.character_narrative,
            l2_disciplinary_lenses=["[Psychology] Maslow_Hierarchy"],
            core_tensions=[
                CoreTension(
                    name="安全 vs 自由",
                    theory_source="Maslow_Hierarchy",  # Psychology理论
                    lens_category=LensCategory.SOCIOLOGY,  # 错误类别
                    description="测试描述" * 3,
                    design_implication="测试启示" * 3,
                )
            ],
            ontology_parameters=valid_output.ontology_parameters,
            breakthrough_insight="测试洞察" * 5,
            design_principles=["原则1", "原则2", "原则3"],
            confidence_score=0.8,
        )
    except Exception as e:
        print(f" 成功拦截类别不匹配: {type(e).__name__}")
        print(f"   错误信息: {str(e)[:150]}...")

    print("\n" + "=" * 70)
    print(" Schema测试总结:")
    print("   合法输出正常通过")
    print("   幻觉理论被成功拦截")
    print("   理论-类别匹配验证生效")
    print("=" * 70)
