# Domain Validator 数据提取修复

## 问题根因

**现象**: requirements_confirmation 提交后,工作流陷入无限循环:
```
requirements_confirmation → requirements_analyst → domain_validator → calibration_questionnaire → requirements_confirmation
```

**根本原因**: `domain_validator_node.py` 无法从 state 中提取需求分析数据,导致:
1. 数据源错误: 查找不存在的 `requirements_result` 字段
2. 字段不匹配: `_extract_project_summary` 查找旧版字段,与 V3.5 实际字段不符

**错误日志**:
```
ERROR | domain_validator_node:execute:59 - ❌ 需求分析结果为空,无法继续
```

## 修复内容

### 修复 1: 数据源路径 (Lines 44-62)

**问题**: 
```python
requirements_result = state.get("requirements_result", {})  # ❌ 字段不存在
```

**修复**:
```python
# 从 agent_results 中提取 requirements_analyst 的结果
agent_results = state.get("agent_results", {})
requirements_analyst_result = agent_results.get("requirements_analyst", {})

# 获取 structured_data 字段
requirements_result = requirements_analyst_result.get("structured_data", {})

# 兼容旧版本: 如果 agent_results 中没有,尝试直接从 structured_requirements 获取
if not requirements_result:
    requirements_result = state.get("structured_requirements", {})

logger.info(f"🔍 [DEBUG] requirements_result keys: {list(requirements_result.keys()) if requirements_result else 'None'}")
```

**依据**: 
- `requirements_analyst` 通过 `agent.execute()` 返回 `AnalysisResult` 对象
- `main_workflow._requirements_analyst_node` 将其存储为:
  ```python
  "agent_results": {
      AgentType.REQUIREMENTS_ANALYST.value: result.to_dict()
  }
  ```
- `result.to_dict()` 包含 `structured_data` 字段

### 修复 2: 字段名称匹配 (Lines 205-277)

**问题**: `_extract_project_summary` 查找旧版字段
```python
if "project_info" in requirements_result:  # ❌ V3.5 不存在
if "core_requirements" in requirements_result:  # ❌ V3.5 不存在
if "objectives" in requirements_result:  # ❌ V3.5 不存在
```

**实际 V3.5 字段** (来自日志):
```
['project_task', 'character_narrative', 'physical_context', 
 'resource_constraints', 'regulatory_requirements', 'inspiration_references', 
 'experience_behavior', 'design_challenge', 'calibration_questionnaire', 
 'expert_handoff', 'space_constraints', 'core_tension', 
 'project_overview', 'core_objectives', 'target_users', 'constraints']
```

**修复**: 优先查找 V3.5 字段,兼容旧版
```python
# V3.5 新格式字段
if "project_task" in requirements_result:
    summary_parts.append(f"项目任务: {requirements_result['project_task']}")
if "project_overview" in requirements_result:
    summary_parts.append(f"项目概述: {requirements_result['project_overview']}")
if "core_objectives" in requirements_result:
    summary_parts.append(f"核心目标: {requirements_result['core_objectives']}")
if "design_challenge" in requirements_result:
    summary_parts.append(f"设计挑战: {requirements_result['design_challenge']}")
if "physical_context" in requirements_result:
    summary_parts.append(f"物理环境: {requirements_result['physical_context']}")

# 兼容旧格式 (v3.4及之前)
if not summary_parts:
    # ... 旧字段逻辑 ...
```

## 预期效果

修复后,workflow 应正常进行:
```
requirements_confirmation (用户确认) 
  → requirements_analyst (重新分析)
  → domain_validator (✅ 成功提取数据并验证)
  → calibration_questionnaire (检测 calibration_processed=True,跳过)
  → requirements_confirmation (再次确认)
    → 如用户完全批准,路由到 project_director (继续后续流程)
```

## 测试步骤

1. 保存修改后的 `domain_validator_node.py`
2. 重启 API 服务: `python intelligent_project_analyzer/api/server.py`
3. 提交问卷 → 确认需求 → 修改某些字段并批准
4. 观察日志:
   - ✅ 应看到 `🔍 [DEBUG] requirements_result keys: [...]`
   - ✅ 应看到 `📄 项目摘要: 项目任务: ... | 项目概述: ...`
   - ❌ 不应再出现 `❌ 需求分析结果为空`
5. 确认工作流正常进入 `project_director`

## 相关文件

- `intelligent_project_analyzer/security/domain_validator_node.py` (本次修复)
- `intelligent_project_analyzer/agents/requirements_analyst.py` (数据生产者)
- `intelligent_project_analyzer/workflow/main_workflow.py` (数据桥接者)
- `intelligent_project_analyzer/agents/base.py` (AnalysisResult 定义)

## 修复时间

2025-11-25 17:43
