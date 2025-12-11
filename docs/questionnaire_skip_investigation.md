# 问卷交互被跳过问题调查报告

**会话ID**: api-20251129102622-d5509e65
**调查时间**: 2025-11-29
**问题描述**: 系统生成了7个战略校准问题（v3.5修复已生效），但用户从未看到问卷，直接进入专家执行。

---

## 一、问题表现

从会话历史分析可以看到：
- ✅ 问卷已生成（7个问题，通过v3.5智能补齐机制）
- ❌ 用户未看到问卷界面
- ❌ `calibration_processed` 标志直接为 `True`
- ✅ 系统直接进入专家执行阶段

---

## 二、代码调查发现

### 2.1 工作流路由结构

从 `main_workflow.py` 可以看到：
```python
# Line 149: 静态路由，domain_validator → calibration_questionnaire
workflow.add_edge("domain_validator", "calibration_questionnaire")

# Line 150: calibration_questionnaire 使用 Command 完全动态路由（无静态 edge）
```

**结论**: `calibration_questionnaire` 节点总是会被调用（静态edge保证）

### 2.2 问卷节点跳过逻辑

从 `calibration_questionnaire.py:442-452` 可以看到：
```python
# Line 442-443: 检查是否已处理
calibration_processed = state.get("calibration_processed")
logger.info(f"🔍 [DEBUG] calibration_processed 标志: {calibration_processed}")

# Line 446-448: 防御性编程 - 如果标志丢失但已存在答案，视为已处理
if not calibration_processed and state.get("calibration_answers"):
    logger.warning("⚠️ calibration_processed flag missing but calibration_answers found. Assuming processed.")
    calibration_processed = True

# Line 450-452: 如果已处理，直接跳过
if calibration_processed:
    logger.info("✅ Calibration already processed, skipping to requirements confirmation")
    return Command(goto="requirements_confirmation")
```

**关键发现**: 只有当 `calibration_processed=True` 时，问卷才会被跳过。

### 2.3 `calibration_processed` 标志的设置位置

搜索代码发现，`calibration_processed` 只在以下情况被设置为 `True`：

1. **用户提交问卷答案** (`calibration_questionnaire.py:721`):
   ```python
   updated_state["calibration_processed"] = True  # 答案提交后
   ```

2. **用户选择跳过** (`calibration_questionnaire.py:602`):
   ```python
   if skip_detected:
       logger.info("⏭️ User chose to skip questionnaire, proceeding without answers")
       updated_state["calibration_processed"] = True
       updated_state["calibration_skipped"] = True
   ```

3. **防御性逻辑** (`calibration_questionnaire.py:446-448`):
   ```python
   # 如果标志丢失但已存在答案，视为已处理
   if not calibration_processed and state.get("calibration_answers"):
       calibration_processed = True
   ```

**结论**: 正常情况下，`calibration_processed` 不会在节点首次执行时就为 `True`。

---

## 三、可能的原因分析

### 原因1: 会话恢复/重试导致标志残留 ⭐ **最可能**
如果这个会话是从之前的失败会话恢复的，或者发生了重试，`calibration_processed` 标志可能已经被设置。

**证据需求**:
- 检查会话开始时的状态初始化
- 查看是否有会话恢复逻辑

### 原因2: 前端直接调用了跳过接口
前端可能有一个"自动跳过"或"快速模式"的开关，导致直接发送了skip指令。

**证据需求**:
- 检查 `/api/analysis/resume` 接口的调用日志
- 查看前端是否有"跳过问卷"的UI元素

### 原因3: 状态污染
其他节点（如 `requirements_confirmation`）可能错误地设置了 `calibration_processed` 标志。

**证据需求**:
- 搜索所有 `calibration_processed` 的赋值位置
- 确认没有其他地方意外设置此标志

### 原因4: API测试模式
如果这是通过API直接调用的（非前端UI），可能在初始化时就设置了跳过标志。

**证据需求**:
- 检查会话ID格式：`api-20251129102622-d5509e65` （前缀是 `api-`，暗示API调用）
- 查看API启动参数

---

## 四、排查步骤

### 步骤1: 添加详细日志追踪
在 `calibration_questionnaire.py` 的节点入口处添加：
```python
def __call__(self, state: ProjectAnalysisState) -> Command:
    logger.info("=" * 80)
    logger.info("🎯 Starting calibration questionnaire interaction")
    logger.info("=" * 80)

    # ✅ 新增：追踪状态来源
    logger.info("🔍 [DEBUG] 节点调用时的完整状态:")
    logger.info(f"  - calibration_processed: {state.get('calibration_processed')}")
    logger.info(f"  - calibration_answers: {bool(state.get('calibration_answers'))}")
    logger.info(f"  - calibration_skipped: {state.get('calibration_skipped')}")
    logger.info(f"  - skip_unified_review: {state.get('skip_unified_review')}")
    logger.info(f"  - session_id: {state.get('session_id')}")
    logger.info(f"  - 所有状态键: {list(state.keys())}")
```

### 步骤2: 检查会话初始化
查看 `main_workflow.py` 中的会话启动逻辑：
```python
def start_analysis(self, session_id: str, user_input: str, **kwargs):
    # 检查初始状态是否包含 calibration_processed
```

### 步骤3: 检查API调用模式
如果会话ID以 `api-` 开头，可能是API测试模式：
```python
# 搜索: if session_id.startswith("api-")
```

### 步骤4: 检查前端resume调用
查看服务器日志中是否有：
```
POST /api/analysis/resume
{
  "session_id": "api-20251129102622-d5509e65",
  "resume_value": "skip"  # 或类似的跳过指令
}
```

---

## 五、临时解决方案

### 选项A: 强制显示问卷（修改代码）
```python
# calibration_questionnaire.py:442附近
calibration_processed = state.get("calibration_processed")

# 🔥 临时修复：忽略 calibration_processed 标志（调试用）
if os.getenv("FORCE_QUESTIONNAIRE", "false").lower() == "true":
    logger.warning("⚠️ FORCE_QUESTIONNAIRE enabled, ignoring calibration_processed flag")
    calibration_processed = False
```

然后设置环境变量：
```bash
export FORCE_QUESTIONNAIRE=true
```

### 选项B: 添加用户配置
在会话启动时允许用户指定是否跳过问卷：
```python
{
  "user_input": "...",
  "skip_questionnaire": false,  # 明确要求显示问卷
  "skip_unified_review": false  # 明确要求显示角色审核
}
```

### 选项C: 重置状态标志
在启动新会话时，确保清理历史标志：
```python
initial_state = {
    "session_id": session_id,
    "user_input": user_input,
    # 明确初始化所有跳过标志为 False
    "calibration_processed": False,
    "calibration_skipped": False,
    "skip_unified_review": False,
    "requirements_confirmed": False,
}
```

---

## 六、建议的修复方案

### 修复1: 添加状态初始化检查 (P1)
确保新会话启动时，所有标志都被明确初始化：

**文件**: `main_workflow.py`
**位置**: 会话启动函数

```python
def start_analysis(self, session_id: str, user_input: str, **kwargs):
    initial_state = ProjectAnalysisState(
        session_id=session_id,
        user_input=user_input,
        # 🔥 明确初始化交互标志（防止状态污染）
        calibration_processed=False,
        calibration_skipped=False,
        calibration_answers=None,
        skip_unified_review=False,
        requirements_confirmed=False,
        # ... 其他字段
    )

    logger.info(f"🔍 [DEBUG] 初始化新会话状态:")
    logger.info(f"  - calibration_processed: {initial_state.calibration_processed}")
    logger.info(f"  - skip_unified_review: {initial_state.skip_unified_review}")
```

### 修复2: 添加状态追踪日志 (P1)
在 `calibration_questionnaire.py` 节点入口处添加详细日志：

```python
def __call__(self, state: ProjectAnalysisState) -> Command:
    logger.info("=" * 80)
    logger.info("🎯 Starting calibration questionnaire interaction")
    logger.info("=" * 80)

    # 🔥 新增：状态来源追踪
    logger.info("🔍 [状态追踪] 当前标志状态:")
    logger.info(f"  calibration_processed: {state.get('calibration_processed')} (类型: {type(state.get('calibration_processed'))})")
    logger.info(f"  calibration_answers: {bool(state.get('calibration_answers'))}")
    logger.info(f"  skip_unified_review: {state.get('skip_unified_review')}")

    # 如果 calibration_processed 为 True，追踪来源
    if state.get('calibration_processed'):
        logger.warning("⚠️ calibration_processed 为 True，可能的原因:")
        logger.warning("  1. 会话恢复/重试导致标志残留")
        logger.warning("  2. 前端调用了跳过接口")
        logger.warning("  3. 其他节点错误设置了标志")
        logger.warning("  4. API测试模式")
```

### 修复3: 分离 `skip_unified_review` 和问卷跳过 (P2)
目前 `skip_unified_review` 用于跳过角色审核，不应该影响问卷交互。

确认代码中没有混淆这两个标志：
```python
# ❌ 错误示例（如果存在）:
if state.get("skip_unified_review"):
    # 不应该跳过问卷，只应该跳过角色审核
    calibration_processed = True

# ✅ 正确做法:
if state.get("skip_unified_review"):
    # 仅用于跳过 unified_review 节点
    skip_role_review = True
```

---

## 七、验证清单

修复后，需要验证：

- [ ] 新会话启动时，`calibration_processed` 初始值为 `False`
- [ ] 节点入口日志清晰显示标志来源
- [ ] 问卷生成后，用户能够看到问卷界面
- [ ] 用户可以选择回答或跳过
- [ ] 跳过后 `calibration_skipped=True`，正常提交后 `calibration_processed=True`
- [ ] `skip_unified_review` 不影响问卷交互

---

## 八、下一步行动

1. **立即**: 添加状态初始化检查和追踪日志（修复1和修复2）
2. **本周内**: 运行新的测试会话，检查日志输出
3. **如果问题复现**: 使用日志追踪标志来源，确定根本原因
4. **如果无法复现**: 可能是特定条件触发（如API模式），需要分情况处理

---

**调查者**: Claude (Droid)
**更新时间**: 2025-11-29
**状态**: 调查完成，待实施修复
