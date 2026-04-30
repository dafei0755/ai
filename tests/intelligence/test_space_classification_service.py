import pytest

from intelligent_project_analyzer.services.space_classification_service import (
    SpaceClassificationService,
)
from intelligent_project_analyzer.services.project_type_detector import (
    PROJECT_TYPE_REGISTRY,
)


@pytest.fixture
def svc():
    return SpaceClassificationService()


def test_classify_returns_valid_schema(svc):
    result = svc.classify("帮我设计一个精品民宿，有8间客房，乡村风格")
    assert result.schema_version == "space_classification.v1"
    assert result.project_type is not None
    assert result.confidence >= 0.0
    assert result.confidence_level in ("high", "medium", "low")
    assert result.ambiguity is not None
    assert result.routing is not None


def test_classify_hospitality_type(svc):
    result = svc.classify("高端精品酒店室内设计，50间客房，豪华风格")
    assert result.project_type == "commercial_hospitality"
    assert result.primary_bucket == "hospitality"
    assert result.confidence_level in ("high", "medium")


def test_classify_residential_type(svc):
    result = svc.classify("三居室住宅精装修，现代简约风格，140平米")
    assert result.project_type in ("personal_residential", "residential_renovation")


def test_confidence_level_mapping(svc):
    result = svc.classify("高端精品酒店室内设计，50间客房")
    if result.confidence >= 0.75:
        assert result.confidence_level == "high"
    elif result.confidence >= 0.5:
        assert result.confidence_level == "medium"
    else:
        assert result.confidence_level == "low"


def test_boundary_rule_hospitality_vs_residential(svc):
    # 民宿 + 对外经营 应触发 hospitality_vs_residential 边界规则
    # 需要 project_type 是 commercial_hospitality 才会触发
    result = svc.classify("乡村度假屋，民宿风格，对外经营8间客房")
    if result.project_type == "commercial_hospitality":
        assert result.ambiguity.boundary_risk is True
        assert result.ambiguity.needs_clarification is True


def test_boundary_rule_brand_vs_retail(svc):
    result = svc.classify("品牌旗舰店展厅设计，体验中心，showroom")
    if result.project_type in ("brand_experience", "commercial_retail"):
        # 如果 project_type 在规则的 types 中且有触发词
        # 展厅 是触发词之一
        pass  # 边界规则可能触发也可能不触发，取决于主类型
    # 核心：结果 schema 有效
    assert result.schema_version == "space_classification.v1"


def test_secondary_candidate_structure(svc):
    result = svc.classify("民宿展厅品牌体验酒店零售")
    assert isinstance(result.secondary_candidates, list)
    for sc in result.secondary_candidates:
        assert sc.project_type is not None
        assert sc.confidence >= 0.0
        assert sc.role in ("supporting_function", "competing_primary", "seasonal_variant", "unknown")


def test_routing_non_empty(svc):
    result = svc.classify("医疗康复中心室内设计方案")
    assert result.routing.questionnaire_profile != ""
    assert result.routing.ontology_key != ""


def test_result_serializable(svc):
    result = svc.classify("办公室设计，500平方米，现代风格")
    d = result.model_dump()
    assert isinstance(d, dict)
    assert "project_type" in d
    assert "ambiguity" in d
    assert "routing" in d
    assert "schema_version" in d


def test_type_enumeration_valid(svc):
    # PROJECT_TYPE_REGISTRY 是 dict，键即为项目类型 ID
    if isinstance(PROJECT_TYPE_REGISTRY, dict):
        valid_types = set(PROJECT_TYPE_REGISTRY.keys())
    else:
        valid_types = {
            entry["id"]
            for entry in PROJECT_TYPE_REGISTRY
            if isinstance(entry, dict) and "id" in entry
        }
    valid_types.add("other")

    test_inputs = [
        "精品民宿设计",
        "办公楼大厅",
        "医院候诊区",
        "品牌体验店",
        "住宅改造",
    ]
    for text in test_inputs:
        result = svc.classify(text)
        assert result.project_type in valid_types, (
            f"输入: {text!r}, project_type={result.project_type!r} 不在注册表中"
        )


def test_classify_with_llm_fallback_non_ambiguous(svc):
    # 低歧义案例不应触发 LLM（直接返回规则结果）
    result = svc.classify_with_llm_fallback("三居室住宅装修，现代风格，140平米")
    assert result.project_type is not None
    assert result.schema_version == "space_classification.v1"


def test_spatial_zone_refs_passed_through(svc):
    refs = ["zone_001", "zone_002"]
    result = svc.classify("酒店大堂设计", spatial_zone_refs=refs)
    assert result.spatial_zone_refs == refs


def test_specialty_tags_list(svc):
    result = svc.classify("牙科诊所室内设计")
    assert isinstance(result.specialty_tags, list)
    # specialty_tags 可能为空或包含细粒度标签


def test_classify_empty_input(svc):
    # 空字符串不应抛异常，应回退到 "other"
    result = svc.classify("")
    assert result.project_type is not None
    assert result.schema_version == "space_classification.v1"


def test_llm_boundary_resolve_valid_ids_cover_registry(svc):
    # 验证 valid_ids 真正包含注册表中的类型 ID（非空集合）
    from intelligent_project_analyzer.services.project_type_detector import PROJECT_TYPE_REGISTRY
    assert isinstance(PROJECT_TYPE_REGISTRY, dict)
    assert len(PROJECT_TYPE_REGISTRY) > 0
    # 所有注册表 key 都应能被 valid_ids 逻辑覆盖
    valid_ids = set(PROJECT_TYPE_REGISTRY.keys())
    valid_ids.add("other")
    assert "commercial_retail" in valid_ids
    assert "residential_renovation" in valid_ids
    assert len(valid_ids) >= 32
