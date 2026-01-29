# v7.151 需求洞察模块实现报告

## 版本信息
- **版本号**: v7.151
- **实现日期**: 2026-01-08
- **模块名称**: Requirements Insight (需求洞察)

---

## 一、实现概述

### 1.1 变更目标
将原有的"问卷汇总"(questionnaire_summary) + "需求确认"(requirements_confirmation) 两个节点合并为一个智能化的"需求洞察"节点，实现：

1. **LLM 深度分析**：从原来 14% 提升到 70%+ LLM 利用率
2. **节点合并**：7→6 个交互点，减少用户操作步骤
3. **增量编辑策略**：<50字符 → 本地更新；>=50字符 → 重新分析
4. **新增洞察维度**：项目本质、隐性需求、关键冲突

### 1.2 核心文件变更

| 文件 | 变更类型 | 主要改动 |
|------|---------|---------|
| `requirements_restructuring.py` | 功能增强 | 新增 3 个 LLM 分析方法 |
| `questionnaire_summary.py` | 重构 | 合并确认逻辑，新增 `_handle_user_response()` |
| `main_workflow.py` | 流程修改 | 移除静态边，使用 Command 动态路由 |
| `QuestionnaireSummaryDisplay.tsx` | UI 升级 | 新增编辑模式、新洞察区块 |
| `UnifiedProgressiveQuestionnaireModal.tsx` | 接口调整 | `handleStep4Confirm()` 传递 modifications |
| `types/index.ts` | 类型扩展 | 新增 5 个 TypeScript 接口字段 |

---

## 二、后端实现详情

### 2.1 需求重构引擎 (`requirements_restructuring.py`)

#### 新增方法 1: `_llm_comprehensive_analysis()`
```python
async def _llm_comprehensive_analysis(
    self,
    questionnaire_data: Dict[str, Any],
    structured_doc: Dict[str, Any]
) -> Dict[str, Any]:
    """
    LLM 综合分析，生成：
    - project_essence: 一句话项目本质
    - implicit_requirements: 隐性需求列表
    - key_conflicts: 关键冲突与解决策略
    """
```
- **调用时机**: `restructure()` 最后阶段
- **输出字段**: 直接合并到返回的 restructured_doc

#### 新增方法 2: `_llm_generate_tension_strategies()`
```python
async def _llm_generate_tension_strategies(
    self,
    tension_description: str,
    context: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    生成核心张力的 3-4 个策略选项，替代原有硬编码模板
    """
```
- **调用条件**: `_extract_core_tension(use_llm=True)`
- **输出格式**: `[{strategy, trade_off, recommended_for}, ...]`

#### 修改方法: `_extract_objectives_with_jtbd()`
- **新增字段**: `understanding_comparison`
  - `user_original`: 用户原始表述
  - `ai_understanding`: AI 理解版本
  - `alignment_score`: 对齐度 (0-100)

### 2.2 问卷汇总节点 (`questionnaire_summary.py`)

#### 节点更名
- **原名**: `questionnaire_summary` (问卷汇总)
- **新名**: `requirements_insight` (需求洞察)
- **交互类型**: `requirements_insight`

#### 新增方法: `_handle_user_response()`
```python
@staticmethod
def _handle_user_response(
    state: ProjectAnalysisState,
    restructured_doc: Dict[str, Any],
    update_dict: Dict[str, Any]
) -> Command:
    """
    处理用户响应，实现增量编辑策略:

    修改量判断:
    - 0 字符: 直接确认 → project_director
    - <50 字符: 微调，更新本地 → project_director
    - >=50 字符: 重大修改 → requirements_analyst
    """
```

#### 路由逻辑
```
用户确认/微调 → project_director (跳过 requirements_confirmation)
重大修改      → requirements_analyst (重新分析)
拒绝         → requirements_analyst
```

### 2.3 工作流边定义 (`main_workflow.py`)

#### 移除静态边
```python
# 🔧 v7.151: 移除，改为 Command 动态路由
# ("questionnaire_summary", "requirements_confirmation"),
```

#### 新的路由逻辑
由 `questionnaire_summary.py` 内部通过 `Command(goto="...")` 决定下一节点

---

## 三、前端实现详情

### 3.1 `QuestionnaireSummaryDisplay.tsx`

#### 新增 UI 区块
1. **项目本质** (`project_essence`)
   - 位置: 页面顶部，紫色渐变背景
   - 图标: Lightbulb

2. **⚠️ 请重点关注** (`key_conflicts` + 高风险 `identified_risks`)
   - 位置: 执行摘要下方
   - 条件: 有关键冲突或高风险时显示

3. **隐性需求** (`implicit_requirements`)
   - 位置: 可折叠区块
   - 默认: 收起

#### 编辑模式
```typescript
const [isEditing, setIsEditing] = useState(false);
const [editedGoal, setEditedGoal] = useState(data.project_objectives?.primary_goal || '');

const handleConfirm = () => {
  if (isEditing && editedGoal !== data.project_objectives?.primary_goal) {
    onConfirm({ primary_goal: editedGoal });
  } else {
    onConfirm();
  }
};
```

### 3.2 `UnifiedProgressiveQuestionnaireModal.tsx`

#### Step 4 确认处理
```typescript
const handleStep4Confirm = (modifications?: Record<string, string>) => {
  if (modifications && Object.keys(modifications).length > 0) {
    onConfirm({
      intent: 'confirm',
      modifications: modifications
    });
  } else {
    handleConfirmClick();
  }
};
```

### 3.3 `types/index.ts`

#### 新增类型字段
```typescript
export interface RestructuredRequirements {
  // ... existing fields ...

  // 🆕 v7.151 新增
  project_essence?: string;
  implicit_requirements?: Array<{
    requirement: string;
    evidence: string;
    priority: 'high' | 'medium' | 'low';
  }>;
  key_conflicts?: Array<{
    conflict: string;
    sides: string[];
    recommended_approach: string;
    trade_off: string;
  }>;

  metadata?: {
    // ... existing ...
    llm_enhanced?: boolean;  // 🆕 v7.151
  };

  project_objectives?: {
    // ... existing ...
    understanding_comparison?: {  // 🆕 v7.151
      user_original: string;
      ai_understanding: string;
      alignment_score: number;
    };
  };

  core_tension?: {
    // ... existing ...
    strategic_options?: Array<{  // 🆕 v7.151
      strategy: string;
      trade_off: string;
      recommended_for: string;
    }>;
  };
}
```

---

## 四、交互类型兼容

前端同时支持新旧两种交互类型：

```typescript
// page.tsx
if (data.interrupt_data.interaction_type === 'progressive_questionnaire_step4'
    || data.interrupt_data.interaction_type === 'requirements_insight') {
  // 显示需求洞察组件
}
```

---

## 五、状态字段

### 动态添加的字段 (不在 TypedDict 中显式定义)
- `restructured_requirements`: 重构后的需求文档
- `questionnaire_summary_completed`: 问卷汇总完成标志
- `user_requirement_adjustments`: 用户编辑的调整内容 (v7.151 新增)
- `has_user_modifications`: 是否有用户修改标志

### 已存在的字段 (state.py 中定义)
- `requirements_confirmed`: 需求确认标志
- `user_modification_processed`: 修改处理标志

---

## 六、测试验证

### 验证点
1. ✅ 后端语法无错误 (`get_errors` 检查通过)
2. ✅ 前端 TypeScript 编译成功 (`npm run build` → `Compiled successfully`)
3. ✅ 交互类型兼容
4. ✅ 工作流边正确定义

### 单元测试结果
| 测试文件 | 通过/总数 | 说明 |
|---------|----------|------|
| `tests/unit/test_questionnaire_summary.py` | **18/18** | 包含 v7.151 新增的 3 个交互测试 |
| `tests/test_questionnaire_flow_integration.py` | **8/8** | Step 1-4 全流程验证 |

### v7.151 新增测试用例
1. `test_minor_modification_updates_locally` - 微调(<50字符)本地更新
2. `test_major_modification_triggers_reanalysis` - 重大修改(>=50字符)触发重新分析
3. `test_rejection_triggers_reanalysis` - 用户拒绝返回分析

### Bug 修复
- **修复**: 重大修改判断逻辑错误 - 原代码在 `is_approved=True` 时忽略修改量判断
- **方案**: 将 `has_major_modification` 检查移到 `is_approved` 之前，优先处理重大修改

---

## 七、流程图更新

### 原流程 (v7.150)
```
Step 3 (雷达图)
    ↓
questionnaire_summary
    ↓
requirements_confirmation  ←── 用户修改 ──→ requirements_analyst
    ↓
project_director
```

### 新流程 (v7.151)
```
Step 3 (雷达图)
    ↓
requirements_insight (需求洞察)
    │
    ├── 确认/微调 ──────────────→ project_director
    │
    └── 重大修改/拒绝 ──────────→ requirements_analyst
```

---

## 八、后续优化建议

1. **state.py 类型定义**: 可选择性将 `user_requirement_adjustments` 添加到 TypedDict
2. **单元测试**: 更新 `test_questionnaire_summary_e2e_v7147.py` 以匹配新交互类型
3. **文档更新**: 更新 `imperative-wishing-boole.md` 反映节点合并
4. **错误处理**: 增强 LLM 超时重试机制

---

## 版本历史
- v7.147: 初始问卷汇总显示实现
- v7.148: 修复类型错误
- v7.149: 增强异常日志
- v7.150: 修复后端4个错误
- **v7.151**: 需求洞察模块 (当前)
