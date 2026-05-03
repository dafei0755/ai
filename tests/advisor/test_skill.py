import pytest
from unittest.mock import patch, MagicMock
from intelligent_project_analyzer.advisor.skill_registry import SkillRegistry
from intelligent_project_analyzer.advisor.skills.requirement_structuring import (
    RequirementStructuringSkill, SkillInput, SkillOutput,
)


@pytest.fixture
def skill():
    registry = SkillRegistry()
    with patch("intelligent_project_analyzer.advisor.skills.requirement_structuring.LLMFactory.create_llm") as mock_factory:
        mock_factory.return_value = MagicMock()
        yield RequirementStructuringSkill(registry)


def test_skill_registered_in_manifest(skill):
    """红线：Skill 必须从 SkillManifest 选取"""
    registry = SkillRegistry()
    manifest = registry.require("req_structuring_v1")
    assert manifest.skill_id == "req_structuring_v1"
    assert manifest.side_effect_level == "none"


def test_empty_input_raises_422(skill):
    """红线：空输入返回 422"""
    with pytest.raises(ValueError) as exc:
        skill.run(SkillInput(project_id="p1", raw_description=""))
    assert "422" in str(exc.value)


def test_output_is_structured(skill):
    """红线：Skill 输出必须结构化（Pydantic 验证通过）"""
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content="""{
        "project_type": "民宿",
        "location": "山地",
        "key_requirements": ["设计感", "自然融合"],
        "missing_fields": ["面积", "房间数"],
        "confidence": "medium"
    }""")
    with patch.object(skill, "_llm", mock_llm):
        result = skill.run(SkillInput(project_id="p1", raw_description="山地民宿，注重自然融合"))
    assert isinstance(result, SkillOutput)
    assert result.evidence_status in ("none", "internal_hint", "verified")
    assert result.confidence in ("high", "medium", "low")
    assert isinstance(result.structured_data, dict)


def test_llm_parse_error_falls_back(skill):
    """LLM 解析失败时走 fallback（返回 partial + low_confidence）"""
    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = Exception("LLM timeout")
    with patch.object(skill, "_llm", mock_llm):
        result = skill.run(SkillInput(project_id="p1", raw_description="民宿设计"))
    assert result.confidence == "low"
    assert result.evidence_status == "none"


def test_output_required_fields_present(skill):
    """输出必须包含 output_contract.required 定义的所有字段"""
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content='{"project_type":"民宿","confidence":"high"}')
    with patch.object(skill, "_llm", mock_llm):
        result = skill.run(SkillInput(project_id="p1", raw_description="民宿设计"))
    assert hasattr(result, "structured_data")
    assert hasattr(result, "evidence_status")
    assert hasattr(result, "confidence")
