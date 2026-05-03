import uuid
from datetime import datetime

from intelligent_project_analyzer.advisor.gate import MVPGate
from intelligent_project_analyzer.advisor.models import (
    AdvisorActionDraft, ProjectBasePatch, SyncExecutionTicket, AuditLogEntry,
)
from intelligent_project_analyzer.advisor.object_gateway import ObjectGateway
from intelligent_project_analyzer.advisor.state_transition import StateTransitionService


def _bump_version(version: str) -> str:
    parts = version.split(".")
    parts[-1] = str(int(parts[-1]) + 1)
    return ".".join(parts)


class CommandHandler:
    """Write Path 编排器。负责 Gate → Ticket → Object Write → AuditLog。"""

    def __init__(self, gateway: ObjectGateway, gate: MVPGate,
                 state_svc: StateTransitionService):
        self._gw = gateway
        self._gate = gate
        self._state_svc = state_svc

    def execute(self, draft: AdvisorActionDraft) -> SyncExecutionTicket:
        gate_result = self._gate.run(draft, actor=draft.actor)

        if not gate_result.passed:
            # Gate 失败：写入失败 AuditLog，抛出异常
            self._write_failure_audit(draft, "gate_rejected")
            first_error = gate_result.errors[0]
            if first_error.code == 409:
                raise PermissionError(f"Gate blocked: {first_error.message}")
            elif first_error.code == 403:
                raise PermissionError(f"Permission denied: {first_error.message}")
            else:
                raise ValueError(f"422 Validation error: {first_error.message}")

        ticket = SyncExecutionTicket(
            ticket_id=str(uuid.uuid4()),
            trace_id=draft.trace_id,
            draft_id=draft.draft_id,
            actor=draft.actor,
            action=draft.action,
            object_id=draft.project_id,
            object_version=self._get_current_version(draft.project_id),
            execution_state="running",
            created_at=datetime.utcnow(),
        )
        self._gw.save_ticket(ticket)

        try:
            old_version = ticket.object_version
            new_version = _bump_version(old_version)

            patch = ProjectBasePatch(
                patch_id=str(uuid.uuid4()),
                project_id=draft.project_id,
                draft_id=draft.draft_id,
                content=draft.payload,
                object_state="draft",
                created_at=datetime.utcnow(),
            )
            self._gw.save_patch(patch)

            self._gw.update_ticket_state(ticket.ticket_id, "succeeded")

            self._gw.append_audit_log(AuditLogEntry(
                log_id=str(uuid.uuid4()),
                trace_id=draft.trace_id,
                ticket_id=ticket.ticket_id,
                actor=draft.actor,
                action=draft.action,
                object_id=draft.project_id,
                object_version_before=old_version,
                object_version_after=new_version,
                result="success",
                created_at=datetime.utcnow(),
            ))

            ticket.execution_state = "succeeded"
            return ticket

        except Exception as exc:
            self._gw.update_ticket_state(ticket.ticket_id, "failed", str(exc))
            self._write_failure_audit(draft, str(exc), ticket_id=ticket.ticket_id)
            ticket.execution_state = "failed"
            return ticket

    def _get_current_version(self, project_id: str) -> str:
        project = self._gw.get_project(project_id)
        return project.object_version if project else "0.1.0"

    def _write_failure_audit(self, draft: AdvisorActionDraft, reason: str,
                              ticket_id: str = "none") -> None:
        self._gw.append_audit_log(AuditLogEntry(
            log_id=str(uuid.uuid4()),
            trace_id=draft.trace_id,
            ticket_id=ticket_id,
            actor=draft.actor,
            action=draft.action,
            object_id=draft.project_id,
            object_version_before="unknown",
            object_version_after="unknown",
            result="failure",
            detail={"reason": reason},
            created_at=datetime.utcnow(),
        ))
