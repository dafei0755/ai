# Phase A1：方案高参前端结构升级设计

日期：2026-05-03  
范围：Phase A1（前端可见闭环，mock 数据，不含后端实现）  
上位文档：`sf/2026.4.18/6 方案高参/01-方案高参升级定义与架构-2026-05-03.md` v2.2  
技术决策：`sf/2026.4.18/6 方案高参/12-TechStackADR-2026-05-03.md` v1.0

---

## 1. 目标

将 `AdvisorPanel.tsx` 从当前 mock 聊天模式升级为符合架构规范的五区结构，数据模型从 `AdvisorOutput` 替换为 `AdvisorViewModel`，为 Phase A2 后端接入建立干净的类型基础。

**不做（Phase A1 范围外）**：
- 后端 API 接入（`POST /v1/advisor/intents`）
- 真实 LLM 响应
- freeze / backfill Chip 渲染
- 已激活能力真实数据（占位即可）

---

## 2. 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `frontend-nextjs/types/advisor.ts` | **新建** | 完整 AdvisorViewModel TypeScript 类型 |
| `frontend-nextjs/components/project-cockpit/AdvisorPanel.tsx` | **重写** | 五区结构，接受 AdvisorViewModel |
| `frontend-nextjs/components/project-cockpit/mock/mockData.ts` | **更新** | 新增 MOCK_ADVISOR_VIEW_MODEL，移除 ADVISOR_OUTPUT |
| `frontend-nextjs/app/project-cockpit/[projectId]/page.tsx` | **更新** | 新增 sceneRef/viewModel 状态，navigate Chip 路由逻辑 |

---

## 3. 类型层设计（`types/advisor.ts`）

完整对应架构 §8，不裁剪任何字段（Phase A1 未用到的字段 optional，类型安全兜底）。

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

export interface EvidenceMetadata {
  evidenceClass: 'none' | 'internal_reasoning' | 'knowledge_base' | 'case_validated' | 'standard_verified';
  verificationState: 'unverified' | 'pending_registry' | 'registered' | 'expert_confirmed';
}

export interface AdvisorJudgment {
  content: string;
  confidence: 'high' | 'medium' | 'low';
  evidence: EvidenceMetadata;
  sourceParts: {
    ontology?: string;
    methodology?: string;
    knowledge?: string;
    userHistory?: string;
  };
  cannotDo?: { reason: string; blockedChipTypes?: ActionChip['type'][] }[];
}

export interface ActivatedCapability {
  type: 'ontology' | 'methodology' | 'knowledge' | 'evidence' | 'user_history';
  name: string;
  status: 'active' | 'pending' | 'unavailable' | 'placeholder';
  summary: string;
  sourceId?: string;
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

---

## 4. AdvisorPanel.tsx 五区结构

### Props

```typescript
interface AdvisorPanelProps {
  viewModel: AdvisorViewModel;
  prefillMessage?: string;
  onChipAction: (chip: ActionChip) => void;
  onAsk: (text: string) => void;
}
```

### 五区布局

```
┌─────────────────────────────────────┐
│ ① 标题栏 + 场景绑定指示              │  固定，不滚动
│   "方案高参 · project_base · draft"  │
│   evidenceStatus 徽章               │
├─────────────────────────────────────┤
│ ② 判断区                            │  flex-1，可滚动
│   无 chat → 我正在看 / 判断文本       │
│   有 chat → 状态摘要条（objectState + judgment 前20字）+ 对话历史 │
├─────────────────────────────────────┤
│ ③ ActionChip 区                     │  固定，不滚动
│   主 Chip（蓝底）                    │
│   次 Chip ×≤2（描边）                │
│   cannotDo 提示（灰色小字）           │
├─────────────────────────────────────┤
│ ④ 已激活能力（Phase A1 占位）         │  固定，纯展示，不可点击
│   本体论 placeholder · 方法论 ·      │
│   知识库（均为 status:placeholder）   │
├─────────────────────────────────────┤
│ ⑤ 输入框                            │  固定，不滚动
└─────────────────────────────────────┘
```

### ActionChip 行为

| Chip 类型 | Phase A1 行为 |
|-----------|--------------|
| `ask` | 将 `payload.question` 填入输入框，用户可修改后发送 |
| `navigate` | 调用 `onChipAction(chip)`，路由逻辑在 page.tsx |
| `fill` | 调用 `onChipAction(chip)`，page.tsx 打印 console.log（Phase A2 接表单） |
| `freeze` / `backfill` / `compare` | 不渲染（Phase A1 范围外） |

### evidenceStatus 徽章

| 值 | 样式 |
|----|------|
| `none` | 灰色圆点 + "无依据" |
| `internal_hint` | 黄色圆点 + "内部推断" |
| `verified` | 绿色圆点 + "已验证" |

---

## 5. page.tsx 变更

### 新增状态

```typescript
const [sceneRef, setSceneRef] = useState<SceneRef>({
  projectId,
  sessionId: 'local-session',
  module: 'project_base',
  userAction: 'view',
  dispatchLevel: 'L1',
});
const [viewModel, setViewModel] = useState<AdvisorViewModel>(MOCK_ADVISOR_VIEW_MODEL);
```

移除：`advisorFocus` 状态、`ADVISOR_OUTPUT` 常量、`INPUT_PLACEHOLDERS` 常量。

### navigate Chip 路由规则

```typescript
// 底盘页内模块（切换 activeCapability，不跳页）
const COCKPIT_MODULES = new Set<AdvisorModule>([
  'project_base', 'floor_plan', 'scheme_canvas'
]);

const handleChipAction = (chip: ActionChip) => {
  if (chip.type === 'navigate') {
    const { target } = chip.payload;
    if (COCKPIT_MODULES.has(target)) {
      setActiveCapability(target as CapabilityStatus['key']);
      // navigate_in 到达 → 触发 L2（Phase A2 替换为真实 API 调用）
      setSceneRef(prev => ({
        ...prev,
        module: target,
        userAction: 'navigate_in',
        dispatchLevel: 'L2',
      }));
    } else {
      router.push(`/analysis/${projectId}?module=${target}`);
    }
  }
  if (chip.type === 'ask') {
    setPrefillMessage(chip.payload.question);
  }
};
```

---

## 6. Mock 数据（`mock/mockData.ts` 新增）

新增 `MOCK_ADVISOR_VIEW_MODEL: AdvisorViewModel`，代表 HAY 七里坪项目底盘的初始高参状态：

- `boundObjectId`: `'project-hay-qilipng'`
- `objectState`: `'draft'`
- `evidenceStatus`: `'internal_hint'`
- `judgment.content`: 当前项目方向判断文本
- `judgment.confidence`: `'medium'`
- `actionChips`: 3 个（1 主 ask + 1 次 navigate to floor_plan + 1 次 fill）
- `activatedCapabilities`: 3 个 placeholder（ontology/methodology/knowledge，均 `status: 'placeholder'`）

---

## 7. 不破坏现有功能

- `DecisionView.tsx` 不改动
- `LeftNavWithStatus.tsx` 不改动
- `PageLayout.tsx` 不改动
- `EmptyStateInvitation.tsx` 不改动
- `CockpitPanel.tsx` 不引用 `AdvisorPanel`，无需改动

---

## 8. Phase A2 接入点（预留）

Phase A1 完成后，Phase A2 只需：
1. 将 `page.tsx` 中 `handleAsk` 改为 `POST /v1/advisor/intents`，响应赋值给 `setViewModel`
2. `MOCK_ADVISOR_VIEW_MODEL` 仅作为请求前的初始状态
3. 类型层不需要改动（Pydantic 后端 schema 对应同一类型定义）
