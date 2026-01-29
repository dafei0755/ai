# Bug Fix v7.152: LLM 深度分析独立性增强

## 问题描述

用户测试 session `8pdwoxj8-20260107115426-6fe29cda` 后发现：
- AI洞察显示 "锐度评分: 0/10"、"锐度说明: 待分析"
- `L3_core_tension`、`L4_project_task_jtbd` 均为空
- 数据未能正确生成或传递

## 根因分析

子代理深度调查后发现核心问题：**当前实现是"机械拼接"而非"智能重构"**

| Step | 当前实现 | 问题 |
|------|---------|------|
| Step 1-7 | 纯数据提取，无 LLM | 直接 copy 数据，无智能增强 |
| Step 8 | 仅生成一句话总结 | 太简单，未深度分析 |
| Step 9 | LLM 依赖 `analysis_layers` | `analysis_layers` 通常为空！|

**关键发现**：Step 9 的 `_llm_comprehensive_analysis` 设计为总结 L1-L5 层洞察，但问卷阶段 `analysis_layers` 通常为空，导致 LLM 无法生成有意义的输出。

## 修复方案 (v7.152)

### 1. 增强 `_llm_comprehensive_analysis` 独立性

**修改前**：依赖 `analysis_layers`，为空时返回空结果
**修改后**：
- 直接从 `questionnaire_data` 提取丰富上下文（tasks、gap_filling、dimensions）
- 当 `analysis_layers` 为空时仍能独立工作
- 添加显式 fallback 到 `_fallback_deep_insights`

```python
# 🔧 v7.152: 从 questionnaire_data 提取丰富上下文
if questionnaire_data:
    tasks_data = questionnaire_data.get("tasks", [])
    gap_filling = questionnaire_data.get("gap_filling", {})
    dimensions = questionnaire_data.get("dimensions", {})
    # ... 构建独立的分析上下文
```

### 2. 添加 `_fallback_deep_insights` 方法

当 LLM 调用失败或返回空时，基于规则生成基础洞察：

```python
def _fallback_deep_insights(self, objectives: Dict, constraints: Dict, ...) -> Dict:
    """规则型 fallback，确保总有内容返回"""
    return {
        "project_essence": "一个专注于...",
        "implicit_requirements": [...],
        "key_conflicts": [...]
    }
```

### 3. 增强 Step 1 目标提取

**修改前**：直接使用用户原始表达
**修改后**：添加 `use_llm` 参数，当 JTBD insight 为空时使用 LLM 智能重写

```python
async def _llm_enhance_goal(self, user_expression: str) -> str:
    """将用户简单表达转换为 JTBD 风格专业目标"""
    # 使用 LLM 提升目标表达质量
```

### 4. 更新 `_extract_insight_summary` 降级逻辑

**修改前**：返回空值（score=0, note="待分析"）
**修改后**：
- 使用 `score=-1` 表示"未生成"而非"0分"
- 添加 `_status: "pending"` 标记
- 返回有意义的提示文本

### 5. 前端优雅降级展示

更新 `QuestionnaireSummaryDisplay.tsx`：

```tsx
{/* 智能显示锐度评分状态 */}
{data.insight_summary.L5_sharpness_score < 0
  ? '⏳ 生成中...'
  : data.insight_summary.L5_sharpness_score === 0
    ? '⚠️ 待分析'
    : `锐度评分: ${score}/10`
}

{/* 空洞察状态提示 */}
{isEmpty && (
  <div className="bg-amber-50 ...">
    <AlertCircle />
    <p>⚠️ 洞察生成失败</p>
    <p>可能是分析层数据不足，系统已使用基础分析模式</p>
  </div>
)}
```

### 6. 路由修复

更新 `calibration_questionnaire.py` 追问模式路由：
- `goto="requirements_confirmation"` → `goto="project_director"`

## 修改文件清单

| 文件 | 修改内容 |
|------|---------|
| `requirements_restructuring.py` | 增强 LLM 独立分析、添加 fallback、Step 1 LLM 增强 |
| `QuestionnaireSummaryDisplay.tsx` | 空洞察优雅降级展示 |
| `types/index.ts` | 添加 `_status` 类型定义 |
| `calibration_questionnaire.py` | 修复追问模式路由 |

## 测试验证

重新测试 session，预期：
1. ✅ 锐度评分不再显示 "0/10"（改为 "⏳ 生成中..." 或实际分数）
2. ✅ 即使 `analysis_layers` 为空，仍能生成基础洞察
3. ✅ 前端正确显示生成状态和 fallback 提示
4. ✅ 追问模式正确路由到 `project_director`

## 版本信息

- **版本号**: v7.152
- **修复日期**: 2026-01-07
- **关联问题**: 问卷汇总"机械拼接"问题
- **依赖版本**: v7.151（需求洞察重构）
