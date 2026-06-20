"""Strict registry audit helpers for project type detection governance."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import yaml

from intelligent_project_analyzer.modules.project_type.contracts import (
    PROJECT_TYPE_REGISTRY_PATHS,
)


class ProjectTypeRegistryAuditError(RuntimeError):
    """Raised when project type registry governance inputs are missing or invalid."""


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_yaml_document_strict(path: Path) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as exc:  # pragma: no cover - exact parser exception is yaml-version specific.
        raise ProjectTypeRegistryAuditError(
            f"project type registry YAML parse failed: {path}"
        ) from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ProjectTypeRegistryAuditError(
            f"project type registry YAML must be a mapping: {path}"
        )
    return data


def audit_project_type_registries(
    *,
    root: Optional[Path] = None,
    registry_paths: Iterable[str] = PROJECT_TYPE_REGISTRY_PATHS,
) -> Dict[str, Any]:
    """Strictly verify current project type registry authorities for CI/governance."""

    base = Path(root or _repo_root())
    checked_paths = []
    errors = []

    for relative_path in registry_paths:
        path = base / relative_path
        checked_paths.append(str(relative_path))
        if not path.exists():
            errors.append(f"missing registry authority: {relative_path}")
            continue
        if path.suffix.lower() in {".yaml", ".yml"}:
            try:
                _load_yaml_document_strict(path)
            except ProjectTypeRegistryAuditError as exc:
                errors.append(str(exc))
        elif relative_path.endswith("project_type_detector.py"):
            text = path.read_text(encoding="utf-8")
            if "PROJECT_TYPE_REGISTRY" not in text:
                errors.append("PROJECT_TYPE_REGISTRY missing from project_type_detector.py")

    if errors:
        raise ProjectTypeRegistryAuditError("; ".join(errors))

    return {
        "status": "ok",
        "checked_paths": checked_paths,
    }
