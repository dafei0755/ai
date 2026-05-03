# AdvisorPanel Phase A1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 AdvisorPanel 从 mock 聊天模式升级为符合架构规范的五区结构，数据模型替换为 AdvisorViewModel，为 Phase A2 后端接入建立干净的类型基础。

**Architecture:** 新建 `types/advisor.ts` 作为 TypeScript 类型单一真相源；AdvisorPanel 重写为五区布局（标题/判断/Chip/能力/输入）；page.tsx 负责路由逻辑并向下传递 AdvisorViewModel。Mock 数据在 Phase A2 时只替换数据来源，不改类型和组件结构。

**Tech Stack:** Next.js 15, React 19, TypeScript, Tailwind CSS, Jest + @testing-library/react (@swc/jest transform), lucide-react

---

## 文件变更清单

| 操作 | 文件 | 职责 |
|------|------|------|
| 新建 | `frontend-nextjs/types/advisor.ts` | 完整 AdvisorViewModel TypeScript 类型 |
| 修改 | `frontend-nextjs/components/project-cockpit/mock/mockData.ts` | 新增 MOCK_ADVISOR_VIEW_MODEL，移除 ADVISOR_OUTPUT 及相关常量 |
| 新建 | `frontend-nextjs/__tests__/AdvisorPanel.test.tsx` | AdvisorPanel 单元测试 |
| 重写 | `frontend-nextjs/components/project-cockpit/AdvisorPanel.tsx` | 五区结构，接受 AdvisorViewModel |
| 修改 | `frontend-nextjs/app/project-cockpit/[projectId]/page.tsx` | 接线新 props，navigate Chip 路由逻辑 |

---

## Task 1: 创建 TypeScript 类型文件

**Files:**
- Create: `frontend-nextjs/types/advisor.ts`

- [ ] **Step 1: 创建 types/advisor.ts**

```typescript
// frontend-nextjs/types/advisor.ts

export type AdvisorModule =
  | 'project_base'
  | 'floor_plan'
  | 'scheme_canvas'
  | 'resource_radar'
  | 'silicon_avatar'
  | 'knowledge_hub';

export type AdvisorObjectType =
  | 'project'
  | 'space'
  | 'brief'
  | 'spg'
  | 'floor_plan_pack'
  | 'layout_variant'
  | 'concept_canvas'
  | 'placement_canvas'
  | 'resource_candidate'
  | 'decision_log'
  | 'preference_rule';

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
  evidenceClass:
    | 'none'
    | 'internal_reasoning'
    | 'knowledge_base'
    | 'case_validated'
    | 'standard_verified';
  verificationState:
    | 'unverified'
    | 'pending_registry'
    | 'registered'
    | 'expert_confirmed';
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

- [ ] **Step 2: TypeScript 编译检查**

```bash
cd frontend-nextjs
npx tsc --noEmit
```

期望：无 error 输出（warning 可接受）。

- [ ] **Step 3: Commit**

```bash
git add frontend-nextjs/types/advisor.ts
git commit -m "feat: add AdvisorViewModel TypeScript types (Phase A1)"
```

---

## Task 2: 更新 Mock 数据

**Files:**
- Modify: `frontend-nextjs/components/project-cockpit/mock/mockData.ts`
- Create: `frontend-nextjs/__tests__/mockAdvisorViewModel.test.ts`

- [ ] **Step 1: 写 mock 数据测试（先让它失败）**

新建 `frontend-nextjs/__tests__/mockAdvisorViewModel.test.ts`：

```typescript
// frontend-nextjs/__tests__/mockAdvisorViewModel.test.ts
import { MOCK_ADVISOR_VIEW_MODEL } from '@/components/project-cockpit/mock/mockData';

describe('MOCK_ADVISOR_VIEW_MODEL', () => {
  it('has required traceId and generatedAt', () => {
    expect(MOCK_ADVISOR_VIEW_MODEL.traceId).toBeTruthy();
    expect(MOCK_ADVISOR_VIEW_MODEL.generatedAt).toBeTruthy();
  });

  it('has valid evidenceStatus', () => {
    expect(['none', 'internal_hint', 'verified']).toContain(
      MOCK_ADVISOR_VIEW_MODEL.evidenceStatus
    );
  });

  it('has at least one actionChip', () => {
    expect(MOCK_ADVISOR_VIEW_MODEL.actionChips.length).toBeGreaterThan(0);
  });

  it('has at most one primary chip', () => {
    const primary = MOCK_ADVISOR_VIEW_MODEL.actionChips.filter(c => c.isPrimary);
    expect(primary.length).toBeLessThanOrEqual(1);
  });

  it('has at most 2 secondary chips', () => {
    const secondary = MOCK_ADVISOR_VIEW_MODEL.actionChips.filter(c => !c.isPrimary);
    expect(secondary.length).toBeLessThanOrEqual(2);
  });

  it('has 3 activated capabilities all placeholder', () => {
    expect(MOCK_ADVISOR_VIEW_MODEL.activatedCapabilities).toHaveLength(3);
    MOCK_ADVISOR_VIEW_MODEL.activatedCapabilities.forEach(cap => {
      expect(cap.status).toBe('placeholder');
    });
  });

  it('sceneContext.module is project_base', () => {
    expect(MOCK_ADVISOR_VIEW_MODEL.sceneContext.module).toBe('project_base');
  });
});
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd frontend-nextjs
npx jest __tests__/mockAdvisorViewModel.test.ts --verbose
```

期望：FAIL（`MOCK_ADVISOR_VIEW_MODEL` is not exported from mockData.ts）。

- [ ] **Step 3: 在 mockData.ts 末尾添加 MOCK_ADVISOR_VIEW_MODEL**

在 `frontend-nextjs/components/project-cockpit/mock/mockData.ts` 文件**顶部**添加 import，**末尾**添加常量：

顶部追加（文件第 1 行之后，在现有 import 之前）：
```typescript
import type { AdvisorViewModel } from '@/types/advisor';
```

文件末尾追加：
```typescript
export const MOCK_ADVISOR_VIEW_MODEL: AdvisorViewModel = {
  traceId: 'trace-mock-001',
  generatedAt: '2026-05-03T10:00:00Z',
  sceneContext: {
    projectId: 'hay-qilipng',
    sessionId: 'local-session',
    module: 'project_base',
    userAction: 'view',
    dispatchLevel: 'L1',
  },
  boundObjectId: 'project-hay-qilipng',
  objectState: 'draft',
  objectVersion: '0.1.0',
  judgment: {
    content:
      '品牌气质和地点约束已明确；主要缺口是面积分布、房间数量和平面图。补齐后平面推演可正式启动。',
    confidence: 'medium',
    evidence: {
      evidenceClass: 'internal_reasoning',
      verificationState: 'unverified',
    },
    sourceParts: {
      ontology: '民宿类型 · 山地',
    },
    cannotDo: [
      {
        reason: '缺少面积和平面图，无法启动空间推演',
        blockedChipTypes: ['navigate'],
      },
    ],
  },
  evidenceStatus: 'internal_hint',
  activatedCapabilities: [
    {
      type: 'ontology',
      name: '本体论',
      status: 'placeholder',
      summary: 'Phase A2 接入后生效',
    },
    {
      type: 'methodology',
      name: '方法论',
      status: 'placeholder',
      summary: 'Phase A2 接入后生效',
    },
    {
      type: 'knowledge',
      name: '知识库',
      status: 'placeholder',
      summary: 'Phase A2 接入后生效',
    },
  ],
  actionChips: [
    {
      type: 'ask',
      label: '补充 3 个关键信息',
      isPrimary: true,
      payload: {
        question:
          '请问项目总建筑面积大概是多少？客房数量和房型组合是什么？是否有平面图或现场照片？',
      },
    },
    {
      type: 'navigate',
      label: '预览平面推演',
      isPrimary: false,
      payload: { target: 'floor_plan' },
    },
    {
      type: 'fill',
      label: '保存项目方向草案',
      isPrimary: false,
      payload: { formId: 'project-base-draft' },
    },
  ],
};
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
cd frontend-nextjs
npx jest __tests__/mockAdvisorViewModel.test.ts --verbose
```

期望：7 tests passing。

- [ ] **Step 5: TypeScript 检查**

```bash
cd frontend-nextjs
npx tsc --noEmit
```

期望：无 error。

- [ ] **Step 6: Commit**

```bash
git add frontend-nextjs/components/project-cockpit/mock/mockData.ts
git add frontend-nextjs/__tests__/mockAdvisorViewModel.test.ts
git commit -m "feat: add MOCK_ADVISOR_VIEW_MODEL to mockData (Phase A1)"
```

---

## Task 3: 写 AdvisorPanel 单元测试（失败态）

**Files:**
- Create: `frontend-nextjs/__tests__/AdvisorPanel.test.tsx`

- [ ] **Step 1: 新建测试文件**

```tsx
// frontend-nextjs/__tests__/AdvisorPanel.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { AdvisorPanel } from '@/components/project-cockpit/AdvisorPanel';
import { MOCK_ADVISOR_VIEW_MODEL } from '@/components/project-cockpit/mock/mockData';
import type { ActionChip } from '@/types/advisor';

describe('AdvisorPanel', () => {
  const mockOnChipAction = jest.fn();
  const mockOnAsk = jest.fn();

  beforeEach(() => {
    mockOnChipAction.mockClear();
    mockOnAsk.mockClear();
  });

  it('renders title "方案高参"', () => {
    render(
      <AdvisorPanel
        viewModel={MOCK_ADVISOR_VIEW_MODEL}
        onChipAction={mockOnChipAction}
        onAsk={mockOnAsk}
      />
    );
    expect(screen.getByText('方案高参')).toBeInTheDocument();
  });

  it('renders module label in title bar', () => {
    render(
      <AdvisorPanel
        viewModel={MOCK_ADVISOR_VIEW_MODEL}
        onChipAction={mockOnChipAction}
        onAsk={mockOnAsk}
      />
    );
    expect(screen.getByText(/项目底盘/)).toBeInTheDocument();
  });

  it('renders evidenceStatus badge "内部推断"', () => {
    render(
      <AdvisorPanel
        viewModel={MOCK_ADVISOR_VIEW_MODEL}
        onChipAction={mockOnChipAction}
        onAsk={mockOnAsk}
      />
    );
    expect(screen.getByText('内部推断')).toBeInTheDocument();
  });

  it('renders judgment content', () => {
    render(
      <AdvisorPanel
        viewModel={MOCK_ADVISOR_VIEW_MODEL}
        onChipAction={mockOnChipAction}
        onAsk={mockOnAsk}
      />
    );
    expect(
      screen.getByText(MOCK_ADVISOR_VIEW_MODEL.judgment.content)
    ).toBeInTheDocument();
  });

  it('renders primary chip label', () => {
    render(
      <AdvisorPanel
        viewModel={MOCK_ADVISOR_VIEW_MODEL}
        onChipAction={mockOnChipAction}
        onAsk={mockOnAsk}
      />
    );
    expect(screen.getByText('补充 3 个关键信息')).toBeInTheDocument();
  });

  it('ask chip click fills textarea with question (does not call onChipAction)', () => {
    render(
      <AdvisorPanel
        viewModel={MOCK_ADVISOR_VIEW_MODEL}
        onChipAction={mockOnChipAction}
        onAsk={mockOnAsk}
      />
    );
    fireEvent.click(screen.getByText('补充 3 个关键信息'));
    const textarea = screen.getByRole('textbox');
    expect(textarea).toHaveValue(
      '请问项目总建筑面积大概是多少？客房数量和房型组合是什么？是否有平面图或现场照片？'
    );
    expect(mockOnChipAction).not.toHaveBeenCalled();
  });

  it('navigate chip click calls onChipAction with chip object', () => {
    render(
      <AdvisorPanel
        viewModel={MOCK_ADVISOR_VIEW_MODEL}
        onChipAction={mockOnChipAction}
        onAsk={mockOnAsk}
      />
    );
    fireEvent.click(screen.getByText('预览平面推演'));
    expect(mockOnChipAction).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'navigate',
        payload: { target: 'floor_plan' },
      })
    );
  });

  it('fill chip click calls onChipAction', () => {
    render(
      <AdvisorPanel
        viewModel={MOCK_ADVISOR_VIEW_MODEL}
        onChipAction={mockOnChipAction}
        onAsk={mockOnAsk}
      />
    );
    fireEvent.click(screen.getByText('保存项目方向草案'));
    expect(mockOnChipAction).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'fill' })
    );
  });

  it('renders 3 activated capabilities as placeholders', () => {
    render(
      <AdvisorPanel
        viewModel={MOCK_ADVISOR_VIEW_MODEL}
        onChipAction={mockOnChipAction}
        onAsk={mockOnAsk}
      />
    );
    expect(screen.getByText('本体论')).toBeInTheDocument();
    expect(screen.getByText('方法论')).toBeInTheDocument();
    expect(screen.getByText('知识库')).toBeInTheDocument();
  });

  it('prefillMessage sets textarea value', () => {
    render(
      <AdvisorPanel
        viewModel={MOCK_ADVISOR_VIEW_MODEL}
        prefillMessage="测试预填充"
        onChipAction={mockOnChipAction}
        onAsk={mockOnAsk}
      />
    );
    expect(screen.getByRole('textbox')).toHaveValue('测试预填充');
  });

  it('renders cannotDo reason text', () => {
    render(
      <AdvisorPanel
        viewModel={MOCK_ADVISOR_VIEW_MODEL}
        onChipAction={mockOnChipAction}
        onAsk={mockOnAsk}
      />
    );
    expect(
      screen.getByText('缺少面积和平面图，无法启动空间推演')
    ).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd frontend-nextjs
npx jest __tests__/AdvisorPanel.test.tsx --verbose
```

期望：多项 FAIL（旧组件不接受 `viewModel` prop，缺少 `evidenceStatus` / `activatedCapabilities` 渲染）。

- [ ] **Step 3: Commit 测试文件**

```bash
git add frontend-nextjs/__tests__/AdvisorPanel.test.tsx
git commit -m "test: add failing AdvisorPanel tests for Phase A1 five-zone structure"
```

---

## Task 4: 重写 AdvisorPanel.tsx

**Files:**
- Rewrite: `frontend-nextjs/components/project-cockpit/AdvisorPanel.tsx`

- [ ] **Step 1: 完整替换 AdvisorPanel.tsx**

用以下内容**完整替换** `frontend-nextjs/components/project-cockpit/AdvisorPanel.tsx`：

```tsx
'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Loader2 } from 'lucide-react';
import type { AdvisorViewModel, ActionChip } from '@/types/advisor';

interface AdvisorPanelProps {
  viewModel: AdvisorViewModel;
  prefillMessage?: string;
  onChipAction: (chip: ActionChip) => void;
  onAsk: (text: string) => void;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'advisor';
  text: string;
}

const EVIDENCE_CONFIG = {
  none:          { dot: 'bg-gray-500',   label: '无依据' },
  internal_hint: { dot: 'bg-yellow-400', label: '内部推断' },
  verified:      { dot: 'bg-green-400',  label: '已验证' },
} as const;

const MODULE_LABELS: Record<string, string> = {
  project_base:   '项目底盘',
  floor_plan:     '平面推演',
  scheme_canvas:  '方案画布',
  resource_radar: '资源雷达',
  silicon_avatar: '硅基分身',
  knowledge_hub:  '知识中枢',
};

const OBJECT_STATE_LABELS: Record<string, string> = {
  draft:               '草案',
  pending_confirmation: '待确认',
  frozen:              '已冻结',
  stale:               '已过期',
  forked:              '已分叉',
  archived:            '已归档',
};

export function AdvisorPanel({
  viewModel,
  prefillMessage,
  onChipAction,
  onAsk,
}: AdvisorPanelProps) {
  const [inputValue, setInputValue] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isThinking, setIsThinking] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (prefillMessage) setInputValue(prefillMessage);
  }, [prefillMessage]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isThinking]);

  const handleSend = () => {
    const text = inputValue.trim();
    if (!text || isThinking) return;
    setMessages(prev => [...prev, { id: Date.now().toString(), role: 'user', text }]);
    setInputValue('');
    setIsThinking(true);
    onAsk(text);
    // Phase A1 mock response: echo judgment content after delay
    setTimeout(() => {
      setIsThinking(false);
      setMessages(prev => [
        ...prev,
        { id: (Date.now() + 1).toString(), role: 'advisor', text: viewModel.judgment.content },
      ]);
    }, 1200);
  };

  const handleChipClick = (chip: ActionChip) => {
    if (chip.type === 'ask') {
      setInputValue(chip.payload.question);
    } else {
      onChipAction(chip);
    }
  };

  const hasChatHistory = messages.length > 0;
  const evidenceConfig = EVIDENCE_CONFIG[viewModel.evidenceStatus];
  const renderableChips = viewModel.actionChips.filter(
    c => c.type === 'ask' || c.type === 'navigate' || c.type === 'fill'
  );
  const primaryChips = renderableChips.filter(c => c.isPrimary);
  const secondaryChips = renderableChips.filter(c => !c.isPrimary).slice(0, 2);

  return (
    <div className="flex flex-col h-full bg-[#161616] text-white">

      {/* ① 标题栏 + 场景绑定 */}
      <div className="flex items-center gap-3 border-b border-white/8 px-4 py-3.5 shrink-0">
        <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-[#2e67ff] text-white shrink-0">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M12 2L2 7l10 5 10-5-10-5z"/>
            <path d="M2 17l10 5 10-5"/>
            <path d="M2 12l10 5 10-5"/>
          </svg>
        </div>
        <div className="flex-1 min-w-0">
          <span className="text-sm font-semibold text-white">方案高参</span>
          <div className="flex items-center gap-1.5 mt-0.5">
            <span className="text-[10px] text-white/40">
              {MODULE_LABELS[viewModel.sceneContext.module] ?? viewModel.sceneContext.module}
              {viewModel.objectState && ` · ${OBJECT_STATE_LABELS[viewModel.objectState] ?? viewModel.objectState}`}
            </span>
            <span className={`inline-block w-1.5 h-1.5 rounded-full ${evidenceConfig.dot}`} />
            <span className="text-[10px] text-white/40">{evidenceConfig.label}</span>
          </div>
        </div>
      </div>

      {/* ② 判断区 */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {!hasChatHistory ? (
          <>
            <section>
              <p className="text-[10px] font-semibold text-white/38 uppercase tracking-widest mb-1.5">
                我正在看
              </p>
              <p className="text-sm text-white/80 leading-relaxed">
                {MODULE_LABELS[viewModel.sceneContext.module] ?? viewModel.sceneContext.module}
                {viewModel.boundObjectId && (
                  <span className="text-white/40"> · {viewModel.boundObjectId}</span>
                )}
              </p>
            </section>
            <section>
              <p className="text-[10px] font-semibold text-white/38 uppercase tracking-widest mb-1.5">
                判断
              </p>
              <p className="text-sm text-white/90 leading-relaxed">{viewModel.judgment.content}</p>
              {viewModel.judgment.confidence === 'low' && (
                <p className="mt-1 text-[10px] text-yellow-400/70">
                  置信度低，建议补充信息后重新评估
                </p>
              )}
            </section>
          </>
        ) : (
          <>
            <div className="rounded-lg bg-white/5 px-3 py-2 text-xs text-white/40 border border-white/8 shrink-0">
              <span className="font-medium text-white/60">
                {OBJECT_STATE_LABELS[viewModel.objectState ?? 'draft'] ?? '草案'}：
              </span>
              {viewModel.judgment.content.slice(0, 40)}...
            </div>
            {messages.map(msg => (
              <div
                key={msg.id}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {msg.role === 'advisor' && (
                  <div className="h-6 w-6 rounded-full bg-[#2e67ff] flex items-center justify-center shrink-0 mr-2 mt-0.5">
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                      <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                    </svg>
                  </div>
                )}
                <div
                  className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed whitespace-pre-line ${
                    msg.role === 'user'
                      ? 'bg-[#2e67ff] text-white rounded-tr-sm'
                      : 'bg-white/8 text-white/90 rounded-tl-sm'
                  }`}
                >
                  {msg.text}
                </div>
              </div>
            ))}
            {isThinking && (
              <div className="flex justify-start">
                <div className="h-6 w-6 rounded-full bg-[#2e67ff] flex items-center justify-center shrink-0 mr-2 mt-0.5">
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                  </svg>
                </div>
                <div className="bg-white/8 rounded-2xl rounded-tl-sm px-3.5 py-2.5 flex items-center gap-1.5">
                  <Loader2 className="w-3.5 h-3.5 text-white/50 animate-spin" />
                  <span className="text-xs text-white/40">思考中...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* ③ ActionChip 区 */}
      <div className="px-3 pb-2 shrink-0 space-y-1.5">
        {primaryChips.map((chip, i) => (
          <button
            key={i}
            onClick={() => handleChipClick(chip)}
            className="w-full text-left rounded-lg bg-[#2e67ff] px-3 py-2 text-sm font-medium text-white hover:bg-[#2558e0] transition-colors"
          >
            {chip.label}
          </button>
        ))}
        {secondaryChips.length > 0 && (
          <div className="flex gap-1.5">
            {secondaryChips.map((chip, i) => (
              <button
                key={i}
                onClick={() => handleChipClick(chip)}
                className="flex-1 rounded-lg border border-white/15 px-3 py-1.5 text-xs text-white/70 hover:border-white/30 hover:text-white transition-colors"
              >
                {chip.label}
              </button>
            ))}
          </div>
        )}
        {viewModel.judgment.cannotDo?.map((item, i) => (
          <p key={i} className="text-[10px] text-white/30 px-1">
            {item.reason}
          </p>
        ))}
      </div>

      {/* ④ 已激活能力（Phase A1 占位，纯展示） */}
      <div className="px-3 pb-2 shrink-0">
        <div className="rounded-lg bg-white/3 border border-white/8 px-3 py-2">
          <p className="text-[10px] font-semibold text-white/30 uppercase tracking-widest mb-1.5">
            已激活能力
          </p>
          <div className="flex gap-2 flex-wrap">
            {viewModel.activatedCapabilities.map((cap, i) => (
              <span
                key={i}
                className={`text-[10px] px-2 py-0.5 rounded-full border ${
                  cap.status === 'placeholder'
                    ? 'border-white/10 text-white/25'
                    : 'border-blue-500/40 text-blue-400/70'
                }`}
              >
                {cap.name}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* ⑤ 输入框 */}
      <div className="px-3 pb-3 pt-1 border-t border-white/8 shrink-0">
        <div className="flex items-end gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 focus-within:border-white/20 transition-colors">
          <textarea
            value={inputValue}
            onChange={e => setInputValue(e.target.value)}
            placeholder="问我任何关于这个项目的问题..."
            rows={2}
            className="flex-1 bg-transparent text-sm text-white placeholder:text-white/30 resize-none outline-none leading-relaxed"
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
          />
          <button
            onClick={handleSend}
            disabled={!inputValue.trim() || isThinking}
            className="shrink-0 p-1.5 rounded-lg text-[#2e67ff] disabled:opacity-30 hover:bg-white/8 transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>

    </div>
  );
}
```

- [ ] **Step 2: 运行 AdvisorPanel 测试，确认通过**

```bash
cd frontend-nextjs
npx jest __tests__/AdvisorPanel.test.tsx --verbose
```

期望：10 tests passing，0 failing。

- [ ] **Step 3: 运行所有测试，确认无回归**

```bash
cd frontend-nextjs
npx jest --verbose
```

期望：已有测试全部 passing，无新 failing。

- [ ] **Step 4: TypeScript 检查**

```bash
cd frontend-nextjs
npx tsc --noEmit
```

期望：无 error。

- [ ] **Step 5: Commit**

```bash
git add frontend-nextjs/components/project-cockpit/AdvisorPanel.tsx
git commit -m "feat: rewrite AdvisorPanel with AdvisorViewModel five-zone structure (Phase A1)"
```

---

## Task 5: 更新 page.tsx 接线

**Files:**
- Modify: `frontend-nextjs/app/project-cockpit/[projectId]/page.tsx`

- [ ] **Step 1: 完整替换 page.tsx**

用以下内容**完整替换** `frontend-nextjs/app/project-cockpit/[projectId]/page.tsx`：

```tsx
'use client';

/**
 * 项目底盘页 — 方案高参核心决策视图
 *
 * 路由：
 *   /project-cockpit/new       → 空状态激活入口
 *   /project-cockpit/[id]      → 已激活项目决策视图
 */

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { PageLayout } from '@/components/project-cockpit/PageLayout';
import { EmptyStateInvitation, type EntryType } from '@/components/project-cockpit/EmptyStateInvitation';
import { DecisionView } from '@/components/project-cockpit/DecisionView';
import { LeftNavWithStatus } from '@/components/project-cockpit/LeftNavWithStatus';
import { AdvisorPanel } from '@/components/project-cockpit/AdvisorPanel';
import {
  MOCK_PROJECT_OVERVIEW,
  MOCK_STAGES,
  MOCK_ADVISOR_VIEW_MODEL,
  type ViewKey,
  type CapabilityStatus,
} from '@/components/project-cockpit/mock/mockData';
import type { AdvisorViewModel, SceneRef, ActionChip, AdvisorModule } from '@/types/advisor';

// 底盘页内模块：页内切换 activeCapability，不跳页
const COCKPIT_MODULES = new Set<AdvisorModule>([
  'project_base',
  'floor_plan',
  'scheme_canvas',
]);

export default function ProjectCockpitPage() {
  const params    = useParams();
  const router    = useRouter();
  const projectId = params.projectId as string;

  const [isActivated, setIsActivated]           = useState(projectId !== 'new');
  const [activeView, setActiveView]             = useState<ViewKey>('overview');
  const [activeCapability, setActiveCapability] = useState<CapabilityStatus['key']>('project_base');
  const [prefillMessage, setPrefillMessage]     = useState<string | undefined>(undefined);
  const [sceneRef, setSceneRef]                 = useState<SceneRef>({
    projectId,
    sessionId: 'local-session',
    module: 'project_base',
    userAction: 'view',
    dispatchLevel: 'L1',
  });
  // Phase A2: const [viewModel, setViewModel] = useState<AdvisorViewModel>(MOCK_ADVISOR_VIEW_MODEL);
  // 届时 handleAsk 调用 setViewModel(response) 替换 mock
  const viewModel: AdvisorViewModel = MOCK_ADVISOR_VIEW_MODEL;

  const handleEntry = (type: EntryType) => {
    console.log('[mock] activation entry:', type);
    setIsActivated(true);
    if (projectId === 'new') {
      router.push('/project-cockpit/hay-demo');
    }
  };

  const handleAction = (actionLabel: string) => {
    console.log('[mock] action:', actionLabel);
  };

  const handleCapabilityClick = (key: CapabilityStatus['key']) => {
    setActiveCapability(key);
  };

  const handleChipAction = (chip: ActionChip) => {
    if (chip.type === 'navigate') {
      const { target } = chip.payload;
      if (COCKPIT_MODULES.has(target)) {
        // L0：页内切换，不发后端请求
        setActiveCapability(target as CapabilityStatus['key']);
        // navigate_in 到达 → 触发 L2（Phase A2 替换为 POST /v1/advisor/intents）
        setSceneRef(prev => ({
          ...prev,
          module: target,
          userAction: 'navigate_in',
          dispatchLevel: 'L2',
        }));
      } else {
        router.push(`/analysis/${projectId}?module=${target}`);
      }
    } else if (chip.type === 'fill') {
      console.log('[mock] fill chip:', chip.payload);
      // Phase A2: 打开对应表单
    }
  };

  const handleAsk = (text: string) => {
    console.log('[mock] advisor ask:', text);
    setSceneRef(prev => ({ ...prev, userAction: 'ask', dispatchLevel: 'L3' }));
    setPrefillMessage(undefined);
    // Phase A2: POST /v1/advisor/intents → setViewModel(response)
  };

  const handleAdvisorPrefill = (text: string) => {
    setPrefillMessage(text);
  };

  const leftNav = (
    <LeftNavWithStatus
      capabilities={MOCK_PROJECT_OVERVIEW.capabilities}
      activeKey={activeCapability}
      onCapabilityClick={handleCapabilityClick}
    />
  );

  const mainContent = !isActivated ? (
    <EmptyStateInvitation onEntry={handleEntry} />
  ) : (
    <DecisionView
      overview={MOCK_PROJECT_OVERVIEW}
      stages={MOCK_STAGES}
      activeView={activeView}
      onViewChange={setActiveView}
      onAction={handleAction}
      onCapabilityClick={handleCapabilityClick}
      onAdvisorPrefill={handleAdvisorPrefill}
    />
  );

  const advisorPanel = (
    <AdvisorPanel
      viewModel={viewModel}
      prefillMessage={prefillMessage}
      onChipAction={handleChipAction}
      onAsk={handleAsk}
    />
  );

  return (
    <PageLayout
      leftNav={leftNav}
      mainContent={mainContent}
      advisorPanel={advisorPanel}
    />
  );
}
```

- [ ] **Step 2: TypeScript 检查**

```bash
cd frontend-nextjs
npx tsc --noEmit
```

期望：无 error。

- [ ] **Step 3: 运行全部测试，确认无回归**

```bash
cd frontend-nextjs
npx jest --verbose
```

期望：所有已有测试 passing，AdvisorPanel 测试 10/10 passing。

- [ ] **Step 4: Commit**

```bash
git add frontend-nextjs/app/project-cockpit/[projectId]/page.tsx
git commit -m "feat: wire AdvisorPanel Phase A1 in project cockpit page"
```

---

## Task 6: 合并分支

- [ ] **Step 1: 切回 main，确认 diff**

```bash
git checkout main
git diff main..HEAD --stat
```

期望：5 个文件变更（types/advisor.ts 新建，mockData.ts 修改，AdvisorPanel.tsx 修改，page.tsx 修改，测试文件 2 个新建）。

- [ ] **Step 2: 合并**

```bash
git merge --no-ff feature/advisor-panel-phase-a1 -m "feat: AdvisorPanel Phase A1 — AdvisorViewModel 五区结构升级"
```

- [ ] **Step 3: 最终全量测试**

```bash
cd frontend-nextjs
npx jest --verbose
```

期望：所有测试 passing。

---

## Phase A2 接入点备忘

完成本计划后，Phase A2 只需改 2 处：

1. `page.tsx` `handleAsk` 函数内：
   ```typescript
   // 替换这一行 comment：
   // Phase A2: POST /v1/advisor/intents → setViewModel(response)
   // 改为：
   const response = await fetch('/v1/advisor/intents', {
     method: 'POST',
     body: JSON.stringify({ sceneContext: sceneRef }),
   });
   setViewModel(await response.json());
   ```

2. `MOCK_ADVISOR_VIEW_MODEL` 降级为初始状态占位，不再是唯一数据源。

类型层和组件结构**不需要改动**。
