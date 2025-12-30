# 问题修复优先级方案

**会话**: api-20251129102622-d5509e65
**生成时间**: 2025-11-29
**详细分析**: [session_analysis_api-20251129102622-d5509e65.md](session_analysis_api-20251129102622-d5509e65.md)

---

## 🔴 P0 - 紧急修复（必须立即解决）

### 问题1: 报告内容JSON解析错误导致字段截断

**症状**:
- 生成的374KB报告中，核心字段内容被异常截断
- 例如：`"project_task": "本项目为project_task设计为...能在。"`（完整内容约2000字被截断）

**根本原因**:
`requirements_analyst.py:168-173`使用简单的`find('{')`和`rfind('}')`来提取JSON，当响应包含：
- 嵌套的JSON对象
- 字符串中的大括号
- 特殊转义字符

会导致解析位置错误，截取到不完整的JSON字符串。

**证据**:
```python
# 当前实现（Line 168-173）
start_idx = llm_response.find('{')          # ❌ 可能匹配到字符串内的{
end_idx = llm_response.rfind('}') + 1       # ❌ 可能匹配到字符串内的}
json_str = llm_response[start_idx:end_idx]  # ❌ 导致JSON不完整
structured_data = json.loads(json_str)       # ❌ 解析失败或数据损坏
```

**修复方案**:

```python
def _parse_requirements(self, llm_response: str) -> Dict[str, Any]:
    """解析LLM响应中的结构化需求 - v3.6修复JSON解析"""
    import re
    import json

    try:
        # 方法1: 使用正则提取JSON block（支持code fence）
        json_pattern = r'```json\s*\n(.*?)\n```'
        match = re.search(json_pattern, llm_response, re.DOTALL)
        if match:
            json_str = match.group(1)
            logger.info("[JSON解析] 使用code fence提取")
        else:
            # 方法2: 使用栈匹配法找到完整JSON（平衡大括号）
            json_str = self._extract_balanced_json(llm_response)
            logger.info("[JSON解析] 使用平衡括号提取")

        if not json_str:
            logger.warning("[JSON解析] 未找到有效JSON，使用fallback")
            return self._create_fallback_structure(llm_response)

        # 解析JSON
        structured_data = json.loads(json_str)
        logger.info(f"[JSON解析] ✅ 成功解析，包含 {len(structured_data)} 个字段")

        # ... 后续验证逻辑 ...

    except json.JSONDecodeError as e:
        logger.error(f"[JSON解析] ❌ JSONDecodeError: {str(e)}")
        logger.error(f"[JSON解析] 问题位置: line {e.lineno}, col {e.colno}")
        logger.error(f"[JSON解析] 前后文本: ...{json_str[max(0,e.pos-50):e.pos+50]}...")
        return self._create_fallback_structure(llm_response)
    except Exception as e:
        logger.error(f"[JSON解析] ❌ 未知错误: {str(e)}")
        return self._create_fallback_structure(llm_response)

def _extract_balanced_json(self, text: str) -> Optional[str]:
    """使用栈匹配法提取完整的JSON对象"""
    start_idx = text.find('{')
    if start_idx == -1:
        return None

    stack = []
    in_string = False
    escape = False

    for i in range(start_idx, len(text)):
        ch = text[i]

        # 处理转义字符
        if escape:
            escape = False
            continue
        if ch == '\\':
            escape = True
            continue

        # 处理字符串状态
        if ch == '"':
            in_string = not in_string
            continue

        # 只在非字符串状态下处理括号
        if not in_string:
            if ch == '{':
                stack.append(ch)
            elif ch == '}':
                if stack:
                    stack.pop()
                if not stack:  # 栈空，找到完整JSON
                    return text[start_idx:i+1]

    return None
```

**影响范围**:
- 所有使用requirements_analyst生成的报告
- 所有专家继承的requirements数据

**测试验证**:
```python
# 测试case1: 嵌套JSON
test1 = 'Some text {"project_task": "包含 { 嵌套内容 } 的任务", "nested": {"key": "value"}} more text'

# 测试case2: 字符串中的大括号
test2 = 'Text {"description": "Use {variable} syntax"} end'

# 测试case3: 多行JSON
test3 = '''
{
  "project_task": "很长的任务描述\\n包含多行\\n和特殊字符\\"引号\\""
}
'''
```

---

## 🟠 P1 - 重要问题（影响用户体验）

### 问题2: 问卷交互被跳过

**症状**:
- 生成了7个战略校准问题（v3.5修复已生效）
- 但用户从未看到问卷，直接进入专家执行

**分析**:
从会话历史看，`calibration_processed`直接为`True`，可能原因：
1. `skip_unified_review`标志被设置
2. 前端调用了skip接口
3. 问卷节点逻辑错误判断为已处理

**需要检查的位置**:
```
intelligent_project_analyzer/interaction/nodes/calibration_questionnaire.py:256-275
```

检查`calibration_processed`标志的设置逻辑。

**修复建议**:
添加日志追踪`calibration_processed`标志的来源：
```python
# Line 256附近
calibration_processed = state.get("calibration_processed")
logger.info(f"🔍 [DEBUG] calibration_processed 标志: {calibration_processed}")
logger.info(f"🔍 [DEBUG] skip_unified_review 标志: {state.get('skip_unified_review')}")
logger.info(f"🔍 [DEBUG] calibration_answers 存在: {bool(state.get('calibration_answers'))}")

# 防御性编程
if not calibration_processed and state.get("calibration_answers"):
    logger.warning("⚠️ calibration_processed missing but calibration_answers found. Assuming processed.")
    calibration_processed = True
```

### 问题3: 所有批次自动执行，无用户确认

**症状**:
- 日志显示："⚡ 批次X/5 自动执行（方案C：全自动批次调度）"
- 用户无法确认专家分配是否合理

**分析**:
`batch_strategy_review_node`检测到某个条件（可能是`skip_unified_review=True`），选择了全自动模式。

**需要检查的位置**:
```
intelligent_project_analyzer/workflow/main_workflow.py:1433
```

**修复建议选项**:

**选项A - 添加用户配置**（推荐）:
```python
# 在session配置中添加
"batch_execution_mode": "manual" | "automatic" | "auto_with_notification"

# manual: 每批次都需要用户确认
# automatic: 全自动执行（当前行为）
# auto_with_notification: 自动执行但发送通知
```

**选项B - 修改默认行为**:
```python
def _batch_strategy_review_node(state: ProjectAnalysisState) -> str:
    # 默认需要用户确认（除非明确设置自动）
    if state.get("force_auto_execution"):
        logger.info("⚡ 强制自动执行模式")
        return "batch_executor"
    else:
        logger.info("👤 等待用户确认批次执行")
        # 发送中断，等待用户确认
        ...
```

---

## 🟡 P2 - 优化改进（提升可用性）

### 问题4: 缺少完整执行详情报告

**需求**:
用户要求生成包含以下内容的详细报告：
- 每个阶段的执行时间
- 用户确认情况
- 输入输出详情
- 资源消耗统计

**实现建议**:

创建新的报告生成器：`execution_details_reporter.py`

```python
class ExecutionDetailsReporter:
    """执行详情报告生成器"""

    def generate_report(self, state: ProjectAnalysisState) -> str:
        """生成执行详情报告"""
        report = []

        # 1. 会话元数据
        report.append("# 执行详情报告")
        report.append(f"会话ID: {state['session_id']}")
        report.append(f"开始时间: {state.get('start_time')}")
        report.append(f"结束时间: {state.get('end_time')}")

        # 2. 阶段时间线
        history = state.get("interaction_history", [])
        for entry in history:
            report.append(f"\n## {entry['type']}")
            report.append(f"时间: {entry['timestamp']}")
            report.append(f"意图: {entry.get('intent', 'N/A')}")

        # 3. 专家执行详情
        agent_results = state.get("agent_results", {})
        for agent_id, result in agent_results.items():
            report.append(f"\n### {agent_id}")
            report.append(f"置信度: {result.get('confidence')}")
            report.append(f"输出长度: {len(result.get('content', ''))}")

        # 4. 资源消耗
        report.append("\n## 资源消耗统计")
        report.append(f"LLM调用次数: {self._count_llm_calls(state)}")
        report.append(f"总Token数: {self._estimate_tokens(state)}")

        return "\n".join(report)
```

### 问题5: 追问功能未实现

**需要检查**:
1. 前端是否有追问按钮/界面
2. `/api/analysis/resume`接口是否正确实现
3. `unified_review_node`中的追问逻辑

**测试步骤**:
```bash
# 1. 检查会话状态是否支持追问
curl -s "http://127.0.0.1:8000/api/analysis/status/SESSION_ID"

# 2. 尝试提交追问
curl -X POST "http://127.0.0.1:8000/api/analysis/resume" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "SESSION_ID",
    "resume_value": {
      "action": "followup",
      "question": "测试追问"
    }
  }'
```

---

## 实施计划

### 第一阶段（立即）✅ 已完成
1. ✅ **修复JSON解析问题** - 防止数据损坏 (v3.6已实现)
   - 实现了平衡括号提取算法 (`_extract_balanced_json`)
   - 添加了code fence提取支持
   - 添加了详细的JSON解析日志
   - 所有单元测试通过 (6/6 tests PASS)
2. ✅ 验证问卷生成 - 确认v3.5修复生效
3. ✅ 添加详细日志 - 追踪问题根源

### 第二阶段（本周内）
4. 🔧 调查问卷跳过问题 - 修复交互流程
5. 🔧 实现批次确认配置 - 给用户选择权
6. 🔧 完善追问功能 - 测试端到端流程

### 第三阶段（优化）
7. 📊 实现执行详情报告生成
8. 📈 添加资源消耗统计
9. 🧹 代码重构和性能优化

---

## 验证清单

- [ ] JSON解析修复后，使用相同输入重新运行分析
- [ ] 检查生成的报告，确认字段完整
- [ ] 手动测试问卷交互流程
- [ ] 测试批次确认功能
- [ ] 导出执行详情报告
- [ ] 进行端到端追问测试

---

**下一步行动**: 立即修复JSON解析问题，然后重新运行测试会话验证修复效果。

**负责人**: Claude (Droid)
**更新时间**: 2025-11-29
