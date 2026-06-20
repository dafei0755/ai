"""Dedicated LLM adapter for demand reconstruction.

The demand-reconstruction first step is latency-sensitive and must be
observable.  It uses a direct OpenAI-compatible client so provider-specific
parameters are explicit and are not hidden behind the general chat wrapper.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional

from loguru import logger

_FALSE_ENV_VALUES = {"0", "false", "no", "off"}
_LOCAL_NO_PROXY_HOSTS = ("127.0.0.1", "localhost", "::1")


@dataclass(frozen=True)
class DemandReconstructionLLMResponse:
    content: str


class DirectDemandReconstructionLLM:
    """OpenAI-compatible direct adapter used by the demand-reconstruction layer."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout: int,
        max_retries: int,
        max_tokens: int,
        temperature: float,
        enable_thinking: bool,
        provider: str = "openai-compatible",
        reasoning_effort: Optional[str] = None,
        client_kwargs: Optional[dict[str, Any]] = None,
        client_factory: Optional[Callable[..., Any]] = None,
    ) -> None:
        if client_factory is None:
            from openai import OpenAI  # noqa: PLC0415

            client_factory = OpenAI

        self._model = model
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._enable_thinking = enable_thinking
        self._provider = provider
        self._reasoning_effort = reasoning_effort
        self._client = client_factory(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            **dict(client_kwargs or {}),
        )

    def invoke(self, prompt: str) -> DemandReconstructionLLMResponse:
        start = time.perf_counter()
        prompt_chars = len(str(prompt or ""))
        try:
            request_kwargs = {
                "model": self._model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self._temperature,
                "max_tokens": self._max_tokens,
            }
            if self._provider == "deepseek":
                if self._enable_thinking:
                    request_kwargs["extra_body"] = {"thinking": {"type": "enabled"}}
                if self._reasoning_effort:
                    request_kwargs["reasoning_effort"] = self._reasoning_effort
            else:
                request_kwargs["extra_body"] = {"enable_thinking": self._enable_thinking}

            completion = self._client.chat.completions.create(**request_kwargs)
            message = completion.choices[0].message
            content = str(getattr(message, "content", "") or "")
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            logger.info(
                "[DemandReconstructionLLM] direct call succeeded: "
                f"model={self._model}, prompt_chars={prompt_chars}, "
                f"content_chars={len(content)}, elapsed_ms={elapsed_ms}, "
                f"enable_thinking={self._enable_thinking}"
            )
            return DemandReconstructionLLMResponse(content=content)
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            cause = getattr(exc, "__cause__", None)
            context = getattr(exc, "__context__", None)
            logger.warning(
                "[DemandReconstructionLLM] direct call failed: "
                f"model={self._model}, prompt_chars={prompt_chars}, "
                f"elapsed_ms={elapsed_ms}, error_type={type(exc).__name__}, error={exc}, "
                f"cause_type={type(cause).__name__ if cause else None}, cause={cause}, "
                f"context_type={type(context).__name__ if context else None}, context={context}"
            )
            raise


def create_demand_reconstruction_llm(
    *,
    client_factory: Optional[Callable[..., Any]] = None,
    fallback_factory: Optional[Callable[..., Any]] = None,
) -> Any:
    timeout = _env_int("DEMAND_RECONSTRUCTION_LLM_TIMEOUT", 45)
    max_retries = _env_int("DEMAND_RECONSTRUCTION_LLM_MAX_RETRIES", 0)
    max_tokens = _env_int("DEMAND_RECONSTRUCTION_LLM_MAX_TOKENS", 1200)

    if _env_flag("DEMAND_RECONSTRUCTION_LLM_DIRECT", "1"):
        provider = (
            os.getenv("DEMAND_RECONSTRUCTION_LLM_PROVIDER")
            or os.getenv("LLM_PROVIDER")
            or ""
        ).strip().lower()
        auto_fallback = _env_flag("LLM_AUTO_FALLBACK", "0")
        if auto_fallback:
            from intelligent_project_analyzer.services.multi_llm_factory import (  # noqa: PLC0415
                FallbackLLM,
                build_fallback_provider_chain,
            )

            provider_chain = _build_demand_reconstruction_provider_chain(
                primary_provider=provider,
                default_factory=build_fallback_provider_chain,
            )
            provider_max_retries = _env_int("DEMAND_RECONSTRUCTION_LLM_FALLBACK_PROVIDER_MAX_RETRIES", 0)
            llm_instances = {}
            for item in provider_chain:
                adapter = _create_direct_adapter_for_provider(
                    item,
                    timeout=timeout,
                    max_retries=provider_max_retries,
                    max_tokens=max_tokens,
                    client_factory=client_factory,
                )
                if adapter is not None:
                    llm_instances[item] = adapter
            if llm_instances:
                logger.info(
                    "[DemandReconstructionLLM] using direct fallback chain: "
                    f"providers={list(llm_instances.keys())}, timeout={timeout}s, "
                    f"provider_max_retries={provider_max_retries}, max_tokens={max_tokens}"
                )
                return FallbackLLM(providers=provider_chain, llm_instances=llm_instances)

        adapter = _create_direct_adapter_for_provider(
            provider,
            timeout=timeout,
            max_retries=max_retries,
            max_tokens=max_tokens,
            client_factory=client_factory,
        )
        if adapter is not None:
            return adapter
        logger.warning("[DemandReconstructionLLM] direct adapter skipped: API key is not configured")

    if fallback_factory is None:
        return None
    logger.info(
        "[DemandReconstructionLLM] using fallback LLM factory: "
        f"timeout={timeout}s, max_retries={max_retries}, max_tokens={max_tokens}"
    )
    return fallback_factory(timeout=timeout, max_retries=max_retries, max_tokens=max_tokens)


def describe_demand_reconstruction_llm_config() -> dict[str, Any]:
    """Return a redacted, side-effect-free readiness snapshot for diagnostics."""
    requested_provider = (
        os.getenv("DEMAND_RECONSTRUCTION_LLM_PROVIDER")
        or os.getenv("LLM_PROVIDER")
        or ""
    ).strip().lower()
    normalized_provider = _normalize_provider(requested_provider)
    direct_enabled = _env_flag("DEMAND_RECONSTRUCTION_LLM_DIRECT", "1")
    auto_fallback = _env_flag("LLM_AUTO_FALLBACK", "0")
    provider_chain: list[str] = []
    if direct_enabled:
        if auto_fallback:
            provider_chain = _build_demand_reconstruction_provider_chain(
                primary_provider=normalized_provider or requested_provider,
                default_factory=_default_provider_chain_for_diagnostics,
            )
        elif normalized_provider:
            provider_chain = [normalized_provider]

    provider_statuses = [_provider_config_status(provider) for provider in provider_chain]
    any_direct_key = any(item["api_key_configured"] for item in provider_statuses)
    use_llm_enabled = _env_flag("DEMAND_RECONSTRUCTION_USE_LLM", "1")
    ready = bool(use_llm_enabled and (not direct_enabled or any_direct_key))
    blocked_reasons: list[str] = []
    if not use_llm_enabled:
        blocked_reasons.append("DEMAND_RECONSTRUCTION_USE_LLM disabled")
    if direct_enabled and not provider_chain:
        blocked_reasons.append("no supported direct provider")
    if direct_enabled and provider_chain and not any_direct_key:
        blocked_reasons.append("no API key configured for direct providers")

    return {
        "use_llm_enabled": use_llm_enabled,
        "direct_enabled": direct_enabled,
        "auto_fallback_enabled": auto_fallback,
        "requested_provider": requested_provider or None,
        "primary_provider": normalized_provider,
        "provider_chain": provider_chain,
        "providers": provider_statuses,
        "timeout_seconds": _env_int("DEMAND_RECONSTRUCTION_LLM_TIMEOUT", 45),
        "max_retries": _env_int("DEMAND_RECONSTRUCTION_LLM_MAX_RETRIES", 0),
        "max_tokens": _env_int("DEMAND_RECONSTRUCTION_LLM_MAX_TOKENS", 1200),
        "ready": ready,
        "blocked_reasons": blocked_reasons,
    }


def _create_direct_adapter_for_provider(
    provider: str,
    *,
    timeout: int,
    max_retries: int,
    max_tokens: int,
    client_factory: Optional[Callable[..., Any]],
) -> Optional[DirectDemandReconstructionLLM]:
    normalized = _normalize_provider(provider)
    if normalized is None:
        return None

    api_key = _api_key_for_provider(normalized)
    if not api_key:
        return None

    base_url = _base_url_for_provider(normalized)
    model = _model_for_provider(normalized)
    proxy_status = _apply_provider_proxy_environment(provider=normalized)
    logger.info(
        "[DemandReconstructionLLM] using direct compatible adapter: "
        f"provider={normalized}, model={model}, timeout={timeout}s, "
        f"max_retries={max_retries}, max_tokens={max_tokens}, "
        f"enable_thinking={_env_flag('DEMAND_RECONSTRUCTION_LLM_ENABLE_THINKING', '0')}, "
        f"proxy={proxy_status}"
    )
    return DirectDemandReconstructionLLM(
        api_key=api_key,
        base_url=base_url,
        model=model,
        timeout=timeout,
        max_retries=max_retries,
        max_tokens=max_tokens,
        temperature=_env_float("DEMAND_RECONSTRUCTION_LLM_TEMPERATURE", 0.25),
        enable_thinking=_env_flag("DEMAND_RECONSTRUCTION_LLM_ENABLE_THINKING", "0"),
        provider=normalized,
        reasoning_effort=(
            os.getenv("DEMAND_RECONSTRUCTION_LLM_REASONING_EFFORT")
            or os.getenv("DEEPSEEK_REASONING_EFFORT")
            if normalized == "deepseek"
            else None
        ),
        client_kwargs=_client_kwargs_for_provider(normalized),
        client_factory=client_factory,
    )


def _default_provider_chain_for_diagnostics(primary_provider: str | None) -> list[str]:
    configured = os.getenv("LLM_FALLBACK_PROVIDERS", "")
    if configured.strip():
        providers: list[str] = []
        for item in configured.split(","):
            normalized = _normalize_provider(item)
            if normalized and normalized not in providers:
                providers.append(normalized)
        if providers:
            return providers

    providers = []
    for item in (primary_provider, "qwen", "deepseek", "openrouter"):
        normalized = _normalize_provider(str(item or ""))
        if normalized and normalized not in providers:
            providers.append(normalized)
    return providers


def _provider_config_status(provider: str) -> dict[str, Any]:
    normalized = _normalize_provider(provider)
    if normalized is None:
        return {
            "provider": provider,
            "supported": False,
            "api_key_configured": False,
            "api_key_source": None,
            "model": None,
            "base_url": None,
            "proxy": "not_applicable",
        }
    api_key_source = _api_key_source_for_provider(normalized)
    return {
        "provider": normalized,
        "supported": True,
        "api_key_configured": bool(api_key_source),
        "api_key_source": api_key_source,
        "model": _model_for_provider(normalized),
        "base_url": _base_url_for_provider(normalized),
        "proxy": _proxy_config_status_for_provider(normalized),
    }


def _normalize_provider(provider: str) -> Optional[str]:
    normalized = (provider or "").strip().lower()
    if normalized in {"qwen", "dashscope", "bailian", "openai-compatible", "openai_compatible", ""}:
        return "qwen"
    if normalized in {"deepseek", "openrouter"}:
        return normalized
    return None


def _build_demand_reconstruction_provider_chain(
    *,
    primary_provider: str,
    default_factory: Callable[[str | None], list[str]],
) -> list[str]:
    configured = os.getenv("DEMAND_RECONSTRUCTION_LLM_FALLBACK_PROVIDERS", "")
    if not configured.strip():
        return default_factory(primary_provider)

    providers: list[str] = []
    for item in configured.split(","):
        normalized = _normalize_provider(item)
        if normalized and normalized not in providers:
            providers.append(normalized)
    return providers


def _api_key_source_for_provider(provider: str) -> Optional[str]:
    provider_specific_name = f"DEMAND_RECONSTRUCTION_LLM_{provider.upper()}_API_KEY"
    if os.getenv(provider_specific_name):
        return provider_specific_name
    if os.getenv("DEMAND_RECONSTRUCTION_LLM_API_KEY") and not _env_flag("LLM_AUTO_FALLBACK", "0"):
        return "DEMAND_RECONSTRUCTION_LLM_API_KEY"
    if provider == "deepseek":
        return _first_existing_env_name("DEEPSEEK_API_KEY")
    if provider == "openrouter":
        return _first_existing_env_name("OPENROUTER_API_KEY")
    return _first_existing_env_name("QWEN_API_KEY", "DASHSCOPE_API_KEY")


def _api_key_for_provider(provider: str) -> Optional[str]:
    provider_specific = os.getenv(f"DEMAND_RECONSTRUCTION_LLM_{provider.upper()}_API_KEY")
    if provider_specific:
        return provider_specific
    global_override = os.getenv("DEMAND_RECONSTRUCTION_LLM_API_KEY")
    if global_override and not _env_flag("LLM_AUTO_FALLBACK", "0"):
        return global_override
    if provider == "deepseek":
        return _first_env("DEEPSEEK_API_KEY")
    if provider == "openrouter":
        return _first_env("OPENROUTER_API_KEY")
    return _first_env("QWEN_API_KEY", "DASHSCOPE_API_KEY")


def _base_url_for_provider(provider: str) -> str:
    provider_specific = os.getenv(f"DEMAND_RECONSTRUCTION_LLM_{provider.upper()}_BASE_URL")
    if provider_specific:
        return provider_specific
    global_override = os.getenv("DEMAND_RECONSTRUCTION_LLM_BASE_URL")
    if global_override and not _env_flag("LLM_AUTO_FALLBACK", "0"):
        return global_override
    if provider == "deepseek":
        return (
            os.getenv("DEEPSEEK_BASE_URL")
            or "https://api.deepseek.com"
        )
    if provider == "openrouter":
        return (
            os.getenv("OPENROUTER_BASE_URL")
            or "https://openrouter.ai/api/v1"
        )
    return (
        os.getenv("QWEN_BASE_URL")
        or "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )


def _model_for_provider(provider: str) -> str:
    provider_specific = os.getenv(f"DEMAND_RECONSTRUCTION_LLM_{provider.upper()}_MODEL")
    if provider_specific:
        return provider_specific
    global_override = os.getenv("DEMAND_RECONSTRUCTION_LLM_MODEL")
    if global_override and not _env_flag("LLM_AUTO_FALLBACK", "0"):
        return global_override
    if provider == "deepseek":
        return os.getenv("DEEPSEEK_MODEL") or "deepseek-v4-pro"
    if provider == "openrouter":
        return os.getenv("OPENROUTER_MODEL") or "openai/gpt-4o"
    return os.getenv("QWEN_MODEL") or "qwen3.7-max"


def _client_kwargs_for_provider(provider: str) -> dict[str, Any]:
    if provider != "openrouter":
        return {}
    return {
        "default_headers": {
            "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "https://github.com/your-repo"),
            "X-Title": os.getenv("OPENROUTER_APP_NAME", "Intelligent Project Analyzer"),
        }
    }


def _first_env(*names: str) -> Optional[str]:
    for name in names:
        if not name:
            continue
        value = os.getenv(name)
        if value:
            return value
    return None


def _first_existing_env_name(*names: str) -> Optional[str]:
    for name in names:
        if name and os.getenv(name):
            return name
    return None


def _proxy_config_status_for_provider(provider: str = "") -> str:
    provider_proxy_names = [
        "DEMAND_RECONSTRUCTION_LLM_PROXY_URL",
        "DEEPSEEK_PROXY_URL" if provider == "deepseek" else "",
        "QWEN_PROXY_URL",
        "DASHSCOPE_PROXY_URL",
    ]
    provider_proxy = _first_existing_env_name(*provider_proxy_names)
    if provider_proxy:
        return f"configured:{provider_proxy}"
    existing_proxy = _first_existing_env_name("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy")
    if existing_proxy:
        return f"existing_env:{existing_proxy}"
    return "not_configured"


def _apply_provider_proxy_environment(*, provider: str = "") -> str:
    proxy_url = _first_env(
        "DEMAND_RECONSTRUCTION_LLM_PROXY_URL",
        "DEEPSEEK_PROXY_URL" if provider == "deepseek" else "",
        "QWEN_PROXY_URL",
        "DASHSCOPE_PROXY_URL",
    )
    if not proxy_url:
        return "not_configured" if not _has_proxy_env() else "existing_env"

    changed = False
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        if not os.getenv(name):
            os.environ[name] = proxy_url
            changed = True
    _merge_no_proxy_hosts()
    return "configured" if changed else "existing_env"


def _has_proxy_env() -> bool:
    return any(os.getenv(name) for name in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"))


def _merge_no_proxy_hosts() -> None:
    existing = os.getenv("NO_PROXY") or os.getenv("no_proxy") or ""
    entries = [entry.strip() for entry in existing.split(",") if entry.strip()]
    lowered = {entry.lower() for entry in entries}
    for host in _LOCAL_NO_PROXY_HOSTS:
        if host.lower() not in lowered:
            entries.append(host)
            lowered.add(host.lower())
    merged = ",".join(entries)
    os.environ["NO_PROXY"] = merged
    os.environ["no_proxy"] = merged


def _env_flag(name: str, default: str) -> bool:
    return os.getenv(name, default).strip().lower() not in _FALSE_ENV_VALUES


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default
