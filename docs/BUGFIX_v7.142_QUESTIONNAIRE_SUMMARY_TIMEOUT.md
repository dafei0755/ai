# Bug修复报告 v7.142 - 问卷汇总LLM调用超时

## 问题描述

**症状**: 用户在确认雷达图维度后，系统卡住不再响应，前端持续显示loading状态。

**复现路径**:
1. 用户完成第1步（任务梳理）→ 确认
2. 用户完成第2步（信息补全）→ 确认
3. 用户完成第3步（雷达维度）→ 确认
4. **系统卡住** - 进入问卷汇总节点后无响应

## 根因分析

### 调用链路追踪

从日志分析，系统卡在以下调用链：

```
用户确认雷达维度
  ↓
step2_radar 完成 (progressive_questionnaire.py:752)
  ↓
questionnaire_summary_node (questionnaire_summary.py:47)
  ↓
RequirementsRestructuringEngine.restructure (requirements_restructuring.py:67)
  ↓
_generate_executive_summary (requirements_restructuring.py:96, use_llm=True)
  ↓
_llm_generate_one_sentence (requirements_restructuring.py:575)
  ↓
llm.invoke(prompt) ← 在这里卡住（无超时保护）
```

### 代码问题

**requirements_restructuring.py:595**
```python
response = llm.invoke(prompt)  # ❌ 无超时保护，LLM响应慢时会无限等待
```

虽然 `LLMFactory.create_llm()` 支持 `timeout` 参数，但：
1. 创建时设置了 `timeout=30`（line 579中改为15）
2. 但 `invoke()` 方法的超时依赖于底层SDK实现
3. 在某些网络或LLM服务异常情况下，SDK超时可能失效

## 修复方案

### 1. 添加线程池超时保护（双重保险）

**requirements_restructuring.py:575-617**

```python
@staticmethod
def _llm_generate_one_sentence(goal: str, constraints: str, approach: str) -> str:
    """使用LLM生成流畅的一句话摘要"""

    try:
        # 🔧 v7.142: 添加超时保护，防止LLM调用卡住
        import concurrent.futures

        def llm_call_with_timeout():
            llm = LLMFactory.create_llm(temperature=0.7, max_tokens=200, timeout=15)

            prompt = f"""基于以下信息，生成一句话项目摘要（30-50字）。

项目目标：{goal}
核心约束：{constraints}
实现方式：{approach}

要求：
1. 一句话概括项目核心价值
2. 语言简洁专业，避免冗余
3. 突出用户获得的价值
4. 30-50字

一句话摘要："""

            response = llm.invoke(prompt)
            return response.content.strip()

        # 使用线程池 + 超时机制（双重保险）
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(llm_call_with_timeout)
            try:
                summary = future.result(timeout=20)  # 20秒总超时
                logger.info(f"✅ LLM生成摘要: {summary}")
                return summary
            except concurrent.futures.TimeoutError:
                logger.warning("⚠️ LLM调用超时(20秒)，使用简单版本")
                return f"{goal}，{approach}"

    except Exception as e:
        logger.warning(f"⚠️ LLM调用失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return f"{goal}，{approach}"
```

**关键改进**:
- ✅ 线程池 + `future.result(timeout=20)` 强制超时
- ✅ SDK层 `timeout=15` + 外层 `timeout=20` 双重保险
- ✅ 超时后自动降级到简单拼接版本
- ✅ 减少 `max_tokens` 从 4000→200（生成摘要不需要大token）

### 2. 问卷汇总节点添加超时保护

**questionnaire_summary.py:66-91**

```python
# 3. 执行需求重构
try:
    # 🔧 v7.142: 添加超时保护，防止LLM调用卡住
    import concurrent.futures

    def restructure_with_timeout():
        return RequirementsRestructuringEngine.restructure(
            questionnaire_data,
            ai_analysis,
            analysis_layers,
            user_input,
            use_llm=True  # 启用LLM优化描述
        )

    # 使用线程池 + 超时机制（30秒总超时）
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(restructure_with_timeout)
        try:
            restructured_doc = future.result(timeout=30)
        except concurrent.futures.TimeoutError:
            logger.warning("⚠️ 需求重构超时(30秒)，使用降级方案")
            raise TimeoutError("需求重构超时")

except Exception as e:
    logger.error(f"❌ 需求重构失败: {e}")
    import traceback
    traceback.print_exc()

    # 降级：返回简化版本
    restructured_doc = QuestionnaireSummaryNode._fallback_restructure(
        questionnaire_data,
        ai_analysis,
        user_input
    )
```

**关键改进**:
- ✅ 整个重构流程 30秒总超时
- ✅ 超时后触发 `_fallback_restructure` 降级方案
- ✅ 确保用户体验不受影响（最多等待30秒）

## 验证测试

创建了 [test_llm_timeout_fix_v7142.py](../tests/test_llm_timeout_fix_v7142.py) 包含3个测试用例：

### 测试1: LLM超时保护
- 模拟 LLM 响应延迟 25秒
- 验证 20秒超时生效
- 验证降级方案返回

### 测试2: LLM正常生成
- 验证正常情况下能成功调用
- 验证返回内容质量

### 测试3: 问卷汇总超时降级
- 模拟整个重构流程延迟 35秒
- 验证 30秒超时生效
- 验证降级方案 `fallback_restructure` 被调用

## 运行测试

```bash
# 运行完整测试套件
pytest tests/test_llm_timeout_fix_v7142.py -v

# 快速验证（直接运行）
python tests/test_llm_timeout_fix_v7142.py
```

## 影响范围

### 修改文件
1. `intelligent_project_analyzer/interaction/nodes/requirements_restructuring.py`
   - 修改 `_llm_generate_one_sentence` 方法

2. `intelligent_project_analyzer/interaction/nodes/questionnaire_summary.py`
   - 修改 `execute` 方法中的重构调用

### 降级行为
- **超时前**: 使用LLM生成优质摘要
- **超时后**: 自动降级到简单拼接版本，确保流程继续
- **用户感知**: 最多等待 30秒，体验可控

## 后续优化建议

1. **监控告警**: 添加超时事件监控，及时发现LLM服务异常
2. **性能优化**: 考虑使用更快的模型（如 gpt-4o-mini）生成摘要
3. **缓存机制**: 对相似需求的摘要结果缓存，减少LLM调用
4. **异步处理**: 将非关键路径的LLM调用改为异步，提升用户体验

## 版本标记

- **版本号**: v7.142
- **修复日期**: 2026-01-06
- **严重程度**: P0（阻塞用户完成流程）
- **修复状态**: ✅ 已修复，待测试验证

---

**修复人**: Claude Sonnet 4.5
**审核人**: 待定
**测试人**: 待定
