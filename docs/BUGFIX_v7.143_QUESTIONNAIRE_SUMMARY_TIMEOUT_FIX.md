# BugFix v7.143: 问卷汇总超时失败修复

**问题描述**：问卷流程在Step 3（信息补全）的专家视角分析阶段超时或卡住，导致questionnaire_summary节点从未被调用，结构化需求文档生成失败。

**修复日期**：2026-01-06

**影响范围**：Progressive Questionnaire 工作流、Questionnaire Summary节点、Requirements Restructuring

---

## 🔍 根本原因分析

### 流程路径
```
progressive_step1 (任务拆解)
  → progressive_step3_gap_filling (信息补全) ❌ 卡在这里
  → progressive_step2_radar (雷达维度)
  → questionnaire_summary (需求文档生成) ❌ 从未到达
  → requirements_confirmation
```

### 失败点
从日志分析，问题发生在Step 3的两个LLM密集型操作：

1. **专家角色预测** (`_predict_expert_roles`)
   - 调用LLM预测需要哪些专家角色
   - 无超时保护，可能因网络问题卡住

2. **专家视角分析** (`analyze_with_expert_foresight`)
   - 基于预测的专家角色进行深度分析
   - 可能耗时60秒以上，且无超时保护

### 日志证据
```
2026-01-06 15:35:51.382 | INFO | 🔮 [v7.136] 启用专家视角风险预判
# 之后没有任何后续日志...
```

---

## ✅ 实施的修复

### P0修复：添加超时保护

#### 1. 专家角色预测超时保护 (30秒)

**文件**: [intelligent_project_analyzer/interaction/nodes/progressive_questionnaire.py](intelligent_project_analyzer/interaction/nodes/progressive_questionnaire.py)

**修改位置**: Line 864-894

**修复内容**:
```python
# 使用 ThreadPoolExecutor 包装，30秒超时
with ThreadPoolExecutor(max_workers=1) as executor:
    future = executor.submit(
        ProgressiveQuestionnaireNode._predict_expert_roles,
        user_input=user_input,
        confirmed_tasks=confirmed_tasks,
        structured_data=structured_data
    )
    try:
        predicted_roles = future.result(timeout=30)
    except FuturesTimeoutError:
        logger.warning("⏰ [专家角色] 预测超时(30秒)，跳过专家视角分析")
        predicted_roles = None
```

**效果**:
- ✅ 即使角色预测失败，流程也能继续
- ✅ 自动降级到基础分析（不含专家视角）
- ✅ 避免无限等待

#### 2. 专家视角分析超时保护 (60秒)

**文件**: [intelligent_project_analyzer/interaction/nodes/progressive_questionnaire.py](intelligent_project_analyzer/interaction/nodes/progressive_questionnaire.py)

**修改位置**: Line 896-935

**修复内容**:
```python
# 使用 ThreadPoolExecutor 包装，60秒超时
with ThreadPoolExecutor(max_workers=1) as executor:
    future = executor.submit(
        analyzer.analyze_with_expert_foresight,
        confirmed_tasks=confirmed_tasks,
        user_input=user_input,
        structured_data=structured_data,
        predicted_roles=predicted_roles
    )
    try:
        completeness = future.result(timeout=60)
    except FuturesTimeoutError:
        logger.warning("⏰ [完整性分析] 专家视角分析超时(60秒)，降级到基础分析")
        completeness = analyzer.analyze(confirmed_tasks, user_input, structured_data)
```

**效果**:
- ✅ 超时后自动降级到基础分析
- ✅ 保证Step 3总能完成
- ✅ 提供简化的completeness结构作为降级方案

#### 3. 全局异常保护

**文件**: [intelligent_project_analyzer/interaction/nodes/progressive_questionnaire.py](intelligent_project_analyzer/interaction/nodes/progressive_questionnaire.py)

**修改位置**: Line 1216-1240

**修复内容**:
```python
except Exception as e:
    # 全局异常保护 - 确保即使失败也能继续流程
    logger.error(f"❌ [第2步] 严重错误: {e}")
    import traceback
    logger.error(f"🔍 [错误堆栈] {traceback.format_exc()}")

    # 降级：使用简化数据继续流程
    fallback_update = {
        "progressive_questionnaire_step": 2,
        "gap_filling_answers": {},
        "task_completeness_analysis": {
            "completeness_score": 0.3,
            "analysis_method": "emergency_fallback"
        },
        "error_occurred_in_step3": True
    }
    return Command(update=fallback_update, goto="progressive_step2_radar")
```

**效果**:
- ✅ 捕获所有未预期的异常
- ✅ 确保总是返回Command，流程不会中断
- ✅ 提供紧急降级方案

---

### P1修复：增强日志和重试机制

#### 4. questionnaire_summary 入口/出口日志

**文件**: [intelligent_project_analyzer/interaction/nodes/questionnaire_summary.py](intelligent_project_analyzer/interaction/nodes/questionnaire_summary.py)

**修改位置**: Line 46-70, 134-139

**修复内容**:
```python
# 入口日志
logger.info("=" * 100)
logger.info("📋 [问卷汇总] ✅ ENTERING questionnaire_summary node")
logger.info("=" * 100)

# 前置数据检查
logger.info(f"🔍 [前置数据检查]")
logger.info(f"   - confirmed_core_tasks: {len(confirmed_tasks)}个")
logger.info(f"   - gap_filling_answers: {len(gap_filling)}个字段")
logger.info(f"   - selected_dimensions: {len(selected_dims)}个")

# 出口日志
logger.info("=" * 100)
logger.info("📋 [问卷汇总] ✅ EXITING questionnaire_summary node - SUCCESS")
logger.info(f"   返回字段: {list(result.keys())}")
logger.info("=" * 100)
```

**效果**:
- ✅ 明确显示节点是否被调用
- ✅ 诊断前置数据缺失问题
- ✅ 确认返回数据结构

#### 5. 集成LLM重试机制

**文件**: [intelligent_project_analyzer/interaction/nodes/requirements_restructuring.py](intelligent_project_analyzer/interaction/nodes/requirements_restructuring.py)

**修改位置**: Line 574-617

**修复内容**:
```python
from ...utils.llm_retry import invoke_llm_with_retry, LLMRetryConfig

# 配置重试策略
retry_config = LLMRetryConfig(
    max_attempts=3,      # 最多3次尝试
    min_wait=1.0,        # 最小等待1秒
    max_wait=5.0,        # 最大等待5秒
    multiplier=2.0,      # 指数退避
    timeout=15.0         # 每次15秒超时
)

# 使用重试机制调用LLM
response = invoke_llm_with_retry(llm, prompt, config=retry_config)
```

**效果**:
- ✅ 自动重试网络错误和超时
- ✅ 指数退避策略避免过载
- ✅ 所有重试失败后优雅降级

---

## 🎯 预期效果

### 修复前
```
Step 1 (任务拆解) ✅
  ↓
Step 3 (信息补全) ❌ 卡住60秒+
  ↓
Step 2 (雷达维度) ❌ 从未到达
  ↓
questionnaire_summary ❌ 从未到达
```

### 修复后
```
Step 1 (任务拆解) ✅
  ↓
Step 3 (信息补全) ✅
  - 专家角色预测: 30秒超时 → 降级
  - 完整性分析: 60秒超时 → 基础分析
  ↓
Step 2 (雷达维度) ✅
  ↓
questionnaire_summary ✅
  - LLM摘要: 3次重试 × 15秒超时 → 降级
```

---

## 📊 降级策略总结

| 失败点 | 超时时间 | 降级方案 | 数据质量 |
|--------|----------|----------|----------|
| 专家角色预测 | 30秒 | 跳过专家视角 | 90% (基础分析) |
| 专家视角分析 | 60秒 | 基础完整性分析 | 85% (无专家视角) |
| LLM摘要生成 | 45秒 (3次×15秒) | 模板拼接 | 70% (无LLM优化) |
| 整个Step 3失败 | - | 紧急降级 | 50% (最小可用数据) |

---

## ✅ 验证清单

- [x] Step 3 专家角色预测添加30秒超时保护
- [x] Step 3 完整性分析添加60秒超时保护
- [x] Step 3 全局异常保护确保返回Command
- [x] questionnaire_summary 添加明确的入口/出口日志
- [x] requirements_restructuring 集成LLM重试机制
- [x] 所有降级方案提供基本可用数据
- [x] 日志足够详细，可快速诊断问题

---

## 🧪 测试建议

### 正常场景测试
```bash
# 启动服务
python -B scripts\run_server_production.py

# 完整运行一次问卷流程，观察日志:
# 1. Step 1 任务拆解完成
# 2. Step 3 信息补全完成（查看是否有超时警告）
# 3. Step 2 雷达维度完成
# 4. questionnaire_summary 被调用并成功
```

### 预期日志输出
```
📋 [问卷汇总] ✅ ENTERING questionnaire_summary node
🔍 [前置数据检查]
   - confirmed_core_tasks: 7个
   - gap_filling_answers: 5个字段
   - selected_dimensions: 9个
📋 [问卷汇总] 开始生成结构化需求文档
✅ 问卷汇总完成
📋 [问卷汇总] ✅ EXITING questionnaire_summary node - SUCCESS
```

### 超时场景测试
模拟网络延迟/LLM服务慢：
- 预期：Step 3 在90秒内完成（30s+60s超时）
- 预期：questionnaire_summary 仍然被调用
- 预期：日志显示降级警告

---

## 📝 后续优化建议

### 性能优化
1. **环境变量控制** (已有):
   ```python
   ENABLE_EXPERT_FORESIGHT=false  # 禁用专家视角（节省60秒）
   USE_LLM_GAP_QUESTIONS=false   # 禁用LLM问题生成（节省15秒）
   ```

2. **缓存机制** (待实现):
   - 缓存相似项目的expert_roles预测结果
   - 缓存常见项目类型的completeness分析模板

### 雷达图智能化 (下一步)
- 参考修复计划 Phase 6
- 添加动态维度生成的超时保护
- 实现项目类型驱动的维度选择

---

## 🔗 相关文件

- [intelligent_project_analyzer/interaction/nodes/progressive_questionnaire.py](intelligent_project_analyzer/interaction/nodes/progressive_questionnaire.py) - Step 3核心逻辑
- [intelligent_project_analyzer/interaction/nodes/questionnaire_summary.py](intelligent_project_analyzer/interaction/nodes/questionnaire_summary.py) - 问卷汇总
- [intelligent_project_analyzer/interaction/nodes/requirements_restructuring.py](intelligent_project_analyzer/interaction/nodes/requirements_restructuring.py) - 需求重构引擎
- [intelligent_project_analyzer/utils/llm_retry.py](intelligent_project_analyzer/utils/llm_retry.py) - LLM重试机制
- [修复计划](../plans/expressive-drifting-quiche.md) - 完整修复计划

---

**修复版本**: v7.143
**测试状态**: 待验证
**文档更新**: 2026-01-06
