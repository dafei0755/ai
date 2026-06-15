"""Read-only registry for Type Operating Profiles.

Type Operating Profiles sit after project type detection. They decide how a
classified type activates ontology, method profiles, knowledge packages, and
downstream delivery profiles.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import yaml

from .project_type_detector import PROJECT_TYPE_REGISTRY


_ROOT = Path(__file__).resolve().parent.parent
_CONFIG = _ROOT / "config"
_PROFILE_PATH = _CONFIG / "type_operating_profiles.yaml"
_MASTER_INDEX_PATH = _CONFIG / "registries" / "classification_master_index.yaml"
_KNOWLEDGE_PACKAGE_REGISTRY_PATH = _CONFIG / "knowledge_package_registry.yaml"


class TypeOperatingProfileRegistry:
    """Load, merge, summarize, and validate type operating profiles."""

    def __init__(
        self,
        profile_path: Optional[Path] = None,
        master_index_path: Optional[Path] = None,
        knowledge_package_registry_path: Optional[Path] = None,
    ) -> None:
        self.profile_path = Path(profile_path or _PROFILE_PATH)
        self.master_index_path = Path(master_index_path or _MASTER_INDEX_PATH)
        self.knowledge_package_registry_path = Path(
            knowledge_package_registry_path or _KNOWLEDGE_PACKAGE_REGISTRY_PATH
        )
        self._raw_profiles = self._load_yaml(self.profile_path)
        self._master_index = self._load_yaml(self.master_index_path)
        self._knowledge_packages = self._load_yaml(self.knowledge_package_registry_path)

    @property
    def explicit_profiles(self) -> Dict[str, Any]:
        return self._raw_profiles.get("profiles") or {}

    def get_profile(self, type_id: Optional[str]) -> Dict[str, Any]:
        """Return defaults merged with an explicit profile when present."""
        defaults = deepcopy(self._raw_profiles.get("defaults", {}))
        profile = deepcopy(self.explicit_profiles.get(type_id or "", {}))
        return self._deep_merge(defaults, profile)

    def get_profile_summary(self, type_id: str) -> Dict[str, Any]:
        profile = self.get_profile(type_id)
        explicit = self.explicit_profiles.get(type_id) or {}
        binding = profile.get("knowledge_base_binding") or profile.get("knowledge_binding") or {}
        knowledge_package_ids = self._unique_strings(binding.get("knowledge_packages"))
        package_registry = self._knowledge_packages.get("packages") or {}
        missing_packages = [
            package_id for package_id in knowledge_package_ids if package_id not in package_registry
        ]
        master_framework = self._master_index_frameworks().get(type_id)
        ontology_framework = profile.get("ontology_framework")
        framework_matches = (
            not master_framework
            or not ontology_framework
            or str(ontology_framework) == str(master_framework)
        )

        issue_codes: List[str] = []
        if not explicit:
            issue_codes.append("missing_type_operating_profile")
        if not profile.get("profile_id"):
            issue_codes.append("missing_profile_id")
        if not framework_matches:
            issue_codes.append("ontology_framework_mismatch")
        if missing_packages:
            issue_codes.append("missing_knowledge_package_refs")

        type_method_profile = profile.get("type_method_profile") or profile.get("business_method_profile") or {}
        general_method_profile = profile.get("general_method_profile") or {}
        domain_framework = profile.get("domain_framework") or {}
        system_binding = profile.get("system_binding") or {}
        return {
            "type_id": type_id,
            "has_explicit_profile": bool(explicit),
            "profile_id": profile.get("profile_id"),
            "display_label": profile.get("display_label"),
            "primary_bucket": profile.get("primary_bucket"),
            "ontology_framework": ontology_framework,
            "master_index_ontology_framework": master_framework,
            "framework_matches_master_index": framework_matches,
            "required_dimensions": self._unique_strings(domain_framework.get("required_dimensions")),
            "required_min_coverage": domain_framework.get("required_min_coverage"),
            "knowledge_package_ids": knowledge_package_ids,
            "missing_knowledge_package_ids": missing_packages,
            "search_tags": self._unique_strings(binding.get("search_tags")),
            "active_discipline_ids": self._unique_strings(profile.get("active_discipline_ids")),
            "type_method_profile_id": type_method_profile.get("profile_id"),
            "type_method_priority_sequence": self._unique_strings(
                type_method_profile.get("priority_sequence")
            ),
            "general_method_profile_id": general_method_profile.get("profile_id"),
            "general_method_check_ids": [
                item.get("check_id")
                for item in self._as_list(general_method_profile.get("active_checks"))
                if isinstance(item, dict) and item.get("check_id")
            ],
            "downstream_profiles": {
                "questionnaire_profile": profile.get("questionnaire_profile"),
                "floorplan_profile": profile.get("floorplan_profile"),
                "visual_prompt_profile": profile.get("visual_prompt_profile"),
                "deliverable_profile": profile.get("deliverable_profile"),
            },
            "system_target_objects": self._unique_strings(system_binding.get("target_objects")),
            "system_required_freeze": self._unique_strings(system_binding.get("required_freeze")),
            "issue_codes": issue_codes,
        }

    def list_profile_summaries(
        self, type_ids: Optional[Iterable[str]] = None
    ) -> List[Dict[str, Any]]:
        ids = list(type_ids or PROJECT_TYPE_REGISTRY.keys())
        return [self.get_profile_summary(type_id) for type_id in sorted(set(ids))]

    def validate(self, type_ids: Optional[Iterable[str]] = None) -> Dict[str, Any]:
        ids = sorted(set(type_ids or PROJECT_TYPE_REGISTRY.keys()))
        summaries = self.list_profile_summaries(ids)
        profile_ids = [
            str(summary.get("profile_id"))
            for summary in summaries
            if summary.get("profile_id")
        ]
        duplicate_profile_ids = sorted(
            profile_id for profile_id in set(profile_ids) if profile_ids.count(profile_id) > 1
        )
        missing_profiles = sorted(
            summary["type_id"] for summary in summaries if not summary["has_explicit_profile"]
        )
        missing_profile_ids = sorted(
            summary["type_id"] for summary in summaries if not summary.get("profile_id")
        )
        framework_mismatches = sorted(
            summary["type_id"]
            for summary in summaries
            if summary["master_index_ontology_framework"]
            and not summary["framework_matches_master_index"]
        )
        missing_package_refs = sorted(
            f"{summary['type_id']}:{package_id}"
            for summary in summaries
            for package_id in summary["missing_knowledge_package_ids"]
        )

        issues = {
            "missing_type_operating_profiles": missing_profiles,
            "missing_type_profile_ids": missing_profile_ids,
            "duplicate_type_profile_ids": duplicate_profile_ids,
            "type_profile_framework_mismatches": framework_mismatches,
            "missing_type_profile_knowledge_package_refs": missing_package_refs,
        }
        blocking_count = (
            len(missing_profiles)
            + len(missing_profile_ids)
            + len(duplicate_profile_ids)
            + len(framework_mismatches)
        )
        warning_count = len(missing_package_refs)
        return {
            "schema_version": "type_operating_profile_registry_health.v1",
            "status": "ok" if blocking_count == 0 else "needs_attention",
            "summary": {
                "project_type_count": len(ids),
                "explicit_profile_count": sum(1 for item in summaries if item["has_explicit_profile"]),
                "profile_summary_count": len(summaries),
                "blocking_issue_count": blocking_count,
                "warning_issue_count": warning_count,
            },
            "issues": issues,
            "items": summaries,
        }

    def _master_index_frameworks(self) -> Dict[str, Any]:
        axis_mappings = self._master_index.get("axis_mappings") or {}
        return (
            (axis_mappings.get("project_type_to_framework") or {}).get("mappings")
            or {}
        )

    @staticmethod
    def _load_yaml(path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}

    @staticmethod
    def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        result = deepcopy(base)
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(result.get(key), dict):
                result[key] = TypeOperatingProfileRegistry._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    @staticmethod
    def _as_list(value: Any) -> List[Any]:
        if value is None or value == "":
            return []
        if isinstance(value, list):
            return value
        return [value]

    @staticmethod
    def _unique_strings(values: Any) -> List[str]:
        result: List[str] = []
        seen = set()
        for value in TypeOperatingProfileRegistry._as_list(values):
            if value in (None, ""):
                continue
            text = str(value)
            if text in seen:
                continue
            result.append(text)
            seen.add(text)
        return result
