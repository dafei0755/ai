# v7.222 搜索流程全面整治

## 版本信息
- **版本**: v7.222
- **日期**: 2026-01-18
- **类型**: 重构 + Bug修复

## 问题背景

用户反馈搜索流程存在以下问题：
1. **思考过程UI不一致**: 思考过程显示扁平化UI样式，但结果显示又是老版本UI
2. **多轮搜索无结果呈现**: 多轮搜索过程中搜索结果不可见
3. **流程逻辑混乱**: 深度搜索还在总结时，AI分析问答就开始进行最终总结（时序错误）
4. **组件重复**: `SearchRoundsCard` 和 `renderDeepSearchProgress` 功能重叠

## 修复内容

### 1. 添加调试模式 (DEBUG_MODE)

在 `page.tsx` 开头添加调试配置：

```typescript
const DEBUG_MODE = process.env.NODE_ENV === 'development';
const DEBUG_SSE_EVENTS = DEBUG_MODE;      // SSE事件日志
const DEBUG_STATE_CHANGES = DEBUG_MODE;   // 状态变化日志
const DEBUG_PHASE_TRANSITIONS = DEBUG_MODE; // 阶段转换日志
```

调试面板功能：
- 在搜索进度卡片右上角显示虫子图标（仅开发环境）
- 点击可展开调试面板，显示当前状态：
  - `currentPhase`: 当前流程阶段
  - `status`: 状态机状态
  - `currentRound`: 当前轮次
  - `rounds.length`: 总轮次数
  - `searchRounds`: 搜索轮次数
  - `completedRounds`: 已完成轮次数

### 2. 添加 currentPhase 状态字段

在 `SearchState` 接口中添加：

```typescript
currentPhase: 'idle' | 'analysis' | 'search' | 'synthesis' | 'done';
```

阶段说明：
- **idle**: 初始空闲状态
- **analysis**: Phase 0 需求理解与深度分析（DeepSeek推理）
- **search**: Phase 2 多轮搜索（执行搜索计划）
- **synthesis**: Phase 3 答案生成（综合分析生成最终回答）
- **done**: 完成状态

SSE 事件自动更新 currentPhase：
- `unified_dialogue_chunk` → `analysis`
- `question_analyzed` → `search`
- `thinking_chunk` → `search`
- `answer_chunk` → `synthesis`
- `done` → `done`

### 3. 合并 SearchRoundsCard 和 renderDeepSearchProgress

创建统一的 `UnifiedSearchProgressCard` 组件：

**合并后的功能**：
- ✅ 搜索规划展示（从 DeepSearchProgress）
- ✅ 实时思考进度（从 DeepSearchProgress）
- ✅ 轮次列表和来源预览（从 SearchRoundsCard）
- ✅ 根据 currentPhase 动态调整标题和颜色
- ✅ 内置调试面板（开发环境）

**删除的旧代码**：
- `renderDeepSearchProgress()` 函数（约150行）
- 旧的 `SearchRoundsCard` 组件（约200行）

**新增的 Props**：
```typescript
interface UnifiedSearchProgressCardProps {
  rounds: RoundRecord[];
  searchPlan: SearchPlan | null;
  currentRound: number;
  currentPhase: 'idle' | 'analysis' | 'search' | 'synthesis' | 'done';
  status: string;
  statusMessage: string;
  currentRoundReasoning: string;
  currentRoundThinking: string;
  currentThinkingRound: number;
  isExpanded: boolean;
  onToggle: () => void;
}
```

### 4. 修复 Tailwind 动态类名问题

Tailwind 不支持动态类名模板字符串（如 `bg-${color}-100`），改为预定义完整类名：

```typescript
const getPhaseInfo = () => {
  if (isSynthesisPhase) {
    return {
      iconBgClass: 'bg-emerald-100 dark:bg-emerald-900/30',
      iconClass: 'text-emerald-600 dark:text-emerald-400',
      titleClass: 'text-emerald-600 dark:text-emerald-400',
      // ...
    };
  }
  // ... 其他阶段
};
```

## 文件变更

### 修改的文件

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `frontend-nextjs/app/search/[session_id]/page.tsx` | 重构 | 添加调试模式、currentPhase、合并组件 |

### 变更统计

- 新增代码: ~100行（调试配置、currentPhase更新、统一组件）
- 删除代码: ~200行（重复的renderDeepSearchProgress）
- 净减少: ~100行

## 流程阶段图示

```
┌─────────────────────────────────────────────────────────────┐
│                        用户输入查询                          │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ Phase 0: 需求理解与深度分析 (currentPhase = 'analysis')      │
│                                                              │
│ • unified_dialogue_chunk 流式输出 DeepSeek 推理内容          │
│ • TaskUnderstandingCard 显示分析进度                         │
│ • 结束: question_analyzed 事件                              │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ Phase 2: 多轮搜索 (currentPhase = 'search')                  │
│                                                              │
│ • round_start / round_sources / round_complete               │
│ • thinking_chunk 流式输出每轮思考                            │
│ • UnifiedSearchProgressCard 显示搜索进度和轮次结果            │
│ • 结束: search_complete 事件                                │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ Phase 3: 答案生成 (currentPhase = 'synthesis')               │
│                                                              │
│ • answer_chunk(is_thinking=true) 答案构思                    │
│ • answer_chunk(is_thinking=false) 实际答案                   │
│ • UnifiedSearchProgressCard 显示"答案生成中"                 │
│ • 结束: done 事件                                           │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ 完成 (currentPhase = 'done')                                 │
│                                                              │
│ • 显示完整答案                                               │
│ • 显示搜索来源引用                                           │
│ • 支持追问                                                   │
└─────────────────────────────────────────────────────────────┘
```

## 测试验证

### 手动测试步骤

1. **启动开发服务器**:
   ```bash
   cd frontend-nextjs
   npm run dev
   ```

2. **打开搜索页面**: http://localhost:3001/search

3. **输入测试查询**: "深圳湾海景别墅设计概念"

4. **验证调试面板**:
   - 在搜索进度卡片右上角应该看到虫子图标
   - 点击展开调试面板，观察 `currentPhase` 变化

5. **验证阶段转换**:
   - 分析阶段: `currentPhase = 'analysis'`
   - 搜索阶段: `currentPhase = 'search'`
   - 综合阶段: `currentPhase = 'synthesis'`
   - 完成: `currentPhase = 'done'`

6. **验证UI一致性**:
   - 所有卡片使用统一的扁平化样式
   - 搜索规划和轮次结果在同一个卡片中显示
   - 没有重复的进度显示

## 后续计划

### 第二阶段优化（建议）

1. **清理冗余状态字段**:
   - 合并 `l0Content` / `analysisContent`
   - 合并 `thinkingContent` / `currentRoundReasoning` / `currentRoundThinking`

2. **补充缺失的 SSE 事件处理**:
   - `ready_to_answer`
   - `narrative_reflection`
   - `phase_checkpoint`
   - `search_retrospective`

3. **删除未使用的组件**:
   - `components/search/UcpptSearchProgress.tsx`（未被引用）

4. **修复后端 SSE 事件格式**:
   - `unified_dialogue_chunk` 使用 `{"type": ..., "content": ...}` 格式
   - 应该改为 `{"type": ..., "data": {"content": ...}}` 与其他事件一致

## 相关文档

- [搜索流程全面诊断报告](诊断报告在对话历史中)
- [v7.219 持久化链路修复](IMPLEMENTATION_v7.219_PERSISTENCE_FIX.md)
- [开发规范](/.github/DEVELOPMENT_RULES_CORE.md)
