# 外部工具模块 - AI 协作文档

> 📍 **路径导航**: [根目录](../../CLAUDE.md) > [intelligent_project_analyzer](../) > **tools**

---

## 📋 模块职责

**外部工具集成 (External Tools Integration)**

本模块集成多个外部工具和 API，为智能体提供信息检索、知识查询等能力。

### 核心功能
- 🔍 **Tavily 搜索**: 互联网实时搜索
- 📚 **Arxiv 搜索**: 学术论文检索
- 🗄️ **RAGFlow 知识库**: 本地知识库查询（可选）

---

## 📁 文件结构

```
tools/
├── tavily_search.py       # Tavily 搜索工具
├── arxiv_search.py        # Arxiv 学术搜索工具
└── ragflow_kb.py          # RAGFlow 知识库工具
```

---

## 🔑 核心工具

### 1. Tavily Search（互联网搜索）

**用途**: 实时搜索互联网内容，获取最新设计趋势、案例等。

**配置**:
```python
# .env
TAVILY_API_KEY=tvly-xxx
```

**使用示例**:
```python
from intelligent_project_analyzer.tools.tavily_search import tavily_search_tool

results = tavily_search_tool.invoke({"query": "商业空间设计趋势 2024"})
```

---

### 2. Arxiv Search（学术论文检索）

**用途**: 检索 arxiv.org 学术论文，获取理论支撑。

**使用示例**:
```python
from intelligent_project_analyzer.tools.arxiv_search import arxiv_search_tool

papers = arxiv_search_tool.invoke({"query": "interior design methodology"})
```

---

### 3. RAGFlow Knowledge Base（知识库查询）

**用途**: 查询本地部署的 RAGFlow 知识库（设计指南、最佳实践等）。

**配置**:
```python
# .env
RAGFLOW_ENDPOINT=http://localhost:9380
RAGFLOW_API_KEY=ragflow-xxx
```

**使用示例**:
```python
from intelligent_project_analyzer.tools.ragflow_kb import ragflow_kb_tool

docs = ragflow_kb_tool.invoke({"query": "商业空间设计指南"})
```

---

## 🛠️ 工具注册

工具由 `SpecializedAgentFactory` 自动注册给智能体：

```python
# 第一批专家 (V3, V4, V5): 不使用工具
# 第二批专家 (V2, V6): 使用工具

V2 (设计总监): [ragflow_kb_tool]
V6 (实施规划师): [tavily_search_tool, arxiv_search_tool, ragflow_kb_tool]
```

---

## 📚 相关资源

- [智能体系统](../agents/CLAUDE.md)
- [Tavily API](https://tavily.com/)
- [Arxiv API](https://arxiv.org/help/api/)
- [RAGFlow](https://github.com/infiniflow/ragflow)

---

**最后更新**: 2025-11-16
**覆盖率**: 100%
**文档版本**: 1.0.0
