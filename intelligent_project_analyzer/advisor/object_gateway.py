import json
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from intelligent_project_analyzer.advisor.database import (
    ProjectRow, ProjectContextRow, AdvisorActionDraftRow,
    ProjectBasePatchRow, SyncExecutionTicketRow, AuditLogRow,
)
from intelligent_project_analyzer.advisor.models import (
    Project, ProjectContext, AlignedBrief, AdvisorActionDraft,
    ProjectBasePatch, SyncExecutionTicket, AuditLogEntry,
)


class ObjectGateway:
    """LangGraph 节点和服务访问命名对象的唯一入口。禁止绕过此类直接查询 DB。"""

    def __init__(self, session: Session):
        self._session = session

    # ── Project ──────────────────────────────────────────
    def get_project(self, project_id: str) -> Optional[Project]:
        row = self._session.query(ProjectRow).filter_by(project_id=project_id).first()
        if not row:
            return None
        return Project(
            project_id=row.project_id, name=row.name,
            object_state=row.object_state, object_version=row.object_version,
            created_at=row.created_at, updated_at=row.updated_at,
        )

    def save_project(self, project: Project) -> None:
        existing = self._session.query(ProjectRow).filter_by(project_id=project.project_id).first()
        if existing:
            existing.name = project.name
            existing.object_state = project.object_state
            existing.object_version = project.object_version
            existing.updated_at = project.updated_at
        else:
            self._session.add(ProjectRow(
                project_id=project.project_id, name=project.name,
                object_state=project.object_state, object_version=project.object_version,
                created_at=project.created_at, updated_at=project.updated_at,
            ))

    def update_project_state(self, project_id: str, new_state: str) -> None:
        row = self._session.query(ProjectRow).filter_by(project_id=project_id).first()
        if row:
            row.object_state = new_state
            row.updated_at = datetime.utcnow()

    # ── ProjectContext ────────────────────────────────────
    def get_project_context(self, project_id: str) -> Optional[ProjectContext]:
        row = self._session.query(ProjectContextRow).filter_by(project_id=project_id).first()
        if not row:
            return None
        return ProjectContext(
            project_id=row.project_id,
            raw_description=row.raw_description,
            structured_data=json.loads(row.structured_data),
            evidence_status=row.evidence_status,
        )

    def save_project_context(self, ctx: ProjectContext) -> None:
        existing = self._session.query(ProjectContextRow).filter_by(project_id=ctx.project_id).first()
        if existing:
            existing.raw_description = ctx.raw_description
            existing.structured_data = json.dumps(ctx.structured_data, ensure_ascii=False)
            existing.evidence_status = ctx.evidence_status
        else:
            self._session.add(ProjectContextRow(
                project_id=ctx.project_id,
                raw_description=ctx.raw_description,
                structured_data=json.dumps(ctx.structured_data, ensure_ascii=False),
                evidence_status=ctx.evidence_status,
            ))

    # ── AdvisorActionDraft ────────────────────────────────
    def save_draft(self, draft: AdvisorActionDraft) -> None:
        self._session.add(AdvisorActionDraftRow(
            draft_id=draft.draft_id, project_id=draft.project_id,
            trace_id=draft.trace_id, actor=draft.actor, action=draft.action,
            payload=json.dumps(draft.payload, ensure_ascii=False),
            object_state=draft.object_state, created_at=draft.created_at,
        ))

    def get_draft(self, draft_id: str) -> Optional[AdvisorActionDraft]:
        row = self._session.query(AdvisorActionDraftRow).filter_by(draft_id=draft_id).first()
        if not row:
            return None
        return AdvisorActionDraft(
            draft_id=row.draft_id, project_id=row.project_id,
            trace_id=row.trace_id, actor=row.actor, action=row.action,
            payload=json.loads(row.payload), object_state=row.object_state,
            created_at=row.created_at,
        )

    # ── ProjectBasePatch ──────────────────────────────────
    def save_patch(self, patch: ProjectBasePatch) -> None:
        self._session.add(ProjectBasePatchRow(
            patch_id=patch.patch_id, project_id=patch.project_id,
            draft_id=patch.draft_id,
            content=json.dumps(patch.content, ensure_ascii=False),
            object_state=patch.object_state, created_at=patch.created_at,
        ))

    # ── SyncExecutionTicket ───────────────────────────────
    def save_ticket(self, ticket: SyncExecutionTicket) -> None:
        self._session.add(SyncExecutionTicketRow(
            ticket_id=ticket.ticket_id, trace_id=ticket.trace_id,
            draft_id=ticket.draft_id, actor=ticket.actor, action=ticket.action,
            object_id=ticket.object_id, object_version=ticket.object_version,
            execution_state=ticket.execution_state,
            created_at=ticket.created_at,
            completed_at=ticket.completed_at, error=ticket.error,
        ))

    def update_ticket_state(self, ticket_id: str, state: str,
                            error: Optional[str] = None) -> None:
        row = self._session.query(SyncExecutionTicketRow).filter_by(ticket_id=ticket_id).first()
        if row:
            row.execution_state = state
            row.completed_at = datetime.utcnow()
            row.error = error

    def get_ticket(self, ticket_id: str) -> Optional[SyncExecutionTicket]:
        row = self._session.query(SyncExecutionTicketRow).filter_by(ticket_id=ticket_id).first()
        if not row:
            return None
        return SyncExecutionTicket(
            ticket_id=row.ticket_id, trace_id=row.trace_id,
            draft_id=row.draft_id, actor=row.actor, action=row.action,
            object_id=row.object_id, object_version=row.object_version,
            execution_state=row.execution_state, created_at=row.created_at,
            completed_at=row.completed_at, error=row.error,
        )

    # ── AuditLog ──────────────────────────────────────────
    def append_audit_log(self, entry: AuditLogEntry) -> None:
        self._session.add(AuditLogRow(
            log_id=entry.log_id, trace_id=entry.trace_id,
            ticket_id=entry.ticket_id, actor=entry.actor, action=entry.action,
            object_id=entry.object_id,
            object_version_before=entry.object_version_before,
            object_version_after=entry.object_version_after,
            result=entry.result,
            detail=json.dumps(entry.detail, ensure_ascii=False),
            created_at=entry.created_at,
        ))

    def get_audit_log(self, project_id: str) -> list[AuditLogEntry]:
        rows = (
            self._session.query(AuditLogRow)
            .filter(AuditLogRow.object_id.like(f"{project_id}%"))
            .order_by(AuditLogRow.created_at)
            .all()
        )
        return [
            AuditLogEntry(
                log_id=r.log_id, trace_id=r.trace_id, ticket_id=r.ticket_id,
                actor=r.actor, action=r.action, object_id=r.object_id,
                object_version_before=r.object_version_before,
                object_version_after=r.object_version_after,
                result=r.result, detail=json.loads(r.detail),
                created_at=r.created_at,
            )
            for r in rows
        ]
