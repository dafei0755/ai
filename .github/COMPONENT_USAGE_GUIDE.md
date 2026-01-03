# 前端组件使用规范

## 问卷组件选择指南

### ✅ 推荐使用：UnifiedProgressiveQuestionnaireModal（完整版）

**文件位置**：`frontend-nextjs/components/UnifiedProgressiveQuestionnaireModal.tsx`

**适用场景**：
- ✅ **所有生产环境**（强制要求）
- ✅ Step 1: 任务梳理（核心任务拆解）
- ✅ Step 2: 雷达图维度调整
- ✅ Step 3: 补充信息收集

**功能特性**：
- ✅ 12种动机类型标签展示
- ✅ AI推理说明（`ai_reasoning`字段）
- ✅ 关键词标签（`source_keywords`）
- ✅ 任务依赖关系（`dependencies` + `execution_order`）
- ✅ 任务编辑功能（标题、描述、类型、优先级）
- ✅ 完整的数据验证和错误处理

**导入方式**：
```tsx
import { UnifiedProgressiveQuestionnaireModal } from '@/components/UnifiedProgressiveQuestionnaireModal';
```

**使用示例**：
```tsx
<UnifiedProgressiveQuestionnaireModal
  isOpen={showQuestionnaire}
  data={questionnaireData}
  onConfirm={handleQuestionnaireConfirm}
  onSkip={handleQuestionnaireSkip}
/>
```

---

### ❌ 已废弃：ProgressiveQuestionnaireModal（简化版）

**文件位置**：`frontend-nextjs/components/ProgressiveQuestionnaireModal.tsx`

**废弃日期**：2026-01-02
**计划删除日期**：2026-02-01

**废弃原因**：
1. **功能不完整**：缺少v7.106新增的6个关键功能
2. **历史问题**：导致依赖关系等功能不显示（详见 `QUESTIONNAIRE_UI_FIX.md`）
3. **维护成本**：双组件并存增加bug风险

**缺失功能列表**：
- ❌ 动机类型标签
- ❌ AI推理说明
- ❌ 关键词标签
- ❌ 依赖关系显示
- ❌ 任务编辑功能
- ❌ 执行顺序显示

**迁移指南**：
```diff
- import { ProgressiveQuestionnaireModal } from '@/components/ProgressiveQuestionnaireModal';
+ import { UnifiedProgressiveQuestionnaireModal } from '@/components/UnifiedProgressiveQuestionnaireModal';

- <ProgressiveQuestionnaireModal
+ <UnifiedProgressiveQuestionnaireModal
    isOpen={showQuestionnaire}
    data={questionnaireData}
    onConfirm={handleQuestionnaireConfirm}
    onSkip={handleQuestionnaireSkip}
  />
```

**注意**：
- ⚠️ 两个组件的Props接口完全兼容，可以直接替换
- ⚠️ 如果发现代码中仍在使用简化版，请立即修改
- ⚠️ 新功能开发严禁使用简化版组件

---

## 其他问卷相关组件

### QuestionnaireModal（传统版）

**文件位置**：`frontend-nextjs/components/QuestionnaireModal.tsx`

**适用场景**：
- ✅ Step 2: 战略校准问卷（calibration_questionnaire）
- ✅ 非递进式的单步问卷

**特点**：
- 单步问卷，无多步导航
- 用于独立的问答环节
- 不包含任务卡片展示

**导入方式**：
```tsx
import { QuestionnaireModal } from '@/components/QuestionnaireModal';
```

---

### UserQuestionModal（用户追问）

**文件位置**：`frontend-nextjs/components/UserQuestionModal.tsx`

**适用场景**：
- ✅ 专家向用户提出的追问
- ✅ 在分析过程中需要澄清的问题

**特点**：
- 轻量级问答框
- 支持单选、多选、开放题
- 实时提交答案

**导入方式**：
```tsx
import { UserQuestionModal } from '@/components/UserQuestionModal';
```

---

## 组件选择决策树

```
是否为三步递进式问卷？
├── 是 → 使用 UnifiedProgressiveQuestionnaireModal ✅
│   ├── Step 1: 任务梳理
│   ├── Step 2: 雷达图维度
│   └── Step 3: 补充信息
│
├── 否 → 是否为战略校准问卷？
    ├── 是 → 使用 QuestionnaireModal ✅
    │
    └── 否 → 是否为专家追问？
        ├── 是 → 使用 UserQuestionModal ✅
        └── 否 → 需要自定义组件
```

---

## 强制规范

### 1. 代码审查检查点

在提交PR前，必须检查：
- [ ] 是否导入了 `ProgressiveQuestionnaireModal`（简化版）？→ 如果是，**拒绝合并**
- [ ] 是否使用了 `<ProgressiveQuestionnaireModal ...>`？→ 如果是，**拒绝合并**
- [ ] 是否在正确的场景使用了正确的组件？

### 2. ESLint规则（未来计划）

```js
// .eslintrc.js
{
  "rules": {
    "no-restricted-imports": ["error", {
      "patterns": [{
        "group": ["**/ProgressiveQuestionnaireModal"],
        "message": "⚠️ ProgressiveQuestionnaireModal已废弃，请使用UnifiedProgressiveQuestionnaireModal"
      }]
    }]
  }
}
```

### 3. 文件删除计划

```
2026-01-02: 添加废弃警告 ✅
2026-01-15: 代码库全面扫描，确保无引用
2026-02-01: 删除 ProgressiveQuestionnaireModal.tsx
```

---

## 常见问题

### Q: 为什么要废弃简化版组件？

A: 简化版组件缺少6个关键功能，导致用户体验降级。2026-01-02有用户报告"依赖关系不显示"，排查后发现是因为误用了简化版组件。为防止类似问题，统一使用完整版。

### Q: 两个组件的性能差异？

A: 完整版组件增加了约200行代码，但性能影响可忽略（<1ms渲染差异）。相比功能完整性，这个开销可以接受。

### Q: 如果我需要一个轻量级的问卷组件怎么办？

A: 请创建新的专用组件，而不是复用已废弃的简化版。新组件应该：
- 明确命名用途（如 `LightweightQuestionnaireModal`）
- 记录使用场景
- 添加到本文档

### Q: 废弃后的文件何时删除？

A: 计划于2026-02-01删除。在此之前保留文件是为了：
1. 紧急回退需要（如果完整版出现严重bug）
2. 给开发者时间迁移代码
3. 逐步验证完整版的稳定性

---

## 相关文档

- [问卷UI修复报告](../QUESTIONNAIRE_UI_FIX.md) - 2026-01-02发现的问题
- [v7.106功能说明](../DIMENSION_LLM_GENERATION_v7.106.md) - 12种动机类型实现
- [历史修复记录](../.github/historical_fixes/) - 类似问题的修复案例

---

## 更新日志

- **2026-01-02**: 创建本文档，标记 `ProgressiveQuestionnaireModal` 为废弃

---

**维护者**: @dafei0755
**最后更新**: 2026-01-02
**文档状态**: ✅ 生效中
