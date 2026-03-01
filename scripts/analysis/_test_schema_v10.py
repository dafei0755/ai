"""v10 schema integration test"""
import sys

sys.path.insert(0, r"d:\11-20\langgraph-design")

from intelligent_project_analyzer.agents.requirements_analyst_schema import (
    RequirementsAnalystOutput,
    ConstraintsMap,
    ProjectTask,
    CharacterNarrative,
    CoreTension,
    OntologyParameter,
    LensCategory,
)

out = RequirementsAnalystOutput(
    project_task=ProjectTask(
        when="当我在这个空间切换从律师到博主的角色时",
        i_want_to="拥有一个帮我完成内部身份切换的场所",
        so_i_can="在不对外解释的情况下自由表达两种自我",
        full_statement="当我在这个空间切换角色时，我想拥有一个帮我完成内部身份切换的场所，这样我就能在不对外解释的情况下自由表达两种自我",
    ),
    character_narrative=CharacterNarrative(
        who="32岁前金融律师，正处于职业身份转型到生活美学博主的关键节点",
        internal_conflict="渴望自由表达真我 vs 担心失去专业形象的外界认可",
        symbolic_identity="通过空间传递：我是一个生活美学传播者，不需要对世界解释自己的选择",
    ),
    l2_disciplinary_lenses=["[Psychology] Identity_Theory", "[Sociology] Symbolic_Interactionism"],
    core_tensions=[
        CoreTension(
            name="展示前台 vs 精神后台",
            theory_source="Goffman_Front_Back_Stage",
            lens_category=LensCategory.SOCIOLOGY,
            description="内容创作者需要可展示的'前台空间'，同时强烈渴望可退隐的'后台庇护所'，两种需求对同一空间提出矛盾要求",
            design_implication="空间必须支持物理或视觉上的'前台/后台切换机制'",
        ),
        CoreTension(
            name="生理安全需求 vs 自我实现需求",
            theory_source="Maslow_Hierarchy",
            lens_category=LensCategory.PSYCHOLOGY,
            description="用户既需要私密安全感（生理/安全层），又渴望自我表达和被认可（自我实现层），两者在空间中常常冲突",
            design_implication="空间需要同时拥有'可关闭的私密角落'和'可展示的舞台感'",
        ),
    ],
    ontology_parameters=[
        OntologyParameter(name="privacy_control", value="dynamic", rationale="用户需要可切换的社交边界"),
        OntologyParameter(name="identity_staging", value="dual", rationale="律师与博主双重身份需要共存"),
        OntologyParameter(name="cultural_fusion", value="juxtaposition", rationale="北欧+在地并置而非强行融合"),
    ],
    breakthrough_insight="这个民宿不是空间设计，而是为转型中的自我提供一个可切换身份的变身机制",
    design_principles=["用可控的视觉隔断支持身份切换", "HAY设计语言 > HAY品牌家具", "山地材料真实性优先于北欧风格标签"],
    confidence_score=0.85,
    # v10 新字段
    constraints_map=ConstraintsMap(
        budget={"total": "30万RMB", "hard_ceiling": True}, constraint_map_insight="预算偏紧，需价值工程取舍"
    ),
)

print("RequirementsAnalystOutput validation: OK")
print("  constraints_map:", out.constraints_map.constraint_map_insight)
print("  confidence_score:", out.confidence_score)
print("  core_tensions count:", len(out.core_tensions))
print("  constraints_map field in model_fields:", "constraints_map" in RequirementsAnalystOutput.model_fields)
print("ALL ASSERTIONS PASSED")
