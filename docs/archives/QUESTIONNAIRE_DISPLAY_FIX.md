# 问卷前端显示错误修复

**修复日期**: 2025-12-10
**问题**: 前端显示"未回答"的问卷问题
**优先级**: P0 (紧急)

---

## 问题描述

### 现象
前端报告页面显示问卷回顾区块，但所有问题都显示"未回答"：

```
Q1: 这是本项目最核心的设计核心诉求，将决定设计的根本方向...
您的回答: 未回答

Q2: 帮助我们进一步资源有限时做出明智的优先级决策...
您的回答: 未回答

Q3: V1.5检测到工期紧张与质量要求的优先级...
您的回答: 未回答
```

### 用户期望
1. **如果跳过问卷**: 前端不显示问卷回顾区块
2. **如果有回答**: 前端显示实际答案
3. **不可能出现**: 前端显示"未回答"的情况

---

## 根因分析

### 问题根源
**文件**: `intelligent_project_analyzer/report/result_aggregator.py`

在 `_extract_questionnaire_data` 方法（第1725-1793行）中：

```python
# 问题代码
for idx, q in enumerate(questions, 1):
    question_id = q.get("id", f"Q{idx}")
    raw_answer = (
        answers.get(question_id)
        or answers.get(f"q{idx}")
    )
    responses.append({
        "question_id": question_id,
        "question": q.get("question", ""),
        "answer": self._stringify_answer(raw_answer),  # ❌ 即使 raw_answer 为 None 也会添加
        "context": q.get("context", "")
    })
```

**问题**:
1. 即使 `raw_answer` 为 `None`，也会调用 `_stringify_answer(None)`
2. `_stringify_answer(None)` 返回 `"未回答"`（第1798-1799行）
3. 所有未回答的问题都被添加到 `responses` 列表中
4. 前端收到包含"未回答"的问卷数据，无法区分是否应该显示

---

## 修复方案

### 修复内容

**文件**: [result_aggregator.py:1725-1821](intelligent_project_analyzer/report/result_aggregator.py#L1725-L1821)

#### 1. 修改返回类型（第1730行）
```python
# 修复前
def _extract_questionnaire_data(...) -> Dict[str, Any]:

# 修复后
def _extract_questionnaire_data(...) -> Optional[Dict[str, Any]]:
```

#### 2. 添加答案过滤逻辑（第1756-1763行，第1781-1788行）

**summary_entries 分支**:
```python
if summary_entries:
    for idx, entry in enumerate(summary_entries, 1):
        answer_value = entry.get("value")
        # 🔧 修复: 跳过未回答的问题
        if answer_value is None or answer_value == "" or answer_value == []:
            continue

        answer_str = self._stringify_answer(answer_value)
        # 🔧 修复: 再次检查格式化后的答案
        if answer_str == "未回答" or answer_str == "":
            continue

        responses.append({
            "question_id": entry.get("id", f"Q{idx}"),
            "question": entry.get("question", ""),
            "answer": answer_str,
            "context": entry.get("context", "")
        })
```

**questions/answers 分支**:
```python
else:
    questions = calibration_questionnaire.get("questions", [])
    answers = questionnaire_responses.get("answers", {})
    for idx, q in enumerate(questions, 1):
        question_id = q.get("id", f"Q{idx}")
        raw_answer = (
            answers.get(question_id)
            or answers.get(f"q{idx}")
        )

        # 🔧 修复: 跳过未回答的问题
        if raw_answer is None or raw_answer == "" or raw_answer == []:
            continue

        answer_str = self._stringify_answer(raw_answer)
        # 🔧 修复: 再次检查格式化后的答案
        if answer_str == "未回答" or answer_str == "":
            continue

        responses.append({
            "question_id": question_id,
            "question": q.get("question", ""),
            "answer": answer_str,
            "context": q.get("context", "")
        })
```

#### 3. 添加空响应检查（第1797-1800行）
```python
# 🔧 修复: 如果所有问题都未回答，返回 None（前端会隐藏整个问卷区块）
if not responses:
    logger.info("📋 所有问卷问题都未回答，返回 None（前端将隐藏问卷区块）")
    return None
```

#### 4. 添加日志记录（第1814行）
```python
logger.info(f"✅ 提取到 {len(responses)} 个有效问卷回答")
```

---

## 修复逻辑

### 过滤规则

**第一层过滤**（原始值检查）:
```python
if answer_value is None or answer_value == "" or answer_value == []:
    continue
```

**第二层过滤**（格式化后检查）:
```python
answer_str = self._stringify_answer(answer_value)
if answer_str == "未回答" or answer_str == "":
    continue
```

**第三层过滤**（空响应检查）:
```python
if not responses:
    return None
```

### 前端处理

**文件**: `frontend-nextjs/components/report/QuestionnaireSection.tsx`

前端已有正确的空值处理（第27-29行）:
```tsx
if (!questionnaireData || !questionnaireData.responses || questionnaireData.responses.length === 0) {
  return null; // 用户跳过问卷
}
```

**效果**:
- 如果后端返回 `null`，前端不渲染问卷区块
- 如果后端返回空数组 `[]`，前端不渲染问卷区块
- 只有当后端返回有效答案时，前端才显示问卷区块

---

## 测试验证

### 测试场景

#### 场景1: 用户跳过问卷
**输入**: 用户在问卷阶段点击"跳过"
**预期**:
- 后端: `_extract_questionnaire_data` 返回 `None`
- 前端: 不显示问卷回顾区块

#### 场景2: 用户回答部分问题
**输入**: 用户回答了Q1、Q3，跳过了Q2、Q4
**预期**:
- 后端: 只返回Q1、Q3的答案
- 前端: 只显示Q1、Q3的卡片

#### 场景3: 用户回答所有问题
**输入**: 用户回答了所有8个问题
**预期**:
- 后端: 返回所有8个答案
- 前端: 显示8个问卷卡片

### 测试命令

```bash
# 1. 清除旧会话
redis-cli FLUSHDB

# 2. 重启后端
python -m uvicorn intelligent_project_analyzer.api.server:app --reload

# 3. 提交测试用例
# 使用"上海静安区一家30平米的精品咖啡店"测试用例

# 4. 检查日志
grep "提取到.*个有效问卷回答" logs/api.log
grep "所有问卷问题都未回答" logs/api.log
```

### 预期日志

**场景1（跳过问卷）**:
```
📋 所有问卷问题都未回答，返回 None（前端将隐藏问卷区块）
```

**场景2（部分回答）**:
```
✅ 提取到 2 个有效问卷回答
```

**场景3（全部回答）**:
```
✅ 提取到 8 个有效问卷回答
```

---

## 相关代码路径

### 后端
1. **问卷数据提取**: [result_aggregator.py:1725-1821](intelligent_project_analyzer/report/result_aggregator.py#L1725-L1821)
2. **答案格式化**: [result_aggregator.py:1823-1841](intelligent_project_analyzer/report/result_aggregator.py#L1823-L1841)
3. **任务描述构建**: [result_aggregator.py:533-538](intelligent_project_analyzer/report/result_aggregator.py#L533-L538)

### 前端
1. **问卷区块组件**: [QuestionnaireSection.tsx:26-80](frontend-nextjs/components/report/QuestionnaireSection.tsx#L26-L80)
2. **报告页面渲染**: [page.tsx:782](frontend-nextjs/app/report/[sessionId]/page.tsx#L782)

---

## 边界情况处理

### 1. 空字符串答案
```python
if answer_value == "":
    continue  # ✅ 跳过
```

### 2. 空列表答案（多选题未选）
```python
if answer_value == []:
    continue  # ✅ 跳过
```

### 3. 空字典答案
```python
# _stringify_answer 会返回 "{}"
if answer_str == "":
    continue  # ✅ 跳过
```

### 4. 仅包含空格的答案
```python
text = str(value).strip()
return text or "未回答"  # ✅ 返回"未回答"，会被第二层过滤
```

---

## 修复前后对比

### 修复前
```json
{
  "questionnaire_responses": {
    "responses": [
      {"question_id": "Q1", "question": "...", "answer": "未回答", "context": "..."},
      {"question_id": "Q2", "question": "...", "answer": "未回答", "context": "..."},
      {"question_id": "Q3", "question": "...", "answer": "未回答", "context": "..."}
    ],
    "timestamp": "2025-12-10T15:48:57",
    "analysis_insights": "..."
  }
}
```

**前端显示**: 3个卡片，全部显示"未回答" ❌

### 修复后

**场景1（跳过问卷）**:
```json
{
  "questionnaire_responses": null
}
```
**前端显示**: 不显示问卷区块 ✅

**场景2（部分回答）**:
```json
{
  "questionnaire_responses": {
    "responses": [
      {"question_id": "Q1", "question": "...", "answer": "寻求平衡点...", "context": "..."},
      {"question_id": "Q3", "question": "...", "answer": "优化施工方案...", "context": "..."}
    ],
    "timestamp": "2025-12-10T15:48:57",
    "analysis_insights": "..."
  }
}
```
**前端显示**: 2个卡片，显示实际答案 ✅

---

## 长期优化建议

### 1. 在问卷生成阶段标记必填项
```python
# calibration_questionnaire_node.py
{
  "id": "Q1",
  "question": "...",
  "required": True,  # 🆕 标记必填
  "type": "single_choice"
}
```

### 2. 前端实时验证
```tsx
// QuestionnaireModal.tsx
const validateAnswers = () => {
  const unanswered = questions.filter(q =>
    q.required && !answers[q.id]
  );
  if (unanswered.length > 0) {
    alert(`请回答必填问题: ${unanswered.map(q => q.id).join(', ')}`);
    return false;
  }
  return true;
};
```

### 3. 后端验证
```python
# calibration_questionnaire.py
def validate_answers(questions, answers):
    required_questions = [q for q in questions if q.get("required")]
    unanswered = [q["id"] for q in required_questions if q["id"] not in answers]
    if unanswered:
        raise ValueError(f"必填问题未回答: {unanswered}")
```

---

## 修复总结

| 修改项 | 文件 | 行数 | 状态 |
|--------|------|------|------|
| 修改返回类型为 Optional | result_aggregator.py | 1730 | ✅ 已完成 |
| 添加第一层过滤（原始值） | result_aggregator.py | 1757-1758, 1782-1783 | ✅ 已完成 |
| 添加第二层过滤（格式化后） | result_aggregator.py | 1761-1763, 1786-1788 | ✅ 已完成 |
| 添加第三层过滤（空响应） | result_aggregator.py | 1797-1800 | ✅ 已完成 |
| 添加日志记录 | result_aggregator.py | 1814 | ✅ 已完成 |

**总计**: 5处修改，全部完成

---

**修复负责人**: Claude Code
**测试状态**: 待验证
**预计生效**: 立即生效
