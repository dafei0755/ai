# 搜索引用组件集成指南 (v7.113)

## 📦 已创建的组件

### 1. SearchReferences（基础版）
**文件**: `frontend-nextjs/components/SearchReferences.tsx`
**特点**:
- 展示所有搜索引用
- 支持按工具筛选
- 支持关键词搜索
- 可展开/收起详情

### 2. ExpertSearchReferences（专家分组版）
**文件**: `frontend-nextjs/components/ExpertSearchReferences.tsx`
**特点**:
- 按专家分组展示
- 显示每个专家使用的搜索资料
- 统计搜索工具使用情况
- 更适合理解专家工作流程

---

## 🔧 在报告页面中集成

### 步骤 1: 导入组件

在 `frontend-nextjs/app/report/[sessionId]/page.tsx` 文件顶部添加导入：

```typescript
import { SearchReferences } from '@/components/SearchReferences';
import { ExpertSearchReferences } from '@/components/ExpertSearchReferences';
```

### 步骤 2: 在渲染函数中添加组件

找到 `renderContent()` 函数，在报告内容渲染的末尾添加搜索引用组件。

**推荐位置**: 在 "原始文本视图" 或结构化报告内容之后

```typescript
const renderContent = () => {
  // ... 现有代码 ...

  return (
    <div className="space-y-6">
      {/* 报告头部 */}
      <div className="bg-[var(--card-bg)] border border-[var(--border-color)] rounded-2xl p-6">
        {/* ... 现有头部内容 ... */}
      </div>

      {/* 结构化报告或原始文本 */}
      {report.structuredReport ? (
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-6">
          {/* ... 现有报告内容 ... */}
        </div>
      ) : (
        <div className="bg-[var(--card-bg)] border border-[var(--border-color)] rounded-2xl p-6">
          {/* ... 原始文本视图 ... */}
        </div>
      )}

      {/* 🆕 v7.113: 搜索引用组件 */}
      {report.structuredReport?.search_references &&
       report.structuredReport.search_references.length > 0 && (
        <>
          {/* 选项1: 基础版 - 展示所有引用 */}
          <SearchReferences
            references={report.structuredReport.search_references}
            className="mt-6"
          />

          {/* 选项2: 专家分组版 - 按专家展示（可选，二选一） */}
          {/* <ExpertSearchReferences
            references={report.structuredReport.search_references}
            expertReports={report.structuredReport.expert_reports}
            className="mt-6"
          /> */}
        </>
      )}
    </div>
  );
};
```

---

## 🎨 样式说明

组件已内置Tailwind CSS样式，与报告页面的暗色主题兼容。

### 主题适配

如果需要适配暗色主题，可以修改组件中的样式类：

```typescript
// 将白色背景改为暗色
bg-white → bg-[var(--card-bg)]

// 将灰色文本改为浅色
text-gray-900 → text-white
text-gray-600 → text-gray-300
text-gray-500 → text-gray-400

// 边框颜色
border-gray-200 → border-[var(--border-color)]
```

---

## 📊 两个组件的对比

### SearchReferences（基础版）
**优点**:
- 简洁直观
- 适合快速浏览所有引用
- 强大的筛选和搜索功能

**适用场景**:
- 用户想要快速查看所有参考资料
- 需要按工具类型筛选
- 需要搜索特定关键词

**预览**:
```
📚 参考文献
专家分析使用的搜索资料 · 15 条引用

[搜索框] [工具筛选: 所有来源 ▼]

1. 现代简约室内设计案例 2024 🔍 博查搜索
   摘要: 本文介绍了现代简约风格的室内设计案例...
   查询: 现代简约 室内设计 2024 | 相关性: 85%

2. Audrey Hepburn 风格住宅空间研究 📚 arXiv学术
   ...
```

---

### ExpertSearchReferences（专家分组版）
**优点**:
- 按专家分组，理解专家工作流程
- 看到每个专家使用了哪些资料
- 更好的组织结构

**适用场景**:
- 想要了解每个专家的研究过程
- 需要验证专家的资料来源
- 分析专家之间的资料差异

**预览**:
```
👥 专家搜索资料
5 位专家 · 15 条引用

┌─ V2 设计总监
│  3 条引用 · 🔍 2 📚 1
│
│  1. 现代简约室内设计案例 2024
│  2. 居住空间设计指南
│  3. ...
│
├─ V3 技术架构师
│  2 条引用 · 🌐 2
│  ...
```

---

## 🔍 完整集成示例

```typescript
'use client';

import { useState, useEffect } from 'react';
import { SearchReferences } from '@/components/SearchReferences';
import { ExpertSearchReferences } from '@/components/ExpertSearchReferences';
// ... 其他导入 ...

export default function ReportPage() {
  // ... 现有状态和逻辑 ...

  const renderContent = () => {
    if (fetchStatus === 'loading') {
      return <LoadingState />;
    }

    if (fetchStatus === 'error') {
      return <ErrorState />;
    }

    if (!report?.reportText) {
      return <GeneratingState />;
    }

    return (
      <div className="space-y-6">
        {/* 报告头部 */}
        <ReportHeader />

        {/* 报告主体内容 */}
        {report.structuredReport ? (
          <StructuredReportView />
        ) : (
          <PlainTextReportView />
        )}

        {/* 🆕 v7.113: 搜索引用 - 条件渲染 */}
        {report.structuredReport?.search_references?.length > 0 && (
          <div className="space-y-4">
            {/* 分隔线 */}
            <div className="border-t border-[var(--border-color)] my-8" />

            {/* 选择使用哪个组件 */}
            <ExpertSearchReferences
              references={report.structuredReport.search_references}
              expertReports={report.structuredReport.expert_reports}
            />
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-[var(--background)]">
      <Header />
      <main className="max-w-7xl mx-auto px-6 py-10">
        {renderContent()}
      </main>
      <FollowupDialog />
    </div>
  );
}
```

---

## ✅ 验证清单

集成完成后，请检查：

- [ ] 组件文件已创建
  - [ ] `SearchReferences.tsx`
  - [ ] `ExpertSearchReferences.tsx`

- [ ] 报告页面已导入组件
  - [ ] import语句正确
  - [ ] 组件正确放置在renderContent()中

- [ ] 数据正确传递
  - [ ] `report.structuredReport?.search_references` 存在
  - [ ] 数据格式正确（数组）

- [ ] 样式正确显示
  - [ ] 组件渲染正常
  - [ ] 颜色主题协调
  - [ ] 响应式布局正常

- [ ] 功能正常
  - [ ] 可以展开/收起
  - [ ] 筛选功能工作
  - [ ] 搜索功能工作
  - [ ] 链接可点击

---

## 🐛 常见问题

### Q1: 组件不显示？
**检查**:
1. `search_references` 字段是否存在且不为空
2. 条件渲染逻辑是否正确
3. 浏览器Console是否有错误

**解决**:
```typescript
// 添加调试日志
console.log('搜索引用数据:', report.structuredReport?.search_references);

// 确保条件正确
{report.structuredReport?.search_references?.length > 0 && (
  <SearchReferences ... />
)}
```

---

### Q2: 样式不协调？
**检查**: 是否需要适配暗色主题

**解决**: 参考上面的"主题适配"部分修改颜色类

---

### Q3: TypeScript类型错误？
**检查**: `types/index.ts` 是否已更新

**解决**: 确保类型定义包含 `search_references` 字段

---

## 🎯 下一步建议

1. **添加PDF导出支持**: 在PDF报告中也包含参考文献章节
2. **添加统计面板**: 显示搜索工具使用统计、来源分布等
3. **添加引用质量评分**: 可视化展示每条引用的相关性评分
4. **添加导出功能**: 导出引用列表为BibTeX、EndNote等格式

---

**集成完成后，记得测试以下场景**:
- ✅ 有搜索引用的报告
- ✅ 没有搜索引用的报告
- ✅ 搜索引用为空数组的报告
- ✅ 移动端显示
