# v7.188 思考UI优化修复

## 修复日期
2025-01-07

## 问题描述

用户反馈 v7.188 的思考内容显示存在以下问题：
1. **"深度推理"和"思考总结"分开显示**：应该合并为统一的"思考过程"
2. **"第 X 轮"在多处重复显示**：statusMessage 和轮次卡片都显示了轮次信息
3. **思考内容不是流式显示**：看不到实时的思考过程

## 修复方案

### 1. 合并"深度推理"和"思考总结"

**文件**: `frontend-nextjs/app/search/[session_id]/page.tsx`

将原来分开的两个部分：
- "深度推理" (reasoningContent, is_reasoning=true)
- "思考总结" (thinkingContent, is_reasoning=false)

合并为统一的"思考过程"区块，内容连续显示。

**修改前**：
```tsx
{/* 推理过程（is_reasoning=true）*/}
{round.reasoningContent && (
  <div className="mb-3">
    <div className="flex items-center gap-1 mb-2">
      <Sparkles className="w-3.5 h-3.5 text-purple-500" />
      <span>深度推理</span>
    </div>
    ...
  </div>
)}

{/* 最终思考（is_reasoning=false）*/}
{round.thinkingContent && (
  <div>
    <div className="flex items-center gap-1 mb-2">
      <Brain className="w-3.5 h-3.5 text-indigo-500" />
      <span>思考总结</span>
    </div>
    ...
  </div>
)}
```

**修改后**：
```tsx
{/* 思考内容 - 合并显示 */}
{round.showThinking !== false && (
  <div className="px-4 py-3 ...">
    <div className="text-sm ... whitespace-pre-wrap">
      {round.reasoningContent}
      {round.reasoningContent && round.thinkingContent && '\n\n'}
      {round.thinkingContent}
    </div>
  </div>
)}
```

### 2. 移除 statusMessage 中的"第 X 轮"前缀

避免与轮次卡片上的轮次信息重复。

**修改点**：

1. `thinking_chunk` 事件：
   - `第 ${data.round} 轮：深度推理中...` → `深度推理中...`
   - `第 ${data.round} 轮：思考中...` → `思考中...`

2. `narrative_thinking` 事件：
   - `第 ${data.round} 轮：思考完成` → `思考完成`

3. `round_start` 事件：
   - `第 ${data.round} 轮 | 已回答...` → `已回答... | 探索: ...`

4. `round_reflecting` 事件：
   - `第 ${data.round} 轮：评估信息充分度...` → `评估信息充分度...`

5. `round_complete` 事件：
   - `第 ${data.round} 轮完成` → `搜索完成`

### 3. 添加实时流式思考显示

在搜索进行中（`status === 'thinking'`），添加实时显示当前轮次思考内容的区块：

```tsx
{/* v7.188: 实时流式显示当前轮次的思考内容 */}
{isSearching && status === 'thinking' && (searchState.currentRoundReasoning || searchState.currentRoundThinking) && (
  <div className="bg-gradient-to-r from-purple-50 to-indigo-50 ...">
    <div className="px-4 py-2 ...">
      <Brain className="w-4 h-4 text-purple-600 animate-pulse" />
      <span>第 {searchState.currentThinkingRound} 轮 · 思考中...</span>
    </div>
    <div className="px-4 py-3">
      <div className="... whitespace-pre-wrap">
        {searchState.currentRoundReasoning || searchState.currentRoundThinking}
        <span className="inline-block w-2 h-4 bg-purple-500 ml-1 animate-pulse rounded-sm" />
      </div>
    </div>
  </div>
)}
```

特点：
- 仅在搜索进行中（`isSearching && status === 'thinking'`）显示
- 显示当前轮次编号
- 实时更新思考内容（流式显示）
- 带有动态光标动画提示正在输入
- 搜索完成后自动隐藏，内容保存在各轮次卡片中

## 修改文件

- `frontend-nextjs/app/search/[session_id]/page.tsx`

## 用户体验改进

1. **更简洁的界面**：不再有重复的轮次信息
2. **统一的思考显示**：推理和思考内容合并，阅读更连贯
3. **实时反馈**：搜索过程中可以看到实时的思考过程
4. **清晰的状态提示**：光标动画提示正在进行

## 验证方法

1. 启动前端开发服务器
2. 进行一次深度搜索
3. 观察：
   - 搜索过程中是否显示实时思考内容
   - statusMessage 中是否不再显示"第 X 轮"
   - 各轮次卡片中是否统一显示"思考过程"而非分开的两个部分
