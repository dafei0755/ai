# BUG FIX v7.227: 搜索进度卡片扁平化与取消折叠

## 修复日期
2025-01-XX

## 问题描述

用户反馈三个主要问题：
1. **UI样式老版本**: 搜索进度卡片使用旧版渐变背景，需要扁平化
2. **各轮搜索没有结果**: 搜索来源未正确显示
3. **多轮搜索需要全部呈现**: 不应使用折叠功能，所有内容直接展示

## 修复方案

### 1. 完全重写 `UnifiedSearchProgressCard` 组件

**修改文件**: `frontend-nextjs/app/search/[session_id]/page.tsx`

**核心改动**:

1. **移除折叠逻辑**:
   - 删除 `useState` 的 `expandedRounds` 和 `showDebugPanel` 状态
   - 删除 `toggleRound` 函数
   - 所有轮次内容直接展示，无折叠/展开切换

2. **扁平化样式**:
   - 主容器改为 `space-y-3`，无包裹卡片
   - 搜索规划使用 `bg-blue-50` 背景
   - 各轮次使用简洁的 `bg-white border border-gray-200` 样式
   - 移除渐变背景和复杂阴影

3. **搜索结果直接展示**:
   - 每个轮次的 `sources` 直接渲染，无需点击展开
   - 使用统一的卡片式链接样式
   - 无来源时显示 "本轮未找到相关来源" 提示

## 代码变更

### 新结构

```tsx
<div className="mb-4 space-y-3">
  {/* 标题栏 - 简化扁平化 */}
  <div className="flex items-center gap-3 px-1">...</div>

  {/* 搜索规划 */}
  {searchPlan && (
    <div className="bg-blue-50 rounded-lg p-3">...</div>
  )}

  {/* 轮次列表 - 全部展开，无折叠 */}
  {searchRounds.map((round) => (
    <div className="bg-white border border-gray-200 rounded-lg p-3">
      {/* 轮次标题行 */}
      {/* 搜索查询 */}
      {/* 来源列表 - 直接展示 */}
    </div>
  ))}

  {/* 实时思考进度 */}
  {isSearching && ...}
</div>
```

### 样式变化

| 元素 | 旧样式 | 新样式 |
|------|--------|--------|
| 容器 | `bg-white rounded-xl overflow-hidden` | `space-y-3` (无包裹) |
| 轮次卡片 | 可折叠 + 渐变头部 | 固定展开 + 简洁边框 |
| 来源预览 | 仅折叠时显示2个 | 全部直接显示 |
| 思考过程 | 隐藏在折叠内 | 搜索中时直接显示 |

## 向后兼容

- 保留 `isExpanded` 和 `onToggle` 参数以兼容调用端，但不再使用
- 可在后续版本中清理调用端代码

## 测试验证

1. 清理 `.next` 缓存
2. 重启前端开发服务器
3. 验证：
   - [ ] 搜索进度使用扁平化样式
   - [ ] 所有轮次内容直接显示
   - [ ] 各轮次的搜索来源正确展示
   - [ ] 无折叠/展开按钮

## 文件变更

- `frontend-nextjs/app/search/[session_id]/page.tsx`
  - 行 578-760: 重写 `UnifiedSearchProgressCard` 组件
