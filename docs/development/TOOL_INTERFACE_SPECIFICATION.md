# 工具类接口规范 (Tool Interface Specification)

> **版本**: v7.117
> **日期**: 2026-01-02
> **状态**: 强制执行

## 目的

统一所有工具类的接口实现，确保与 LangChain 的 `bind_tools()` 方法完全兼容，避免属性缺失导致的运行时错误。

## 强制性要求

### 1. 必须实现的属性

所有工具类**必须**同时实现以下两个属性：

#### ✅ `self.name` (直接属性)
```python
self.name = "tool_name"
```

- **用途**: LangChain `bind_tools()` 直接访问
- **类型**: `str`
- **命名规范**: 小写字母 + 下划线，例如 `bocha_search`, `tavily_search`

#### ✅ `self.config` (ToolConfig 对象)
```python
from intelligent_project_analyzer.core.types import ToolConfig

self.config = config or ToolConfig(name="tool_name")
self.name = self.config.name  # 从 config 同步
```

- **用途**: 统一配置管理
- **类型**: `ToolConfig` (dataclass)
- **包含**: `name`, `enabled`, `api_key`, `endpoint`, `timeout`, `max_retries`, `config`

### 2. 标准初始化模板

```python
from typing import Optional
from intelligent_project_analyzer.core.types import ToolConfig

class YourSearchTool:
    def __init__(
        self,
        api_key: str,
        config: Optional[ToolConfig] = None  # ✅ 可选配置参数
    ):
        self.api_key = api_key

        # ✅ 初始化 config（带默认值）
        self.config = config or ToolConfig(name="your_search")

        # ✅ 从 config 同步 name（LangChain 兼容性）
        self.name = self.config.name
```

### 3. 为什么需要两者？

| 属性 | 访问者 | 用途 |
|------|--------|------|
| `self.name` | LangChain `bind_tools()` | 工具绑定时的直接属性访问 |
| `self.config.name` | 内部系统 | 配置管理、日志、工具注册 |

**核心原则**: `self.name` 应始终等于 `self.config.name`

## 当前系统中的工具类

### ✅ 已修复（符合规范）

| 工具类 | 文件路径 | name 值 | 修复版本 |
|--------|----------|---------|----------|
| **BochaSearchTool** | `agents/bocha_search_tool.py` | `bocha_search` | v7.117 |
| **TavilySearchTool** | `tools/tavily_search.py` | `tavily_search` | v7.117 |
| **ArxivSearchTool** | `tools/arxiv_search.py` | `arxiv_search` | v7.117 |
| **RagflowKBTool** | `tools/ragflow_kb.py` | `ragflow_kb` | v7.117 |

### 验证方法

使用自动化测试验证工具符合规范：

```bash
python tests/check_all_tools_name.py
```

**预期输出**:
```
✅ 所有工具都正确实现了 name 属性
```

## 新工具类开发指南

### Step 1: 导入 ToolConfig
```python
from intelligent_project_analyzer.core.types import ToolConfig
```

### Step 2: 在 `__init__` 中初始化
```python
def __init__(self, ..., config: Optional[ToolConfig] = None):
    # ... 其他初始化
    self.config = config or ToolConfig(name="new_tool")
    self.name = self.config.name  # ✅ 必需
```

### Step 3: 在 ToolFactory 中注册
```python
# intelligent_project_analyzer/services/tool_factory.py

@staticmethod
def create_new_tool(config: Optional[NewToolConfig] = None):
    from intelligent_project_analyzer.tools.new_tool import NewTool
    from intelligent_project_analyzer.core.types import ToolConfig

    tool_config = ToolConfig(name="new_tool")

    return NewTool(
        api_key=config.api_key,
        config=tool_config  # ✅ 传递 ToolConfig
    )
```

### Step 4: 更新角色工具映射
```python
# intelligent_project_analyzer/workflow/main_workflow.py

role_tool_mapping = {
    "V2": [],
    "V3": ["bocha", "tavily", "new_tool"],  # ✅ 添加新工具
    ...
}
```

## 常见错误及解决方案

### ❌ 错误 1: 缺少 `self.name`
```python
# ❌ 错误示例
def __init__(self, api_key: str):
    self.api_key = api_key
    self.config = ToolConfig(name="tool")
    # 缺少 self.name!
```

**错误信息**:
```
'YourTool' object has no attribute 'name'
```

**解决方案**:
```python
# ✅ 正确示例
def __init__(self, api_key: str):
    self.api_key = api_key
    self.config = ToolConfig(name="tool")
    self.name = self.config.name  # ✅ 添加这一行
```

### ❌ 错误 2: 不接受 `config` 参数
```python
# ❌ 错误示例
def __init__(self, api_key: str):  # 缺少 config 参数
    self.api_key = api_key
```

**解决方案**:
```python
# ✅ 正确示例
def __init__(self, api_key: str, config: Optional[ToolConfig] = None):
    self.api_key = api_key
    self.config = config or ToolConfig(name="tool")
    self.name = self.config.name
```

### ❌ 错误 3: name 与 config.name 不一致
```python
# ❌ 错误示例
self.config = ToolConfig(name="search_tool")
self.name = "SearchTool"  # 不一致！
```

**解决方案**:
```python
# ✅ 正确示例
self.config = ToolConfig(name="search_tool")
self.name = self.config.name  # 从 config 同步，确保一致
```

## 测试检查清单

新工具开发完成后，必须通过以下测试：

- [ ] `hasattr(tool, 'name')` 返回 `True`
- [ ] `hasattr(tool, 'config')` 返回 `True`
- [ ] `tool.name == tool.config.name`
- [ ] `tool.name` 是字符串且不为空
- [ ] 工具可以被 `ToolFactory.create_all_tools()` 成功创建
- [ ] 工具可以被 LangChain `bind_tools()` 绑定而不报错

## 自动化检查

系统包含自动化检查脚本：

```bash
# 检查所有工具类
python tests/check_all_tools_name.py

# 检查特定工具
python tests/test_bocha_name_fix.py
```

## 参考资料

- **ToolConfig 定义**: [intelligent_project_analyzer/core/types.py](../intelligent_project_analyzer/core/types.py)
- **工具工厂**: [intelligent_project_analyzer/services/tool_factory.py](../intelligent_project_analyzer/services/tool_factory.py)
- **示例实现**: [intelligent_project_analyzer/agents/bocha_search_tool.py](../intelligent_project_analyzer/agents/bocha_search_tool.py)

## 修订历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| v7.117 | 2026-01-02 | 创建规范，修复所有现有工具类 |

---

**强制执行**: 所有新工具类必须通过 Code Review 检查是否符合此规范。
