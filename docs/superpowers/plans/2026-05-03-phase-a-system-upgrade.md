# Phase A 系统升级 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有 LangGraph 工作流上叠加母架构对象链，交付 Day 1 最小闭环：用户输入 → Skill 结构化 → AdvisorViewModel 返回 → 用户确认 → ProjectBasePatch(draft) 写库 → AuditLog。

**Architecture:** 新增 `intelligent_project_analyzer/advisor/` 模块，包含 Pydantic 对象模型、SQLite 存储、ObjectGateway、StateTransitionService、MVPGate、CommandHandler；LangGraph 新增独立 `advisor_workflow.py` 子图，不修改现有 main_workflow.py；前端 Phase A1 使用现有已设计计划。

**Tech Stack:** Python 3.11+, Pydantic v2, SQLAlchemy 2.x, LangGraph 0.2+, FastAPI, pytest, Next.js 15, TypeScript, Tailwind CSS

---

## 文件变更清单

### 前端（Phase A1 — 已有详细计划）
| 操作 | 文件 |
|------|------|
| 新建 | `frontend-nextjs/types/advisor.ts` |
| 重写 | `frontend-nextjs/components/project-cockpit/AdvisorPanel.tsx` |
| 更新 | `frontend-nextjs/components/project-cockpit/mock/mockData.ts` |
| 更新 | `frontend-nextjs/app/project-cockpit/[projectId]/page.tsx` |
| 新建 | `frontend-nextjs/__tests__/AdvisorPanel.test.tsx` |
| 新建 | `frontend-nextjs/__tests__/mockAdvisorViewModel.test.ts` |

### 后端（Phase A — 新设计）
| 操作 | 文件 | 职责 |
|------|------|------|
| 新建 | `intelligent_project_analyzer/advisor/__init__.py` | 模块入口 |
| 新建 | `intelligent_project_analyzer/advisor/models.py` | Pydantic 核心对象 + ObjectState |
| 新建 | `intelligent_project_analyzer/advisor/database.py` | SQLAlchemy 引擎 + 表定义 + Session |
| 新建 | `intelligent_project_analyzer/advisor/object_gateway.py` | ObjectGateway — 命名对象的唯一读取代理 |
| 新建 | `intelligent_project_analyzer/advisor/state_transition.py` | StateTransitionService — 对象状态迁移 |
| 新建 | `intelligent_project_analyzer/advisor/skill_registry.py` | SkillRegistry — 加载 SkillManifest YAML |
| 新建 | `intelligent_project_analyzer/advisor/skills/__init__.py` | Skill 子包 |
| 新建 | `intelligent_project_analyzer/advisor/skills/requirement_structuring.py` | 需求结构化 Skill |
| 新建 | `intelligent_project_analyzer/advisor/gate.py` | MVPGate — 4 项写前校验 |
| 新建 | `intelligent_project_analyzer/advisor/command_handler.py` | CommandHandler — Write Path 编排 |
| 新建 | `intelligent_project_analyzer/workflow/advisor_workflow.py` | AdvisorAgent LangGraph 子图 |
| 新建 | `intelligent_project_analyzer/api/advisor_routes.py` | FastAPI 路由（6 个端点） |
| 修改 | `intelligent_project_analyzer/api/server.py` | 注册 advisor_router |
| 新建 | `intelligent_project_analyzer/config/skills/requirement_structuring.yaml` | SkillManifest |
| 新建 | `tests/advisor/__init__.py` | 测试包 |
| 新建 | `tests/advisor/test_models.py` | 对象模型测试 |
| 新建 | `tests/advisor/test_state_transition.py` | 状态迁移测试（含红线） |
| 新建 | `tests/advisor/test_gate.py` | MVPGate 测试 |
| 新建 | `tests/advisor/test_command_handler.py` | CommandHandler 测试 |
| 新建 | `tests/advisor/test_skill.py` | Skill 契约测试 |
| 新建 | `tests/advisor/test_api.py` | API 端点测试 |
| 新建 | `tests/advisor/test_trace_id.py` | trace_id 回放测试 |

---

## Task 1: 前端 Phase A1（执行已有计划）

**Files:** 见上方前端变更清单

- [ ] **Step 1: 执行已有前端计划**

打开 `docs/superpowers/plans/2026-05-03-advisor-panel-phase-a1.md`，按 Task 1→5 顺序执行所有步骤。

最终验证：
```bash
cd frontend-nextjs
npx jest --verbose
npx tsc --noEmit
```
期望：所有测试通过，无 TypeScript error。

- [ ] **Step 2: 确认 AdvisorPanel Phase A1 完成**

运行开发服务器，访问 `/project-cockpit/hay-demo`，确认右侧高参席显示：
- 五区结构（标题/判断/Chip/能力/输入）
- `内部推断` 徽章
- `补充 3 个关键信息` 主 Chip（蓝底）
- 两个次 Chip（描边）

---

## Task 2: 后端模块骨架 + Pydantic 对象模型

**Files:**
- Create: `intelligent_project_analyzer/advisor/__init__.py`
- Create: `intelligent_project_analyzer/advisor/models.py`
- Create: `tests/advisor/__init__.py`
- Create: `tests/advisor/test_models.py`

- [ ] **Step 1: 写模型测试（先让它失败）**

新建 `tests/advisor/__init__.py`（空文件），然后新建 `tests/advisor/test_models.py`：

```python
import pytest
from datetime import datetime
from intelligent_project_analyzer.advisor.models import (
    Project, ProjectContext, AlignedBrief, AdvisorActionDraft,
    ProjectBasePatch, SyncExecutionTicket, AuditLogEntry,
    ObjectState, ExecutionState,
)


def test_project_default_state():
    p = Project(
        project_id="proj-001",
        name="测试项目",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    assert p.object_state == "draft"
    assert p.object_version == "0.1.0"


def test_project_context_default_evidence():
    ctx = ProjectContext(
        project_id="proj-001",
        raw_description="民宿设计项目",
    )
    assert ctx.evidence_status == "none"
    assert ctx.structured_data == {}


def test_advisor_action_draft_fields():
    draft = AdvisorActionDraft(
        draft_id="draft-001",
        project_id="proj-001",
        trace_id="trace-001",
        actor="user-1",
        action="create_project_base_patch",
        payload={"name": "HAY 七里坪"},
        created_at=datetime.utcnow(),
    )
    assert draft.object_state == "draft"


def test_sync_execution_ticket_initial_state():
    ticket = SyncExecutionTicket(
        ticket_id="ticket-001",
        trace_id="trace-001",
        draft_id="draft-001",
        actor="user-1",
        action="create_project_base_patch",
        object_id="proj-001",
        object_version="0.1.0",
        execution_state="pending",
        created_at=datetime.utcnow(),
    )
    assert ticket.completed_at is None
    assert ticket.error is None


def test_audit_log_entry_fields():
    entry = AuditLogEntry(
        log_id="log-001",
        trace_id="trace-001",
        ticket_id="ticket-001",
        actor="user-1",
        action="create_project_base_patch",
        object_id="proj-001",
        object_version_before="0.1.0",
        object_version_after="0.1.1",
        result="success",
        created_at=datetime.utcnow(),
    )
    assert entry.detail == {}
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd intelligent_project_analyzer
python -m pytest ../tests/advisor/test_models.py -v
```
期望：ImportError（模块不存在）。

- [ ] **Step 3: 创建目录和 __init__.py**

```bash
mkdir -p intelligent_project_analyzer/advisor/skills
touch intelligent_project_analyzer/advisor/__init__.py
touch intelligent_project_analyzer/advisor/skills/__init__.py
```

- [ ] **Step 4: 创建 `intelligent_project_analyzer/advisor/models.py`**

```python
from datetime import datetime
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field

ObjectState = Literal["draft", "pending_confirmation", "frozen", "stale"]
ExecutionState = Literal["pending", "running", "succeeded", "failed", "cancelled", "timeout"]
EvidenceStatus = Literal["none", "internal_hint", "verified"]


class Project(BaseModel):
    project_id: str
    name: str
    object_state: ObjectState = "draft"
    object_version: str = "0.1.0"
    created_at: datetime
    updated_at: datetime


class ProjectContext(BaseModel):
    project_id: str
    raw_description: str
    structured_data: dict[str, Any] = Field(default_factory=dict)
    evidence_status: EvidenceStatus = "none"


class AlignedBrief(BaseModel):
    project_id: str
    object_state: ObjectState = "draft"
    content: dict[str, Any] = Field(default_factory=dict)


class AdvisorActionDraft(BaseModel):
    draft_id: str
    project_id: str
    trace_id: str
    actor: str
    action: str
    payload: dict[str, Any]
    object_state: ObjectState = "draft"
    created_at: datetime


class ProjectBasePatch(BaseModel):
    patch_id: str
    project_id: str
    draft_id: str
    content: dict[str, Any]
    object_state: Literal["draft", "applied", "discarded"] = "draft"
    created_at: datetime


class SyncExecutionTicket(BaseModel):
    ticket_id: str
    trace_id: str
    draft_id: str
    actor: str
    action: str
    object_id: str
    object_version: str
    execution_state: ExecutionState
    created_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class AuditLogEntry(BaseModel):
    log_id: str
    trace_id: str
    ticket_id: str
    actor: str
    action: str
    object_id: str
    object_version_before: str
    object_version_after: str
    result: Literal["success", "failure"]
    detail: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
```

- [ ] **Step 5: 运行测试，确认通过**

```bash
python -m pytest ../tests/advisor/test_models.py -v
```
期望：5 tests passing。

- [ ] **Step 6: Commit**

```bash
git add intelligent_project_analyzer/advisor/ tests/advisor/
git commit -m "feat: add advisor module skeleton and Pydantic object models"
```

---

## Task 3: 数据库层 + ObjectGateway

**Files:**
- Create: `intelligent_project_analyzer/advisor/database.py`
- Create: `intelligent_project_analyzer/advisor/object_gateway.py`
- Create: `tests/advisor/test_object_gateway.py`

- [ ] **Step 1: 写 ObjectGateway 测试**

新建 `tests/advisor/test_object_gateway.py`：

```python
import pytest
from datetime import datetime
from intelligent_project_analyzer.advisor.database import init_db, get_session
from intelligent_project_analyzer.advisor.object_gateway import ObjectGateway
from intelligent_project_analyzer.advisor.models import Project, ProjectContext


@pytest.fixture
def gateway():
    engine = init_db("sqlite:///:memory:")
    with get_session(engine) as session:
        yield ObjectGateway(session)


def test_create_and_get_project(gateway):
    project = Project(
        project_id="proj-001",
        name="HAY 七里坪",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    gateway.save_project(project)
    result = gateway.get_project("proj-001")
    assert result is not None
    assert result.name == "HAY 七里坪"
    assert result.object_state == "draft"


def test_get_project_returns_none_if_missing(gateway):
    result = gateway.get_project("nonexistent")
    assert result is None


def test_save_and_get_project_context(gateway):
    ctx = ProjectContext(
        project_id="proj-001",
        raw_description="民宿设计，山地，300㎡",
    )
    gateway.save_project_context(ctx)
    result = gateway.get_project_context("proj-001")
    assert result.raw_description == "民宿设计，山地，300㎡"


def test_update_project_state(gateway):
    project = Project(
        project_id="proj-002",
        name="Test",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    gateway.save_project(project)
    gateway.update_project_state("proj-002", "pending_confirmation")
    result = gateway.get_project("proj-002")
    assert result.object_state == "pending_confirmation"
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
python -m pytest ../tests/advisor/test_object_gateway.py -v
```
期望：ImportError。

- [ ] **Step 3: 创建 `intelligent_project_analyzer/advisor/database.py`**

```python
import json
from contextlib import contextmanager
from datetime import datetime
from typing import Generator

from sqlalchemy import create_engine, Column, String, DateTime, Text, Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


class ProjectRow(Base):
    __tablename__ = "advisor_projects"
    project_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    object_state = Column(String, nullable=False, default="draft")
    object_version = Column(String, nullable=False, default="0.1.0")
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class ProjectContextRow(Base):
    __tablename__ = "advisor_project_contexts"
    project_id = Column(String, primary_key=True)
    raw_description = Column(Text, nullable=False)
    structured_data = Column(Text, nullable=False, default="{}")
    evidence_status = Column(String, nullable=False, default="none")


class AdvisorActionDraftRow(Base):
    __tablename__ = "advisor_action_drafts"
    draft_id = Column(String, primary_key=True)
    project_id = Column(String, nullable=False)
    trace_id = Column(String, nullable=False)
    actor = Column(String, nullable=False)
    action = Column(String, nullable=False)
    payload = Column(Text, nullable=False, default="{}")
    object_state = Column(String, nullable=False, default="draft")
    created_at = Column(DateTime, nullable=False)


class ProjectBasePatchRow(Base):
    __tablename__ = "advisor_project_base_patches"
    patch_id = Column(String, primary_key=True)
    project_id = Column(String, nullable=False)
    draft_id = Column(String, nullable=False)
    content = Column(Text, nullable=False, default="{}")
    object_state = Column(String, nullable=False, default="draft")
    created_at = Column(DateTime, nullable=False)


class SyncExecutionTicketRow(Base):
    __tablename__ = "advisor_sync_execution_tickets"
    ticket_id = Column(String, primary_key=True)
    trace_id = Column(String, nullable=False)
    draft_id = Column(String, nullable=False)
    actor = Column(String, nullable=False)
    action = Column(String, nullable=False)
    object_id = Column(String, nullable=False)
    object_version = Column(String, nullable=False)
    execution_state = Column(String, nullable=False, default="pending")
    created_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=True)


class AuditLogRow(Base):
    __tablename__ = "advisor_audit_log"
    log_id = Column(String, primary_key=True)
    trace_id = Column(String, nullable=False)
    ticket_id = Column(String, nullable=False)
    actor = Column(String, nullable=False)
    action = Column(String, nullable=False)
    object_id = Column(String, nullable=False)
    object_version_before = Column(String, nullable=False)
    object_version_after = Column(String, nullable=False)
    result = Column(String, nullable=False)
    detail = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, nullable=False)


def init_db(url: str = "sqlite:///advisor_objects.db") -> Engine:
    if url == "sqlite:///:memory:":
        from sqlalchemy.pool import StaticPool
        engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        engine = create_engine(url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return engine


@contextmanager
def get_session(engine: Engine) -> Generator[Session, None, None]:
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

- [ ] **Step 4: 创建 `intelligent_project_analyzer/advisor/object_gateway.py`**

```python
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
```

- [ ] **Step 5: 运行测试，确认通过**

```bash
python -m pytest ../tests/advisor/test_object_gateway.py -v
```
期望：4 tests passing。

- [ ] **Step 6: Commit**

```bash
git add intelligent_project_analyzer/advisor/database.py \
        intelligent_project_analyzer/advisor/object_gateway.py \
        tests/advisor/test_object_gateway.py
git commit -m "feat: add database layer and ObjectGateway"
```

---

## Task 4: StateTransitionService

**Files:**
- Create: `intelligent_project_analyzer/advisor/state_transition.py`
- Create: `tests/advisor/test_state_transition.py`

- [ ] **Step 1: 写状态迁移测试（含红线测试）**

新建 `tests/advisor/test_state_transition.py`：

```python
import pytest
from datetime import datetime
from intelligent_project_analyzer.advisor.database import init_db, get_session
from intelligent_project_analyzer.advisor.object_gateway import ObjectGateway
from intelligent_project_analyzer.advisor.state_transition import StateTransitionService, InvalidStateTransitionError
from intelligent_project_analyzer.advisor.models import Project


@pytest.fixture
def svc():
    engine = init_db("sqlite:///:memory:")
    with get_session(engine) as session:
        gw = ObjectGateway(session)
        yield StateTransitionService(gw), gw


def _make_project(project_id: str, state: str) -> Project:
    return Project(
        project_id=project_id, name="Test",
        object_state=state,
        created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    )


def test_draft_to_pending_confirmation(svc):
    service, gw = svc
    gw.save_project(_make_project("proj-1", "draft"))
    service.transition("proj-1", "pending_confirmation")
    assert gw.get_project("proj-1").object_state == "pending_confirmation"


def test_pending_to_frozen(svc):
    service, gw = svc
    gw.save_project(_make_project("proj-2", "pending_confirmation"))
    service.transition("proj-2", "frozen")
    assert gw.get_project("proj-2").object_state == "frozen"


def test_pending_back_to_draft(svc):
    service, gw = svc
    gw.save_project(_make_project("proj-3", "pending_confirmation"))
    service.transition("proj-3", "draft")
    assert gw.get_project("proj-3").object_state == "draft"


# ── 架构红线：非法迁移必须被拒绝 ──────────────────────────────
def test_frozen_to_draft_raises_409(svc):
    """红线：冻结对象不得直接回到草案状态"""
    service, gw = svc
    gw.save_project(_make_project("proj-4", "frozen"))
    with pytest.raises(InvalidStateTransitionError) as exc_info:
        service.transition("proj-4", "draft")
    assert exc_info.value.status_code == 409


def test_draft_to_frozen_raises_409(svc):
    """红线：草案对象不得跳过 pending_confirmation 直接冻结"""
    service, gw = svc
    gw.save_project(_make_project("proj-5", "draft"))
    with pytest.raises(InvalidStateTransitionError) as exc_info:
        service.transition("proj-5", "frozen")
    assert exc_info.value.status_code == 409


def test_frozen_to_stale_allowed(svc):
    """上游升版时允许 frozen → stale"""
    service, gw = svc
    gw.save_project(_make_project("proj-6", "frozen"))
    service.transition("proj-6", "stale")
    assert gw.get_project("proj-6").object_state == "stale"
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
python -m pytest ../tests/advisor/test_state_transition.py -v
```
期望：ImportError。

- [ ] **Step 3: 创建 `intelligent_project_analyzer/advisor/state_transition.py`**

```python
from intelligent_project_analyzer.advisor.object_gateway import ObjectGateway

# 合法迁移表：{current_state: [allowed_target_states]}
ALLOWED_TRANSITIONS: dict[str, list[str]] = {
    "draft":                ["pending_confirmation"],
    "pending_confirmation": ["frozen", "draft"],
    "frozen":               ["stale"],
    "stale":                ["pending_confirmation"],
}


class InvalidStateTransitionError(Exception):
    def __init__(self, current: str, target: str):
        self.status_code = 409
        super().__init__(
            f"Invalid state transition: {current} → {target}. "
            f"Allowed from {current}: {ALLOWED_TRANSITIONS.get(current, [])}"
        )


class StateTransitionService:
    def __init__(self, gateway: ObjectGateway):
        self._gw = gateway

    def transition(self, project_id: str, target_state: str) -> None:
        project = self._gw.get_project(project_id)
        if project is None:
            raise ValueError(f"Project {project_id} not found")
        current = project.object_state
        allowed = ALLOWED_TRANSITIONS.get(current, [])
        if target_state not in allowed:
            raise InvalidStateTransitionError(current, target_state)
        self._gw.update_project_state(project_id, target_state)
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
python -m pytest ../tests/advisor/test_state_transition.py -v
```
期望：6 tests passing。

- [ ] **Step 5: Commit**

```bash
git add intelligent_project_analyzer/advisor/state_transition.py \
        tests/advisor/test_state_transition.py
git commit -m "feat: add StateTransitionService with red-line tests"
```

---

## Task 5: SkillManifest YAML + SkillRegistry

**Files:**
- Create: `intelligent_project_analyzer/config/skills/requirement_structuring.yaml`
- Create: `intelligent_project_analyzer/advisor/skill_registry.py`
- Create: `tests/advisor/test_skill_registry.py`（内嵌在 test_skill.py 中，见 Task 6）

- [ ] **Step 1: 创建 SkillManifest YAML**

新建目录和文件 `intelligent_project_analyzer/config/skills/requirement_structuring.yaml`：

```yaml
skill_id: req_structuring_v1
skill_name: 需求结构化 Skill
skill_type: analysis
owner_domain: project_base
input_contract:
  required:
    - project_id
    - raw_description
  optional:
    - context_hints
output_contract:
  required:
    - structured_data
    - evidence_status
    - confidence
  optional:
    - missing_fields
    - suggestions
failure_modes:
  llm_parse_error: retry_once_then_degrade
  empty_input: return_422
execution_mode: sync
side_effect_level: none
timeout_ms: 30000
fallback_strategy: return_partial_with_low_confidence
version: "1.0.0"
```

- [ ] **Step 2: 创建 `intelligent_project_analyzer/advisor/skill_registry.py`**

```python
import os
from pathlib import Path
from typing import Optional
import yaml


class SkillManifest:
    def __init__(self, data: dict):
        self.skill_id: str = data["skill_id"]
        self.skill_name: str = data["skill_name"]
        self.skill_type: str = data["skill_type"]
        self.owner_domain: str = data["owner_domain"]
        self.input_contract: dict = data["input_contract"]
        self.output_contract: dict = data["output_contract"]
        self.execution_mode: str = data["execution_mode"]
        self.side_effect_level: str = data["side_effect_level"]
        self.timeout_ms: int = data["timeout_ms"]
        self.fallback_strategy: str = data["fallback_strategy"]
        self.version: str = data["version"]
        self.failure_modes: dict = data.get("failure_modes", {})


class SkillRegistry:
    """加载并提供 SkillManifest 查询。Skill 必须在此注册才能进入正式链路。"""

    def __init__(self, skills_dir: Optional[str] = None):
        if skills_dir is None:
            base = Path(__file__).parent.parent
            skills_dir = str(base / "config" / "skills")
        self._skills: dict[str, SkillManifest] = {}
        self._load_all(skills_dir)

    def _load_all(self, skills_dir: str) -> None:
        path = Path(skills_dir)
        if not path.exists():
            return
        for yaml_file in path.glob("*.yaml"):
            with open(yaml_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            manifest = SkillManifest(data)
            self._skills[manifest.skill_id] = manifest

    def get(self, skill_id: str) -> Optional[SkillManifest]:
        return self._skills.get(skill_id)

    def require(self, skill_id: str) -> SkillManifest:
        """获取 Skill，不存在则抛出异常（无 Manifest 不得进入正式链路）。"""
        manifest = self.get(skill_id)
        if manifest is None:
            raise ValueError(
                f"Skill '{skill_id}' not found in SkillRegistry. "
                "Register a SkillManifest YAML before entering the main pipeline."
            )
        return manifest

    def list_all(self) -> list[str]:
        return list(self._skills.keys())
```

- [ ] **Step 3: 快速冒烟测试**

```bash
python -c "
from intelligent_project_analyzer.advisor.skill_registry import SkillRegistry
r = SkillRegistry()
m = r.require('req_structuring_v1')
print('Loaded:', m.skill_name, 'version', m.version)
print('Required inputs:', m.input_contract['required'])
"
```
期望输出：`Loaded: 需求结构化 Skill version 1.0.0`，`Required inputs: ['project_id', 'raw_description']`

- [ ] **Step 4: Commit**

```bash
git add intelligent_project_analyzer/config/skills/requirement_structuring.yaml \
        intelligent_project_analyzer/advisor/skill_registry.py
git commit -m "feat: add SkillManifest YAML and SkillRegistry"
```

---

## Task 6: 需求结构化 Skill + 契约测试

**Files:**
- Create: `intelligent_project_analyzer/advisor/skills/requirement_structuring.py`
- Create: `tests/advisor/test_skill.py`

- [ ] **Step 1: 写 Skill 契约测试**

新建 `tests/advisor/test_skill.py`：

```python
import pytest
from unittest.mock import patch, MagicMock
from intelligent_project_analyzer.advisor.skill_registry import SkillRegistry
from intelligent_project_analyzer.advisor.skills.requirement_structuring import (
    RequirementStructuringSkill, SkillInput, SkillOutput,
)


@pytest.fixture
def skill():
    registry = SkillRegistry()
    return RequirementStructuringSkill(registry)


def test_skill_registered_in_manifest(skill):
    """红线：Skill 必须从 SkillManifest 选取"""
    registry = SkillRegistry()
    manifest = registry.require("req_structuring_v1")
    assert manifest.skill_id == "req_structuring_v1"
    assert manifest.side_effect_level == "none"


def test_empty_input_raises_422(skill):
    """红线：空输入返回 422"""
    with pytest.raises(ValueError) as exc:
        skill.run(SkillInput(project_id="p1", raw_description=""))
    assert "422" in str(exc.value)


def test_output_is_structured(skill):
    """红线：Skill 输出必须结构化（Pydantic 验证通过）"""
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content='''{
        "project_type": "民宿",
        "location": "山地",
        "key_requirements": ["设计感", "自然融合"],
        "missing_fields": ["面积", "房间数"],
        "confidence": "medium"
    }''')
    with patch.object(skill, "_llm", mock_llm):
        result = skill.run(SkillInput(project_id="p1", raw_description="山地民宿，注重自然融合"))
    assert isinstance(result, SkillOutput)
    assert result.evidence_status in ("none", "internal_hint", "verified")
    assert result.confidence in ("high", "medium", "low")
    assert isinstance(result.structured_data, dict)


def test_llm_parse_error_falls_back(skill):
    """LLM 解析失败时走 fallback（返回 partial + low_confidence）"""
    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = Exception("LLM timeout")
    with patch.object(skill, "_llm", mock_llm):
        result = skill.run(SkillInput(project_id="p1", raw_description="民宿设计"))
    assert result.confidence == "low"
    assert result.evidence_status == "none"


def test_output_required_fields_present(skill):
    """输出必须包含 output_contract.required 定义的所有字段"""
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content='{"project_type":"民宿","confidence":"high"}')
    with patch.object(skill, "_llm", mock_llm):
        result = skill.run(SkillInput(project_id="p1", raw_description="民宿设计"))
    assert hasattr(result, "structured_data")
    assert hasattr(result, "evidence_status")
    assert hasattr(result, "confidence")
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
python -m pytest ../tests/advisor/test_skill.py -v
```
期望：ImportError。

- [ ] **Step 3: 创建 `intelligent_project_analyzer/advisor/skills/requirement_structuring.py`**

```python
import json
from typing import Any, Literal, Optional
from pydantic import BaseModel

from intelligent_project_analyzer.advisor.skill_registry import SkillRegistry
from intelligent_project_analyzer.services.llm_factory import LLMFactory


class SkillInput(BaseModel):
    project_id: str
    raw_description: str
    context_hints: Optional[list[str]] = None


class SkillOutput(BaseModel):
    structured_data: dict[str, Any]
    evidence_status: Literal["none", "internal_hint", "verified"] = "none"
    confidence: Literal["high", "medium", "low"]
    missing_fields: list[str] = []
    suggestions: list[str] = []


_SYSTEM_PROMPT = """你是一个需求结构化专家。将用户的项目描述解析为结构化 JSON，包含以下字段（如有）：
- project_type: 项目类型（如民宿、办公、餐厅等）
- location: 地点/环境特征
- area_sqm: 建筑面积（数值，如已知）
- room_count: 房间数量（数值，如已知）
- key_requirements: 核心需求列表
- style_keywords: 风格关键词列表
- missing_fields: 明显缺失但重要的信息列表
- confidence: 你对结构化结果的置信度（high/medium/low）

只返回 JSON，不要有任何其他文字。"""


class RequirementStructuringSkill:
    SKILL_ID = "req_structuring_v1"

    def __init__(self, registry: SkillRegistry):
        self._manifest = registry.require(self.SKILL_ID)
        self._llm = LLMFactory.create_llm(temperature=0.1, max_tokens=1000)

    def run(self, inp: SkillInput) -> SkillOutput:
        if not inp.raw_description.strip():
            raise ValueError("422: raw_description 不能为空")

        try:
            messages = [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": inp.raw_description},
            ]
            response = self._llm.invoke(messages)
            raw = response.content.strip()
            data = json.loads(raw)
            confidence = data.pop("confidence", "medium")
            missing_fields = data.pop("missing_fields", [])
            return SkillOutput(
                structured_data=data,
                evidence_status="internal_hint",
                confidence=confidence,
                missing_fields=missing_fields,
            )
        except Exception:
            return SkillOutput(
                structured_data={},
                evidence_status="none",
                confidence="low",
                missing_fields=[],
                suggestions=["原始描述解析失败，请检查输入或重试"],
            )
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
python -m pytest ../tests/advisor/test_skill.py -v
```
期望：5 tests passing。

- [ ] **Step 5: Commit**

```bash
git add intelligent_project_analyzer/advisor/skills/requirement_structuring.py \
        tests/advisor/test_skill.py
git commit -m "feat: add RequirementStructuringSkill with contract tests"
```

---

## Task 7: MVPGate

**Files:**
- Create: `intelligent_project_analyzer/advisor/gate.py`
- Create: `tests/advisor/test_gate.py`

- [ ] **Step 1: 写 Gate 测试**

新建 `tests/advisor/test_gate.py`：

```python
import pytest
from datetime import datetime
from intelligent_project_analyzer.advisor.database import init_db, get_session
from intelligent_project_analyzer.advisor.object_gateway import ObjectGateway
from intelligent_project_analyzer.advisor.gate import MVPGate, GateError
from intelligent_project_analyzer.advisor.models import Project, AdvisorActionDraft


def _draft(project_id="proj-1", actor="user-1", action="create_project_base_patch",
           payload=None) -> AdvisorActionDraft:
    return AdvisorActionDraft(
        draft_id="d-001", project_id=project_id, trace_id="t-001",
        actor=actor, action=action,
        payload=payload or {"name": "HAY 七里坪"},
        created_at=datetime.utcnow(),
    )


@pytest.fixture
def setup():
    engine = init_db("sqlite:///:memory:")
    with get_session(engine) as session:
        gw = ObjectGateway(session)
        gate = MVPGate(gw)
        project = Project(
            project_id="proj-1", name="HAY 七里坪", object_state="draft",
            created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
        )
        gw.save_project(project)
        yield gate, gw


def test_schema_check_fails_on_empty_payload(setup):
    """红线：Draft 缺必填字段返回 422"""
    gate, _ = setup
    draft = _draft(payload={})
    result = gate.run(draft, actor="user-1")
    assert not result.passed
    assert any(e.code == 422 for e in result.errors)


def test_permission_check_fails_for_unknown_actor(setup):
    """权限校验：未知 actor 返回 403"""
    gate, _ = setup
    draft = _draft(actor="unknown-user")
    result = gate.run(draft, actor="unknown-user")
    assert not result.passed
    assert any(e.code == 403 for e in result.errors)


def test_object_state_check_fails_on_frozen(setup):
    """红线：冻结对象直写返回 409"""
    gate, gw = setup
    gw.update_project_state("proj-1", "frozen")
    draft = _draft()
    result = gate.run(draft, actor="user-1")
    assert not result.passed
    assert any(e.code == 409 for e in result.errors)


def test_object_state_not_changed_on_gate_failure(setup):
    """红线：Gate 阻断后对象状态不变"""
    gate, gw = setup
    gw.update_project_state("proj-1", "frozen")
    draft = _draft()
    gate.run(draft, actor="user-1")
    # 状态仍为 frozen，Gate 失败不改变对象状态
    assert gw.get_project("proj-1").object_state == "frozen"


def test_confirmation_required_returns_202(setup):
    """需要确认时返回 202 + pending_confirmation"""
    gate, _ = setup
    draft = _draft()
    result = gate.run(draft, actor="user-1")
    # schema OK, permission OK, state OK → needs confirmation
    assert result.needs_confirmation is True
    assert result.response_code == 202


def test_valid_payload_passes_schema_check(setup):
    """包含 name 字段的 payload 通过 schema 校验"""
    gate, _ = setup
    draft = _draft(payload={"name": "HAY 七里坪"})
    result = gate.run(draft, actor="user-1")
    assert not any(e.code == 422 for e in result.errors)
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
python -m pytest ../tests/advisor/test_gate.py -v
```
期望：ImportError。

- [ ] **Step 3: 创建 `intelligent_project_analyzer/advisor/gate.py`**

```python
from dataclasses import dataclass, field
from intelligent_project_analyzer.advisor.models import AdvisorActionDraft
from intelligent_project_analyzer.advisor.object_gateway import ObjectGateway

# Phase A 允许的 actor（简化，Phase B+ 接入真实权限系统）
_ALLOWED_ACTORS = {"user-1", "user-demo", "advisor", "system"}


@dataclass
class GateCheckError:
    code: int
    message: str


@dataclass
class GateResult:
    passed: bool = False
    errors: list[GateCheckError] = field(default_factory=list)
    needs_confirmation: bool = False
    response_code: int = 200


class MVPGate:
    """写路径前的 4 项同步校验。失败不改变对象状态。"""

    def __init__(self, gateway: ObjectGateway):
        self._gw = gateway

    def run(self, draft: AdvisorActionDraft, actor: str) -> GateResult:
        errors: list[GateCheckError] = []

        # 1. schema_check
        if not draft.payload.get("name"):
            errors.append(GateCheckError(422, "payload.name 是必填字段"))

        # 2. permission_check
        if actor not in _ALLOWED_ACTORS:
            errors.append(GateCheckError(403, f"actor '{actor}' 无权限执行此操作"))

        # 3. object_state_check
        project = self._gw.get_project(draft.project_id)
        if project and project.object_state == "frozen":
            errors.append(GateCheckError(409, f"Project {draft.project_id} 已冻结，拒绝写入"))

        if errors:
            return GateResult(passed=False, errors=errors)

        # 4. confirmation_required_check — Phase A 所有写操作都需要确认
        return GateResult(
            passed=True,
            errors=[],
            needs_confirmation=True,
            response_code=202,
        )
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
python -m pytest ../tests/advisor/test_gate.py -v
```
期望：6 tests passing。

- [ ] **Step 5: Commit**

```bash
git add intelligent_project_analyzer/advisor/gate.py tests/advisor/test_gate.py
git commit -m "feat: add MVPGate with red-line tests (422/403/409)"
```

---

## Task 8: CommandHandler + AuditLog

**Files:**
- Create: `intelligent_project_analyzer/advisor/command_handler.py`
- Create: `tests/advisor/test_command_handler.py`

- [ ] **Step 1: 写 CommandHandler 测试**

新建 `tests/advisor/test_command_handler.py`：

```python
import pytest
from datetime import datetime
from intelligent_project_analyzer.advisor.database import init_db, get_session
from intelligent_project_analyzer.advisor.object_gateway import ObjectGateway
from intelligent_project_analyzer.advisor.gate import MVPGate
from intelligent_project_analyzer.advisor.state_transition import StateTransitionService
from intelligent_project_analyzer.advisor.command_handler import CommandHandler
from intelligent_project_analyzer.advisor.models import Project, AdvisorActionDraft


@pytest.fixture
def handler():
    engine = init_db("sqlite:///:memory:")
    with get_session(engine) as session:
        gw = ObjectGateway(session)
        gate = MVPGate(gw)
        svc = StateTransitionService(gw)
        project = Project(
            project_id="proj-1", name="HAY 七里坪", object_state="draft",
            created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
        )
        gw.save_project(project)
        yield CommandHandler(gw, gate, svc), gw


def _draft():
    return AdvisorActionDraft(
        draft_id="d-001", project_id="proj-1", trace_id="trace-001",
        actor="user-1", action="create_project_base_patch",
        payload={"name": "HAY 七里坪"},
        created_at=datetime.utcnow(),
    )


def test_execute_creates_patch(handler):
    ch, gw = handler
    result = ch.execute(_draft())
    assert result.execution_state == "succeeded"
    ticket = gw.get_ticket(result.ticket_id)
    assert ticket is not None
    assert ticket.execution_state == "succeeded"


def test_execute_writes_audit_log(handler):
    ch, gw = handler
    ch.execute(_draft())
    logs = gw.get_audit_log("proj-1")
    assert len(logs) >= 1
    assert logs[-1].result == "success"
    assert logs[-1].trace_id == "trace-001"


def test_execute_trace_id_in_ticket(handler):
    """trace_id 贯穿：ticket 携带 trace_id"""
    ch, gw = handler
    result = ch.execute(_draft())
    ticket = gw.get_ticket(result.ticket_id)
    assert ticket.trace_id == "trace-001"


def test_frozen_object_not_written(handler):
    """红线：冻结对象 Gate 阻断后不写 Patch"""
    ch, gw = handler
    gw.update_project_state("proj-1", "frozen")
    with pytest.raises(PermissionError):
        ch.execute(_draft())
    # 确认没有 Patch 写入
    logs = gw.get_audit_log("proj-1")
    assert all(log.result == "failure" for log in logs)
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
python -m pytest ../tests/advisor/test_command_handler.py -v
```
期望：ImportError。

- [ ] **Step 3: 创建 `intelligent_project_analyzer/advisor/command_handler.py`**

```python
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
                raise ValueError(f"Validation error: {first_error.message}")

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
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
python -m pytest ../tests/advisor/test_command_handler.py -v
```
期望：4 tests passing。

- [ ] **Step 5: Commit**

```bash
git add intelligent_project_analyzer/advisor/command_handler.py \
        tests/advisor/test_command_handler.py
git commit -m "feat: add CommandHandler with AuditLog and trace_id"
```

---

## Task 9: AdvisorAgent LangGraph 子图

**Files:**
- Create: `intelligent_project_analyzer/workflow/advisor_workflow.py`

- [ ] **Step 1: 创建 `intelligent_project_analyzer/workflow/advisor_workflow.py`**

```python
"""AdvisorAgent LangGraph 子图。

独立于 main_workflow.py，不修改现有节点。
LangGraph Command 只用于节点路由，不承担对象写入。
所有对象读取必须经 ObjectGateway，禁止节点直接查 DB。
"""
from typing import Any, Optional, TypedDict
import uuid
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from intelligent_project_analyzer.advisor.database import init_db, get_session
from intelligent_project_analyzer.advisor.object_gateway import ObjectGateway
from intelligent_project_analyzer.advisor.skill_registry import SkillRegistry
from intelligent_project_analyzer.advisor.skills.requirement_structuring import (
    RequirementStructuringSkill, SkillInput,
)
from intelligent_project_analyzer.advisor.gate import MVPGate
from intelligent_project_analyzer.advisor.command_handler import CommandHandler
from intelligent_project_analyzer.advisor.state_transition import StateTransitionService
from intelligent_project_analyzer.advisor.models import AdvisorActionDraft


class AdvisorState(TypedDict):
    project_id: str
    trace_id: str
    session_id: str
    user_message: str
    module: str
    user_action: str
    dispatch_level: str
    # 节点输出
    skill_output: Optional[dict]
    action_draft: Optional[dict]
    confirmed: bool
    ticket_id: Optional[str]
    error: Optional[str]
    # 最终 ViewModel 字段
    bound_object_id: Optional[str]
    object_state: Optional[str]
    object_version: Optional[str]
    evidence_status: Optional[str]
    judgment_content: Optional[str]
    judgment_confidence: Optional[str]
    action_chips: Optional[list]
    activated_capabilities: Optional[list]


def _make_advisor_graph(db_url: str = "sqlite:///advisor_objects.db"):
    engine = init_db(db_url)
    registry = SkillRegistry()

    def read_context_node(state: AdvisorState) -> dict:
        with get_session(engine) as session:
            gw = ObjectGateway(session)
            project = gw.get_project(state["project_id"])
            ctx = gw.get_project_context(state["project_id"])
        return {
            "bound_object_id": state["project_id"],
            "object_state": project.object_state if project else "draft",
            "object_version": project.object_version if project else "0.1.0",
        }

    def run_skill_node(state: AdvisorState) -> dict:
        skill = RequirementStructuringSkill(registry)
        inp = SkillInput(
            project_id=state["project_id"],
            raw_description=state["user_message"],
        )
        output = skill.run(inp)
        return {
            "skill_output": output.model_dump(),
            "evidence_status": output.evidence_status,
            "judgment_content": _build_judgment(output),
            "judgment_confidence": output.confidence,
        }

    def generate_draft_node(state: AdvisorState) -> dict:
        chips = _build_chips(state)
        capabilities = [
            {"type": "ontology", "name": "本体论", "status": "placeholder",
             "summary": "Phase A2 接入后生效"},
            {"type": "methodology", "name": "方法论", "status": "placeholder",
             "summary": "Phase A2 接入后生效"},
            {"type": "knowledge", "name": "知识库", "status": "placeholder",
             "summary": "Phase A2 接入后生效"},
        ]
        return {
            "action_chips": chips,
            "activated_capabilities": capabilities,
        }

    def build_advisor_graph() -> StateGraph:
        graph = StateGraph(AdvisorState)
        graph.add_node("read_context", read_context_node)
        graph.add_node("run_skill", run_skill_node)
        graph.add_node("generate_draft", generate_draft_node)
        graph.set_entry_point("read_context")
        graph.add_edge("read_context", "run_skill")
        graph.add_edge("run_skill", "generate_draft")
        graph.add_edge("generate_draft", END)
        return graph

    return build_advisor_graph().compile(checkpointer=MemorySaver())


def _build_judgment(output) -> str:
    if output.confidence == "low":
        return "输入信息不足，无法生成有效判断。请补充关键信息后重试。"
    parts = []
    sd = output.structured_data
    if sd.get("project_type"):
        parts.append(f"项目类型：{sd['project_type']}")
    if sd.get("location"):
        parts.append(f"地点：{sd['location']}")
    if output.missing_fields:
        parts.append(f"缺失信息：{', '.join(output.missing_fields)}")
    return "；".join(parts) if parts else "需求已初步结构化，请查看建议行动。"


def _build_chips(state: AdvisorState) -> list:
    skill_out = state.get("skill_output", {})
    missing = skill_out.get("missing_fields", [])
    chips = []
    if missing:
        chips.append({
            "type": "ask",
            "label": f"补充 {len(missing)} 个关键信息",
            "isPrimary": True,
            "payload": {"question": f"请补充以下信息：{', '.join(missing)}"},
        })
    chips.append({
        "type": "fill",
        "label": "保存项目方向草案",
        "isPrimary": not chips,
        "payload": {"formId": "project-base-draft"},
    })
    return chips


# 全局单例（生产使用）
_advisor_app = None


def get_advisor_app(db_url: str = "sqlite:///advisor_objects.db"):
    global _advisor_app
    if _advisor_app is None:
        _advisor_app = _make_advisor_graph(db_url)
    return _advisor_app


def run_advisor(project_id: str, trace_id: str, session_id: str,
                user_message: str, module: str = "project_base",
                db_url: str = "sqlite:///advisor_objects.db") -> dict:
    app = get_advisor_app(db_url)
    initial_state = AdvisorState(
        project_id=project_id, trace_id=trace_id, session_id=session_id,
        user_message=user_message, module=module,
        user_action="ask", dispatch_level="L1",
        skill_output=None, action_draft=None, confirmed=False,
        ticket_id=None, error=None,
        bound_object_id=None, object_state=None, object_version=None,
        evidence_status=None, judgment_content=None, judgment_confidence=None,
        action_chips=None, activated_capabilities=None,
    )
    config = {"configurable": {"thread_id": session_id}}
    result = app.invoke(initial_state, config=config)
    return result
```

- [ ] **Step 2: 冒烟测试（mock LLM）**

```bash
python -c "
import os
os.environ['OPENAI_API_KEY'] = 'sk-test'
from unittest.mock import patch, MagicMock
mock_resp = MagicMock()
mock_resp.content = '{\"project_type\": \"民宿\", \"confidence\": \"medium\", \"missing_fields\": [\"面积\"]}'
with patch('intelligent_project_analyzer.services.llm_factory.LLMFactory.create_llm') as mock_factory:
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = mock_resp
    mock_factory.return_value = mock_llm
    from intelligent_project_analyzer.workflow.advisor_workflow import run_advisor
    result = run_advisor('proj-test', 'trace-001', 'session-001', '山地民宿设计', db_url='sqlite:///:memory:')
    print('object_state:', result.get('object_state'))
    print('evidence_status:', result.get('evidence_status'))
    print('chips:', result.get('action_chips'))
"
```
期望：打印 object_state, evidence_status 和 chips 列表（无报错）。

- [ ] **Step 3: Commit**

```bash
git add intelligent_project_analyzer/workflow/advisor_workflow.py
git commit -m "feat: add AdvisorAgent LangGraph subgraph"
```

---

## Task 10: FastAPI 路由

**Files:**
- Create: `intelligent_project_analyzer/api/advisor_routes.py`
- Modify: `intelligent_project_analyzer/api/server.py`（注册路由）
- Create: `tests/advisor/test_api.py`

- [ ] **Step 1: 写 API 测试**

新建 `tests/advisor/test_api.py`：

```python
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from intelligent_project_analyzer.api.advisor_routes import router
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def _mock_advisor_result():
    return {
        "project_id": "proj-1", "trace_id": "trace-001", "session_id": "sess-1",
        "user_message": "民宿设计", "module": "project_base",
        "user_action": "ask", "dispatch_level": "L1",
        "bound_object_id": "proj-1", "object_state": "draft", "object_version": "0.1.0",
        "evidence_status": "internal_hint",
        "judgment_content": "项目类型：民宿；缺失信息：面积",
        "judgment_confidence": "medium",
        "action_chips": [{"type": "ask", "label": "补充信息", "isPrimary": True,
                          "payload": {"question": "面积是多少？"}}],
        "activated_capabilities": [
            {"type": "ontology", "name": "本体论", "status": "placeholder", "summary": ""}
        ],
        "skill_output": {}, "action_draft": None, "confirmed": False,
        "ticket_id": None, "error": None,
    }


@patch("intelligent_project_analyzer.api.advisor_routes.run_advisor")
def test_post_intents_returns_200(mock_run):
    mock_run.return_value = _mock_advisor_result()
    response = client.post("/v1/advisor/intents", json={
        "project_id": "proj-1", "trace_id": "trace-001",
        "scene_context": {"module": "project_base", "user_action": "ask", "dispatch_level": "L1"},
        "message": "民宿设计",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["trace_id"] == "trace-001"
    assert data["object_state"] == "draft"
    assert data["evidence_status"] == "internal_hint"


@patch("intelligent_project_analyzer.api.advisor_routes.run_advisor")
def test_response_has_action_chips(mock_run):
    mock_run.return_value = _mock_advisor_result()
    response = client.post("/v1/advisor/intents", json={
        "project_id": "proj-1", "trace_id": "trace-001",
        "scene_context": {"module": "project_base", "user_action": "ask", "dispatch_level": "L1"},
        "message": "民宿",
    })
    data = response.json()
    assert len(data["action_chips"]) >= 1


def test_missing_project_id_returns_422():
    response = client.post("/v1/advisor/intents", json={
        "trace_id": "trace-001",
        "scene_context": {"module": "project_base", "user_action": "ask", "dispatch_level": "L1"},
        "message": "民宿",
    })
    assert response.status_code == 422


def test_post_project_returns_201():
    from intelligent_project_analyzer.api import advisor_routes
    from intelligent_project_analyzer.advisor.database import init_db
    test_engine = init_db("sqlite:///:memory:")
    original = advisor_routes._engine
    advisor_routes._engine = test_engine
    try:
        response = client.post("/v1/projects", json={"name": "测试项目"})
        assert response.status_code == 201
        assert "project_id" in response.json()
    finally:
        advisor_routes._engine = original
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
python -m pytest ../tests/advisor/test_api.py -v
```
期望：ImportError。

- [ ] **Step 3: 创建 `intelligent_project_analyzer/api/advisor_routes.py`**

```python
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
        except (PermissionError, ValueError) as e:
            raise HTTPException(status_code=409, detail=str(e))
    return {"ticket_id": ticket.ticket_id, "execution_state": ticket.execution_state}


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
```

- [ ] **Step 4: 注册路由到 server.py**

在 `intelligent_project_analyzer/api/server.py` 中找到最后一个 `app.include_router` 调用（约第 996 行附近），在其后添加：

```python
from intelligent_project_analyzer.api.advisor_routes import router as advisor_router
# ... 在 include_router 列表末尾添加：
app.include_router(advisor_router)
```

- [ ] **Step 5: 运行 API 测试**

```bash
python -m pytest ../tests/advisor/test_api.py -v
```
期望：前 3 个测试通过（mock run_advisor），第 4 个可能需要调整 mock 写法。

- [ ] **Step 6: Commit**

```bash
git add intelligent_project_analyzer/api/advisor_routes.py \
        intelligent_project_analyzer/api/server.py \
        tests/advisor/test_api.py
git commit -m "feat: add advisor FastAPI routes (POST /v1/advisor/intents + CRUD)"
```

---

## Task 11: trace_id 回放测试 + Phase A 硬验收

**Files:**
- Create: `tests/advisor/test_trace_id.py`

- [ ] **Step 1: 创建 `tests/advisor/test_trace_id.py`**

```python
"""trace_id 回放测试：单次请求 trace_id 必须出现在 4 处。

Phase A 硬验收：
□ 所有写操作必须产生 AuditLog
□ Draft 对象缺必填字段返回 422
□ 非法状态迁移返回 409
□ 冻结对象直写、Gate 阻断、越权调用必须有失败用例
"""
import pytest
import uuid
from datetime import datetime
from intelligent_project_analyzer.advisor.database import init_db, get_session
from intelligent_project_analyzer.advisor.object_gateway import ObjectGateway
from intelligent_project_analyzer.advisor.gate import MVPGate
from intelligent_project_analyzer.advisor.state_transition import StateTransitionService, InvalidStateTransitionError
from intelligent_project_analyzer.advisor.command_handler import CommandHandler
from intelligent_project_analyzer.advisor.models import Project, AdvisorActionDraft


@pytest.fixture
def full_stack():
    engine = init_db("sqlite:///:memory:")
    with get_session(engine) as session:
        gw = ObjectGateway(session)
        gate = MVPGate(gw)
        state_svc = StateTransitionService(gw)
        ch = CommandHandler(gw, gate, state_svc)
        project = Project(
            project_id="proj-trace", name="Trace Test",
            created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
        )
        gw.save_project(project)
        yield ch, gw, state_svc


def _draft(trace_id: str) -> AdvisorActionDraft:
    return AdvisorActionDraft(
        draft_id=str(uuid.uuid4()),
        project_id="proj-trace",
        trace_id=trace_id,
        actor="user-1",
        action="create_project_base_patch",
        payload={"name": "Trace Test"},
        created_at=datetime.utcnow(),
    )


def test_trace_id_in_ticket(full_stack):
    """trace_id 必须出现在 SyncExecutionTicket 中"""
    ch, gw, _ = full_stack
    trace_id = f"trace-{uuid.uuid4().hex[:8]}"
    ticket = ch.execute(_draft(trace_id))
    stored = gw.get_ticket(ticket.ticket_id)
    assert stored.trace_id == trace_id


def test_trace_id_in_audit_log(full_stack):
    """trace_id 必须出现在 AuditLogEntry 中"""
    ch, gw, _ = full_stack
    trace_id = f"trace-{uuid.uuid4().hex[:8]}"
    ch.execute(_draft(trace_id))
    logs = gw.get_audit_log("proj-trace")
    assert any(log.trace_id == trace_id for log in logs)


def test_audit_log_written_on_success(full_stack):
    """所有写操作必须产生 AuditLog（Phase A 硬验收）"""
    ch, gw, _ = full_stack
    before = len(gw.get_audit_log("proj-trace"))
    ch.execute(_draft("trace-x"))
    after = len(gw.get_audit_log("proj-trace"))
    assert after > before


def test_audit_log_written_on_failure(full_stack):
    """Gate 阻断时也必须产生失败 AuditLog"""
    ch, gw, _ = full_stack
    gw.update_project_state("proj-trace", "frozen")
    before = len(gw.get_audit_log("proj-trace"))
    with pytest.raises(PermissionError):
        ch.execute(_draft("trace-fail"))
    after = len(gw.get_audit_log("proj-trace"))
    assert after > before
    logs = gw.get_audit_log("proj-trace")
    assert logs[-1].result == "failure"


# ── Phase A 硬验收：架构红线汇总 ──────────────────────────────────

def test_hardgate_frozen_write_rejected(full_stack):
    """硬验收：冻结对象直写返回 409"""
    ch, gw, _ = full_stack
    gw.update_project_state("proj-trace", "frozen")
    with pytest.raises(PermissionError) as exc:
        ch.execute(_draft("trace-frozen"))
    assert "frozen" in str(exc.value).lower() or "Gate blocked" in str(exc.value)


def test_hardgate_schema_missing_name(full_stack):
    """硬验收：Draft 缺必填字段 name 返回 422"""
    ch, gw, _ = full_stack
    # 重置状态
    gw.update_project_state("proj-trace", "draft")
    bad_draft = AdvisorActionDraft(
        draft_id=str(uuid.uuid4()), project_id="proj-trace",
        trace_id="trace-422", actor="user-1",
        action="create_project_base_patch",
        payload={},  # 缺少 name
        created_at=datetime.utcnow(),
    )
    with pytest.raises(ValueError) as exc:
        ch.execute(bad_draft)
    assert "422" in str(exc.value)


def test_hardgate_unauthorized_actor(full_stack):
    """硬验收：跨域越权调用返回 403"""
    ch, gw, _ = full_stack
    gw.update_project_state("proj-trace", "draft")
    unauthorized_draft = AdvisorActionDraft(
        draft_id=str(uuid.uuid4()), project_id="proj-trace",
        trace_id="trace-403", actor="hacker",
        action="create_project_base_patch",
        payload={"name": "hack"},
        created_at=datetime.utcnow(),
    )
    with pytest.raises(PermissionError):
        ch.execute(unauthorized_draft)


def test_hardgate_illegal_state_transition(full_stack):
    """硬验收：非法状态迁移返回 409"""
    _, gw, state_svc = full_stack
    gw.update_project_state("proj-trace", "frozen")
    with pytest.raises(InvalidStateTransitionError) as exc:
        state_svc.transition("proj-trace", "draft")
    assert exc.value.status_code == 409
```

- [ ] **Step 2: 运行全部 advisor 测试**

```bash
python -m pytest ../tests/advisor/ -v
```
期望：所有测试通过，Phase A 硬验收 8 项全绿。

- [ ] **Step 3: 运行全量测试，确认无回归**

```bash
python -m pytest ../tests/ -v --ignore=../tests/advisor/test_api.py 2>&1 | tail -20
```

- [ ] **Step 4: Commit**

```bash
git add tests/advisor/test_trace_id.py
git commit -m "test: trace_id replay tests + Phase A hard acceptance validation"
```

---

## Task 12: 全链路验收

- [ ] **Step 1: 运行全部后端 advisor 测试**

```bash
python -m pytest ../tests/advisor/ -v --tb=short
```
期望：全部通过，包含以下红线验证：
```
PASSED tests/advisor/test_state_transition.py::test_frozen_to_draft_raises_409
PASSED tests/advisor/test_gate.py::test_object_state_check_fails_on_frozen
PASSED tests/advisor/test_gate.py::test_object_state_not_changed_on_gate_failure
PASSED tests/advisor/test_trace_id.py::test_hardgate_frozen_write_rejected
PASSED tests/advisor/test_trace_id.py::test_hardgate_schema_missing_name
PASSED tests/advisor/test_trace_id.py::test_hardgate_unauthorized_actor
PASSED tests/advisor/test_trace_id.py::test_hardgate_illegal_state_transition
PASSED tests/advisor/test_trace_id.py::test_audit_log_written_on_failure
```

- [ ] **Step 2: 运行前端测试**

```bash
cd frontend-nextjs
npx jest --verbose
```
期望：AdvisorPanel 10 项 + mockAdvisorViewModel 7 项全部通过。

- [ ] **Step 3: Phase A 硬验收检查表**

对照以下检查表，逐项确认：

```
□ AdvisorAgent 调用 Skill 必须从 SkillManifest 选取
  → test_skill.py::test_skill_registered_in_manifest ✓

□ 所有写操作必须产生 AuditLog
  → test_trace_id.py::test_audit_log_written_on_success ✓

□ Draft 对象缺必填字段返回 422
  → test_trace_id.py::test_hardgate_schema_missing_name ✓

□ 非法状态迁移返回 409
  → test_state_transition.py::test_frozen_to_draft_raises_409 ✓
  → test_state_transition.py::test_draft_to_frozen_raises_409 ✓

□ 右侧高参席展示 bound_object_id / object_state / evidence_status
  → AdvisorPanel.test.tsx (Phase A1) ✓

□ 任一请求可凭 trace_id 回放到 Ticket + AuditLog
  → test_trace_id.py::test_trace_id_in_ticket ✓
  → test_trace_id.py::test_trace_id_in_audit_log ✓

□ 冻结对象直写被拒绝
  → test_trace_id.py::test_hardgate_frozen_write_rejected ✓

□ 跨域越权调用被拒绝
  → test_trace_id.py::test_hardgate_unauthorized_actor ✓
```

- [ ] **Step 4: 最终 Commit**

```bash
git add .
git commit -m "feat: Phase A 系统升级完成 — 前端A1 + 后端工程地基全链路"
```

---

## Phase A2 接入点备忘

Phase A 完成后，Phase A2 只需 2 处改动：

**前端 `page.tsx`（handleAsk 函数）：**
```typescript
// 将注释替换为：
const response = await fetch('/v1/advisor/intents', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'X-Trace-Id': traceId },
  body: JSON.stringify({ project_id: projectId, trace_id: traceId,
    scene_context: sceneRef, message: text }),
});
setViewModel(await response.json());
```

**后端 `advisor_workflow.py`（`run_advisor` 函数）：**
- 在 `read_context_node` 中增加真实 ProjectContext 保存逻辑
- 在 `run_skill_node` 中将结构化输出写回 ObjectGateway

类型层、组件结构、所有测试**不需要改动**。
