# 问卷UI样式统一更新 v7.109

**更新时间**: 2024-12-31
**关联版本**: v7.105-v7.109
**影响范围**: 前端UI统一性

---

## 📋 更新概述

将`UnifiedProgressiveQuestionnaireModal`组件的所有硬编码颜色统一为主页面CSS变量，实现与整个对话流程的视觉一致性。

---

## 🎨 统一的CSS变量

### 核心颜色变量
```css
--primary              主色调（蓝色）- 用于按钮、图标、强调元素
--primary-hover        主色调hover状态
--card-bg             卡片背景色
--background          页面背景色
--sidebar-bg          侧边栏/次级背景色
--foreground          主要文本颜色
--foreground-secondary 次要文本颜色
--border-color        边框颜色
```

### 暗色模式支持
- 所有颜色自动适配暗色模式
- 移除所有`dark:bg-xxx`和`dark:text-xxx`硬编码
- 通过CSS变量实现主题切换

---

## 🔄 详细修改清单

### 1. 外层容器统一
**修改前**:
```tsx
<div className="fixed inset-0 bg-black/50 z-50">
  <div className="bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-700">
```

**修改后**:
```tsx
<div className="fixed inset-0 bg-black/50 z-50">
  <div className="bg-[var(--card-bg)] border-[var(--border-color)]">
```

---

### 2. 步骤指示器统一
**修改前**:
```tsx
// 当前步骤
<div className="bg-blue-600 text-white">
// 完成步骤
<div className="bg-green-500">
// 未完成步骤
<div className="bg-gray-300 dark:bg-gray-600">
// 连接线
<div className="bg-gray-300 dark:bg-gray-600">
```

**修改后**:
```tsx
// 当前步骤
<div className="bg-[var(--primary)] text-white">
// 完成步骤
<div className="bg-green-500"> // 保留绿色表示完成
// 未完成步骤
<div className="bg-[var(--sidebar-bg)]">
// 连接线
<div className="bg-[var(--border-color)]">
```

---

### 3. Header区域统一
**修改前**:
```tsx
<div className="bg-gradient-to-r from-blue-50 to-indigo-50">
  <h2 className="text-gray-900 dark:text-white">
  <p className="text-gray-500 dark:text-gray-400">
```

**修改后**:
```tsx
<div className="bg-[var(--background)]">
  <h2 className="text-[var(--foreground)]">
  <p className="text-[var(--foreground-secondary)]">
```

---

### 4. Step 1内容统一
**修改前**:
```tsx
// 需求摘要卡片
<div className="bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200">
  <h3 className="text-blue-900">
  <p className="text-gray-700">

// 任务卡片
<div className="bg-white dark:bg-gray-800 border-gray-200">
  <div className="bg-gradient-to-br from-blue-500 to-indigo-600">
  <h4 className="text-gray-900 group-hover:text-blue-600">
  <p className="text-gray-600">

// 关键词标签
<span className="bg-blue-100 text-blue-700">
```

**修改后**:
```tsx
// 需求摘要卡片
<div className="bg-[var(--card-bg)] border-[var(--border-color)]">
  <h3 className="text-[var(--primary)]">
  <p className="text-[var(--foreground-secondary)]">

// 任务卡片
<div className="bg-[var(--card-bg)] border-[var(--border-color)]">
  <div className="bg-[var(--primary)]">
  <h4 className="text-[var(--foreground)]">
  <p className="text-[var(--foreground-secondary)]">

// 关键词标签
<span className="bg-[var(--primary)]/10 text-[var(--primary)]">
```

---

### 5. Step 2雷达图统一
**修改前**:
```tsx
// 提示区域
<div className="bg-gradient-to-r from-purple-50 to-pink-50 border-purple-200">
  <p className="text-gray-700">

// 雷达图卡片
<div className="bg-white dark:bg-gray-800 border-gray-200">
  <h3 className="text-gray-900">
  <p className="text-gray-500">

// 滑块卡片
<div className="bg-white border-gray-200">
  <div className="bg-gradient-to-br from-purple-500 to-pink-600">
  <span className="text-gray-900">
  <span className="text-blue-600 bg-blue-100">
  <span className="text-gray-500">
  <div className="bg-gradient-to-r from-gray-300">
  <input className="bg-gray-200 accent-blue-600">
  <p className="text-gray-500 bg-gray-50">
```

**修改后**:
```tsx
// 提示区域
<div className="bg-[var(--card-bg)] border-[var(--border-color)]">
  <p className="text-[var(--foreground-secondary)]">

// 雷达图卡片
<div className="bg-[var(--card-bg)] border-[var(--border-color)]">
  <h3 className="text-[var(--foreground)]">
  <p className="text-[var(--foreground-secondary)]">

// 滑块卡片
<div className="bg-[var(--card-bg)] border-[var(--border-color)]">
  <div className="bg-[var(--primary)]">
  <span className="text-[var(--foreground)]">
  <span className="text-[var(--primary)] bg-[var(--primary)]/10">
  <span className="text-[var(--foreground-secondary)]">
  <div className="bg-[var(--border-color)]">
  <input className="bg-[var(--sidebar-bg)] accent-[var(--primary)]">
  <p className="text-[var(--foreground-secondary)] bg-[var(--sidebar-bg)]">
```

---

### 6. Step 3问卷统一
**修改前**:
```tsx
// 介绍区域
<div className="bg-gradient-to-r from-green-50 to-emerald-50 border-green-200">
  <p className="text-gray-700">

// 问题卡片
<div className="bg-white dark:bg-gray-800 border-gray-200">
  <div className="bg-gradient-to-br from-green-500 to-emerald-600">
  <h4 className="text-gray-900">
  <span className="text-gray-400">
  <p className="text-gray-500">

// 单选/多选项
<label className="hover:bg-gray-50">
  <input className="text-blue-600 accent-blue-600">
  <span className="text-gray-700">

// 文本输入框
<textarea className="border-gray-300 focus:ring-blue-500 dark:bg-gray-700">

// Note提示
<div className="text-gray-500 bg-gray-50">
```

**修改后**:
```tsx
// 介绍区域
<div className="bg-[var(--card-bg)] border-[var(--border-color)]">
  <p className="text-[var(--foreground-secondary)]">

// 问题卡片
<div className="bg-[var(--card-bg)] border-[var(--border-color)]">
  <div className="bg-[var(--primary)]">
  <h4 className="text-[var(--foreground)]">
  <span className="text-[var(--foreground-secondary)]">
  <p className="text-[var(--foreground-secondary)]">

// 单选/多选项
<label className="hover:bg-[var(--sidebar-bg)]">
  <input className="text-[var(--primary)] accent-[var(--primary)]">
  <span className="text-[var(--foreground)]">

// 文本输入框
<textarea className="border-[var(--border-color)] focus:ring-[var(--primary)] bg-[var(--background)] text-[var(--foreground)]">

// Note提示
<div className="text-[var(--foreground-secondary)] bg-[var(--sidebar-bg)]">
```

---

### 7. Footer按钮统一
**修改前**:
```tsx
<button className="bg-blue-600 hover:bg-blue-700 text-white">
  确认
</button>
```

**修改后**:
```tsx
<button className="bg-[var(--primary)] hover:bg-[var(--primary-hover)] text-white">
  确认
</button>
```

---

## ✅ 统一后的优势

### 1. 视觉一致性
- 问卷Modal与主页面完全统一
- 颜色语义清晰（主色/背景/文本/边框）
- 暗色模式自动适配

### 2. 代码简洁性
- 移除所有`dark:`前缀重复代码
- 减少硬编码颜色值
- 易于维护和主题切换

### 3. 用户体验
- 无缝的视觉过渡
- 统一的交互反馈
- 专业的品牌一致性

---

## 📊 修改统计

| 类别 | 修改数量 |
|------|---------|
| 外层容器 | 1 |
| 步骤指示器 | 3 |
| Header区域 | 2 |
| Step 1内容 | 4 |
| Step 2雷达图 | 6 |
| Step 3问卷 | 9 |
| Footer按钮 | 1 |
| **总计** | **26处** |

---

## 🧪 测试验证

### 必测场景
1. **亮色模式**
   - [ ] 卡片背景清晰可见
   - [ ] 文本对比度足够
   - [ ] 主色调统一为蓝色
   - [ ] 边框颜色适中

2. **暗色模式**
   - [ ] 卡片背景不刺眼
   - [ ] 文本清晰可读
   - [ ] 主色调保持一致
   - [ ] 边框颜色柔和

3. **交互状态**
   - [ ] hover效果统一
   - [ ] focus状态清晰
   - [ ] 按钮反馈及时
   - [ ] 滑块拖动流畅

4. **三步流程**
   - [ ] Step 1任务列表展示正常
   - [ ] Step 2雷达图颜色协调
   - [ ] Step 3问题表单清晰

---

## 🔧 技术细节

### CSS变量使用规范
```tsx
// ✅ 正确用法
className="bg-[var(--card-bg)]"
className="text-[var(--foreground)]"
className="border-[var(--border-color)]"

// ❌ 避免用法
className="bg-white dark:bg-gray-900"
className="text-gray-900 dark:text-white"
className="border-gray-200 dark:border-gray-700"
```

### 透明度处理
```tsx
// 主色调10%透明度（用于背景）
className="bg-[var(--primary)]/10"

// 保留特殊用途的硬编码（如遮罩层）
className="bg-black/50"
```

---

## 📝 后续建议

1. **主题扩展**
   - 考虑添加更多颜色主题（绿色、紫色等）
   - 通过CSS变量切换整体风格

2. **动画优化**
   - 统一过渡动画时长（200ms）
   - 添加微交互反馈

3. **响应式优化**
   - 移动端适配验证
   - 小屏幕下的布局调整

---

## 📌 相关文档

- [v7.105 统一问卷组件创建](./UNIFIED_QUESTIONNAIRE_v7.105.md)
- [v7.106 必填字段验证](./QUESTIONNAIRE_REQUIRED_FIELDS_UPDATE.md)
- [v7.107 性能优化](./QUESTIONNAIRE_PERFORMANCE_v7.107.md)
- [v7.108 布局优化](无文档)

---

**状态**: ✅ 已完成
**编译状态**: ✅ 无错误
**测试状态**: ⏳ 待测试
