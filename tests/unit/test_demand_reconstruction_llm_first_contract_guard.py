from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "intelligent_project_analyzer/services/demand_reconstruction_service.py"
ROUTE = ROOT / "intelligent_project_analyzer/api/dual_mode_routes.py"
DOC = ROOT / "docs/development/方案高参需求重构运行时开发纲领.md"


def test_demand_reconstruction_service_keeps_llm_first_semantic_router_contract() -> None:
    source = SERVICE.read_text(encoding="utf-8")

    assert "class DemandReconstructionUnavailable" in source
    assert "def _build_llm_semantic_understanding" in source
    assert "LLM Semantic Router" in source
    assert "UNDERSTANDING_UNAVAILABLE" in source
    assert "SYNTHESIS_UNAVAILABLE" in source
    assert "semantic_fallback" in source


def test_conversation_route_maps_required_llm_unavailability_to_http_503() -> None:
    source = ROUTE.read_text(encoding="utf-8")

    assert "DemandReconstructionUnavailable" in source
    assert "DEMAND_RECONSTRUCTION_USE_LLM" in source
    assert "status_code=503" in source
    assert "exc.error_code" in source


def test_runtime_doctrine_does_not_reintroduce_silent_rule_fallback_for_llm_first() -> None:
    text = DOC.read_text(encoding="utf-8")

    assert "不得静默退回旧规则蓝图" in text
    assert "UNDERSTANDING_UNAVAILABLE" in text
    assert "SYNTHESIS_UNAVAILABLE" in text
    assert "关闭或失败时，系统必须继续返回规则蓝图" not in text