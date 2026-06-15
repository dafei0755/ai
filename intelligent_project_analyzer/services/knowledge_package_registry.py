"""Knowledge package registry and binding helpers."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import yaml
from loguru import logger

from .knowledge_asset_registry import KnowledgeAssetRegistry
from .knowledge_asset_runtime import resolve_governed_knowledge_cards


_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "knowledge_package_registry.yaml"
_ACTIVATION_PACK_DIR = Path(__file__).resolve().parent.parent / "knowledge_base" / "activation_packs"


class KnowledgePackageRegistry:
    """Resolve logical kp.xxx identifiers into searchable package metadata."""

    def __init__(self, registry_path: Optional[Path] = None) -> None:
        self.registry_path = Path(registry_path or _CONFIG_PATH)
        self._data = self._load()

    def _load(self) -> Dict[str, Any]:
        if not self.registry_path.exists():
            logger.warning(f"[KnowledgePackageRegistry] missing registry: {self.registry_path}")
            return {"packages": {}, "defaults": {}}
        try:
            with open(self.registry_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {"packages": {}, "defaults": {}}
        except Exception as exc:
            logger.warning(f"[KnowledgePackageRegistry] failed to load registry: {exc}")
            return {"packages": {}, "defaults": {}}

    @property
    def defaults(self) -> Dict[str, Any]:
        return deepcopy(self._data.get("defaults") or {})

    def list_packages(self) -> List[Dict[str, Any]]:
        packages = self._data.get("packages") or {}
        result = []
        for package_id, package in sorted(packages.items()):
            item = deepcopy(package or {})
            item["package_id"] = package_id
            item.setdefault("status", "active")
            item.setdefault("backend", self.defaults.get("backend", "milvus"))
            item.setdefault("collection_name", self.defaults.get("collection_name", "design_knowledge_base"))
            result.append(item)
        return result

    def get_package(self, package_id: str) -> Optional[Dict[str, Any]]:
        package = (self._data.get("packages") or {}).get(package_id)
        if not package:
            return None
        item = deepcopy(package)
        item["package_id"] = package_id
        item.setdefault("backend", self.defaults.get("backend", "milvus"))
        item.setdefault("collection_name", self.defaults.get("collection_name", "design_knowledge_base"))
        return item

    def resolve(self, package_ids: Iterable[str]) -> List[Dict[str, Any]]:
        resolved = []
        for package_id in package_ids or []:
            if not package_id:
                continue
            package = self.get_package(str(package_id))
            if package:
                resolved.append(package)
            else:
                logger.warning(f"[KnowledgePackageRegistry] unknown package_id: {package_id}")
        return resolved

    def build_search_context(self, binding: Dict[str, Any], project_type: str = "") -> Dict[str, Any]:
        """Build a compact search context from project knowledge binding."""
        binding = binding or {}
        package_ids = self._unique_strings(
            list(binding.get("package_ids", []) or []) + list(binding.get("knowledge_packages", []) or [])
        )
        binding_tags = [str(item) for item in binding.get("search_tags", []) or [] if item]
        packages = self.resolve(package_ids)

        package_tags: List[str] = []
        package_project_types: List[str] = []
        for package in packages:
            package_tags.extend(str(tag) for tag in package.get("search_tags", []) or [] if tag)
            package_project_types.extend(str(t) for t in package.get("project_types", []) or [] if t)

        tags = sorted({*binding_tags, *package_tags})
        project_types = sorted({*(package_project_types or []), *( [project_type] if project_type else [] )})
        approved_cards = resolve_governed_knowledge_cards(
            package_ids=package_ids,
            intended_use=str(binding.get("intended_use") or "theme_generation"),
            min_evidence_level=str(binding.get("min_evidence_level") or "weak_evidence"),
        )
        return {
            "knowledge_packages": package_ids,
            "resolved_packages": packages,
            "search_tags": tags,
            "project_types": project_types,
            "project_type": project_type,
            "approved_knowledge_cards": approved_cards,
        }

    def build_coverage_report(self) -> Dict[str, Any]:
        """Report governed approved-card coverage for each logical knowledge package."""
        packages = self.list_packages()
        asset_index = KnowledgeAssetRegistry().load_index()
        package_index = asset_index.get("package_index") or {}
        approved_cards = asset_index.get("cards") or {}
        activation_refs = self._load_activation_pack_package_refs()

        enriched: List[Dict[str, Any]] = []
        for package in packages:
            package_id = package["package_id"]
            card_ids = sorted(
                {
                    str(card_id)
                    for card_id in package_index.get(package_id, []) or []
                    if (approved_cards.get(str(card_id)) or {}).get("status") == "approved"
                }
            )
            activation_pack_ids = sorted(activation_refs.get(package_id, set()))
            if card_ids:
                coverage_status = "ready"
            elif activation_pack_ids:
                coverage_status = "referenced_no_cards"
            else:
                coverage_status = "registered_only"

            item = deepcopy(package)
            item.update(
                {
                    "approved_card_ids": card_ids,
                    "approved_card_count": len(card_ids),
                    "activation_pack_ids": activation_pack_ids,
                    "activation_pack_ref_count": len(activation_pack_ids),
                    "coverage_status": coverage_status,
                }
            )
            enriched.append(item)

        missing_for_referenced = [
            item["package_id"]
            for item in enriched
            if item["activation_pack_ref_count"] > 0 and item["approved_card_count"] == 0
        ]
        return {
            "package_count": len(enriched),
            "approved_card_count": len(
                {
                    card_id
                    for item in enriched
                    for card_id in item.get("approved_card_ids", [])
                }
            ),
            "package_with_approved_cards_count": sum(1 for item in enriched if item["approved_card_count"] > 0),
            "activation_referenced_package_count": sum(1 for item in enriched if item["activation_pack_ref_count"] > 0),
            "missing_approved_cards_for_referenced_packages": sorted(missing_for_referenced),
            "packages": enriched,
        }

    def _load_activation_pack_package_refs(self) -> Dict[str, set[str]]:
        refs: Dict[str, set[str]] = {}
        if not _ACTIVATION_PACK_DIR.exists():
            return refs
        for path in sorted(_ACTIVATION_PACK_DIR.glob("*_pack.yaml")):
            try:
                pack = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except Exception as exc:
                logger.warning(f"[KnowledgePackageRegistry] failed to load activation pack {path}: {exc}")
                continue
            pack_id = str(pack.get("pack_id") or path.stem)
            binding = (
                pack.get("knowledge_recall_profile")
                or pack.get("knowledge_base_binding")
                or pack.get("knowledge_binding")
                or {}
            )
            package_ids = self._unique_strings(
                list(binding.get("package_ids", []) or []) + list(binding.get("knowledge_packages", []) or [])
            )
            for package_id in package_ids:
                refs.setdefault(package_id, set()).add(pack_id)
        return refs

    @staticmethod
    def _unique_strings(items: Iterable[Any]) -> List[str]:
        seen = set()
        result = []
        for item in items or []:
            if item is None:
                continue
            text = str(item).strip()
            if text and text not in seen:
                seen.add(text)
                result.append(text)
        return result


def get_knowledge_context_from_state(state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    state = state or {}
    pack = state.get("project_definition_activation_pack") or {}
    binding = pack.get("knowledge_base_binding") or pack.get("knowledge_binding") or {}
    project_type = state.get("project_type") or (pack.get("classification") or {}).get("project_type") or ""
    return KnowledgePackageRegistry().build_search_context(binding, project_type=str(project_type or ""))
