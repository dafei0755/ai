import os

from intelligent_project_analyzer.services.demand_reconstruction_llm import (
    DirectDemandReconstructionLLM,
    create_demand_reconstruction_llm,
    describe_demand_reconstruction_llm_config,
)
from intelligent_project_analyzer.services.multi_llm_factory import FallbackLLM

_DEMAND_RECONSTRUCTION_PROVIDER_OVERRIDES = (
    "DEMAND_RECONSTRUCTION_LLM_PROVIDER",
    "DEMAND_RECONSTRUCTION_LLM_FALLBACK_PROVIDERS",
    "DEMAND_RECONSTRUCTION_LLM_API_KEY",
    "DEMAND_RECONSTRUCTION_LLM_MODEL",
    "DEMAND_RECONSTRUCTION_LLM_BASE_URL",
    "DEMAND_RECONSTRUCTION_LLM_REASONING_EFFORT",
)


def _clear_demand_reconstruction_provider_overrides(monkeypatch):
    for name in _DEMAND_RECONSTRUCTION_PROVIDER_OVERRIDES:
        monkeypatch.delenv(name, raising=False)


class _FakeOpenAI:
    instances = []

    def __init__(self, **kwargs):
        self.init_kwargs = kwargs
        self.last_create_kwargs = None
        self.chat = _FakeChat(self)
        type(self).instances.append(self)


class _FakeChat:
    def __init__(self, owner):
        self.completions = _FakeCompletions(owner)


class _FakeCompletions:
    def __init__(self, owner):
        self._owner = owner

    def create(self, **kwargs):
        self._owner.last_create_kwargs = kwargs
        return type(
            "FakeCompletion",
            (),
            {
                "choices": [
                    type(
                        "FakeChoice",
                        (),
                        {
                            "message": type(
                                "FakeMessage",
                                (),
                                {"content": '{"task_reframe": "LLM insight"}'},
                            )()
                        },
                    )()
                ]
            },
        )()


def test_direct_demand_reconstruction_llm_calls_bailian_compatible_chat_api():
    _FakeOpenAI.instances = []

    llm = DirectDemandReconstructionLLM(
        api_key="sk-test",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        model="qwen3.7-max",
        timeout=33,
        max_retries=0,
        max_tokens=1800,
        temperature=0.25,
        enable_thinking=False,
        client_factory=_FakeOpenAI,
    )

    response = llm.invoke("prompt text")

    assert response.content == '{"task_reframe": "LLM insight"}'
    instance = _FakeOpenAI.instances[0]
    assert instance.init_kwargs == {
        "api_key": "sk-test",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "timeout": 33,
        "max_retries": 0,
    }
    assert instance.last_create_kwargs == {
        "model": "qwen3.7-max",
        "messages": [{"role": "user", "content": "prompt text"}],
        "temperature": 0.25,
        "max_tokens": 1800,
        "extra_body": {"enable_thinking": False},
    }


def test_factory_prefers_direct_qwen_adapter_for_demand_reconstruction(monkeypatch):
    _FakeOpenAI.instances = []
    _clear_demand_reconstruction_provider_overrides(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "qwen")
    monkeypatch.setenv("LLM_AUTO_FALLBACK", "false")
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-test-dashscope")
    monkeypatch.setenv("QWEN_MODEL", "qwen3.7-max")
    monkeypatch.setenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    monkeypatch.setenv("DEMAND_RECONSTRUCTION_LLM_TIMEOUT", "45")
    monkeypatch.setenv("DEMAND_RECONSTRUCTION_LLM_MAX_RETRIES", "0")
    monkeypatch.setenv("DEMAND_RECONSTRUCTION_LLM_MAX_TOKENS", "1800")
    monkeypatch.setenv("DEMAND_RECONSTRUCTION_LLM_TEMPERATURE", "0.25")
    monkeypatch.setenv("DEMAND_RECONSTRUCTION_LLM_ENABLE_THINKING", "false")

    llm = create_demand_reconstruction_llm(client_factory=_FakeOpenAI)
    llm.invoke("hello")

    assert isinstance(llm, DirectDemandReconstructionLLM)
    instance = _FakeOpenAI.instances[0]
    assert instance.init_kwargs["api_key"] == "sk-test-dashscope"
    assert instance.init_kwargs["base_url"] == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert instance.last_create_kwargs["model"] == "qwen3.7-max"
    assert instance.last_create_kwargs["extra_body"] == {"enable_thinking": False}


def test_factory_prefers_direct_deepseek_adapter_with_official_thinking_payload(monkeypatch):
    _FakeOpenAI.instances = []
    _clear_demand_reconstruction_provider_overrides(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("LLM_AUTO_FALLBACK", "false")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-deepseek")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    monkeypatch.setenv("DEMAND_RECONSTRUCTION_LLM_TIMEOUT", "45")
    monkeypatch.setenv("DEMAND_RECONSTRUCTION_LLM_MAX_RETRIES", "0")
    monkeypatch.setenv("DEMAND_RECONSTRUCTION_LLM_MAX_TOKENS", "1800")
    monkeypatch.setenv("DEMAND_RECONSTRUCTION_LLM_TEMPERATURE", "0.25")
    monkeypatch.setenv("DEMAND_RECONSTRUCTION_LLM_ENABLE_THINKING", "true")
    monkeypatch.setenv("DEEPSEEK_REASONING_EFFORT", "high")

    llm = create_demand_reconstruction_llm(client_factory=_FakeOpenAI)
    llm.invoke("hello")

    assert isinstance(llm, DirectDemandReconstructionLLM)
    instance = _FakeOpenAI.instances[0]
    assert instance.init_kwargs["api_key"] == "sk-test-deepseek"
    assert instance.init_kwargs["base_url"] == "https://api.deepseek.com"
    assert instance.last_create_kwargs["model"] == "deepseek-v4-pro"
    assert instance.last_create_kwargs["extra_body"] == {"thinking": {"type": "enabled"}}
    assert instance.last_create_kwargs["reasoning_effort"] == "high"


def test_factory_builds_direct_qwen_deepseek_openrouter_fallback_chain(monkeypatch):
    _FakeOpenAI.instances = []
    _clear_demand_reconstruction_provider_overrides(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "qwen")
    monkeypatch.setenv("LLM_AUTO_FALLBACK", "true")
    monkeypatch.setenv("LLM_FALLBACK_PROVIDERS", "qwen,deepseek,openrouter")
    monkeypatch.setenv("QWEN_API_KEY", "sk-test-qwen")
    monkeypatch.setenv("QWEN_MODEL", "qwen3.7-max")
    monkeypatch.setenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-deepseek")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-openrouter")
    monkeypatch.setenv("OPENROUTER_MODEL", "openai/gpt-4o")
    monkeypatch.setenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

    llm = create_demand_reconstruction_llm(client_factory=_FakeOpenAI)

    assert isinstance(llm, FallbackLLM)
    assert llm.providers == ["qwen", "deepseek", "openrouter"]
    assert list(llm.llm_instances) == ["qwen", "deepseek", "openrouter"]
    assert [instance.init_kwargs["base_url"] for instance in _FakeOpenAI.instances] == [
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "https://api.deepseek.com",
        "https://openrouter.ai/api/v1",
    ]


def test_factory_disables_per_provider_retries_inside_direct_fallback_chain(monkeypatch):
    _FakeOpenAI.instances = []
    _clear_demand_reconstruction_provider_overrides(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "qwen")
    monkeypatch.setenv("LLM_AUTO_FALLBACK", "true")
    monkeypatch.setenv("LLM_FALLBACK_PROVIDERS", "qwen,deepseek,openrouter")
    monkeypatch.setenv("QWEN_API_KEY", "sk-test-qwen")
    monkeypatch.setenv("QWEN_MODEL", "qwen3.7-max")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-deepseek")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-openrouter")
    monkeypatch.setenv("OPENROUTER_MODEL", "qwen/qwen3.7-max")
    monkeypatch.setenv("DEMAND_RECONSTRUCTION_LLM_TIMEOUT", "45")
    monkeypatch.setenv("DEMAND_RECONSTRUCTION_LLM_MAX_RETRIES", "2")

    llm = create_demand_reconstruction_llm(client_factory=_FakeOpenAI)

    assert isinstance(llm, FallbackLLM)
    assert [instance.init_kwargs["max_retries"] for instance in _FakeOpenAI.instances] == [0, 0, 0]


def test_factory_uses_demand_reconstruction_specific_fallback_order(monkeypatch):
    _FakeOpenAI.instances = []
    _clear_demand_reconstruction_provider_overrides(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "qwen")
    monkeypatch.setenv("LLM_AUTO_FALLBACK", "true")
    monkeypatch.setenv("LLM_FALLBACK_PROVIDERS", "qwen,deepseek,openrouter")
    monkeypatch.setenv("DEMAND_RECONSTRUCTION_LLM_FALLBACK_PROVIDERS", "openrouter,qwen,deepseek")
    monkeypatch.setenv("QWEN_API_KEY", "sk-test-qwen")
    monkeypatch.setenv("QWEN_MODEL", "qwen3.7-max")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-deepseek")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-openrouter")
    monkeypatch.setenv("OPENROUTER_MODEL", "qwen/qwen3.7-max")

    llm = create_demand_reconstruction_llm(client_factory=_FakeOpenAI)

    assert isinstance(llm, FallbackLLM)
    assert llm.providers == ["openrouter", "qwen", "deepseek"]
    assert list(llm.llm_instances) == ["openrouter", "qwen", "deepseek"]


def test_factory_defaults_to_latency_sensitive_output_budget(monkeypatch):
    _FakeOpenAI.instances = []
    _clear_demand_reconstruction_provider_overrides(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "qwen")
    monkeypatch.setenv("LLM_AUTO_FALLBACK", "false")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-test-dashscope")
    monkeypatch.setenv("QWEN_MODEL", "qwen3.7-max")
    monkeypatch.delenv("DEMAND_RECONSTRUCTION_LLM_MAX_TOKENS", raising=False)

    llm = create_demand_reconstruction_llm(client_factory=_FakeOpenAI)
    llm.invoke("hello")

    assert _FakeOpenAI.instances[0].last_create_kwargs["max_tokens"] == 1200


def test_diagnostic_config_reports_missing_direct_provider_keys_without_secrets(monkeypatch):
    _clear_demand_reconstruction_provider_overrides(monkeypatch)
    monkeypatch.setenv("DEMAND_RECONSTRUCTION_USE_LLM", "1")
    monkeypatch.setenv("DEMAND_RECONSTRUCTION_LLM_DIRECT", "1")
    monkeypatch.setenv("LLM_AUTO_FALLBACK", "false")
    monkeypatch.setenv("LLM_PROVIDER", "qwen")
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)

    status = describe_demand_reconstruction_llm_config()

    assert status["ready"] is False
    assert status["provider_chain"] == ["qwen"]
    assert status["providers"][0]["api_key_configured"] is False
    assert status["providers"][0]["api_key_source"] is None
    assert "no API key configured" in status["blocked_reasons"][0]


def test_diagnostic_config_reports_direct_fallback_chain_readiness(monkeypatch):
    _clear_demand_reconstruction_provider_overrides(monkeypatch)
    monkeypatch.setenv("DEMAND_RECONSTRUCTION_USE_LLM", "1")
    monkeypatch.setenv("DEMAND_RECONSTRUCTION_LLM_DIRECT", "1")
    monkeypatch.setenv("LLM_AUTO_FALLBACK", "true")
    monkeypatch.setenv("DEMAND_RECONSTRUCTION_LLM_FALLBACK_PROVIDERS", "openrouter,qwen,deepseek")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-openrouter-secret")
    monkeypatch.setenv("OPENROUTER_MODEL", "qwen/qwen3.7-max")
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-deepseek-secret")

    status = describe_demand_reconstruction_llm_config()

    assert status["ready"] is True
    assert status["provider_chain"] == ["openrouter", "qwen", "deepseek"]
    providers = {item["provider"]: item for item in status["providers"]}
    assert providers["openrouter"]["api_key_configured"] is True
    assert providers["openrouter"]["api_key_source"] == "OPENROUTER_API_KEY"
    assert providers["qwen"]["api_key_configured"] is False
    assert providers["deepseek"]["api_key_configured"] is True
    assert "sk-openrouter-secret" not in str(status)
    assert "sk-deepseek-secret" not in str(status)


def test_factory_applies_qwen_proxy_when_backend_process_lacks_proxy_env(monkeypatch):
    _FakeOpenAI.instances = []
    _clear_demand_reconstruction_provider_overrides(monkeypatch)
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "NO_PROXY", "no_proxy"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "qwen")
    monkeypatch.setenv("LLM_AUTO_FALLBACK", "false")
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-test-dashscope")
    monkeypatch.setenv("QWEN_MODEL", "qwen3.7-max")
    monkeypatch.setenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    monkeypatch.setenv("QWEN_PROXY_URL", "http://127.0.0.1:7890")

    llm = create_demand_reconstruction_llm(client_factory=_FakeOpenAI)

    assert isinstance(llm, DirectDemandReconstructionLLM)
    assert os.environ["HTTP_PROXY"] == "http://127.0.0.1:7890"
    assert os.environ["HTTPS_PROXY"] == "http://127.0.0.1:7890"
    assert os.environ["http_proxy"] == "http://127.0.0.1:7890"
    assert os.environ["https_proxy"] == "http://127.0.0.1:7890"
    assert "127.0.0.1" in os.environ["NO_PROXY"]
    assert "localhost" in os.environ["NO_PROXY"]


def test_factory_can_fall_back_to_existing_llm_factory_when_direct_disabled(monkeypatch):
    calls = []
    fake_llm = object()

    def fallback_factory(**kwargs):
        calls.append(kwargs)
        return fake_llm

    monkeypatch.setenv("DEMAND_RECONSTRUCTION_LLM_DIRECT", "0")
    monkeypatch.setenv("DEMAND_RECONSTRUCTION_LLM_TIMEOUT", "45")
    monkeypatch.setenv("DEMAND_RECONSTRUCTION_LLM_MAX_RETRIES", "1")
    monkeypatch.setenv("DEMAND_RECONSTRUCTION_LLM_MAX_TOKENS", "1800")

    llm = create_demand_reconstruction_llm(fallback_factory=fallback_factory)

    assert llm is fake_llm
    assert calls == [{"timeout": 45, "max_retries": 1, "max_tokens": 1800}]
