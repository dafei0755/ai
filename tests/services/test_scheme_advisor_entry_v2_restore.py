from intelligent_project_analyzer.services.scheme_advisor_entry_service import (
    SchemeAdvisorEntryService,
)
from pathlib import Path


FORMAL_MILK_TEA_PROMPT = (
    "\u6df1\u5733\u5e02\u5357\u5c71\u533a\u6765\u798f\u58eb\u5e7f\u573a"
    "\uff0c\u8d1f\u4e00\u697c\uff0c30\u5e73\u7c73\u5546\u94fa"
    "\uff0c\u5730\u94c1\u901a\u9053\u4e0e\u5546\u573a\u7684\u8fde\u63a5\u5904"
    "\uff0c\u6253\u7b97\u505a\u4e00\u4e2a\u5976\u8336\u5e97"
    "\uff0c\u5e0c\u671b\u534a\u5e74\u80fd\u6536\u56de\u6210\u672c"
    "\uff0c\u6211\u9700\u8981\u4e00\u4efd\u5b8c\u6574\u7684\u8bbe\u8ba1\u5efa\u8bae\u3002"
)


SEAVIEW_FOUNDER_VILLA_PROMPT = (
    "\u6df1\u5733\u6e7e\u4e00\u7ebf\u6d77\u666f\u522b\u5885"
    "\uff0c\u4e1a\u4e3b\u4e3a\u7b2c\u4e00\u4ee3\u521b\u4e1a\u8005"
    "\uff0c\u4ece\u8349\u6839\u594b\u6597\u81f3\u8d44\u672c\u6210\u529f"
    "\uff0c\u5bf9\u7a7a\u95f4\u7684\u671f\u5f85\u65e2\u5305\u542b\u6210\u5c31\u8c61\u5f81"
    "\uff0c\u4e5f\u5305\u542b\u5bb6\u65cf\u4f20\u627f\u4e0e\u5185\u5fc3\u56de\u5f52\u3002"
    "\u8bf7\u4ece\u4e00\u4ee3\u521b\u4e1a\u8005\u7684\u7cbe\u795e\u7ed3\u6784\u51fa\u53d1"
    "\uff0c\u63d0\u51fa\u5b8c\u6574\u5ba4\u5185\u8bbe\u8ba1\u6982\u5ff5"
    "\uff0c\u5305\u62ec\u7a7a\u95f4\u6c14\u573a\u6784\u5efa"
    "\u3001\u516c\u5171\u4e0e\u79c1\u5bc6\u533a\u57df\u6743\u529b\u5173\u7cfb"
    "\u3001\u6d77\u666f\u8d44\u6e90\u5229\u7528\u65b9\u5f0f"
    "\u3001\u6750\u8d28\u8c61\u5f81\u7cfb\u7edf\u4ee5\u53ca\u5982\u4f55"
    "\u907f\u514d\u8fc7\u5ea6\u70ab\u8000\u800c\u8f6c\u5411\u66f4\u5177"
    "\u539a\u5ea6\u7684\u7cbe\u795e\u8868\u8fbe\u3002"
)

PRIVATE_RESIDENCE_CRISIS_ROOM_PROMPT = (
    "\u4e00\u4f4d\u8de8\u56fd\u653f\u6cbb\u4eba\u7269\u5e0c\u671b"
    "\u5728\u79c1\u4eba\u4f4f\u5b85\u4e2d\u5efa\u7acb"
    "\u201c\u5371\u673a\u51b3\u7b56\u5ba4\u201d"
    "\uff0c\u53ef\u5728\u7d27\u6025\u72b6\u6001\u4e0b"
    "\u8f6c\u5316\u4e3a\u6307\u6325\u4e2d\u5fc3\u3002"
    "\u8bf7\u63d0\u51fa\u5b8c\u6574\u8bbe\u8ba1\u6846\u67b6"
    "\uff0c\u5305\u62ec\u901a\u8baf\u7cfb\u7edf\u6574\u5408"
    "\u3001\u9690\u853d\u5b89\u5168\u8bbe\u8ba1"
    "\u4e0e\u5c45\u4f4f\u7a7a\u95f4\u5e73\u8861\u3002"
)

INDEPENDENT_WOMAN_RESIDENCE_PROMPT = (
    "\u6df1\u5733\u5357\u5c71200\u33a1\u5927\u5e73\u5c42"
    "\uff0c\u4e1a\u4e3b\u4e3a38\u5c81\u82f1\u56fd\u6d77\u5f52\u72ec\u7acb\u5973\u6027"
    "\uff0c\u4e0d\u5a5a\u4e3b\u4e49"
    "\uff0c\u5bf9Audrey Hepburn\u8d6b\u672c\u7cbe\u795e\u9ad8\u5ea6\u8ba4\u540c\u3002"
    "\u8bf7\u63d0\u51fa\u5b8c\u6574\u5ba4\u5185\u8bbe\u8ba1\u6982\u5ff5"
    "\uff0c\u4ece\u4f18\u96c5\u3001\u81ea\u5f8b\u3001\u8f7b\u76c8\u4e0e\u73b0\u4ee3\u5973\u6027\u72ec\u7acb\u7cbe\u795e\u51fa\u53d1"
    "\uff0c\u5efa\u7acb\u7a7a\u95f4\u6bd4\u4f8b\u3001\u52a8\u7ebf\u7ec4\u7ec7"
    "\u3001\u793e\u4ea4\u4e0e\u72ec\u5904\u5e73\u8861\u7cfb\u7edf"
    "\uff0c\u5e76\u907f\u514d\u590d\u53e4\u5316\u7b26\u53f7\u5806\u780c\u3002"
)

COMMERCIAL_TRANSIT_RETAIL_PROMPT = (
    "\u5730\u94c1\u6362\u4e58\u901a\u9053\u65c1\u6709\u4e00\u95f418\u5e73\u7c73\u5c0f\u94fa"
    "\uff0c\u79df\u91d1\u5f88\u9ad8\uff0c\u4f46\u6bcf\u5929\u4eba\u6d41\u91cf\u5f88\u5927"
    "\uff0c\u60f3\u505a\u4e00\u4e2a\u4f4e\u6295\u5165\u3001\u5feb\u5468\u8f6c\u7684\u96f6\u552e\u9879\u76ee"
    "\uff0c\u5e0c\u671b6\u4e2a\u6708\u56de\u6536\u6295\u8d44\u3002"
    "\u8bf7\u5e2e\u6211\u5224\u65ad\u7a7a\u95f4\u8bbe\u8ba1\u548c\u7ecf\u8425\u52a8\u7ebf\u5e94\u8be5\u5148\u6293\u54ea\u4e9b\u5173\u952e\u70b9\u3002"
)

MILK_TEA_HARD_BOUNDARY_PROMPT = (
    "\u6211\u60f3\u5728\u5546\u573a\u91cc\u505a\u4e00\u4e2a25\u5e73\u7c73\u5976\u8336\u5e97"
    "\uff0c\u4f46\u662f\u4e0a\u4e0b\u6c34\u3001\u7535\u91cf\u3001\u6392\u70df\u548c\u6d88\u9632\u90fd\u8fd8\u6ca1\u786e\u8ba4"
    "\uff0c\u60f3\u5148\u5224\u65ad\u8fd9\u4e2a\u94fa\u4f4d\u80fd\u4e0d\u80fd\u505a\u3002"
)

MILK_TEA_OPERATIONAL_DIAGNOSTIC_PROMPT = (
    "\u6211\u60f3\u6d4b\u8bd5\u4e00\u4e0b\u5976\u8336\u5e97\u7684\u7a7a\u95f4\u95ee\u9898"
    "\uff0c\u89c2\u5bdf\u95e8\u5934\u662f\u5426\u80fd\u8ba9\u4eba\u505c\u4e0b"
    "\uff0c\u5e73\u5747\u70b9\u5355\u3001\u51fa\u676f\u3001\u53d6\u9910\u548c\u6392\u961f\u54ea\u91cc\u6700\u5bb9\u6613\u5361\u3002"
)

COFFEE_CONTEXTUAL_PROMPT = (
    "\u5199\u5b57\u697c\u4e00\u697c\u670920\u5e73\u7c73\u5c0f\u94fa"
    "\uff0c\u60f3\u505a\u4e00\u4e2a\u7cbe\u54c1\u5496\u5561\u5e97"
    "\uff0c\u4e3b\u8981\u9762\u5411\u4e0a\u73ed\u65cf\u77ed\u505c\u7559\u548c\u5916\u5e26"
    "\uff0c\u9700\u8981\u5148\u5224\u65ad\u7a7a\u95f4\u8be5\u6293\u4ec0\u4e48\u3002"
)


def test_formal_milk_tea_prompt_enters_design_taskbook_entry_flow():
    result = SchemeAdvisorEntryService().handle_message(
        session={},
        user_message=FORMAL_MILK_TEA_PROMPT,
        in_response_to_card_id=None,
        selected_option_id=None,
    )

    assert result is not None
    assert result["intent"] == "scheme_advisor_entry"
    assert result["guidance_card"]["card_type"] == "scheme_round_1"
    assert result["scheme_entry_state"]["step"] == "round_1"
    assert result["guidance_card"]["pages"]


def test_formal_milk_tea_round_one_card_uses_configured_entry_copy():
    result = SchemeAdvisorEntryService().handle_message(
        session={},
        user_message=FORMAL_MILK_TEA_PROMPT,
        in_response_to_card_id=None,
        selected_option_id=None,
    )

    page_titles = [page.get("page_title") for page in result["guidance_card"]["pages"]]

    assert "先看回本靠什么撑住" in page_titles
    assert "先看能不能回本" not in page_titles
    assert result["guidance_card"].get("source") == "entry_copy.configured"


def test_formal_milk_tea_round_two_card_uses_configured_entry_copy():
    service = SchemeAdvisorEntryService()
    first = service.handle_message(
        session={},
        user_message=FORMAL_MILK_TEA_PROMPT,
        in_response_to_card_id=None,
        selected_option_id=None,
    )
    second = service.handle_message(
        session={
            "scheme_advisor_entry_v2": first["scheme_entry_state"],
            "pending_guidance_card": first["guidance_card"],
        },
        user_message="先保半年回本和门头转化，高峰出杯不能拖慢。",
        in_response_to_card_id=first["guidance_card"]["card_id"],
        selected_option_id=None,
    )

    page_titles = [page.get("page_title") for page in second["guidance_card"]["pages"]]

    assert "优先级冲突" in page_titles
    assert "这家店最像哪种打法" not in page_titles
    assert second["guidance_card"].get("source") == "entry_copy.configured"


def test_beverage_round_two_card_type_priority_comes_from_configured_rules():
    service = SchemeAdvisorEntryService()
    tea_copy = service._entry_copy.setdefault("tea_retail_space", {})
    tea_copy["round_2_cards"] = {
        "hard_boundary": {
            "title": "配置里的硬条件二轮",
            "prompt_text": "只确认会改变能不能推进的底线。",
            "pages": [
                {
                    "page_title": "先保硬条件",
                    "prompt_text": "如果只能先确认一个底线，优先确认什么？",
                    "response_mode": "single_select",
                    "max_select": 1,
                    "allow_freetext": True,
                    "options": [
                        {
                            "id": "water_power_fire",
                            "label": "上下水、电量和消防",
                            "description": "先确认铺位能不能合法稳定经营。",
                        }
                    ],
                }
            ],
        }
    }
    tea_copy["round_2_card_selection_rules"] = [
        {
            "card_path": "tea_retail_space.round_2_cards.hard_boundary",
            "when": {"tags_all": ["hard_boundary"]},
        },
        {
            "card_path": "tea_retail_space.round_2_card",
            "default": True,
        },
    ]

    card = service._beverage_round_2_card(
        {"subdomain_id": "tea_drink_store", "entry_scene_tags": ["hard_boundary"]}
    )

    assert card["title"] == "配置里的硬条件二轮"
    assert card["pages"][0]["page_title"] == "先保硬条件"


def test_beverage_stage_conclusion_template_comes_from_configured_rules():
    service = SchemeAdvisorEntryService()
    tea_copy = service._entry_copy.setdefault("tea_retail_space", {})
    tea_copy["stage_conclusion_templates"] = {
        "hard_boundary": "配置里的硬条件收束：{tier_name}；重心是{directory_focus}。"
    }
    tea_copy["stage_conclusion_selection_rules"] = [
        {
            "template_path": "tea_retail_space.stage_conclusion_templates.hard_boundary",
            "when": {"tags_all": ["hard_boundary"]},
        },
        {
            "template_path": "tea_retail_space.stage_conclusion_template",
            "default": True,
        },
    ]
    state = {
        "initial_input": MILK_TEA_HARD_BOUNDARY_PROMPT,
        "rounds": [],
        "profile": {
            "subdomain_id": "tea_drink_store",
            "space_label": "茶饮小店",
            "entry_scene_tags": ["hard_boundary"],
            "maturity": {"pending": ["物业条件表"]},
        },
    }

    reply = service._build_stage_conclusion_fallback(
        state,
        "先确认上下水、电量、排烟和消防。",
        "standard",
    )

    assert reply.startswith("配置里的硬条件收束：标准版")
    assert "上下水" in reply or "消防" in reply or "取餐外卖与排队边界" in reply


def test_beverage_version_intro_template_comes_from_configured_rules():
    service = SchemeAdvisorEntryService()
    tea_copy = service._entry_copy.setdefault("tea_retail_space", {})
    tea_copy["version_intro_templates"] = {
        "coffee": "配置里的咖啡版本说明：{tier_name}；打法是{model_label}。"
    }
    tea_copy["version_intro_selection_rules"] = [
        {
            "template_path": "tea_retail_space.version_intro_templates.coffee",
            "when": {
                "profile_contains_any": {
                    "subdomain_id": ["coffee_shop"],
                    "activation_pack_id": ["coffee_shop_pack"],
                }
            },
        },
        {
            "template_path": "tea_retail_space.version_intro_template",
            "default": True,
        },
    ]
    state = {
        "initial_input": COFFEE_CONTEXTUAL_PROMPT,
        "rounds": [],
        "profile": {
            "subdomain_id": "coffee_shop",
            "activation_pack_id": "coffee_shop_pack",
            "space_label": "咖啡小店",
            "entry_scene_tags": ["office"],
            "version_score": {"reasons": ["涉及投资、租金、回本或成本压力"]},
        },
    }

    reply = service._build_version_intro_fallback(state, "standard")

    assert reply.startswith("配置里的咖啡版本说明：标准版")
    assert "打法是" in reply


def test_generic_stage_conclusion_template_comes_from_semantic_axis_rules():
    service = SchemeAdvisorEntryService()
    generic_copy = service._entry_copy.setdefault("generic_project", {})
    generic_copy["stage_conclusion_templates"] = {
        "residential_identity": "配置里的身份住宅收束：{tier_name}；重心是{decision_focus}；待校准是{pending}。"
    }
    generic_copy["stage_conclusion_selection_rules"] = [
        {
            "template_path": "generic_project.stage_conclusion_templates.residential_identity",
            "when": {
                "profile_contains_any": {
                    "space_axis_id": ["private_residential_identity"]
                }
            },
        },
        {
            "template_path": "generic_project.stage_conclusion",
            "default": True,
        },
    ]
    state = {
        "initial_input": SEAVIEW_FOUNDER_VILLA_PROMPT,
        "rounds": [],
        "profile": {
            "space_label": "深圳湾海景别墅",
            "classification": {"project_type": "personal_residential"},
            "space_axis": {
                "primary_axis_id": "private_residential_identity_legacy",
                "label": "私人住宅身份与传承",
            },
            "maturity": {"pending": ["家庭成员结构", "平面图"]},
        },
    }

    reply = service._build_stage_conclusion_fallback(
        state,
        "先保身份表达、家族传承和海景利用。",
        "standard",
    )

    assert reply.startswith("配置里的身份住宅收束：标准版")
    assert "身份" in reply or "家族" in reply or "海景" in reply
    assert "家庭成员结构" in reply


def test_generic_version_intro_template_comes_from_semantic_axis_rules():
    service = SchemeAdvisorEntryService()
    generic_copy = service._entry_copy.setdefault("generic_project", {})
    generic_copy["version_intro_templates"] = {
        "residential_identity": "配置里的身份住宅版本说明：{tier_name}；依据是{reason_text}；项目是{space_label}。"
    }
    generic_copy["version_intro_selection_rules"] = [
        {
            "template_path": "generic_project.version_intro_templates.residential_identity",
            "when": {
                "profile_contains_any": {
                    "space_axis_id": ["private_residential_identity"]
                }
            },
        },
        {
            "template_path": "generic_project.version_intro",
            "default": True,
        },
    ]
    state = {
        "initial_input": SEAVIEW_FOUNDER_VILLA_PROMPT,
        "rounds": [],
        "profile": {
            "space_label": "深圳湾海景别墅",
            "classification": {"project_type": "personal_residential"},
            "space_axis": {
                "primary_axis_id": "private_residential_identity_legacy",
                "label": "私人住宅身份与传承",
            },
            "version_score": {"reasons": ["涉及复杂身份表达和家族传承"]},
        },
    }

    reply = service._build_version_intro_fallback(state, "standard")

    assert reply.startswith("配置里的身份住宅版本说明：标准版")
    assert "身份" in reply or "家族" in reply
    assert "深圳湾海景别墅" in reply


def test_generic_first_confidence_template_comes_from_semantic_axis_rules():
    service = SchemeAdvisorEntryService()
    generic_copy = service._entry_copy.setdefault("generic_project", {})
    generic_copy["first_confidence_templates"] = {
        "residential_identity": "配置里的身份住宅首答：{space_label}；先看{decision_focus}。"
    }
    generic_copy["first_confidence_selection_rules"] = [
        {
            "template_path": "generic_project.first_confidence_templates.residential_identity",
            "when": {
                "profile_contains_any": {
                    "space_axis_id": ["private_residential_identity"]
                }
            },
        },
        {
            "template_path": "first_confidence.default_project",
            "default": True,
        },
    ]
    profile = {
        "space_label": "深圳湾海景别墅",
        "classification": {"project_type": "personal_residential"},
        "space_axis": {
            "primary_axis_id": "private_residential_identity_legacy",
            "label": "私人住宅身份与传承",
        },
    }

    reply = service._build_first_confidence_fallback(
        profile,
        SEAVIEW_FOUNDER_VILLA_PROMPT,
    )

    assert reply.startswith("配置里的身份住宅首答：深圳湾海景别墅")
    assert "身份" in reply or "家族" in reply or "精神" in reply


def test_generic_first_confidence_template_can_explain_knowledge_coverage_ceiling():
    service = SchemeAdvisorEntryService()
    generic_copy = service._entry_copy.setdefault("generic_project", {})
    generic_copy["first_confidence_templates"] = {
        "residential_identity": "配置里的封顶首答：{coverage_note}"
    }
    generic_copy["first_confidence_selection_rules"] = [
        {
            "template_path": "generic_project.first_confidence_templates.residential_identity",
            "when": {
                "profile_contains_any": {
                    "space_axis_id": ["private_residential_identity"]
                }
            },
        },
    ]
    profile = {
        "space_label": "深圳湾海景别墅",
        "classification": {"project_type": "personal_residential"},
        "space_axis": {
            "primary_axis_id": "private_residential_identity_legacy",
            "label": "私人住宅身份与传承",
        },
        "context_packet": {
            "knowledge_binding": {
                "coverage_ceiling": {
                    "coverage_level": "general_method_only",
                    "ceiling_level": "strategy_framework",
                    "must_not_claim_specialist_coverage": True,
                    "user_visible_note": (
                        "当前还没有足够的专科知识支撑，只能先给通用方法论和策略级判断，"
                        "不能套用专科知识包。"
                    ),
                }
            }
        },
    }

    reply = service._build_first_confidence_fallback(
        profile,
        SEAVIEW_FOUNDER_VILLA_PROMPT,
    )

    assert reply.startswith("配置里的封顶首答：")
    assert "只能先给通用方法论和策略级判断" in reply
    assert "不能套用专科知识包" in reply
    assert "general_method_only" not in reply
    assert "coverage_ceiling" not in reply


def test_generic_round_one_card_template_comes_from_semantic_axis_rules():
    service = SchemeAdvisorEntryService()
    generic_copy = service._entry_copy.setdefault("generic_project", {})
    generic_copy["round_1_cards"] = {
        "residential_identity": {
            "title": "配置里的身份住宅首轮卡",
            "prompt_text": "先确认身份表达、家族关系和海景资源。",
            "pages": [
                {
                    "page_title": "先看精神主轴",
                    "prompt_text": "这个家的精神主轴最应该先保什么？",
                    "response_mode": "single_select",
                    "max_select": 1,
                    "allow_freetext": True,
                    "options": [
                        {
                            "id": "legacy",
                            "label": "家族传承",
                            "description": "先保家族关系和长期精神秩序。",
                        }
                    ],
                }
            ],
        }
    }
    generic_copy["round_1_card_selection_rules"] = [
        {
            "card_path": "generic_project.round_1_cards.residential_identity",
            "when": {
                "profile_contains_any": {
                    "space_axis_id": ["private_residential_identity"]
                }
            },
        },
        {
            "card_path": "generic_project.round_1_cards.default",
            "default": True,
        },
    ]
    profile = {
        "space_label": "深圳湾海景别墅",
        "classification": {"project_type": "personal_residential"},
        "space_axis": {
            "primary_axis_id": "private_residential_identity_legacy",
            "label": "私人住宅身份与传承",
        },
        "question_plan": {
            "round_1_card": {
                "title": "计划里的旧卡",
                "prompt_text": "这个应该被配置覆盖。",
                "pages": [
                    {
                        "page_title": "旧页面",
                        "prompt_text": "旧问题",
                        "options": [],
                    }
                ],
            }
        },
    }

    card = service._round_1_card_for_profile(profile)

    assert card["title"] == "配置里的身份住宅首轮卡"
    assert card.get("source") == "entry_copy.configured"
    assert card["pages"][0]["page_title"] == "先看精神主轴"


def test_standard_beverage_entry_cards_do_not_keep_service_level_copy_blocks():
    source = Path(
        "intelligent_project_analyzer/services/scheme_advisor_entry_service.py"
    ).read_text(encoding="utf-8")

    retired_service_copy = [
        "先看能不能回本",
        "这家店最像哪种打法",
        "最不能接受哪种失败",
        "这份建议需要做到多深",
    ]

    assert not any(copy in source for copy in retired_service_copy)


def test_milk_tea_hard_boundary_card_uses_configured_entry_copy():
    result = SchemeAdvisorEntryService().handle_message(
        session={},
        user_message=MILK_TEA_HARD_BOUNDARY_PROMPT,
        in_response_to_card_id=None,
        selected_option_id=None,
    )

    card = result["guidance_card"]

    assert card.get("source") == "entry_copy.configured"
    assert card["title"] == "先判断硬条件能不能成立"
    assert [page.get("page_title") for page in card["pages"]][:2] == [
        "先看硬条件",
        "先看制作条件",
    ]


def test_milk_tea_operational_diagnostic_card_uses_configured_entry_copy():
    result = SchemeAdvisorEntryService().handle_message(
        session={},
        user_message=MILK_TEA_OPERATIONAL_DIAGNOSTIC_PROMPT,
        in_response_to_card_id=None,
        selected_option_id=None,
    )

    card = result["guidance_card"]

    assert card.get("source") == "entry_copy.configured"
    assert card["title"] == "先做茶饮空间运营诊断"
    assert "先看转化卡在哪" in [page.get("page_title") for page in card["pages"]]


def test_coffee_contextual_round_one_card_uses_configured_entry_copy():
    result = SchemeAdvisorEntryService().handle_message(
        session={},
        user_message=COFFEE_CONTEXTUAL_PROMPT,
        in_response_to_card_id=None,
        selected_option_id=None,
    )

    card = result["guidance_card"]
    first_page = card["pages"][0]

    assert card.get("source") == "entry_copy.configured"
    assert card["title"] == "先把这家咖啡店怎么做成说清楚"
    assert first_page["prompt_text"] == "这家咖啡店最应该靠什么让顾客愿意进来并接受短停留？"


def test_beverage_round_one_card_type_priority_comes_from_configured_rules():
    service = SchemeAdvisorEntryService()
    tea_copy = service._entry_copy.setdefault("tea_retail_space", {})
    tea_copy["round_1_card_selection_rules"] = [
        {
            "card_path": "tea_retail_space.contextual_round_1_cards.default",
            "when": {"tags_all": ["hard_boundary"]},
        },
        {
            "card_path": "tea_retail_space.hard_boundary_card",
            "when": {"tags_all": ["hard_boundary"]},
        },
        {
            "card_path": "tea_retail_space.round_1_card",
            "default": True,
        },
    ]

    card = service._beverage_round_1_card(
        {"subdomain_id": "tea_drink_store", "entry_scene_tags": ["hard_boundary"]}
    )

    assert card["title"] == "先把这家饮品店怎么做成说清楚"


def test_beverage_round_one_card_selection_does_not_keep_service_priority_chain():
    source = Path(
        "intelligent_project_analyzer/services/scheme_advisor_entry_service.py"
    ).read_text(encoding="utf-8")
    body = source.split("def _beverage_round_1_card", 1)[1].split(
        "def _beverage_round_2_card", 1
    )[0]

    retired_priority_branches = [
        "_is_coffee_entry_profile",
        '"hard_boundary" in tags',
        '"operational_diagnostic" in tags',
        '{"transit", "payback"}.issubset(tags)',
        "_beverage_hard_boundary_card()",
        "_beverage_operational_diagnostic_card()",
        "_beverage_contextual_round_1_card(profile)",
    ]

    assert not any(branch in body for branch in retired_priority_branches)
    assert "def _beverage_hard_boundary_card" not in source
    assert "def _beverage_operational_diagnostic_card" not in source
    assert "def _beverage_contextual_round_1_card" not in source
    assert "def _is_coffee_entry_profile" not in source


def test_beverage_special_entry_cards_do_not_keep_service_level_copy_blocks():
    source = Path(
        "intelligent_project_analyzer/services/scheme_advisor_entry_service.py"
    ).read_text(encoding="utf-8")

    retired_service_copy = [
        "先做茶饮空间运营诊断",
        "先判断硬条件能不能成立",
        "先把这家咖啡店怎么做成说清楚",
        "先把这家饮品店怎么做成说清楚",
        "先看转化卡在哪",
        "先看硬条件",
        "先看顾客为什么买",
    ]

    assert not any(copy in source for copy in retired_service_copy)


def test_beverage_first_confidence_replies_use_configured_entry_copy():
    service = SchemeAdvisorEntryService()
    service._entry_copy.setdefault("tea_retail_space", {})["first_confidence_variants"] = {
        "coffee": "配置里的咖啡首轮判断",
        "hard_boundary": "配置里的硬条件首轮判断",
        "operational_diagnostic": "配置里的运营诊断首轮判断",
        "transit_payback": "配置里的交通回本首轮判断",
        "default": "配置里的饮品默认首轮判断",
    }

    assert service._build_beverage_first_confidence(
        {"subdomain_id": "coffee_shop", "entry_scene_tags": ["office"]}
    ) == "配置里的咖啡首轮判断"
    assert service._build_beverage_first_confidence(
        {"subdomain_id": "tea_drink_store", "entry_scene_tags": ["hard_boundary"]}
    ) == "配置里的硬条件首轮判断"
    assert service._build_beverage_first_confidence(
        {"subdomain_id": "tea_drink_store", "entry_scene_tags": ["operational_diagnostic"]}
    ) == "配置里的运营诊断首轮判断"
    assert service._build_beverage_first_confidence(
        {"subdomain_id": "tea_drink_store", "entry_scene_tags": ["transit", "payback"]}
    ) == "配置里的交通回本首轮判断"
    assert service._build_beverage_first_confidence(
        {"subdomain_id": "tea_drink_store", "entry_scene_tags": ["general_tea"]}
    ) == "配置里的饮品默认首轮判断"


def test_beverage_first_confidence_variant_priority_comes_from_configured_rules():
    service = SchemeAdvisorEntryService()
    tea_copy = service._entry_copy.setdefault("tea_retail_space", {})
    tea_copy["first_confidence_variants"] = {
        "payback": "配置优先选择回本判断",
        "transit_payback": "配置里的交通回本判断",
        "default": "配置里的饮品默认判断",
    }
    tea_copy["first_confidence_variant_rules"] = [
        {
            "variant": "payback",
            "when": {"tags_all": ["payback"]},
        },
        {
            "variant": "transit_payback",
            "when": {"tags_all": ["transit", "payback"]},
        },
        {
            "variant": "default",
            "default": True,
        },
    ]

    assert service._build_beverage_first_confidence(
        {"subdomain_id": "tea_drink_store", "entry_scene_tags": ["transit", "payback"]}
    ) == "配置优先选择回本判断"


def test_beverage_first_confidence_variant_selection_does_not_keep_service_priority_chain():
    source = Path(
        "intelligent_project_analyzer/services/scheme_advisor_entry_service.py"
    ).read_text(encoding="utf-8")
    body = source.split("def _beverage_first_confidence_variant", 1)[1].split(
        "def _configured_beverage_first_confidence_variant", 1
    )[0]

    retired_priority_branches = [
        "_is_coffee_entry_profile(profile)",
        '"hard_boundary" in tags',
        '"operational_diagnostic" in tags',
        '{"transit", "payback"}.issubset(tags)',
        '"community" in tags',
        '"office" in tags',
        '"campus" in tags',
        '"tourism" in tags',
        '"competition" in tags',
        '"payback" in tags',
        '"transit" in tags',
    ]

    assert not any(branch in body for branch in retired_priority_branches)


def test_beverage_first_confidence_replies_do_not_keep_service_level_copy_blocks():
    source = Path(
        "intelligent_project_analyzer/services/scheme_advisor_entry_service.py"
    ).read_text(encoding="utf-8")

    retired_service_copy = [
        "这更像是一个小面积精品咖啡店的经营体验题",
        "这类茶饮小店先别急着排平面",
        "这不是在让你补一堆工程资料",
        "这更像是一个地铁连接口的小面积高周转饮品店",
        "这更像是社区复购型茶饮小店",
        "这更像是办公人群的高峰型茶饮小店",
        "这更像是学生价格敏感型茶饮小店",
        "这更像是游客快拍快买型茶饮店",
        "这更像是在强竞品旁边找差异的茶饮小店",
        "这更像是带明确回本压力的茶饮小店",
        "这更像是交通节点型茶饮小店",
        "这更像是一个需要先判断能不能做成的饮品小店",
    ]

    assert not any(copy in source for copy in retired_service_copy)


def test_seaview_founder_villa_uses_semantic_residence_entry_questions():
    result = SchemeAdvisorEntryService().handle_message(
        session={},
        user_message=SEAVIEW_FOUNDER_VILLA_PROMPT,
        in_response_to_card_id=None,
        selected_option_id=None,
    )

    assert result is not None
    assert result["intent"] == "scheme_advisor_entry"
    assert "\u8eab\u4efd" in result["reply"] or "\u521b\u59cb\u4eba" in result["reply"]
    assert "\u5bb6\u65cf" in result["reply"]
    assert "\u7b2c\u4e00\u4ee3\u521b\u4e1a\u8005\u7684" not in result["reply"]
    assert "\u4ece\u8349\u6839\u594b\u6597\u5230\u8d44\u672c\u6210\u529f\u4e4b\u540e" not in result["reply"]
    assert "\u5c0f\u9762\u79ef\u9ad8\u5468\u8f6c" not in result["reply"]

    profile = result["scheme_entry_state"]["profile"]
    assert profile["classification"]["project_type"] == "personal_residential"

    card = result["guidance_card"]
    visible_text_parts = [result["reply"], card.get("title", ""), card.get("prompt_text", "")]
    for page in card["pages"]:
        visible_text_parts.extend([
            page.get("page_title", ""),
            page.get("prompt_text", ""),
            page.get("helper_text", ""),
        ])
        for option in page.get("options", []):
            visible_text_parts.extend([
                option.get("label", ""),
                option.get("description", ""),
            ])
    visible_text = "\n".join(visible_text_parts)

    assert "\u521b\u59cb\u4eba/\u4e1a\u4e3b\u7cbe\u795e\u753b\u50cf" in visible_text or "\u8eab\u4efd\u4e0e\u7cbe\u795e\u8868\u8fbe" in visible_text
    assert "\u666f\u89c2\u8d44\u6e90" in visible_text or "\u6d77\u666f" in visible_text
    assert "\u5bb6\u65cf" in visible_text
    assert "\u57ce\u5e02\u66f4\u65b0" not in visible_text
    assert "\u5386\u53f2\u5efa\u7b51" not in visible_text
    assert "\u9009\u62e9\u5224\u65ad\u8def\u5f84" not in visible_text
    assert "\u6210\u7acb\u8def\u5f84" not in visible_text
    assert "\u786c\u7ea6\u675f" not in visible_text
    assert "\u53d6\u820d\u8fb9\u754c" not in visible_text
    assert "household structure" not in visible_text
    assert "privacy boundary" not in visible_text
    assert "individual privacy" not in visible_text


def test_private_residence_with_crisis_room_enters_flow_as_residence_not_enterprise():
    result = SchemeAdvisorEntryService().handle_message(
        session={},
        user_message=PRIVATE_RESIDENCE_CRISIS_ROOM_PROMPT,
        in_response_to_card_id=None,
        selected_option_id=None,
    )

    assert result is not None
    assert result["intent"] == "scheme_advisor_entry"

    profile = result["scheme_entry_state"]["profile"]
    assert profile["classification"]["project_type"] == "personal_residential"

    visible_text = result["reply"]
    assert "\u4f01\u4e1a\u7a7a\u95f4" not in visible_text
    assert "\u54c1\u724c\u5c55\u5385" not in visible_text
    assert "\u5c45\u4f4f" in visible_text or "\u4f4f\u5b85" in visible_text


def test_private_residence_entry_does_not_turn_lifestyle_flow_into_operational_efficiency():
    result = SchemeAdvisorEntryService().handle_message(
        session={},
        user_message=INDEPENDENT_WOMAN_RESIDENCE_PROMPT,
        in_response_to_card_id=None,
        selected_option_id=None,
    )

    assert result is not None
    profile = result["scheme_entry_state"]["profile"]
    assert profile["classification"]["project_type"] == "personal_residential"

    card = result["guidance_card"]
    visible_text_parts = [result["reply"], card.get("title", ""), card.get("prompt_text", "")]
    for page in card["pages"]:
        visible_text_parts.extend([
            page.get("page_title", ""),
            page.get("prompt_text", ""),
            page.get("helper_text", ""),
        ])
        for option in page.get("options", []):
            visible_text_parts.extend([
                option.get("label", ""),
                option.get("description", ""),
            ])
    visible_text = "\n".join(visible_text_parts)

    assert "\u8fd0\u8425\u6548\u7387" not in visible_text
    assert "\u5973\u6027" in visible_text
    assert "\u72ec\u7acb" in visible_text or "\u793e\u4ea4\u4e0e\u72ec\u5904" in visible_text


def test_second_confidence_for_commercial_transit_shop_keeps_business_pressure_visible():
    service = SchemeAdvisorEntryService()
    first = service.handle_message(
        session={},
        user_message=COMMERCIAL_TRANSIT_RETAIL_PROMPT,
        in_response_to_card_id=None,
        selected_option_id=None,
    )
    second = service.handle_message(
        session={
            "scheme_advisor_entry_v2": first["scheme_entry_state"],
            "pending_guidance_card": first["guidance_card"],
        },
        user_message="\u5148\u4fdd\u56de\u672c\u548c\u5ba2\u6d41\u8f6c\u5316\uff0c\u4e0d\u63a5\u53d7\u52a8\u7ebf\u62d6\u6162\u9ad8\u5cf0\u671f\u3002",
        in_response_to_card_id=first["guidance_card"]["card_id"],
        selected_option_id=None,
    )
    reply = second["reply"]

    assert any(term in reply for term in ["\u56de\u672c", "\u56de\u6536\u6295\u8d44"])
    assert any(term in reply for term in ["\u5ba2\u6d41", "\u4eba\u6d41", "\u5730\u94c1", "\u4ea4\u901a"])
    assert any(term in reply for term in ["\u52a8\u7ebf", "\u5468\u8f6c", "\u8fd0\u8425", "\u8f6c\u5316"])
    assert "\u9879\u76ee\u77e5\u8bc6\u5e93" not in reply
    assert "\u7a7a\u95f4\u5206\u7c7b" not in reply
    assert "\u672c\u4f53" not in reply


def test_stage_conclusion_for_commercial_transit_shop_summarizes_real_decision_axes():
    service = SchemeAdvisorEntryService()
    first = service.handle_message(
        session={},
        user_message=COMMERCIAL_TRANSIT_RETAIL_PROMPT,
        in_response_to_card_id=None,
        selected_option_id=None,
    )
    second = service.handle_message(
        session={
            "scheme_advisor_entry_v2": first["scheme_entry_state"],
            "pending_guidance_card": first["guidance_card"],
        },
        user_message="\u5148\u4fdd\u56de\u672c\u548c\u5ba2\u6d41\u8f6c\u5316\uff0c\u4e0d\u63a5\u53d7\u52a8\u7ebf\u62d6\u6162\u9ad8\u5cf0\u671f\u3002",
        in_response_to_card_id=first["guidance_card"]["card_id"],
        selected_option_id=None,
    )
    conclusion = service.handle_message(
        session={
            "scheme_advisor_entry_v2": second["scheme_entry_state"],
            "pending_guidance_card": second["guidance_card"],
        },
        user_message="\u4f18\u5148\u505a\u4f4e\u6295\u5165\u65b9\u6848\uff0c\u4f46\u4e0d\u80fd\u727a\u7272\u9ad8\u5cf0\u671f\u51fa\u8d27\u6548\u7387\u3002",
        in_response_to_card_id=second["guidance_card"]["card_id"],
        selected_option_id=None,
    )
    reply = conclusion["reply"]

    assert any(term in reply for term in ["\u56de\u672c", "\u56de\u6536\u6295\u8d44"])
    assert any(term in reply for term in ["\u5ba2\u6d41", "\u4eba\u6d41", "\u5730\u94c1", "\u4ea4\u901a"])
    assert any(term in reply for term in ["\u52a8\u7ebf", "\u5468\u8f6c", "\u8fd0\u8425", "\u8f6c\u5316"])
    assert "\u7a7a\u95f4\u5206\u7c7b" not in reply
    assert "\u672c\u4f53" not in reply
    assert "\u77e5\u8bc6\u5e93" not in reply
