"""Smoke test real demand-reconstruction LLM intervention through the backend API."""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

PASS_STATES = {("llm", "used"), ("llm_partial", "partial")}
MIN_TEXT_LENGTH = 20
LEGACY_PENDING_SOURCES = {"rule_pending_llm", "semantic_pending_llm"}
TERMINAL_FAILURE_STATUSES = {
    "invoke_failed",
    "quality_rejected",
    "invalid_json",
    "empty_response",
}


@dataclass(frozen=True)
class Case:
    name: str
    prompt: str


CASES = [
    Case(
        name="cultural-villa",
        prompt=(
            "成都麓山国际1500m2别墅，要求从古典文人园林连廊的精神出发，"
            "重新审视当代豪宅的空间逻辑。请给出深度解析与反思，"
            "并形成可落地的室内设计概念。"
        ),
    ),
    Case(
        name="urban-apartment",
        prompt=(
            "深圳南山200m2大平层，业主为38岁英国海归独立女性，"
            "不婚主义，对Audrey Hepburn赫本精神高度认同。"
            "请提出完整室内设计概念，从优雅、自律、轻盈与现代女性独立精神出发。"
        ),
    ),
    Case(
        name="return-home-house",
        prompt=(
            "50岁男性室内设计师，背井离乡多年，想在老家建一栋民居，"
            "既要回应乡土和家族关系，又不能做成展示作品。请给出建议。"
        ),
    ),
]


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument(
        "--poll-seconds",
        type=float,
        default=3.0,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=120.0,
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--user-id", default="dev_user")
    parser.add_argument(
        "--no-local-llm-diagnosis",
        action="store_true",
        help="Do not print the local redacted demand-reconstruction LLM config snapshot.",
    )
    parser.add_argument(
        "--case",
        choices=[case.name for case in CASES],
        help="Run a single smoke case instead of the full set.",
    )
    args = parser.parse_args()

    if not args.no_local_llm_diagnosis:
        _load_local_env_for_diagnostics()
        print(_format_local_llm_config())

    cases = [case for case in CASES if args.case in (None, case.name)]
    failures: list[str] = []
    http = requests.Session()
    http.trust_env = False
    for index, case in enumerate(cases, start=1):
        print(f"\n[{index}/{len(cases)}] {case.name}")
        try:
            result = run_case(
                http=http,
                base_url=args.base_url.rstrip("/"),
                user_id=args.user_id,
                case=case,
                poll_seconds=args.poll_seconds,
                timeout_seconds=args.timeout_seconds,
            )
        except Exception as exc:  # noqa: BLE001 - smoke output should include the failing layer.
            failures.append(f"{case.name}: {type(exc).__name__}: {exc}")
            print(f"FAIL {case.name}: {type(exc).__name__}: {exc}")
            continue
        print(
            "PASS "
            f"{case.name}: session={result['session_id']}, "
            f"elapsed={result['elapsed_seconds']:.1f}s, "
            f"source={result['source']}, status={result['status']}"
        )
        print(f"  reframe: {result['task_reframe'][:120]}")

    if failures:
        print("\nFAILED CASES:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(
        f"\nALL PASSED: {len(cases)}/{len(cases)} "
        "demand-reconstruction cases reached final fused first response."
    )
    return 0


def run_case(
    *,
    http: requests.Session,
    base_url: str,
    user_id: str,
    case: Case,
    poll_seconds: float,
    timeout_seconds: float,
) -> dict[str, Any]:
    started_at = time.monotonic()
    response = http.post(
        f"{base_url}/api/v2/conversation/message",
        json={"session_id": "", "message": case.prompt, "user_id": user_id},
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    initial = response.json()
    session_id = initial.get("session_id")
    if not session_id:
        raise RuntimeError(f"missing session_id in response: {initial}")

    initial_blueprint = _extract_blueprint_from_response(initial)
    initial_source = initial_blueprint.get("insight_source")
    initial_status = initial_blueprint.get("llm_status")
    print(f"  session={session_id}")
    print(f"  initial source={initial_source}, status={initial_status}")
    if initial.get("intent") != "demand_reconstruction_blueprint":
        raise RuntimeError(
            "did not enter demand reconstruction: "
            f"intent={initial.get('intent')}, dialogue_layer={initial.get('dialogue_layer')}, "
            f"reply={str(initial.get('reply') or '')[:120]}"
        )

    if (initial_source, initial_status) in PASS_STATES:
        _validate_effective_blueprint(initial_blueprint)
        return {
            "session_id": session_id,
            "elapsed_seconds": time.monotonic() - started_at,
            "source": initial_source,
            "status": initial_status,
            "task_reframe": initial_blueprint.get("task_reframe") or "",
        }
    if initial_source in LEGACY_PENDING_SOURCES or initial_status == "scheduled":
        raise RuntimeError(
            "backend is still using the legacy async demand reconstruction path: "
            f"source={initial_source}, status={initial_status}, session={session_id}. "
            "Restart the backend with the current worktree; demand reconstruction should be fused in the first response."
        )
    if initial_status in TERMINAL_FAILURE_STATUSES or initial_source == "semantic_fallback":
        raise RuntimeError(
            "LLM was not used in the first response: "
            f"source={initial_source}, status={initial_status}, "
            f"error_type={initial_blueprint.get('llm_error_type')}, "
            f"error={initial_blueprint.get('llm_error')}. "
            f"{_local_llm_config_hint()}"
        )

    raise RuntimeError(
        "first response was not a final fused demand reconstruction result: "
        f"source={initial_source}, status={initial_status}, session={session_id}. "
        "The current architecture requires the first response to be either LLM-used, "
        "LLM-partial, or an explicit semantic fallback; do not wait for async replacement."
    )


def _extract_blueprint_from_response(response: dict[str, Any]) -> dict[str, Any]:
    context = response.get("demand_reconstruction_context")
    if isinstance(context, dict) and isinstance(context.get("blueprint"), dict):
        return context["blueprint"]
    card = response.get("guidance_card")
    if isinstance(card, dict) and isinstance(card.get("summary"), dict):
        return card["summary"]
    return {}


def _load_local_env_for_diagnostics() -> None:
    """Mirror backend startup env loading for local smoke diagnostics only."""
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(env_path, override=False)
    except Exception:
        return


def _local_llm_config_hint() -> str:
    try:
        return _format_local_llm_config()
    except Exception as exc:  # noqa: BLE001 - diagnostics must not mask the smoke failure.
        return f"local LLM config diagnosis unavailable: {type(exc).__name__}: {exc}"


def _format_local_llm_config() -> str:
    from intelligent_project_analyzer.services.demand_reconstruction_llm import (
        describe_demand_reconstruction_llm_config,
    )

    status = describe_demand_reconstruction_llm_config()
    providers = status.get("providers") or []
    provider_bits = []
    for item in providers:
        provider_bits.append(
            "{provider}(key={key}, model={model}, proxy={proxy})".format(
                provider=item.get("provider"),
                key="yes" if item.get("api_key_configured") else "no",
                model=item.get("model") or "unknown",
                proxy=item.get("proxy") or "unknown",
            )
        )
    blocked = ", ".join(status.get("blocked_reasons") or []) or "none"
    return (
        "local LLM config: "
        f"ready={status.get('ready')}, "
        f"use_llm={status.get('use_llm_enabled')}, "
        f"direct={status.get('direct_enabled')}, "
        f"auto_fallback={status.get('auto_fallback_enabled')}, "
        f"max_tokens={status.get('max_tokens')}, "
        f"providers=[{'; '.join(provider_bits)}], "
        f"blocked=[{blocked}]"
    )


def _extract_blueprint_from_session(session: dict[str, Any]) -> dict[str, Any]:
    context = session.get("demand_reconstruction_context")
    if isinstance(context, dict) and isinstance(context.get("blueprint"), dict):
        return context["blueprint"]

    card = session.get("pending_guidance_card")
    if isinstance(card, dict) and isinstance(card.get("summary"), dict):
        return card["summary"]

    for item in reversed(session.get("conversation_history_v2") or []):
        if not isinstance(item, dict):
            continue
        card = item.get("guidance_card")
        if isinstance(card, dict) and isinstance(card.get("summary"), dict):
            return card["summary"]
    return {}


def _validate_effective_blueprint(blueprint: dict[str, Any]) -> None:
    missing: list[str] = []
    for field in ("task_reframe", "primary_risk", "routing_recommendation", "next_question"):
        value = blueprint.get(field)
        if not isinstance(value, str) or len(value.strip()) < MIN_TEXT_LENGTH:
            missing.append(field)
    for field in ("key_forks", "unknowns"):
        value = blueprint.get(field)
        if not isinstance(value, list) or len([item for item in value if str(item).strip()]) < 2:
            missing.append(field)
    sections = blueprint.get("sections")
    if not isinstance(sections, list) or len(sections) < 2:
        missing.append("sections")
    if missing:
        raise RuntimeError(f"LLM blueprint is not effective enough; weak fields: {', '.join(missing)}")


if __name__ == "__main__":
    raise SystemExit(main())
