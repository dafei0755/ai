"""Diagnostics for space classification governance.

This module is intentionally read-only. It reports how a user input travels
through classification, ontology binding, activation packs, and knowledge
package bindings without mutating registries or approved assets.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import yaml

from .project_type_detector import (
    FOUNDING_TYPE_REGISTRY,
    PARENT_TYPE_MAP,
    PROJECT_TYPE_REGISTRY,
    SPATIAL_LAYER_REGISTRY,
    SUBDOMAIN_REGISTRY,
)
from .space_classification_service import SpaceClassificationService
from .space_context_packet_service import SpaceContextPacketService
from .type_operating_profile_registry import TypeOperatingProfileRegistry


_ROOT = Path(__file__).resolve().parent.parent
_CONFIG = _ROOT / "config"
_KB = _ROOT / "knowledge_base"
_MASTER_INDEX = _CONFIG / "registries" / "classification_master_index.yaml"
_SUBDOMAIN_REGISTRY = _CONFIG / "registries" / "subdomain_registry.yaml"
_FOUNDING_TYPE_REGISTRY = _CONFIG / "registries" / "founding_type_registry.yaml"
_PROJECT_TYPE_META = _CONFIG / "registries" / "project_type_registry_meta.yaml"
_PROJECT_SCALE_REGISTRY = _CONFIG / "registries" / "project_scale_registry.yaml"
_SPATIAL_LAYER_REGISTRY = _CONFIG / "registries" / "spatial_layer_registry.yaml"
_TYPE_OPERATING_PROFILES = _CONFIG / "type_operating_profiles.yaml"
_ONTOLOGY_DIMENSIONS = _KB / "ontology_dimension_registry.yaml"
_KNOWLEDGE_PACKAGE_REGISTRY = _CONFIG / "knowledge_package_registry.yaml"
_DEFAULT_OVERRIDE_PATH = _ROOT / "data" / "space_classification_admin_overrides.json"
_EDITABLE_FIELDS = [
    "display_name",
    "name_en",
    "description",
    "status",
    "review_status",
    "owner",
    "ontology_framework_id",
]


class SpaceClassificationDiagnosticsService:
    """Build admin-facing diagnostic reports for the classification system."""

    def __init__(
        self,
        classification_service: Optional[SpaceClassificationService] = None,
        override_path: Optional[Path] = None,
    ) -> None:
        self.classification_service = classification_service or SpaceClassificationService()
        self.override_path = Path(
            override_path
            or os.environ.get("SPACE_CLASSIFICATION_ADMIN_OVERRIDES_PATH")
            or _DEFAULT_OVERRIDE_PATH
        )

    def diagnose(
        self,
        user_input: str,
        structured_requirements: Optional[Dict[str, Any]] = None,
        confirmed_tasks: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Return a full diagnostic report for a single project description."""
        result = self.classification_service.classify_and_activate(
            user_input=user_input,
            structured_requirements=structured_requirements,
            confirmed_tasks=confirmed_tasks,
        )
        context_packet = SpaceContextPacketService(
            classification_service=self.classification_service
        ).build_from_activation(user_input, result)
        classification = result["space_classification"]
        activation_pack = result["project_definition_activation_pack"]
        classification_output = activation_pack.get("classification_output") or {}
        v18 = activation_pack.get("_v18_extensions") or {}

        activation_pack_yaml = self._load_activation_pack(v18.get("activation_pack_id"))
        activation_pack_coordination = context_packet.get("activation_pack_coordination") or {}
        ontology_binding = context_packet.get("ontology_binding") or {}
        context_knowledge_binding = context_packet.get("knowledge_binding") or {}
        pack_knowledge_binding = self._pack_knowledge_binding(activation_pack_yaml)
        runtime_knowledge_binding = activation_pack.get("knowledge_base_binding") or {}
        knowledge_package_ids = self._unique_strings(
            self._as_list(context_knowledge_binding.get("knowledge_package_ids"))
            + self._as_list(pack_knowledge_binding.get("package_ids"))
            + self._as_list(pack_knowledge_binding.get("knowledge_packages"))
            + self._as_list(runtime_knowledge_binding.get("knowledge_packages"))
        )
        ontology_dimension_ids = self._unique_strings(
            self._as_list(v18.get("active_ontology_dimension_ids"))
            + self._as_list(v18.get("priority_ontology_dimension_ids"))
        )

        gaps = self._diagnostic_gaps(
            classification=classification,
            v18=v18,
            activation_pack_yaml=activation_pack_yaml,
            ontology_dimension_ids=ontology_dimension_ids,
            knowledge_package_ids=knowledge_package_ids,
        )

        return {
            "schema_version": "space_classification_diagnostic.v1",
            "input": {
                "user_input": user_input,
                "structured_requirements": structured_requirements or {},
            },
            "normalization_trace": (
                (classification.get("evidence") or {}).get("normalization_trace") or {}
            ),
            "classification": classification,
            "classification_output": classification_output,
            "subdomain_signals": (
                ((classification.get("evidence") or {}).get("_detector_full") or {}).get("subdomain_signals")
                or []
            ),
            "founding_type_candidates": (
                ((classification.get("evidence") or {}).get("_detector_full") or {}).get("founding_type_candidates")
                or []
            ),
            "binding_summary": {
                "ontology_framework_id": v18.get("ontology_framework_id"),
                "subdomain_id": v18.get("subdomain_id"),
                "activation_pack_id": v18.get("activation_pack_id"),
                "secondary_activation_pack_ids": self._as_list(
                    ontology_binding.get("secondary_activation_pack_ids")
                ),
                "project_scale": v18.get("project_scale"),
                "spatial_layer_ids": self._as_list(v18.get("spatial_layer_ids")),
                "ontology_dimension_ids": ontology_dimension_ids,
                "priority_ontology_dimension_ids": self._as_list(
                    v18.get("priority_ontology_dimension_ids")
                ),
                "knowledge_package_ids": knowledge_package_ids,
                "industry_domain": v18.get("industry_domain"),
                "founding_type": v18.get("founding_type"),
                "knowledge_card_weights": v18.get("knowledge_card_weights") or {},
            },
            "context_packet": context_packet,
            "activation_pack_coordination": activation_pack_coordination,
            "coverage_gaps": gaps,
            "health": self._health(gaps),
            "activation_pack_preview": {
                "loaded": bool(activation_pack_yaml),
                "pack_id": activation_pack_yaml.get("pack_id"),
                "routing_binding": activation_pack_yaml.get("routing_binding") or {},
            },
        }

    def validate_registry_consistency(self) -> Dict[str, Any]:
        """Validate cross-file consistency for classification governance."""
        master = self._load_yaml(_MASTER_INDEX)
        subdomains = self._load_yaml(_SUBDOMAIN_REGISTRY)
        founding_types = self._load_yaml(_FOUNDING_TYPE_REGISTRY)
        project_type_meta = self._load_yaml(_PROJECT_TYPE_META)
        project_scales = self._load_yaml(_PROJECT_SCALE_REGISTRY)
        spatial_layers = self._load_yaml(_SPATIAL_LAYER_REGISTRY)
        ontology_dimensions = self._load_yaml(_ONTOLOGY_DIMENSIONS)
        knowledge_packages = self._load_yaml(_KNOWLEDGE_PACKAGE_REGISTRY)
        type_profile_registry = TypeOperatingProfileRegistry()
        type_profile_health = type_profile_registry.validate(PROJECT_TYPE_REGISTRY.keys())

        axis_mappings = master.get("axis_mappings") or {}
        project_type_to_framework = (
            axis_mappings.get("project_type_to_framework") or {}
        ).get("mappings") or {}
        subdomain_to_pack = (axis_mappings.get("subdomain_to_pack") or {}).get("mappings") or {}
        pack_paths = (axis_mappings.get("subdomain_to_pack") or {}).get("pack_paths") or {}
        spatial_layer_to_dimensions = (
            axis_mappings.get("spatial_layer_to_dimensions") or {}
        ).get("mappings") or {}

        dimension_ids = set((ontology_dimensions.get("ontology_dimensions") or {}).keys())
        package_ids = set((knowledge_packages.get("packages") or {}).keys())
        subdomain_items = subdomains.get("items") or {}
        founding_type_items = founding_types.get("items") or {}
        spatial_layer_items = spatial_layers.get("items") or {}
        project_scale_items = project_scales.get("items") or {}
        meta_items = project_type_meta.get("project_types") or project_type_meta.get("items") or {}
        profile_items = type_profile_registry.explicit_profiles

        missing_framework = sorted(
            type_id for type_id in PROJECT_TYPE_REGISTRY if type_id not in project_type_to_framework
        )
        missing_meta = sorted(type_id for type_id in PROJECT_TYPE_REGISTRY if type_id not in meta_items)
        type_profile_issues = type_profile_health.get("issues") or {}
        missing_type_profiles = self._as_list(
            type_profile_issues.get("missing_type_operating_profiles")
        )
        missing_type_profile_knowledge_refs = self._as_list(
            type_profile_issues.get("missing_type_profile_knowledge_package_refs")
        )
        missing_type_profile_ids = self._as_list(
            type_profile_issues.get("missing_type_profile_ids")
        )
        duplicate_type_profile_ids = self._as_list(
            type_profile_issues.get("duplicate_type_profile_ids")
        )
        type_profile_framework_mismatches = self._as_list(
            type_profile_issues.get("type_profile_framework_mismatches")
        )
        missing_subdomain_pack_mappings = sorted(
            subdomain_id for subdomain_id in subdomain_items if subdomain_id not in subdomain_to_pack
        )
        missing_pack_files = sorted(
            pack_id
            for pack_id in set(subdomain_to_pack.values())
            if not self._activation_pack_file_exists(pack_id, pack_paths.get(pack_id))
        )
        missing_dimensions = sorted(
            dimension_id
            for mapping in spatial_layer_to_dimensions.values()
            for dimension_id in self._as_list(mapping.get("active_dimensions"))
            + self._as_list(mapping.get("priority_dimensions"))
            if dimension_id not in dimension_ids
        )
        unknown_project_scale_spatial_layers = sorted(
            layer_id
            for item in project_scale_items.values()
            for layer_id in self._as_list((item or {}).get("default_spatial_layer_ids"))
            if layer_id not in spatial_layer_items
        )
        unknown_spatial_layer_dimension_mappings = sorted(
            layer_id
            for layer_id in spatial_layer_to_dimensions
            if layer_id not in spatial_layer_items
        )
        spatial_layers_without_dimension_mapping = sorted(
            layer_id
            for layer_id in spatial_layer_items
            if layer_id not in spatial_layer_to_dimensions
        )
        missing_package_refs = sorted(
            package_id
            for package_id in self._iter_activation_pack_knowledge_packages(subdomain_to_pack.values())
            if package_id not in package_ids
        )
        founding_yaml_detector_drift = sorted(
            founding_type_id
            for founding_type_id in set(founding_type_items) | set(FOUNDING_TYPE_REGISTRY)
            if self._founding_type_runtime_fingerprint(founding_type_items.get(founding_type_id) or {})
            != self._founding_type_runtime_fingerprint(FOUNDING_TYPE_REGISTRY.get(founding_type_id) or {})
        )

        issues = {
            "missing_project_type_framework_mappings": missing_framework,
            "missing_project_type_meta": missing_meta,
            "missing_type_operating_profiles": missing_type_profiles,
            "missing_type_profile_ids": missing_type_profile_ids,
            "duplicate_type_profile_ids": duplicate_type_profile_ids,
            "type_profile_framework_mismatches": type_profile_framework_mismatches,
            "missing_type_profile_knowledge_package_refs": missing_type_profile_knowledge_refs,
            "missing_subdomain_pack_mappings": missing_subdomain_pack_mappings,
            "founding_type_yaml_detector_drift": founding_yaml_detector_drift,
            "missing_activation_pack_files": missing_pack_files,
            "missing_ontology_dimensions": missing_dimensions,
            "unknown_project_scale_spatial_layers": unknown_project_scale_spatial_layers,
            "unknown_spatial_layer_dimension_mappings": unknown_spatial_layer_dimension_mappings,
            "spatial_layers_without_dimension_mapping": spatial_layers_without_dimension_mapping,
            "missing_knowledge_package_refs": missing_package_refs,
        }
        warning_issue_keys = {
            "missing_project_type_meta",
            "missing_type_operating_profiles",
            "founding_type_yaml_detector_drift",
            "missing_type_profile_knowledge_package_refs",
        }
        blocking_count = sum(len(v) for k, v in issues.items() if k not in warning_issue_keys)
        warning_count = (
            len(missing_meta)
            + len(missing_type_profiles)
            + len(founding_yaml_detector_drift)
            + len(missing_type_profile_knowledge_refs)
        )

        return {
            "schema_version": "space_classification_registry_health.v1",
            "status": "ok" if blocking_count == 0 else "needs_attention",
            "summary": {
                "project_type_count": len(PROJECT_TYPE_REGISTRY),
                "project_type_framework_mapping_count": len(project_type_to_framework),
                "project_type_meta_count": len(meta_items),
                "type_operating_profile_count": len(profile_items),
                "type_operating_profile_issue_count": sum(
                    len(values) for values in type_profile_issues.values()
                ),
                "subdomain_count": len(subdomain_items),
                "subdomain_pack_mapping_count": len(subdomain_to_pack),
                "founding_type_count": len(founding_type_items),
                "runtime_founding_type_count": len(FOUNDING_TYPE_REGISTRY),
                "spatial_layer_count": len(spatial_layer_items),
                "runtime_spatial_layer_count": len(SPATIAL_LAYER_REGISTRY),
                "ontology_dimension_count": len(dimension_ids),
                "knowledge_package_count": len(package_ids),
                "blocking_issue_count": blocking_count,
                "warning_issue_count": warning_count,
            },
            "issues": issues,
        }

    def list_subdomains(self) -> Dict[str, Any]:
        """Return admin-facing subdomain registry records."""
        master = self._load_yaml(_MASTER_INDEX)
        subdomains = self._load_yaml(_SUBDOMAIN_REGISTRY)
        knowledge_packages = self._load_yaml(_KNOWLEDGE_PACKAGE_REGISTRY)
        axis_mappings = master.get("axis_mappings") or {}
        project_type_to_framework = (
            axis_mappings.get("project_type_to_framework") or {}
        ).get("mappings") or {}
        subdomain_to_pack = (axis_mappings.get("subdomain_to_pack") or {}).get("mappings") or {}
        yaml_items = subdomains.get("items") or {}

        items: List[Dict[str, Any]] = []
        for subdomain_id in sorted(set(yaml_items) | set(SUBDOMAIN_REGISTRY)):
            yaml_item = yaml_items.get(subdomain_id) or {}
            runtime_item = SUBDOMAIN_REGISTRY.get(subdomain_id) or {}
            parent_id = (
                yaml_item.get("parent_project_type_id")
                or runtime_item.get("parent_project_type_id")
            )
            activation_pack_id = (
                yaml_item.get("activation_pack_id")
                or runtime_item.get("activation_pack_id")
                or subdomain_to_pack.get(subdomain_id)
            )
            activation_pack_yaml = self._load_activation_pack(activation_pack_id)
            routing = activation_pack_yaml.get("routing_binding") or {}
            pack_binding = self._pack_knowledge_binding(activation_pack_yaml)
            package_ids = self._unique_strings(
                self._as_list(pack_binding.get("package_ids"))
                + self._as_list(pack_binding.get("knowledge_packages"))
            )
            package_registry = knowledge_packages.get("packages") or {}
            items.append({
                "subdomain_id": subdomain_id,
                "name_cn": yaml_item.get("name_cn") or runtime_item.get("name") or subdomain_id,
                "name_en": yaml_item.get("name_en") or "",
                "parent_project_type_id": parent_id,
                "parent_project_type_name": (PROJECT_TYPE_REGISTRY.get(parent_id) or {}).get("name"),
                "ontology_framework_id": project_type_to_framework.get(parent_id),
                "activation_pack_id": activation_pack_id,
                "activation_pack_file": yaml_item.get("activation_pack_file"),
                "activation_pack_loaded": bool(activation_pack_yaml),
                "status": yaml_item.get("status") or runtime_item.get("status") or "reserved",
                "review_status": yaml_item.get("review_status") or subdomains.get("review_status"),
                "owner": yaml_item.get("owner") or subdomains.get("owner"),
                "signal_keywords": self._as_list(
                    yaml_item.get("signal_keywords") or runtime_item.get("signal_keywords")
                ),
                "specialty_tag_assist": self._as_list(yaml_item.get("specialty_tag_assist")),
                "aliases": self._as_list(yaml_item.get("aliases")),
                "has_runtime_detector_binding": subdomain_id in SUBDOMAIN_REGISTRY,
                "has_yaml_registry_binding": subdomain_id in yaml_items,
                "has_master_index_pack_mapping": subdomain_to_pack.get(subdomain_id) == activation_pack_id,
                "routing_binding_matched": bool(activation_pack_yaml)
                and routing.get("parent_project_type_id") == parent_id
                and routing.get("subdomain_id") == subdomain_id,
                "knowledge_package_ids": package_ids,
                "missing_knowledge_package_ids": [
                    package_id for package_id in package_ids if package_id not in package_registry
                ],
                "editable_fields": [
                    "name_cn",
                    "name_en",
                    "status",
                    "review_status",
                    "owner",
                    "signal_keywords",
                    "specialty_tag_assist",
                    "aliases",
                ],
            })

        return {
            "schema_version": "space_classification_subdomains.v1",
            "items": items,
            "total": len(items),
        }

    def validate_subdomain_registry(self) -> Dict[str, Any]:
        """Validate subdomain registry, detector mirror, and activation pack routing."""
        subdomains = self._load_yaml(_SUBDOMAIN_REGISTRY)
        master = self._load_yaml(_MASTER_INDEX)
        yaml_items = subdomains.get("items") or {}
        axis_mappings = master.get("axis_mappings") or {}
        subdomain_to_pack = (axis_mappings.get("subdomain_to_pack") or {}).get("mappings") or {}

        invalid_parent_type = sorted(
            subdomain_id
            for subdomain_id, item in yaml_items.items()
            if item.get("parent_project_type_id") not in PROJECT_TYPE_REGISTRY
        )
        subdomain_yaml_detector_drift = sorted(
            subdomain_id
            for subdomain_id in set(yaml_items) | set(SUBDOMAIN_REGISTRY)
            if self._subdomain_runtime_fingerprint(yaml_items.get(subdomain_id) or {})
            != self._subdomain_runtime_fingerprint(SUBDOMAIN_REGISTRY.get(subdomain_id) or {})
        )
        missing_master_pack_mapping = sorted(
            subdomain_id
            for subdomain_id in yaml_items
            if subdomain_id not in subdomain_to_pack
        )
        active_subdomain_without_pack = sorted(
            subdomain_id
            for subdomain_id, item in yaml_items.items()
            if str(item.get("status") or "").startswith("active")
            and not item.get("activation_pack_id")
        )

        activation_pack_routing_mismatch: List[str] = []
        missing_activation_pack_files: List[str] = []
        for subdomain_id, item in yaml_items.items():
            pack_id = item.get("activation_pack_id") or subdomain_to_pack.get(subdomain_id)
            if not pack_id:
                continue
            pack = self._load_activation_pack(pack_id)
            if not pack:
                missing_activation_pack_files.append(str(pack_id))
                continue
            routing = pack.get("routing_binding") or {}
            if (
                routing.get("parent_project_type_id") != item.get("parent_project_type_id")
                or routing.get("subdomain_id") != subdomain_id
            ):
                activation_pack_routing_mismatch.append(subdomain_id)

        issues = {
            "invalid_subdomain_parent_type": invalid_parent_type,
            "subdomain_yaml_detector_drift": subdomain_yaml_detector_drift,
            "missing_master_pack_mapping": missing_master_pack_mapping,
            "missing_activation_pack_files": sorted(set(missing_activation_pack_files)),
            "activation_pack_routing_mismatch": sorted(activation_pack_routing_mismatch),
            "active_subdomain_without_pack": active_subdomain_without_pack,
        }
        blocking_count = sum(len(values) for values in issues.values())
        items = self.list_subdomains()["items"]
        return {
            "schema_version": "space_classification_subdomain_health.v1",
            "status": "ok" if blocking_count == 0 else "needs_attention",
            "summary": {
                "subdomain_count": len(yaml_items),
                "runtime_subdomain_count": len(SUBDOMAIN_REGISTRY),
                "activation_pack_loaded_count": sum(
                    1 for item in items if item.get("activation_pack_loaded")
                ),
                "blocking_issue_count": blocking_count,
                "warning_issue_count": 0,
            },
            "issues": issues,
        }

    def list_project_types(self) -> Dict[str, Any]:
        """Return editable admin records for all known project types."""
        master = self._load_yaml(_MASTER_INDEX)
        project_type_meta = self._load_yaml(_PROJECT_TYPE_META)
        type_profile_registry = TypeOperatingProfileRegistry()
        overrides = self._load_overrides()
        framework_mappings = (
            ((master.get("axis_mappings") or {}).get("project_type_to_framework") or {})
            .get("mappings")
            or {}
        )
        meta_items = project_type_meta.get("items") or {}
        profile_summaries = {
            item["type_id"]: item
            for item in type_profile_registry.list_profile_summaries(PROJECT_TYPE_REGISTRY.keys())
        }

        items: List[Dict[str, Any]] = []
        for type_id, config in sorted(PROJECT_TYPE_REGISTRY.items()):
            meta = meta_items.get(type_id) or {}
            override = overrides.get(type_id) or {}
            profile_summary = profile_summaries.get(type_id) or {}
            item = {
                "type_id": type_id,
                "display_name": override.get("display_name") or meta.get("display_name") or config.get("name") or type_id,
                "name": config.get("name") or type_id,
                "name_en": override.get("name_en") or config.get("name_en") or "",
                "description": override.get("description") or meta.get("description") or "",
                "status": override.get("status") or meta.get("status") or (project_type_meta.get("defaults") or {}).get("status", "active_mvp"),
                "review_status": override.get("review_status") or meta.get("review_status") or (project_type_meta.get("defaults") or {}).get("review_status", "approved"),
                "owner": override.get("owner") or meta.get("owner") or (project_type_meta.get("defaults") or {}).get("owner", "core_team"),
                "parent_type": PARENT_TYPE_MAP.get(type_id),
                "ontology_framework_id": override.get("ontology_framework_id") or framework_mappings.get(type_id),
                "has_type_operating_profile": bool(profile_summary.get("has_explicit_profile")),
                "profile_id": profile_summary.get("profile_id"),
                "type_operating_profile": profile_summary,
                "priority": config.get("priority", 0),
                "keyword_count": len(config.get("keywords", [])),
                "has_admin_override": bool(override),
                "editable_fields": list(_EDITABLE_FIELDS),
            }
            items.append(item)

        items.sort(key=lambda item: (-int(item.get("priority") or 0), item["type_id"]))
        return {
            "schema_version": "space_classification_types.v1",
            "items": items,
            "total": len(items),
            "override_count": sum(1 for item in items if item["has_admin_override"]),
            "editable_fields": list(_EDITABLE_FIELDS),
        }

    def get_project_type(self, type_id: str) -> Dict[str, Any]:
        for item in self.list_project_types()["items"]:
            if item["type_id"] == type_id:
                return item
        raise KeyError(type_id)

    def update_project_type(self, type_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Persist editable governance fields for a project type."""
        if type_id not in PROJECT_TYPE_REGISTRY:
            raise KeyError(type_id)

        clean: Dict[str, Any] = {}
        for field in _EDITABLE_FIELDS:
            value = payload.get(field)
            if isinstance(value, str):
                value = value.strip()
            if value not in (None, ""):
                clean[field] = value

        overrides = self._load_overrides()
        existing = overrides.get(type_id) or {}
        overrides[type_id] = {**existing, **clean}
        self._save_overrides(overrides)
        return self.get_project_type(type_id)

    def _diagnostic_gaps(
        self,
        classification: Dict[str, Any],
        v18: Dict[str, Any],
        activation_pack_yaml: Dict[str, Any],
        ontology_dimension_ids: List[str],
        knowledge_package_ids: List[str],
    ) -> List[Dict[str, str]]:
        gaps: List[Dict[str, str]] = []
        if classification.get("coverage_gap"):
            gaps.append({
                "severity": "warning",
                "code": "classification_coverage_gap",
                "message": "分类结果需要进一步补充行业或上下文信息。",
            })
        if not v18.get("ontology_framework_id"):
            gaps.append({
                "severity": "blocking",
                "code": "missing_ontology_framework",
                "message": "未找到项目类型到 ontology framework 的映射。",
            })
        if v18.get("subdomain_id") and not v18.get("activation_pack_id"):
            gaps.append({
                "severity": "blocking",
                "code": "missing_activation_pack_mapping",
                "message": "识别出细分业态，但未绑定 activation pack。",
            })
        if v18.get("activation_pack_id") and not activation_pack_yaml:
            gaps.append({
                "severity": "blocking",
                "code": "missing_activation_pack_file",
                "message": "activation pack 映射存在，但文件不可读取。",
            })
        if not ontology_dimension_ids:
            gaps.append({
                "severity": "warning",
                "code": "missing_active_ontology_dimensions",
                "message": "本次分类未激活 ontology dimension。",
            })
        if not knowledge_package_ids:
            gaps.append({
                "severity": "warning",
                "code": "missing_knowledge_packages",
                "message": "本次分类未绑定知识包。",
            })
        return gaps

    @staticmethod
    def _health(gaps: List[Dict[str, str]]) -> Dict[str, Any]:
        blocking = [gap for gap in gaps if gap.get("severity") == "blocking"]
        warnings = [gap for gap in gaps if gap.get("severity") == "warning"]
        if blocking:
            severity = "blocking"
        elif warnings:
            severity = "warning"
        else:
            severity = "ok"
        return {
            "severity": severity,
            "blocking_count": len(blocking),
            "warning_count": len(warnings),
        }

    def _load_activation_pack(self, pack_id: Optional[str]) -> Dict[str, Any]:
        if not pack_id:
            return {}
        path = _KB / "activation_packs" / f"{pack_id}.yaml"
        return self._load_yaml(path)

    @staticmethod
    def _activation_pack_file_exists(pack_id: str, configured_path: Optional[str]) -> bool:
        candidates = [_KB / "activation_packs" / f"{pack_id}.yaml"]
        if configured_path:
            candidates.append((_CONFIG / "registries" / configured_path).resolve())
        return any(path.exists() for path in candidates)

    def _iter_activation_pack_knowledge_packages(self, pack_ids: Iterable[str]) -> Iterable[str]:
        for pack_id in set(pack_ids):
            data = self._load_activation_pack(pack_id)
            binding = self._pack_knowledge_binding(data)
            for package_id in (
                self._as_list(binding.get("package_ids"))
                + self._as_list(binding.get("knowledge_packages"))
            ):
                yield package_id

    @staticmethod
    def _pack_knowledge_binding(pack: Dict[str, Any]) -> Dict[str, Any]:
        return (
            pack.get("knowledge_recall_profile")
            or pack.get("knowledge_base_binding")
            or pack.get("knowledge_binding")
            or {}
        )

    @staticmethod
    def _subdomain_runtime_fingerprint(item: Dict[str, Any]) -> Dict[str, Any]:
        name = item.get("name") or item.get("name_cn")
        return {
            "name": name,
            "name_en": item.get("name_en"),
            "parent_project_type_id": item.get("parent_project_type_id"),
            "activation_pack_id": item.get("activation_pack_id"),
            "signal_keywords": SpaceClassificationDiagnosticsService._as_list(
                item.get("signal_keywords")
            ),
            "specialty_tag_assist": SpaceClassificationDiagnosticsService._as_list(
                item.get("specialty_tag_assist")
            ),
            "aliases": SpaceClassificationDiagnosticsService._as_list(item.get("aliases")),
            "status": item.get("status"),
        }

    @staticmethod
    def _founding_type_runtime_fingerprint(item: Dict[str, Any]) -> Dict[str, Any]:
        name = item.get("name") or item.get("name_cn")
        return {
            "name": name,
            "name_en": item.get("name_en"),
            "group": item.get("group"),
            "keywords": SpaceClassificationDiagnosticsService._as_list(item.get("keywords")),
            "secondary_keywords": SpaceClassificationDiagnosticsService._as_list(
                item.get("secondary_keywords")
            ),
            "negative_co_occurrence": SpaceClassificationDiagnosticsService._as_list(
                item.get("negative_co_occurrence")
            ),
            "priority": item.get("priority"),
            "status": item.get("status"),
        }

    @staticmethod
    def _load_yaml(path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}

    def _load_overrides(self) -> Dict[str, Any]:
        if not self.override_path.exists():
            return {}
        with open(self.override_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}

    def _save_overrides(self, data: Dict[str, Any]) -> None:
        self.override_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.override_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)

    @staticmethod
    def _as_list(value: Any) -> List[Any]:
        if value is None or value == "":
            return []
        if isinstance(value, list):
            return value
        return [value]

    @staticmethod
    def _unique_strings(values: Iterable[Any]) -> List[str]:
        result: List[str] = []
        seen = set()
        for value in values:
            if not isinstance(value, str) or not value or value in seen:
                continue
            result.append(value)
            seen.add(value)
        return result
