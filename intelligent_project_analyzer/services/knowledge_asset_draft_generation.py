"""Generate local asset drafts from explicitly selected knowledge sources."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .space_classification_service import SpaceClassificationService


SUPPORTED_TEXT_SUFFIXES = {".md", ".markdown", ".txt"}
_ACTIVATION_PACK_ROOT = Path(__file__).resolve().parent.parent / "knowledge_base" / "activation_packs"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_draft_id(source_key: str) -> str:
    digest = hashlib.sha256(source_key.encode("utf-8")).hexdigest()[:12].upper()
    return f"AD-{digest}"


def _read_text_document(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"source does not exist: {path}")
    if not path.is_file():
        raise ValueError(f"source is not a file: {path}")
    if path.suffix.lower() not in SUPPORTED_TEXT_SUFFIXES:
        raise ValueError(f"unsupported document type: {path.suffix}")
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError(f"source is empty: {path}")
    return text


def _title_from_text(text: str, fallback: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            title = stripped.lstrip("#").strip()
            if title:
                return title
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:80]
    return fallback


def _summary_from_text(text: str, title: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        return stripped[:160]
    return title


def _load_activation_pack(pack_id: Optional[str]) -> Dict[str, Any]:
    if not pack_id:
        return {}
    path = _ACTIVATION_PACK_ROOT / f"{pack_id}.yaml"
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _looks_like_tea_drink_asset(text: str) -> bool:
    markers = ("茶饮", "奶茶", "果茶", "喜茶", "HEYTEA", "出杯", "取餐", "外带")
    return any(marker in text for marker in markers)


def _build_binding_candidates(text: str) -> Dict[str, Dict[str, Any]]:
    classification_service = SpaceClassificationService()
    activation = classification_service.classify_and_activate(text)
    classification = activation.get("space_classification") or {}
    pack = activation.get("project_definition_activation_pack") or {}
    v18 = pack.get("_v18_extensions") or {}

    project_type = classification.get("project_type")
    subdomain_id = v18.get("subdomain_id")
    activation_pack_id = v18.get("activation_pack_id")
    confidence = float(classification.get("confidence") or 0.0)
    reasons = [str((classification.get("evidence") or {}).get("detector_reason") or "").strip()]

    if _looks_like_tea_drink_asset(text) and (not project_type or confidence < 0.55):
        project_type = "commercial_dining"
        subdomain_id = "tea_drink_store"
        activation_pack_id = "tea_drink_store_pack"
        confidence = max(confidence, 0.62)
        reasons.append("keyword_hint: tea_drink_store")

    activation_pack = _load_activation_pack(activation_pack_id)
    domain_framework = activation_pack.get("domain_framework") or pack.get("domain_framework") or {}
    recall_profile = (
        activation_pack.get("knowledge_recall_profile")
        or activation_pack.get("knowledge_base_binding")
        or pack.get("knowledge_base_binding")
        or {}
    )

    required_dims = domain_framework.get("required_dimensions") or []
    recommended_dims = domain_framework.get("recommended_dimensions") or []
    ontology_dimension_ids = list(dict.fromkeys([*required_dims, *recommended_dims]))
    if not ontology_dimension_ids:
        ontology_dimension_ids = v18.get("active_ontology_dimension_ids") or []

    package_ids = recall_profile.get("package_ids") or recall_profile.get("knowledge_packages") or []

    classification_candidate = {
        "project_type": project_type,
        "subdomain_id": subdomain_id,
        "activation_pack_id": activation_pack_id,
        "confidence": round(confidence, 3),
        "reasons": [reason for reason in reasons if reason],
        "promotion_policy": "review_before_registry_promotion",
    }
    ontology_binding_candidate = {
        "ontology_dimension_ids": ontology_dimension_ids,
        "confidence": "medium" if ontology_dimension_ids else "low",
        "reasons": [
            "derived_from_activation_pack_domain_framework"
            if activation_pack
            else "derived_from_project_type_profile_or_empty_fallback"
        ],
        "promotion_policy": "manual_review_before_ontology_change",
    }
    knowledge_binding_candidate = {
        "package_ids": package_ids,
        "allowed_use": [
            "concept_inspiration",
            "theme_generation",
            "motif_recall",
            "spatial_narrative_design",
        ],
        "not_allowed_use": [
            "business_performance_claim",
            "construction_standard",
            "compliance_basis",
            "confirmed_user_preference",
        ],
        "confidence": "medium" if package_ids else "low",
        "reasons": [
            "derived_from_activation_pack_knowledge_recall_profile"
            if activation_pack
            else "derived_from_generic_project_binding"
        ],
        "promotion_policy": "manual_review_before_runtime_recall",
    }
    return {
        "classification_candidate": classification_candidate,
        "ontology_binding_candidate": ontology_binding_candidate,
        "knowledge_binding_candidate": knowledge_binding_candidate,
    }


def _base_draft(
    *,
    source_key: str,
    source_ref: Dict[str, Any],
    title: str,
    summary: str,
    body_markdown: str,
    evidence_map: Dict[str, Any],
) -> Dict[str, Any]:
    missing_fields: List[str] = []
    risk_flags = ["rights_status_unknown"]
    binding_candidates = _build_binding_candidates(f"{title}\n{summary}\n{body_markdown}")
    return {
        "schema_version": "asset_draft.v1",
        "draft_id": _stable_draft_id(source_key),
        "source_ref": source_ref,
        "asset_card_candidate": {
            "title": title,
            "summary": summary,
            "body_markdown": body_markdown,
            "language": "zh-CN",
        },
        "metadata_candidate": {
            "asset_type": "EvidenceNote",
            "domain_tags": [],
            "review_status": "pending_review",
            "rights_status": "unknown",
            "risk_flags": risk_flags,
        },
        "evidence_map_candidate": evidence_map,
        **binding_candidates,
        "risk_flags": risk_flags,
        "missing_fields": missing_fields,
        "generation_notes": [
            "Generated from an explicitly selected local source.",
            "Manual review is required before creating an AssetPackage.",
        ],
        "review_status": "needs_manual_review",
        "created_at": _now_iso(),
    }


def generate_asset_draft_from_document(source_path: Path | str) -> Dict[str, Any]:
    """Generate an AssetDraft candidate from one explicit text document."""
    path = Path(source_path)
    text = _read_text_document(path)
    title = _title_from_text(text, path.stem)
    evidence_map = {
        "source_observations": [],
        "local_source_paths": [str(path)],
        "source_urls": [],
        "cleaning_reports": [],
        "evidence_strength": "weak",
        "limitations": ["Needs manual review for classification, rights status, and evidence strength."],
    }
    return _base_draft(
        source_key=str(path),
        source_ref={"source_type": "document", "source_path": str(path)},
        title=title,
        summary=_summary_from_text(text, title),
        body_markdown=text,
        evidence_map=evidence_map,
    )


def _find_observation_text(observation_dir: Path) -> tuple[Path, str]:
    preferred_names = ("observation.md", "index.md", "README.md", "cleaned.md")
    for name in preferred_names:
        candidate = observation_dir / name
        if candidate.exists() and candidate.is_file():
            return candidate, _read_text_document(candidate)
    for candidate in sorted(observation_dir.glob("*.md")):
        return candidate, _read_text_document(candidate)
    raise FileNotFoundError(f"no supported observation document found in: {observation_dir}")


def _find_cleaning_reports(observation_dir: Path) -> List[str]:
    return [
        str(path)
        for path in sorted(observation_dir.rglob("cleaning-report.md"))
        if path.is_file()
    ]


def generate_asset_draft_from_observation(
    observation_id: str,
    observation_root: Path | str,
) -> Dict[str, Any]:
    """Generate an AssetDraft candidate from one explicit observation directory."""
    observation_dir = Path(observation_root) / observation_id
    if not observation_dir.exists() or not observation_dir.is_dir():
        raise FileNotFoundError(f"observation directory does not exist: {observation_dir}")

    source_doc, text = _find_observation_text(observation_dir)
    title = _title_from_text(text, observation_id)
    reports = _find_cleaning_reports(observation_dir)
    evidence_map = {
        "source_observations": [observation_id],
        "local_source_paths": [str(observation_dir), str(source_doc)],
        "source_urls": [],
        "cleaning_reports": reports,
        "evidence_strength": "medium" if reports else "weak",
        "limitations": ["Needs manual review for classification and reusable asset boundaries."],
    }
    return _base_draft(
        source_key=str(observation_dir),
        source_ref={
            "source_type": "observation",
            "observation_id": observation_id,
            "source_path": str(observation_dir),
        },
        title=title,
        summary=_summary_from_text(text, title),
        body_markdown=text,
        evidence_map=evidence_map,
    )


def _is_observation_dir(path: Path) -> bool:
    return path.is_dir() and path.name.startswith("OBS-")


def generate_asset_drafts_from_directory(directory_path: Path | str) -> Dict[str, Any]:
    """Generate drafts from immediate items in one explicitly selected directory."""
    directory = Path(directory_path)
    if not directory.exists() or not directory.is_dir():
        raise FileNotFoundError(f"directory does not exist: {directory}")

    items: List[Dict[str, Any]] = []
    generated_count = 0
    skipped_count = 0
    failed_count = 0

    for source in sorted(directory.iterdir(), key=lambda item: item.name):
        item: Dict[str, Any] = {
            "source_path": str(source),
            "draft_id": None,
            "status": "",
            "reason": "",
            "warnings": [],
        }
        try:
            if _is_observation_dir(source):
                draft = generate_asset_draft_from_observation(source.name, directory)
            elif source.is_file() and source.suffix.lower() in SUPPORTED_TEXT_SUFFIXES:
                draft = generate_asset_draft_from_document(source)
            else:
                skipped_count += 1
                item["status"] = "skipped"
                item["reason"] = "unsupported_item"
                items.append(item)
                continue
        except (FileNotFoundError, UnicodeDecodeError, ValueError) as exc:
            failed_count += 1
            item["status"] = "failed"
            item["reason"] = str(exc)
            items.append(item)
            continue

        generated_count += 1
        item["draft_id"] = draft["draft_id"]
        item["status"] = "draft_generated"
        item["reason"] = "ok"
        item["warnings"] = draft["risk_flags"]
        items.append(item)

    return {
        "total_items": len(items),
        "generated_count": generated_count,
        "skipped_count": skipped_count,
        "failed_count": failed_count,
        "items": items,
    }
