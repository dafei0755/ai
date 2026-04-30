# 问卷第一步回退策略参数缺失修复 (v7.119)

## 📋 问题描述

**用户反馈**：
> "问卷第一步，任务是否还是7个的硬编码？？怎么改不过来"

**排查结果**：
- ✅ LLM 任务拆解实际工作正常（日志显示动态生成了 5、7、8 个不等的任务）
- ❌ 回退策略 `_simple_fallback_decompose` 调用缺少 `structured_data` 参数

## 🔍 根因分析

### 问题定位

在 `progressive_questionnaire.py` 中，当 LLM 返回空列表或调用失败时，回退策略的调用缺少 `structured_data` 参数：

```python
# 第119行 - LLM 返回空列表时
extracted_tasks = _simple_fallback_decompose(user_input)  # ❌ 缺少 structured_data

# 第124行 - LLM 调用异常时
extracted_tasks = _simple_fallback_decompose(user_input)  # ❌ 缺少 structured_data
```

### 函数签名（core_task_decomposer.py:557）

```python
def _simple_fallback_decompose(
    user_input: str,
    structured_data: Optional[Dict[str, Any]] = None,  # ← 需要传递
    complexity_analysis: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
```

## ✅ 修复方案

### 修改文件
`intelligent_project_analyzer/interaction/nodes/progressive_questionnaire.py`

### 修改内容

**第119行**：
```python
# 修改前
extracted_tasks = _simple_fallback_decompose(user_input)

# 修改后
extracted_tasks = _simple_fallback_decompose(user_input, structured_data)
```

**第124行**：
```python
# 修改前
extracted_tasks = _simple_fallback_decompose(user_input)

# 修改后
extracted_tasks = _simple_fallback_decompose(user_input, structured_data)
```

## 🧪 验证测试

```python
from intelligent_project_analyzer.services.core_task_decomposer import _simple_fallback_decompose

# 测试 structured_data 参数传递
structured_data = {
    'design_challenge': '为年轻家庭设计智能家居控制系统',
    'character_narrative': '35岁的科技爱好者，有两个孩子',
    'project_type_label': '住宅设计'
}
result = _simple_fallback_decompose('设计一个智能家居系统', structured_data)
print(f'生成 {len(result)} 个任务')  # 输出: 生成 3 个任务
```

## 📊 预期效果

| 场景 | 修复前 | 修复后 |
|------|--------|--------|
| 回退策略利用 structured_data | ❌ 无法利用 | ✅ 可用 |
| 任务数量 | 可能硬编码 | 动态 3-12 个 |
| 任务质量 | 基础模板 | 基于用户输入智能生成 |

## 📅 修复信息

- **修复日期**: 2026-01-02
- **修复版本**: v7.119
- **影响范围**: 问卷第一步回退场景（LLM 失败或返回空时）
