# UCPPT v7.270 前端集成指南

## 概述

本文档说明如何在前端集成 UCPPT v7.270 的新功能，包括解题思路展示和两步流程进度指示。

## 新增功能

### 1. 两步流程

**旧流程（v7.269及之前）**:
```
统一分析 → 搜索执行
```

**新流程（v7.270）**:
```
Step 1: 需求理解与深度分析 → Step 2: 搜索框架生成 → 搜索执行
```

### 2. 新增事件

| 事件类型 | 触发时机 | 数据内容 | 用途 |
|---------|---------|---------|------|
| `problem_solving_approach_ready` | 第一步解题思路生成完成 | `ProblemSolvingApproach` 对象 | 展示解题路径卡片 |
| `step1_complete` | 第一步完整分析完成 | 包含 user_profile, analysis, problem_solving_approach, step2_context | 更新UI状态，准备进入第二步 |
| `step2_start` | 第二步开始 | `{ message: string }` | 显示"生成搜索任务清单..." |
| `step2_complete` | 第二步完成 | `{ message: string, target_count: number }` | 显示完成状态，进入搜索阶段 |

## 文件清单

### 1. 类型定义

**文件**: `frontend-nextjs/types/index.ts`

新增类型：
- `SolutionStep` - 解题步骤
- `BreakthroughPoint` - 关键突破口
- `ExpectedDeliverable` - 预期交付物
- `ProblemSolvingApproach` - 解题思路
- `Step2Context` - Step2上下文

### 2. WebSocket 事件类型

**文件**: `frontend-nextjs/lib/websocket.ts`

新增事件类型：
```typescript
| { type: 'problem_solving_approach_ready'; data: any }
| { type: 'step1_complete'; data: any }
| { type: 'step2_start'; data: any }
| { type: 'step2_complete'; data: any }
```

### 3. UI 组件

#### 3.1 解题思路卡片

**文件**: `frontend-nextjs/components/ProblemSolvingApproachCard.tsx`

**功能**:
- 展示任务本质识别（任务类型、复杂度、所需专业知识）
- 展示解题路径（5-8步详细步骤）
- 展示关键突破口（1-3个）
- 展示预期产出形态
- 支持展开/折叠

**使用示例**:
```tsx
import ProblemSolvingApproachCard from '@/components/ProblemSolvingApproachCard';

<ProblemSolvingApproachCard approach={problemSolvingApproach} />
```

#### 3.2 进度指示器

**文件**: `frontend-nextjs/components/UcpptSearchProgress.tsx`

**功能**:
- 展示三个阶段：Step 1 → Step 2 → 搜索执行
- 每个阶段有三种状态：pending / in_progress / completed
- 动画效果：进行中的阶段有脉冲动画
- 连接线颜色随状态变化

**使用示例**:
```tsx
import UcpptSearchProgress from '@/components/UcpptSearchProgress';

<UcpptSearchProgress
  currentPhase="step2"
  step1Status="completed"
  step2Status="in_progress"
  searchStatus="pending"
/>
```

### 4. 集成示例

**文件**: `frontend-nextjs/app/search-example/page.tsx`

完整的集成示例，展示如何：
1. 监听新事件
2. 更新状态
3. 展示UI组件

## 集成步骤

### Step 1: 更新类型定义

确保 `types/index.ts` 包含新的类型定义（已完成）。

### Step 2: 更新 WebSocket 消息处理

在你的 WebSocket 消息处理函数中添加新事件的处理：

```typescript
const handleWebSocketMessage = (message: WebSocketMessage) => {
  switch (message.type) {
    case 'problem_solving_approach_ready':
      // 保存解题思路
      setProblemSolvingApproach(message.data);
      break;

    case 'step1_complete':
      // 第一步完成，更新状态
      setStep1Status('completed');
      setStep2Status('in_progress');
      break;

    case 'step2_start':
      // 第二步开始
      console.log('开始生成搜索框架:', message.data.message);
      break;

    case 'step2_complete':
      // 第二步完成，进入搜索阶段
      setStep2Status('completed');
      setSearchStatus('in_progress');
      console.log(`搜索框架已生成，包含 ${message.data.target_count} 个任务`);
      break;

    // ... 其他事件处理
  }
};
```

### Step 3: 添加状态管理

在你的组件中添加必要的状态：

```typescript
const [problemSolvingApproach, setProblemSolvingApproach] =
  useState<ProblemSolvingApproach | null>(null);
const [step1Status, setStep1Status] =
  useState<'pending' | 'in_progress' | 'completed'>('in_progress');
const [step2Status, setStep2Status] =
  useState<'pending' | 'in_progress' | 'completed'>('pending');
const [searchStatus, setSearchStatus] =
  useState<'pending' | 'in_progress' | 'completed'>('pending');
```

### Step 4: 添加 UI 组件

在你的页面中添加新的 UI 组件：

```tsx
{/* 进度指示器 */}
<UcpptSearchProgress
  currentPhase={currentPhase}
  step1Status={step1Status}
  step2Status={step2Status}
  searchStatus={searchStatus}
/>

{/* 解题思路卡片 */}
{problemSolvingApproach && (
  <ProblemSolvingApproachCard approach={problemSolvingApproach} />
)}
```

## 向后兼容性

### 兼容策略

新功能完全向后兼容：
- 旧流程仍然可用（如果后端返回 `search_framework`）
- 新事件为可选增强功能
- 前端可以同时处理新旧两种流程

### 检测流程类型

```typescript
// 检测是否是新流程
const isNewFlow = message.type === 'problem_solving_approach_ready';

if (isNewFlow) {
  // 使用新流程的UI
  showTwoStepProgress();
} else {
  // 使用旧流程的UI
  showLegacyProgress();
}
```

## 样式定制

### 自定义颜色

解题思路卡片使用 Tailwind CSS，可以通过修改类名自定义颜色：

```tsx
// 修改复杂度颜色
const complexityColors = {
  simple: 'bg-green-100 text-green-800 border-green-300',
  moderate: 'bg-blue-100 text-blue-800 border-blue-300',
  complex: 'bg-orange-100 text-orange-800 border-orange-300',
  highly_complex: 'bg-red-100 text-red-800 border-red-300',
};
```

### 自定义图标

```tsx
// 修改任务类型图标
const taskTypeIcons = {
  research: '🔍',
  design: '🎨',
  decision: '⚖️',
  exploration: '🧭',
  verification: '✅',
};
```

## 测试建议

### 1. 单元测试

测试组件渲染：

```typescript
import { render, screen } from '@testing-library/react';
import ProblemSolvingApproachCard from '@/components/ProblemSolvingApproachCard';

test('renders problem solving approach card', () => {
  const approach = {
    task_type: 'design',
    task_type_description: '设计任务',
    complexity_level: 'complex',
    // ... 其他字段
  };

  render(<ProblemSolvingApproachCard approach={approach} />);

  expect(screen.getByText('解题思路')).toBeInTheDocument();
  expect(screen.getByText('设计任务')).toBeInTheDocument();
});
```

### 2. 集成测试

测试事件流：

```typescript
test('handles v7.270 event flow', async () => {
  const { result } = renderHook(() => useWebSocketEvents());

  // 模拟事件序列
  act(() => {
    result.current.handleMessage({
      type: 'problem_solving_approach_ready',
      data: mockApproach
    });
  });

  expect(result.current.problemSolvingApproach).toBeDefined();

  act(() => {
    result.current.handleMessage({
      type: 'step1_complete',
      data: {}
    });
  });

  expect(result.current.step1Status).toBe('completed');
  expect(result.current.step2Status).toBe('in_progress');
});
```

### 3. E2E 测试

使用 Playwright 或 Cypress 测试完整流程：

```typescript
test('complete search flow with v7.270', async ({ page }) => {
  await page.goto('/search');

  // 等待 Step 1 完成
  await page.waitForSelector('[data-testid="step1-completed"]');

  // 验证解题思路卡片显示
  await expect(page.locator('[data-testid="problem-solving-card"]')).toBeVisible();

  // 等待 Step 2 完成
  await page.waitForSelector('[data-testid="step2-completed"]');

  // 验证搜索开始
  await expect(page.locator('[data-testid="search-in-progress"]')).toBeVisible();
});
```

## 常见问题

### Q1: 如何判断后端是否支持 v7.270？

**A**: 监听 `problem_solving_approach_ready` 事件。如果收到此事件，说明后端支持 v7.270。

```typescript
let supportsV7270 = false;

const handleMessage = (message: WebSocketMessage) => {
  if (message.type === 'problem_solving_approach_ready') {
    supportsV7270 = true;
  }
};
```

### Q2: 旧流程和新流程可以共存吗？

**A**: 可以。后端会根据配置决定使用哪种流程，前端应该同时支持两种流程。

### Q3: 如何处理 Step 2 失败的情况？

**A**: 后端会回退到简单搜索框架，前端应该优雅降级：

```typescript
case 'step2_complete':
  if (message.data.target_count === 0) {
    // Step 2 失败，使用默认框架
    console.warn('Step 2 failed, using fallback framework');
  }
  break;
```

### Q4: 解题思路卡片太长怎么办？

**A**: 卡片默认支持展开/折叠，可以通过 `isExpanded` 状态控制：

```tsx
const [isExpanded, setIsExpanded] = useState(false); // 默认折叠
```

## 性能优化

### 1. 懒加载组件

```typescript
const ProblemSolvingApproachCard = dynamic(
  () => import('@/components/ProblemSolvingApproachCard'),
  { ssr: false }
);
```

### 2. 缓存解题思路

```typescript
// 使用 localStorage 缓存
useEffect(() => {
  if (problemSolvingApproach) {
    localStorage.setItem(
      `approach_${sessionId}`,
      JSON.stringify(problemSolvingApproach)
    );
  }
}, [problemSolvingApproach, sessionId]);
```

### 3. 虚拟滚动

如果解题步骤很多，考虑使用虚拟滚动：

```typescript
import { FixedSizeList } from 'react-window';

<FixedSizeList
  height={400}
  itemCount={approach.solution_steps.length}
  itemSize={120}
>
  {({ index, style }) => (
    <div style={style}>
      <StepItem step={approach.solution_steps[index]} />
    </div>
  )}
</FixedSizeList>
```

## 下一步

1. **测试**: 运行单元测试和集成测试
2. **部署**: 部署到测试环境验证
3. **监控**: 监控新事件的触发频率和性能
4. **反馈**: 收集用户反馈，优化UI/UX

## 参考资料

- [后端实现文档](../../UCPPT_STEP_SEPARATION_IMPLEMENTATION_v7.270.md)
- [类型定义](../types/index.ts)
- [WebSocket 客户端](../lib/websocket.ts)
- [集成示例](../app/search-example/page.tsx)

---

**版本**: v7.270
**更新日期**: 2026-01-25
**维护者**: Claude Code
