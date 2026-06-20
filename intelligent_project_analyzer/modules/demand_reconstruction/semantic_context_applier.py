"""Apply LLM semantic understanding to demand reconstruction context."""

from __future__ import annotations

from typing import Any, Dict, Optional

from intelligent_project_analyzer.services.demand_reconstruction_context_adapter import (
    DemandReconstructionContextAdapter,
)


class DemandReconstructionSemanticContextApplier:
    """Promote LLM semantic-router output into adapter context and scan metadata."""

    def __init__(self, *, target_aliases: Dict[str, str]) -> None:
        self._target_aliases = dict(target_aliases or {})

    def apply(
        self,
        adapter_context: Dict[str, Any],
        package: Dict[str, Any],
    ) -> None:
        """Let Stage 1 LLM understanding drive the Stage 2 rule scanner."""
        adapter_context["llm_semantic_understanding"] = package
        llm_candidates = self.llm_semantic_candidates(package)
        fragment_targets = self.llm_semantic_fragment_targets(package)
        scan_result = self.llm_semantic_scan_result(package, llm_candidates)
        adapter_context["llm_semantic_scan"] = scan_result
        if fragment_targets:
            adapter_context["llm_semantic_fragment_targets"] = fragment_targets
        self.refresh_asset_scan(adapter_context, fragment_targets=fragment_targets)
        self.apply_governance_context(adapter_context, package, scan_result)
        context_source = dict(adapter_context.get("context_source") or {})
        context_source["llm_semantic_router"] = True
        context_source["llm_semantic_scan_result"] = scan_result["result"]
        if fragment_targets:
            context_source["llm_semantic_fragment_targets"] = True
        adapter_context["context_source"] = context_source
        if scan_result["result"] == "no_match":
            merged = self.merge_llm_and_rule_candidates(
                [self.llm_no_match_candidate(package)],
                adapter_context.get("semantic_candidate_set") or [],
            )
            adapter_context["semantic_candidate_set"] = merged
            adapter_context["archetype"] = DemandReconstructionContextAdapter._archetype_from_candidates(merged)
            return
        if not llm_candidates:
            return
        merged = self.merge_llm_and_rule_candidates(
            llm_candidates,
            adapter_context.get("semantic_candidate_set") or [],
        )
        adapter_context["semantic_candidate_set"] = merged
        adapter_context["archetype"] = DemandReconstructionContextAdapter._archetype_from_candidates(merged)

    @staticmethod
    def refresh_asset_scan(
        adapter_context: Dict[str, Any],
        *,
        fragment_targets: Optional[list[Dict[str, Any]]] = None,
    ) -> None:
        scan = adapter_context.get("llm_semantic_scan")
        if not isinstance(scan, dict):
            return
        asset_scan: Dict[str, Any] = {}
        targets = fragment_targets
        if targets is None:
            targets = adapter_context.get("llm_semantic_fragment_targets") or []
        rule_fragments = []
        for target in targets or []:
            if not isinstance(target, dict):
                continue
            item = {
                key: target.get(key)
                for key in ("group_id", "fragment_id", "confidence", "source")
                if target.get(key) not in (None, "", [], {})
            }
            evidence = [str(value) for value in (target.get("evidence") or []) if str(value)][:3]
            if evidence:
                item["evidence"] = evidence
            if item:
                rule_fragments.append(item)
        if rule_fragments:
            asset_scan["rule_fragments"] = rule_fragments[:5]

        axes = adapter_context.get("semantic_axes")
        if isinstance(axes, dict) and axes:
            asset_scan["semantic_axes"] = {
                "axis_ids": [str(key) for key in axes.keys() if str(key)][:8],
            }

        tensions = []
        for tension in adapter_context.get("main_tensions") or []:
            if isinstance(tension, dict) and tension.get("title"):
                tensions.append(str(tension.get("title")))
            if len(tensions) >= 5:
                break
        if tensions:
            asset_scan["main_tensions"] = {
                "count": len(adapter_context.get("main_tensions") or []),
                "titles": tensions,
            }

        coverage = adapter_context.get("knowledge_coverage_ceiling")
        if isinstance(coverage, dict) and coverage:
            asset_scan["knowledge_coverage"] = {
                key: coverage.get(key)
                for key in ("level", "coverage_level", "ceiling_level", "source")
                if coverage.get(key) not in (None, "", [], {})
            }

        approved_assets = []
        for asset in adapter_context.get("governed_knowledge_assets") or []:
            if not isinstance(asset, dict):
                continue
            approved_assets.append(
                {
                    key: asset.get(key)
                    for key in ("card_id", "title", "project_type", "evidence_level", "match_metadata")
                    if asset.get(key) not in (None, "", [], {})
                }
            )
            if len(approved_assets) >= 3:
                break
        if approved_assets:
            asset_scan["approved_knowledge_assets"] = approved_assets

        if asset_scan:
            scan["asset_scan"] = asset_scan
            adapter_context["llm_semantic_scan"] = scan

    def apply_governance_context(
        self,
        adapter_context: Dict[str, Any],
        package: Dict[str, Any],
        scan_result: Dict[str, Any],
    ) -> None:
        result = str(scan_result.get("result") or "")
        if result not in {"no_match", "partial_match"}:
            return
        classification = dict(adapter_context.get("classification") or {})
        evidence = self.llm_semantic_package_evidence(package)
        project_object = str(package.get("project_object") or "").strip() or "未覆盖空间项目"
        classification["coverage_gap"] = True
        classification["knowledge_gap"] = True
        classification["knowledge_gap_ticket"] = {
            "gap_type": "llm_semantic_no_match" if result == "no_match" else "llm_semantic_partial_match",
            "project_type": project_object,
            "summary": f"LLM Semantic Router 判断“{project_object}”缺少稳定专科规则/知识覆盖。",
            "source": "llm_semantic_router",
            "evidence": evidence,
            "scan_result": result,
            "matched_targets": list(scan_result.get("matched_targets") or []),
            "package_ids": self.llm_semantic_taxonomy_ids(package, "package_ids", "knowledge_package_ids"),
            "ontology_dimension_ids": self.llm_semantic_taxonomy_ids(
                package,
                "ontology_dimension_ids",
                "dimension_ids",
                "semantic_dimension_ids",
            ),
        }
        if result == "no_match":
            classification["new_fragment_candidate"] = {
                "fragment_id": self.candidate_fragment_id(project_object),
                "project_object": project_object,
                "summary": f"评估是否需要为“{project_object}”沉淀新的需求重构规则碎片。",
                "source": "llm_semantic_router",
                "evidence": evidence,
                "scan_result": result,
            }
        adapter_context["knowledge_coverage_ceiling"] = self.llm_semantic_coverage_ceiling(
            scan_result=result,
            project_object=project_object,
            evidence=evidence,
            matched_targets=list(scan_result.get("matched_targets") or []),
        )
        adapter_context["classification"] = classification

    @staticmethod
    def llm_semantic_coverage_ceiling(
        *,
        scan_result: str,
        project_object: str,
        evidence: list[str],
        matched_targets: list[str],
    ) -> Dict[str, Any]:
        if scan_result == "partial_match":
            return {
                "level": "partial_specialist",
                "coverage_level": "partial_specialist",
                "ceiling_level": "l1_neighbor_transfer",
                "source": "llm_semantic_router",
                "must_not_claim_specialist_coverage": True,
                "matched_targets": matched_targets,
                "evidence": evidence,
                "reasons": [
                    "LLM Semantic Router 判断当前需求只部分命中稳定规则碎片。",
                    "可使用命中的邻近规则做结构约束，但不能冒充完整专科覆盖。",
                ],
                "allowed_outputs": ["邻近迁移判断", "关键未知边界", "需要补充的专科问题"],
                "forbidden_outputs": ["完整专科结论", "施工级建议", "题面无支撑的专名或案例"],
                "user_visible_note": f"“{project_object}”只部分命中现有规则蓝图，需要按邻近迁移处理并标注边界。",
            }
        return {
            "level": "general_method_only",
            "coverage_level": "general_method_only",
            "ceiling_level": "l0_general",
            "source": "llm_semantic_router",
            "must_not_claim_specialist_coverage": True,
            "matched_targets": matched_targets,
            "evidence": evidence,
            "reasons": [
                "LLM Semantic Router 判断当前需求没有可靠命中稳定规则碎片。",
                "只能做通用方法论重构，不能伪造专科规则覆盖。",
            ],
            "allowed_outputs": ["通用第一性推理", "成立条件", "知识缺口与下一步追问"],
            "forbidden_outputs": ["套用相近模板", "完整专科结论", "施工级建议"],
            "user_visible_note": f"“{project_object}”未命中稳定规则蓝图，只能按通用方法论先收束判断。",
        }

    @classmethod
    def llm_semantic_taxonomy_ids(cls, package: Dict[str, Any], *keys: str) -> list[str]:
        values: list[str] = []
        for key in keys:
            raw_values = package.get(key) if isinstance(package, dict) else None
            if not isinstance(raw_values, list):
                continue
            for value in raw_values:
                text = str(value or "").strip()
                if text:
                    values.append(text)
        return cls.dedupe_strings(values)

    @staticmethod
    def candidate_fragment_id(project_object: str) -> str:
        normalized = str(project_object or "").strip().lower()
        ascii_slug = "".join(char if char.isalnum() and ord(char) < 128 else "_" for char in normalized)
        ascii_slug = "_".join(part for part in ascii_slug.split("_") if part)
        return ascii_slug or "llm_semantic_new_fragment"

    @classmethod
    def llm_semantic_package_evidence(cls, package: Dict[str, Any]) -> list[str]:
        evidence: list[str] = []
        for item in package.get("space_candidates") or []:
            if isinstance(item, dict):
                evidence.extend(cls.take_evidence(item.get("evidence")))
        for item in package.get("core_tensions") or []:
            if isinstance(item, dict):
                evidence.extend(cls.take_evidence(item.get("evidence")))
        return cls.dedupe_strings(evidence)

    def llm_semantic_candidates(self, package: Dict[str, Any]) -> list[Dict[str, Any]]:
        recommended = [
            normalized
            for value in (package.get("recommended_scan_targets") or [])
            if (normalized := self.normalize_llm_semantic_target(value))
        ]
        recommended_order = {candidate_id: index for index, candidate_id in enumerate(recommended)}
        candidates_by_id: Dict[str, Dict[str, Any]] = {}
        for index, item in enumerate(package.get("space_candidates") or []):
            if not isinstance(item, dict):
                continue
            candidate_id = self.normalize_llm_semantic_target(item.get("label"))
            if not candidate_id:
                continue
            evidence = self.take_evidence(item.get("evidence"))
            if not evidence:
                continue
            confidence = self.safe_confidence(item.get("confidence"))
            if confidence < 0.5:
                continue
            score = 120 + int(confidence * 30)
            if candidate_id in recommended_order:
                score += max(0, 10 - recommended_order[candidate_id])
            score -= index
            existing = candidates_by_id.get(candidate_id)
            if existing and int(existing.get("score") or 0) >= score:
                existing["evidence"] = self.dedupe_strings(list(existing.get("evidence") or []) + evidence)
                existing["confidence"] = max(float(existing.get("confidence") or 0), confidence)
                continue
            candidates_by_id[candidate_id] = {
                "id": candidate_id,
                "score": score,
                "role": "secondary",
                "evidence": evidence,
                "counter_evidence": [],
                "routing_target": "demand_reconstruction",
                "source": "llm_semantic_router",
                "confidence": confidence,
            }
        return sorted(
            candidates_by_id.values(),
            key=lambda item: (-int(item.get("score") or 0), str(item.get("id") or "")),
        )

    @classmethod
    def llm_semantic_fragment_targets(cls, package: Dict[str, Any]) -> list[Dict[str, Any]]:
        targets: list[Dict[str, Any]] = []
        for item in package.get("recommended_fragment_targets") or []:
            if not isinstance(item, dict):
                continue
            group_id = str(item.get("group_id") or "").strip()
            fragment_id = str(item.get("fragment_id") or "").strip()
            if not group_id or not fragment_id:
                continue
            confidence = cls.safe_confidence(item.get("confidence"))
            if confidence < 0.5:
                continue
            evidence = cls.take_evidence(item.get("evidence"))
            if not evidence:
                continue
            targets.append(
                {
                    "group_id": group_id,
                    "fragment_id": fragment_id,
                    "confidence": confidence,
                    "evidence": evidence,
                    "source": "llm_semantic_router",
                }
            )
        return targets

    @classmethod
    def merge_llm_and_rule_candidates(
        cls,
        llm_candidates: list[Dict[str, Any]],
        rule_candidates: list[Dict[str, Any]],
    ) -> list[Dict[str, Any]]:
        merged_by_id: Dict[str, Dict[str, Any]] = {}
        for candidate in llm_candidates:
            merged_by_id[str(candidate.get("id"))] = dict(candidate)
        for candidate in rule_candidates:
            if not isinstance(candidate, dict) or not candidate.get("id"):
                continue
            candidate_id = str(candidate["id"])
            if candidate_id in merged_by_id:
                merged = merged_by_id[candidate_id]
                merged["score"] = max(int(merged.get("score") or 0), int(candidate.get("score") or 0))
                merged["evidence"] = cls.dedupe_strings(
                    list(merged.get("evidence") or []) + list(candidate.get("evidence") or [])
                )
                merged["counter_evidence"] = cls.dedupe_strings(
                    list(merged.get("counter_evidence") or []) + list(candidate.get("counter_evidence") or [])
                )
            else:
                merged_by_id[candidate_id] = dict(candidate)
        ranked = sorted(
            merged_by_id.values(),
            key=lambda item: (
                0 if item.get("source") == "llm_semantic_router" else 1,
                -int(item.get("score") or 0),
                str(item.get("id") or ""),
            ),
        )
        for index, item in enumerate(ranked):
            if index == 0:
                item["role"] = "primary"
            elif int(item.get("score") or 0) < 50:
                item["role"] = "downweighted"
            else:
                item["role"] = "secondary"
        return ranked

    @classmethod
    def llm_no_match_candidate(cls, package: Dict[str, Any]) -> Dict[str, Any]:
        evidence = []
        for item in package.get("space_candidates") or []:
            if isinstance(item, dict):
                evidence.extend(cls.take_evidence(item.get("evidence")))
        for item in package.get("core_tensions") or []:
            if isinstance(item, dict):
                evidence.extend(cls.take_evidence(item.get("evidence")))
        project_object = str(package.get("project_object") or "").strip()
        if project_object:
            evidence.append(project_object)
        return {
            "id": "general_project",
            "score": 150,
            "role": "primary",
            "evidence": cls.dedupe_strings(evidence) or ["LLM Semantic Router 判断现有规则碎片无可靠命中。"],
            "counter_evidence": [],
            "routing_target": "demand_reconstruction",
            "source": "llm_semantic_router_no_match",
            "confidence": 1.0,
        }

    @classmethod
    def llm_semantic_scan_result(cls, package: Dict[str, Any], candidates: list[Dict[str, Any]]) -> Dict[str, Any]:
        novelty_level = str(package.get("novelty_level") or "").strip() or "unknown"
        matched_targets = [str(item.get("id")) for item in candidates if item.get("id")]
        confidences = [
            cls.safe_confidence(item.get("confidence"))
            for item in candidates
            if item.get("id")
        ]
        max_confidence = round(max(confidences), 4) if confidences else 0.0
        if max_confidence >= 0.75:
            confidence_band = "high"
        elif max_confidence >= 0.5:
            confidence_band = "medium"
        else:
            confidence_band = "low"
        if not matched_targets or novelty_level == "unknown" or confidence_band == "low":
            result = "no_match"
        elif novelty_level == "partial_unknown" or confidence_band == "medium":
            result = "partial_match"
        else:
            result = "strong_match"
        return {
            "result": result,
            "matched_targets": matched_targets,
            "novelty_level": novelty_level,
            "confidence_band": confidence_band,
            "max_confidence": max_confidence,
            "source": "llm_semantic_router",
        }

    def normalize_llm_semantic_target(self, value: Any) -> Optional[str]:
        normalized = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
        return self._target_aliases.get(normalized)

    @staticmethod
    def safe_confidence(value: Any) -> float:
        try:
            confidence = float(value)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(1.0, confidence))

    @classmethod
    def take_evidence(cls, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return cls.dedupe_strings(
            [str(item).strip() for item in value if str(item).strip()]
        )

    @staticmethod
    def dedupe_strings(values: list[str]) -> list[str]:
        result = []
        seen = set()
        for value in values:
            text = str(value or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            result.append(text)
        return result
