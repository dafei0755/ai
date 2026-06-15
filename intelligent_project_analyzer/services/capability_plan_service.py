"""Build v3.3 runtime capability plans for Scheme Advisor."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List

import yaml


_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_REGISTRY_PATH = _ROOT / "config" / "registries" / "capability_registry.yaml"


class CapabilityPlanService:
    """Compile runtime capability guardrails from a context_packet."""

    _REQUIRED_GROUPS = [
        "Understanding",
        "Retrieval",
        "Reasoning",
        "Translation",
        "Generation",
        "MemoryGovernance",
    ]

    _NODE_SPECS = {
        "Understanding": {
            "name": "理解力",
            "primary_principle": "先定位",
            "guardrail_principles": ["防定位上瘾", "低置信时保留澄清入口"],
            "failure_modes": ["把空间类型当成唯一答案", "忽略复合场景中的主次关系"],
            "external_search_allowed": False,
        },
        "Retrieval": {
            "name": "检索力",
            "primary_principle": "信息不全不硬猜",
            "guardrail_principles": ["证据不足不当定论", "只调用治理后的知识包和知识卡"],
            "failure_modes": ["把弱证据说成规律", "把项目事实上升为通用知识"],
            "external_search_allowed": False,
        },
        "Reasoning": {
            "name": "推理力",
            "primary_principle": "排头号风险",
            "guardrail_principles": ["分层判断", "主诉求必须经过风险审查"],
            "failure_modes": ["只讲概念不处理约束", "忽略工程和运营前置条件"],
            "external_search_allowed": False,
        },
        "Translation": {
            "name": "转译力",
            "primary_principle": "源不搬表面，必须解码不变量",
            "guardrail_principles": ["防符号滑坡", "把文化和品牌先转成空间关系"],
            "failure_modes": ["符号堆砌", "把风格词直接当设计策略"],
            "external_search_allowed": False,
        },
        "Generation": {
            "name": "生成力",
            "primary_principle": "结论封顶",
            "guardrail_principles": ["追问克制", "指出风险必须给路径"],
            "failure_modes": ["在硬约束缺失时输出确定结论", "越过成熟度生成落地承诺"],
            "external_search_allowed": False,
        },
        "MemoryGovernance": {
            "name": "沉淀力",
            "primary_principle": "顺手记账",
            "guardrail_principles": ["宁可窄，不错误上提", "候选知识必须经过审核"],
            "failure_modes": ["把一次项目答案直接沉淀为通用知识", "缺证据链入库"],
            "external_search_allowed": False,
        },
    }

    def __init__(self, registry_path: Path | str | None = None) -> None:
        self.registry_path = Path(registry_path) if registry_path else _DEFAULT_REGISTRY_PATH
        self._node_specs, self._registry_meta = self._load_registry()

    def build(
        self,
        *,
        context_packet: Dict[str, Any],
        knowledge_context: Dict[str, Any] | None = None,
        ontology_focus: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        packet = context_packet or {}
        knowledge = knowledge_context or {}
        ontology = ontology_focus or {}

        output_mode = packet.get("output_mode") or {}
        discipline_switch = packet.get("discipline_switch") or {}
        missing_slots = self._as_list(packet.get("missing_slots"))
        hard_blockers = self._hard_blocking_slots(missing_slots)
        coverage_ceiling = (
            knowledge.get("coverage_ceiling")
            or (packet.get("knowledge_binding") or {}).get("coverage_ceiling")
            or {}
        )
        knowledge_blocked = bool(coverage_ceiling.get("must_not_claim_specialist_coverage"))
        status = "degraded" if hard_blockers or knowledge_blocked else "active"
        maturity_ceiling = self._resolve_maturity_ceiling(
            output_mode=output_mode,
            hard_blockers=hard_blockers,
            coverage_ceiling=coverage_ceiling,
        )

        nodes = [
            self._understanding_node(packet, status),
            self._retrieval_node(knowledge, coverage_ceiling),
            self._reasoning_node(ontology, packet, status),
            self._translation_node(ontology, packet, status),
            self._generation_node(output_mode, discipline_switch, hard_blockers, status, coverage_ceiling),
            self._memory_node(knowledge, hard_blockers),
        ]

        return {
            "schema_version": "capability_plan.v1",
            "source": "context_packet",
            "registry": self._registry_meta,
            "status": status,
            "maturity_ceiling": maturity_ceiling,
            "knowledge_coverage": coverage_ceiling,
            "output_mode": output_mode.get("primary_output_mode"),
            "required_disciplines": discipline_switch.get("required_disciplines") or [],
            "discipline_coverage": discipline_switch.get("current_coverage"),
            "capability_nodes": nodes,
            "understand": nodes[0]["inputs"],
            "retrieve": knowledge.get("knowledge_packages") or [],
            "reason": ontology.get("key_tensions") or [],
            "generate": nodes[4]["outputs"],
            "sediment": nodes[5]["outputs"],
        }

    def _understanding_node(self, packet: Dict[str, Any], status: str) -> Dict[str, Any]:
        classification = packet.get("classification") or {}
        confidence_score = self._confidence_score(classification.get("confidence"))
        is_low_confidence = confidence_score < 0.55 or not classification.get("project_type_id")
        inputs = [
            classification.get("project_type_id") or "space_type",
            (classification.get("subdomain") or {}).get("primary_subdomain_id") or "subdomain",
        ]
        return self._node(
            "Understanding",
            status="active",
            inputs=self._unique(inputs),
            outputs=["classified_context", "confidence_status"],
            input_schema={"context_packet.classification": "object"},
            output_schema={"project_type_id": "string", "confidence": "object"},
            maturity_ceiling_rule="low confidence keeps clarification active" if is_low_confidence else "",
        )

    def _retrieval_node(self, knowledge: Dict[str, Any], coverage_ceiling: Dict[str, Any]) -> Dict[str, Any]:
        cards = self._as_list(knowledge.get("approved_knowledge_cards"))
        evidence_levels = self._unique(card.get("evidence_level") for card in cards if isinstance(card, dict))
        knowledge_blocked = bool(coverage_ceiling.get("must_not_claim_specialist_coverage"))
        return self._node(
            "Retrieval",
            status="degraded" if knowledge_blocked or not (cards or knowledge.get("knowledge_packages")) else "active",
            inputs=knowledge.get("knowledge_packages") or [],
            outputs=[card.get("card_id") for card in cards if isinstance(card, dict) and card.get("card_id")],
            input_schema={"knowledge_packages": "string[]", "approved_knowledge_cards": "object[]"},
            output_schema={"approved_card_ids": "string[]", "limitations": "string[]"},
            evidence_requirement="approved_cards_or_declared_limitations",
            evidence_summary={
                "approved_card_count": len(cards),
                "evidence_levels": evidence_levels,
                "coverage_level": coverage_ceiling.get("coverage_level"),
            },
            blocking_reasons=["knowledge_coverage_ceiling"] if knowledge_blocked else [],
        )

    def _reasoning_node(
        self,
        ontology: Dict[str, Any],
        packet: Dict[str, Any],
        status: str,
    ) -> Dict[str, Any]:
        return self._node(
            "Reasoning",
            status=status,
            inputs=(ontology.get("key_tensions") or []) + (ontology.get("activated_constraints") or []),
            outputs=["priority_risks", "tradeoff_sequence"],
            input_schema={"ontology_focus.key_tensions": "string[]", "context_packet.missing_slots": "object[]"},
            output_schema={"tradeoffs": "string[]", "risk_order": "string[]"},
            conflict_precedence=["life_safety", "structure", "operations", "experience", "style"],
            maturity_ceiling_rule="hard constraints must be handled before final reasoning",
        )

    def _translation_node(
        self,
        ontology: Dict[str, Any],
        packet: Dict[str, Any],
        status: str,
    ) -> Dict[str, Any]:
        context_vector = packet.get("context_vector") or {}
        return self._node(
            "Translation",
            status=status,
            inputs=self._unique(
                (ontology.get("activated_objects") or [])
                + (ontology.get("activated_relations") or [])
                + list(context_vector.values())
            ),
            outputs=["space_relationships", "concept_to_operation_mapping"],
            input_schema={"ontology_focus": "object", "context_vector": "object"},
            output_schema={"translated_spatial_principles": "string[]"},
            maturity_ceiling_rule="symbolic claims need spatial invariant translation",
        )

    def _generation_node(
        self,
        output_mode: Dict[str, Any],
        discipline_switch: Dict[str, Any],
        hard_blockers: List[str],
        status: str,
        coverage_ceiling: Dict[str, Any],
    ) -> Dict[str, Any]:
        knowledge_blocked = bool(coverage_ceiling.get("must_not_claim_specialist_coverage"))
        maturity_rule = ""
        if hard_blockers:
            maturity_rule = "P1/P2 missing slots cap output certainty"
        elif knowledge_blocked:
            maturity_rule = "knowledge coverage gap caps output to strategy framework"
        return self._node(
            "Generation",
            status=status,
            inputs=[
                output_mode.get("primary_output_mode") or "design_framework",
                discipline_switch.get("current_coverage") or "partial",
            ],
            outputs=["设计任务书目录", "版本深度建议", "正式阶段资料校准清单"],
            input_schema={"output_mode.primary_output_mode": "string", "discipline_switch": "object"},
            output_schema={
                "primary_output_mode": output_mode.get("primary_output_mode"),
                "user_visible_container": output_mode.get("user_visible_container"),
            },
            maturity_ceiling_rule=maturity_rule,
            blocking_missing_slots=hard_blockers,
            blocking_reasons=["knowledge_coverage_ceiling"] if knowledge_blocked else [],
        )

    def _memory_node(self, knowledge: Dict[str, Any], hard_blockers: List[str]) -> Dict[str, Any]:
        return self._node(
            "MemoryGovernance",
            status="degraded" if hard_blockers else "active",
            inputs=knowledge.get("knowledge_packages") or [],
            outputs=["入口判断", "取舍答案", "知识缺口"],
            input_schema={"runtime_findings": "object[]", "evidence_map": "object"},
            output_schema={"candidate_cards": "object[]", "ledger_entries": "object[]"},
            evidence_requirement="evidence_chain_required_before_promotion",
            maturity_ceiling_rule="missing hard facts can only create project notes, not reusable knowledge",
            logging_policy="candidate_card_only; no_direct_knowledge_base_update",
        )

    def _node(
        self,
        group: str,
        *,
        status: str,
        inputs: Iterable[Any],
        outputs: Iterable[Any],
        input_schema: Dict[str, Any],
        output_schema: Dict[str, Any],
        primary_principle: str | None = None,
        guardrail_principles: List[str] | None = None,
        failure_modes: List[str] | None = None,
        conflict_precedence: List[str] | None = None,
        maturity_ceiling_rule: str = "",
        evidence_requirement: str = "",
        evidence_summary: Dict[str, Any] | None = None,
        external_search_allowed: bool | None = None,
        logging_policy: str = "runtime_trace",
        blocking_missing_slots: List[str] | None = None,
        blocking_reasons: List[str] | None = None,
    ) -> Dict[str, Any]:
        spec = self._node_specs[group]
        return {
            "capability_group": group,
            "name": spec["name"],
            "status": status,
            "inputs": self._unique(inputs),
            "outputs": self._unique(outputs),
            "input_schema": input_schema,
            "output_schema": output_schema,
            "primary_principle": primary_principle or spec["primary_principle"],
            "guardrail_principles": guardrail_principles or spec["guardrail_principles"],
            "failure_modes": failure_modes or spec["failure_modes"],
            "conflict_precedence": conflict_precedence or [],
            "maturity_ceiling_rule": maturity_ceiling_rule,
            "evidence_requirement": evidence_requirement,
            "evidence_summary": evidence_summary or {},
            "external_search_allowed": (
                spec["external_search_allowed"] if external_search_allowed is None else external_search_allowed
            ),
            "logging_policy": logging_policy,
            "blocking_missing_slots": blocking_missing_slots or [],
            "blocking_reasons": blocking_reasons or [],
        }

    @staticmethod
    def _resolve_maturity_ceiling(
        *,
        output_mode: Dict[str, Any],
        hard_blockers: List[str],
        coverage_ceiling: Dict[str, Any],
    ) -> str:
        candidate = output_mode.get("primary_output_mode") or "design_framework"
        if hard_blockers:
            candidate = "conditional_framework"
        knowledge_ceiling = coverage_ceiling.get("ceiling_level")
        if not knowledge_ceiling:
            return candidate
        order = {
            "full_specialist": 0,
            "design_framework": 1,
            "conditional_framework": 2,
            "strategy_framework": 3,
        }
        if order.get(str(knowledge_ceiling), 0) > order.get(str(candidate), 0):
            return str(knowledge_ceiling)
        return str(candidate)

    def _load_registry(self) -> tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
        specs = deepcopy(self._NODE_SPECS)
        meta = {
            "schema_version": "capability_registry.internal_default",
            "status": "ok",
            "path": str(self.registry_path),
            "issues": [],
        }
        if not self.registry_path.exists():
            meta["status"] = "fallback"
            meta["issues"].append({
                "code": "capability_registry_file_missing",
                "message": f"Capability registry not found: {self.registry_path}",
            })
            return specs, meta

        try:
            with self.registry_path.open("r", encoding="utf-8") as f:
                registry = yaml.safe_load(f) or {}
        except Exception as exc:
            meta["status"] = "fallback"
            meta["issues"].append({
                "code": "capability_registry_load_failed",
                "message": f"{type(exc).__name__}: {exc}",
            })
            return specs, meta

        meta["schema_version"] = str(registry.get("schema_version") or "capability_registry.unknown")
        capabilities = registry.get("capabilities") or {}
        if not isinstance(capabilities, dict):
            meta["status"] = "fallback"
            meta["issues"].append({
                "code": "capability_registry_capabilities_invalid",
                "message": "capabilities must be an object",
            })
            return specs, meta

        missing_groups = [group for group in self._REQUIRED_GROUPS if group not in capabilities]
        if missing_groups:
            meta["status"] = "needs_attention"
            meta["issues"].append({
                "code": "missing_capability_groups",
                "message": ", ".join(missing_groups),
            })

        for group in self._REQUIRED_GROUPS:
            override = capabilities.get(group)
            if not isinstance(override, dict):
                continue
            specs[group] = {
                **specs[group],
                **{
                    key: override[key]
                    for key in (
                        "name",
                        "primary_principle",
                        "guardrail_principles",
                        "failure_modes",
                        "external_search_allowed",
                    )
                    if key in override
                },
            }

        if not meta["issues"]:
            meta["status"] = "ok"
        return specs, meta

    @staticmethod
    def _hard_blocking_slots(missing_slots: List[Any]) -> List[str]:
        blockers: List[str] = []
        for slot in missing_slots:
            if not isinstance(slot, dict):
                continue
            if slot.get("priority") in {"P1", "P2"}:
                name = slot.get("name")
                if name:
                    blockers.append(str(name))
        return CapabilityPlanService._unique(blockers)

    @staticmethod
    def _as_list(value: Any) -> List[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, tuple):
            return list(value)
        if isinstance(value, set):
            return list(value)
        return [value]

    @staticmethod
    def _confidence_score(value: Any) -> float:
        if isinstance(value, dict):
            value = value.get("score")
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _unique(values: Iterable[Any]) -> List[str]:
        result: List[str] = []
        seen = set()
        for value in values:
            if value in (None, ""):
                continue
            item = str(value)
            if item not in seen:
                seen.add(item)
                result.append(item)
        return result
