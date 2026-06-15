from intelligent_project_analyzer.services.space_classification_service import (
    SpaceClassificationService,
)


def classify(prompt: str) -> dict:
    return SpaceClassificationService().classify(prompt)


def test_rural_residential_object_outranks_profession_context():
    result = classify(
        "四川广元农村300㎡民居，业主70年代出生的室内设计师，希望“让游子心安回归”。"
        "请在中国乡村真实生活之间找到平衡，提出完整室内设计概念。"
    )

    assert result["project_type"] in {"personal_residential", "rural_construction"}
    assert result["project_type"] != "commercial_office"
    assert result["confidence"] >= 0.55


def test_dental_clinic_alias_preserves_healthcare_signal_and_confidence():
    result = classify(
        "为一家高端私立牙科诊所设计室内空间，核心目标是消除患者恐惧感。"
        "从业主（牙医）与患者双重视角出发，优化等待、问诊与治疗每个空间节点。"
    )

    assert result["project_type"] == "healthcare_wellness"
    assert result["confidence"] >= 0.55


def test_africa_medical_support_center_is_not_negated_or_retailed():
    result = classify(
        "某国际 NGO 计划在非洲设立医疗支援培训中心，预算有限但希望建立长期使用标准。"
        "请提出完整室内设计框架，包括模块化建造逻辑、本地材料应用与培训动线组织。"
    )

    assert result["project_type"] in {
        "community_public",
        "healthcare_wellness",
        "educational_facility",
    }
    assert result["project_type"] != "commercial_retail"
    assert result["confidence"] >= 0.55


def test_generic_design_terms_do_not_force_retail_classification():
    result = classify(
        "施工图深化阶段，设计师提出将进口天然大理石替换为新型环保回收材料，"
        "造价反而高出20%。业主注重成本控制。请提出完整论证逻辑。"
    )

    assert result["project_type"] is None
    assert result["status"] == "needs_input"


def test_generic_demonstration_terms_do_not_force_urban_renewal_market():
    result = classify(
        "一座位于撒哈拉边缘的极端干旱实验社区，需要打造“水资源教育与生活示范中心”。"
        "请提出完整室内设计概念，包括水循环可视化系统、材料耐热选择与公众互动空间组织。"
    )

    assert result["project_type"] != "urban_renewal_market"
    assert result["status"] in {"needs_clarification", "draft"}


def test_enterprise_research_showcase_uses_enterprise_context_not_real_estate():
    result = classify(
        "一家生物科技公司希望打造“未来实验室展示中心”，既展示研发能力，又接待投资人。"
        "请提出完整空间设计概念，包括透明实验界面、洁净区与展示区分隔、品牌科技感表达与安全规范整合。"
    )

    assert result["project_type"] in {"commercial_enterprise", "special_function"}
    assert result["project_type"] != "real_estate_showcase"
    assert result["confidence"] >= 0.55


def test_stable_fallback_patterns_raise_confidence_for_reception_and_research_centers():
    reception = classify(
        "一座位于新疆的国际贸易会客中心，需要在“一带一路”语境下表达多元文化交流精神，"
        "同时避免政治符号化。请提出完整室内设计概念，包括材料语言融合机制、文化隐喻转译与空间外交表达。"
    )
    research = classify(
        "某跨国集团计划在北极圈内建设“极地研究与生活中心”，空间需应对极昼极夜环境。"
        "请提出完整室内设计框架，包括人工光节律系统、保温构造与心理稳定策略。"
    )

    assert reception["project_type"] == "commercial_enterprise"
    assert reception["confidence"] >= 0.55
    assert research["project_type"] == "special_function"
    assert research["confidence"] >= 0.55


def test_company_workplace_context_raises_office_classification_confidence():
    result = classify(
        "一家专注“注意力经济”的互联网公司希望办公空间能增强员工专注力并减少信息过载。"
        "请从认知心理学与神经科学角度提出完整室内设计策略，包括视觉干扰控制、声环境优化与空间节律组织。"
    )

    assert result["project_type"] == "commercial_office"
    assert result["confidence"] >= 0.55


def test_creator_studio_context_outranks_generic_office_studio():
    result = classify(
        "为一位B站知名UP主设计个人工作室，他是动漫与手办收藏爱好者，空间需以收藏品为核心展示，"
        "同时营造强烈“二次元”沉浸感，并支持拍摄直播。请提出完整设计方案，包括展示墙结构、"
        "灯光控制系统、背景可替换模块与视觉层次管理。"
    )

    assert result["project_type"] == "digital_media_studio"
    assert result["confidence"] >= 0.55


def test_institutional_private_reception_context_is_not_children_family():
    result = classify(
        "某跨国银行准备在迪拜打造“超高净值私人会客空间”，强调私密与权力象征。"
        "请提出完整设计框架，包括材料奢华度控制、动线安全机制与文化适应策略。"
    )

    assert result["project_type"] == "commercial_enterprise"
    assert result["project_type"] != "children_family"
    assert result["confidence"] >= 0.55


def test_enterprise_technical_showcase_keeps_enterprise_confidence():
    result = classify(
        "一家新能源企业希望打造“氢能未来展示馆”，既展示技术突破，又向公众普及能源转型理念。"
        "请提出完整室内设计框架，包括能源可视化装置、交互体验路径与科普叙事结构。"
    )

    assert result["project_type"] == "commercial_enterprise"
    assert result["confidence"] >= 0.55


def test_automotive_brand_experience_keeps_automotive_confidence():
    result = classify(
        "为蔚来汽车设计西安大唐不夜城NIO House概念，需将智能电动车未来感与盛唐历史文脉深度融合，"
        "而非简单拼贴。请提出完整室内设计框架，包括科技表达语言、历史文化转译逻辑、会员社交场景构建与材料系统整合。"
    )

    assert result["project_type"] == "automotive_showroom"
    assert result["confidence"] >= 0.55


def test_real_chinese_milk_tea_prompt_exposes_commercial_operation_axis():
    result = classify(
        "\u6df1\u5733\u5e02\u5357\u5c71\u533a\u6765\u798f\u58eb\u5e7f\u573a"
        "\uff0c\u8d1f\u4e00\u697c\uff0c30\u5e73\u7c73\u5546\u94fa"
        "\uff0c\u5730\u94c1\u901a\u9053\u4e0e\u5546\u573a\u7684\u8fde\u63a5\u5904"
        "\uff0c\u6253\u7b97\u505a\u4e00\u4e2a\u5976\u8336\u5e97"
        "\uff0c\u5e0c\u671b\u534a\u5e74\u80fd\u6536\u56de\u6210\u672c"
        "\uff0c\u6211\u9700\u8981\u4e00\u4efd\u5b8c\u6574\u7684\u8bbe\u8ba1\u5efa\u8bae\u3002"
    )

    assert result["project_type"] == "commercial_dining"
    assert result["space_axis"]["primary_axis_id"] == "commercial_operation_roi"
    assert "回本" in result["space_axis"]["primary_axis_label"]
    assert "客流" in result["space_axis"]["decision_focus"][0]
    assert result["space_axis"]["must_not_route_to"] == []


def test_real_chinese_founder_villa_exposes_identity_legacy_axis_not_urban_renewal():
    result = classify(
        "\u9879\u76ee\u4f4d\u4e8e\u6df1\u5733\u6e7e\u4e00\u7ebf\u6d77\u666f\u522b\u5885\u533a"
        "\uff0c\u4e1a\u4e3b\u4e3a\u7b2c\u4e00\u4ee3\u521b\u4e1a\u8005"
        "\uff0c\u4ece\u8349\u6839\u594b\u6597\u81f3\u8d44\u672c\u6210\u529f"
        "\uff0c\u5bf9\u7a7a\u95f4\u7684\u671f\u5f85\u65e2\u5305\u542b\u6210\u5c31\u8c61\u5f81"
        "\uff0c\u4e5f\u5305\u542b\u5bb6\u65cf\u4f20\u627f\u4e0e\u5185\u5fc3\u56de\u5f52\u3002"
        "\u8bf7\u4ece\u4e00\u4ee3\u521b\u4e1a\u8005\u7684\u7cbe\u795e\u7ed3\u6784\u51fa\u53d1"
        "\uff0c\u63d0\u51fa\u5b8c\u6574\u5ba4\u5185\u8bbe\u8ba1\u6982\u5ff5\u3002"
    )

    assert result["project_type"] == "personal_residential"
    assert result["space_axis"]["primary_axis_id"] == "private_residential_identity_legacy"
    assert "身份" in result["space_axis"]["primary_axis_label"]
    assert "家族" in result["space_axis"]["decision_focus"][1]
    assert "urban_renewal_heritage" in result["space_axis"]["must_not_route_to"]


def test_residential_spiritual_theme_words_do_not_override_spatial_container():
    residential_prompts = [
        (
            "成都富人区一栋350㎡别墅，业主为35岁单身女性，偏爱Tiffany品牌的优雅气质与珠宝艺术精神。"
            "请提出完整软装设计概念，深入分析品牌背后的“被珍视感”“仪式感”与女性自我认同逻辑，"
            "构建空间叙事结构、色彩系统与艺术陈设策略。"
        ),
        (
            "一位国际记者每年只在家中居住4个月，需要一个“锁上门就能走”的住宅，易维护、安防性强，"
            "并在回归时迅速恢复温馨感。请提出完整设计策略，包括材料耐久度、智能安防系统、远程监控机制与归家仪式感。"
        ),
        (
            "一位哲学家与神经科学家夫妻希望打造“意识研究住宅实验室”，融合生活与研究。"
            "请提出完整设计概念，包括实验区域安全隔离、冥想空间组织与数据采集设备整合。"
        ),
        (
            "茶道大师希望在家中打造极致纯粹茶室，从入口路径、光线引入到材料选择都必须服务茶道仪式与心境。"
            "请提出完整室内设计框架，包括步行节奏设计、榻榻米比例控制、光影层级与材质克制逻辑。"
        ),
    ]

    for prompt in residential_prompts:
        result = classify(prompt)

        assert result["project_type"] == "personal_residential"
        assert result["project_type"] != "religious_spiritual"
        assert result["space_axis"]["primary_axis_id"] != "spiritual_ritual_order"


def test_explicit_cross_faith_or_dedicated_spiritual_institution_can_route_to_spiritual_axis():
    result = classify(
        "某宗教文化研究机构希望打造“跨信仰对话空间”，用于不同宗教背景人士的交流。"
        "请从宗教哲学与空间象征角度提出完整设计框架，包括光影象征语言、材料中性表达与情绪平衡机制。"
    )

    assert result["project_type"] == "religious_spiritual"
    assert result["space_axis"]["primary_axis_id"] == "spiritual_ritual_order"


def test_blended_family_privacy_conflict_is_residential_not_children_public_service():
    result = classify(
        "\u4e00\u4e2a\u518d\u5a5a\u5bb6\u5ead\uff0c\u7537\u65b9\u5e2616\u5c81\u513f\u5b50"
        "\uff0c\u5973\u65b9\u5e2610\u5c81\u5973\u513f\uff0c\u9700\u8981\u5728\u540c\u4e00\u5c4b\u6a90\u4e0b"
        "\u4e3a\u4e24\u4e2a\u65e0\u8840\u7f18\u3001\u5904\u4e8e\u4e0d\u540c\u9752\u6625\u671f\u9636\u6bb5"
        "\u7684\u5b69\u5b50\u521b\u9020\u65e2\u6709\u516c\u5171\u4ea4\u6d41\u533a"
        "\uff0c\u53c8\u6709\u7edd\u5bf9\u9690\u79c1\u4e0e\u72ec\u7acb\u6027\u7684\u7a7a\u95f4\u3002"
        "\u8bf7\u63d0\u51fa\u5b8c\u6574\u8bbe\u8ba1\u65b9\u6848"
        "\uff0c\u5305\u62ec\u51b2\u7a81\u7f13\u51b2\u673a\u5236"
        "\u3001\u516c\u5171\u7a7a\u95f4\u7ec4\u7ec7\u4e0e\u5fc3\u7406\u5b89\u5168\u8fb9\u754c\u8bbe\u5b9a\u3002"
    )

    assert result["project_type"] == "personal_residential"
    assert result["project_type"] != "children_family"
    assert result["confidence"] >= 0.55
    assert result["space_axis"]["primary_axis_id"] == "residential_conflict_lifestyle_balance"
    assert "隐私" in " ".join(result["space_axis"]["decision_focus"])


def test_family_home_with_autism_support_stays_residential_not_healthcare():
    result = classify(
        "深圳前海160㎡住宅，家庭结构复杂：35岁腾讯程序员父亲，34岁全职母亲，"
        "7岁自闭症儿童，外公外婆每年冬季短住三个月。请提出完整室内设计框架，"
        "涵盖感统训练空间、情绪缓冲区、长辈短住适配系统、收纳与隔音策略以及家庭互动与私密平衡。"
    )

    assert result["project_type"] == "personal_residential"
    assert result["project_type"] != "healthcare_wellness"
    assert result["space_axis"]["primary_axis_id"] == "residential_conflict_lifestyle_balance"


def test_allergy_child_bedroom_stays_residential_not_healthcare_or_mission_critical():
    result = classify(
        "为一位患有严重花粉与粉尘过敏症的儿童设计卧室，要求所有材料低敏或无敏，"
        "并集成医疗级新风与空气净化系统，同时空间不能显得像病房。请提出完整设计方案，"
        "涵盖材料筛选逻辑、软装控制策略、空气系统隐形整合、照明温度控制与心理舒缓机制。"
    )

    assert result["project_type"] == "personal_residential"
    assert result["project_type"] != "healthcare_wellness"
    assert result["space_axis"]["primary_axis_id"] in {
        "private_residential_life_order",
        "residential_conflict_lifestyle_balance",
        "healthcare_wellness_support",
    }
    assert result["space_axis"]["primary_axis_id"] != "mission_critical_resilience"


def test_future_underground_resilience_spaces_use_mission_critical_axis_not_healthcare():
    prompts = [
        (
            "\u67d0\u672a\u6765\u57ce\u5e02\u89c4\u5212\u201c\u5730\u4e0b\u5c45\u4f4f\u5355\u5143\u201d"
            "\uff0c\u5e94\u5bf9\u4eba\u53e3\u8fc7\u5bc6\u4e0e\u6781\u7aef\u6c14\u5019\u95ee\u9898\u3002"
            "\u8bf7\u63d0\u51fa\u5b8c\u6574\u5ba4\u5185\u8bbe\u8ba1\u6846\u67b6"
            "\uff0c\u5305\u62ec\u5149\u4e95\u7cfb\u7edf"
            "\u3001\u7a7a\u6c14\u5faa\u73af\u6a21\u578b\u4e0e\u5fc3\u7406\u8212\u9002\u5ea6\u63a7\u5236\u3002"
        ),
        (
            "\u4e00\u5ea7\u4f4d\u4e8e\u706b\u5c71\u6d3b\u8dc3\u5e26\u7684\u57ce\u5e02"
            "\u51c6\u5907\u5efa\u8bbe\u201c\u5730\u4e0b\u751f\u6d3b\u793e\u533a\u793a\u8303\u5355\u5143\u201d"
            "\uff0c\u4ee5\u5e94\u5bf9\u672a\u6765\u6781\u7aef\u5730\u8d28\u98ce\u9669\u3002"
            "\u8bf7\u63d0\u51fa\u5b8c\u6574\u5ba4\u5185\u8bbe\u8ba1\u7b56\u7565"
            "\uff0c\u5305\u62ec\u7a7a\u6c14\u51c0\u5316\u7cfb\u7edf"
            "\u3001\u5149\u4e95\u7ed3\u6784\u4e0e\u5fc3\u7406\u7f13\u89e3\u7a7a\u95f4\u3002"
        ),
    ]

    for prompt in prompts:
        result = classify(prompt)

        assert result["project_type"] != "healthcare_wellness"
        assert result["confidence"] >= 0.55
        assert result["space_axis"]["primary_axis_id"] == "mission_critical_resilience"
        assert "极端" in result["space_axis"]["primary_axis_label"]


def test_site_scale_planning_inputs_raise_confidence_without_specialist_pack():
    prompts = [
        (
            "一个滨海新区准备开发“未来生活示范社区”，规划阶段尚未确定建筑形式。"
            "请提出完整的前期定位与空间策略框架，包括客群画像推演、产品线分级逻辑、"
            "景观资源利用、公共空间组织与长期品牌IP塑造机制。"
        ),
        (
            "一块位于城市核心区的旧厂房地块准备整体更新为复合型社区，"
            "需兼顾商业、办公与居住。请提出完整城市更新策略，包括土地价值重构逻辑、"
            "功能混合比例、公共开放空间布局与景观系统连续性。"
        ),
        (
            "一处城郊农业用地计划转型为“农业+艺术+居住”复合示范区，尚处概念阶段。"
            "请提出完整战略定位框架，包括产业结构推演、建筑密度控制、"
            "景观系统分层与室内空间叙事逻辑，并说明如何形成可持续的开发模型。"
        ),
        (
            "一座拥有百年历史的工业厂区准备转型为“创意产业园”，但周边客流有限、交通不便利。"
            "请提出完整改造框架，包括功能组合策略、标志性空间打造、"
            "首店品牌引入逻辑与租金梯度设计。"
        ),
        (
            "一个以陶瓷、木雕或刺绣等传统手工艺为特色的乡镇，准备建设“非遗工坊聚落”。"
            "请提出完整空间设计策略，包括工坊展示界面、游客体验路径、"
            "销售转化空间与产业孵化机制。"
        ),
        (
            "一个位于河岸线的城市新区准备打造“滨水文化长廊”，希望通过景观与公共建筑带动周边地产溢价。"
            "请提出完整建筑与景观整合框架，包括视线轴线组织、公共节点设置与室内商业导入策略。"
        ),
    ]

    for prompt in prompts:
        result = classify(prompt)

        assert result["project_type"] in {
            "landscape_outdoor",
            "urban_renewal_market",
            "urban_renewal_heritage",
            "community_public",
            "rural_construction",
        }
        assert result["confidence"] >= 0.55
        assert result["space_axis"]["primary_axis_id"] in {
            "landscape_public_value",
            "urban_renewal_public_regeneration",
            "public_service_inclusive_reuse",
        }


def test_high_constraint_prototype_spaces_raise_confidence_without_specialist_pack():
    prompts = [
        (
            "一个定位“零碳生活方式”的住宅样板房，希望所有材料来源可追溯且可回收。"
            "请提出完整设计框架，包括材料数据库选择逻辑、施工节点优化与碳足迹展示策略。"
        ),
        (
            "一座位于冰岛的极寒艺术驻留中心，需要在严酷自然环境中提供创作与生活空间。"
            "请提出完整室内设计策略，包括保温系统、光照补偿机制与艺术家心理支持空间。"
        ),
        (
            "一家面向未来世代的“后碳城市样板屋”，要求完全脱离化石能源供应。"
            "请提出完整室内设计概念，包括储能系统嵌入、可持续材料数据库与能源使用可视化展示。"
        ),
    ]

    for prompt in prompts:
        result = classify(prompt)

        assert result["project_type"] is not None
        assert result["confidence"] >= 0.55
        assert result["space_axis"]["primary_axis_id"] in {
            "mission_critical_resilience",
            "sustainable_energy_prototype",
        }


def test_structured_cross_disciplinary_design_contexts_get_basic_confidence_floor():
    prompts = [
        (
            "一对经历婚姻危机后决定复合的夫妻，希望重新设计主卧室，象征“重新开始”，预算有限。"
            "请提出完整室内设计概念，包括情绪修复机制、材料选择策略、灯光氛围与低成本实施路径。"
        ),
        (
            "一所大学准备改造老旧宿舍为“创新社区公寓”，鼓励跨专业交流。"
            "请提出完整室内设计概念，包括公共厨房系统、讨论区组织与宿舍单元可变性。"
        ),
        (
            "一位跨国时尚博主希望在上海打造“流动式生活空间”，可快速调整用于派对、拍摄与居住。"
            "请提出完整设计方案，包括可移动家具系统、灯光模块化与社交展示逻辑。"
        ),
        (
            "某农业大县计划建设“农产品品牌体验馆”，将线上销售与线下展示结合。"
            "请提出完整室内设计框架，包括品牌故事叙事路径、产品陈列逻辑与直播空间整合。"
        ),
    ]

    for prompt in prompts:
        result = classify(prompt)

        assert result["project_type"] is not None
        assert result["confidence"] >= 0.55
        assert result["space_axis"]["primary_axis_id"] not in {
            "unclassified_needs_axis",
            "methodology_not_project",
        }


def test_public_policy_or_planning_scale_housing_products_do_not_collapse_to_private_home():
    prompts = [
        (
            "政府主导保障性住房项目，需要制定室内标准，在极低成本下为低收入家庭提供有尊严、"
            "健康且灵活的居住空间。请提出完整设计框架，包括标准化模块、成本控制节点与可升级预留策略。"
        ),
        (
            "一个未来城市提出“文明重启样板住宅”概念，用于在极端灾难后快速重建社会基础生活单元。"
            "请提出完整室内设计策略，包括最小生活单元构成、模块化扩展机制与社区协作空间组织。"
        ),
        (
            "某地方政府提出“乡村人才回流计划”，希望通过改善自建房居住品质吸引青年返乡。"
            "请提出完整室内设计模型，包括可成长住宅结构、家庭工作室整合与乡村现代生活方式表达。"
        ),
        (
            "某地方政府计划建设“高端康养小镇”，目标客群为60岁以上中高净值人群。"
            "请提出完整定位与规划策略，包括医疗资源嵌入、慢行系统设计、景观疗愈空间与住宅产品结构分级。"
        ),
    ]

    for prompt in prompts:
        result = classify(prompt)

        assert result["project_type"] != "personal_residential"
        assert result["confidence"] >= 0.55
        assert result["space_axis"]["primary_axis_id"] not in {
            "private_residential_life_order",
            "private_residential_identity_legacy",
            "residential_conflict_lifestyle_balance",
            "unclassified_needs_axis",
            "methodology_not_project",
        }


def test_wellness_social_club_and_temporary_recyclable_pavilion_have_method_axes():
    prompts = [
        (
            "一座位于重庆山地的高端住宅区，希望在会所中打造“抗焦虑社交空间”，"
            "针对高压金融从业者。请提出完整设计策略，包括空间节奏控制、材料触感系统、"
            "呼吸式动线设计与声环境调节机制。",
            "sports_wellness_social",
        ),
        (
            "某国际艺术双年展希望打造“临时城市展馆”，三个月后必须全部拆除并回收材料。"
            "请提出完整室内设计策略，包括可拆装结构系统、循环材料逻辑与观众动线组织。",
            "material_sustainability_value",
        ),
    ]

    for prompt, expected_axis in prompts:
        result = classify(prompt)

        assert result["confidence"] >= 0.55
        assert result["space_axis"]["primary_axis_id"] == expected_axis
        assert result["space_axis"]["primary_axis_id"] != "unclassified_needs_axis"


def test_rural_public_and_agritourism_projects_do_not_route_to_private_home_axis():
    prompts = [
        (
            "某沿海城市启动“美丽乡村”示范村项目，希望通过设计提升村庄整体形象，"
            "同时带动乡村旅游与农产品销售。请提出完整室内与公共空间设计策略，包括民居立面更新、"
            "公共会客厅打造、农产品展示系统与品牌视觉整合机制。"
        ),
        (
            "某乡村准备打造“农文旅融合示范区”，希望结合农田景观、乡土建筑与民宿经济。"
            "请提出完整空间设计概念，包括游客动线规划、村民参与空间组织、在地材料应用与长期运营机制。"
        ),
    ]

    for prompt in prompts:
        result = classify(prompt)

        assert result["project_type"] == "rural_construction"
        assert result["space_axis"]["primary_axis_id"] == "rural_living_regeneration"
        assert result["space_axis"]["primary_axis_id"] not in {
            "private_residential_life_order",
            "private_residential_identity_legacy",
        }
