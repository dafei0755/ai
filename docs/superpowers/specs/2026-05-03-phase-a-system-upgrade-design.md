# Phase A 系统升级设计规范

日期：2026-05-03
范围：Phase A1（前端 AdvisorPanel 五区重写）+ Phase A 后端工程地基
上位文档：`sf/2026.4.18/9 系统架构/02-方案高参系统母架构-2026-05-02.md` v2.5

---

## 1. 目标

在现有 LangGraph 工作流基础上，叠加母架构对象链，交付 Day 1 最小可演示闭环：

```
用户输入项目描述
→ AdvisorAgent 读取 Project / ProjectContext（经 ObjectGateway）
→ 调用需求结构化 Skill（从 SkillManifest 选取）
→ 返回 AdvisorViewModel（bound_object_id + object_state + evidence_status）
→ 用户点击"创建草案" → 生成 AdvisorActionDraft
→ 用户确认 → MVP Gate 校验
→ 生成 SyncExecutionTicket → CommandHandler 写入 ProjectBasePatch(draft)
→ 写入 AuditLog
```

---

## 2. 架构总览与边界划定

### 2.1 现有代码定位

| 现有模块 | 定位 | 操作 |
|---|---|---|
| `intelligent_project_analyzer` 全量 | 项目底盘需求采集与分析原型 | 保留，不纳入 Phase A 主链路 |
| `StateGraph / main_workflow.py` | AdvisorAgent 编排引擎基础设施 | 增加 advisor 子图，不重写现有节点 |
| `AnalysisStage` 枚举 | 工作流内部阶段，与 ObjectState 隔离 | 加注释防混用，测试验证无交叉 |
| `CheckPointer` (SqliteSaver) | 会话上下文 / 中间产物持久化 | 不作为命名对象真相源 |
| `interrupt` 机制 | 映射为 UserConfirmation 入口 | 直接复用 |
| `LangGraph Command` | 只用于节点路由 | 禁止承担对象写入，加门控注释 |

### 2.2 新增层

```
前端 (Phase A1)                  后端 (Phase A)
────────────────────             ──────────────────────────────────
types/advisor.ts                 核心对象 Pydantic 模型
AdvisorPanel.tsx（五区）          ObjectState + StateTransitionService
mock/mockData.ts 更新             ObjectGateway
page.tsx 接线                     SkillManifest YAML + 需求结构化 Skill
AdvisorPanel 单元测试              MVP Gate（4 项校验）
                                  CommandHandler
                                  SyncExecutionTicket
                                  AuditLog
                                  POST /v1/advisor/intents + CRUD 端点
```

### 2.3 不做（Phase A 范围外）

- 多 Agent 协作
- ExternalConnector / 外部 API 接入
- AsyncExecutionTicket
- 完整合规 Gate（compliance / business_constraint / impact / stakeholder）
- Control Plane 独立平台
- AlignedBrief 冻结写入（Phase B）
- ProjectBasePatch → AlignedBrief v1 写入链（Phase B）

---

## 3. 前端组件（Phase A1）

### 3.1 文件变更清单

| 文件 | 操作 | 说明 |
|---|---|---|
| `frontend-nextjs/types/advisor.ts` | 新建 | AdvisorViewModel 完整 TypeScript 类型 |
| `frontend-nextjs/components/project-cockpit/AdvisorPanel.tsx` | 重写 | 五区结构，接受 AdvisorViewModel props |
| `frontend-nextjs/components/project-cockpit/mock/mockData.ts` | 更新 | 新增 MOCK_ADVISOR_VIEW_MODEL，移除旧 ADVISOR_OUTPUT |
| `frontend-nextjs/app/project-cockpit/[projectId]/page.tsx` | 更新 | 接线 sceneRef / viewModel，navigate Chip 路由逻辑 |
| `frontend-nextjs/__tests__/AdvisorPanel.test.tsx` | 新建 | 10 项单元测试 |
| `frontend-nextjs/__tests__/mockAdvisorViewModel.test.ts` | 新建 | mock 数据结构验证测试 |

### 3.2 AdvisorViewModel 类型（`types/advisor.ts`）

```typescript
export type AdvisorModule =
  | 'project_base' | 'floor_plan' | 'scheme_canvas'
  | 'resource_radar' | 'silicon_avatar' | 'knowledge_hub';

export type AdvisorObjectType =
  | 'project' | 'space' | 'brief' | 'spg' | 'floor_plan_pack'
  | 'layout_variant' | 'concept_canvas' | 'placement_canvas'
  | 'resource_candidate' | 'decision_log' | 'preference_rule';

export interface SceneRef {
  projectId: string;
  sessionId: string;
  module: AdvisorModule;
  view?: string;
  objectId?: string;
  objectType?: AdvisorObjectType;
  userAction: 'view' | 'edit' | 'select' | 'navigate_in' | 'ask' | 'confirm' | 'upload';
  dispatchLevel: 'L0' | 'L1' | 'L2' | 'L3';
}

export type ActionChip =
  | { type: 'ask';      label: string; isPrimary: boolean; payload: { question: string } }
  | { type: 'navigate'; label: string; isPrimary: boolean; payload: { target: AdvisorModule; objectId?: string } }
  | { type: 'fill';     label: string; isPrimary: boolean; payload: { formId: string; fieldId?: string } }
  | { type: 'freeze';   label: string; isPrimary: boolean; payload: { draftId: string } }
  | { type: 'backfill'; label: string; isPrimary: boolean; payload: { sourceObjectId: string; targetModule: AdvisorModule } }
  | { type: 'compare';  label: string; isPrimary: boolean; payload: { objectIdA: string; objectIdB: string } };

export interface AdvisorJudgment {
  content: string;
  confidence: 'high' | 'medium' | 'low';
  evidence: {
    evidenceClass: 'none' | 'internal_reasoning' | 'knowledge_base' | 'case_validated' | 'standard_verified';
    verificationState: 'unverified' | 'pending_registry' | 'registered' | 'expert_confirmed';
  };
  sourceParts: { ontology?: string; methodology?: string; knowledge?: string; userHistory?: string };
  cannotDo?: { reason: string; blockedChipTypes?: ActionChip['type'][] }[];
}

export interface ActivatedCapability {
  type: 'ontology' | 'methodology' | 'knowledge' | 'evidence' | 'user_history';
  name: string;
  status: 'active' | 'pending' | 'unavailable' | 'placeholder';
  summary: string;
  sourceId?: string;
}

export interface CarriedConstraint {
  sourceObjectId: string;
  sourceObjectType: string;
  targetModule: AdvisorModule;
  constraints: {
    label: string;
    value: string;
    strength: 'hard' | 'soft' | 'hint';
    source: 'brief' | 'spg' | 'ontology' | 'methodology' | 'user_confirmed';
  }[];
}

export interface AdvisorViewModel {
  traceId: string;
  generatedAt: string;
  sceneContext: SceneRef;
  boundObjectId?: string;
  objectState?: 'draft' | 'pending_confirmation' | 'frozen' | 'stale' | 'forked' | 'archived';
  objectVersion?: string;
  judgment: AdvisorJudgment;
  evidenceStatus: 'none' | 'internal_hint' | 'verified';
  activatedCapabilities: ActivatedCapability[];
  actionChips: ActionChip[];
  carriedConstraints?: CarriedConstraint[];
}
```

### 3.3 AdvisorPanel 五区布局

```
┌─────────────────────────────────────┐
│ ① 标题栏：方案高参 · 模块 · 状态 + evidenceStatus 徽章  │  固定
├─────────────────────────────────────┤
│ ② 判断区：无对话→判断文本；有对话→摘要条+对话历史      │  可滚动
├─────────────────────────────────────┤
│ ③ ActionChip 区：主 Chip（蓝底）+ 次 Chip×≤2 + cannotDo │  固定
├─────────────────────────────────────┤
│ ④ 已激活能力（Phase A1 全部 placeholder，纯展示）        │  固定
├─────────────────────────────────────┤
│ ⑤ 输入框（textarea + Send 按钮）                         │  固定
└─────────────────────────────────────┘
```

Phase A1 ActionChip 行为：
- `ask` → 填入输入框，不调用 onChipAction
- `navigate` / `fill` → 调用 onChipAction，路由逻辑在 page.tsx
- `freeze` / `backfill` / `compare` → Phase A1 不渲染

### 3.4 Phase A2 接入点（预留）

Phase A1 完成后，Phase A2 只需在 `page.tsx` handleAsk 中：
```typescript
// 替换 mock → 真实 API
const response = await fetch('/v1/advisor/intents', {
  method: 'POST',
  body: JSON.stringify({ sceneContext: sceneRef, message: text }),
});
setViewModel(await response.json());
```
类型层和组件结构不需要改动。

---

## 4. 后端对象模型

### 4.1 核心对象（Pydantic）

```python
ObjectState = Literal['draft', 'pending_confirmation', 'frozen', 'stale']

class Project(BaseModel):
    project_id: str
    name: str
    object_state: ObjectState = 'draft'
    object_version: str = '0.1.0'
    created_at: datetime
    updated_at: datetime

class ProjectContext(BaseModel):
    project_id: str
    raw_description: str
    structured_data: dict = {}
    evidence_status: Literal['none', 'internal_hint', 'verified'] = 'none'

class AlignedBrief(BaseModel):    # Phase A 占位，Phase B 完整写入
    project_id: str
    object_state: ObjectState = 'draft'
    content: dict = {}

class AdvisorActionDraft(BaseModel):
    draft_id: str
    project_id: str
    trace_id: str
    actor: str
    action: str
    payload: dict
    object_state: ObjectState = 'draft'
    created_at: datetime

class ProjectBasePatch(BaseModel):
    patch_id: str
    project_id: str
    draft_id: str
    content: dict
    object_state: Literal['draft', 'applied', 'discarded'] = 'draft'
    created_at: datetime

class SyncExecutionTicket(BaseModel):
    ticket_id: str
    trace_id: str
    draft_id: str
    actor: str
    action: str
    object_id: str
    object_version: str
    execution_state: Literal['pending','running','succeeded','failed','cancelled','timeout']
    created_at: datetime
    completed_at: datetime | None = None
    error: str | None = None

class AuditLogEntry(BaseModel):
    log_id: str
    trace_id: str
    ticket_id: str
    actor: str
    action: str
    object_id: str
    object_version_before: str
    object_version_after: str
    result: Literal['success', 'failure']
    detail: dict = {}
    created_at: datetime
```

### 4.2 ObjectState 迁移规则（Phase A 最小集）

| 当前状态 | 目标状态 | 触发条件 | 触发方 |
|---|---|---|---|
| `draft` | `pending_confirmation` | 用户提交确认请求 | 用户 / AdvisorAgent |
| `pending_confirmation` | `frozen` | MVP Gate 通过 + 用户确认 | 系统 + 用户 |
| `pending_confirmation` | `draft` | 用户撤回 | 用户 |
| `frozen` | `stale` | 上游对象升版 | Phase A 手动触发，Phase B+ SystemBus 自动 |

非法迁移（如 `frozen → draft`）返回 409。

### 4.3 存储策略

- Phase A 使用 SQLite（与现有 CheckPointer 共存，独立数据库文件 `advisor_objects.db`）
- 每类对象一张表，`object_id + object_version` 联合唯一索引
- `audit_log` 表 append-only，禁止 UPDATE / DELETE

---

## 5. Skill 层

### 5.1 SkillManifest（`config/skills/requirement_structuring.yaml`）

```yaml
skill_id: req_structuring_v1
skill_name: 需求结构化 Skill
skill_type: analysis
owner_domain: project_base
input_contract:
  required: [project_id, raw_description]
  optional: [context_hints]
output_contract:
  required: [structured_data, evidence_status, confidence]
  optional: [missing_fields, suggestions]
failure_modes:
  - llm_parse_error: retry_once_then_degrade
  - empty_input: return_422
execution_mode: sync
side_effect_level: none
timeout_ms: 30000
fallback_strategy: return_partial_with_low_confidence
version: "1.0.0"
```

### 5.2 Skill 约束红线

- 无状态、函数式、单次调用完成
- 输出必须经 Pydantic 结构化验证
- 不直接提交 Patch，只生成 PatchProposal
- 不持有外部密钥
- Phase A 不接 ExternalConnector

---

## 6. MVP Gate + CommandHandler

### 6.1 MVP Gate（4 项同步校验）

```python
class MVPGate:
    def run(self, draft: AdvisorActionDraft, actor: str) -> GateResult:
        checks = [
            self._schema_check(draft),
            self._permission_check(actor, draft),
            self._object_state_check(draft),
            self._confirmation_required_check(draft),
        ]
        failures = [c for c in checks if not c.passed]
        return GateResult(passed=not failures, errors=failures)
```

| 校验项 | 失败码 | 对象状态 |
|---|---|---|
| schema_check | 422 | 不变 |
| permission_check | 403 | 不变，写失败 AuditLog |
| object_state_check | 409 | 不变 |
| confirmation_required_check | 202 | → pending_confirmation |

### 6.2 Write Path

```
AdvisorActionDraft
  → MVPGate.run()                    同步阻塞
  → interrupt（UserConfirmation）      LangGraph interrupt
  → SyncExecutionTicket(pending→running)
  → ObjectWriter.write(ProjectBasePatch(draft))
  → DomainEvent 插入
  → AuditLogEntry 插入（append-only）
  → ticket.execution_state = succeeded
```

失败时：ticket → failed，AuditLog 记录失败，Project 状态不变，前端收到错误回显。

---

## 7. API 契约

### 7.1 主入口

```
POST /v1/advisor/intents

Request:
{
  "project_id": "string",
  "trace_id": "string",          // 前端生成 UUID
  "scene_context": {
    "module": "project_base",
    "user_action": "ask",
    "dispatch_level": "L1"
  },
  "message": "string"
}

Response 200:
{
  "trace_id": "string",
  "bound_object_id": "string",
  "object_state": "draft",
  "evidence_status": "internal_hint",
  "judgment": { "content": "...", "confidence": "medium", ... },
  "action_chips": [...],
  "activated_capabilities": [...]
}

Error (RFC 7807):
{
  "type": "/errors/object-state-conflict",
  "title": "Object is frozen",
  "status": 409,
  "detail": "..."
}
```

### 7.2 其他 Phase A 端点

| 端点 | 说明 |
|---|---|
| `POST /v1/projects` | 创建 Project |
| `GET /v1/projects/{id}` | 读取 Project + object_state |
| `POST /v1/projects/{id}/drafts` | 创建 AdvisorActionDraft |
| `POST /v1/projects/{id}/drafts/{draft_id}/confirm` | 用户确认，触发 CommandHandler |
| `GET /v1/tickets/{ticket_id}` | 查询 SyncExecutionTicket |
| `GET /v1/audit/{project_id}` | 查询 AuditLog |

### 7.3 trace_id 贯穿链路

`X-Trace-Id` 请求头 → LangGraph state → SkillManifest 调用记录 → SyncExecutionTicket → AuditLogEntry → 响应头。

---

## 8. LangGraph 对齐

### 8.1 AdvisorAgent 子图（新文件，不修改现有 main_workflow.py）

```python
# intelligent_project_analyzer/workflow/advisor_workflow.py

advisor_graph = StateGraph(AdvisorState)
advisor_graph.add_node("read_context",    read_project_context_node)
advisor_graph.add_node("run_skill",       run_requirement_structuring)
advisor_graph.add_node("generate_draft",  generate_action_draft_node)
advisor_graph.add_node("user_confirm",    interrupt_for_confirmation)
advisor_graph.add_node("command_handler", command_handler_node)
```

### 8.2 ObjectGateway

```python
class ObjectGateway:
    """LangGraph 节点访问命名对象的唯一入口。"""
    def get_project(self, project_id: str) -> Project: ...
    def get_project_context(self, project_id: str) -> ProjectContext: ...
    def get_aligned_brief(self, project_id: str) -> AlignedBrief | None: ...
```

### 8.3 边界红线

| 禁止行为 | 防护方式 |
|---|---|
| Command(update=...) 修改命名对象 | 注释 + 测试：Command 只做路由 |
| 节点直接写 DB | 所有写入必须经 CommandHandler |
| CheckPointer 作为 Project 真相源 | 测试：Project 状态从 ObjectGateway 读 |
| AnalysisStage 混用为 ObjectState | 类型隔离，测试验证无 import 交叉 |

---

## 9. 测试策略

### 9.1 四类测试

**1. 架构红线测试（最高优先级）**
- 冻结对象直写 → 409
- Skill 输出非结构化 → 422
- Gate 阻断 → 对象状态不变
- 跨域越权调用 → 403

**2. 对象状态迁移测试**
- draft → pending_confirmation → frozen 正向路径
- pending_confirmation → draft 撤回路径
- frozen 对象拒绝写入 → 409

**3. Skill 契约测试**
- 需求结构化 Skill 输入/输出符合 SkillManifest
- 空输入返回 422
- LLM 解析失败走 fallback（partial + low_confidence）

**4. trace_id 回放测试**
- 单次请求 trace_id 出现在 HTTP响应头 + SkillLog + ExecutionTicket + AuditLog（共 4 处）

**5. 前端测试（Phase A1，10 项）**
- AdvisorPanel 五区渲染、ActionChip 行为、prefillMessage、cannotDo

---

## 10. Phase A 硬验收标准

```
□ AdvisorAgent 调用 Skill 必须从 SkillManifest 选取
□ 所有写操作必须产生 AuditLog
□ Draft 对象缺必填字段返回 422
□ 非法状态迁移返回 409
□ 右侧高参席展示 bound_object_id / object_state / evidence_status
□ 任一请求可凭 trace_id 回放到输入、Skill、对象版本、执行记录和 AuditLog
□ 每条架构红线至少 1 个自动化测试
□ 冻结对象直写、Skill 输出非结构化、Gate 阻断、跨域越权调用必须有失败用例
```

---

## 11. 实施顺序

```
Week 1
  Day 1-2：前端 Phase A1（types → AdvisorPanel → mockData → page.tsx → 测试）
  Day 3-4：后端对象模型（Pydantic 类 + SQLite 表 + ObjectGateway）
  Day 5：  SkillManifest + 需求结构化 Skill（LLM 调用 + 输出结构化）

Week 2
  Day 1-2：MVP Gate + CommandHandler + SyncExecutionTicket + AuditLog
  Day 3：  AdvisorAgent 子图（advisor_workflow.py + LangGraph interrupt）
  Day 4：  API 端点（POST /v1/advisor/intents + CRUD）
  Day 5：  架构红线测试 + trace_id 回放测试 + 端到端验收
```
