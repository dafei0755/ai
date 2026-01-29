# BUG_FIX v7.188: 深度思考内容融入搜索轮次

## 问题描述

用户反馈三个问题：

1. **`[object Object]` 显示问题**: 在"深度推理"部分显示 `[object Object]` 而非实际思考内容
2. **思考内容位置问题**: "深度推理"显示为独立卡片，而非融入各轮搜索中
3. **每轮思考不可见**: 无法看到每轮搜索的具体思考过程

## 用户需求

- 思考内容可折叠，**默认展开**
- **推理过程**（is_reasoning=true）与**最终思考**（is_reasoning=false）分开展示

## 根本原因分析

### 问题 1: `[object Object]`
- 文件: `frontend-nextjs/app/search/[session_id]/page.tsx`
- 原因: 存在两个 `thinking_chunk` 事件处理器
  - 第一个 (~L445): 正确提取 `data.content`
  - 第二个 (~L728): 错误地直接连接 `data` 对象到字符串

### 问题 2 & 3: 思考内容位置
- 原因: 所有思考内容累积到全局 `thinkingContent`，通过独立的 `renderThinking()` 渲染
- 无法将思考内容与具体轮次关联

## 修复方案

### 1. 扩展 `RoundRecord` 接口

```tsx
interface RoundRecord {
  // ... 现有字段 ...
  // v7.188: 思考内容（融入轮次而非单独卡片）
  reasoningContent?: string;  // 推理过程（is_reasoning=true）
  thinkingContent?: string;   // 最终思考（is_reasoning=false）
  showThinking?: boolean;     // 是否展开思考内容
}
```

### 2. 扩展 `SearchState` 接口

```tsx
interface SearchState {
  // ... 现有字段 ...
  currentRoundReasoning: string;     // v7.188: 当前轮推理过程
  currentRoundThinking: string;      // v7.188: 当前轮最终思考
}
```

### 3. 修复 `[object Object]` Bug

```tsx
// 之前（错误）
setSearchState(prev => ({
  ...prev,
  thinkingContent: prev.thinkingContent + data,  // data 是对象！
}));

// 之后（正确）
setSearchState(prev => ({
  ...prev,
  thinkingContent: prev.thinkingContent + (typeof data === 'string' ? data : (data.content || '')),
}));
```

### 4. 修改 `thinking_chunk` 处理器

```tsx
case 'thinking_chunk':
  setSearchState(prev => {
    const content = data.content || '';
    const isReasoning = data.is_reasoning === true;
    return {
      ...prev,
      status: 'thinking',
      isThinking: true,
      // v7.188: 分别累积推理过程和最终思考
      currentRoundReasoning: isReasoning ? prev.currentRoundReasoning + content : prev.currentRoundReasoning,
      currentRoundThinking: !isReasoning ? prev.currentRoundThinking + content : prev.currentRoundThinking,
      thinkingContent: prev.thinkingContent + content,
      statusMessage: isReasoning ? `第 ${data.round} 轮：深度推理中...` : `第 ${data.round} 轮：思考中...`,
    };
  });
  break;
```

### 5. 修改 `round_start` 处理器

```tsx
case 'round_start':
  setSearchState(prev => ({
    ...prev,
    // v7.188: 新轮次开始时清空当前轮思考内容
    currentRoundReasoning: '',
    currentRoundThinking: '',
    // ... 其他字段
  }));
  break;
```

### 6. 修改 `round_sources` 处理器

```tsx
const newRound: RoundRecord = {
  // ... 现有字段 ...
  // v7.188: 保存当前轮的思考内容
  reasoningContent: prev.currentRoundReasoning,
  thinkingContent: prev.currentRoundThinking,
  showThinking: true,  // 默认展开
};
```

### 7. 在轮次渲染中添加思考内容 UI

在每轮搜索卡片中添加可折叠的思考内容区域：

```tsx
{/* v7.188: 在轮次中显示思考内容 */}
{(round.reasoningContent || round.thinkingContent) && (
  <div className="mt-4 pt-4 border-t border-[var(--border-color)]">
    <div
      className="flex items-center justify-between cursor-pointer hover:bg-purple-50 dark:hover:bg-purple-900/20 rounded-lg p-2 -mx-2"
      onClick={() => {
        setSearchState(prev => ({
          ...prev,
          rounds: prev.rounds.map(r =>
            r.roundNum === round.roundNum
              ? { ...r, showThinking: !r.showThinking }
              : r
          ),
        }));
      }}
    >
      <div className="flex items-center gap-2">
        <Brain className="w-4 h-4 text-purple-600 dark:text-purple-400" />
        <span className="text-sm font-medium text-purple-600 dark:text-purple-400">
          深度推理过程
        </span>
        {round.reasoningContent && (
          <span className="text-xs px-1.5 py-0.5 bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 rounded">
            深度推理
          </span>
        )}
      </div>
      <ChevronRight className={`w-4 h-4 text-purple-600 dark:text-purple-400 transition-transform ${round.showThinking ? 'rotate-90' : ''}`} />
    </div>

    {round.showThinking && (
      <div className="mt-2 space-y-3">
        {/* 推理过程 */}
        {round.reasoningContent && (
          <div className="bg-gradient-to-r from-purple-50 to-indigo-50 dark:from-purple-900/20 dark:to-indigo-900/20 rounded-lg p-3 border border-purple-200 dark:border-purple-800">
            <div className="flex items-center gap-2 mb-2">
              <Sparkles className="w-4 h-4 text-purple-500" />
              <span className="text-xs font-medium text-purple-600 dark:text-purple-400">推理过程</span>
            </div>
            <div className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap max-h-[200px] overflow-y-auto custom-scrollbar">
              {round.reasoningContent}
            </div>
          </div>
        )}

        {/* 最终思考 */}
        {round.thinkingContent && (
          <div className="bg-gradient-to-r from-blue-50 to-cyan-50 dark:from-blue-900/20 dark:to-cyan-900/20 rounded-lg p-3 border border-blue-200 dark:border-blue-800">
            <div className="flex items-center gap-2 mb-2">
              <Brain className="w-4 h-4 text-blue-500" />
              <span className="text-xs font-medium text-blue-600 dark:text-blue-400">思考总结</span>
            </div>
            <div className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap max-h-[200px] overflow-y-auto custom-scrollbar">
              {round.thinkingContent}
            </div>
          </div>
        )}
      </div>
    )}
  </div>
)}
```

### 8. 修改 `renderThinking()` 函数

```tsx
// v7.188: 仅在搜索进行中显示实时思考进度，搜索完成后思考内容已融入各轮次
const renderThinking = () => {
  const { thinkingContent, status, isThinking } = searchState;

  // v7.188: 搜索完成后不再显示独立的思考卡片（内容已融入各轮次）
  if (status === 'complete' || status === 'error') return null;

  // 正在思考或有思考内容时显示
  if (!thinkingContent && !isThinking) return null;

  // ... 其余逻辑保持不变
};
```

## 修改的文件

- `frontend-nextjs/app/search/[session_id]/page.tsx`

## 用户体验改进

### 修复前
- 显示 `[object Object]`
- 思考过程在独立卡片中
- 无法区分推理过程和最终思考
- 无法关联到具体轮次

### 修复后
- ✅ 正确显示思考内容
- ✅ 每轮搜索卡片内显示该轮的思考过程
- ✅ 推理过程（紫色渐变背景）和最终思考（蓝色渐变背景）分开展示
- ✅ 可折叠，默认展开
- ✅ 搜索进行中仍可看到实时思考进度
- ✅ 搜索完成后，思考内容保留在各轮次中

## 版本信息

- **版本**: v7.188
- **日期**: 2025-01-07
- **类型**: Bug 修复 + 功能增强
