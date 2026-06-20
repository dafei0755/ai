from pathlib import Path

import pytest
import yaml
from sqlalchemy import create_engine

from intelligent_project_analyzer.services.demand_reconstruction_insight_protocol import (
    DemandReconstructionInsightProtocol,
)
from intelligent_project_analyzer.services.demand_reconstruction_context_adapter import (
    DemandReconstructionContextAdapter,
)
from intelligent_project_analyzer.services.demand_reconstruction_output_planner import (
    DemandReconstructionOutputPlanner,
)
from intelligent_project_analyzer.services.demand_reconstruction_service import (
    DemandReconstructionService,
    DemandReconstructionUnavailable,
)
from intelligent_project_analyzer.services.knowledge_governance_store import KnowledgeGovernanceStore
from intelligent_project_analyzer.services.multi_llm_factory import FallbackLLM


RURAL_HOME_PROMPT = "50岁男性室内设计师，背井离乡，想在老家建一栋民居，给出建议"
CAFE_PROMPT = "30㎡社区咖啡店，怎么提高翻台和外带效率，给出建议"
FRAGRANCE_FLAGSHIP_PROMPT = (
    "一个小众香薰品牌希望打造80㎡旗舰店，兼顾产品试闻、品牌故事、会员活动和高客单转化，"
    "请先帮我重构需求。"
)
RESTAURANT_NAMING_PROMPT = (
    "一家中餐厅希望用苏东坡文化为包房命名，形成一套有文化感但不堆砌典故的空间语言，"
    "请先帮我重构需求。"
)
FINE_DINING_RESTAURANT_PROMPT = (
    "一家高端中餐厅希望重构品牌文化体验，包含宴请接待、包房秩序、茶室、艺术陈设和服务动线，"
    "请先帮我重构需求。"
)
HOTEL_LOBBY_PROMPT = (
    "一家精品酒店希望改造大堂，包含入住接待、行李寄存、早餐外摆、商务等候和城市文化展示，"
    "请先帮我重构需求。"
)
LONG_TERM_APARTMENT_AMENITY_PROMPT = (
    "一个长租公寓项目希望改造公共区，包含共享厨房、健身、社交活动、快递收纳和运营维护，"
    "请先帮我重构需求。"
)
POPUP_BRAND_EXPERIENCE_PROMPT = (
    "一个手机品牌希望打造快闪体验店，包含新品互动展陈、会员活动、销售转化和社交传播，"
    "请先帮我重构需求。"
)
AUTOMATED_RETAIL_PROMPT = (
    "一家无人便利店希望重构80㎡门店，包含自助结算、货架补货、冷柜监控、防损摄像头、"
    "夜间运营和会员复购，请先帮我重构需求。"
)
FAMILY_RESTAURANT_PROMPT = (
    "一家亲子家庭餐厅希望重新设计空间，包含儿童活动区、家庭聚餐、生日派对、厨房出餐和会员运营，"
    "请先帮我重构需求。"
)
RESIDENTIAL_BRAND_SHOWROOM_PROMPT = (
    "一家住宅品牌希望打造体验馆，包含样板间展示、材料体验、销售咨询和会员活动，"
    "请先帮我重构需求。"
)
RETIREMENT_COMMUNITY_SERVICE_PROMPT = (
    "一个退休社区服务中心需要重构空间，包含日间照料、活动教室、社区食堂和医护值班，"
    "请先帮我重构需求。"
)
FAMILY_ENTERPRISE_BRAND_EXHIBITION_PROMPT = (
    "一个家族企业希望打造品牌展厅，包含企业历史、产品展示、客户接待和员工活动，"
    "请先帮我重构需求。"
)
LAW_OFFICE_PROMPT = (
    "一家精品律所希望改造办公室，包含律师独立办公、客户会谈、档案保密、合伙人会议和团队协作，"
    "请先帮我重构需求。"
)
COUNSELING_OFFICE_PROMPT = (
    "一家心理咨询机构希望改造办公室，包含接待、咨询室、团体活动、档案保密和咨询师恢复，"
    "请先帮我重构需求。"
)
STYLE_PROMPT = "我想做一个有东方感但不老气的茶空间，给点建议"
WABI_SABI_GUESTHOUSE_STYLE_PROMPT = (
    "一个民宿接待区想做侘寂和松弛感，但不能显得破旧或廉价，"
    "需要兼顾入住等候、拍照打卡和材料耐维护，请先帮我重构需求。"
)
HARD_CONSTRAINT_PROMPT = "小型茶饮店冷藏柜留多大，怎么看"
DEEP_RESEARCH_PROMPT = "我想研究宋代文人雅集对当代会所空间的启发，给出建议"
LINGNAN_BOOKSTORE_RESEARCH_PROMPT = (
    "我想研究岭南骑楼文化对社区书店空间的启发，"
    "请先帮我重构研究路径。"
)
FORMAL_BRIEF_PROMPT = (
    "四川广元农村300㎡田园民居，业主为50岁男性室内设计师，"
    "请提出完整室内设计概念框架，围绕光、材料、自然、界面和精神性空间。"
)
CITIZEN_FARM_PROMPT = (
    "崇明岛“市民农场”访客中心，包含农产品展示、亲子厨房、科普教育与咖啡区，"
    "需体现有机、自然与可持续理念。请提出完整设计框架，包括材料循环策略、"
    "动线组织、教育互动模块与品牌视觉系统。"
)
GENERIC_CITIZEN_FARM_PROMPT = (
    "某市民农场访客中心，包含农产品展示、亲子厨房、科普教育与咖啡区，"
    "请先帮我重构需求。"
)
FARM_KITCHEN_CAFE_PROMPT = (
    "某市民农场访客中心，包含亲子厨房、科普教育与咖啡区，"
    "请先帮我重构需求。"
)
COMMUNITY_LIBRARY_READING_PROMPT = (
    "一所社区图书馆希望改造儿童阅读区，包含亲子阅读、绘本活动、安静学习和借阅管理，"
    "请先帮我重构需求。"
)
COMMUNITY_CULTURE_CENTER_PROMPT = (
    "一个社区文化中心希望重构公共空间，包含非遗手作、居民活动、临时展览、公共讲座和志愿者运营，"
    "请先帮我重构需求。"
)
KUNQU_OLD_HOUSE_PROMPT = (
    "苏州昆曲老宅改造为教学故居，包含展陈、练声教学和小型交流，"
    "请先帮我重构需求。"
)
HISTORIC_CRAFT_EXHIBITION_PROMPT = (
    "一处历史建筑希望改造为地方工艺展示中心，包含展陈、手作教学和小型交流，"
    "请先帮我重构需求。"
)
HYDROGEN_EXHIBITION_PROMPT = (
    "一家新能源企业希望打造“氢能未来展示馆”，面向政府访客、产业伙伴和公众开放，"
    "请提出完整设计框架，包括展陈叙事、互动体验、技术安全边界和品牌信任建立。"
)
ORGANIC_EXHIBITION_PROMPT = (
    "一家材料科技企业希望打造有机可持续材料展示馆，面向客户、设计师和公众开放，"
    "请先帮我重构需求。"
)
ARCHIVE_LIBRARY_PROMPT = (
    "某城市档案馆需要建设地下档案库，要求恒温恒湿、防火分区、安防管理和公众查阅动线分离，"
    "请提出完整空间策略。"
)
DOLBY_CINEMA_PROMPT = (
    "一个家庭影音室希望配置杜比全景声系统，包含扬声器布局、隔声、吸声、低频控制、设备散热和观影座位，"
    "请先帮我重构需求。"
)
COASTAL_TIMBER_GUESTHOUSE_PROMPT = (
    "一处滨海木结构民宿需要改造，要求应对盐雾、防腐、台风抗风、结构安全、潮湿环境和长期维护，"
    "请先帮我重构需求。"
)
EXTREME_COLD_OXYGEN_GUESTHOUSE_PROMPT = (
    "一处高海拔极寒民宿需要改造，要求稳定供氧、新风保温、应急电力、设备维护、避难冗余和低温运营，"
    "请先帮我重构需求。"
)
POWER_INFRASTRUCTURE_ROOM_PROMPT = (
    "一个企业展厅需要设置弱电机房，包含UPS、电力容量、机柜散热、网络布线、检修通道和消防联动，"
    "请先帮我重构需求。"
)
BIOTECH_LAB_PROMPT = (
    "一个生物科技实验室需要重构空间，包含样本接收、洁净实验、设备维护、人员更衣和废弃物处理，"
    "请先帮我重构需求。"
)
METHODOLOGY_ONLY_PROMPT = (
    "请系统分析农耕文化与城市化进程如何影响当代室内设计概念结构，"
    "并总结可迁移的方法论框架。"
)
SPATIAL_RESEARCH_METHOD_PROMPT = (
    "社区文化空间应该怎么研究在地性、公共性和运营模式，"
    "请给出分析框架和判断方法。"
)
COMPETITION_STRATEGY_PROMPT = (
    "请帮我分析一个商业空间设计竞标的汇报策略、评审打动逻辑和PPT叙事，"
    "不需要重构项目需求。"
)
PURE_NAMING_COPY_PROMPT = (
    "请帮我给中餐厅包房做苏东坡主题命名，不涉及空间设计，只要名称和文案。"
)
REFERENCE_CASE_PROMPT = (
    "请整理10个办公总部设计案例，按动线、材料和品牌表达分类。"
)
AUTISM_FAMILY_HOME_PROMPT = (
    "一个有自闭症儿童的家庭，希望重新设计120㎡住宅，"
    "需要兼顾感统训练、父母休息、普通生活秩序和安全边界。请先帮我重构需求。"
)
WHEELCHAIR_HOME_PROMPT = (
    "一位轮椅使用者希望重新设计90㎡住宅，包含独立起居、洗浴安全、厨房操作、转弯半径、"
    "收纳可达和家人陪伴，请先帮我重构需求。"
)
BLENDED_FAMILY_HOME_PROMPT = (
    "一个再婚家庭希望重新设计160㎡住宅，包含无血缘青春期孩子、公共交流区、绝对隐私、"
    "独立性、冲突缓冲和心理安全边界，请先帮我重构需求。"
)
RURAL_CHILDREN_CENTER_PROMPT = (
    "农村老民居计划改造为社区儿童活动中心，包含图书阅读、手作课堂、家长等候和安全看护，"
    "请先帮我重构需求。"
)
RURAL_GUESTHOUSE_PROMPT = (
    "农村老民居计划改造为小型民宿，包含客房、早餐、公共客厅、在地文化体验和运营维护，"
    "请先帮我重构需求。"
)
ECOMMERCE_LIVE_STUDIO_PROMPT = (
    "一家跨境电商公司计划打造直播基地，包含选品展示、主播间、运营中控、样品仓和短视频拍摄区，"
    "请提出完整设计框架。"
)
FOOD_STYLING_STUDIO_PROMPT = (
    "一位美食博主希望打造甜品摆盘与餐具布景短视频拍摄区，"
    "主要用于成品展示、桌面布景、补光和收音，请先帮我重构需求。"
)
PODCAST_RECORDING_STUDIO_PROMPT = (
    "一家知识播客团队希望打造录音室，包含双人访谈、远程连线、声学隔音、导播控制、"
    "设备走线和后期剪辑，请先帮我重构需求。"
)
ESPORTS_LIVE_TRAINING_ROOM_PROMPT = (
    "一个电竞俱乐部希望打造直播训练间，包含选手训练、赛事直播、隔音、灯光、设备散热、"
    "战术复盘和粉丝互动，请先帮我重构需求。"
)
HOSPICE_WARD_PROMPT = (
    "一家医院希望改造临终关怀病房，兼顾患者尊严、家属陪伴、医护观察、安静休息和感染控制，"
    "请先帮我重构需求。"
)
DENTAL_CLINIC_PROMPT = (
    "一家牙科诊所希望改造空间，包含前台接待、候诊、诊疗椅、消毒室、拍片室和儿童安抚，"
    "请先帮我重构需求。"
)
MATERNITY_CENTER_PROMPT = (
    "一家月子中心希望改造公共区和护理房，包含产妇休息、婴儿护理、家属探访、营养餐配送和护士站，"
    "请先帮我重构需求。"
)
REHABILITATION_CENTER_PROMPT = (
    "一家康复中心希望改造训练区，包含评估室、物理治疗、器械训练、家属等候和无障碍动线，"
    "请先帮我重构需求。"
)
DENTAL_REGISTRY_TRIGGER_PROMPT = (
    "一家医疗诊所希望改造种植牙手术间，包含接诊、洁牙区、器械清洗和影像检查，"
    "请先帮我重构需求。"
)
MATERNITY_REGISTRY_TRIGGER_PROMPT = (
    "一家护理机构希望设置产康房，包含哺乳指导、亲属会客、餐食送达和恢复休息，"
    "请先帮我重构需求。"
)
REHAB_REGISTRY_TRIGGER_PROMPT = (
    "一家医院康复科希望改造训练空间，包含步态训练、作业治疗、助行训练和陪同等候，"
    "请先帮我重构需求。"
)
TECH_HEADQUARTERS_PROMPT = (
    "一家科技公司准备改造总部办公空间，包含研发团队、产品会议、客户接待、员工休息和品牌展示，"
    "希望提升协作效率和组织文化表达，请先帮我重构需求。"
)
URBAN_RENEWAL_PROMPT = (
    "一个老旧街区更新项目，需要兼顾原住民生活、社区商业、公共活动、历史界面保留和分期实施，"
    "请先帮我重构需求。"
)
COLLECTION_MUSEUM_PROMPT = (
    "一位收藏家希望打造球鞋博物馆，包含限量藏品展示、恒温恒湿保护、品牌历史叙事、公众参观和会员活动，"
    "请先帮我重构需求。"
)
REGISTRY_COLLECTION_MUSEUM_PROMPT = (
    "一个潮流品牌希望打造珍藏展厅，包含限量鞋款保护、品牌时间线、公众参观和会员活动，"
    "请先帮我重构需求。"
)
BRAND_EXPERIENCE_HISTORIC_DISTRICT_PROMPT = (
    "成都历史街区里的一家汽车品牌体验店，需要将城市记忆转译为品牌空间，"
    "请先帮我重构需求。"
)
BRAND_EXPERIENCE_HISTORIC_DISTRICT_ADVICE_PROMPT = (
    "成都历史街区里的一家汽车品牌体验店，需要将城市记忆转译为品牌空间，"
    "给出建议。"
)
REGISTRY_URBAN_RENEWAL_PROMPT = (
    "一个片区焕新项目，需要兼顾在地生活、公共活动、渐进运营和长期维护，"
    "请先帮我重构需求。"
)
REGISTRY_WORKPLACE_PROMPT = (
    "一家企业希望打造企业协作枢纽空间项目，包含研发小组、项目讨论、客户来访和团队恢复，"
    "请先帮我重构需求。"
)
REGISTRY_HEALTHCARE_PROMPT = (
    "一个安宁疗护单元空间项目，需要兼顾临别陪伴、护理观察、家属停留和安静恢复，"
    "请提出完整设计框架，并先帮我重构需求。"
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


class SequentialFakeLLM:
    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.prompts: list[str] = []

    def invoke(self, prompt: str):
        self.prompts.append(prompt)
        if not self.responses:
            raise AssertionError("No fake LLM responses left")
        return type("FakeResponse", (), {"content": self.responses.pop(0)})()


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
    assert "{owner_profile}" not in plan["task_reframe"]
    assert "设计师" in plan["task_reframe"]
    assert plan["brief_handoff_slots"]["fragment_source"] == "registry:life_identity_specialties.returning_home_residence"
    assert plan["brief_handoff_slots"]["owner_profile"]


def test_commercial_prompt_gets_different_structure_than_life_identity_prompt():
    rural = _blueprint(RURAL_HOME_PROMPT)
    cafe = _blueprint(CAFE_PROMPT)

    assert cafe["archetype"]["primary"] == "commercial_operation"
    assert cafe["archetype"]["primary"] != rural["archetype"]["primary"]
    cafe_titles = [section["title"] for section in cafe["sections"]]
    rural_titles = [section["title"] for section in rural["sections"]]
    assert "经营变量" in cafe_titles
    assert "商业成立方式" in cafe_titles
    assert "身份与生活结构" not in cafe_titles
    assert "经营变量" not in rural_titles
    assert any("翻台" in item or "外带" in item for section in cafe["sections"] for item in section.get("items", []))


def test_food_beverage_operation_blueprint_is_loaded_from_registry():
    plan = _blueprint(CAFE_PROMPT)

    assert plan["brief_handoff_slots"]["fragment_source"] == "registry:commercial_specialties.food_beverage_operation"


def test_retail_flagship_commercial_plan_does_not_use_dining_takeaway_logic():
    plan = _blueprint(FRAGRANCE_FLAGSHIP_PROMPT)
    rendered = _reply(FRAGRANCE_FLAGSHIP_PROMPT)

    assert plan["archetype"]["primary"] == "commercial_operation"
    assert plan["brief_handoff_slots"]["fragment_source"] == "registry:commercial_specialties.retail_brand_conversion"
    assert any(term in rendered for term in ("品牌", "转化", "试闻", "会员"))
    assert "翻台" not in rendered
    assert "外带" not in rendered
    assert "堂食" not in rendered
    assert "吧台" not in rendered
    assert "出品" not in rendered


def test_restaurant_naming_prompt_does_not_use_dining_efficiency_logic():
    plan = _blueprint(RESTAURANT_NAMING_PROMPT)
    rendered = _reply(RESTAURANT_NAMING_PROMPT)

    assert plan["archetype"]["primary"] == "commercial_operation"
    assert plan["brief_handoff_slots"]["fragment_source"] == "registry:commercial_specialties.naming_language"
    assert any(term in rendered for term in ("命名", "文化", "语言"))
    assert "翻台" not in rendered
    assert "外带" not in rendered
    assert "堂食" not in rendered
    assert "吧台" not in rendered
    assert "出品" not in rendered


def test_fine_dining_restaurant_does_not_use_quick_service_efficiency_logic():
    plan = _blueprint(FINE_DINING_RESTAURANT_PROMPT)
    rendered = _reply(FINE_DINING_RESTAURANT_PROMPT)

    assert plan["archetype"]["primary"] == "commercial_operation"
    assert plan["brief_handoff_slots"]["fragment_source"] == "registry:commercial_specialties.dining_hospitality_experience"
    assert any(term in rendered for term in ("品牌", "宴请", "包房", "茶室", "服务"))
    assert "翻台" not in rendered
    assert "外带" not in rendered
    assert "堂食" not in rendered
    assert "吧台" not in rendered
    assert "出品" not in rendered


def test_hotel_lobby_is_hospitality_operation_not_public_exhibition():
    plan = _blueprint(HOTEL_LOBBY_PROMPT)
    rendered = _reply(HOTEL_LOBBY_PROMPT)

    assert plan["archetype"]["primary"] == "commercial_operation"
    assert any(term in rendered for term in ("入住接待", "行李寄存", "早餐外摆", "商务等候", "酒店"))
    assert "展示馆" not in rendered
    assert "观众" not in rendered
    assert "政府访客" not in rendered
    assert "互动装置" not in rendered


def test_long_term_apartment_amenity_is_operational_shared_living_not_family_home():
    plan = _blueprint(LONG_TERM_APARTMENT_AMENITY_PROMPT)
    rendered = _reply(LONG_TERM_APARTMENT_AMENITY_PROMPT)

    assert plan["archetype"]["primary"] == "commercial_operation"
    assert any(term in rendered for term in ("长租公寓", "共享厨房", "健身", "社交活动", "快递收纳", "运营维护"))
    assert "家庭成员" not in rendered
    assert "住宅风格" not in rendered
    assert "训练" not in rendered
    assert "照护" not in rendered


@pytest.mark.parametrize(
    ("prompt", "fragment_id"),
    [
        (HOTEL_LOBBY_PROMPT, "hotel_lobby"),
        (LONG_TERM_APARTMENT_AMENITY_PROMPT, "long_term_apartment_amenity"),
    ],
)
def test_hospitality_specialized_blueprints_are_loaded_from_registry(prompt, fragment_id):
    plan = _blueprint(prompt)

    assert plan["brief_handoff_slots"]["fragment_source"] == f"registry:hospitality_specialties.{fragment_id}"


def test_popup_brand_experience_store_is_not_treated_as_public_cultural_project():
    plan = _blueprint(POPUP_BRAND_EXPERIENCE_PROMPT)
    rendered = _reply(POPUP_BRAND_EXPERIENCE_PROMPT)

    assert plan["archetype"]["primary"] == "commercial_operation"
    assert any(term in rendered for term in ("品牌", "快闪", "会员", "销售", "社交"))
    assert "公共文化体验空间" not in rendered
    assert "亲子" not in rendered
    assert "科普" not in rendered
    assert "农产品" not in rendered


def test_automated_retail_uses_registry_fragment_without_dining_efficiency_logic():
    plan = _blueprint(AUTOMATED_RETAIL_PROMPT)
    rendered = _reply(AUTOMATED_RETAIL_PROMPT)

    assert plan["archetype"]["primary"] == "commercial_operation"
    assert plan["brief_handoff_slots"]["fragment_source"] == "registry:commercial_specialties.automated_retail"
    assert "无人零售运营链路" in [section["title"] for section in plan["sections"]]
    assert any(
        term in rendered
        for term in ("自助结算", "货架补货", "冷柜监控", "防损摄像头", "夜间运营", "会员复购")
    )
    assert "翻台" not in rendered
    assert "堂食" not in rendered
    assert "吧台" not in rendered


def test_family_restaurant_is_commercial_not_public_cultural_or_life_identity():
    plan = _blueprint(FAMILY_RESTAURANT_PROMPT)
    rendered = _reply(FAMILY_RESTAURANT_PROMPT)

    assert plan["archetype"]["primary"] == "commercial_operation"
    assert any(term in rendered for term in ("餐厅", "儿童", "家庭", "生日", "会员"))
    assert "公共文化体验空间" not in rendered
    assert "科普" not in rendered
    assert "原乡" not in rendered
    assert "返乡" not in rendered
    assert "作品化住宅" not in rendered


def test_residential_brand_showroom_is_commercial_not_life_identity():
    plan = _blueprint(RESIDENTIAL_BRAND_SHOWROOM_PROMPT)
    rendered = _reply(RESIDENTIAL_BRAND_SHOWROOM_PROMPT)

    assert plan["archetype"]["primary"] == "commercial_operation"
    assert any(term in rendered for term in ("住宅品牌", "样板间", "材料体验", "销售", "会员"))
    assert "原乡" not in rendered
    assert "返乡" not in rendered
    assert "作品化住宅" not in rendered
    assert "家族" not in rendered


def test_retirement_community_service_uses_healthcare_care_not_public_culture_or_life_identity():
    plan = _blueprint(RETIREMENT_COMMUNITY_SERVICE_PROMPT)
    rendered = _reply(RETIREMENT_COMMUNITY_SERVICE_PROMPT)

    assert plan["archetype"]["primary"] == "healthcare_care"
    assert any(term in rendered for term in ("日间照料", "活动教室", "社区食堂", "医护", "照护"))
    assert "公共文化体验空间" not in rendered
    assert "科普" not in rendered
    assert "亲子" not in rendered
    assert "农产品" not in rendered
    assert "原乡" not in rendered
    assert "返乡" not in rendered


def test_family_enterprise_brand_exhibition_is_not_treated_as_headquarters_office():
    plan = _blueprint(FAMILY_ENTERPRISE_BRAND_EXHIBITION_PROMPT)
    rendered = _reply(FAMILY_ENTERPRISE_BRAND_EXHIBITION_PROMPT)

    assert plan["archetype"]["primary"] == "commercial_operation"
    assert any(term in rendered for term in ("品牌", "企业历史", "产品展示", "客户接待"))
    assert "总部办公" not in rendered
    assert "研发" not in rendered
    assert "工位" not in rendered
    assert "员工休息" not in rendered


def test_law_office_is_workplace_not_life_identity():
    plan = _blueprint(LAW_OFFICE_PROMPT)
    rendered = _reply(LAW_OFFICE_PROMPT)

    assert plan["archetype"]["primary"] == "workplace_headquarters"
    assert "专业服务秩序" in [section["title"] for section in plan["sections"]]
    assert any(term in rendered for term in ("律师", "客户会谈", "档案保密", "合伙人会议", "团队协作"))
    assert "家庭成员" not in rendered
    assert "住宅" not in rendered
    assert "训练" not in rendered
    assert "照护" not in rendered


def test_counseling_office_uses_professional_service_workplace_not_headquarters_template():
    plan = _blueprint(COUNSELING_OFFICE_PROMPT)
    rendered = _reply(COUNSELING_OFFICE_PROMPT)

    assert plan["archetype"]["primary"] == "workplace_headquarters"
    assert any(term in rendered for term in ("咨询室", "团体活动", "档案保密", "咨询师恢复"))
    assert "总部办公" not in rendered
    assert "研发" not in rendered
    assert "产品会议" not in rendered
    assert "品牌展示" not in rendered


@pytest.mark.parametrize(
    ("prompt", "fragment_source"),
    [
        (LAW_OFFICE_PROMPT, "registry:workplace_specialties.professional_service"),
        (COUNSELING_OFFICE_PROMPT, "registry:workplace_specialties.professional_service"),
        (WHEELCHAIR_HOME_PROMPT, "registry:life_identity_specialties.accessible_residence"),
        (BLENDED_FAMILY_HOME_PROMPT, "registry:life_identity_specialties.blended_family_privacy"),
        (ARCHIVE_LIBRARY_PROMPT, "registry:technical_specialties.archive_preservation"),
        (DOLBY_CINEMA_PROMPT, "registry:technical_specialties.acoustic_constraint"),
        (COASTAL_TIMBER_GUESTHOUSE_PROMPT, "registry:technical_specialties.coastal_resilience"),
        (EXTREME_COLD_OXYGEN_GUESTHOUSE_PROMPT, "registry:technical_specialties.life_support_resilience"),
        (POWER_INFRASTRUCTURE_ROOM_PROMPT, "registry:technical_specialties.power_infrastructure"),
        (BIOTECH_LAB_PROMPT, "registry:technical_specialties.laboratory_constraint"),
        (COMMUNITY_LIBRARY_READING_PROMPT, "registry:public_cultural_specialties.library_reading"),
    ],
)
def test_core_specialized_blueprints_are_loaded_from_registry(prompt, fragment_source):
    plan = _blueprint(prompt)

    assert plan["brief_handoff_slots"]["fragment_source"] == fragment_source


def test_style_and_hard_constraint_prompts_select_different_module_sets():
    style = _blueprint(STYLE_PROMPT)
    hard_constraint = _blueprint(HARD_CONSTRAINT_PROMPT)

    assert style["archetype"]["primary"] == "style_semantics"
    assert hard_constraint["archetype"]["primary"] == "hard_constraint"
    assert style["brief_handoff_slots"]["fragment_source"] == "registry:primary_archetypes.style_semantics"
    assert "语义边界" in [section["title"] for section in style["sections"]]
    assert "表达禁区" in [section["title"] for section in style["sections"]]
    assert "隐藏开关" in [section["title"] for section in hard_constraint["sections"]]
    assert hard_constraint["brief_handoff_slots"]["fragment_source"] == "registry:technical_specialties.cold_storage_constraint"


def test_wabi_sabi_guesthouse_style_uses_specific_style_fragment_not_tea_template():
    plan = _blueprint(WABI_SABI_GUESTHOUSE_STYLE_PROMPT)
    rendered = _reply(WABI_SABI_GUESTHOUSE_STYLE_PROMPT)

    assert plan["archetype"]["primary"] == "style_semantics"
    assert plan["brief_handoff_slots"]["fragment_source"] == "registry:style_specialties.wabi_sabi_relaxation"
    assert "松弛感边界" in [section["title"] for section in plan["sections"]]
    assert any(term in rendered for term in ("侘寂", "松弛感", "民宿", "入住等候", "材料耐维护"))
    assert "东方感" not in rendered
    assert "茶空间" not in rendered
    assert "中式符号" not in rendered


def test_deep_research_prompt_is_routed_without_pretending_to_complete_evidence():
    plan = _blueprint(DEEP_RESEARCH_PROMPT)

    assert plan["routing"]["target"] == "deep_research"
    assert "深度研究" in plan["routing"]["label"]
    assert any("证据" in item for section in plan["sections"] for item in section.get("items", []))


def test_cultural_research_prompt_does_not_inject_yaji_club_context_for_other_topics():
    plan = _blueprint(LINGNAN_BOOKSTORE_RESEARCH_PROMPT)
    rendered = _reply(LINGNAN_BOOKSTORE_RESEARCH_PROMPT)

    assert plan["archetype"]["primary"] == "cultural_research"
    assert "研究对象边界" in [section["title"] for section in plan["sections"]]
    assert "岭南骑楼文化" in plan["task_reframe"]
    assert "社区书店空间" in plan["task_reframe"]
    assert any(term in rendered for term in ("岭南", "骑楼", "社区书店"))
    assert "雅集" not in rendered
    assert "会所" not in rendered


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


def test_real_exhibition_project_with_new_industry_terms_enters_demand_reconstruction():
    service = DemandReconstructionService()

    assert service.should_handle(HYDROGEN_EXHIBITION_PROMPT) is True
    plan = _blueprint(HYDROGEN_EXHIBITION_PROMPT)

    assert plan["archetype"]["primary"] == "public_cultural_experience"
    assert plan["brief_handoff_slots"]["fragment_source"] == "registry:public_cultural_specialties.generic_exhibition"
    assert "公共成立边界" in [section["title"] for section in plan["sections"]]
    rendered = _reply(HYDROGEN_EXHIBITION_PROMPT)
    assert "需求重构" in rendered
    assert "展陈" in rendered or "互动" in rendered or "公众" in rendered
    assert "亲子厨房" not in rendered
    assert "农产品" not in rendered
    assert "咖啡区" not in rendered
    assert "崇明岛" not in rendered
    assert "昆曲" not in rendered
    assert "练声" not in rendered
    assert "老宅" not in rendered


def test_organic_exhibition_without_farm_anchors_does_not_leak_farm_fragments():
    plan = _blueprint(ORGANIC_EXHIBITION_PROMPT)
    rendered = _reply(ORGANIC_EXHIBITION_PROMPT)

    assert plan["archetype"]["primary"] == "public_cultural_experience"
    assert "有机" in rendered or "可持续" in rendered
    assert "亲子厨房" not in rendered
    assert "农产品" not in rendered
    assert "咖啡区" not in rendered
    assert "崇明岛" not in rendered
    assert "农事" not in rendered


def test_public_cultural_material_topic_terms_are_loaded_from_registry():
    prompt = (
        "一家新型建材企业希望打造循环材质展示馆，面向客户、设计师和公众开放，"
        "请先帮我重构需求。"
    )
    plan = _blueprint(prompt)
    rendered = _reply(prompt)

    assert plan["archetype"]["primary"] == "public_cultural_experience"
    assert "循环材质" in rendered or "材料主题" in rendered
    assert "可验证的展陈证据" in rendered
    assert "农产品" not in rendered
    assert "亲子厨房" not in rendered


def test_archive_project_with_environmental_constraints_enters_demand_reconstruction():
    service = DemandReconstructionService()

    assert service.should_handle(ARCHIVE_LIBRARY_PROMPT) is True
    plan = _blueprint(ARCHIVE_LIBRARY_PROMPT)

    assert plan["archetype"]["primary"] == "hard_constraint"
    assert plan["brief_handoff_slots"]["fragment_source"] == "registry:technical_specialties.archive_preservation"
    assert "档案保护链路" in [section["title"] for section in plan["sections"]]
    rendered = _reply(ARCHIVE_LIBRARY_PROMPT)
    assert "需求重构" in rendered
    assert "恒温恒湿" in rendered or "防火" in rendered or "安防" in rendered
    assert "公众查阅" in rendered or "库区" in rendered
    assert "SKU" not in rendered
    assert "补货" not in rendered
    assert "冷藏柜" not in rendered


def test_acoustic_cinema_constraint_uses_registry_not_cold_storage_template():
    plan = _blueprint(DOLBY_CINEMA_PROMPT)
    rendered = _reply(DOLBY_CINEMA_PROMPT)

    assert plan["archetype"]["primary"] == "hard_constraint"
    assert plan["brief_handoff_slots"]["fragment_source"] == "registry:technical_specialties.acoustic_constraint"
    assert "声学链路" in [section["title"] for section in plan["sections"]]
    assert any(term in rendered for term in ("杜比", "隔声", "吸声", "低频", "设备散热"))
    assert "冷藏柜" not in rendered
    assert "SKU" not in rendered
    assert "补货" not in rendered


def test_coastal_timber_guesthouse_uses_resilience_constraint_not_generic_technical_template():
    plan = _blueprint(COASTAL_TIMBER_GUESTHOUSE_PROMPT)
    rendered = _reply(COASTAL_TIMBER_GUESTHOUSE_PROMPT)

    assert plan["archetype"]["primary"] == "hard_constraint"
    assert plan["brief_handoff_slots"]["fragment_source"] == "registry:technical_specialties.coastal_resilience"
    assert "滨海韧性链路" in [section["title"] for section in plan["sections"]]
    assert any(term in rendered for term in ("盐雾", "防腐", "台风", "抗风", "木结构", "长期维护"))
    assert "冷藏柜" not in rendered
    assert "SKU" not in rendered
    assert "补货" not in rendered


def test_extreme_cold_oxygen_guesthouse_uses_life_support_resilience_not_generic_template():
    plan = _blueprint(EXTREME_COLD_OXYGEN_GUESTHOUSE_PROMPT)
    rendered = _reply(EXTREME_COLD_OXYGEN_GUESTHOUSE_PROMPT)

    assert plan["archetype"]["primary"] == "hard_constraint"
    assert plan["brief_handoff_slots"]["fragment_source"] == "registry:technical_specialties.life_support_resilience"
    assert "生命支持链路" in [section["title"] for section in plan["sections"]]
    assert any(term in rendered for term in ("供氧", "新风", "保温", "应急电力", "避难冗余", "低温运营"))
    assert "冷藏柜" not in rendered
    assert "SKU" not in rendered
    assert "补货" not in rendered


def test_power_infrastructure_room_uses_registry_fragment_without_handwritten_branch():
    plan = _blueprint(POWER_INFRASTRUCTURE_ROOM_PROMPT)
    rendered = _reply(POWER_INFRASTRUCTURE_ROOM_PROMPT)

    assert plan["archetype"]["primary"] == "hard_constraint"
    assert plan["brief_handoff_slots"]["fragment_source"] == "registry:technical_specialties.power_infrastructure"
    assert "电力与弱电链路" in [section["title"] for section in plan["sections"]]
    assert any(term in rendered for term in ("UPS", "电力容量", "机柜散热", "网络布线", "检修通道", "消防联动"))
    assert "冷藏柜" not in rendered
    assert "SKU" not in rendered
    assert "补货" not in rendered


def test_biotech_lab_uses_laboratory_constraint_chain_not_generic_technical_template():
    plan = _blueprint(BIOTECH_LAB_PROMPT)
    rendered = _reply(BIOTECH_LAB_PROMPT)

    assert plan["archetype"]["primary"] == "hard_constraint"
    assert any(term in rendered for term in ("样本接收", "洁净实验", "设备维护", "人员更衣", "废弃物处理"))
    assert "实验链路" in [section["title"] for section in plan["sections"]]
    assert "冷藏柜" not in rendered
    assert "SKU" not in rendered
    assert "补货" not in rendered


def test_methodology_only_prompt_is_not_taken_by_demand_reconstruction():
    service = DemandReconstructionService()

    assert service.should_handle(METHODOLOGY_ONLY_PROMPT) is False


def test_spatial_research_method_prompt_without_project_anchor_is_not_taken_by_demand_reconstruction():
    service = DemandReconstructionService()

    assert service.should_handle(SPATIAL_RESEARCH_METHOD_PROMPT) is False


def test_competition_strategy_prompt_is_not_taken_by_demand_reconstruction():
    service = DemandReconstructionService()

    assert service.should_handle(COMPETITION_STRATEGY_PROMPT) is False


def test_pure_naming_copy_prompt_is_not_taken_by_demand_reconstruction():
    service = DemandReconstructionService()

    assert service.should_handle(PURE_NAMING_COPY_PROMPT) is False


def test_reference_case_prompt_is_not_taken_by_demand_reconstruction():
    service = DemandReconstructionService()

    assert service.should_handle(REFERENCE_CASE_PROMPT) is False


def test_wheelchair_home_uses_accessible_residence_not_generic_residential_life_order():
    plan = _blueprint(WHEELCHAIR_HOME_PROMPT)
    rendered = _reply(WHEELCHAIR_HOME_PROMPT)

    assert plan["archetype"]["primary"] == "life_identity"
    assert plan["brief_handoff_slots"]["fragment_source"] == "registry:life_identity_specialties.accessible_residence"
    assert "无障碍生活链路" in [section["title"] for section in plan["sections"]]
    assert any(term in rendered for term in ("轮椅", "独立起居", "洗浴安全", "转弯半径", "收纳可达"))
    assert "儿童支持" not in rendered
    assert "原乡" not in rendered


def test_blended_family_home_uses_registry_fragment_without_handwritten_branch():
    plan = _blueprint(BLENDED_FAMILY_HOME_PROMPT)
    rendered = _reply(BLENDED_FAMILY_HOME_PROMPT)

    assert plan["archetype"]["primary"] == "life_identity"
    assert plan["brief_handoff_slots"]["fragment_source"] == "registry:life_identity_specialties.blended_family_privacy"
    assert "共居边界" in [section["title"] for section in plan["sections"]]
    assert any(term in rendered for term in ("再婚家庭", "无血缘", "青春期", "绝对隐私", "冲突缓冲"))
    assert "原乡" not in rendered
    assert "轮椅" not in rendered


def test_healthcare_care_project_gets_specific_blueprint_instead_of_generic_fallback():
    plan = _blueprint(HOSPICE_WARD_PROMPT)
    rendered = _reply(HOSPICE_WARD_PROMPT)

    assert any(term in rendered for term in ("医疗", "照护", "尊严", "医护", "感染控制"))
    assert "先抓变量" not in [section["title"] for section in plan["sections"]]
    assert "目标优先级" not in plan["key_forks"]
    assert "使用者结构" not in plan["key_forks"]


def test_dental_clinic_uses_diagnosis_treatment_flow_not_hospice_ward_template():
    plan = _blueprint(DENTAL_CLINIC_PROMPT)
    rendered = _reply(DENTAL_CLINIC_PROMPT)

    assert plan["archetype"]["primary"] == "healthcare_care"
    assert "诊疗链路" in [section["title"] for section in plan["sections"]]
    assert any(term in rendered for term in ("前台接待", "候诊", "诊疗椅", "消毒室", "拍片室", "儿童安抚"))
    assert "临终" not in rendered
    assert "病房" not in rendered
    assert "过夜陪护" not in rendered


def test_maternity_center_uses_postpartum_care_flow_not_hospice_ward_template():
    plan = _blueprint(MATERNITY_CENTER_PROMPT)
    rendered = _reply(MATERNITY_CENTER_PROMPT)

    assert plan["archetype"]["primary"] == "healthcare_care"
    assert "母婴护理链路" in [section["title"] for section in plan["sections"]]
    assert any(term in rendered for term in ("产妇休息", "婴儿护理", "家属探访", "营养餐配送", "护士站"))
    assert "临终" not in rendered
    assert "病房" not in rendered
    assert "过夜陪护" not in rendered


def test_rehabilitation_center_uses_rehab_training_flow_not_generic_hard_constraint():
    plan = _blueprint(REHABILITATION_CENTER_PROMPT)
    rendered = _reply(REHABILITATION_CENTER_PROMPT)

    assert plan["archetype"]["primary"] == "healthcare_care"
    assert "康复训练链路" in [section["title"] for section in plan["sections"]]
    assert any(term in rendered for term in ("评估室", "物理治疗", "器械训练", "家属等候", "无障碍动线"))
    assert "技术成立边界" not in [section["title"] for section in plan["sections"]]
    assert "冷藏柜" not in rendered
    assert "SKU" not in rendered
    assert "补货" not in rendered


@pytest.mark.parametrize(
    ("prompt", "fragment_id"),
    [
        (DENTAL_CLINIC_PROMPT, "dental_clinic"),
        (MATERNITY_CENTER_PROMPT, "maternity_center"),
        (REHABILITATION_CENTER_PROMPT, "rehabilitation_center"),
    ],
)
def test_healthcare_specialized_blueprints_are_loaded_from_registry(prompt, fragment_id):
    plan = _blueprint(prompt)

    assert plan["brief_handoff_slots"]["fragment_source"] == f"registry:healthcare_specialties.{fragment_id}"


@pytest.mark.parametrize(
    ("prompt", "fragment_id"),
    [
        (DENTAL_REGISTRY_TRIGGER_PROMPT, "dental_clinic"),
        (MATERNITY_REGISTRY_TRIGGER_PROMPT, "maternity_center"),
        (REHAB_REGISTRY_TRIGGER_PROMPT, "rehabilitation_center"),
    ],
)
def test_healthcare_specialty_trigger_terms_are_loaded_from_registry(prompt, fragment_id):
    plan = _blueprint(prompt)

    assert plan["archetype"]["primary"] == "healthcare_care"
    assert plan["brief_handoff_slots"]["fragment_source"] == f"registry:healthcare_specialties.{fragment_id}"


def test_workplace_headquarters_project_gets_specific_blueprint_instead_of_generic_fallback():
    plan = _blueprint(TECH_HEADQUARTERS_PROMPT)
    rendered = _reply(TECH_HEADQUARTERS_PROMPT)

    assert "组织协作" in [section["title"] for section in plan["sections"]]
    assert "访客与员工边界" in [section["title"] for section in plan["sections"]]
    assert any(term in rendered for term in ("组织", "协作", "会议", "客户接待", "品牌展示"))
    assert "先抓变量" not in [section["title"] for section in plan["sections"]]
    assert "目标优先级" not in plan["key_forks"]
    assert "使用者结构" not in plan["key_forks"]


@pytest.mark.parametrize("prompt", [TECH_HEADQUARTERS_PROMPT, REGISTRY_WORKPLACE_PROMPT])
def test_workplace_headquarters_blueprint_is_loaded_from_registry(prompt):
    plan = _blueprint(prompt)

    assert plan["brief_handoff_slots"]["fragment_source"] == "registry:workplace_specialties.headquarters"


def test_urban_renewal_project_gets_specific_blueprint_instead_of_generic_fallback():
    plan = _blueprint(URBAN_RENEWAL_PROMPT)
    rendered = _reply(URBAN_RENEWAL_PROMPT)

    assert plan["archetype"]["primary"] == "urban_renewal"
    assert "利益相关方" in [section["title"] for section in plan["sections"]]
    assert "分期实施" in [section["title"] for section in plan["sections"]]
    assert any(term in rendered for term in ("原住民", "社区商业", "公共活动", "历史界面", "分期"))
    assert "先抓变量" not in [section["title"] for section in plan["sections"]]
    assert "目标优先级" not in plan["key_forks"]


def test_collection_museum_project_gets_collection_specific_blueprint():
    plan = _blueprint(COLLECTION_MUSEUM_PROMPT)
    rendered = _reply(COLLECTION_MUSEUM_PROMPT)

    assert plan["archetype"]["primary"] == "collection_museum"
    assert "hard_constraint" in plan["archetype"]["secondary"]
    assert "藏品保护" in [section["title"] for section in plan["sections"]]
    assert "展陈叙事" in [section["title"] for section in plan["sections"]]
    assert any(term in rendered for term in ("限量藏品", "恒温恒湿", "品牌历史", "公众参观", "会员活动"))
    assert "亲子厨房" not in rendered
    assert "农产品" not in rendered
    assert "练声" not in rendered
    assert "翻台" not in rendered
    assert "外带" not in rendered


def test_collection_museum_trigger_terms_are_loaded_from_registry():
    plan = _blueprint(REGISTRY_COLLECTION_MUSEUM_PROMPT)

    assert "藏品保护" in [section["title"] for section in plan["sections"]]
    assert "展陈叙事" in [section["title"] for section in plan["sections"]]
    assert plan["brief_handoff_slots"]["core_tension"] == "藏品保护、展陈叙事、公众参观和会员运营之间的张力"


def test_other_blueprint_override_terms_are_loaded_from_registry():
    urban = _blueprint(REGISTRY_URBAN_RENEWAL_PROMPT)
    workplace = _blueprint(REGISTRY_WORKPLACE_PROMPT)
    healthcare = _blueprint(REGISTRY_HEALTHCARE_PROMPT)

    assert "利益相关方" in [section["title"] for section in urban["sections"]]
    assert "组织协作" in [section["title"] for section in workplace["sections"]]
    assert "照护秩序" in [section["title"] for section in healthcare["sections"]]


@pytest.mark.parametrize(
    ("prompt", "fragment_source"),
    [
        (COLLECTION_MUSEUM_PROMPT, "registry:public_cultural_specialties.collection_museum"),
        (REGISTRY_COLLECTION_MUSEUM_PROMPT, "registry:public_cultural_specialties.collection_museum"),
        (URBAN_RENEWAL_PROMPT, "registry:urban_renewal_specialties.district_renewal"),
        (REGISTRY_URBAN_RENEWAL_PROMPT, "registry:urban_renewal_specialties.district_renewal"),
    ],
)
def test_remaining_prioritized_blueprints_are_loaded_from_registry(prompt, fragment_source):
    plan = _blueprint(prompt)

    assert plan["brief_handoff_slots"]["fragment_source"] == fragment_source


@pytest.mark.parametrize(
    ("prompt", "expected_candidate"),
    [
        (URBAN_RENEWAL_PROMPT, "urban_renewal"),
        (REGISTRY_URBAN_RENEWAL_PROMPT, "urban_renewal"),
        (COLLECTION_MUSEUM_PROMPT, "collection_museum"),
        (REGISTRY_COLLECTION_MUSEUM_PROMPT, "collection_museum"),
    ],
)
def test_prioritized_blueprints_enter_unified_semantic_candidate_set(prompt, expected_candidate):
    context = DemandReconstructionContextAdapter().build(prompt)

    candidate_ids = [item["id"] for item in context["semantic_candidate_set"]]
    assert expected_candidate in candidate_ids
    assert context["archetype"]["primary"] == expected_candidate


@pytest.mark.parametrize(
    "prompt",
    [
        URBAN_RENEWAL_PROMPT,
        COLLECTION_MUSEUM_PROMPT,
        REGISTRY_URBAN_RENEWAL_PROMPT,
        REGISTRY_COLLECTION_MUSEUM_PROMPT,
    ],
)
def test_registry_blueprint_fragments_do_not_leak_format_placeholders(prompt):
    rendered = _reply(prompt)

    assert "{" not in rendered
    assert "}" not in rendered


def test_non_returning_family_home_does_not_use_rural_home_identity_story():
    plan = _blueprint(AUTISM_FAMILY_HOME_PROMPT)
    rendered = _reply(AUTISM_FAMILY_HOME_PROMPT)

    assert plan["archetype"]["primary"] == "life_identity"
    assert "生活身份底盘" in [section["title"] for section in plan["sections"]]
    assert any(term in rendered for term in ("儿童", "家庭", "安全", "生活秩序", "感统"))
    assert "原乡" not in rendered
    assert "回乡" not in rendered
    assert "返乡" not in rendered
    assert "背井离乡" not in rendered
    assert "家族位置重排" not in rendered
    assert "作品化住宅" not in rendered


def test_children_support_terms_are_loaded_from_registry_for_residential_life_order():
    prompt = (
        "一个低龄使用者家庭希望重新设计120㎡住宅，"
        "需要兼顾感觉统合训练、父母休息、普通生活秩序和安全边界。请先帮我重构需求。"
    )
    plan = _blueprint(prompt)
    rendered = _reply(prompt)

    assert plan["archetype"]["primary"] == "life_identity"
    assert plan["brief_handoff_slots"]["fragment_source"] == "registry:life_identity_specialties.residential_child_support"
    assert "儿童支持、父母恢复和普通家庭生活之间的张力" == plan["brief_handoff_slots"]["core_tension"]
    assert "儿童" in rendered
    assert "父母" in rendered
    assert "训练" in rendered
    assert "原乡" not in rendered


def test_rural_public_children_center_does_not_use_returning_home_identity_story():
    plan = _blueprint(RURAL_CHILDREN_CENTER_PROMPT)
    rendered = _reply(RURAL_CHILDREN_CENTER_PROMPT)

    assert plan["archetype"]["primary"] == "public_cultural_experience"
    assert any(term in rendered for term in ("儿童", "社区", "活动", "安全"))
    assert "原乡" not in rendered
    assert "回乡" not in rendered
    assert "返乡" not in rendered
    assert "背井离乡" not in rendered
    assert "家族位置重排" not in rendered
    assert "作品化住宅" not in rendered


def test_rural_guesthouse_reuse_does_not_use_returning_home_identity_story():
    rendered = _reply(RURAL_GUESTHOUSE_PROMPT)

    assert any(term in rendered for term in ("民宿", "客房", "早餐", "运营", "维护"))
    assert "原乡" not in rendered
    assert "回乡" not in rendered
    assert "返乡" not in rendered
    assert "背井离乡" not in rendered
    assert "家族位置重排" not in rendered
    assert "作品化住宅" not in rendered


def test_media_kitchen_project_starts_with_demand_reconstruction_layer():
    prompt = (
        "一位美食作家兼KOL希望将厨房设计为“美食实验室”，既满足日常烹饪，"
        "也适合高质量拍摄与视频录制。请提出完整设计方案，包括操作动线优化、"
        "灯光布置系统、背景可替换模块与油烟控制机制。"
    )
    service = DemandReconstructionService()

    assert service.should_handle(prompt) is True
    result = service.handle_message(
        session={},
        user_message=prompt,
        in_response_to_card_id=None,
        selected_option_id=None,
    )

    assert result is not None
    assert result["dialogue_layer"] == "demand_reconstruction"
    assert result["guidance_card"]["card_type"] == "demand_reconstruction_blueprint"
    plan = result["demand_reconstruction_context"]["blueprint"]
    assert plan["archetype"]["primary"] == "media_production"
    assert plan["brief_handoff_slots"]["fragment_source"] == "registry:media_specialties.kitchen_media_lab"
    assert "场景切换机制" in [section["title"] for section in plan["sections"]]
    assert "拍摄工作流" in plan["brief_handoff_slots"]["recommended_brief_focus"]
    rendered = result["reply"] + str(result["guidance_card"])
    assert "老家建房" not in rendered
    assert "回乡" not in rendered
    assert "家族" not in rendered
    assert "作品化住宅" not in rendered


def test_ecommerce_live_studio_media_plan_does_not_use_kitchen_pollution_logic():
    plan = _blueprint(ECOMMERCE_LIVE_STUDIO_PROMPT)
    rendered = _reply(ECOMMERCE_LIVE_STUDIO_PROMPT)

    assert plan["archetype"]["primary"] == "media_production"
    assert plan["brief_handoff_slots"]["fragment_source"] == "registry:media_specialties.live_commerce_studio"
    assert "内容生产底盘" in [section["title"] for section in plan["sections"]]
    assert any(term in rendered for term in ("直播", "主播", "中控", "样品", "短视频"))
    assert "油烟" not in rendered
    assert "烹饪" not in rendered
    assert "厨房" not in rendered
    assert "菜系" not in rendered


def test_food_styling_media_plan_does_not_inject_heavy_cooking_pollution_logic():
    plan = _blueprint(FOOD_STYLING_STUDIO_PROMPT)
    rendered = _reply(FOOD_STYLING_STUDIO_PROMPT)

    assert plan["archetype"]["primary"] == "media_production"
    assert plan["brief_handoff_slots"]["fragment_source"] == "registry:media_specialties.food_styling_studio"
    assert any(term in rendered for term in ("摆盘", "布景", "补光", "收音", "拍摄"))
    assert "油烟" not in rendered
    assert "热炒" not in rendered
    assert "排风" not in rendered
    assert "新风" not in rendered
    assert "烹饪" not in rendered
    assert "做饭" not in rendered
    assert "备菜" not in rendered


def test_podcast_recording_studio_uses_audio_registry_fragment_not_live_commerce():
    plan = _blueprint(PODCAST_RECORDING_STUDIO_PROMPT)
    rendered = _reply(PODCAST_RECORDING_STUDIO_PROMPT)

    assert plan["archetype"]["primary"] == "media_production"
    assert plan["brief_handoff_slots"]["fragment_source"] == "registry:media_specialties.podcast_recording_studio"
    assert "录音工作流" in [section["title"] for section in plan["sections"]]
    assert any(term in rendered for term in ("播客", "录音", "双人访谈", "远程连线", "导播控制", "后期剪辑"))
    assert "主播" not in rendered
    assert "样品仓" not in rendered
    assert "选品展示" not in rendered
    assert "直播带货" not in rendered


def test_esports_live_training_room_uses_esports_media_fragment_not_generic_equipment():
    plan = _blueprint(ESPORTS_LIVE_TRAINING_ROOM_PROMPT)
    rendered = _reply(ESPORTS_LIVE_TRAINING_ROOM_PROMPT)

    assert plan["archetype"]["primary"] == "media_production"
    assert plan["brief_handoff_slots"]["fragment_source"] == "registry:media_specialties.esports_live_training_room"
    assert "训练直播协同" in [section["title"] for section in plan["sections"]]
    assert any(term in rendered for term in ("电竞", "选手训练", "赛事直播", "战术复盘", "粉丝互动"))
    assert "冷藏柜" not in rendered
    assert "样品仓" not in rendered
    assert "选品展示" not in rendered
    assert "直播带货" not in rendered


def test_citizen_farm_visitor_center_uses_public_cultural_experience_plan():
    result = DemandReconstructionService().handle_message(
        session={},
        user_message=CITIZEN_FARM_PROMPT,
        in_response_to_card_id=None,
        selected_option_id=None,
    )

    assert result is not None
    plan = result["demand_reconstruction_context"]["blueprint"]
    assert plan["archetype"]["primary"] == "public_cultural_experience"
    assert "公共体验" in [section["title"] for section in plan["sections"]]
    rendered = result["reply"] + str(result["guidance_card"])
    assert "亲子" in rendered
    assert "科普" in rendered
    assert "材料循环" in rendered
    assert "翻台" not in rendered
    assert "外带" not in rendered
    assert "堂食" not in rendered
    assert "坪效" not in rendered
    assert "摊贩" not in rendered


def test_generic_citizen_farm_without_chongming_anchor_does_not_leak_chongming_place_name():
    rendered = _reply(GENERIC_CITIZEN_FARM_PROMPT)

    assert "亲子" in rendered
    assert "农产品" in rendered
    assert "科普" in rendered
    assert "崇明岛" not in rendered


def test_farm_learning_center_without_product_anchor_does_not_inject_product_logistics():
    rendered = _reply(FARM_KITCHEN_CAFE_PROMPT)

    assert "亲子" in rendered
    assert "科普" in rendered
    assert "咖啡" in rendered
    assert "农产品" not in rendered
    assert "SKU" not in rendered
    assert "冷链" not in rendered
    assert "补货" not in rendered


def test_farm_learning_center_product_anchor_terms_are_loaded_from_registry():
    prompt = (
        "某市民农场访客中心，包含产地直供展示、亲子厨房、科普教育与咖啡区，"
        "请先帮我重构需求。"
    )
    rendered = _reply(prompt)

    assert "亲子" in rendered
    assert "科普" in rendered
    assert "农产品" in rendered
    assert "冷链" in rendered


@pytest.mark.parametrize(
    ("prompt", "fragment_source"),
    [
        (CITIZEN_FARM_PROMPT, "registry:public_cultural_specialties.farm_learning_center"),
        (FARM_KITCHEN_CAFE_PROMPT, "registry:public_cultural_specialties.farm_learning_center"),
        (KUNQU_OLD_HOUSE_PROMPT, "registry:public_cultural_specialties.performance_heritage"),
    ],
)
def test_public_cultural_heavy_specialties_are_loaded_from_registry(prompt, fragment_source):
    plan = _blueprint(prompt)

    assert plan["brief_handoff_slots"]["fragment_source"] == fragment_source


def test_public_cultural_plan_body_does_not_keep_unreachable_handwritten_branches():
    source = Path(
        "intelligent_project_analyzer/services/demand_reconstruction_output_planner.py"
    ).read_text(encoding="utf-8")
    start = source.index("def _public_cultural_experience_plan")
    end = source.index("def _public_cultural_specialty_plan", start)
    plan_body = source[start:end]

    assert "if self._is_performance_heritage_project(text):" not in plan_body
    assert "if not self._is_farm_learning_center(text):" not in plan_body
    assert "亲子厨房与科普教育是预约制课程" not in plan_body


def test_generic_public_cultural_plan_uses_registry_instead_of_handwritten_exhibition_template():
    source = Path(
        "intelligent_project_analyzer/services/demand_reconstruction_output_planner.py"
    ).read_text(encoding="utf-8")
    start = source.index("def _generic_public_cultural_plan")
    end = source.index("def _has_generic_exhibition_material_topic", start)
    plan_body = source[start:end]

    assert '"public_cultural_specialties",' in plan_body
    assert '"generic_exhibition",' in plan_body
    assert "政府访客、产业伙伴和公众的理解深度不同" not in plan_body
    assert "这个展示馆首先服务政府访客、产业伙伴，还是普通公众理解" not in plan_body


def test_commercial_operation_plan_does_not_default_to_retail_handwritten_fallback():
    source = Path(
        "intelligent_project_analyzer/services/demand_reconstruction_output_planner.py"
    ).read_text(encoding="utf-8")
    start = source.index("def _commercial_operation_plan")
    end = source.index("def _commercial_specialty_plan", start)
    plan_body = source[start:end]

    assert "_retail_brand_conversion_plan(context)" not in plan_body


def test_retail_brand_conversion_plan_uses_registry_instead_of_handwritten_template():
    source = Path(
        "intelligent_project_analyzer/services/demand_reconstruction_output_planner.py"
    ).read_text(encoding="utf-8")
    start = source.index("def _retail_brand_conversion_plan")
    end = source.index("def _media_production_plan", start)
    plan_body = source[start:end]

    assert '"commercial_specialties", "retail_brand_conversion"' in plan_body
    assert "零售型商业需求重构要先判断顾客为什么进店、停留、理解并购买。" not in plan_body
    assert "这个旗舰店首先靠品牌故事、产品试用，还是会员活动推动高客单转化" not in plan_body


def test_residential_life_order_plan_does_not_keep_child_support_handwritten_fallback():
    source = Path(
        "intelligent_project_analyzer/services/demand_reconstruction_output_planner.py"
    ).read_text(encoding="utf-8")
    start = source.index("def _residential_life_order_plan")
    end = source.index("def _commercial_operation_plan", start)
    plan_body = source[start:end]

    assert "儿童支持、父母休息和普通生活谁是第一优先级？" not in plan_body
    assert "儿童年龄、感统训练方式和触发风险会改变空间细节。" not in plan_body


def test_style_semantics_plan_does_not_keep_tea_space_handwritten_fallback():
    source = Path(
        "intelligent_project_analyzer/services/demand_reconstruction_output_planner.py"
    ).read_text(encoding="utf-8")
    start = source.index("def _style_semantics_plan")
    end = source.index("def _style_specialty_plan", start)
    plan_body = source[start:end]

    assert "茶空间还要判断是社交、独处、展示，还是生活方式消费。" not in plan_body
    assert "只追求极简，可能丢掉茶空间应有的停留层次。" not in plan_body


def test_cultural_research_plan_uses_registry_instead_of_handwritten_research_template():
    source = Path(
        "intelligent_project_analyzer/services/demand_reconstruction_output_planner.py"
    ).read_text(encoding="utf-8")
    start = source.index("def _cultural_research_plan")
    end = source.index("def _research_subject_phrase", start)
    plan_body = source[start:end]

    assert '_primary_fragment_plan(context, "cultural_research")' in plan_body
    assert "需求重构只能定义研究路径，不能把未经验证的文化想象当结论。" not in plan_body
    assert "当前适合生成研究计划，不适合直接生成空间结论。" not in plan_body


def test_cultural_research_phrase_extraction_rules_are_registry_driven():
    source = Path(
        "intelligent_project_analyzer/services/demand_reconstruction_output_planner.py"
    ).read_text(encoding="utf-8")
    start = source.index("def _research_subject_phrase")
    end = source.index("def _urban_renewal_plan", start)
    phrase_body = source[start:end]
    registry_path = Path(
        "intelligent_project_analyzer/config/registries/demand_reconstruction_blueprints.yaml"
    )
    registry_source = registry_path.read_text(encoding="utf-8")
    fragments = yaml.safe_load(registry_source)["demand_reconstruction_blueprint_fragments"]

    assert "research_phrase_extractors:" in registry_source
    assert "subject_end_markers:" in registry_source
    assert "target_end_markers:" in registry_source
    assert 'for marker in ("对", "如何影响", "如何启发", "启发")' not in phrase_body
    assert '"的启发", "的影响", "如何"' not in phrase_body


def test_blueprint_fragments_live_in_dedicated_registry_not_semantic_axes_registry():
    blueprint_registry = Path(
        "intelligent_project_analyzer/config/registries/demand_reconstruction_blueprints.yaml"
    ).read_text(encoding="utf-8")
    semantic_axes_registry = Path(
        "intelligent_project_analyzer/config/registries/scheme_advisor_semantic_axes.yaml"
    ).read_text(encoding="utf-8")

    assert "demand_reconstruction_blueprint_fragments:" in blueprint_registry
    assert "demand_reconstruction_blueprint_fragments:" not in semantic_axes_registry


def test_subject_phrase_mapping_is_registry_driven():
    source = Path(
        "intelligent_project_analyzer/services/demand_reconstruction_output_planner.py"
    ).read_text(encoding="utf-8")
    start = source.index("def _subject_phrase")
    end = source.index("def _axis_labels", start)
    phrase_body = source[start:end]
    registry_path = Path(
        "intelligent_project_analyzer/config/registries/demand_reconstruction_blueprints.yaml"
    )
    registry_source = registry_path.read_text(encoding="utf-8")
    fragments = yaml.safe_load(registry_source)["demand_reconstruction_blueprint_fragments"]

    assert "subject_phrase_mapping:" in registry_source
    assert "text_rules:" in registry_source
    assert "axis_rules:" in registry_source
    assert 'if "设计师" in text' not in phrase_body
    assert 'if "业主" in text' not in phrase_body
    assert '"50岁专业设计师"' not in phrase_body
    assert '"创始人业主"' not in phrase_body


def test_technical_constraint_plan_uses_registry_instead_of_handwritten_generic_template():
    source = Path(
        "intelligent_project_analyzer/services/demand_reconstruction_output_planner.py"
    ).read_text(encoding="utf-8")
    start = source.index("def _technical_constraint_plan")
    end = source.index("def _technical_constraint_items", start)
    plan_body = source[start:end]

    assert 'self._specialized_fragment_plan(context, "technical_specialties", "generic_constraint")' in plan_body
    assert "focus_items = self._technical_constraint_items(context)" not in plan_body
    assert "当前能判断技术约束的优先级，但不能在参数缺失时直接冻结方案。" not in plan_body


def test_hospitality_operation_plans_use_registry_instead_of_handwritten_templates():
    source = Path(
        "intelligent_project_analyzer/services/demand_reconstruction_output_planner.py"
    ).read_text(encoding="utf-8")
    hotel_start = source.index("def _hotel_hospitality_operation_plan")
    hotel_end = source.index("def _shared_living_amenity_operation_plan", hotel_start)
    hotel_body = source[hotel_start:hotel_end]
    apartment_start = source.index("def _shared_living_amenity_operation_plan")
    apartment_end = source.index("def _retail_brand_conversion_plan", apartment_start)
    apartment_body = source[apartment_start:apartment_end]

    assert '"hospitality_specialties", "hotel_lobby"' in hotel_body
    assert "酒店大堂需求重构要先判断抵达、办理、等候、寄存和短暂停留能否同时成立" not in hotel_body
    assert '"hospitality_specialties",' in apartment_body
    assert '"long_term_apartment_amenity",' in apartment_body
    assert "长租公寓公共区需求重构要先判断共享功能如何被运营和维护" not in apartment_body


def test_urban_renewal_and_collection_museum_plans_use_registry_instead_of_handwritten_templates():
    source = Path(
        "intelligent_project_analyzer/services/demand_reconstruction_output_planner.py"
    ).read_text(encoding="utf-8")
    urban_start = source.index("def _urban_renewal_plan")
    urban_end = source.index("def _collection_museum_plan", urban_start)
    urban_body = source[urban_start:urban_end]
    collection_start = source.index("def _collection_museum_plan")
    collection_end = source.index("def _is_collection_museum_project", collection_start)
    collection_body = source[collection_start:collection_end]

    assert '"urban_renewal_specialties"' in urban_body
    assert '"district_renewal"' in urban_body
    assert "城市更新不是单一空间改造题，必须先确认原住民、商户、访客、运营方和管理方之间的利益边界。" not in urban_body
    assert "这不是单纯改造老旧街区的问题，而是把原住民生活、社区商业、公共活动、历史界面和分期实施重新排成可协商的更新秩序。" not in urban_body
    assert '"public_cultural_specialties"' in collection_body
    assert '"collection_museum"' in collection_body
    assert "收藏型展陈首先要确认藏品保护等级，再决定展示密度、灯光、互动和会员活动。" not in collection_body
    assert "这不是把藏品做成漂亮展墙的问题，而是让藏品保护、品牌历史叙事、公众参观和会员运营在同一套博物馆秩序里成立。" not in collection_body


def test_workplace_plans_use_registry_instead_of_handwritten_templates():
    source = Path(
        "intelligent_project_analyzer/services/demand_reconstruction_output_planner.py"
    ).read_text(encoding="utf-8")
    headquarters_start = source.index("def _workplace_headquarters_plan")
    headquarters_end = source.index("def _professional_service_workplace_plan", headquarters_start)
    headquarters_body = source[headquarters_start:headquarters_end]
    professional_start = source.index("def _professional_service_workplace_plan")
    professional_end = source.index("def _is_professional_service_workplace", professional_start)
    professional_body = source[professional_start:professional_end]

    assert '"workplace_specialties"' in headquarters_body
    assert '"headquarters"' in headquarters_body
    assert "总部办公需求重构要先判断组织如何工作，而不是先做前台、会议室和工位的面积拼盘。" not in headquarters_body
    assert "这不是给总部办公空间做形象包装的问题，而是把组织协作、客户接待、员工恢复和品牌展示重新排成可运行的空间秩序。" not in headquarters_body
    assert '"workplace_specialties"' in professional_body
    assert '"professional_service"' in professional_body
    assert "专业服务办公首先要确认服务对象、专业人员和资料安全如何共存，而不是直接套通用组织形象模板。" not in professional_body
    assert "这不是给办公室做形象包装的问题，而是把接待、专业服务、档案保密、内部协作和人员恢复重新排成可运行的服务秩序。" not in professional_body


def test_healthcare_specialty_plans_use_registry_instead_of_handwritten_templates():
    source = Path(
        "intelligent_project_analyzer/services/demand_reconstruction_output_planner.py"
    ).read_text(encoding="utf-8")
    dental_start = source.index("def _dental_clinic_plan")
    dental_end = source.index("def _is_dental_clinic_project", dental_start)
    dental_body = source[dental_start:dental_end]
    maternity_start = source.index("def _maternity_center_plan")
    maternity_end = source.index("def _is_maternity_center_project", maternity_start)
    maternity_body = source[maternity_start:maternity_end]
    rehab_start = source.index("def _rehabilitation_center_plan")
    rehab_end = source.index("def _is_rehabilitation_center_project", rehab_start)
    rehab_body = source[rehab_start:rehab_end]

    assert '"healthcare_specialties", "dental_clinic"' in dental_body
    assert "牙科诊所首先要把接待、候诊、拍片、诊疗、消毒和安抚串成稳定流程，而不是套用泛医疗照护逻辑。" not in dental_body
    assert '"healthcare_specialties", "maternity_center"' in maternity_body
    assert "月子中心的核心不是住宿感，而是产妇休息、婴儿护理、护士站响应和服务配送能否稳定衔接。" not in maternity_body
    assert '"healthcare_specialties", "rehabilitation_center"' in rehab_body
    assert "康复中心的关键不是先罗列器械，而是把评估、治疗、训练、等候和无障碍动线组织成渐进恢复路径。" not in rehab_body


def test_library_reading_plan_uses_registry_instead_of_handwritten_template():
    source = Path(
        "intelligent_project_analyzer/services/demand_reconstruction_output_planner.py"
    ).read_text(encoding="utf-8")
    start = source.index("def _library_reading_plan")
    end = source.index("def _generic_public_cultural_plan", start)
    plan_body = source[start:end]

    assert '"public_cultural_specialties", "library_reading"' in plan_body
    assert "这不是给社区图书馆儿童阅读区做展示包装的问题，而是把亲子阅读、绘本活动、安静学习和借阅管理排成可持续运营的阅读秩序。" not in plan_body
    assert "儿童阅读区需求重构要先判断亲子活动和安静学习如何共存，而不是套用一般展陈或亲子体验馆逻辑。" not in plan_body


def test_style_and_general_project_plans_use_primary_registry_fragments():
    source = Path(
        "intelligent_project_analyzer/services/demand_reconstruction_output_planner.py"
    ).read_text(encoding="utf-8")
    style_start = source.index("def _style_semantics_plan")
    style_end = source.index("def _style_specialty_plan", style_start)
    style_body = source[style_start:style_end]
    general_start = source.index("def _general_project_plan")
    general_end = source.index("def _workplace_headquarters_plan", general_start)
    general_body = source[general_start:general_end]

    assert '_primary_fragment_plan(context, "style_semantics")' in style_body
    assert "风格需求重构要先防止词语滑向符号堆叠。" not in style_body
    assert "头号风险是用风格词替代空间判断，最后得到一套看似统一但不可使用的氛围包装。" not in style_body
    assert '_primary_fragment_plan(context, "general_project")' in general_body
    assert "当前还不能直接进入方案，应先把影响判断的变量排出来。" not in general_body
    assert "头号风险是过早给方案，掩盖真正决定项目方向的未知条件。" not in general_body


def test_residential_and_general_media_plans_use_registry_fragments():
    source = Path(
        "intelligent_project_analyzer/services/demand_reconstruction_output_planner.py"
    ).read_text(encoding="utf-8")
    residential_start = source.index("def _residential_life_order_plan")
    residential_end = source.index("def _commercial_operation_plan", residential_start)
    residential_body = source[residential_start:residential_end]
    media_start = source.index("def _general_media_production_plan")
    media_end = source.index("def _public_cultural_experience_plan", media_start)
    media_body = source[media_start:media_end]

    assert '"life_identity_specialties"' in residential_body
    assert '"residential_life_order"' in residential_body
    assert "居住类需求重构要先看谁每天如何使用，而不是先套住宅风格或身份叙事。" not in residential_body
    assert "这不是先做{space}风格的问题，而是家庭成员的生活秩序、隐私边界和长期维护能否被同一套住宅机制承接。" not in residential_body
    assert '"media_specialties", "live_commerce_studio"' in media_body
    assert "直播和短视频空间要先确认内容从选品、展示、拍摄到运营复盘如何流动。" not in media_body
    assert "头号风险是只做漂亮直播间，却忽视样品流转、中控协同、设备走线和多团队并行。" not in media_body


def test_media_specialty_exclusions_are_registry_driven():
    source = Path(
        "intelligent_project_analyzer/services/demand_reconstruction_output_planner.py"
    ).read_text(encoding="utf-8")
    registry_path = Path("intelligent_project_analyzer/config/registries/demand_reconstruction_blueprints.yaml")
    registry_source = registry_path.read_text(encoding="utf-8")
    fragments = yaml.safe_load(registry_source)["demand_reconstruction_blueprint_fragments"]
    start = source.index("def _media_specialty_score")
    end = source.index("def _general_media_production_plan", start)
    score_body = source[start:end]

    assert "exclude_when_any_fragment_terms:" in registry_source
    assert 'fragment_id == "food_styling_studio"' not in score_body
    assert "heavy_cooking_exclusion" not in score_body


def test_farm_learning_anchor_replacements_are_registry_driven():
    source = Path(
        "intelligent_project_analyzer/services/demand_reconstruction_output_planner.py"
    ).read_text(encoding="utf-8")
    registry_path = Path("intelligent_project_analyzer/config/registries/demand_reconstruction_blueprints.yaml")
    registry_source = registry_path.read_text(encoding="utf-8")
    fragments = yaml.safe_load(registry_source)["demand_reconstruction_blueprint_fragments"]
    start = source.index("def _apply_anchor_missing_postprocess")
    end = source.index("def _is_library_reading_project", start)
    cleaner_body = source[start:end]

    assert "anchor_missing_replacements:" in registry_source
    assert '"农产品展示": "配套展示"' not in cleaner_body
    assert '"农产品SKU和冷链要求": "展示品类、储藏要求"' not in cleaner_body
    assert '"生鲜补货": "后勤维护"' not in cleaner_body


def test_public_cultural_anchor_postprocess_is_registry_driven():
    source = Path(
        "intelligent_project_analyzer/services/demand_reconstruction_output_planner.py"
    ).read_text(encoding="utf-8")
    registry_source = Path(
        "intelligent_project_analyzer/config/registries/demand_reconstruction_blueprints.yaml"
    ).read_text(encoding="utf-8")
    start = source.index("def _public_cultural_specialty_plan")
    end = source.index("def _public_cultural_specialty_score", start)
    planner_body = source[start:end]
    fragment_start = registry_source.index("farm_learning_center:")
    fragment_end = registry_source.index("library_reading:", fragment_start)
    farm_fragment = registry_source[fragment_start:fragment_end]

    assert "anchor_missing_postprocess:" in farm_fragment
    assert 'fragment_id == "farm_learning_center"' not in planner_body


def test_technical_specialty_axis_matches_are_registry_driven():
    source = Path(
        "intelligent_project_analyzer/services/demand_reconstruction_output_planner.py"
    ).read_text(encoding="utf-8")
    registry_source = Path(
        "intelligent_project_analyzer/config/registries/demand_reconstruction_blueprints.yaml"
    ).read_text(encoding="utf-8")
    start = source.index("def _technical_specialty_matches")
    end = source.index("def _technical_constraint_plan", start)
    matcher_body = source[start:end]

    assert "semantic_axis_matches:" in registry_source
    assert 'fragment_id == "acoustic_constraint"' not in matcher_body
    assert 'fragment_id == "cold_storage_constraint"' not in matcher_body
    assert '"acoustics" in constraints' not in matcher_body
    assert '"cold_chain_logistics" in constraints' not in matcher_body


def test_commercial_specialty_term_rules_are_registry_driven():
    source = Path(
        "intelligent_project_analyzer/services/demand_reconstruction_output_planner.py"
    ).read_text(encoding="utf-8")
    registry_source = Path(
        "intelligent_project_analyzer/config/registries/demand_reconstruction_blueprints.yaml"
    ).read_text(encoding="utf-8")
    start = source.index("def _commercial_specialty_score")
    end = source.index("def _is_hotel_hospitality_operation", start)
    score_body = source[start:end]

    assert "exclude_when_any_fragment_terms: [quick_service_exclusion]" in registry_source
    assert "require_any_fragment_terms: [cultural_language]" in registry_source
    assert 'fragment_id == "dining_hospitality_experience"' not in score_body
    assert 'fragment_id == "naming_language"' not in score_body
    assert "quick_service_exclusion" not in score_body
    assert "cultural_language" not in score_body


def test_life_identity_subject_axis_matches_are_registry_driven():
    source = Path(
        "intelligent_project_analyzer/services/demand_reconstruction_output_planner.py"
    ).read_text(encoding="utf-8")
    registry_source = Path(
        "intelligent_project_analyzer/config/registries/demand_reconstruction_blueprints.yaml"
    ).read_text(encoding="utf-8")
    start = source.index("def _life_identity_specialty_matches")
    end = source.index("def _residential_life_order_plan", start)
    matcher_body = source[start:end]
    fragment_start = registry_source.index("residential_child_support:")
    fragment_end = registry_source.index("accessible_residence:", fragment_start)
    child_fragment = registry_source[fragment_start:fragment_end]

    assert "semantic_axis_matches:" in child_fragment
    assert "subject_profiles: [children]" in child_fragment
    assert 'fragment_id == "residential_child_support"' not in matcher_body
    assert '"children" in subjects' not in matcher_body


def test_default_blueprint_fragments_are_marked_in_registry_not_skipped_by_name():
    source = Path(
        "intelligent_project_analyzer/services/demand_reconstruction_output_planner.py"
    ).read_text(encoding="utf-8")
    registry_path = Path("intelligent_project_analyzer/config/registries/demand_reconstruction_blueprints.yaml")
    registry_source = registry_path.read_text(encoding="utf-8")
    fragments = yaml.safe_load(registry_source)["demand_reconstruction_blueprint_fragments"]
    life_start = source.index("def _life_identity_specialty_plan")
    life_end = source.index("def _life_identity_specialty_matches", life_start)
    public_start = source.index("def _public_cultural_specialty_plan")
    public_end = source.index("def _public_cultural_specialty_score", public_start)
    technical_start = source.index("def _technical_specialty_plan")
    technical_end = source.index("def _technical_specialty_matches", technical_start)
    loop_body = source[life_start:life_end] + source[public_start:public_end] + source[technical_start:technical_end]

    assert fragments["life_identity_specialties"]["residential_life_order"]["is_default_fragment"] is True
    assert fragments["public_cultural_specialties"]["generic_exhibition"]["is_default_fragment"] is True
    assert fragments["technical_specialties"]["generic_constraint"]["is_default_fragment"] is True
    for fragment_id in ("residential_life_order", "generic_exhibition", "generic_constraint"):
        assert f'fragment_id == "{fragment_id}"' not in loop_body


def test_demand_reconstruction_registry_visible_text_does_not_leak_internal_terms():
    registry_path = Path("intelligent_project_analyzer/config/registries/demand_reconstruction_blueprints.yaml")
    fragments = yaml.safe_load(registry_path.read_text(encoding="utf-8"))["demand_reconstruction_blueprint_fragments"]
    visible_fields = {
        "task_reframe",
        "viability",
        "primary_risk",
        "key_forks",
        "unknowns",
        "next_question",
        "title",
        "body",
        "items",
    }
    forbidden_terms = (
        "registry",
        "fragment",
        "archetype",
        "candidate_set",
        "component_intent",
        "axis_id",
        "ontology",
        "LLM",
        "llm",
    )
    visible_texts: list[str] = []

    def collect_visible(value, *, visible: bool = False) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                collect_visible(child, visible=visible or str(key) in visible_fields)
            return
        if isinstance(value, list):
            for child in value:
                collect_visible(child, visible=visible)
            return
        if visible and isinstance(value, str):
            visible_texts.append(value)

    for group_id, group in fragments.items():
        if group_id in {"research_phrase_extractors", "subject_phrase_mapping"}:
            continue
        collect_visible(group)

    leaked = [
        text
        for text in visible_texts
        if any(term in text for term in forbidden_terms)
    ]
    assert leaked == []


def test_generic_commercial_operation_plan_uses_primary_registry_fragment():
    source = Path(
        "intelligent_project_analyzer/services/demand_reconstruction_output_planner.py"
    ).read_text(encoding="utf-8")
    start = source.index("def _generic_commercial_operation_plan")
    end = source.index("def _commercial_specialty_plan", start)
    plan_body = source[start:end]

    assert '_primary_fragment_plan(context, "commercial_operation")' in plan_body
    assert "商业类需求重构要先确认项目靠什么成立，而不是直接把所有商业空间都写成单一业态的效率问题。" not in plan_body
    assert "这不是先给{space}做风格包装的问题，而是先确认商业模型、顾客路径、服务方式和运营边界能否共同成立。" not in plan_body


def test_healthcare_care_plan_uses_primary_registry_fragment():
    source = Path(
        "intelligent_project_analyzer/services/demand_reconstruction_output_planner.py"
    ).read_text(encoding="utf-8")
    start = source.index("def _healthcare_care_plan")
    end = source.index("def _dental_clinic_plan", start)
    plan_body = source[start:end]

    assert '_primary_fragment_plan(context, "healthcare_care")' in plan_body
    assert "医疗照护空间首先不是风格问题，而是患者、家属和医护三条行为线能否同时成立。" not in plan_body
    assert "这不是单纯改造病房的问题，而是把患者尊严、家属陪伴、医护效率和感染控制重新排成可执行的照护秩序。" not in plan_body


def test_community_library_reading_area_is_not_public_exhibition_template():
    plan = _blueprint(COMMUNITY_LIBRARY_READING_PROMPT)
    rendered = _reply(COMMUNITY_LIBRARY_READING_PROMPT)

    assert plan["archetype"]["primary"] == "public_cultural_experience"
    assert any(term in rendered for term in ("社区图书馆", "儿童阅读", "亲子阅读", "绘本活动", "安静学习", "借阅管理"))
    assert "展示馆" not in rendered
    assert "观众" not in rendered
    assert "政府访客" not in rendered
    assert "互动装置" not in rendered


def test_community_culture_center_uses_registry_fragment_not_generic_exhibition():
    plan = _blueprint(COMMUNITY_CULTURE_CENTER_PROMPT)
    rendered = _reply(COMMUNITY_CULTURE_CENTER_PROMPT)

    assert plan["archetype"]["primary"] == "public_cultural_experience"
    assert plan["brief_handoff_slots"]["fragment_source"] == "registry:public_cultural_specialties.community_culture_center"
    assert "社区文化运营" in [section["title"] for section in plan["sections"]]
    assert any(term in rendered for term in ("非遗手作", "居民活动", "临时展览", "公共讲座", "志愿者运营"))
    assert "政府访客" not in rendered
    assert "产业伙伴" not in rendered
    assert "技术安全边界" not in rendered


def test_kunqu_old_house_uses_performance_heritage_fragments_not_farm_fragments():
    result = DemandReconstructionService().handle_message(
        session={},
        user_message=KUNQU_OLD_HOUSE_PROMPT,
        in_response_to_card_id=None,
        selected_option_id=None,
    )

    assert result is not None
    plan = result["demand_reconstruction_context"]["blueprint"]
    assert plan["archetype"]["primary"] == "public_cultural_experience"
    section_titles = [section["title"] for section in plan["sections"]]
    assert "动静分区" in section_titles
    assert "保护边界" in section_titles
    assert "文化转译" in section_titles
    rendered = result["reply"] + str(result["guidance_card"])
    assert "练声" in rendered
    assert "展陈" in rendered
    assert "亲子厨房" not in rendered
    assert "咖啡" not in rendered
    assert "材料循环" not in rendered


def test_historic_craft_exhibition_without_kunqu_anchors_does_not_leak_performance_fragments():
    plan = _blueprint(HISTORIC_CRAFT_EXHIBITION_PROMPT)
    rendered = _reply(HISTORIC_CRAFT_EXHIBITION_PROMPT)

    assert plan["archetype"]["primary"] == "public_cultural_experience"
    assert "历史建筑" in rendered or "工艺" in rendered or "展陈" in rendered
    assert "昆曲" not in rendered
    assert "练声" not in rendered
    assert "老宅" not in rendered
    assert "故居" not in rendered


def test_context_adapter_builds_candidate_set_and_downweights_supporting_commerce():
    context = DemandReconstructionContextAdapter().build(CITIZEN_FARM_PROMPT)

    candidates = context["semantic_candidate_set"]

    assert candidates[0]["id"] == "public_cultural_experience"
    assert candidates[0]["role"] == "primary"
    assert any(candidate["id"] == "commercial_operation" and candidate["role"] == "downweighted" for candidate in candidates)
    assert any("咖啡" in " ".join(candidate.get("counter_evidence", [])) for candidate in candidates if candidate["id"] == "commercial_operation")
    assert context["archetype"]["primary"] == "public_cultural_experience"


def test_context_adapter_does_not_let_cultural_research_terms_hijack_concrete_project():
    context = DemandReconstructionContextAdapter().build(
        "成都历史街区里的一家汽车品牌体验店，需要将城市记忆转译为品牌空间，"
        "请提出完整设计框架，包括展陈、会员活动和销售转化。"
    )

    assert context["archetype"]["primary"] != "cultural_research"
    assert context["archetype"]["routing_target"] != "deep_research"
    assert any(
        candidate["id"] == "cultural_research" and candidate["role"] != "primary"
        for candidate in context["semantic_candidate_set"]
    )


def test_concrete_brand_experience_reconstruction_is_not_routed_to_deep_research():
    plan = _blueprint(BRAND_EXPERIENCE_HISTORIC_DISTRICT_PROMPT)
    rendered = _reply(BRAND_EXPERIENCE_HISTORIC_DISTRICT_PROMPT)

    assert plan["archetype"]["primary"] != "cultural_research"
    assert plan["routing"]["target"] != "deep_research"
    assert any(term in rendered for term in ("品牌", "体验", "城市记忆", "转译"))
    assert "深度研究" not in rendered
    assert "研究对象边界" not in [section["title"] for section in plan["sections"]]


def test_concrete_brand_experience_advice_is_not_routed_to_deep_research():
    plan = _blueprint(BRAND_EXPERIENCE_HISTORIC_DISTRICT_ADVICE_PROMPT)
    rendered = _reply(BRAND_EXPERIENCE_HISTORIC_DISTRICT_ADVICE_PROMPT)

    assert plan["archetype"]["primary"] != "cultural_research"
    assert plan["routing"]["target"] != "deep_research"
    assert any(term in rendered for term in ("品牌", "体验", "城市记忆", "转译"))
    assert "深度研究" not in rendered
    assert "研究对象边界" not in [section["title"] for section in plan["sections"]]


def test_output_planner_uses_main_tensions_missing_slots_and_coverage_before_template_defaults():
    plan = DemandReconstructionOutputPlanner().build_plan(
        {
            "source_message": "苏州昆曲老宅改造为教学故居，包含展陈、练声教学和小型交流。",
            "space_label": "昆曲教学故居",
            "project_type": "public_cultural",
            "project_type_name": "公共文化空间",
            "archetype": {"primary": "general_project", "secondary": []},
            "context_source": {"semantic_axes": True},
            "main_tensions": [
                {
                    "id": "acoustic_exhibition_conflict",
                    "title": "练声声学与静态展陈之间的冲突",
                    "prompt": "先确认昆曲练声、教学讲解和静态展陈是否需要同时发生。",
                }
            ],
            "missing_slots": [
                {
                    "name": "heritage_scope",
                    "user_visible_note": "老宅结构、消防和可改造边界尚未确认。",
                    "priority": "P1",
                }
            ],
            "advisor_packet": {
                "context_packet": {
                    "knowledge_binding": {
                        "coverage_ceiling": {
                            "level": "general_method_only",
                            "user_visible_note": "当前只能按公共文化空间通用方法论判断，不能假装已有昆曲教学故居专科包。",
                        }
                    }
                }
            },
        }
    )

    assert plan["key_forks"][0] == "练声声学与静态展陈之间的冲突"
    assert plan["brief_handoff_slots"]["fragment_source"] == "registry:primary_archetypes.general_project"
    assert plan["next_question"] == "先确认昆曲练声、教学讲解和静态展陈是否需要同时发生。"
    assert "老宅结构、消防和可改造边界尚未确认。" in plan["unknowns"]
    assert plan["coverage_level"] == "general_method_only"
    assert any("通用方法论" in item for section in plan["sections"] for item in section.get("items", []))
    assert "通用方法论" in plan["project_viability_judgment"]
    assert "不能" in plan["primary_risk"]


def test_low_coverage_level_downgrades_user_visible_commitment_depth():
    plan = DemandReconstructionOutputPlanner().build_plan(
        {
            "source_message": "一个未知新型沉浸式空间，需要结合脑机接口、嗅觉反馈和群体疗愈体验。",
            "space_label": "未知新型沉浸式空间",
            "project_type": "experimental_space",
            "project_type_name": "实验性空间",
            "archetype": {"primary": "general_project", "secondary": []},
            "context_source": {"semantic_axes": True},
            "main_tensions": [],
            "missing_slots": [],
            "knowledge_coverage_ceiling": {
                "level": "general_method_only",
                "user_visible_note": "当前没有该新型空间的专科知识包，只能按通用需求重构框架处理。",
            },
        }
    )

    assert plan["coverage_level"] == "general_method_only"
    assert plan["task_reframe"].startswith("当前只能在通用方法论层面重构")
    assert "未知新型沉浸式空间" in plan["task_reframe"]
    assert "不能把专科结论写成已经验证的确定判断" in plan["project_viability_judgment"]
    assert "知识覆盖边界" in [section["title"] for section in plan["sections"]]


def test_demand_reconstruction_blueprint_surfaces_knowledge_gap_governance_signals_without_user_leakage():
    plan = DemandReconstructionOutputPlanner().build_plan(
        {
            "source_message": "一个未知新型沉浸式空间，需要结合脑机接口、嗅觉反馈和群体疗愈体验。",
            "space_label": "未知新型沉浸式空间",
            "project_type": "experimental_space",
            "project_type_name": "实验性空间",
            "archetype": {"primary": "general_project", "secondary": []},
            "context_source": {"semantic_axes": True},
            "classification": {
                "coverage_gap": True,
                "knowledge_gap_ticket": {
                    "gap_type": "knowledge_coverage",
                    "project_type": "experimental_space",
                    "summary": "缺少脑机接口与嗅觉反馈沉浸空间知识资产。",
                },
            },
            "main_tensions": [],
            "missing_slots": [],
            "knowledge_coverage_ceiling": {
                "level": "general_method_only",
                "user_visible_note": "当前没有该新型空间的专科知识包，只能按通用需求重构框架处理。",
            },
        }
    )

    signals = plan["governance_signals"]
    assert {signal["code"] for signal in signals} == {"coverage_gap", "knowledge_gap_ticket"}
    assert {signal["review_queue"] for signal in signals} == {"space_registry_review", "knowledge_asset_review"}
    assert all(signal["user_visible"] is False for signal in signals)

    rendered = DemandReconstructionService._render_reply(plan)
    assert "knowledge_gap_ticket" not in rendered
    assert "coverage_gap" not in rendered
    assert "space_registry_review" not in rendered
    assert "knowledge_asset_review" not in rendered


def test_output_planner_surfaces_secondary_candidates_as_composite_project_notes():
    plan = DemandReconstructionOutputPlanner().build_plan(
        {
            "source_message": "住宅兼小型工作室，希望兼顾长期居住、拍摄展示和材料气质。",
            "space_label": "住宅兼工作室",
            "project_type": "hybrid_residential_commercial",
            "project_type_name": "复合居住工作空间",
            "archetype": {
                "primary": "life_identity",
                "secondary": ["media_production", "style_semantics"],
                "candidate_set": [
                    {"id": "life_identity", "score": 86, "role": "primary"},
                    {"id": "media_production", "score": 76, "role": "secondary"},
                    {"id": "style_semantics", "score": 68, "role": "secondary"},
                ],
            },
            "context_source": {"semantic_axes": True},
            "main_tensions": [],
            "missing_slots": [],
        }
    )

    section_titles = [section["title"] for section in plan["sections"]]
    assert "复合关系" in section_titles
    composite = next(section for section in plan["sections"] if section["title"] == "复合关系")
    composite_text = composite["body"] + " ".join(composite["items"])
    assert "媒体生产" in composite_text
    assert "风格语义" in composite_text


def test_output_planner_adds_concrete_sections_for_secondary_candidates():
    plan = DemandReconstructionOutputPlanner().build_plan(
        {
            "source_message": "社区公共展厅包含咖啡零售、亲子活动和设备消防限制，需要先重构需求。",
            "space_label": "社区公共展厅",
            "project_type": "public_cultural",
            "project_type_name": "公共文化空间",
            "archetype": {
                "primary": "public_cultural_experience",
                "secondary": ["commercial_operation", "hard_constraint"],
                "candidate_set": [
                    {"id": "public_cultural_experience", "score": 91, "role": "primary"},
                    {"id": "commercial_operation", "score": 74, "role": "secondary"},
                    {"id": "hard_constraint", "score": 67, "role": "secondary"},
                ],
            },
            "context_source": {"semantic_axes": True},
            "main_tensions": [],
            "missing_slots": [],
        }
    )

    section_titles = [section["title"] for section in plan["sections"]]
    assert "商业运营边界" in section_titles
    assert "硬约束边界" in section_titles


@pytest.mark.parametrize(
    ("candidate_id", "expected_title"),
    [
        ("media_production", "内容生产边界"),
        ("style_semantics", "语义表达边界"),
        ("public_cultural_experience", "公共体验边界"),
        ("life_identity", "生活身份边界"),
        ("cultural_research", "研究证据边界"),
    ],
)
def test_output_planner_has_concrete_sections_for_all_secondary_candidate_fragments(
    candidate_id,
    expected_title,
):
    plan = DemandReconstructionOutputPlanner().build_plan(
        {
            "source_message": "复合项目需要校准主线和次线，避免只按单一空间类型写任务书。",
            "space_label": "复合空间",
            "project_type": "hybrid_project",
            "project_type_name": "复合空间",
            "archetype": {
                "primary": "general_project",
                "secondary": [candidate_id],
                "candidate_set": [
                    {"id": "general_project", "score": 62, "role": "primary"},
                    {"id": candidate_id, "score": 58, "role": "secondary"},
                ],
            },
            "context_source": {"semantic_axes": True},
            "main_tensions": [],
            "missing_slots": [],
        }
    )

    assert expected_title in [section["title"] for section in plan["sections"]]


def test_output_planner_uses_subject_profile_axis_for_owner_phrase():
    plan = DemandReconstructionOutputPlanner().build_plan(
        {
            "source_message": "退休老人准备返乡改造老家民居，希望兼顾适老生活、亲友探访和长期维护。",
            "space_label": "返乡适老民居",
            "project_type": "residential_life",
            "project_type_name": "居住空间",
            "archetype": {"primary": "life_identity", "secondary": []},
            "context_source": {"semantic_axes": True},
            "semantic_axes": {"subject_profiles": ["elderly_users"]},
            "main_tensions": [],
            "missing_slots": [],
        }
    )

    assert plan["brief_handoff_slots"]["owner_profile"] == "老年使用者"
    assert "老年使用者" in plan["task_reframe"]
    assert "而是使用者如何" not in plan["task_reframe"]


def test_output_planner_loads_generic_residential_life_order_from_registry():
    plan = DemandReconstructionOutputPlanner().build_plan(
        {
            "source_message": "一对夫妻希望重新设计140㎡住宅，兼顾长期居住、亲友来访、收纳和安静休息。",
            "space_label": "家庭住宅",
            "project_type": "residential_life",
            "project_type_name": "居住空间",
            "archetype": {"primary": "life_identity", "secondary": []},
            "context_source": {"semantic_axes": True},
            "semantic_axes": {"subject_profiles": ["family"]},
            "main_tensions": [],
            "missing_slots": [],
        }
    )

    assert plan["brief_handoff_slots"]["fragment_source"] == "registry:life_identity_specialties.residential_life_order"
    assert plan["brief_handoff_slots"]["core_tension"] == "家庭关系、生活节奏和空间表达之间的张力"
    assert "生活秩序" in [section["title"] for section in plan["sections"]]
    assert "儿童支持" not in plan["key_forks"][0]
    assert "原乡" not in plan["task_reframe"]


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
    assert blueprint["llm_status"] == "used"
    assert "真正的对手不是乡村环境" in result["reply"]
    assert "最后一件作品" in blueprint["primary_risk"]
    assert "当前规则蓝图" in llm.prompts[0]
    assert "禁止输出完整方案" in llm.prompts[0]
    assert "第一性剥离" in llm.prompts[0]
    assert "核心张力" in llm.prompts[0]
    assert "空间被雇佣" in llm.prompts[0]
    assert "锐度自检" in llm.prompts[0]
    assert "不要在前台输出这些内部术语" in llm.prompts[0]


def test_llm_partial_insight_is_salvaged_instead_of_full_rule_fallback():
    llm = FakeLLM(
        """
        {
          "task_reframe": "这不是给设计师做一栋返乡民居的问题，而是他如何在职业表达、原乡关系和后半生生活之间重新建立一个可长期停留的秩序。",
          "project_viability_judgment": "可以做。",
          "primary_risk": "真正的风险是把这栋房子做成被观看的专业作品，却没有承受日常重复、家族进入和长期维护的能力。",
          "sections": [
            {
              "title": "洞察判断",
              "body": "这栋房子先要回答人如何回来，而不是形式如何成立。",
              "items": ["职业身份需要被日常生活校准。", "原乡关系会重写公共与私密边界。"],
              "emphasis": "high"
            }
          ],
          "key_forks": ["长期自住还是阶段性返乡？", "家族关系进入日常还是只进入节庆？"],
          "unknowns": ["真实居住频率未知。", "家庭成员结构未知。"],
          "next_question": "你喜欢什么风格",
          "insight_packet": {
            "observed_facts": ["50岁男性室内设计师", "背井离乡", "想在老家建民居"],
            "inferred_intents": [
              {"claim": "他可能不是只要一栋房子，而是在处理回乡后的身份安放", "evidence": "背井离乡与老家建民居同时出现", "confidence": "medium"}
            ],
            "core_tension": {"a": "职业表达", "b": "长期生活", "why_it_matters": "两者会导向完全不同的空间优先级"},
            "hypotheses": ["长期自住型", "阶段性返乡型", "作品化精神据点型"],
            "chosen_hypothesis": "阶段性返乡与身份重建混合型",
            "disconfirming_risks": ["如果实际只是投资建房，这个判断会失效"],
            "decisive_question": "这栋房子首先服务长期生活，还是服务与故乡重新建立关系"
          }
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
    assert blueprint["insight_source"] == "llm_partial"
    assert blueprint["llm_status"] == "partial"
    assert "被观看的专业作品" in result["reply"]
    assert "你喜欢什么风格" not in result["reply"]
    assert blueprint["next_question"] != "你喜欢什么风格"
    assert blueprint["insight_packet"]["chosen_hypothesis"] == "阶段性返乡与身份重建混合型"
    assert "primary_risk" in blueprint["quality_report"]["accepted_fields"]
    assert "next_question" in blueprint["quality_report"]["fallback_fields"]
    assert "project_viability_judgment" in blueprint["quality_report"]["fallback_fields"]


def test_llm_sections_with_generic_internal_step_titles_are_salvaged_by_quality_gate():
    llm = FakeLLM(
        """
        {
          "task_reframe": "这不是给设计师做一栋返乡民居的问题，而是他如何在职业表达、原乡关系和后半生生活之间重新建立一个可长期停留的秩序。",
          "project_viability_judgment": "项目能否成立，取决于它能否让设计冲动服从长期生活，而不是把家变成证明专业能力的展厅。",
          "primary_risk": "真正的风险是作品表达压过居住韧性，导致房子能被观看，却无法承受重复、琐碎和家族关系的长期进入。",
          "sections": [
            {
              "title": "成立路径",
              "body": "先判断这栋房子被拿来安放谁，而不是先判断它像什么。",
              "items": ["职业身份必须被日常使用校准。", "故乡关系会改变公共与私密边界。"],
              "emphasis": "high"
            }
          ],
          "key_forks": ["长期居住还是阶段性返乡？", "家族关系进入日常还是只进入节庆？"],
          "unknowns": ["真实居住频率未知。", "家庭成员结构未知。"],
          "next_question": "这栋房子首先服务长期生活，还是服务与故乡重新建立关系",
          "insight_packet": {
            "observed_facts": ["50岁男性室内设计师", "背井离乡", "想在老家建民居"],
            "inferred_intents": [
              {"claim": "他可能不是只要一栋房子，而是在处理回乡后的身份安放", "evidence": "背井离乡与老家建民居同时出现", "confidence": "medium"}
            ],
            "core_tension": {"a": "职业表达", "b": "长期生活", "why_it_matters": "两者会导向完全不同的空间优先级"},
            "hypotheses": ["长期自住型", "阶段性返乡型", "作品化精神据点型"],
            "chosen_hypothesis": "阶段性返乡与身份重建混合型",
            "disconfirming_risks": ["如果实际只是投资建房，这个判断会失效"],
            "decisive_question": "这栋房子首先服务长期生活，还是服务与故乡重新建立关系"
          }
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
    assert blueprint["insight_source"] == "llm_partial"
    assert blueprint["llm_status"] == "partial"
    assert blueprint["quality_report"]["rejected_fields"]["sections"] == "generic_step_title"
    assert "sections" in blueprint["quality_report"]["fallback_fields"]
    assert "成立路径" not in result["reply"]
    assert "作品表达压过居住韧性" in result["reply"]


def test_provider_fallback_continues_when_first_llm_only_produces_partial_blueprint():
    qwen = FakeLLM(
        """
        {
          "task_reframe": "这不是给设计师做一栋返乡民居的问题，而是他如何在职业表达、原乡关系和后半生生活之间重新建立一个可长期停留的秩序。",
          "project_viability_judgment": "可以做。",
          "primary_risk": "真正的风险是把这栋房子做成被观看的专业作品，却没有承受日常重复、家族进入和长期维护的能力。",
          "sections": [
            {
              "title": "洞察判断",
              "body": "这栋房子先要回答人如何回来，而不是形式如何成立。",
              "items": ["职业身份需要被日常生活校准。", "原乡关系会重写公共与私密边界。"],
              "emphasis": "high"
            }
          ],
          "key_forks": ["长期自住还是阶段性返乡？", "家族关系进入日常还是只进入节庆？"],
          "unknowns": ["真实居住频率未知。", "家庭成员结构未知。"],
          "next_question": "你喜欢什么风格"
        }
        """
    )
    deepseek = FakeLLM(
        """
        {
          "task_reframe": "这不是给设计师做一栋返乡民居的问题，而是他如何把职业表达、原乡关系和后半生生活重新放回同一个日常秩序里。",
          "project_viability_judgment": "项目能否成立，取决于它能否让设计冲动服从长期生活，而不是把家变成证明专业能力的展厅。",
          "primary_risk": "真正的风险是作品表达压过居住韧性，导致房子能被观看，却无法承受重复、琐碎和家族关系的长期进入。",
          "sections": [
            {
              "title": "洞察判断",
              "body": "先判断这栋房子被拿来安放谁，而不是先判断它像什么。",
              "items": ["职业身份必须被日常使用校准。", "故乡关系会改变公共与私密边界。"],
              "emphasis": "high"
            }
          ],
          "key_forks": ["长期居住还是阶段性返乡？", "家族关系进入日常还是只进入节庆？"],
          "unknowns": ["真实居住频率未知。", "家庭成员结构未知。"],
          "next_question": "这栋房子首先服务长期生活，还是服务与故乡重新建立关系"
        }
        """
    )
    llm = FallbackLLM(
        providers=["qwen", "deepseek"],
        llm_instances={"qwen": qwen, "deepseek": deepseek},
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
    assert blueprint["llm_status"] == "used"
    assert len(qwen.prompts) == 1
    assert len(deepseek.prompts) == 1
    assert "作品表达压过居住韧性" in result["reply"]
    assert "你喜欢什么风格" not in result["reply"]


def test_insight_prompt_demotes_rule_blueprint_to_constraints_and_requires_hypotheses():
    protocol = DemandReconstructionInsightProtocol()
    prompt = protocol.build_prompt(
        adapter_context={"source_message": RURAL_HOME_PROMPT},
        rule_plan={"task_reframe": "规则蓝图", "sections": []},
    )

    assert "规则蓝图是约束与兜底，不是标准答案" in prompt
    assert "可以反驳规则蓝图" in prompt
    assert "insight_packet" in prompt
    assert "hypotheses" in prompt
    assert "chosen_hypothesis" in prompt


def test_insight_prompt_receives_full_project_semantic_contract():
    protocol = DemandReconstructionInsightProtocol()
    prompt = protocol.build_prompt(
        adapter_context={
            "source_message": "轮椅前运动员需要改造康复住宅，要求无障碍、复健和家属照护不互相打架。",
            "classification": {
                "project_type": "healthcare_care",
                "confidence": 0.72,
                "coverage_gap": True,
            },
            "context_vector": {
                "subject_profile": "wheelchair_user",
                "operation_driver": "rehabilitation_daily_life",
            },
            "semantic_candidate_set": [
                {"id": "healthcare_care", "score": 92, "role": "primary"},
                {"id": "hard_constraint", "score": 80, "role": "secondary"},
            ],
            "main_tensions": [
                {
                    "title": "复健训练与日常照护的动线冲突",
                    "prompt": "先确认复健器械、家属照护和日常起居谁优先。",
                }
            ],
            "missing_slots": [
                {"user_visible_note": "需要确认轮椅回转半径与复健器械尺寸。"}
            ],
            "knowledge_coverage_ceiling": {
                "level": "partial_specialist",
                "note": "康复住宅只能给出相邻经验迁移判断。",
            },
        },
        rule_plan={
            "task_reframe": "规则蓝图",
            "sections": [],
            "governance_signals": [{"code": "coverage_gap", "review_queue": "space_registry_review"}],
        },
    )

    assert '"classification"' in prompt
    assert '"confidence": 0.72' in prompt
    assert '"context_vector"' in prompt
    assert "wheelchair_user" in prompt
    assert "复健训练与日常照护的动线冲突" in prompt
    assert "需要确认轮椅回转半径与复健器械尺寸" in prompt
    assert "coverage_gap" in prompt
    assert "治理信号" in prompt
    assert "不要把 coverage_gap" in prompt


def test_insight_prompt_compacts_runtime_context_without_losing_semantic_contract():
    user_prompt = (
        "50岁男性室内设计师，背井离乡多年，想在老家建一栋民居，"
        "既要回应乡土和家族关系，又不能做成展示作品。请给出建议。"
    )
    adapter_context = DemandReconstructionContextAdapter().build(user_prompt)
    rule_plan = DemandReconstructionOutputPlanner().build_plan(adapter_context)

    prompt = DemandReconstructionInsightProtocol().build_prompt(adapter_context, rule_plan)

    assert len(prompt) < 8000
    assert user_prompt in prompt
    assert '"classification"' in prompt
    assert '"context_vector"' in prompt
    assert '"semantic_candidate_set"' in prompt
    assert '"task_reframe"' in prompt
    assert "规则蓝图是约束与兜底，不是标准答案" in prompt


def test_insight_prompt_sets_concise_output_budget_for_first_screen_latency():
    prompt = DemandReconstructionInsightProtocol().build_prompt(
        adapter_context={"source_message": RURAL_HOME_PROMPT},
        rule_plan={"task_reframe": "规则蓝图", "sections": []},
    )

    assert "输出要短" in prompt
    assert "sections 最多 2 段" in prompt
    assert "items 每段最多 2 条" in prompt
    assert "总输出控制在 1200 中文字以内" in prompt


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
    assert blueprint["insight_source"] == "semantic_fallback"
    assert blueprint["llm_status"] == "invoke_failed"
    assert blueprint["llm_error"] == "llm unavailable"
    assert "作品化住宅压过真实生活" in result["reply"]


def test_required_llm_failure_raises_explicit_unavailable_error_instead_of_rule_fallback():
    llm = FakeLLM("", raises=True)

    with pytest.raises(DemandReconstructionUnavailable) as exc_info:
        DemandReconstructionService(llm=llm, require_llm=True).handle_message(
            session={},
            user_message=RURAL_HOME_PROMPT,
            in_response_to_card_id=None,
            selected_option_id=None,
        )

    assert exc_info.value.error_code == "UNDERSTANDING_UNAVAILABLE"
    assert exc_info.value.user_message == "智能识别暂不可用，请重试。"
    assert exc_info.value.diagnostics["status"] == "invoke_failed"


def test_required_llm_missing_raises_explicit_unavailable_error_instead_of_rule_fallback():
    with pytest.raises(DemandReconstructionUnavailable) as exc_info:
        DemandReconstructionService(require_llm=True).handle_message(
            session={},
            user_message=RURAL_HOME_PROMPT,
            in_response_to_card_id=None,
            selected_option_id=None,
        )

    assert exc_info.value.error_code == "UNDERSTANDING_UNAVAILABLE"
    assert exc_info.value.user_message == "智能识别暂不可用，请重试。"
    assert exc_info.value.diagnostics["status"] == "not_configured"


def test_required_llm_runs_semantic_router_before_final_synthesis():
    llm = SequentialFakeLLM(
        [
            """
            {
              "intent_type": "specific_project_reconstruction",
              "project_anchor": true,
              "project_object": "返乡民居",
              "space_candidates": [
                {"label": "personal_residential", "confidence": 0.86, "evidence": ["老家建一栋民居"]}
              ],
              "core_tensions": [
                {"title": "职业表达与长期生活之间的张力", "confidence": 0.8, "evidence": ["室内设计师", "老家建一栋民居"]}
              ],
              "missing_slots": ["真实居住频率未知"],
              "novelty_level": "known"
            }
            """,
            """
            {
              "task_reframe": "这不是给设计师做一栋返乡民居的问题，而是他如何把职业表达、原乡关系和后半生生活重新放回同一个日常秩序里。",
              "project_viability_judgment": "项目能否成立，取决于它能否让设计冲动服从长期生活，而不是把家变成证明专业能力的展厅。",
              "primary_risk": "真正的风险是作品表达压过居住韧性，导致房子能被观看，却无法承受重复、琐碎和家族关系的长期进入。",
              "sections": [{"title": "洞察判断", "body": "先判断这栋房子被拿来安放谁，而不是先判断它像什么。", "items": ["职业身份必须被日常使用校准。"], "emphasis": "high"}],
              "key_forks": ["长期居住还是阶段性返乡？"],
              "unknowns": ["真实居住频率未知。"],
              "next_question": "这栋房子首先服务长期生活，还是服务与故乡重新建立关系"
            }
            """,
        ]
    )

    result = DemandReconstructionService(llm=llm, require_llm=True).handle_message(
        session={},
        user_message=RURAL_HOME_PROMPT,
        in_response_to_card_id=None,
        selected_option_id=None,
    )

    assert result is not None
    assert len(llm.prompts) == 2
    assert "LLM Semantic Router" in llm.prompts[0]
    assert "不要直接回答用户" in llm.prompts[0]
    assert "LLM 语义理解包" in llm.prompts[1]
    public_context = result["demand_reconstruction_context"]["adapter_context"]
    assert public_context["llm_semantic_understanding"]["intent_type"] == "specific_project_reconstruction"
    assert public_context["llm_semantic_understanding"]["project_object"] == "返乡民居"


def test_required_llm_semantic_router_drives_rule_scanner_before_blueprint_selection():
    user_message = (
        "一个社区咖啡店希望改造成居民公共客厅，平时卖咖啡，周末承接亲子阅读、"
        "社区展览和邻里议事，请先做需求重构。"
    )
    llm = SequentialFakeLLM(
        [
            """
            {
              "intent_type": "specific_project_reconstruction",
              "project_anchor": true,
              "project_object": "社区公共客厅",
              "space_candidates": [
                {"label": "public_cultural_experience", "confidence": 0.9, "evidence": ["社区展览", "邻里议事", "亲子阅读"]},
                {"label": "commercial_operation", "confidence": 0.56, "evidence": ["卖咖啡"]}
              ],
              "core_tensions": [
                {"title": "公共停留与咖啡经营效率之间的张力", "confidence": 0.88, "evidence": ["居民公共客厅", "卖咖啡"]}
              ],
              "missing_slots": ["公共活动和咖啡经营谁优先"],
              "novelty_level": "known",
              "recommended_scan_targets": ["public_cultural_experience", "commercial_operation"]
            }
            """,
            """
            {
              "task_reframe": "这不是把咖啡店做得更有氛围的问题，而是判断它首先服务社区公共停留，还是服务咖啡经营效率。",
              "project_viability_judgment": "项目可以成立，但前提是先确定公共活动与日常经营的优先级，否则空间会同时拖慢运营和削弱社区使用。",
              "primary_risk": "最大风险是把公共客厅当成咖啡店软装升级，结果展览、亲子阅读和邻里议事都被翻台逻辑挤压。",
              "sections": [{"title": "公共性与经营性的先后", "body": "先判断谁是主任务，再决定咖啡只是支撑还是主业。", "items": ["亲子阅读、社区展览和邻里议事需要稳定停留。"], "emphasis": "high"}],
              "key_forks": ["公共活动优先还是咖啡经营优先？"],
              "unknowns": ["公共活动和咖啡经营谁优先"],
              "next_question": "这个空间首先要提高咖啡经营效率，还是先成为可被居民反复使用的公共客厅"
            }
            """,
        ]
    )

    result = DemandReconstructionService(llm=llm, require_llm=True).handle_message(
        session={},
        user_message=user_message,
        in_response_to_card_id=None,
        selected_option_id=None,
    )

    public_context = result["demand_reconstruction_context"]["adapter_context"]
    blueprint = result["demand_reconstruction_context"]["blueprint"]
    assert public_context["archetype"]["primary"] == "public_cultural_experience"
    assert public_context["semantic_candidate_set"][0]["id"] == "public_cultural_experience"
    assert public_context["semantic_candidate_set"][0]["source"] == "llm_semantic_router"
    assert public_context["context_source"]["llm_semantic_router"] is True
    assert blueprint["archetype"]["primary"] == "public_cultural_experience"


def test_llm_semantic_router_can_drive_specific_blueprint_fragment_selection():
    message = (
        "一个邻里共创驿站要承接手作课、居民讨论、临时内容展示和志愿者排班，"
        "请先帮我做需求重构。"
    )
    package = {
        "intent_type": "specific_project_reconstruction",
        "project_anchor": True,
        "project_object": "邻里共创驿站",
        "space_candidates": [
            {
                "label": "public_cultural_experience",
                "confidence": 0.91,
                "evidence": ["手作课", "居民讨论", "临时内容展示"],
            }
        ],
        "core_tensions": [
            {
                "title": "居民共创活动与日常运营管理之间的张力",
                "confidence": 0.86,
                "evidence": ["志愿者排班", "居民讨论"],
            }
        ],
        "missing_slots": ["手作课、讨论和展示谁是主线"],
        "novelty_level": "known",
        "recommended_scan_targets": ["public_cultural_experience"],
        "recommended_fragment_targets": [
            {
                "group_id": "public_cultural_specialties",
                "fragment_id": "community_culture_center",
                "confidence": 0.88,
                "evidence": ["手作课", "居民讨论", "临时内容展示", "志愿者排班"],
            }
        ],
    }
    service = DemandReconstructionService(require_llm=True, llm=FakeLLM("{}"))
    adapter_context = DemandReconstructionContextAdapter().build(message)

    service._apply_llm_semantic_understanding_to_adapter_context(adapter_context, package)
    plan = DemandReconstructionOutputPlanner().build_plan(adapter_context)

    assert adapter_context["context_source"]["llm_semantic_fragment_targets"] is True
    assert plan["brief_handoff_slots"]["fragment_source"] == (
        "registry:public_cultural_specialties.community_culture_center"
    )
    assert "社区文化中心" in plan["task_reframe"]


def test_required_llm_semantic_router_no_match_prevents_keyword_template_hijack():
    user_message = (
        "一个咖啡店想转型成虚拟偶像线下粉丝共创空间，兼顾沉浸互动、"
        "线下聚会、内容生产和商业转化，请提出空间改造设计概念框架。"
    )
    llm = SequentialFakeLLM(
        [
            """
            {
              "intent_type": "specific_project_reconstruction",
              "project_anchor": true,
              "project_object": "虚拟偶像线下粉丝共创空间",
              "space_candidates": [
                {"label": "virtual_idol_fan_cocreation", "confidence": 0.92, "evidence": ["虚拟偶像线下粉丝共创空间", "沉浸互动", "内容生产"]}
              ],
              "core_tensions": [
                {"title": "粉丝共创与商业转化之间的张力", "confidence": 0.86, "evidence": ["粉丝共创空间", "商业转化"]}
              ],
              "missing_slots": ["粉丝共创、线下聚会和商业转化的优先级未知"],
              "novelty_level": "unknown",
              "recommended_scan_targets": ["virtual_idol_fan_cocreation"]
            }
            """,
            """
            {
              "task_reframe": "这不是咖啡店升级问题，而是一个尚未进入稳定规则库的粉丝共创空间，需要先判断共创、聚会、内容生产和商业转化谁是主任务。",
              "project_viability_judgment": "项目能否成立，取决于它是否能先定义粉丝行为和内容生产机制，而不是直接套用门店经营逻辑。",
              "primary_risk": "最大风险是把未知复合空间压回咖啡店模板，导致沉浸互动和粉丝共创被翻台、客流和消费转化逻辑吞掉。",
              "sections": [{"title": "未知类型的成立逻辑", "body": "先承认它不是现有规则蓝图能完整覆盖的类型。", "items": ["需要建立粉丝共创、内容生产和商业转化的优先级。"], "emphasis": "high"}],
              "key_forks": ["粉丝共创优先还是商业转化优先？"],
              "unknowns": ["粉丝共创、线下聚会和商业转化的优先级未知"],
              "next_question": "这个空间首先服务粉丝共创，还是首先服务商业转化"
            }
            """,
        ]
    )

    result = DemandReconstructionService(llm=llm, require_llm=True).handle_message(
        session={},
        user_message=user_message,
        in_response_to_card_id=None,
        selected_option_id=None,
    )

    public_context = result["demand_reconstruction_context"]["adapter_context"]
    blueprint = result["demand_reconstruction_context"]["blueprint"]
    assert public_context["llm_semantic_scan"]["result"] == "no_match"
    assert public_context["archetype"]["primary"] == "general_project"
    assert public_context["semantic_candidate_set"][0]["id"] == "general_project"
    assert public_context["semantic_candidate_set"][0]["source"] == "llm_semantic_router_no_match"
    assert blueprint["archetype"]["primary"] == "general_project"
    assert "咖啡区" not in result["reply"]
    assert "外带" not in result["reply"]
    assert "补货" not in result["reply"]


def test_required_llm_semantic_router_no_match_creates_knowledge_gap_governance_signal():
    user_message = (
        "一个咖啡店想转型成虚拟偶像线下粉丝共创空间，兼顾沉浸互动、"
        "线下聚会、内容生产和商业转化，请提出空间改造设计概念框架。"
    )
    llm = SequentialFakeLLM(
        [
            """
            {
              "intent_type": "specific_project_reconstruction",
              "project_anchor": true,
              "project_object": "虚拟偶像线下粉丝共创空间",
              "space_candidates": [
                {"label": "virtual_idol_fan_cocreation", "confidence": 0.92, "evidence": ["虚拟偶像线下粉丝共创空间", "沉浸互动", "内容生产"]}
              ],
              "core_tensions": [
                {"title": "粉丝共创与商业转化之间的张力", "confidence": 0.86, "evidence": ["粉丝共创空间", "商业转化"]}
              ],
              "missing_slots": ["粉丝共创、线下聚会和商业转化的优先级未知"],
              "novelty_level": "unknown",
              "recommended_scan_targets": ["virtual_idol_fan_cocreation"]
            }
            """,
            """
            {
              "task_reframe": "这不是咖啡店升级问题，而是一个尚未进入稳定规则库的粉丝共创空间，需要先判断共创、聚会、内容生产和商业转化谁是主任务。",
              "project_viability_judgment": "项目能否成立，取决于它是否能先定义粉丝行为和内容生产机制，而不是直接套用门店经营逻辑。",
              "primary_risk": "最大风险是把未知复合空间压回咖啡店模板，导致沉浸互动和粉丝共创被客流和消费转化逻辑吞掉。",
              "sections": [{"title": "未知类型的成立逻辑", "body": "先承认它不是现有规则蓝图能完整覆盖的类型。", "items": ["需要建立粉丝共创、内容生产和商业转化的优先级。"], "emphasis": "high"}],
              "key_forks": ["粉丝共创优先还是商业转化优先？"],
              "unknowns": ["粉丝共创、线下聚会和商业转化的优先级未知"],
              "next_question": "这个空间首先服务粉丝共创，还是首先服务商业转化"
            }
            """,
        ]
    )

    result = DemandReconstructionService(llm=llm, require_llm=True).handle_message(
        session={},
        user_message=user_message,
        in_response_to_card_id=None,
        selected_option_id=None,
    )

    blueprint = result["demand_reconstruction_context"]["blueprint"]
    signals = blueprint.get("governance_signals") or []
    signal_by_code = {signal.get("code"): signal for signal in signals}
    assert signal_by_code["knowledge_gap_ticket"]["review_queue"] == "knowledge_asset_review"
    assert signal_by_code["new_fragment_candidate"]["review_queue"] == "blueprint_fragment_review"
    assert signal_by_code["knowledge_gap_ticket"]["user_visible"] is False
    assert signal_by_code["new_fragment_candidate"]["user_visible"] is False
    assert signal_by_code["knowledge_gap_ticket"]["source"] == "llm_semantic_router"
    rendered = result["reply"] + str(result["guidance_card"])
    assert "knowledge_gap_ticket" not in rendered
    assert "new_fragment_candidate" not in rendered
    assert "blueprint_fragment_review" not in rendered


def test_required_llm_semantic_router_governance_signals_are_persisted_to_review_queue():
    engine = create_engine("sqlite:///:memory:")
    governance_store = KnowledgeGovernanceStore(engine=engine)
    governance_store.create_all()
    user_message = (
        "一个咖啡店想转型成虚拟偶像线下粉丝共创空间，兼顾沉浸互动、"
        "线下聚会、内容生产和商业转化，请提出空间改造设计概念框架。"
    )
    llm = SequentialFakeLLM(
        [
            """
            {
              "intent_type": "specific_project_reconstruction",
              "project_anchor": true,
              "project_object": "虚拟偶像线下粉丝共创空间",
              "space_candidates": [
                {"label": "virtual_idol_fan_cocreation", "confidence": 0.92, "evidence": ["虚拟偶像线下粉丝共创空间", "沉浸互动", "内容生产"]}
              ],
              "core_tensions": [
                {"title": "粉丝共创与商业转化之间的张力", "confidence": 0.86, "evidence": ["粉丝共创空间", "商业转化"]}
              ],
              "missing_slots": ["粉丝共创、线下聚会和商业转化的优先级未知"],
              "novelty_level": "unknown",
              "recommended_scan_targets": ["virtual_idol_fan_cocreation"]
            }
            """,
            """
            {
              "task_reframe": "这不是咖啡店升级问题，而是一个尚未进入稳定规则库的粉丝共创空间，需要先判断共创、聚会、内容生产和商业转化谁是主任务。",
              "project_viability_judgment": "项目能否成立，取决于它是否能先定义粉丝行为和内容生产机制，而不是直接套用门店经营逻辑。",
              "primary_risk": "最大风险是把未知复合空间压回咖啡店模板，导致沉浸互动和粉丝共创被客流和消费转化逻辑吞掉。",
              "sections": [{"title": "未知类型的成立逻辑", "body": "先承认它不是现有规则蓝图能完整覆盖的类型。", "items": ["需要建立粉丝共创、内容生产和商业转化的优先级。"], "emphasis": "high"}],
              "key_forks": ["粉丝共创优先还是商业转化优先？"],
              "unknowns": ["粉丝共创、线下聚会和商业转化的优先级未知"],
              "next_question": "这个空间首先服务粉丝共创，还是首先服务商业转化"
            }
            """,
        ]
    )

    result = DemandReconstructionService(
        llm=llm,
        require_llm=True,
        governance_store=governance_store,
    ).handle_message(
        session={"tenant_id": "tenant-1", "workspace_id": "workspace-1", "user_id": "user-1"},
        user_message=user_message,
        in_response_to_card_id=None,
        selected_option_id=None,
    )

    items = governance_store.list_review_items(tenant_id="tenant-1", workspace_id="workspace-1")
    codes = {item["metadata"]["code"] for item in items}
    assert {"coverage_gap", "knowledge_gap_ticket", "new_fragment_candidate"}.issubset(codes)
    assert {item["module"] for item in items} == {"demand_reconstruction"}
    assert {item["review_status"] for item in items} == {"pending"}
    blueprint = result["demand_reconstruction_context"]["blueprint"]
    assert blueprint["governance_persistence"]["status"] == "queued_for_review"
    assert blueprint["governance_persistence"]["queued_count"] == len(items)
    rendered = result["reply"] + str(result["guidance_card"])
    assert "knowledge_gap_ticket" not in rendered
    assert "blueprint_fragment_review" not in rendered


def test_required_llm_semantic_router_uses_approved_governance_knowledge_assets_in_synthesis():
    engine = create_engine("sqlite:///:memory:")
    governance_store = KnowledgeGovernanceStore(engine=engine)
    governance_store.create_all()
    governance_store.create_asset_draft(
        draft_id="demand_gap_special_children_classroom",
        tenant_id="tenant-1",
        workspace_id="workspace-1",
        user_id="user-1",
        payload={
            "title": "特殊儿童康复教室 知识缺口候选",
            "knowledge_status": "candidate",
            "project_type": "特殊儿童康复教室",
            "summary": "此类项目需要先确认感统训练、安静恢复、家长等待和安全看护之间的主次。",
            "evidence": ["特殊儿童康复教室", "感统训练", "安静恢复", "家长等待"],
            "package_ids": ["special_children_rehab_classroom"],
            "ontology_dimension_ids": ["sensory_recovery_boundary"],
            "allowed_use": ["仅用于需求重构阶段提醒覆盖边界和关键未知项。"],
            "not_allowed_use": ["不得直接输出施工级康复医疗标准。"],
            "evidence_level": "expert_review",
        },
        source_ref={"source": "test"},
        created_by="reviewer",
    )
    governance_store.approve_asset_draft(
        draft_id="demand_gap_special_children_classroom",
        tenant_id="tenant-1",
        workspace_id="workspace-1",
        reviewer_id="reviewer",
    )
    user_message = "一个特殊儿童康复教室，需要兼顾感统训练、安静恢复、家长等待和安全看护，请先帮我重构需求。"
    llm = SequentialFakeLLM(
        [
            """
            {
              "intent_type": "specific_project_reconstruction",
              "project_anchor": true,
              "project_object": "特殊儿童康复教室",
              "space_candidates": [
                {"label": "special_children_rehab_classroom", "confidence": 0.9, "evidence": ["特殊儿童康复教室", "感统训练", "安静恢复"]}
              ],
              "core_tensions": [
                {"title": "训练刺激与安静恢复之间的张力", "confidence": 0.86, "evidence": ["感统训练", "安静恢复"]}
              ],
              "missing_slots": ["训练、恢复、等候和看护的优先级未知"],
              "novelty_level": "unknown",
              "recommended_scan_targets": ["special_children_rehab_classroom"]
            }
            """,
            """
            {
              "task_reframe": "这不是普通教室设计，而是先判断训练刺激、安静恢复、家长等待和安全看护如何排序。",
              "project_viability_judgment": "项目可以先按治理知识资产提示做需求重构，但仍需确认专科边界。",
              "primary_risk": "最大风险是把康复教室简化为儿童活动室，忽视安静恢复和安全看护。",
              "sections": [{"title": "治理知识资产提示", "body": "需先确认感统训练、安静恢复、家长等待和安全看护的主次。", "items": ["不能直接输出施工级康复医疗标准。"], "emphasis": "high"}],
              "key_forks": ["训练刺激优先还是安静恢复优先？"],
              "unknowns": ["训练、恢复、等候和看护的优先级未知"],
              "next_question": "这个康复教室首先服务训练刺激，还是首先服务安静恢复"
            }
            """,
        ]
    )

    result = DemandReconstructionService(
        llm=llm,
        require_llm=True,
        governance_store=governance_store,
    ).handle_message(
        session={"tenant_id": "tenant-1", "workspace_id": "workspace-1", "user_id": "user-1"},
        user_message=user_message,
        in_response_to_card_id=None,
        selected_option_id=None,
    )

    public_context = result["demand_reconstruction_context"]["adapter_context"]
    assets = public_context["governed_knowledge_assets"]
    assert assets[0]["card_id"] == "demand_gap_special_children_classroom"
    assert assets[0]["title"] == "特殊儿童康复教室 知识缺口候选"
    assert assets[0]["package_ids"] == ["special_children_rehab_classroom"]
    assert assets[0]["ontology_dimension_ids"] == ["sensory_recovery_boundary"]
    assert assets[0]["match_metadata"]["decision"] == "accepted"
    assert assets[0]["match_metadata"]["package_hits"] == ["special_children_rehab_classroom"]
    assert '"governed_knowledge_assets"' in llm.prompts[1]
    assert "特殊儿童康复教室 知识缺口候选" in llm.prompts[1]


def test_required_llm_semantic_router_partial_match_marks_limited_coverage_for_synthesis():
    user_message = (
        "一个社区图书馆希望改造儿童阅读区，包含亲子阅读、绘本活动、安静学习、"
        "借阅管理和特殊儿童友好使用，请先帮我重构需求。"
    )
    llm = SequentialFakeLLM(
        [
            """
            {
              "intent_type": "specific_project_reconstruction",
              "project_anchor": true,
              "project_object": "特殊儿童友好社区图书馆阅读区",
              "space_candidates": [
                {"label": "public_cultural_experience", "confidence": 0.82, "evidence": ["社区图书馆", "儿童阅读区", "亲子阅读"]},
                {"label": "healthcare_care", "confidence": 0.54, "evidence": ["特殊儿童友好使用"]}
              ],
              "core_tensions": [
                {"title": "公共阅读秩序与特殊儿童友好支持之间的张力", "confidence": 0.84, "evidence": ["安静学习", "特殊儿童友好使用"]}
              ],
              "missing_slots": ["特殊儿童友好使用的具体行为边界未知"],
              "novelty_level": "partial_unknown",
              "recommended_scan_targets": ["public_cultural_experience", "healthcare_care"]
            }
            """,
            """
            {
              "task_reframe": "这不是普通儿童阅读区改造，而是要判断公共图书馆秩序能否部分吸收特殊儿童友好使用的支持机制。",
              "project_viability_judgment": "项目可以成立，但只能先做邻近迁移判断，不能把公共文化规则直接当成特殊儿童友好专科结论。",
              "primary_risk": "最大风险是把特殊儿童友好支持简化成儿童区软装，导致安静学习、亲子阅读和感统友好需求互相冲突。",
              "sections": [{"title": "公共阅读与友好支持的边界", "body": "先承认现有公共文化碎片只能覆盖一部分问题。", "items": ["特殊儿童友好使用需要单独确认行为和安全边界。"], "emphasis": "high"}],
              "key_forks": ["公共阅读秩序优先还是特殊儿童友好支持优先？"],
              "unknowns": ["特殊儿童友好使用的具体行为边界未知"],
              "next_question": "这个儿童阅读区首先服务普通阅读秩序，还是需要优先支持特殊儿童友好使用"
            }
            """,
        ]
    )

    result = DemandReconstructionService(llm=llm, require_llm=True).handle_message(
        session={},
        user_message=user_message,
        in_response_to_card_id=None,
        selected_option_id=None,
    )

    public_context = result["demand_reconstruction_context"]["adapter_context"]
    blueprint = result["demand_reconstruction_context"]["blueprint"]
    signals = blueprint.get("governance_signals") or []
    signal_by_code = {signal.get("code"): signal for signal in signals}
    assert public_context["llm_semantic_scan"]["result"] == "partial_match"
    assert public_context["knowledge_coverage_ceiling"]["coverage_level"] == "partial_specialist"
    assert blueprint["coverage_level"] == "partial_specialist"
    assert signal_by_code["knowledge_coverage_watch"]["review_queue"] == "coverage_watch_pool"
    assert '"llm_semantic_scan"' in llm.prompts[1]
    assert "partial_match" in llm.prompts[1]
    assert "partial_specialist" in llm.prompts[1]


def test_llm_semantic_router_partial_match_sets_coverage_ceiling_without_adapter_help():
    service = DemandReconstructionService(require_llm=True)
    adapter_context = {
        "classification": {},
        "semantic_candidate_set": [
            {
                "id": "general_project",
                "score": 10,
                "role": "primary",
                "evidence": ["兜底"],
                "counter_evidence": [],
            }
        ],
        "context_source": {},
    }
    package = {
        "project_object": "特殊儿童友好社区图书馆阅读区",
        "space_candidates": [
            {
                "label": "public_cultural_experience",
                "confidence": 0.8,
                "evidence": ["社区图书馆", "儿童阅读区"],
            }
        ],
        "core_tensions": [
            {
                "title": "公共阅读秩序与特殊儿童友好支持之间的张力",
                "confidence": 0.82,
                "evidence": ["安静学习", "特殊儿童友好使用"],
            }
        ],
        "novelty_level": "partial_unknown",
        "recommended_scan_targets": ["public_cultural_experience"],
    }

    service._apply_llm_semantic_understanding_to_adapter_context(adapter_context, package)

    coverage = adapter_context["knowledge_coverage_ceiling"]
    assert coverage["coverage_level"] == "partial_specialist"
    assert coverage["source"] == "llm_semantic_router"
    assert coverage["must_not_claim_specialist_coverage"] is True
    assert adapter_context["classification"]["knowledge_gap_ticket"]["gap_type"] == "llm_semantic_partial_match"


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
    assert blueprint["insight_source"] == "semantic_fallback"
    assert blueprint["llm_status"] == "quality_rejected"
    assert blueprint["llm_rejection_reason"] in {"too_short", "missing_required_fields", "over_reaching"}
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
    assert blueprint["insight_source"] == "semantic_fallback"
    assert blueprint["llm_status"] == "quality_rejected"
    assert blueprint["llm_rejection_reason"] == "cliche"
    assert "温馨舒适的品质生活" not in result["reply"]


def test_quality_rejected_llm_output_gets_one_repair_attempt_before_fallback():
    llm = SequentialFakeLLM(
        [
            """
            {
              "task_reframe": "这个项目是为用户打造温馨舒适的品质生活空间，满足业主对于现代乡村民居的整体需求。",
              "project_viability_judgment": "项目整体可以成立，重点是打造简约大气、自然和谐、有归属感的居住环境。",
              "primary_risk": "主要风险是功能不够齐全、动线不够合理，影响后续空间利用率和居住体验。",
              "sections": [{"title": "泛化判断", "body": "通过合理布局营造品质生活。", "items": ["功能齐全。"], "emphasis": "medium"}],
              "key_forks": ["喜欢现代还是传统？"],
              "unknowns": ["面积未知。"],
              "next_question": "你喜欢什么风格"
            }
            """,
            """
            {
              "task_reframe": "这不是给设计师做一栋返乡民居的问题，而是他如何把职业表达、原乡关系和后半生生活重新放回同一个日常秩序里。",
              "project_viability_judgment": "项目能否成立，取决于它能否让设计冲动服从长期生活，而不是把家变成证明专业能力的展厅。",
              "primary_risk": "真正的风险是作品表达压过居住韧性，导致房子能被观看，却无法承受重复、琐碎和家族关系的长期进入。",
              "sections": [{"title": "洞察判断", "body": "先判断这栋房子被拿来安放谁，而不是先判断它像什么。", "items": ["职业身份必须被日常使用校准。", "故乡关系会改变公共与私密边界。"], "emphasis": "high"}],
              "key_forks": ["长期居住还是阶段性返乡？", "家族关系进入日常还是只进入节庆？"],
              "unknowns": ["真实居住频率未知。", "家庭成员结构未知。"],
              "next_question": "这栋房子首先服务长期生活，还是服务与故乡重新建立关系"
            }
            """,
        ]
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
    assert blueprint["llm_status"] == "used"
    assert len(llm.prompts) == 2
    assert "上一次输出被需求重构协议门拒绝" in llm.prompts[1]
    assert "cliche" in llm.prompts[1]
    assert "作品表达压过居住韧性" in result["reply"]
    assert "温馨舒适的品质生活" not in result["reply"]


def test_invalid_json_llm_output_gets_one_repair_attempt_before_fallback():
    llm = SequentialFakeLLM(
        [
            "我会先分析这个项目，然后给出结构：task_reframe: 这是一个返乡民居问题",
            """
            {
              "task_reframe": "这不是给设计师做一栋返乡民居的问题，而是他如何把职业表达、原乡关系和后半生生活重新放回同一个日常秩序里。",
              "project_viability_judgment": "项目能否成立，取决于它能否让设计冲动服从长期生活，而不是把家变成证明专业能力的展厅。",
              "primary_risk": "真正的风险是作品表达压过居住韧性，导致房子能被观看，却无法承受重复、琐碎和家族关系的长期进入。",
              "sections": [{"title": "洞察判断", "body": "先判断这栋房子被拿来安放谁，而不是先判断它像什么。", "items": ["职业身份必须被日常使用校准。", "故乡关系会改变公共与私密边界。"], "emphasis": "high"}],
              "key_forks": ["长期居住还是阶段性返乡？", "家族关系进入日常还是只进入节庆？"],
              "unknowns": ["真实居住频率未知。", "家庭成员结构未知。"],
              "next_question": "这栋房子首先服务长期生活，还是服务与故乡重新建立关系"
            }
            """,
        ]
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
    assert blueprint["llm_status"] == "used"
    assert len(llm.prompts) == 2
    assert "invalid_json" in llm.prompts[1]
    assert "作品表达压过居住韧性" in result["reply"]


def test_rule_blueprint_records_that_llm_was_not_configured():
    result = DemandReconstructionService().handle_message(
        session={},
        user_message=RURAL_HOME_PROMPT,
        in_response_to_card_id=None,
        selected_option_id=None,
    )

    assert result is not None
    blueprint = result["demand_reconstruction_context"]["blueprint"]
    assert blueprint["insight_source"] == "semantic_fallback"
    assert blueprint["llm_status"] == "not_configured"


def test_component_intent_carries_user_facing_payload():
    prompt = (
        "一位美食作家兼KOL希望将厨房设计为“美食实验室”，既满足日常烹饪，"
        "也适合高质量拍摄与视频录制。请提出完整设计方案，包括操作动线优化、"
        "灯光布置系统、背景可替换模块与油烟控制机制。"
    )
    result = DemandReconstructionService().handle_message(
        session={},
        user_message=prompt,
        in_response_to_card_id=None,
        selected_option_id=None,
    )

    assert result is not None
    blueprint = result["demand_reconstruction_context"]["blueprint"]
    intents = blueprint["component_intent"]
    conflict_intent = next(item for item in intents if item["type"] == "conflict_check")
    checklist_intent = next(item for item in intents if item["type"] == "data_checklist")

    assert conflict_intent["items"]
    assert conflict_intent["prompt"]
    assert checklist_intent["items"]


_CLEAN_LLM_RESPONSE = """
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


def _force_blocking_alignment(monkeypatch):
    monkeypatch.setattr(
        "intelligent_project_analyzer.modules.demand_reconstruction.alignment_gate.evaluate_semantic_alignment",
        lambda *args, **kwargs: [
            {"code": "wrong_domain_reference", "severity": "blocking", "message": "forced"}
        ],
    )


def test_alignment_hard_gate_rejects_blocking_llm_blueprint_by_default(monkeypatch):
    monkeypatch.delenv("DEMAND_RECONSTRUCTION_ALIGNMENT_GATE", raising=False)
    _force_blocking_alignment(monkeypatch)
    llm = FakeLLM(_CLEAN_LLM_RESPONSE)

    result = DemandReconstructionService(llm=llm).handle_message(
        session={},
        user_message=RURAL_HOME_PROMPT,
        in_response_to_card_id=None,
        selected_option_id=None,
    )

    assert result is not None
    blueprint = result["demand_reconstruction_context"]["blueprint"]
    assert blueprint["insight_source"] == "semantic_fallback"
    assert blueprint["llm_status"] == "alignment_gate_rejected"
    assert blueprint["alignment_gate"]["action"] == "llm_rejected"
    assert "wrong_domain_reference" in blueprint["alignment_gate"]["codes"]
    alignment_signals = [
        signal for signal in blueprint.get("governance_signals", [])
        if signal.get("code") == "semantic_alignment_rejection"
    ]
    assert alignment_signals
    assert alignment_signals[0]["review_queue"] == "wrong_domain_output_review"
    assert "wrong_domain_reference" in alignment_signals[0]["source_codes"]
    # The drifted LLM phrasing must not survive into the user-visible reply.
    assert "最后一件作品" not in result["reply"]
    assert "semantic_alignment_rejection" not in result["reply"]
    assert "wrong_domain_output_review" not in result["reply"]


def test_alignment_gate_can_be_disabled_for_shadow_only_diagnostics(monkeypatch):
    monkeypatch.setenv("DEMAND_RECONSTRUCTION_ALIGNMENT_GATE", "0")
    _force_blocking_alignment(monkeypatch)
    llm = FakeLLM(_CLEAN_LLM_RESPONSE)

    result = DemandReconstructionService(llm=llm).handle_message(
        session={},
        user_message=RURAL_HOME_PROMPT,
        in_response_to_card_id=None,
        selected_option_id=None,
    )

    assert result is not None
    blueprint = result["demand_reconstruction_context"]["blueprint"]
    # Explicit diagnostic mode: the gate observes but never alters the output.
    assert blueprint["insight_source"] == "llm"
    assert "alignment_gate" not in blueprint
    assert blueprint["semantic_alignment_shadow"]["blocking_count"] == 1
    assert "最后一件作品" in result["reply"]

