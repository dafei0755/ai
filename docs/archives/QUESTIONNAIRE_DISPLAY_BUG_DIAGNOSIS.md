# 问卷显示"未回答"问题诊断报告

**问题**: 用户在截图中看到所有问卷问题显示"未回答"（Q1-Q9），但实际用户已经填写了问卷
**诊断日期**: 2025-12-04
**版本**: v20251203

---

## 🔍 问题现象

### 前端显示
从用户截图看到：
- **校准问卷回顾** 区块显示
- 提交时间：2025/12/4 01:33:26
- 所有9个问题（Q1-Q9）的回答都显示为：**"未回答"**
- 但用户明确表示已经填写了问卷

### 数据结构

**前端期望的数据结构** (QuestionnaireSection.tsx):
```typescript
interface QuestionnaireResponseItem {
  question_id: string;
  question: string;
  answer: string;      // ← 这是前端显示的字段
  context: string;
}

interface QuestionnaireResponseData {
  responses: QuestionnaireResponseItem[];
  timestamp: string;
  analysis_insights: string;
}
```

---

## 🐛 根本原因

### 原因分析

**后端代码 `result_aggregator.py:1526-1530`**:
```python
@staticmethod
def _stringify_answer(value: Any) -> str:
    """将问卷答案格式化为易读字符串"""
    if value is None:
        return "未回答"  # ← 问题在这里！
```

**数据流**:

1. **用户填写问卷** → 数据保存到 `questionnaire_responses`

2. **保存格式** (calibration_questionnaire.py:740-747):
```python
summary_payload = {
    "entries": summary_entries,  # List[{id, question, value, type, context}]
    "answers": answers_map,      # Dict[question_id, answer_value]
    "submitted_at": timestamp,
    "timestamp": timestamp,
    "notes": notes,
    "source": "calibration_questionnaire"
}
```

3. **提取数据** (result_aggregator.py:1476-1489):
```python
if summary_entries:
    for idx, entry in enumerate(summary_entries, 1):
        answer_value = entry.get("value")  # 从entries中获取
        responses.append({
            "question_id": entry.get("id", f"Q{idx}"),
            "question": entry.get("question", ""),
            "answer": self._stringify_answer(answer_value),  # ← 调用stringify
            "context": entry.get("context", "")
        })
else:
    # 备用路径：从answers字典获取
    questions = calibration_questionnaire.get("questions", [])
    answers = questionnaire_responses.get("answers", {})
    for idx, q in enumerate(questions, 1):
        question_id = q.get("id", f"Q{idx}")
        raw_answer = (
            answers.get(question_id)
            or answers.get(f"q{idx}")
        )
        responses.append({
            "question_id": question_id,
            "question": q.get("question", ""),
            "answer": self._stringify_answer(raw_answer),  # ← 调用stringify
            "context": q.get("context", "")
        })
```

4. **_stringify_answer处理**:
```python
if value is None:
    return "未回答"
```

### 🎯 问题核心

**如果 `entry.get("value")` 返回 `None`，或者 `answers.get(question_id)` 返回 `None`，那么所有答案都会显示为"未回答"。**

---

## 🔍 可能的原因（3种情况）

### 情况1: entries中的value字段为None

**检查点**:
- `_build_answer_entries` 方法 (calibration_questionnaire.py:300-376)
- 第359-360行：
  ```python
  if answer_value is None:
      continue  # 跳过该问题，不添加到entries
  ```
- 第362-364行：
  ```python
  normalized_value = CalibrationQuestionnaireNode._normalize_answer_value(question, answer_value)
  if normalized_value is None:
      continue  # 跳过该问题
  ```

**结论**: 如果value为None，entry根本不会被添加到entries列表中。所以这不是原因。

### 情况2: entries列表为空，使用了备用路径

**检查点**:
- result_aggregator.py:1476行：`if summary_entries:`
- 如果entries为空，会走else分支，从answers字典获取

**可能性**:
- `questionnaire_responses.get("entries")` 返回空列表
- 但 `questionnaire_responses.get("answers")` 也为空或不匹配

### 情况3: 字段值被错误地设为空字符串

**检查点**:
- _stringify_answer只检查 `if value is None`
- 但如果value是空字符串`""`、空列表`[]`或空字典`{}`，会怎样？

```python
if isinstance(value, (list, tuple, set)):
    cleaned = [str(item).strip() for item in value if str(item).strip()]
    return "、".join(cleaned) if cleaned else "未回答"  # ← 空列表返回"未回答"
```

**结论**: 如果value是空列表，也会返回"未回答"。

---

## 🔬 诊断步骤

### 步骤1: 检查后端日志中的问卷数据

查找关键日志：
```bash
grep "Integrating.*questionnaire answers" logs/server.log
grep "summary_entries" logs/server.log
```

### 步骤2: 检查Redis中保存的数据

```bash
# 查询会话数据
redis-cli get "session:api-20251204012323-0f6deaa3"
```

查找以下字段：
- `questionnaire_responses`
- `questionnaire_summary`
- `calibration_answers`

### 步骤3: 在result_aggregator中添加调试日志

在 `_extract_questionnaire_data` 方法中添加：
```python
logger.info(f"[DEBUG] summary_entries count: {len(summary_entries)}")
logger.info(f"[DEBUG] first entry: {summary_entries[0] if summary_entries else 'EMPTY'}")

for idx, entry in enumerate(summary_entries, 1):
    answer_value = entry.get("value")
    logger.info(f"[DEBUG] Q{idx} value type: {type(answer_value)}, value: {answer_value}")
    stringified = self._stringify_answer(answer_value)
    logger.info(f"[DEBUG] Q{idx} stringified: {stringified}")
```

---

## 💡 快速验证方法

### 方法1: 检查API响应

打开浏览器DevTools（F12） → Network标签页 → 找到报告请求：
```
GET /api/analysis/results/{sessionId}
```

查看Response中的 `questionnaire_responses`:
```json
{
  "questionnaire_responses": {
    "responses": [
      {
        "question_id": "Q1",
        "question": "...",
        "answer": "未回答",  // ← 如果是这样，说明后端已经返回了"未回答"
        "context": "..."
      }
    ],
    "timestamp": "...",
    "analysis_insights": "..."
  }
}
```

### 方法2: 后端添加日志

修改 `result_aggregator.py:1480` 附近，添加：
```python
for idx, entry in enumerate(summary_entries, 1):
    answer_value = entry.get("value")
    # 🔥 添加调试日志
    logger.info(f"🔍 [QUESTIONNAIRE_DEBUG] Q{idx}:")
    logger.info(f"  entry keys: {list(entry.keys())}")
    logger.info(f"  value type: {type(answer_value)}")
    logger.info(f"  value content: {repr(answer_value)[:200]}")

    stringified = self._stringify_answer(answer_value)
    logger.info(f"  stringified: {stringified}")

    responses.append({
        "question_id": entry.get("id", f"Q{idx}"),
        "question": entry.get("question", ""),
        "answer": stringified,
        "context": entry.get("context", "")
    })
```

---

## 🎯 最可能的原因（推测）

基于代码逻辑分析，**最可能的原因是**：

### 原因A: entries中的value字段是空列表或空对象

用户填写的答案可能被保存为：
- 多选题：`[]` (空列表)
- 复杂对象：`{}` (空字典)
- 字符串但trim后为空：`""` (空字符串)

**_stringify_answer的处理**:
```python
if isinstance(value, (list, tuple, set)):
    cleaned = [str(item).strip() for item in value if str(item).strip()]
    return "、".join(cleaned) if cleaned else "未回答"  # ← 返回"未回答"
```

### 原因B: _normalize_answer_value返回了None

在 `_build_answer_entries` 中：
```python
normalized_value = CalibrationQuestionnaireNode._normalize_answer_value(question, answer_value)
if normalized_value is None:
    continue  # 不添加到entries
```

如果normalize方法有bug，可能会错误地返回None。

---

## 🔧 临时修复方案

### 方案1: 修改_stringify_answer（最简单）

```python
@staticmethod
def _stringify_answer(value: Any) -> str:
    """将问卷答案格式化为易读字符串"""
    if value is None:
        return "未回答"

    # 🔥 添加更多调试信息
    if isinstance(value, (list, tuple, set)):
        if not value:  # 空列表
            logger.warning(f"[QUESTIONNAIRE] Empty list detected: {value}")
        cleaned = [str(item).strip() for item in value if str(item).strip()]
        return "、".join(cleaned) if cleaned else "未回答"

    if isinstance(value, dict):
        if not value:  # 空字典
            logger.warning(f"[QUESTIONNAIRE] Empty dict detected: {value}")
        # ... rest of code
```

### 方案2: 检查_normalize_answer_value

查看该方法是否正确处理所有答案类型。

---

## 📞 需要用户提供的信息

为了准确诊断，请提供：

1. **前端Network日志**
   - F12 → Network → 找到 `/api/analysis/results/{sessionId}` 请求
   - 查看Response中的 `questionnaire_responses.responses` 内容
   - 截图或复制JSON

2. **后端完整日志**
   - 搜索 "Integrating.*questionnaire answers"
   - 搜索 "summary_entries"
   - 提供这些日志行及前后10行

3. **用户填写的答案**
   - 问卷类型（单选/多选/填空）
   - 每个问题的答案内容

4. **或者**，如果可以：
   - 重新进行一次分析（填写问卷）
   - 在后端添加上述调试日志
   - 提供新的完整日志

---

## 📊 下一步

**如果是空列表/空字典问题**:
需要检查用户填写问卷时，前端是如何提交答案的。可能前端提交的数据格式不正确。

**如果是normalize问题**:
需要查看 `_normalize_answer_value` 方法的逻辑。

**如果是数据未保存**:
需要检查 `calibration_questionnaire.py` 中数据保存的逻辑。

---

**文档创建时间**: 2025-12-04
**状态**: ⏳ 等待用户提供更多信息（Network日志或后端日志）
**优先级**: 🔴 高（影响用户体验）
