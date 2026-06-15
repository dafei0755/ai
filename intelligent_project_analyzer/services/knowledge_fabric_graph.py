"""Lightweight governed knowledge-fabric graph."""

from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import yaml
from loguru import logger

from .knowledge_asset_ingestion import ASSET_ROOT
from .knowledge_asset_registry import KnowledgeAssetRegistry
from .knowledge_fabric_models import KnowledgeFabricEdge, KnowledgeFabricNode
from .knowledge_package_registry import KnowledgePackageRegistry


_ROOT = Path(__file__).resolve().parent.parent
_ACTIVATION_PACK_DIR = _ROOT / "knowledge_base" / "activation_packs"
_ONTOLOGY_PATH = _ROOT / "knowledge_base" / "ontology.yaml"


class KnowledgeFabricGraph:
    """Build and expand a compact graph from governed knowledge sources."""

    def __init__(
        self,
        package_registry: Optional[KnowledgePackageRegistry] = None,
        asset_registry: Optional[KnowledgeAssetRegistry] = None,
        activation_pack_dir: Optional[Path] = None,
        ontology_path: Optional[Path] = None,
    ) -> None:
        self.package_registry = package_registry or KnowledgePackageRegistry()
        self.asset_registry = asset_registry or KnowledgeAssetRegistry(ASSET_ROOT)
        self.activation_pack_dir = Path(activation_pack_dir or _ACTIVATION_PACK_DIR)
        self.ontology_path = Path(ontology_path or _ONTOLOGY_PATH)
        self.nodes: Dict[str, KnowledgeFabricNode] = {}
        self.edges: List[KnowledgeFabricEdge] = []
        self._edge_keys: Set[Tuple[str, str, str]] = set()
        self._built = False

    def build(self) -> "KnowledgeFabricGraph":
        self.nodes = {}
        self.edges = []
        self._edge_keys = set()
        self._add_packages()
        self._add_approved_cards()
        self._add_activation_packs()
        self._add_ontology()
        self._built = True
        return self

    def expand(self, seed_ids: Iterable[str], max_hops: int = 2) -> Dict[str, Any]:
        """Return nodes and edges reachable from seeds within ``max_hops``."""
        if not self._built:
            self.build()

        seeds = [str(seed_id) for seed_id in seed_ids or [] if str(seed_id) in self.nodes]
        if not seeds:
            return {"nodes": [], "edges": []}

        max_hops = max(0, int(max_hops))
        adjacency: Dict[str, List[str]] = {}
        for edge in self.edges:
            adjacency.setdefault(edge.source_id, []).append(edge.target_id)
            adjacency.setdefault(edge.target_id, []).append(edge.source_id)

        distances = {seed: 0 for seed in seeds}
        queue: deque[str] = deque(seeds)
        while queue:
            node_id = queue.popleft()
            distance = distances[node_id]
            if distance >= max_hops:
                continue
            for neighbor_id in adjacency.get(node_id, []):
                if neighbor_id in distances:
                    continue
                distances[neighbor_id] = distance + 1
                queue.append(neighbor_id)

        included = set(distances)
        return {
            "nodes": [self.nodes[node_id].model_dump() for node_id in sorted(included)],
            "edges": [
                edge.model_dump()
                for edge in self.edges
                if edge.source_id in included and edge.target_id in included
            ],
        }

    def _add_node(
        self,
        node_id: str,
        node_type: str,
        title: Optional[str] = None,
        labels: Optional[Iterable[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not node_id:
            return
        node_id = str(node_id)
        if node_id in self.nodes:
            node = self.nodes[node_id]
            if title and not node.title:
                node.title = title
            node.labels = sorted({*node.labels, *[str(label) for label in labels or [] if label]})
            node.metadata.update(metadata or {})
            return
        self.nodes[node_id] = KnowledgeFabricNode(
            id=node_id,
            node_type=node_type,
            title=title,
            labels=[str(label) for label in labels or [] if label],
            metadata=metadata or {},
        )

    def _add_edge(
        self,
        source_id: str,
        target_id: str,
        relation: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not source_id or not target_id:
            return
        key = (str(source_id), str(target_id), str(relation))
        if key in self._edge_keys:
            return
        self._edge_keys.add(key)
        self.edges.append(
            KnowledgeFabricEdge(
                source_id=key[0],
                target_id=key[1],
                relation=key[2],
                metadata=metadata or {},
            )
        )

    def _add_packages(self) -> None:
        for package in self.package_registry.list_packages():
            package_id = str(package.get("package_id") or "")
            self._add_node(
                package_id,
                "knowledge_package",
                title=package.get("title"),
                labels=package.get("search_tags") or [],
                metadata={
                    "project_types": package.get("project_types") or [],
                    "status": package.get("status"),
                    "backend": package.get("backend"),
                    "collection_name": package.get("collection_name"),
                },
            )
            for project_type in package.get("project_types") or []:
                self._add_project_type(str(project_type))
                self._add_edge(package_id, str(project_type), "supports_project_type")

    def _add_approved_cards(self) -> None:
        index = self.asset_registry.load_index()
        for card_id in sorted((index.get("cards") or {}).keys()):
            card = self.asset_registry.get_card(str(card_id))
            if not card:
                continue
            self._add_node(
                str(card.get("card_id") or card_id),
                "approved_knowledge_card",
                title=card.get("title"),
                labels=card.get("species") or [],
                metadata={
                    "knowledge_status": card.get("knowledge_status"),
                    "evidence_level": card.get("evidence_level"),
                    "allowed_use": card.get("allowed_use") or [],
                    "not_allowed_use": card.get("not_allowed_use") or [],
                },
            )
            for package_id in card.get("package_ids") or []:
                self._add_node(str(package_id), "knowledge_package")
                self._add_edge(str(package_id), str(card.get("card_id") or card_id), "has_approved_card")
            for dimension_id in card.get("ontology_dimension_ids") or []:
                self._add_dimension(str(dimension_id))
                self._add_edge(str(card.get("card_id") or card_id), str(dimension_id), "tagged_by_dimension")

    def _add_activation_packs(self) -> None:
        if not self.activation_pack_dir.exists():
            return
        for path in sorted(self.activation_pack_dir.glob("*_pack.yaml")):
            try:
                pack = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except Exception as exc:
                logger.warning(f"[KnowledgeFabricGraph] failed to load activation pack {path}: {exc}")
                continue

            pack_id = str(pack.get("pack_id") or path.stem)
            self._add_node(
                pack_id,
                "activation_pack",
                title=((pack.get("meta") or {}).get("display_name")),
                metadata={
                    "path": str(path),
                    "status": pack.get("status"),
                    "maturity": pack.get("maturity"),
                },
            )
            binding = (
                pack.get("knowledge_recall_profile")
                or pack.get("knowledge_base_binding")
                or pack.get("knowledge_binding")
                or {}
            )
            package_ids = self._unique_strings(
                list(binding.get("package_ids") or []) + list(binding.get("knowledge_packages") or [])
            )
            for package_id in package_ids:
                self._add_node(package_id, "knowledge_package")
                self._add_edge(pack_id, package_id, "recalls_package")

            routing = pack.get("routing_binding") or {}
            parent_type = routing.get("parent_project_type_id")
            subdomain_id = routing.get("subdomain_id")
            if parent_type:
                self._add_project_type(str(parent_type))
                self._add_edge(pack_id, str(parent_type), "routes_from_project_type")
            if subdomain_id:
                self._add_node(str(subdomain_id), "space_subdomain")
                self._add_edge(pack_id, str(subdomain_id), "routes_to_subdomain")

            for dimension_id in self._activation_pack_dimensions(pack):
                self._add_dimension(dimension_id)
                self._add_edge(pack_id, dimension_id, "activates_dimension")

    def _add_ontology(self) -> None:
        if not self.ontology_path.exists():
            return
        try:
            ontology = yaml.safe_load(self.ontology_path.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            logger.warning(f"[KnowledgeFabricGraph] failed to load ontology {self.ontology_path}: {exc}")
            return

        for key, framework in (ontology.get("ontology_framework_v18_examples") or {}).items():
            if not isinstance(framework, dict):
                continue
            framework_id = str(framework.get("parent_framework") or key)
            framework_node_id = self._framework_node_id(framework_id)
            self._add_node(framework_node_id, "ontology_framework", title=framework_id)
            for dimension_id in self._unique_strings(framework.get("ontology_dimension_ids") or []):
                self._add_dimension(dimension_id)
                self._add_edge(framework_node_id, dimension_id, "contains_dimension")

        for framework_id, framework in (ontology.get("ontology_frameworks") or {}).items():
            framework_node_id = self._framework_node_id(str(framework_id))
            self._add_node(framework_node_id, "ontology_framework", title=str(framework_id))
            for dimension_id in self._extract_dimensions(framework):
                self._add_dimension(dimension_id)
                self._add_edge(framework_node_id, dimension_id, "contains_dimension")

    def _add_project_type(self, project_type: str) -> None:
        self._add_node(project_type, "project_type", title=project_type)
        self._add_node(self._framework_node_id(project_type), "ontology_framework", title=project_type)
        self._add_edge(project_type, self._framework_node_id(project_type), "uses_ontology_framework")

    def _add_dimension(self, dimension_id: str) -> None:
        self._add_node(dimension_id, "ontology_dimension", title=dimension_id)

    @staticmethod
    def _framework_node_id(framework_id: str) -> str:
        return f"ontology_framework:{framework_id}"

    def _activation_pack_dimensions(self, pack: Dict[str, Any]) -> List[str]:
        domain_framework = pack.get("domain_framework") or {}
        return self._unique_strings(
            list(domain_framework.get("required_dimensions") or [])
            + list(domain_framework.get("recommended_dimensions") or [])
            + list(pack.get("active_ontology_dimension_ids") or [])
        )

    def _extract_dimensions(self, value: Any) -> List[str]:
        dimensions: List[str] = []
        if isinstance(value, dict):
            dimensions.extend(self._unique_strings(value.get("ontology_dimension_ids") or []))
            issue_id = value.get("issue_id")
            if issue_id:
                dimensions.append(str(issue_id))
            for nested in value.values():
                dimensions.extend(self._extract_dimensions(nested))
        elif isinstance(value, list):
            for item in value:
                dimensions.extend(self._extract_dimensions(item))
        return self._unique_strings(dimensions)

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
