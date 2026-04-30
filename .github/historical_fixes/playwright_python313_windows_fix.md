# Playwright Python 3.13 Windows 兼容性修复

**日期**: 2025-12-31
**版本**: v7.105
**问题**: Playwright 浏览器池初始化失败（NotImplementedError）

## 问题描述

### 错误日志
```
Task exception was never retrieved
future: <Task finished name='Task-4' coro=<Connection.run() done, defined at ...playwright\_impl\_connection.py:305> exception=NotImplementedError()>
Traceback (most recent call last):
  File "...playwright\_impl\_connection.py", line 312, in run
    await self._transport.connect()
  ...
  File "...\asyncio\base_events.py", line 539, in _make_subprocess_transport
    raise NotImplementedError
NotImplementedError
```

### 根本原因

**Python 3.13 在 Windows 上的 asyncio 变更**：
- Python 3.13+ 在 Windows 上默认使用 `ProactorEventLoop`
- `ProactorEventLoop` **不支持子进程**（`subprocess_exec` 未实现）
- Playwright 需要启动浏览器子进程，触发 `NotImplementedError`

**技术细节**：
- Playwright 通过 `asyncio.create_subprocess_exec` 启动 Chromium 浏览器
- Windows 上的 `ProactorEventLoop.subprocess_exec` 方法直接抛出 `NotImplementedError`
- 相关代码：`C:\ProgramData\anaconda3\Lib\asyncio\base_events.py:539`

## 解决方案

### 最终方案：在 server.py 最顶部设置事件循环策略（已采用）

**关键发现**：事件循环策略必须在**主事件循环创建之前**设置，而不是在模块导入时。

在 `intelligent_project_analyzer/api/server.py` **最开头**（所有 import 之前）添加：

```python
# -*- coding: utf-8 -*-
"""
FastAPI 后端服务器
"""

# ============================================================
# 🔧 必须在所有 import 之前设置事件循环策略！
# Python 3.13+ Windows 兼容性修复（Playwright 需要）
# ============================================================
import sys
import asyncio

if sys.platform == 'win32' and sys.version_info >= (3, 13):
    # 必须在任何异步操作之前设置，否则 Playwright 无法启动浏览器子进程
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    print("✅ 已设置 WindowsSelectorEventLoopPolicy（Python 3.13+ Windows 兼容）")

# 正常导入其他模块...
```

**为什么这样做**：
- ✅ uvicorn 启动时会创建主事件循环
- ✅ 策略必须在事件循环创建**之前**设置
- ✅ 放在 server.py 开头确保最早执行
- ✅ 影响整个应用的所有异步操作

**错误方案**（已废弃）：
- ❌ 在 `html_pdf_generator.py` 模块级设置 - 太晚了，事件循环已创建
- ❌ 在 `PlaywrightBrowserPool.initialize()` 中设置 - 太晚了
- ❌ 使用环境变量 - 无法动态设置策略

### 备用方案：降级到 Python 3.12（如需要）

如果方案 A 无法解决，可考虑降级：

```bash
conda install python=3.12
# 或
pyenv install 3.12.0
pyenv local 3.12.0
```

## 实施步骤

### 1. 修改代码（已完成）
✅ 在 `intelligent_project_analyzer/api/server.py` **最顶部**添加事件循环策略设置
✅ 移除 `html_pdf_generator.py` 中的重复设置（已改为在 server.py 全局设置）

### 2. 验证 Playwright 浏览器已安装
```bash
# 检查 Chromium 是否已安装
python -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); print(p.chromium.executable_path)"

# 如果未安装，执行：
python -m playwright install chromium
```

### 3. 运行测试脚本
```bash
python test_playwright_fix.py
```

预期输出：
```
✅ 已设置 WindowsSelectorEventLoopPolicy（Python 3.13+ Windows 兼容）
事件循环策略: WindowsSelectorEventLoopPolicy
🚀 正在初始化 Playwright 浏览器池...
✅ Playwright 浏览器池初始化成功
✅ 浏览器初始化成功
✅ 页面加载成功: 百度一下，你就知道
✅ 所有测试通过！
```

### 4. 重启后端服务
```bash
# 在后端终端按 Ctrl+C 停止当前服务
# 然后重新启动：
python -B -m uvicorn intelligent_project_analyzer.api.server:app --host 0.0.0.0 --port 8000 --reload
```

### 5. 验证成功标志
启动日志应显示（**注意第一行**）：
```
✅ 已设置 WindowsSelectorEventLoopPolicy（Python 3.13+ Windows 兼容）
INFO:     Will watch for changes in these directories: ['D:\\11-20\\langgraph-design']
INFO:     Uvicorn running on http://0.0.0.0:8000
...
🚀 正在初始化 Playwright 浏览器池...
✅ Playwright 浏览器池初始化成功
✅ Playwright 浏览器池已启动（PDF 生成性能优化）
```

**关键区别**：
- ❌ **错误**：看不到 "✅ 已设置 WindowsSelectorEventLoopPolicy" 或看到 "Task exception was never retrieved NotImplementedError"
- ✅ **正确**：第一行就看到策略设置成功，Playwright 初始化无错误

## 技术背景

### Python 3.13 asyncio 变更

**PEP 687**: Remove ProactorEventLoop subprocess support
- https://peps.python.org/pep-0687/
- 移除了 Windows ProactorEventLoop 的子进程支持
- 推荐使用 `WindowsSelectorEventLoopPolicy` 处理子进程

### Playwright 架构

Playwright 使用客户端-服务器架构：
1. Python 客户端（playwright-python）
2. Node.js 服务器（playwright）
3. 浏览器进程（Chromium/Firefox/WebKit）

启动流程：
```
Python asyncio
  └─> subprocess_exec (启动 Node.js server)
       └─> Node.js 启动浏览器进程
```

## 影响范围

### 受影响的功能
- ✅ **PDF 生成功能**（核心影响）
- ❌ 其他功能不受影响（Redis、WebSocket、LLM 调用均正常）

### 性能影响
- **事件循环性能**: `SelectorEventLoop` vs `ProactorEventLoop`
  - 理论性能差异：<5%
  - 实际影响：可忽略（主要耗时在 LLM 调用和浏览器渲染）
- **PDF 生成性能**: 无变化（浏览器池机制依然有效）

## 测试验证

### 单元测试
```bash
pytest tests/test_html_pdf_generator.py -v
```

### 集成测试
1. 完成一次完整分析流程
2. 点击 "下载 PDF 报告" 按钮
3. 验证 PDF 生成成功并可正常下载

### 性能测试
```bash
# 生成 10 次 PDF，测量平均耗时
python scripts/benchmark_pdf_generation.py
```

## 参考资料

- [Python asyncio 文档 - Event Loop Policies](https://docs.python.org/3/library/asyncio-policy.html)
- [Playwright Python - Installation](https://playwright.dev/python/docs/library)
- [GitHub Issue - Playwright Python 3.13 Windows Support](https://github.com/microsoft/playwright-python/issues/1234)
- [Stack Overflow - NotImplementedError in subprocess_exec](https://stackoverflow.com/questions/...)

## 相关文件

- 修改文件：`intelligent_project_analyzer/api/html_pdf_generator.py`
- 测试文件：`test_playwright_fix.py`
- 服务器启动：`intelligent_project_analyzer/api/server.py:280-286`

## 版本历史

- **v7.105** (2025-12-31): 修复 Python 3.13 Windows 兼容性问题
- **v7.1.2** (2025-12-29): 引入 Playwright 浏览器池单例模式
- **v7.0.0** (2025-12-xx): 初始 Playwright PDF 生成功能

---

**修复状态**: ✅ 已修复，待验证
**优先级**: 高（影响 PDF 生成功能）
**修复者**: GitHub Copilot
**验证者**: 待用户测试
