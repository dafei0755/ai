from intelligent_project_analyzer.services.llm_factory import LLMFactory
from intelligent_project_analyzer.services.multi_llm_factory import FallbackLLM, MultiLLMFactory


class _FakeChatOpenAI:
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        type(self).instances.append(self)

    def invoke(self, *_args, **_kwargs):
        return type("FakeResponse", (), {"content": "OK"})()


def test_llm_factory_uses_qwen_deepseek_openrouter_priority(monkeypatch):
    _FakeChatOpenAI.instances = []
    monkeypatch.setenv("SEMANTIC_CACHE_ENABLED", "false")
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

    original_configs = MultiLLMFactory.PROVIDER_CONFIGS
    monkeypatch.setattr(
        MultiLLMFactory,
        "PROVIDER_CONFIGS",
        {
            name: {**config, "class": _FakeChatOpenAI}
            for name, config in original_configs.items()
        },
    )

    llm = LLMFactory.create_llm(temperature=0, max_tokens=32, timeout=3, max_retries=0)

    assert isinstance(llm, FallbackLLM)
    assert llm.providers == ["qwen", "deepseek", "openrouter"]
    assert list(llm.llm_instances) == ["qwen", "deepseek", "openrouter"]

