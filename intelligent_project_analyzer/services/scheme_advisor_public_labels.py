"""User-facing label translation for Scheme Advisor internal keys."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

import yaml


_CONFIG_PATH = (
    Path(__file__).resolve().parent.parent
    / "config"
    / "registries"
    / "scheme_advisor_public_labels.yaml"
)


@lru_cache(maxsize=1)
def load_public_label_registry() -> Dict[str, Any]:
    if not _CONFIG_PATH.exists():
        return {
            "exact_labels": {},
            "token_labels": {},
            "fallback_label": "待确认项",
        }
    data = yaml.safe_load(_CONFIG_PATH.read_text(encoding="utf-8")) or {}
    return {
        "exact_labels": {
            str(key): str(value)
            for key, value in (data.get("exact_labels") or {}).items()
        },
        "token_labels": {
            str(key): str(value)
            for key, value in (data.get("token_labels") or {}).items()
        },
        "fallback_label": str(data.get("fallback_label") or "待确认项"),
    }


def public_label(value: str) -> str:
    """Translate internal ids or machine-ish phrases into user-facing Chinese.

    Unknown internal keys must not leak to the front end. If a key cannot be
    translated from exact or token labels, return the registry fallback.
    """

    raw = str(value or "").strip()
    registry = load_public_label_registry()
    fallback = str(registry.get("fallback_label") or "待确认项")
    if not raw:
        return fallback

    exact_labels = registry.get("exact_labels") or {}
    if raw in exact_labels:
        return str(exact_labels[raw])

    if "/" in raw:
        parts = [part.strip() for part in raw.split("/") if part.strip()]
        translated_parts = [public_label(part) for part in parts]
        if translated_parts and all(part != fallback for part in translated_parts):
            return " / ".join(translated_parts)

    if "_vs_" in raw:
        left, right = raw.split("_vs_", 1)
        return f"{public_label(left)} / {public_label(right)}"

    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", raw).lower()
    tokens = [
        token
        for token in re.split(r"[^a-z0-9]+", normalized)
        if token and token not in {"the", "of", "to", "for"}
    ]
    token_labels = registry.get("token_labels") or {}
    translated = [str(token_labels[token]) for token in tokens if token in token_labels]
    if translated:
        return "".join(translated)

    if any("\u4e00" <= ch <= "\u9fff" for ch in raw):
        return raw
    return fallback
