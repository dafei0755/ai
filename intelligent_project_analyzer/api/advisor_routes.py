"""Phase A Advisor API 路由。

端点：
  POST /v1/advisor/intents             — 主入口，Read Path
  POST /v1/projects                    — 创建 Project
  GET  /v1/projects/{id}               — 读取 Project
  POST /v1/projects/{id}/drafts        — 创建 AdvisorActionDraft
  POST /v1/projects/{id}/drafts/{did}/confirm  — 用户确认，触发 CommandHandler
  GET  /v1/tickets/{ticket_id}         — 查询 SyncExecutionTicket
  GET  /v1/audit/{project_id}          — 查询 AuditLog
"""
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from intelligent_project_analyzer.advisor.database import init_db, get_session
from intelligent_project_analyzer.advisor.object_gateway import ObjectGateway
from intelligent_project_analyzer.advisor.gate import MVPGate
from intelligent_project_analyzer.advisor.state_transition import StateTransitionService, InvalidStateTransitionError
from intelligent_project_analyzer.advisor.command_handler import CommandHandler
from intelligent_project_analyzer.advisor.models import Project, AdvisorActionDraft
from intelligent_project_analyzer.workflow.advisor_workflow import run_advisor

router = APIRouter()
_engine = init_db()


# ── Request / Response 模型 ────────────────────────────────────────

class SceneContextIn(BaseModel):
    module: str
    user_action: str
    dispatch_level: str


class AdvisorIntentRequest(BaseModel):
    project_id: str
    trace_id: str
    scene_context: SceneContextIn
    message: str


class AdvisorIntentResponse(BaseModel):
    trace_id: str
    bound_object_id: Optional[str]
    object_state: Optional[str]
    object_version: Optional[str]
    evidence_status: Optional[str]
    judgment: dict
    action_chips: list
    activated_capabilities: list


class CreateProjectRequest(BaseModel):
    name: str


class CreateDraftRequest(BaseModel):
    trace_id: str
    actor: str
    action: str = "create_project_base_patch"
    payload: dict


# ── 端点实现 ──────────────────────────────────────────────────────

@router.post("/v1/advisor/intents")
async def post_advisor_intents(req: AdvisorIntentRequest, request: Request):
    """Read Path — 调用 AdvisorAgent，返回 AdvisorViewModel。不写库。"""
    trace_id = req.trace_id
    result = run_advisor(
        project_id=req.project_id,
        trace_id=trace_id,
        session_id=f"{req.project_id}-{trace_id}",
        user_message=req.message,
        module=req.scene_context.module,
    )
    return {
        "trace_id": trace_id,
        "bound_object_id": result.get("bound_object_id"),
        "object_state": result.get("object_state"),
        "object_version": result.get("object_version"),
        "evidence_status": result.get("evidence_status"),
        "judgment": {
            "content": result.get("judgment_content", ""),
            "confidence": result.get("judgment_confidence", "low"),
        },
        "action_chips": result.get("action_chips") or [],
        "activated_capabilities": result.get("activated_capabilities") or [],
    }


@router.post("/v1/projects", status_code=201)
async def create_project(req: CreateProjectRequest):
    project_id = f"proj-{uuid.uuid4().hex[:8]}"
    now = datetime.utcnow()
    project = Project(
        project_id=project_id, name=req.name,
        created_at=now, updated_at=now,
    )
    with get_session(_engine) as session:
        ObjectGateway(session).save_project(project)
    return {"project_id": project_id, "object_state": "draft"}


@router.get("/v1/projects/{project_id}")
async def get_project(project_id: str):
    with get_session(_engine) as session:
        project = ObjectGateway(session).get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    return project.model_dump()


@router.post("/v1/projects/{project_id}/drafts", status_code=201)
async def create_draft(project_id: str, req: CreateDraftRequest):
    draft = AdvisorActionDraft(
        draft_id=str(uuid.uuid4()),
        project_id=project_id,
        trace_id=req.trace_id,
        actor=req.actor,
        action=req.action,
        payload=req.payload,
        created_at=datetime.utcnow(),
    )
    with get_session(_engine) as session:
        ObjectGateway(session).save_draft(draft)
    return {"draft_id": draft.draft_id, "object_state": "draft"}


@router.post("/v1/projects/{project_id}/drafts/{draft_id}/confirm")
async def confirm_draft(project_id: str, draft_id: str):
    """Write Path — MVP Gate + CommandHandler。"""
    error_detail = None
    result_data = None
    with get_session(_engine) as session:
        gw = ObjectGateway(session)
        draft = gw.get_draft(draft_id)
        if not draft:
            raise HTTPException(status_code=404, detail=f"Draft {draft_id} not found")
        gate = MVPGate(gw)
        state_svc = StateTransitionService(gw)
        ch = CommandHandler(gw, gate, state_svc)
        try:
            ticket = ch.execute(draft)
            result_data = {"ticket_id": ticket.ticket_id, "execution_state": ticket.execution_state}
        except (PermissionError, ValueError) as e:
            error_detail = str(e)
    if error_detail:
        raise HTTPException(status_code=409, detail=error_detail)
    return result_data


@router.get("/v1/tickets/{ticket_id}")
async def get_ticket(ticket_id: str):
    with get_session(_engine) as session:
        ticket = ObjectGateway(session).get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    return ticket.model_dump()


@router.get("/v1/audit/{project_id}")
async def get_audit_log(project_id: str):
    with get_session(_engine) as session:
        logs = ObjectGateway(session).get_audit_log(project_id)
    return [e.model_dump() for e in logs]
