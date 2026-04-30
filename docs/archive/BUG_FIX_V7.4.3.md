# Bug Fix v7.4.3: 添加超时保护和异常处理

**修复日期:** 2025-12-11
**版本:** v7.4.3
**严重程度:** 🟡 High (P1)

---

## 问题描述

### 症状
- 工作流在 `calibration_questionnaire` 节点卡住
- 后端日志显示 "Step B: 开始调用 KeywordExtractor.extract()..." 后无后续输出
- 错误日志: `cannot access local variable 'user_input' where it is not associated with a value`
- 工作流无法继续执行

### 根本原因
**变量作用域错误：**
1. `user_input` 变量在第324行（`if not questionnaire` 块内）定义
2. 但在第405行（`if` 块外）又被使用
3. 如果 `questionnaire` 已存在，第405行会找不到 `user_input`
4. 导致 `NameError` 或 `UnboundLocalError`

**次要问题：**
1. 日志输出可能因为数据序列化问题而阻塞
2. 缺少异常处理和超时保护
3. 如果 `extract()` 真的卡住，没有降级策略

---

## 修复方案

### 1. 修复变量作用域错误

**问题代码:**
```python
# 第320行: if 块内定义
if not questionnaire or not questionnaire.get("questions"):
    user_input = state.get("user_input", "")  # 只在 if 块内可见
    ...

# 第405行: if 块外使用
user_input = state.get("user_input", "")  # 重复定义，但如果 if 未执行会出错
scenario_type = CalibrationQuestionnaireNode._identify_scenario_type(user_input, structured_data)
```

**修复后:**
```python
# 第305行: 在所有代码块之前定义
user_input = state.get("user_input", "")  # 全局可用

# 第320行: if 块内直接使用
if not questionnaire or not questionnaire.get("questions"):
    # 不再重复定义
    ...

# 第405行: 直接使用，不再重复定义
scenario_type = CalibrationQuestionnaireNode._identify_scenario_type(user_input, structured_data)
```

### 2. 添加日志保护

**修改前:**
```python
logger.info(f"🔍 [DEBUG] Step B.1: user_input length={len(user_input)}")
logger.info(f"🔍 [DEBUG] Step B.2: structured_data keys={list(structured_data.keys()) if structured_data else 'None'}")
```

**修改后:**
```python
try:
    logger.info(f"🔍 [DEBUG] Step B.1: user_input length={len(user_input)}")
except Exception as e:
    logger.warning(f"⚠️ [DEBUG] Step B.1 failed: {e}")
try:
    logger.info(f"🔍 [DEBUG] Step B.2: structured_data keys={list(structured_data.keys()) if structured_data else 'None'}")
except Exception as e:
    logger.warning(f"⚠️ [DEBUG] Step B.2 failed: {e}")
```

### 2. 添加超时保护（非Windows系统）

```python
import signal
import sys

def timeout_handler(signum, frame):
    raise TimeoutError("KeywordExtractor.extract() 超时")

try:
    # 设置5秒超时（仅在非Windows系统）
    if sys.platform != 'win32':
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(5)

    extracted_info = KeywordExtractor.extract(user_input, structured_data)

    # 取消超时
    if sys.platform != 'win32':
        signal.alarm(0)

    logger.info(f"🔍 [DEBUG] Step C: KeywordExtractor.extract() 完成，提取了 {len(extracted_info)} 个字段")
except TimeoutError as e:
    logger.error(f"❌ KeywordExtractor.extract() 超时，使用空结果")
    extracted_info = KeywordExtractor._empty_result()
except Exception as e:
    logger.error(f"❌ KeywordExtractor.extract() 失败: {e}")
    import traceback
    traceback.print_exc()
    extracted_info = KeywordExtractor._empty_result()
```

### 3. 降级策略

如果 `KeywordExtractor.extract()` 失败或超时：
- 使用 `KeywordExtractor._empty_result()` 返回空结果
- 工作流继续执行，使用通用问卷
- 记录错误日志，便于后续排查

---

## 修复文件清单

### 修改的文件

1. **[intelligent_project_analyzer/interaction/nodes/calibration_questionnaire.py](intelligent_project_analyzer/interaction/nodes/calibration_questionnaire.py)**
   - 第305行：将 `user_input` 定义移到所有代码块之前
   - 第330-367行：添加异常处理和超时保护
   - 第405行：删除重复的 `user_input` 定义

### 新增的文件

2. **[BUG_FIX_V7.4.3.md](BUG_FIX_V7.4.3.md)**
   - 本文档

---

## 测试验证

### 测试方法

1. **重启后端服务**
   ```bash
   # 停止当前服务 (Ctrl+C)
   python -B -m uvicorn intelligent_project_analyzer.api.server:app --host 0.0.0.0 --port 8000
   ```

2. **提交设计需求**
   - 在前端提交任意设计需求
   - 观察后端日志

3. **预期结果**
   - 应该看到 "Step B.1" 和 "Step B.2" 的日志
   - 应该看到 "Step C: KeywordExtractor.extract() 完成"
   - 工作流应该继续到 "Step D: 开始调用 FallbackQuestionGenerator.generate()..."
   - 如果超时，应该看到错误日志并使用空结果继续

### 性能指标

| 指标 | 目标 | 说明 |
|------|------|------|
| `extract()` 执行时间 | < 1秒 | 正常情况 |
| 超时阈值 | 5秒 | 非Windows系统 |
| 降级策略 | 100% | 失败时使用空结果 |

---

## 限制和注意事项

### Windows 系统限制

- `signal.SIGALRM` 在 Windows 上不可用
- Windows 系统无法使用超时保护
- 但仍有异常捕获和降级策略

### 替代方案（Windows）

如果需要在 Windows 上实现超时，可以使用：
1. `threading.Timer` + 线程中断
2. `multiprocessing` + 进程超时
3. `asyncio.wait_for()` + 异步超时

---

## 后续优化建议

### 短期 (P1)

1. **实现跨平台超时**
   - 使用 `threading.Timer` 替代 `signal.SIGALRM`
   - 支持 Windows 系统

2. **添加性能监控**
   - 记录 `extract()` 执行时间
   - 统计超时次数
   - 发送告警

### 中期 (P2)

3. **优化日志输出**
   - 避免在日志中序列化大型对象
   - 使用 `repr()` 或 `str()` 限制输出长度

4. **添加单元测试**
   - 测试超时场景
   - 测试异常场景
   - 测试降级策略

---

## 相关链接

- **前置修复:** [BUG_FIX_REGEX_TIMEOUT.md](BUG_FIX_REGEX_TIMEOUT.md) (v7.4.2)
- **测试脚本:** [test_extractor_real.py](test_extractor_real.py)

---

## 总结

v7.4.3 修复通过添加：
1. ✅ 日志保护（异常处理）
2. ✅ 超时保护（非Windows系统）
3. ✅ 降级策略（使用空结果）

确保工作流在任何情况下都能继续执行，不会因为 `KeywordExtractor` 的问题而卡住。

**修复状态:** ✅ 已完成
**需要重启服务:** ✅ 是（修改了核心代码）
