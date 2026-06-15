from intelligent_project_analyzer.services.scheme_advisor_context_intelligence import (
    SchemeAdvisorContextIntelligence,
)


def _visible_text(card_pages):
    parts = []
    for page in card_pages:
        parts.extend([
            page.get("page_title", ""),
            page.get("prompt_text", ""),
            page.get("helper_text", ""),
        ])
        for option in page.get("options") or []:
            parts.extend([option.get("label", ""), option.get("description", "")])
    return "\n".join(parts)


def test_missing_slot_pages_do_not_expose_internal_step_titles_or_english_keys():
    service = SchemeAdvisorContextIntelligence()

    pages = service._missing_slot_pages(
        [
            {
                "name": "preservation_grade",
                "action": "option_menu",
                "user_visible_note": "确认保护等级会影响改造深度。",
            },
            {
                "name": "structural_condition",
                "action": "certainty_ceiling",
                "user_visible_note": "确认结构条件后才能判断改造尺度。",
            },
            {
                "name": "kitchen_ventilation_and_exhaust",
                "action": "branch_answer_plus_followup",
                "user_visible_note": "确认厨房通风与排烟后才能判断后场边界。",
            },
        ]
    )

    visible = _visible_text(pages)

    assert "确认会卡住方案的条件" in visible
    assert "补齐会改变判断的信息" in visible
    assert "先选一个判断方向" in visible

    for forbidden in [
        "先确认硬约束",
        "选择判断路径",
        "preservation grade",
        "structural condition",
        "kitchen ventilation",
        "exhaust",
    ]:
        assert forbidden not in visible

    assert "保护等级" in visible
    assert "结构条件" in visible
    assert "厨房通风与排烟" in visible


def test_public_label_fallback_translates_common_space_tokens():
    service = SchemeAdvisorContextIntelligence()

    examples = {
        "fire_egress_clearance": "消防疏散净距",
        "zoning_and_flow_diagram": "分区与动线图示",
        "queue_pickup_strategy_note": "排队取餐策略说明",
        "acoustic_comfort_threshold": "声环境舒适底线",
    }

    for key, expected in examples.items():
        assert service._label(key) == expected


def test_public_label_translates_slash_separated_business_tradeoffs():
    service = SchemeAdvisorContextIntelligence()

    examples = {
        "seating_density / diner_comfort": "座位密度 / 用餐舒适",
        "turnover efficiency / brand experience": "翻台效率 / 品牌体验",
        "kitchen_scale / front_of_house_area": "后场规模 / 前场面积",
        "noise_management / vibrant_atmosphere": "噪声管理 / 活力氛围",
    }

    for key, expected in examples.items():
        assert service._label(key) == expected
