from pathlib import Path

from intelligent_project_analyzer.services.project_type_detector import validate_registries_against_yaml


REGISTRY_DIR = Path("intelligent_project_analyzer/config/registries")


def test_core_space_classification_registries_are_externalized():
    required_files = [
        "founding_type_registry.yaml",
        "subdomain_registry.yaml",
        "spatial_extent_registry.yaml",
        "lifecycle_registry.yaml",
        "spatial_layer_registry.yaml",
        "space_axis_registry.yaml",
    ]

    missing = [name for name in required_files if not (REGISTRY_DIR / name).exists()]

    assert missing == []


def test_core_space_classification_registry_yaml_matches_runtime():
    report = validate_registries_against_yaml()

    for section in ["founding_type", "subdomain", "spatial_extent", "lifecycle", "spatial_layer"]:
        assert section in report
        assert report[section]["consistent"] is True


def test_space_axis_registry_drives_runtime_axis_payload():
    from intelligent_project_analyzer.services.space_classification_service import (
        SpaceClassificationService,
    )

    result = SpaceClassificationService().classify(
        "\u6df1\u5733\u5e02\u5357\u5c71\u533a\u6765\u798f\u58eb\u5e7f\u573a"
        "\uff0c\u8d1f\u4e00\u697c\uff0c30\u5e73\u7c73\u5546\u94fa"
        "\uff0c\u5730\u94c1\u901a\u9053\u4e0e\u5546\u573a\u7684\u8fde\u63a5\u5904"
        "\uff0c\u6253\u7b97\u505a\u4e00\u4e2a\u5976\u8336\u5e97"
        "\uff0c\u5e0c\u671b\u534a\u5e74\u80fd\u6536\u56de\u6210\u672c"
        "\uff0c\u6211\u9700\u8981\u4e00\u4efd\u5b8c\u6574\u7684\u8bbe\u8ba1\u5efa\u8bae\u3002"
    )

    assert result["space_axis"]["registry_source"] == "space_axis_registry.yaml"
    assert result["space_axis"]["matched_rule_id"] == "commercial_operation_roi"
    assert result["space_axis"]["primary_axis_id"] == "commercial_operation_roi"


def test_space_axis_registry_covers_stable_non_tea_project_axes():
    from intelligent_project_analyzer.services.space_classification_service import (
        SpaceClassificationService,
    )

    service = SpaceClassificationService()
    examples = [
        (
            "\u4e2d\u56fd\u4e66\u6cd5\u5927\u9152\u5e97\uff0c\u5efa\u7b51\u9762\u79ef50000\u5e73\u7c73"
            "\uff0c\u529f\u80fd\u6db5\u76d6\u4f4f\u5bbf\u3001\u4f1a\u8bae\u3001\u5c55\u89c8\u548c\u5b66\u672f\u4ea4\u6d41"
            "\uff0c\u9700\u8981\u6210\u4e3a\u4e66\u6cd5\u6587\u5316\u7684\u7cbe\u795e\u5730\u6807\u3002",
            "hospitality_culture_operation",
        ),
        (
            "\u6df1\u5733\u86c7\u53e320000\u5e73\u7c73\u83dc\u5e02\u573a\u66f4\u65b0\u6539\u9020"
            "\uff0c\u9700\u8981\u517c\u987e\u8001\u5c45\u6c11\u3001\u9999\u6e2f\u8bbf\u5ba2\u3001\u5916\u7c4d\u5ba2\u7fa4"
            "\uff0c\u878d\u5165\u6e14\u6751\u4f20\u7edf\u6587\u5316\u548c\u5546\u4e1a\u53ef\u6301\u7eed\u6a21\u578b\u3002",
            "urban_renewal_public_regeneration",
        ),
        (
            "\u5e7f\u5dde\u8001\u65e7\u5c0f\u533a200\u5e73\u7c73\u793e\u533a\u6d3b\u52a8\u4e2d\u5fc3\u6539\u9020"
            "\uff0c\u4e3b\u8981\u4f7f\u7528\u8005\u4e3a\u8001\u5e74\u4eba\u4e0e\u653e\u5b66\u540e\u5c0f\u5b66\u751f"
            "\uff0c\u9700\u8981\u68cb\u724c\u3001\u9605\u8bfb\u3001\u4e66\u6cd5\u548c\u513f\u7ae5\u6258\u7ba1\u5206\u65f6\u590d\u7528\u3002",
            "public_service_inclusive_reuse",
        ),
        (
            "\u4e3a\u4e00\u4f4d\u60a3\u6709\u4e25\u91cd\u82b1\u7c89\u4e0e\u7c89\u5c18\u8fc7\u654f\u75c7\u7684\u513f\u7ae5\u8bbe\u8ba1\u5367\u5ba4"
            "\uff0c\u8981\u6c42\u4f4e\u654f\u6750\u6599\u3001\u533b\u7597\u7ea7\u65b0\u98ce\u548c\u5fc3\u7406\u8212\u7f13\u3002",
            "healthcare_wellness_support",
        ),
        (
            "\u804c\u4e1a\u7535\u7ade\u9009\u624b\u9700\u8981\u5c0615\u5e73\u7c73\u5367\u5ba4\u6539\u9020\u4e3a\u9876\u7ea7\u76f4\u64ad\u4e0e\u8bad\u7ec3\u7a7a\u95f4"
            "\uff0c\u8981\u6c42\u7edd\u5bf9\u9694\u97f3\u3001\u4e13\u4e1a\u706f\u5149\u4e0e\u4eba\u4f53\u5de5\u5b66\u652f\u6301\u3002",
            "technical_performance_environment",
        ),
        (
            "\u5357\u5145\u5609\u9675\u533a\u4e94\u4e07\u5e73\u7c73\u4e24\u5c42\u5546\u4e1a\u8857\u533a"
            "\uff0c\u9762\u4e34\u9644\u8fd1\u5546\u573a\u7ade\u4e89\uff0c\u9700\u8981\u5ba2\u7fa4\u5b9a\u4f4d"
            "\u3001\u52a8\u7ebf\u7ec4\u7ec7\u3001\u591c\u7ecf\u6d4e\u6fc0\u6d3b\u548c\u54c1\u724c\u5dee\u5f02\u5316\u3002",
            "retail_brand_conversion",
        ),
    ]

    for prompt, expected_axis in examples:
        result = service.classify(prompt)

        assert result["space_axis"]["registry_source"] == "space_axis_registry.yaml"
        assert result["space_axis"]["primary_axis_id"] == expected_axis


def test_space_axis_registry_covers_cross_domain_method_axes():
    from intelligent_project_analyzer.services.space_classification_service import (
        SpaceClassificationService,
    )

    service = SpaceClassificationService()
    examples = [
        (
            "南昌四层复合型总部建筑：1楼艺术展厅，2楼办公室，3楼家庭住宅，4楼露台会所。"
            "请阐述公共与私密的分层逻辑、结构改造策略以及事业与家庭精神融合路径。",
            "complex_mixed_use_layering",
        ),
        (
            "中餐厅设8间包房，要求从苏东坡诗词中提炼四字命名，"
            "传递生活态度与价值观，并解释每个名字对应的情绪表达与包房设计气质。",
            "brand_cultural_narrative",
        ),
        (
            "施工图深化阶段，设计师提出将进口天然大理石替换为环保回收材料，"
            "造价高出20%，需要论证长期运营价值、品牌溢价与可持续形象。",
            "material_sustainability_value",
        ),
        (
            "三亚海边半开放式全木结构餐厅，需面对高盐雾腐蚀、潮湿环境、白蚁威胁与台风强风压，"
            "请提出木材防腐工艺、结构连接件选型与抗风构造细节方案。",
            "climate_resilience_construction",
        ),
        (
            "一个位于广州的高端健身俱乐部，希望通过空间升级吸引女性高净值会员，"
            "包括私密训练空间、灯光心理学、香氛系统与社交休息区结构。",
            "sports_wellness_social",
        ),
        (
            "一个国际品牌准备在海南开设沉浸式体验中心，结合度假、品牌展示与销售，"
            "需要动线叙事结构、情绪高潮点设置与销售转化机制。",
            "immersive_experience_conversion",
        ),
        (
            "一个位于河岸线的城市新区准备打造滨水文化长廊，"
            "希望通过景观与公共建筑带动周边地产溢价，请提出建筑与景观整合框架。",
            "landscape_public_value",
        ),
    ]

    for prompt, expected_axis in examples:
        result = service.classify(prompt)

        assert result["space_axis"]["registry_source"] == "space_axis_registry.yaml"
        assert result["space_axis"]["primary_axis_id"] == expected_axis


def test_space_axis_registry_covers_remaining_systemic_axis_families():
    from intelligent_project_analyzer.services.space_classification_service import (
        SpaceClassificationService,
    )

    service = SpaceClassificationService()
    examples = [
        (
            "崇明岛市民农场访客中心，包含农产品展示、亲子厨房、科普教育与咖啡区，"
            "需体现有机、自然与可持续理念。请提出材料循环、动线组织和教育互动模块。",
            "public_learning_visitor_experience",
        ),
        (
            "健身教练与作家夫妻共居公寓，一人需要高强度CrossFit训练空间，"
            "另一人需要绝对安静写作环境。请提出动静分区、隔音系统与视觉分隔机制。",
            "residential_conflict_lifestyle_balance",
        ),
        (
            "百年药铺改造为现代中医生活馆，需兼顾传统文化与年轻客群体验。"
            "请提出药材展示、气味管理、问诊私密动线与品牌视觉更新。",
            "healthcare_culture_experience",
        ),
        (
            "国际NGO计划在非洲设立医疗支援培训中心，预算有限但希望建立长期使用标准。"
            "请提出模块化建造、本地材料应用与培训动线组织。",
            "public_resilience_modular_support",
        ),
        (
            "某跨国集团计划建设数据安全指挥中心，要求空间具备极高安全等级与长期运行能力。"
            "请提出设备布局、冗余能源系统与人员心理压力缓冲空间。",
            "mission_critical_resilience",
        ),
        (
            "一座面向未来世代的后碳城市样板屋，要求完全脱离化石能源供应。"
            "请提出储能系统嵌入、可持续材料数据库与能源使用可视化展示。",
            "sustainable_energy_prototype",
        ),
        (
            "老街区希望打造非标咖啡与小酒馆集群，形成青年文化聚点。"
            "请提出空间风格多样性控制、夜间灯光系统、社交尺度与租金分层逻辑。",
            "urban_public_value_cluster",
        ),
        (
            "某国际品牌希望打造传播学实验零售空间，测试不同空间语言对消费行为的影响。"
            "请提出A/B空间对照系统、灯光与音乐变量控制、数据采集接口与消费转化路径。",
            "experimental_public_experience",
        ),
    ]

    for prompt, expected_axis in examples:
        result = service.classify(prompt)

        assert result["space_axis"]["registry_source"] == "space_axis_registry.yaml"
        assert result["space_axis"]["primary_axis_id"] == expected_axis


def test_space_axis_registry_reuses_existing_axes_for_residual_families():
    from intelligent_project_analyzer.services.space_classification_service import (
        SpaceClassificationService,
    )

    service = SpaceClassificationService()
    examples = [
        (
            "一所大学准备改造老旧宿舍为创新社区公寓，鼓励跨专业交流。"
            "请提出公共厨房系统、讨论区组织与宿舍单元可变性。",
            "education_growth_safety",
        ),
        (
            "一座位于新疆的国际贸易会客中心，需要在一带一路语境下表达多元文化交流精神，"
            "同时避免政治符号化。请提出材料语言融合、文化隐喻转译与空间外交表达。",
            "brand_cultural_narrative",
        ),
        (
            "某农业大县计划建设农产品品牌体验馆，将线上销售与线下展示结合。"
            "请提出品牌故事叙事路径、产品陈列逻辑与直播空间整合。",
            "retail_brand_conversion",
        ),
    ]

    for prompt, expected_axis in examples:
        result = service.classify(prompt)

        assert result["space_axis"]["registry_source"] == "space_axis_registry.yaml"
        assert result["space_axis"]["primary_axis_id"] == expected_axis
