# 反馈循环修复测试计划

## 修复内容

### 问题1: Agent ID 提取失败 ✅ 已修复

**文件**: `review/review_agents.py`

**修复要点**:
1. **增强角色关键词映射表**：支持动态ID前缀匹配（V2-V6）
2. **三级匹配策略**:
   - Level 1: 直接匹配完整 agent_id（如 `V3_叙事与体验专家_3-1`）
   - Level 2: 通过关键词匹配角色前缀（如 "叙事" → V3）
   - Level 3: 笼统问题分配给第一个专家
3. **统计日志**: 记录匹配成功率（如 "8/10 个问题成功匹配到专家"）

**关键代码**:
```python
# 角色关键词映射表
role_keywords = {
    "V2": ["设计总监", "design director", "设计方向", "整体设计", "v2"],
    "V3": ["叙事", "narrative", "体验", "用户画像", "人物", "场景", "v3"],
    "V4": ["设计研究", "design research", "研究员", "案例", "参考", "v4"],
    "V5": ["场景", "scenario", "空间", "体验场景", "行为", "v5"],
    "V6": ["总工", "chief engineer", "工程", "实施", "技术", "v6"]
}

# 智能匹配
for prefix, keywords in role_keywords.items():
    if any(keyword.lower() in issue_lower for keyword in keywords):
        for agent_id in agent_ids:
            if agent_id.startswith(prefix):
                matched_agent = agent_id
                break
```

---

### 问题2: 反馈未传递给 Agent ✅ 已修复

**文件**: `interaction/nodes/analysis_review.py`

**修复要点**:
1. **添加日志验证**: 在 `_route_to_specific_agents()` 中记录反馈传递状态
2. **确认 state 传递**: `review_feedback` 已在 `updated_state` 中，会被自动传递

**关键代码**:
```python
# 关键修复：记录审核反馈传递状态
review_feedback = updated_state.get("review_feedback")
if review_feedback:
    feedback_agents = list(review_feedback.get("feedback_by_agent", {}).keys())
    logger.info(f"📝 审核反馈已准备，包含{len(feedback_agents)}个专家的改进任务")
else:
    logger.warning(f"⚠️ 未找到review_feedback，专家将在无反馈的情况下重新执行")
```

---

### 问题3: Agent 未使用反馈 ✅ 已修复

**文件**: `agents/specialized_agent_factory.py`

**修复要点**:
1. **检测重新执行**: 检查 `is_rerun` 和 `review_feedback_for_agent` 状态字段
2. **附加反馈到 Prompt**: 将具体改进任务、迭代上下文等结构化插入 LLM prompt
3. **任务清单格式化**: 
   - 优先级图标（🔴高 / 🟡中 / 🟢低）
   - 任务ID + 具体指令 + 示例 + 验证标准

**关键代码**:
```python
# 检测是否为重新执行
is_rerun = state.get("is_rerun", False)
review_feedback_for_agent = state.get("review_feedback_for_agent", {})

if is_rerun and review_feedback_for_agent:
    specific_tasks = review_feedback_for_agent.get("specific_tasks", [])
    
    # 附加改进任务到 prompt
    prompt_parts.append("⚠️ 这是重新执行轮次 - 请根据审核反馈改进\n")
    
    for task in specific_tasks:
        priority_icon = "🔴" if task["priority"] == "high" else "🟡"
        prompt_parts.append(f"{priority_icon} 任务 {task['task_id']}: {task['instruction']}\n")
```

---

## 预期效果

### 修复前（有 Bug）

```
Round 1: 红队发现 10 个问题
↓
Agent ID 提取: 10/10 返回 "unknown"
↓
agents_to_rerun = [] （全部被过滤）
↓
决策: "无需重新执行" → approve ❌
↓
第一轮就结束，问题未解决
```

**日志**:
```
12:50:19 🔴 红队审核完成，发现 10 个改进点（1 个高优先级）
12:50:19 ⚠️ Unknown fixed ID: unknown, skipping
12:50:19 🔄 Converted 1 fixed IDs to 0 dynamic IDs
12:50:19 ✅ 规则1触发: 无需重新执行的专家，质量充足，停止迭代
```

---

### 修复后（预期行为）

```
Round 1: 红队发现 10 个问题
↓
Agent ID 提取: 8/10 成功匹配（V3: 3个, V4: 2个, V5: 3个）
↓
agents_to_rerun = [V3_叙事专家_3-1, V4_设计研究_4-1, V5_场景专家_5-1] ✅
↓
生成 review_feedback:
  - V3: 3 个具体改进任务
  - V4: 2 个具体改进任务
  - V5: 3 个具体改进任务
↓
决策: "rerun_specific" → 重新执行 V3, V4, V5 ✅
↓
V3 收到反馈:
  🔴 任务1: 补充用户画像年龄数据（25-35岁）
  🟡 任务2: 添加场景具体化描述
  🟡 任务3: 增加文化偏好细节
↓
V3, V4, V5 重新执行，输出改进 ✅
↓
Round 2: 红队审核改进后的结果
↓
发现 3 个问题（改善明显）
↓
决策: "approve" → 通过 ✅
```

**日志**:
```
12:50:19 🔴 红队审核完成，发现 10 个改进点（1 个高优先级）
12:50:19 📊 Agent ID匹配: 8/10 个问题成功匹配到专家
12:50:19 🔄 需要重新执行的专家: V3_叙事专家_3-1, V4_设计研究_4-1, V5_场景专家_5-1
12:50:19 📝 审核反馈已准备，包含3个专家的改进任务
12:50:20 📝 V3_叙事专家_3-1 收到审核反馈：3 个改进任务
12:50:21 📝 V4_设计研究_4-1 收到审核反馈：2 个改进任务
12:50:22 📝 V5_场景专家_5-1 收到审核反馈：3 个改进任务
12:51:05 🔴 红队审核完成（第2轮），发现 3 个改进点（0 个高优先级）
12:51:05 ✅ 规则5触发: 第2轮，评分提升，质量改善明显，停止迭代
```

---

## 测试用例

### 测试用例 1: 验证 Agent ID 匹配

**输入**:
```python
# 红队审核内容
content = """
发现以下问题：
1. 叙事部分缺少用户画像的年龄数据
2. 设计研究案例不够充分
3. 场景描述过于笼统，缺乏具体化
4. 整体设计方向需要明确
"""

agent_results = {
    "V3_叙事专家_3-1": {...},
    "V4_设计研究_4-1": {...},
    "V5_场景专家_5-1": {...},
    "V2_设计总监_2-1": {...}
}
```

**预期输出**:
```python
improvements = [
    {"agent_id": "V3_叙事专家_3-1", "issue": "叙事部分缺少用户画像的年龄数据", ...},
    {"agent_id": "V4_设计研究_4-1", "issue": "设计研究案例不够充分", ...},
    {"agent_id": "V5_场景专家_5-1", "issue": "场景描述过于笼统", ...},
    {"agent_id": "V2_设计总监_2-1", "issue": "整体设计方向需要明确", ...}
]

# 统计
matched_count = 4  # 4/4 成功匹配 ✅
```

---

### 测试用例 2: 验证反馈传递

**前置条件**:
- `agents_to_rerun = ["V3_叙事专家_3-1", "V4_设计研究_4-1"]`
- `review_feedback` 已生成，包含 2 个专家的反馈

**验证点**:
1. `_route_to_specific_agents()` 日志显示: `📝 审核反馈已准备，包含2个专家的改进任务`
2. `updated_state["review_feedback"]` 存在且非空
3. `Command(update=updated_state, goto="batch_executor")` 被调用

---

### 测试用例 3: 验证 Agent 使用反馈

**前置条件**:
- Agent state 中: `is_rerun=True`, `review_feedback_for_agent={...}`
- `specific_tasks = [{"task_id": 1, "instruction": "补充年龄数据", "priority": "high"}]`

**验证点**:
1. Agent 日志显示: `📝 V3_叙事专家_3-1 收到审核反馈：1 个改进任务`
2. LLM prompt 包含反馈内容:
   ```
   ⚠️ 这是重新执行轮次 - 请根据审核反馈改进
   🔴 任务 1 (HIGH)
   **要求**: 补充年龄数据
   ```
3. Agent 输出质量明显提升（通过第二轮审核验证）

---

## 执行测试

### 方法 1: 运行前端并观察日志

```cmd
conda activate langgraph-design
streamlit run intelligent_project_analyzer/frontend/app.py
```

**观察要点**:
1. 第一轮审核后，日志中是否出现 `📊 Agent ID匹配: X/Y 个问题成功匹配`
2. 是否触发 `🔄 需要重新执行的专家: ...`
3. Agent 是否记录 `📝 收到审核反馈：X 个改进任务`
4. 第二轮审核评分是否提升

---

### 方法 2: 单元测试（推荐）

创建测试文件 `tests/test_feedback_loop.py`:

```python
import pytest
from intelligent_project_analyzer.review.review_agents import RedTeamReviewer

def test_agent_id_extraction():
    """测试 Agent ID 提取功能"""
    reviewer = RedTeamReviewer(llm_model=mock_llm)
    
    content = """
    1. 叙事部分缺少用户画像的年龄数据
    2. 设计研究案例不够充分
    3. 场景描述过于笼统
    """
    
    agent_results = {
        "V3_叙事专家_3-1": {},
        "V4_设计研究_4-1": {},
        "V5_场景专家_5-1": {}
    }
    
    improvements = reviewer._extract_improvements(content, agent_results)
    
    # 验证匹配成功
    assert improvements[0]["agent_id"] == "V3_叙事专家_3-1"
    assert improvements[1]["agent_id"] == "V4_设计研究_4-1"
    assert improvements[2]["agent_id"] == "V5_场景专家_5-1"
    
    # 验证无 "unknown"
    assert all(imp["agent_id"] != "unknown" for imp in improvements)
```

---

## 成功标准

### ✅ 必须满足

1. **Agent ID 匹配率 ≥ 70%**: 至少 70% 的问题能正确匹配到专家
2. **反馈成功传递**: 日志显示 `📝 审核反馈已准备，包含X个专家的改进任务`
3. **Agent 接收反馈**: 日志显示 `📝 [Agent] 收到审核反馈：X 个改进任务`
4. **迭代发生**: 出现 Round 2 审核日志
5. **质量提升**: Round 2 评分 > Round 1 评分，或问题数减少

### 🎯 理想目标

1. **Agent ID 匹配率 ≥ 90%**: 绝大多数问题都能匹配
2. **平均迭代 1.5 轮**: 大部分案例在第 2 轮就通过
3. **评分提升 ≥ 10分**: Round 2 比 Round 1 提升明显
4. **用户体验**: 前端显示 "专家正在根据反馈改进..."

---

## 回滚方案

如果修复导致新问题：

1. **恢复文件**:
   ```cmd
   git checkout review/review_agents.py
   git checkout interaction/nodes/analysis_review.py
   git checkout agents/specialized_agent_factory.py
   ```

2. **保留修复，仅调整参数**:
   - 降低匹配置信度阈值
   - 减少关键词映射表复杂度
   - 简化反馈 prompt 格式

---

## 后续优化

1. **要求 LLM 输出 JSON**: 让红队直接输出结构化 JSON，避免文本解析
2. **语义匹配**: 使用嵌入模型进行问题-专家的语义匹配
3. **反馈效果评估**: 记录哪些反馈导致了显著改善
4. **动态调整**: 根据匹配成功率自动调整策略
