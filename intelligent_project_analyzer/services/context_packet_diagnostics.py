"""Read-only diagnostics for v3.3 context packets."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .capability_plan_service import CapabilityPlanService
from .space_context_packet_service import (
    SpaceContextPacketService,
    SpaceContextPacketValidationError,
    validate_context_packet,
)


class ContextPacketDiagnosticsService:
    """Report context-packet contract and binding health without mutation."""

    def __init__(
        self,
        context_packet_service: Optional[SpaceContextPacketService] = None,
    ) -> None:
        self.context_packet_service = context_packet_service or SpaceContextPacketService()
        self.capability_plan_service = CapabilityPlanService()

    def diagnose(
        self,
        user_input: str,
        structured_requirements: Optional[Dict[str, Any]] = None,
        confirmed_tasks: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Build a context packet and return read-only diagnostic metadata."""
        try:
            context_packet = self.context_packet_service.build(
                user_input=user_input,
                structured_requirements=structured_requirements,
                confirmed_tasks=confirmed_tasks,
            )
        except SpaceContextPacketValidationError as exc:
            return self._build_report(
                context_packet={},
                issues=[
                    {
                        "severity": "blocking",
                        "code": "context_packet_contract_invalid",
                        "message": str(exc),
                    }
                ],
            )
        except Exception as exc:
            return self._build_report(
                context_packet={},
                issues=[
                    {
                        "severity": "blocking",
                        "code": "context_packet_build_failed",
                        "message": f"{type(exc).__name__}: {exc}",
                    }
                ],
            )

        issues: List[Dict[str, str]] = []
        try:
            validate_context_packet(context_packet)
        except SpaceContextPacketValidationError as exc:
            issues.append(
                {
                    "severity": "blocking",
                    "code": "context_packet_contract_invalid",
                    "message": str(exc),
                }
            )

        ontology_binding = context_packet.get("ontology_binding") or {}
        coordination = context_packet.get("activation_pack_coordination") or {}
        loaded_pack_ids = self._as_list(coordination.get("loaded_pack_ids"))
        if not ontology_binding.get("ontology_framework_id") and not loaded_pack_ids:
            issues.append(
                {
                    "severity": "warning",
                    "code": "missing_ontology_framework_and_activation_packs",
                    "message": "No ontology framework or activation packs are loaded for this context packet.",
                }
            )

        knowledge_binding = context_packet.get("knowledge_binding") or {}
        if not self._as_list(knowledge_binding.get("knowledge_package_ids")):
            issues.append(
                {
                    "severity": "warning",
                    "code": "missing_knowledge_package_ids",
                    "message": "No knowledge package ids are bound to this context packet.",
                }
            )

        return self._build_report(context_packet=context_packet, issues=issues)

    def _build_report(
        self,
        context_packet: Dict[str, Any],
        issues: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        ontology_binding = context_packet.get("ontology_binding") or {}
        knowledge_binding = context_packet.get("knowledge_binding") or {}
        coordination = context_packet.get("activation_pack_coordination") or {}
        missing_slots = self._as_list(context_packet.get("missing_slots"))
        capability_plan = self._build_capability_plan(context_packet)
        capability_nodes = self._as_list(capability_plan.get("capability_nodes"))

        blocking_issue_count = sum(1 for issue in issues if issue.get("severity") == "blocking")
        warning_issue_count = sum(1 for issue in issues if issue.get("severity") == "warning")
        contract_status = "ok" if blocking_issue_count == 0 else "error"

        return {
            "schema_version": "context_packet_diagnostic.v1",
            "status": "needs_attention" if blocking_issue_count > 0 else "ok",
            "summary": {
                "missing_slot_count": len(missing_slots),
                "active_missing_slot_count": sum(
                    1 for slot in missing_slots if isinstance(slot, dict) and slot.get("active_for_current_round") is not False
                ),
                "deferred_missing_slot_count": sum(
                    1 for slot in missing_slots if isinstance(slot, dict) and slot.get("active_for_current_round") is False
                ),
                "ontology_dimension_count": len(
                    self._as_list(ontology_binding.get("ontology_dimension_ids"))
                ),
                "knowledge_package_count": len(
                    self._as_list(knowledge_binding.get("knowledge_package_ids"))
                ),
                "loaded_activation_pack_count": len(
                    self._as_list(coordination.get("loaded_pack_ids"))
                ),
                "capability_node_count": len(capability_nodes),
                "blocking_issue_count": blocking_issue_count,
                "warning_issue_count": warning_issue_count,
            },
            "checks": {
                "contract": {"status": contract_status},
                "ontology_binding": {
                    "status": self._binding_status(
                        issues,
                        {"missing_ontology_framework_and_activation_packs"},
                    )
                },
                "knowledge_binding": {
                    "status": self._binding_status(issues, {"missing_knowledge_package_ids"})
                },
            },
            "issues": issues,
            "context_packet": context_packet,
            "capability_plan": capability_plan,
        }

    def _build_capability_plan(self, context_packet: Dict[str, Any]) -> Dict[str, Any]:
        if not context_packet:
            return {}
        knowledge_binding = context_packet.get("knowledge_binding") or {}
        return self.capability_plan_service.build(
            context_packet=context_packet,
            knowledge_context={
                "knowledge_packages": knowledge_binding.get("knowledge_package_ids") or [],
                "approved_knowledge_cards": knowledge_binding.get("approved_knowledge_cards") or [],
            },
            ontology_focus={
                "key_tensions": [],
                "activated_constraints": [],
                "activated_objects": [],
                "activated_relations": [],
            },
        )

    @staticmethod
    def _binding_status(issues: List[Dict[str, str]], warning_codes: set[str]) -> str:
        if any(
            issue.get("severity") == "warning" and issue.get("code") in warning_codes
            for issue in issues
        ):
            return "warning"
        return "ok"

    @staticmethod
    def _as_list(value: Any) -> List[Any]:
        if isinstance(value, list):
            return value
        if value in (None, ""):
            return []
        return [value]
