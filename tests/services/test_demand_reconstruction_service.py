from pathlib import Path

from intelligent_project_analyzer.services.demand_reconstruction_insight_protocol import (
    DemandReconstructionInsightProtocol,
)
from intelligent_project_analyzer.services.demand_reconstruction_service import DemandReconstructionService


RURAL_HOME_PROMPT = "50岁男性室内设计师，背井离乡，想在老家建一栋民居，给出建议"
CAFE_PROMPT = "30㎡社区咖啡店，怎么提高翻台和外带效率，给出建议"
STYLE_PROMPT = "我想做一个有东方感但不老气的茶空间，给点建议"
HARD_CONSTRAINT_PROMPT = "小型茶饮店冷藏柜留多大，怎么看"
DEEP_RESEARCH_PROMPT = "我想研究宋代文人雅集对当代会所空间的启发，给出建议"
FORMAL_BRIEF_PROMPT = (
    "四川广元农村300㎡田园民居，业主为50岁男性室内设计师，"
    "请提出完整室内设计概念框架，围绕光、材料、自然、界面和精神性空间。"
)


class FakeLLM:
    def __init__(self, response: str, *, raises: bool = False) -> None:
        self.response = response
        self.raises = raises
        self.prompts: list[str] = []

    def invoke(self, prompt: str):
        self.prompts.append(prompt)
        if self.raises:
            raise RuntimeError("llm unavailable")
        return type("FakeResponse", (), {"content": self.response})()


def _blueprint(prompt: str) -> dict:
    result = DemandReconstructionService().handle_message(
        session={},
        user_message=prompt,
        in_response_to_card_id=None,
        selected_option_id=None,
    )
    assert result is not None
    return result["demand_reconstruction_context"]["blueprint"]


def _reply(prompt: str) -> str:
    result = DemandReconstructionService().handle_message(
        session={},
        user_message=prompt,
        in_response_to_card_id=None,
        selected_option_id=None,
    )
    assert result is not None
    return result["reply"]


def test_rural_home_prompt_uses_reused_context_and_dynamic_sections():
    plan = _blueprint(RURAL_HOME_PROMPT)

    assert plan["reconstruction_type"] == "demand_reconstruction"
    assert plan["artifact_name"] == "action_blueprint"
    assert plan["archetype"]["primary"] == "life_identity"
    assert plan["context_source"]["context_intelligence"] is True
    assert plan["context_source"]["semantic_axes"] is True
    assert plan["context_source"]["space_classification"] is True
    assert plan["sections"]
    section_titles = [section["title"] for section in plan["sections"]]
    assert "真实需求重构" in section_titles
    assert "四个结构轴" in section_titles
    assert "路径分流" in section_titles
    assert any("作品化" in item for section in plan["sections"] for item in section.get("items", []))
    assert plan["brief_handoff_slots"]["owner_profile"]


def test_commercial_prompt_gets_different_structure_than_life_identity_prompt():
    rural = _blueprint(RURAL_HOME_PROMPT)
    cafe = _blueprint(CAFE_PROMPT)

    assert cafe["archetype"]["primary"] == "commercial_operation"
    assert cafe["archetype"]["primary"] != rural["archetype"]["primary"]
    cafe_titles = [section["title"] for section in cafe["sections"]]
    rural_titles = [section["title"] for section in rural["sections"]]
    assert "经营变量" in cafe_titles
    assert "身份与生活结构" not in cafe_titles
    assert "经营变量" not in rural_titles
    assert any("翻台" in item or "外带" in item for section in cafe["sections"] for item in section.get("items", []))


def test_style_and_hard_constraint_prompts_select_different_module_sets():
    style = _blueprint(STYLE_PROMPT)
    hard_constraint = _blueprint(HARD_CONSTRAINT_PROMPT)

    assert style["archetype"]["primary"] == "style_semantics"
    assert hard_constraint["archetype"]["primary"] == "hard_constraint"
    assert "语义边界" in [section["title"] for section in style["sections"]]
    assert "隐藏开关" in [section["title"] for section in hard_constraint["sections"]]


def test_deep_research_prompt_is_routed_without_pretending_to_complete_evidence():
    plan = _blueprint(DEEP_RESEARCH_PROMPT)

    assert plan["routing"]["target"] == "deep_research"
    assert "深度研究" in plan["routing"]["label"]
    assert any("证据" in item for section in plan["sections"] for item in section.get("items", []))


def test_formal_brief_prompt_still_starts_with_demand_reconstruction_layer():
    service = DemandReconstructionService()

    assert service.should_handle(FORMAL_BRIEF_PROMPT) is True
    result = service.handle_message(
        session={},
        user_message=FORMAL_BRIEF_PROMPT,
        in_response_to_card_id=None,
        selected_option_id=None,
    )

    assert result is not None
    assert result["dialogue_layer"] == "demand_reconstruction"
    assert result["guidance_card"]["card_type"] == "demand_reconstruction_blueprint"


def test_demand_reconstruction_reply_and_card_use_demand_reconstruction_language():
    result = DemandReconstructionService().handle_message(
        session={},
        user_message=RURAL_HOME_PROMPT,
        in_response_to_card_id=None,
        selected_option_id=None,
    )

    assert result is not None
    assert "## 需求重构" in result["reply"]
    assert "我建议先追问一个关键点" in result["reply"]
    assert "阶段性返乡居所" in result["reply"]
    assert "行动蓝图" not in result["reply"]
    assert result["demand_reconstruction_context"]["reconstruction_type"] == "demand_reconstruction"
    assert result["demand_reconstruction_context"]["artifact_name"] == "action_blueprint"
    assert result["guidance_card"]["title"] == "需求重构"
    assert result["guidance_card"]["display_label"] == "需求重构"
    assert result["guidance_card"]["artifact_name"] == "行动蓝图"
    option_labels = [option["label"] for option in result["guidance_card"]["options"]]
    assert "继续需求重构" in option_labels


def test_demand_reconstruction_service_source_does_not_keep_specific_rural_home_answer_branch():
    source = Path("intelligent_project_analyzer/services/demand_reconstruction_service.py").read_text(encoding="utf-8")

    assert 'if "老家" in text and "民居" in text and "设计师" in text' not in source
    assert "离乡多年的专业设计师，如何重新安放自己与故乡关系" not in source


def test_insight_protocol_is_centralized_outside_demand_reconstruction_service():
    source = Path("intelligent_project_analyzer/services/demand_reconstruction_service.py").read_text(encoding="utf-8")

    assert "第一性剥离" not in source
    assert "空间被雇佣" not in source
    assert "锐度自检" not in source
    assert "温馨舒适" not in source
    assert "品质生活" not in source


def test_insight_protocol_owns_prompt_and_quality_gate():
    protocol = DemandReconstructionInsightProtocol()
    prompt = protocol.build_prompt(
        adapter_context={"source_message": RURAL_HOME_PROMPT},
        rule_plan={"task_reframe": "规则蓝图", "sections": []},
    )

    assert "第一性剥离" in prompt
    assert "空间被雇佣" in prompt
    assert "不要在前台输出这些内部术语" in prompt
    assert protocol.passes_quality_gate(
        {
            "task_reframe": "这个项目是为用户打造温馨舒适的品质生活空间，满足业主对于现代乡村民居的整体需求。",
            "project_viability_judgment": "项目整体可以成立。",
            "primary_risk": "主要风险是功能不够齐全、动线不够合理，影响后续空间利用率。",
            "sections": [{"title": "泛化判断", "body": "品质生活", "items": []}],
            "key_forks": ["喜欢现代还是传统？"],
            "unknowns": ["面积未知。"],
            "next_question": "你喜欢什么风格",
        }
    ) is False


def test_llm_insight_layer_rewrites_the_rule_blueprint_when_available():
    llm = FakeLLM(
        """
        {
          "task_reframe": "这不是建一栋返乡民居的问题，而是一个离乡多年的设计师，如何把职业身份、原乡关系和后半生生活重新放回同一个屋檐下。",
          "project_viability_judgment": "项目能否成立，先看它是不是愿意从作品冲动退回到真实生活。",
          "primary_risk": "真正的对手不是乡村环境，而是设计师把自己的家做成最后一件作品的冲动。",
          "sections": [
            {
              "title": "洞察判断",
              "body": "这栋房子需要先安放人，再安放形式。",
              "items": ["原乡关系不是背景，而是空间秩序的一部分。", "专业表达必须被生活节奏约束。"],
              "emphasis": "high"
            }
          ],
          "key_forks": ["长期居住还是阶段性返乡？", "家族关系进入日常还是只进入节庆？"],
          "unknowns": ["真实居住频率未知。", "家庭成员结构未知。"],
          "next_question": "这栋房子首先是给自己住，还是给自己与故乡重新建立关系"
        }
        """
    )

    result = DemandReconstructionService(llm=llm).handle_message(
        session={},
        user_message=RURAL_HOME_PROMPT,
        in_response_to_card_id=None,
        selected_option_id=None,
    )

    assert result is not None
    blueprint = result["demand_reconstruction_context"]["blueprint"]
    assert blueprint["insight_source"] == "llm"
    assert "真正的对手不是乡村环境" in result["reply"]
    assert "最后一件作品" in blueprint["primary_risk"]
    assert "当前规则蓝图" in llm.prompts[0]
    assert "禁止输出完整方案" in llm.prompts[0]
    assert "第一性剥离" in llm.prompts[0]
    assert "核心张力" in llm.prompts[0]
    assert "空间被雇佣" in llm.prompts[0]
    assert "锐度自检" in llm.prompts[0]
    assert "不要在前台输出这些内部术语" in llm.prompts[0]


def test_llm_failure_falls_back_to_rule_blueprint_without_blocking_entry():
    llm = FakeLLM("", raises=True)

    result = DemandReconstructionService(llm=llm).handle_message(
        session={},
        user_message=RURAL_HOME_PROMPT,
        in_response_to_card_id=None,
        selected_option_id=None,
    )

    assert result is not None
    blueprint = result["demand_reconstruction_context"]["blueprint"]
    assert blueprint["insight_source"] == "rule_fallback"
    assert "作品化住宅压过真实生活" in result["reply"]


def test_low_quality_or_over_reaching_llm_output_is_rejected():
    llm = FakeLLM(
        """
        {
          "task_reframe": "建议先明确需求。",
          "project_viability_judgment": "可以做。",
          "primary_risk": "我可以直接给你完整方案和施工级建议。",
          "sections": [],
          "key_forks": [],
          "unknowns": [],
          "next_question": "你想怎么做"
        }
        """
    )

    result = DemandReconstructionService(llm=llm).handle_message(
        session={},
        user_message=RURAL_HOME_PROMPT,
        in_response_to_card_id=None,
        selected_option_id=None,
    )

    assert result is not None
    blueprint = result["demand_reconstruction_context"]["blueprint"]
    assert blueprint["insight_source"] == "rule_fallback"
    assert "完整方案和施工级建议" not in result["reply"]


def test_cliche_llm_output_is_rejected_even_when_structurally_complete():
    llm = FakeLLM(
        """
        {
          "task_reframe": "这个项目是为用户打造温馨舒适的品质生活空间，满足业主对于现代乡村民居的整体需求。",
          "project_viability_judgment": "项目整体可以成立，重点是打造简约大气、自然和谐、有归属感的居住环境。",
          "primary_risk": "主要风险是功能不够齐全、动线不够合理，影响后续空间利用率和居住体验。",
          "sections": [
            {
              "title": "泛化判断",
              "body": "需要通过合理布局和品质生活氛围营造，让空间更温馨舒适。",
              "items": ["功能齐全。", "空间利用率高。"],
              "emphasis": "medium"
            }
          ],
          "key_forks": ["喜欢现代还是传统？", "重视功能还是氛围？"],
          "unknowns": ["面积未知。", "预算未知。"],
          "next_question": "你喜欢什么风格"
        }
        """
    )

    result = DemandReconstructionService(llm=llm).handle_message(
        session={},
        user_message=RURAL_HOME_PROMPT,
        in_response_to_card_id=None,
        selected_option_id=None,
    )

    assert result is not None
    blueprint = result["demand_reconstruction_context"]["blueprint"]
    assert blueprint["insight_source"] == "rule_fallback"
    assert "温馨舒适的品质生活" not in result["reply"]
