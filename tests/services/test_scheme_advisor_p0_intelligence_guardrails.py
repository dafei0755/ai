from pathlib import Path

from intelligent_project_analyzer.services.scheme_advisor_context_intelligence import (
    SchemeAdvisorContextIntelligence,
)
from intelligent_project_analyzer.services.scheme_advisor_semantic_axes import (
    evaluate_semantic_alignment,
)
from intelligent_project_analyzer.services.scheme_advisor_entry_service import (
    SchemeAdvisorEntryService,
)


FOUNDER_SEASIDE_VILLA = (
    "项目位于深圳湾一线海景别墅区，业主为第一代创业者，"
    "从草根奋斗至资本成功，对空间的期待既包含成就象征，"
    "也包含家族传承与内心回归。请从一代创业者的精神结构出发，"
    "提出完整室内设计概念，包括空间气场构建、公共与私密区域权力关系、"
    "海景资源利用方式、材质象征系统以及如何避免过度炫耀。"
)


FOUNDER_LAKE_VILLA = (
    "\u676d\u5dde\u6e56\u666f\u522b\u5885\uff0c\u4e1a\u4e3b\u4e3a\u7b2c\u4e00\u4ee3\u521b\u4e1a\u8005\uff0c"
    "\u4ece\u8349\u6839\u594b\u6597\u5230\u4e8b\u4e1a\u6210\u529f\uff0c"
    "\u5e0c\u671b\u7a7a\u95f4\u540c\u65f6\u627f\u8f7d\u5bb6\u65cf\u4f20\u627f\u3001\u6210\u5c31\u6c89\u6dc0\u4e0e\u5185\u5fc3\u56de\u5f52\u3002"
    "\u8bf7\u63d0\u51fa\u5b8c\u6574\u5ba4\u5185\u8bbe\u8ba1\u6982\u5ff5\uff0c\u5305\u62ec\u516c\u5171\u4e0e\u79c1\u5bc6\u5173\u7cfb\u3001"
    "\u6e56\u666f\u8d44\u6e90\u5229\u7528\u3001\u6750\u6599\u7cbe\u795e\u8868\u8fbe\u4e0e\u514b\u5236\u8fb9\u754c\u3002"
)


PUBLIC_MARKET_RENEWAL = (
    "深圳蛇口20000㎡菜市场更新改造项目，希望对标苏州黄桥菜市场，"
    "同时融入蛇口渔村传统文化。需兼顾老居民、香港访客、外籍客群与社区居民，"
    "成为城市更新标杆。请提出整体改造框架，包括动线组织、冷链系统、"
    "文化展示策略、社交空间植入与商业可持续模型。"
)


def _visible_text(packet: dict) -> str:
    parts = []
    question_plan = packet.get("question_plan") or {}
    for card_key in ("round_1_card", "round_2_card"):
        card = question_plan.get(card_key) or {}
        parts.extend([
            str(card.get("title") or ""),
            str(card.get("prompt_text") or ""),
        ])
        for page in card.get("pages") or []:
            parts.extend([
                str(page.get("page_title") or ""),
                str(page.get("prompt_text") or ""),
                str(page.get("helper_text") or ""),
            ])
            for option in page.get("options") or []:
                parts.extend([
                    str(option.get("label") or ""),
                    str(option.get("description") or ""),
                ])
    return "\n".join(parts)


def _all_question_pages(packet: dict) -> list[dict]:
    question_plan = packet.get("question_plan") or {}
    pages = []
    for card_key in ("round_1_card", "round_2_card"):
        card = question_plan.get(card_key) or {}
        pages.extend(card.get("pages") or [])
    return pages


def test_founder_seaside_villa_prioritizes_identity_and_family_not_urban_renewal():
    packet = SchemeAdvisorContextIntelligence().build(FOUNDER_SEASIDE_VILLA)
    visible = _visible_text(packet)

    assert "创业" in visible or "第一代" in visible
    assert "家族" in visible or "传承" in visible
    assert "城市更新" not in visible
    assert "历史建筑" not in visible

    issues = evaluate_semantic_alignment(FOUNDER_SEASIDE_VILLA, visible)
    assert "wrong_domain_reference" not in {issue["code"] for issue in issues}


def test_round_two_questions_are_natural_and_core_tension_driven():
    service = SchemeAdvisorContextIntelligence()
    commercial_prompt = (
        "深圳市南山区来福士广场，负一楼，30平米商铺，地铁通道与商场的连接处，"
        "打算做一个奶茶店，希望半年能收回成本，我需要一份完整的设计建议。"
    )

    founder_round_2 = (service.build(FOUNDER_SEASIDE_VILLA).get("question_plan") or {}).get("round_2_card") or {}
    commercial_round_2 = (service.build(commercial_prompt).get("question_plan") or {}).get("round_2_card") or {}
    founder_text = _visible_text({"question_plan": {"round_2_card": founder_round_2}})
    commercial_text = _visible_text({"question_plan": {"round_2_card": commercial_round_2}})

    for visible in (founder_text, commercial_text):
        assert "优先级" not in visible
        assert "最先保什么" not in visible
        assert "成立路径" not in visible
        assert "硬约束" not in visible
        assert "取舍边界" not in visible

    assert any(term in founder_text for term in ["创业", "草根", "家族", "内心", "成就"])
    assert any(term in founder_text for term in ["这个家", "主人", "业主"])
    assert any(term in commercial_text for term in ["半年回本", "回本", "客流", "出杯", "高峰"])
    assert any(term in commercial_text for term in ["这家店", "奶茶店", "小店"])


def test_round_one_card_header_names_current_project_core_tension():
    service = SchemeAdvisorContextIntelligence()
    commercial_prompt = (
        "深圳市南山区来福士广场，负一楼，30平米商铺，地铁通道与商场的连接处，"
        "打算做一个奶茶店，希望半年能收回成本，我需要一份完整的设计建议。"
    )

    founder_round_1 = (service.build(FOUNDER_SEASIDE_VILLA).get("question_plan") or {}).get("round_1_card") or {}
    commercial_round_1 = (service.build(commercial_prompt).get("question_plan") or {}).get("round_1_card") or {}
    founder_header = "\n".join([
        str(founder_round_1.get("title") or ""),
        str(founder_round_1.get("prompt_text") or ""),
    ])
    commercial_header = "\n".join([
        str(commercial_round_1.get("title") or ""),
        str(commercial_round_1.get("prompt_text") or ""),
    ])

    assert "空间真正要表达什么" not in founder_header
    assert any(term in founder_header for term in ["这个家", "主人", "业主"])
    assert any(term in founder_header for term in ["创业", "草根", "家族", "内心", "成就"])

    assert "生意是否成立" not in commercial_header
    assert any(term in commercial_header for term in ["这家店", "奶茶店", "小店"])
    assert any(term in commercial_header for term in ["半年回本", "客流", "出杯", "投入"])


def test_founder_seaside_villa_question_plan_uses_semantic_axes_not_case_template():
    packet = SchemeAdvisorContextIntelligence().build(FOUNDER_SEASIDE_VILLA)
    sources = set((packet.get("intelligence_trace") or {}).get("question_plan_sources") or [])
    question_plan = packet.get("question_plan") or {}

    assert "semantic_axes_entry" in sources
    assert "private_founder_residential_entry" not in sources
    assert (question_plan.get("round_1_card") or {}).get("source") == "semantic_axes_entry"


def test_services_do_not_keep_private_founder_case_template():
    service_paths = [
        Path("intelligent_project_analyzer/services/scheme_advisor_context_intelligence.py"),
        Path("intelligent_project_analyzer/services/scheme_advisor_entry_service.py"),
    ]
    source = "\n".join(path.read_text(encoding="utf-8") for path in service_paths)

    forbidden = [
        "private_founder_residential_entry",
        "_private_founder_residence_question_plan",
        "_build_private_founder_residence_first_confidence",
        "_is_private_founder_residence_profile",
        "深圳湾一线海景应该怎么被使用",
        "从草根奋斗到资本成功之后",
    ]
    assert not any(term in source for term in forbidden)


def test_fresh_project_restart_uses_general_project_anchors_not_old_sample_terms():
    service = SchemeAdvisorEntryService()
    prompt = (
        "杭州湖滨商场二楼42平方米咖啡店，需要设计任务书，"
        "目标是小面积快周转，同时保留少量等候和取餐空间。"
    )

    assert service._is_fresh_project_restart(prompt) is True


def test_fresh_project_restart_does_not_keep_old_milk_tea_sample_density_terms():
    source = Path(
        "intelligent_project_analyzer/services/scheme_advisor_entry_service.py"
    ).read_text(encoding="utf-8")
    start = source.index("def _is_fresh_project_restart")
    end = source.index("def _classify_input", start)
    restart_source = source[start:end]

    forbidden = ['"35"', '"深圳"', '"地铁"', '"茶"']
    assert not any(term in restart_source for term in forbidden)


def test_general_method_question_uses_problem_mode_registry_terms():
    service = SchemeAdvisorEntryService()
    prompt = "设计顾问如何建立一套从访谈到判断的实践框架？"

    assert service._is_general_method_question(prompt) is True


def test_general_method_question_does_not_keep_private_keyword_regex():
    source = Path(
        "intelligent_project_analyzer/services/scheme_advisor_entry_service.py"
    ).read_text(encoding="utf-8")
    start = source.index("def _is_general_method_question")
    end = source.index("def _recommend_version", start)
    method_source = source[start:end]

    forbidden = ["马斯克|方法论|启发|哲学|思维方式"]
    assert not any(term in method_source for term in forbidden)


def test_should_enter_flow_uses_semantic_axis_registry_not_private_project_terms():
    service = SchemeAdvisorEntryService()
    prompt = "一座图书馆需要面向儿童和居民形成公众学习路径，请给出完整框架。"

    assert service._should_enter_flow(prompt) is True


def test_should_enter_flow_does_not_keep_private_project_terms_table():
    source = Path(
        "intelligent_project_analyzer/services/scheme_advisor_entry_service.py"
    ).read_text(encoding="utf-8")
    start = source.index("def _should_enter_flow")
    end = source.index("def _is_fresh_project_restart", start)
    flow_source = source[start:end]

    assert "project_terms = [" not in flow_source


def test_entry_service_does_not_duplicate_semantic_axis_id_sets():
    source = Path(
        "intelligent_project_analyzer/services/scheme_advisor_entry_service.py"
    ).read_text(encoding="utf-8")

    forbidden = [
        "methodology_modes =",
        "actionable_intents =",
        "project_intents =",
        '{"methodology_discussion", "analogy_translation", "value_argument"}',
    ]
    assert not any(term in source for term in forbidden)


def test_entry_service_uses_shared_semantic_axis_density_helper():
    source = Path(
        "intelligent_project_analyzer/services/scheme_advisor_entry_service.py"
    ).read_text(encoding="utf-8")
    restart_start = source.index("def _is_fresh_project_restart")
    classify_start = source.index("def _classify_input", restart_start)
    restart_source = source[restart_start:classify_start]
    anchor_start = source.index("def _has_concrete_project_anchor")
    methodology_start = source.index("def _methodology_profile", anchor_start)
    anchor_source = source[anchor_start:methodology_start]

    assert "for axis_name in (" not in restart_source
    assert "for axis_name in (" not in anchor_source
    assert "semantic_axis_density(" in restart_source
    assert "semantic_axis_density(" in anchor_source


def test_semantic_axis_inference_rules_are_registry_driven():
    from intelligent_project_analyzer.services.scheme_advisor_semantic_axes import (
        derive_semantic_axes,
    )

    registry = {
        "axes": {
            "space_domains": {},
            "subject_profiles": {},
            "founding_drivers": {},
            "site_resources": {},
            "input_intents": {},
            "problem_modes": {},
        },
        "inference_rules": [
            {
                "id": "custom_cooccurrence_rule",
                "when": {
                    "all": [
                        {"any_terms": ["甲信号"]},
                        {"any": [{"any_terms": ["乙信号"]}, {"any_terms": ["丙信号"]}]},
                    ]
                },
                "append_axes": [
                    {"axis": "space_domains", "id": "custom_domain"},
                    {"axis": "founding_drivers", "id": "custom_driver"},
                ],
            }
        ],
    }

    axes = derive_semantic_axes("这里有甲信号和乙信号", registry=registry)

    assert axes["space_domains"] == ["custom_domain"]
    assert axes["founding_drivers"] == ["custom_driver"]


def test_semantic_axis_module_does_not_keep_business_term_inference_tables():
    source = Path(
        "intelligent_project_analyzer/services/scheme_advisor_semantic_axes.py"
    ).read_text(encoding="utf-8")
    forbidden = [
        "白手起家",
        "小工厂",
        "回收投资",
        "认知空间",
        "参观路线",
    ]

    assert not any(term in source for term in forbidden)


def test_residential_prompt_without_founder_seaside_combo_does_not_use_founder_case_plan():
    prompt = (
        "一位极简主义艺术收藏家希望住宅成为“白盒子画廊”，但仍需日常居住功能。"
        "请提出完整设计概念，包括可隐藏生活系统、展览级灯光控制与艺术安全保护机制。"
    )

    packet = SchemeAdvisorContextIntelligence().build(prompt)
    visible = _visible_text(packet)
    sources = set((packet.get("intelligence_trace") or {}).get("question_plan_sources") or [])

    assert "private_founder_residential_entry" not in sources
    assert "第一代创业者" not in visible
    assert "深圳湾一线海景" not in visible


def test_founder_lake_villa_uses_semantic_axes_not_shenzhen_seaview_template():
    packet = SchemeAdvisorContextIntelligence().build(FOUNDER_LAKE_VILLA)
    visible = _visible_text(packet)
    sources = set((packet.get("intelligence_trace") or {}).get("question_plan_sources") or [])

    assert "private_founder_residential_entry" not in sources
    assert "\u6df1\u5733\u6e7e" not in visible
    assert "\u4e00\u7ebf\u6d77\u666f" not in visible
    assert "\u6d77\u666f\u4e0e\u6838\u5fc3\u7a7a\u95f4" not in visible
    assert "\u521b\u4e1a" in visible or "\u5bb6\u65cf" in visible or "\u6210\u5c31" in visible


def test_bootstrapped_founder_residence_uses_identity_legacy_axis_without_case_words():
    from intelligent_project_analyzer.services.scheme_advisor_semantic_axes import (
        derive_semantic_axes,
        rank_main_tensions,
    )

    prompt = (
        "宁波湖畔私宅，业主是白手起家的制造业创始人，"
        "从小工厂一路打拼到行业龙头，希望这个家承载事业沉淀、"
        "家族传承和内心安定。请提出完整室内设计概念，"
        "包括待客与家人生活的分层、景观资源利用、材质气质和克制边界。"
    )

    packet = SchemeAdvisorContextIntelligence().build(prompt)
    visible = _visible_text(packet)
    axes = derive_semantic_axes(prompt)
    tensions = rank_main_tensions(prompt)
    tension_ids = [item["id"] for item in tensions[:4]]

    assert "founder_owner" in axes["subject_profiles"]
    assert "identity_expression" in axes["founding_drivers"]
    assert "family_legacy" in axes["founding_drivers"]
    assert "identity_expression" in tension_ids
    assert "family_legacy" in tension_ids
    assert "城市更新" not in visible
    assert "历史建筑" not in visible
    assert "深圳湾" not in visible
    assert "一线海景" not in visible
    assert "白手起家" in visible or "创始人" in visible or "家族" in visible or "事业" in visible


def test_entry_guidance_does_not_expose_internal_english_keys():
    packet = SchemeAdvisorContextIntelligence().build(FOUNDER_SEASIDE_VILLA)
    visible = _visible_text(packet)

    forbidden = [
        "preservation grade",
        "structural condition",
        "heritage value",
        "context_packet",
        "missing_slot",
        "activation_pack",
    ]
    assert not any(item in visible for item in forbidden)


def test_public_market_renewal_questions_are_business_terms_not_internal_keys():
    packet = SchemeAdvisorContextIntelligence().build(PUBLIC_MARKET_RENEWAL)
    visible = _visible_text(packet)

    forbidden = [
        "market role",
        "vendor and customer flow",
        "sanitation and logistics",
        "neighborhood public value",
        "long term operation",
        "sanitation and drainage",
        "fire safety precheck",
        "logistics separation",
        "maintenance cost",
        "livelihood practicality",
        "place branding",
        "vendor efficiency",
        "public experience",
        "renovation activation",
        "daily affordability",
        "选择判断路径",
    ]

    assert not any(term in visible for term in forbidden)
    assert "先确认这个市场更新最不能牺牲什么" in visible
    assert "摊贩" in visible
    assert "居民" in visible or "社区" in visible
    assert "游客" in visible or "访客" in visible
    assert "卫生" in visible or "排水" in visible or "冷链" in visible


def test_public_market_renewal_question_pages_express_selection_semantics():
    packet = SchemeAdvisorContextIntelligence().build(PUBLIC_MARKET_RENEWAL)
    pages = ((packet.get("question_plan") or {}).get("round_1_card") or {}).get("pages") or []
    option_labels = [
        option.get("label", "")
        for page in pages
        for option in (page.get("options") or [])
    ]

    assert pages
    assert any("公共市场" in (page.get("page_title") or "") or "市场" in (page.get("page_title") or "") for page in pages)
    assert all(page.get("response_mode") for page in pages)
    assert any(page.get("response_mode") in {"multi_select", "priority_pick"} for page in pages)
    assert any(int(page.get("max_select") or 0) >= 2 for page in pages)
    assert any("摊贩" in label or "商户" in label for label in option_labels)
    assert any("居民" in label for label in option_labels)
    assert any("访客" in label or "游客" in label for label in option_labels)


def test_public_market_round_one_directly_responds_to_user_prompt_anchors():
    packet = SchemeAdvisorContextIntelligence().build(PUBLIC_MARKET_RENEWAL)
    round_1 = ((packet.get("question_plan") or {}).get("round_1_card") or {})
    header = "\n".join([
        str(round_1.get("title") or ""),
        str(round_1.get("prompt_text") or ""),
    ])

    assert "苏州黄桥菜市场" in header
    assert "蛇口渔村传统文化" in header or "蛇口渔村" in header
    assert "老居民" in header
    assert "香港访客" in header
    assert "外籍客群" in header
    assert "城市更新标杆" in header
    assert "可对标" in header or "对标" in header
    assert "不能照搬" in header or "误区" in header or "不一样" in header


def test_round_one_lists_explicit_prompt_anchors_before_questioning():
    packet = SchemeAdvisorContextIntelligence().build(PUBLIC_MARKET_RENEWAL)
    round_1 = ((packet.get("question_plan") or {}).get("round_1_card") or {})
    prompt = str(round_1.get("prompt_text") or "")

    for index in range(1, 7):
        assert f"{index}." in prompt

    assert "项目对象" in prompt and "深圳蛇口20000㎡菜市场更新改造" in prompt
    assert "对标对象" in prompt and "苏州黄桥菜市场" in prompt
    assert "在地文化" in prompt and "蛇口渔村传统文化" in prompt
    assert "服务对象" in prompt and "老居民、香港访客、外籍客群与社区居民" in prompt
    assert "目标动机" in prompt and "城市更新标杆" in prompt
    assert "任务范围" in prompt and "动线组织、冷链系统、文化展示策略、社交空间植入与商业可持续模型" in prompt
    assert "备注" not in prompt


def test_round_one_caps_visible_anchors_at_six_and_notes_formal_work():
    prompt = (
        PUBLIC_MARKET_RENEWAL
        + "另需统筹消防验收、夜间运营、租户分级、数字化导览与分期施工计划。"
    )

    packet = SchemeAdvisorContextIntelligence().build(prompt)
    round_1 = ((packet.get("question_plan") or {}).get("round_1_card") or {})
    prompt_text = str(round_1.get("prompt_text") or "")

    assert "6." in prompt_text
    assert "7." not in prompt_text
    assert "备注" in prompt_text
    assert "正式任务中展开" in prompt_text
    assert "夜间运营" in prompt_text or "租户分级" in prompt_text or "数字化导览" in prompt_text


def test_round_two_targets_hidden_tradeoffs_not_surface_prompt_repetition():
    packet = SchemeAdvisorContextIntelligence().build(PUBLIC_MARKET_RENEWAL)
    round_2 = ((packet.get("question_plan") or {}).get("round_2_card") or {})
    text = "\n".join([
        str(round_2.get("title") or ""),
        str(round_2.get("prompt_text") or ""),
        *[
            "\n".join([
                str(page.get("page_title") or ""),
                str(page.get("prompt_text") or ""),
                str(page.get("helper_text") or ""),
            ])
            for page in (round_2.get("pages") or [])
        ],
    ])

    assert "背后" in text or "隐含" in text
    assert "取舍" in text or "撕裂" in text or "冲突" in text
    assert "谁付运营成本" in text or "价格感" in text or "后勤" in text
    assert "苏州黄桥菜市场" not in text
    assert "动线组织、冷链系统、文化展示策略、社交空间植入与商业可持续模型" not in text


def test_public_market_first_confidence_names_benchmark_culture_and_motive():
    reply = SchemeAdvisorEntryService._build_semantic_first_confidence(
        {"space_label": "菜市场更新"},
        PUBLIC_MARKET_RENEWAL,
    )

    assert "苏州黄桥菜市场" in reply
    assert "深圳" in reply
    assert "蛇口渔村传统文化" in reply or "蛇口渔村" in reply
    assert "老居民" in reply
    assert "香港访客" in reply
    assert "外籍客群" in reply
    assert "社区居民" in reply
    assert "城市更新标杆" in reply
    assert "不能照搬" in reply or "误区" in reply or "不一样" in reply


def test_question_titles_are_dynamic_not_fixed_workflow_words():
    packet = SchemeAdvisorContextIntelligence().build(FOUNDER_SEASIDE_VILLA)
    visible = _visible_text(packet)

    fixed_titles = ["成立路径", "硬约束", "取舍边界", "选择判断路径"]
    assert not any(title in visible for title in fixed_titles)


def test_public_label_translates_known_keys_without_leaking_raw_key():
    from intelligent_project_analyzer.services.scheme_advisor_context_intelligence import (
        public_label,
    )

    assert public_label("fire_egress_clearance") == "消防疏散净距"
    assert public_label("structural_condition") == "结构现状"
    assert public_label("unknown_internal_key") == "待确认项"


def test_entry_service_user_visible_labels_are_registry_driven():
    source = Path(
        "intelligent_project_analyzer/services/scheme_advisor_entry_service.py"
    ).read_text(encoding="utf-8")

    forbidden_local_maps = [
        "def _humanize(value: str):\n        labels = {",
        "def _humanize_knowledge_module_title(title: str) -> str:\n        labels = {",
    ]

    assert not any(fragment in source for fragment in forbidden_local_maps)


def test_terminal_user_copy_configs_do_not_keep_fixed_workflow_terms():
    config_paths = [
        Path("intelligent_project_analyzer/config/scheme_advisor_intelligence.yaml"),
        Path("intelligent_project_analyzer/config/scheme_advisor_entry_copy.yaml"),
        Path("intelligent_project_analyzer/config/scheme_advisor_version_tiers.yaml"),
    ]
    forbidden_terms = ["选择判断路径", "成立路径", "硬约束", "取舍边界", "风险阈值", "预算押注", "决策级变量"]

    for path in config_paths:
        text = path.read_text(encoding="utf-8")
        for term in forbidden_terms:
            assert term not in text, f"{path} exposes fixed workflow term: {term}"


def test_rank_main_tensions_prefers_founder_identity_and_family_for_villa():
    from intelligent_project_analyzer.services.scheme_advisor_semantic_axes import (
        rank_main_tensions,
    )

    tensions = rank_main_tensions(FOUNDER_SEASIDE_VILLA)
    ids = [item["id"] for item in tensions[:3]]

    assert "identity_expression" in ids
    assert "family_legacy" in ids
    assert "urban_renewal" not in ids


def test_entry_question_pages_use_ranked_tension_titles():
    packet = SchemeAdvisorContextIntelligence().build(FOUNDER_SEASIDE_VILLA)
    visible = _visible_text(packet)

    assert "先确认空间真正要表达什么" in visible or "先确认家人和来客的关系" in visible
    assert "城市更新/历史建筑活化最先要证明哪几件事成立" not in visible


def test_round_two_question_title_is_semantic_axis_specific_not_generic_priority():
    commercial_prompt = (
        "地铁换乘通道旁有一间18平米小铺，租金很高，但每天人流量很大，"
        "想做一个低投入、快周转的零售项目，希望6个月回收投资。"
        "请帮我判断空间设计和经营动线应该先抓哪些关键点。"
    )
    founder_packet = SchemeAdvisorContextIntelligence().build(FOUNDER_SEASIDE_VILLA)
    commercial_packet = SchemeAdvisorContextIntelligence().build(commercial_prompt)

    founder_round_2 = (founder_packet.get("question_plan") or {}).get("round_2_card") or {}
    commercial_round_2 = (commercial_packet.get("question_plan") or {}).get("round_2_card") or {}

    founder_text = _visible_text({"question_plan": {"round_2_card": founder_round_2}})
    commercial_text = _visible_text({"question_plan": {"round_2_card": commercial_round_2}})

    assert founder_round_2.get("title") != "再确认最不能跑偏的一件事"
    assert commercial_round_2.get("title") != "再确认最不能跑偏的一件事"
    assert founder_text != commercial_text
    assert any(term in founder_text for term in ["身份", "家族", "主人", "成就"])
    assert any(term in commercial_text for term in ["商业", "回报", "回本", "客流", "运营"])


def test_entry_question_options_do_not_treat_request_intents_as_decision_choices():
    packet = SchemeAdvisorContextIntelligence().build(FOUNDER_SEASIDE_VILLA)
    pages = (packet.get("question_plan") or {}).get("round_1_card", {}).get("pages") or []
    labels = [
        str(option.get("label") or "")
        for page in pages
        for option in (page.get("options") or [])
    ]

    assert "完整设计框架" not in labels
    assert "技术落地方案" not in labels
    assert any(
        label in labels
        for label in ["身份与精神表达", "家族传承", "创始人/业主精神画像", "景观资源", "安防与隐私"]
    )


def test_single_domain_residence_options_prioritize_real_boundaries_over_type_label():
    packet = SchemeAdvisorContextIntelligence().build(FOUNDER_SEASIDE_VILLA)
    pages = (packet.get("question_plan") or {}).get("round_1_card", {}).get("pages") or []
    labels = [
        str(option.get("label") or "")
        for page in pages
        for option in (page.get("options") or [])
    ]

    assert "居住生活" not in labels
    assert "安防与隐私" in labels
    assert "景观资源" in labels


def test_non_special_residential_question_pages_follow_memory_object_tension():
    prompt = (
        "客户希望新家融入大量旧货市场淘来的老家具与旧物件，年代风格各异。"
        "请提出完整设计策略，包括风格整合逻辑、视觉焦点建立、"
        "材质过渡机制与叙事路径构建。"
    )

    packet = SchemeAdvisorContextIntelligence().build(prompt)
    pages = (packet.get("question_plan") or {}).get("round_1_card", {}).get("pages") or []
    page_titles = [page.get("page_title") for page in pages]
    visible = _visible_text(packet)

    assert "旧物" in visible
    assert "生活记忆" in visible or "记忆" in visible
    assert "项目主轴" not in page_titles
    assert "使用者与关系" not in page_titles
    assert "现实边界" not in page_titles


def test_non_tea_business_question_pages_follow_roi_and_operation_tensions():
    prompt = (
        "一处城市核心区精品酒店改造，租金压力很大，希望通过设计提高入住率，"
        "并在半年内看到投资回报。请提出完整设计建议。"
    )

    packet = SchemeAdvisorContextIntelligence().build(prompt)
    pages = (packet.get("question_plan") or {}).get("round_1_card", {}).get("pages") or []
    page_titles = [page.get("page_title") for page in pages]
    visible = _visible_text(packet)

    assert "生意是否成立" in visible or "回本" in visible or "投资回报" in visible
    assert "项目主轴" not in page_titles
    assert "使用者与关系" not in page_titles
    assert "现实边界" not in page_titles


def test_small_transit_shop_infers_commercial_roi_without_named_subdomain():
    from intelligent_project_analyzer.services.scheme_advisor_pressure_runner import analyze_prompt
    from intelligent_project_analyzer.services.scheme_advisor_semantic_axes import (
        derive_semantic_axes,
        rank_main_tensions,
    )

    prompt = (
        "地铁换乘通道旁有一间18平米小铺，租金很高，但每天人流量很大，"
        "想做一个低投入、快周转的零售项目，希望6个月回收投资。"
        "请帮我判断空间设计和经营动线应该先抓哪些关键点。"
    )

    axes = derive_semantic_axes(prompt)
    tensions = rank_main_tensions(prompt)
    tension_ids = [item["id"] for item in tensions[:4]]
    packet = SchemeAdvisorContextIntelligence().build(prompt)
    visible = _visible_text(packet)
    result = analyze_prompt(prompt, question_id=9901)

    assert "retail_commercial" in axes["space_domains"]
    assert "business_roi" in axes["founding_drivers"]
    assert "operational_efficiency" in axes["founding_drivers"]
    assert "transit_node" in axes["site_resources"]
    assert "business_roi" in tension_ids
    assert result["space_axis_id"] in {"commercial_operation_roi", "retail_brand_conversion"}
    assert "回本" in visible or "客流" in visible or "人流" in visible
    assert "城市更新" not in visible
    assert "历史建筑" not in visible


def test_commercial_focus_pages_keep_enough_actionable_choices_when_one_axis_is_sparse():
    prompt = (
        "地铁换乘通道旁有一间18平米小铺，租金很高，但每天人流量很大，"
        "想做一个低投入、快周转的零售项目，希望6个月回收投资。"
        "请帮我判断空间设计和经营动线应该先抓哪些关键点。"
    )

    packet = SchemeAdvisorContextIntelligence().build(prompt)
    pages = (packet.get("question_plan") or {}).get("round_1_card", {}).get("pages") or []
    option_labels_by_page = [
        [str(option.get("label") or "") for option in (page.get("options") or [])]
        for page in pages
    ]

    assert all(len(labels) >= 3 for labels in option_labels_by_page)
    assert any("商业成立与回报" in labels for labels in option_labels_by_page)
    assert any("运营效率" in labels for labels in option_labels_by_page)
    assert any("交通节点" in labels for labels in option_labels_by_page)


def test_commercial_first_confidence_reply_uses_site_and_roi_axes_not_internal_directory_talk():
    prompt = (
        "地铁换乘通道旁有一间18平米小铺，租金很高，但每天人流量很大，"
        "想做一个低投入、快周转的零售项目，希望6个月回收投资。"
        "请帮我判断空间设计和经营动线应该先抓哪些关键点。"
    )

    result = SchemeAdvisorEntryService().handle_message(
        session={},
        user_message=prompt,
        in_response_to_card_id=None,
        selected_option_id=None,
    )
    reply = result["reply"]

    assert any(term in reply for term in ["回本", "回收投资", "半年"])
    assert any(term in reply for term in ["地铁", "人流", "客流", "交通节点"])
    assert any(term in reply for term in ["运营", "动线", "周转", "购买", "转化"])
    assert "方案目录" not in reply
    assert "后续追问顺序" not in reply
    assert "空间分类" not in reply


def test_public_learning_space_infers_visitor_education_axis_without_museum_terms():
    from intelligent_project_analyzer.services.scheme_advisor_pressure_runner import analyze_prompt
    from intelligent_project_analyzer.services.scheme_advisor_semantic_axes import (
        derive_semantic_axes,
        rank_main_tensions,
    )

    prompt = (
        "一座退役水泵站想改成面向市民和中小学生的水循环认知空间，"
        "包含互动实验、观察点、参观路线和社区活动。请提出完整设计框架，"
        "包括信息节奏、学习路径、公共安全和长期维护。"
    )

    axes = derive_semantic_axes(prompt)
    tensions = rank_main_tensions(prompt)
    tension_ids = [item["id"] for item in tensions[:5]]
    packet = SchemeAdvisorContextIntelligence().build(prompt)
    visible = _visible_text(packet)
    result = analyze_prompt(prompt, question_id=9902)

    assert "education_public" in axes["space_domains"]
    assert "public_users" in axes["subject_profiles"]
    assert "children" in axes["subject_profiles"]
    assert "public_users" in tension_ids or "children" in tension_ids
    assert result["space_axis_id"] == "public_learning_visitor_experience"
    assert "学习" in visible or "参观" in visible or "公众" in visible or "孩子" in visible
    assert "零售" not in visible
    assert "回本" not in visible


def test_generic_project_question_pages_use_space_axis_focus_not_template_fillers():
    prompt = (
        "\u4ee5\u4e39\u9ea6\u5bb6\u5c45\u54c1\u724cHAY\u7684\u5e74\u8f7b\u3001\u514b\u5236\u3001\u529f\u80fd\u4e3b\u4e49\u6c14\u8d28\u4e3a\u6838\u5fc3\uff0c"
        "\u4e3a\u56db\u5ddd\u5ce8\u7709\u5c71\u4e03\u91cc\u576a\u5c71\u5730\u6c11\u5bbf\u63d0\u4f9b\u5ba4\u5185\u8bbe\u8ba1\u6982\u5ff5\u3002"
        "\u9879\u76ee\u9700\u8981\u517c\u987e\u5c71\u5730\u81ea\u7136\u666f\u89c2\u3001\u8f7b\u5ea6\u5ea6\u5047\u4eba\u7fa4\u9700\u6c42\u4e0e\u54c1\u724c\u8fa8\u8bc6\u5ea6\u3002"
        "\u8bf7\u63d0\u51fa\u5b8c\u6574\u8bbe\u8ba1\u6846\u67b6\uff0c\u8bf4\u660e\u8272\u5f69\u7cfb\u7edf\u3001\u5bb6\u5177\u7b56\u7565\u3001\u7a7a\u95f4\u5c3a\u5ea6\u63a7\u5236\u4e0e\u516c\u5171\u793e\u4ea4\u7a7a\u95f4\u7684\u7ec4\u7ec7\u65b9\u5f0f\u3002"
    )

    packet = SchemeAdvisorContextIntelligence().build(prompt)
    pages = (packet.get("question_plan") or {}).get("round_1_card", {}).get("pages") or []
    page_titles = [page.get("page_title") for page in pages]
    visible = _visible_text(packet)

    assert "\u518d\u786e\u8ba4\u8c01\u6700\u5e94\u8be5\u88ab\u56de\u5e94" not in page_titles
    assert "\u518d\u786e\u8ba4\u54ea\u4e9b\u6761\u4ef6\u4e0d\u80fd\u542b\u7cca" not in page_titles
    assert any(
        "\u4f4f\u5ba2" in title
        or "\u8fd0\u8425" in title
        or "\u516c\u5171\u7a7a\u95f4" in title
        or "\u957f\u671f\u56de\u62a5" in title
        for title in page_titles
    )
    assert "\u5c71\u5730" in visible or "\u54c1\u724c" in visible or "\u5ea6\u5047" in visible


def test_first_confidence_reply_mentions_key_subject_profile_without_fixed_triad():
    prompt = (
        "项目为“中国书法大酒店”，位于安徽合肥，总建筑面积50000㎡，"
        "业主为安徽省书法家协会主席，越战老兵，企业家。"
        "项目需成为书法文化的精神地标。请提出完整室内设计概念系统。"
    )

    reply = SchemeAdvisorEntryService._build_semantic_first_confidence(
        {"space_label": "书法文化酒店"},
        prompt,
    )

    assert "业主" in reply or "关键人物" in reply or "主人" in reply
    assert "书法" in reply
    assert "项目主轴" not in reply
    assert "使用者关系" not in reply
    assert "现实边界" not in reply
    assert "先围绕先确认" not in reply


def test_first_confidence_for_founder_lake_villa_does_not_leak_case_specific_site():
    reply = SchemeAdvisorEntryService()._build_first_confidence_fallback(
        {
            "project_type": "personal_residential",
            "space_label": "\u6e56\u666f\u522b\u5885",
            "classification": {"project_type": "personal_residential"},
        },
        FOUNDER_LAKE_VILLA,
    )

    assert "\u6df1\u5733\u6e7e" not in reply
    assert "\u4e00\u7ebf\u6d77\u666f" not in reply
    assert "\u6d77\u666f\u5bb6\u5b85" not in reply
    assert "\u521b\u4e1a" in reply or "\u5bb6\u65cf" in reply or "\u6210\u5c31" in reply


def test_low_confidence_classification_creates_governance_candidate():
    from intelligent_project_analyzer.services.space_context_packet_service import (
        SpaceContextPacketService,
    )

    activation = {
        "space_classification": {
            "project_type": None,
            "project_type_name": None,
            "confidence": 0.22,
            "confidence_level": "low",
            "status": "low_confidence",
            "secondary_types": ["personal_residential", "commercial_hospitality"],
            "ambiguity": {"reason": "multi_domain_or_abstract_prompt"},
        },
        "project_definition_activation_pack": {"_v18_extensions": {}},
    }

    packet = SpaceContextPacketService().build_from_activation("复合空间设计", activation)
    candidate = packet["classification"]["ambiguity"].get("governance_candidate")

    assert candidate["requires_human_review"] is True
    assert candidate["candidate_type"] == "project_type_boundary"
    assert candidate["must_not_update_registry_automatically"] is True
    assert candidate["nearby_type_ids"] == ["personal_residential", "commercial_hospitality"]


def test_context_packet_exposes_space_axis_for_entry_questioning():
    prompt = (
        "\u9879\u76ee\u4f4d\u4e8e\u6df1\u5733\u6e7e\u4e00\u7ebf\u6d77\u666f\u522b\u5885\u533a"
        "\uff0c\u4e1a\u4e3b\u4e3a\u7b2c\u4e00\u4ee3\u521b\u4e1a\u8005"
        "\uff0c\u4ece\u8349\u6839\u594b\u6597\u81f3\u8d44\u672c\u6210\u529f"
        "\uff0c\u5bf9\u7a7a\u95f4\u7684\u671f\u5f85\u65e2\u5305\u542b\u6210\u5c31\u8c61\u5f81"
        "\uff0c\u4e5f\u5305\u542b\u5bb6\u65cf\u4f20\u627f\u4e0e\u5185\u5fc3\u56de\u5f52\u3002"
        "\u8bf7\u4ece\u4e00\u4ee3\u521b\u4e1a\u8005\u7684\u7cbe\u795e\u7ed3\u6784\u51fa\u53d1"
        "\uff0c\u63d0\u51fa\u5b8c\u6574\u5ba4\u5185\u8bbe\u8ba1\u6982\u5ff5\u3002"
    )

    packet = SchemeAdvisorContextIntelligence().build(prompt)

    assert packet["space_axis"]["primary_axis_id"] == "private_residential_identity_legacy"
    assert "身份" in packet["space_axis"]["primary_axis_label"]
    assert "家族" in packet["space_axis"]["decision_focus"][1]
    assert "urban_renewal_heritage" in packet["space_axis"]["must_not_route_to"]
