from intelligent_project_analyzer.services.multi_llm_factory import MultiLLMFactory
from intelligent_project_analyzer.settings import Settings


class _FakeChatOpenAI:
    last_params = None

    def __init__(self, **kwargs):
        type(self).last_params = kwargs


def test_qwen_uses_dashscope_key_fallback_and_enable_thinking(monkeypatch):
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-test-dashscope")
    monkeypatch.setenv("QWEN_MODEL", "qwen3.7-max")
    monkeypatch.setenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    monkeypatch.setenv("QWEN_ENABLE_THINKING", "true")

    config = dict(MultiLLMFactory.PROVIDER_CONFIGS["qwen"])
    monkeypatch.setitem(
        MultiLLMFactory.PROVIDER_CONFIGS,
        "qwen",
        {**config, "class": _FakeChatOpenAI},
    )

    llm = MultiLLMFactory.create_llm(
        provider="qwen",
        temperature=0,
        max_tokens=2048,
        timeout=30,
        max_retries=1,
    )

    assert isinstance(llm, _FakeChatOpenAI)
    assert _FakeChatOpenAI.last_params["api_key"] == "sk-test-dashscope"
    assert _FakeChatOpenAI.last_params["model"] == "qwen3.7-max"
    assert _FakeChatOpenAI.last_params["base_url"] == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert _FakeChatOpenAI.last_params["extra_body"] == {"enable_thinking": True}


def test_qwen_omits_extra_body_when_thinking_disabled(monkeypatch):
    monkeypatch.setenv("QWEN_API_KEY", "sk-test-qwen")
    monkeypatch.setenv("QWEN_MODEL", "qwen3.7-max")
    monkeypatch.setenv("QWEN_ENABLE_THINKING", "false")

    config = dict(MultiLLMFactory.PROVIDER_CONFIGS["qwen"])
    monkeypatch.setitem(
        MultiLLMFactory.PROVIDER_CONFIGS,
        "qwen",
        {**config, "class": _FakeChatOpenAI},
    )

    MultiLLMFactory.create_llm(
        provider="qwen",
        temperature=0,
        max_tokens=2048,
        timeout=30,
        max_retries=1,
    )

    assert "extra_body" not in _FakeChatOpenAI.last_params


def test_settings_syncs_qwen_provider_and_dashscope_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "qwen")
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-test-dashscope")
    monkeypatch.setenv("QWEN_MODEL", "qwen3.7-max")
    monkeypatch.setenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

    settings = Settings()

    assert settings.llm.provider == "qwen"
    assert settings.llm.api_key == "sk-test-dashscope"
    assert settings.llm.model == "qwen3.7-max"
    assert settings.llm.api_base == "https://dashscope.aliyuncs.com/compatible-mode/v1"
