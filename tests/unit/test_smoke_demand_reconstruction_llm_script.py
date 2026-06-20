import importlib
import runpy
import sys
from pathlib import Path

import pytest


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeHttp:
    def __init__(self, payload):
        self.payload = payload
        self.post_calls = 0
        self.post_kwargs = None
        self.get_calls = 0

    def post(self, *args, **kwargs):
        self.post_calls += 1
        self.post_kwargs = kwargs
        return _FakeResponse(self.payload)

    def get(self, *args, **kwargs):
        self.get_calls += 1
        raise AssertionError("sync smoke must not poll session after an initial LLM-used response")


def _used_response():
    return {
        "session_id": "session-sync",
        "intent": "demand_reconstruction_blueprint",
        "demand_reconstruction_context": {
            "blueprint": {
                "insight_source": "llm",
                "llm_status": "used",
                "task_reframe": "这不是直接做风格的问题，而是先判断空间成立条件与真实使用边界。",
                "primary_risk": "如果先做方案，很容易把真实约束压成装饰表达，导致后续判断跑偏。",
                "routing_recommendation": "建议继续需求重构，把关键分叉和缺失条件补齐后再进入任务书。",
                "next_question": "先确认这个空间最不能牺牲的是使用效率、展示表达还是运营弹性",
                "key_forks": ["使用效率优先", "展示表达优先"],
                "unknowns": ["真实使用频率未知", "预算边界未知"],
                "sections": [
                    {"title": "判断一", "body": "先抓成立条件。"},
                    {"title": "判断二", "body": "再抓缺失条件。"},
                ],
            }
        },
    }


def _fallback_response():
    payload = _used_response()
    blueprint = payload["demand_reconstruction_context"]["blueprint"]
    blueprint["insight_source"] = "semantic_fallback"
    blueprint["llm_status"] = "not_configured"
    return payload


def _partial_response():
    payload = _used_response()
    blueprint = payload["demand_reconstruction_context"]["blueprint"]
    blueprint["insight_source"] = "llm_partial"
    blueprint["llm_status"] = "partial"
    return payload


def _legacy_pending_response():
    payload = _used_response()
    blueprint = payload["demand_reconstruction_context"]["blueprint"]
    blueprint["insight_source"] = "rule_pending_llm"
    blueprint["llm_status"] = "scheduled"
    return payload


def _unknown_nonfinal_response():
    payload = _used_response()
    blueprint = payload["demand_reconstruction_context"]["blueprint"]
    blueprint["insight_source"] = "semantic_working"
    blueprint["llm_status"] = "processing"
    return payload


def test_demand_reconstruction_smoke_accepts_initial_sync_llm_result_without_polling():
    smoke = importlib.import_module("scripts.smoke_demand_reconstruction_llm")
    http = _FakeHttp(_used_response())

    result = smoke.run_case(
        http=http,
        base_url="http://127.0.0.1:8001",
        user_id="dev_user",
        case=smoke.CASES[0],
        poll_seconds=0,
        timeout_seconds=0.1,
    )

    assert result["session_id"] == "session-sync"
    assert result["source"] == "llm"
    assert result["status"] == "used"
    assert http.post_calls == 1
    assert http.get_calls == 0


def test_demand_reconstruction_smoke_uses_configured_request_timeout():
    smoke = importlib.import_module("scripts.smoke_demand_reconstruction_llm")
    http = _FakeHttp(_used_response())

    smoke.run_case(
        http=http,
        base_url="http://127.0.0.1:8001",
        user_id="dev_user",
        case=smoke.CASES[0],
        poll_seconds=0,
        timeout_seconds=75,
    )

    assert http.post_kwargs["timeout"] == 75


def test_demand_reconstruction_smoke_summary_accepts_partial_fused_result(monkeypatch, capsys):
    smoke = importlib.import_module("scripts.smoke_demand_reconstruction_llm")

    class _FakeSession:
        trust_env = False

        def post(self, *args, **kwargs):
            return _FakeResponse(_partial_response())

    monkeypatch.setattr(smoke.requests, "Session", lambda: _FakeSession())
    monkeypatch.setattr(smoke, "_format_local_llm_config", lambda: "local LLM config: ready=True")
    monkeypatch.setattr(
        smoke.sys,
        "argv",
        [
            "smoke_demand_reconstruction_llm.py",
            "--case",
            smoke.CASES[0].name,
        ],
    )

    assert smoke.main() == 0
    output = capsys.readouterr().out
    assert "source=llm_partial, status=partial" in output
    assert "ALL PASSED: 1/1 demand-reconstruction cases reached final fused first response." in output
    assert "reached LLM used" not in output


def test_demand_reconstruction_smoke_fails_fast_on_legacy_async_pending_state():
    smoke = importlib.import_module("scripts.smoke_demand_reconstruction_llm")
    http = _FakeHttp(_legacy_pending_response())

    with pytest.raises(RuntimeError, match="legacy async demand reconstruction path"):
        smoke.run_case(
            http=http,
            base_url="http://127.0.0.1:8001",
            user_id="dev_user",
            case=smoke.CASES[0],
            poll_seconds=0,
            timeout_seconds=0.1,
        )

    assert http.post_calls == 1
    assert http.get_calls == 0


def test_demand_reconstruction_smoke_fails_when_first_response_is_semantic_fallback():
    smoke = importlib.import_module("scripts.smoke_demand_reconstruction_llm")
    http = _FakeHttp(_fallback_response())

    with pytest.raises(RuntimeError, match="LLM was not used in the first response"):
        smoke.run_case(
            http=http,
            base_url="http://127.0.0.1:8001",
            user_id="dev_user",
            case=smoke.CASES[0],
            poll_seconds=0,
            timeout_seconds=0.1,
        )

    assert http.post_calls == 1
    assert http.get_calls == 0


def test_demand_reconstruction_smoke_fails_fast_on_any_nonfinal_first_response():
    smoke = importlib.import_module("scripts.smoke_demand_reconstruction_llm")
    http = _FakeHttp(_unknown_nonfinal_response())

    with pytest.raises(RuntimeError, match="first response was not a final fused demand reconstruction result"):
        smoke.run_case(
            http=http,
            base_url="http://127.0.0.1:8001",
            user_id="dev_user",
            case=smoke.CASES[0],
            poll_seconds=0,
            timeout_seconds=0.1,
        )

    assert http.post_calls == 1
    assert http.get_calls == 0


def test_demand_reconstruction_smoke_formats_redacted_local_llm_config(monkeypatch):
    smoke = importlib.import_module("scripts.smoke_demand_reconstruction_llm")
    for name in (
        "DEMAND_RECONSTRUCTION_LLM_PROVIDER",
        "DEMAND_RECONSTRUCTION_LLM_FALLBACK_PROVIDERS",
        "DEMAND_RECONSTRUCTION_LLM_API_KEY",
        "DEMAND_RECONSTRUCTION_LLM_MODEL",
        "DEMAND_RECONSTRUCTION_LLM_BASE_URL",
        "DEMAND_RECONSTRUCTION_LLM_OPENROUTER_API_KEY",
        "DEMAND_RECONSTRUCTION_LLM_OPENROUTER_MODEL",
        "OPENROUTER_API_KEY",
        "OPENROUTER_MODEL",
        "DEMAND_RECONSTRUCTION_LLM_MAX_TOKENS",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DEMAND_RECONSTRUCTION_USE_LLM", "1")
    monkeypatch.setenv("DEMAND_RECONSTRUCTION_LLM_DIRECT", "1")
    monkeypatch.setenv("LLM_AUTO_FALLBACK", "false")
    monkeypatch.setenv("LLM_PROVIDER", "qwen")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-secret-smoke")
    monkeypatch.setenv("QWEN_MODEL", "qwen3.7-max")
    monkeypatch.setenv("DEMAND_RECONSTRUCTION_LLM_MAX_TOKENS", "1200")

    rendered = smoke._format_local_llm_config()

    assert "ready=True" in rendered
    assert "max_tokens=1200" in rendered
    assert "qwen(key=yes" in rendered
    assert "qwen3.7-max" in rendered
    assert "sk-secret-smoke" not in rendered


def test_demand_reconstruction_smoke_bootstraps_repo_root_when_run_as_script(monkeypatch):
    root = Path(__file__).resolve().parents[2]
    script = root / "scripts" / "smoke_demand_reconstruction_llm.py"
    original_path = list(sys.path)
    monkeypatch.setattr(
        sys,
        "path",
        [
            str(script.parent),
            *[
                item
                for item in original_path
                if Path(item or ".").resolve() not in {root, script.parent}
            ],
        ],
    )
    monkeypatch.delitem(sys.modules, "intelligent_project_analyzer", raising=False)

    module_globals = runpy.run_path(str(script), run_name="smoke_path_probe")

    rendered = module_globals["_format_local_llm_config"]()
    assert "local LLM config:" in rendered
