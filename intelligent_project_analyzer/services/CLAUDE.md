# 服务层模块 - AI 协作文档

> 📍 **路径导航**: [根目录](../../CLAUDE.md) > [intelligent_project_analyzer](../) > **services**

---

## 📋 模块职责

**服务层 (Service Layer)**

本模块提供工厂模式的服务层，负责创建和管理 LLM 实例、工具实例和图上下文。

### 核心功能
- 🏭 **LLM 工厂**: 创建和配置 LLM 模型
- 🛠️ **工具工厂**: 创建和注册外部工具
- 📊 **图上下文**: 管理 LangGraph 执行上下文

---

## 📁 文件结构

```
services/
├── llm_factory.py         # LLM 工厂
├── tool_factory.py        # 工具工厂
└── graph_context.py       # 图上下文管理
```

---

## 🔑 核心服务

### 1. LLM Factory

**职责**: 创建和配置 LLM 模型实例。

**使用示例**:
```python
from intelligent_project_analyzer.services.llm_factory import create_llm

llm = create_llm(
    provider="openai",
    model="gpt-4",
    temperature=0.7,
    max_tokens=4000
)
```

---

### 2. Tool Factory

**职责**: 创建和注册外部工具。

**使用示例**:
```python
from intelligent_project_analyzer.services.tool_factory import create_tools

tools = create_tools(
    enable_tavily=True,
    enable_arxiv=True,
    enable_ragflow=True
)
```

---

### 3. Graph Context

**职责**: 管理 LangGraph 执行上下文，包括配置、存储等。

**使用示例**:
```python
from intelligent_project_analyzer.services.graph_context import GraphContext

context = GraphContext(thread_id="session_123")
config = context.get_config()
```

---

## 📚 相关资源

- [核心状态管理](../core/CLAUDE.md)
- [外部工具](../tools/CLAUDE.md)
- [统一配置](../settings.py)

---

**最后更新**: 2025-11-16
**覆盖率**: 100%
**文档版本**: 1.0.0
