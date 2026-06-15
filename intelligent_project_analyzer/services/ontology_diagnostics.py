"""Read-only diagnostics for ontology governance."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Set

import yaml

from .knowledge_asset_registry import KnowledgeAssetRegistry
from .project_type_detector import PROJECT_TYPE_REGISTRY


_ROOT = Path(__file__).resolve().parent.parent
_CONFIG = _ROOT / "config"
_KB = _ROOT / "knowledge_base"
_ONTOLOGY = _KB / "ontology.yaml"
_DIMENSIONS = _KB / "ontology_dimension_registry.yaml"
_MASTER_INDEX = _CONFIG / "registries" / "classification_master_index.yaml"
_ACTIVATION_PACK_DIR = _KB / "activation_packs"


class OntologyDiagnosticsService:
    """Build admin-facing ontology coverage and consistency reports."""

    def __init__(
        self,
        ontology_path: Path | None = None,
        dimension_path: Path | None = None,
        master_index_path: Path | None = None,
        activation_pack_dir: Path | None = None,
    ) -> None:
        self.ontology_path = Path(ontology_path or _ONTOLOGY)
        self.dimension_path = Path(dimension_path or _DIMENSIONS)
        self.master_index_path = Path(master_index_path or _MASTER_INDEX)
        self.activation_pack_dir = Path(activation_pack_dir or _ACTIVATION_PACK_DIR)

    def build_report(self) -> Dict[str, Any]:
        ontology = self._load_yaml(self.ontology_path)
        dimensions_data = self._load_yaml(self.dimension_path)
        master = self._load_yaml(self.master_index_path)
        frameworks = ontology.get("ontology_frameworks") or {}
        dimensions = dimensions_data.get("ontology_dimensions") or {}
        axis_mappings = master.get("axis_mappings") or {}
        project_type_to_framework = (
            axis_mappings.get("project_type_to_framework") or {}
        ).get("mappings") or {}
        spatial_layer_to_dimensions = (
            axis_mappings.get("spatial_layer_to_dimensions") or {}
        ).get("mappings") or {}

        framework_ids = set(frameworks.keys())
        dimension_ids = set(dimensions.keys())
        activation_pack_refs = self._activation_pack_refs(project_type_to_framework)
        asset_index = KnowledgeAssetRegistry().load_index()
        dimension_index = asset_index.get("dimension_index") or {}
        approved_cards = asset_index.get("cards") or {}

        frameworks_report = self._frameworks_report(
            frameworks=frameworks,
            project_type_to_framework=project_type_to_framework,
            activation_pack_refs=activation_pack_refs,
        )
        dimensions_report = self._dimensions_report(
            dimensions=dimensions,
            spatial_layer_to_dimensions=spatial_layer_to_dimensions,
            activation_pack_refs=activation_pack_refs,
            dimension_index=dimension_index,
            approved_cards=approved_cards,
        )

        referenced_frameworks = set(project_type_to_framework.values())
        referenced_dimensions = self._referenced_dimension_ids(spatial_layer_to_dimensions, activation_pack_refs)
        issues = {
            "missing_project_type_framework_mappings": sorted(
                type_id for type_id in PROJECT_TYPE_REGISTRY if type_id not in project_type_to_framework
            ),
            "unknown_framework_refs": sorted(
                framework_id for framework_id in referenced_frameworks if framework_id not in framework_ids
            ),
            "unknown_dimension_refs": sorted(
                dimension_id for dimension_id in referenced_dimensions if dimension_id not in dimension_ids
            ),
            "unused_frameworks": sorted(
                framework_id
                for framework_id in framework_ids - referenced_frameworks
                if framework_id != "meta_framework"
            ),
            "dimensions_without_approved_cards": sorted(
                dimension_id
                for dimension_id in dimension_ids
                if not self._approved_card_ids(dimension_index.get(dimension_id, []), approved_cards)
            ),
        }
        blocking_issue_count = sum(
            len(issues[key])
            for key in (
                "missing_project_type_framework_mappings",
                "unknown_framework_refs",
                "unknown_dimension_refs",
            )
        )
        warning_issue_count = len(issues["unused_frameworks"]) + len(issues["dimensions_without_approved_cards"])

        return {
            "schema_version": "ontology_diagnostics.v1",
            "status": "ok" if blocking_issue_count == 0 else "needs_attention",
            "summary": {
                "framework_count": len(frameworks),
                "dimension_count": len(dimensions),
                "project_type_framework_mapping_count": len(project_type_to_framework),
                "spatial_layer_dimension_mapping_count": len(spatial_layer_to_dimensions),
                "activation_pack_count": len(activation_pack_refs["packs"]),
                "approved_card_dimension_count": len(
                    {
                        dimension_id
                        for dimension_id in dimensions
                        if self._approved_card_ids(dimension_index.get(dimension_id, []), approved_cards)
                    }
                ),
                "blocking_issue_count": blocking_issue_count,
                "warning_issue_count": warning_issue_count,
            },
            "frameworks": frameworks_report,
            "dimensions": dimensions_report,
            "mappings": {
                "project_type_to_framework": project_type_to_framework,
                "spatial_layer_to_dimensions": spatial_layer_to_dimensions,
            },
            "issues": issues,
        }

    def _frameworks_report(
        self,
        frameworks: Dict[str, Any],
        project_type_to_framework: Dict[str, str],
        activation_pack_refs: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        project_types_by_framework: Dict[str, List[str]] = {}
        for project_type, framework_id in project_type_to_framework.items():
            project_types_by_framework.setdefault(str(framework_id), []).append(str(project_type))

        activation_by_framework = activation_pack_refs["framework_to_packs"]
        result = []
        for framework_id, framework in sorted(frameworks.items()):
            category_ids = [key for key, value in (framework or {}).items() if isinstance(value, list)]
            result.append(
                {
                    "framework_id": framework_id,
                    "category_ids": category_ids,
                    "dimension_count": sum(len(framework.get(category_id) or []) for category_id in category_ids),
                    "project_type_ids": sorted(project_types_by_framework.get(framework_id, [])),
                    "project_type_count": len(project_types_by_framework.get(framework_id, [])),
                    "activation_pack_ids": sorted(activation_by_framework.get(framework_id, set())),
                    "activation_pack_count": len(activation_by_framework.get(framework_id, set())),
                }
            )
        return result

    def _dimensions_report(
        self,
        dimensions: Dict[str, Any],
        spatial_layer_to_dimensions: Dict[str, Any],
        activation_pack_refs: Dict[str, Any],
        dimension_index: Dict[str, Any],
        approved_cards: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        spatial_layers_by_dimension: Dict[str, Set[str]] = {}
        priority_layers_by_dimension: Dict[str, Set[str]] = {}
        for layer_id, mapping in spatial_layer_to_dimensions.items():
            for dimension_id in self._as_list(mapping.get("active_dimensions")):
                spatial_layers_by_dimension.setdefault(dimension_id, set()).add(str(layer_id))
            for dimension_id in self._as_list(mapping.get("priority_dimensions")):
                priority_layers_by_dimension.setdefault(dimension_id, set()).add(str(layer_id))

        result = []
        packs_by_dimension = activation_pack_refs["dimension_to_packs"]
        for dimension_id, dimension in sorted(dimensions.items()):
            card_ids = self._approved_card_ids(dimension_index.get(dimension_id, []), approved_cards)
            result.append(
                {
                    "dimension_id": dimension_id,
                    "code": dimension.get("code"),
                    "name_cn": dimension.get("name_cn"),
                    "name_en": dimension.get("name_en"),
                    "status": dimension.get("status"),
                    "spatial_layer_ids": sorted(spatial_layers_by_dimension.get(dimension_id, set())),
                    "priority_spatial_layer_ids": sorted(priority_layers_by_dimension.get(dimension_id, set())),
                    "activation_pack_ids": sorted(packs_by_dimension.get(dimension_id, set())),
                    "approved_card_ids": card_ids,
                    "approved_card_count": len(card_ids),
                }
            )
        return result

    def _activation_pack_refs(self, project_type_to_framework: Dict[str, str]) -> Dict[str, Any]:
        packs: List[Dict[str, Any]] = []
        framework_to_packs: Dict[str, Set[str]] = {}
        dimension_to_packs: Dict[str, Set[str]] = {}
        if not self.activation_pack_dir.exists():
            return {"packs": packs, "framework_to_packs": framework_to_packs, "dimension_to_packs": dimension_to_packs}

        for path in sorted(self.activation_pack_dir.glob("*_pack.yaml")):
            pack = self._load_yaml(path)
            pack_id = str(pack.get("pack_id") or path.stem)
            routing = pack.get("routing_binding") or {}
            parent_type = str(routing.get("parent_project_type_id") or "")
            framework_id = project_type_to_framework.get(parent_type, parent_type)
            domain_framework = pack.get("domain_framework") or {}
            dimension_ids = self._unique_strings(
                self._as_list(domain_framework.get("required_dimensions"))
                + self._as_list(domain_framework.get("recommended_dimensions"))
            )
            packs.append(
                {
                    "pack_id": pack_id,
                    "parent_project_type_id": parent_type,
                    "ontology_framework_id": framework_id,
                    "dimension_ids": dimension_ids,
                }
            )
            if framework_id:
                framework_to_packs.setdefault(framework_id, set()).add(pack_id)
            for dimension_id in dimension_ids:
                dimension_to_packs.setdefault(dimension_id, set()).add(pack_id)
        return {"packs": packs, "framework_to_packs": framework_to_packs, "dimension_to_packs": dimension_to_packs}

    def _referenced_dimension_ids(
        self,
        spatial_layer_to_dimensions: Dict[str, Any],
        activation_pack_refs: Dict[str, Any],
    ) -> Set[str]:
        result: Set[str] = set()
        for mapping in spatial_layer_to_dimensions.values():
            result.update(self._as_list(mapping.get("active_dimensions")))
            result.update(self._as_list(mapping.get("priority_dimensions")))
        result.update(activation_pack_refs["dimension_to_packs"].keys())
        return {str(item) for item in result if item}

    @staticmethod
    def _approved_card_ids(card_ids: Iterable[Any], approved_cards: Dict[str, Any]) -> List[str]:
        return sorted(
            {
                str(card_id)
                for card_id in card_ids or []
                if (approved_cards.get(str(card_id)) or {}).get("status") == "approved"
            }
        )

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

    @staticmethod
    def _as_list(value: Any) -> List[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]

    @staticmethod
    def _load_yaml(path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
