"""Smoke test the configured LLM provider channels.

The script reads keys from .env, never prints secrets, and verifies that each
configured OpenAI-compatible provider can return a minimal response.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI


@dataclass(frozen=True)
class ProviderProbe:
    name: str
    api_key: str | None
    base_url: str | None
    model: str | None
    client_kwargs: dict[str, Any] = field(default_factory=dict)
    request_kwargs: dict[str, Any] = field(default_factory=dict)


def _first_env(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


def _provider_probes() -> list[ProviderProbe]:
    return [
        ProviderProbe(
            name="qwen",
            api_key=_first_env("QWEN_API_KEY", "DASHSCOPE_API_KEY"),
            base_url=os.getenv("QWEN_BASE_URL"),
            model=os.getenv("QWEN_MODEL"),
            request_kwargs={
                "extra_body": {
                    "enable_thinking": os.getenv("QWEN_ENABLE_THINKING", "false").lower() == "true"
                }
            },
        ),
        ProviderProbe(
            name="deepseek",
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url=os.getenv("DEEPSEEK_BASE_URL"),
            model=os.getenv("DEEPSEEK_MODEL"),
            request_kwargs={
                "reasoning_effort": os.getenv("DEEPSEEK_REASONING_EFFORT", "high"),
                "extra_body": {"thinking": {"type": "enabled"}},
            },
        ),
        ProviderProbe(
            name="openrouter",
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url=os.getenv("OPENROUTER_BASE_URL"),
            model=os.getenv("OPENROUTER_MODEL"),
            client_kwargs={
                "default_headers": {
                    "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "https://github.com/your-repo"),
                    "X-Title": os.getenv("OPENROUTER_APP_NAME", "Intelligent Project Analyzer"),
                }
            },
        ),
    ]


def _content_preview(text: str) -> str:
    return text[:80].encode("ascii", "backslashreplace").decode("ascii")


def main() -> int:
    load_dotenv(dotenv_path=".env", override=True)
    failed: list[str] = []

    for probe in _provider_probes():
        print(f"[{probe.name}] start model={probe.model}")
        if not probe.api_key or not probe.base_url or not probe.model:
            print(f"[{probe.name}] fail error_type=ConfigError error=missing api_key/base_url/model")
            failed.append(probe.name)
            continue

        try:
            client = OpenAI(
                api_key=probe.api_key,
                base_url=probe.base_url,
                timeout=90,
                max_retries=0,
                **probe.client_kwargs,
            )
            response = client.chat.completions.create(
                model=probe.model,
                messages=[{"role": "user", "content": "Reply exactly with OK."}],
                max_tokens=256,
                temperature=0,
                **probe.request_kwargs,
            )
            choice = response.choices[0]
            content = choice.message.content or ""
            reasoning = getattr(choice.message, "reasoning_content", "") or ""
            print(
                f"[{probe.name}] ok response_model={response.model} "
                f"finish_reason={choice.finish_reason} content_len={len(content)} "
                f"reasoning_len={len(reasoning)} content={_content_preview(content)}"
            )
        except Exception as exc:  # pragma: no cover - smoke diagnostics
            print(f"[{probe.name}] fail error_type={type(exc).__name__} error={str(exc)[:300]}")
            failed.append(probe.name)

    if failed:
        print("FAILED_PROVIDER_DIRECT_TESTS=" + ",".join(failed))
        return 1
    print("ALL_PROVIDER_DIRECT_TESTS_PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
