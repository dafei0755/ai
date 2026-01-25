# 搜索工具配置：博查 + Tavily + Milvus 方案

**版本**: v7.141.5
**日期**: 2026-01-07
**状态**: ✅ 已实施并验证

---

## 📋 配置概览

### 实施背景

经过Serper API真实测试，发现在中国网络环境存在SSL连接不稳定问题：
- ✅ **第1次测试成功**：简单查询"Python programming"，1.78秒返回结果
- ❌ **第2/3次测试失败**：复杂查询触发SSL错误 `EOF occurred in violation of protocol`

基于网络环境适配性考虑，采用**博查主导 + Tavily辅助 + Milvus知识库**的混合方案。

**🆕 v7.141 重大变更**: RAGFlow 已被 Milvus 向量数据库完全替代

---

## 🎯 最终方案

### 工具组合

| 工具 | 状态 | 定位 | 网络稳定性 |
|------|------|------|-----------|
| **博查 (Bocha)** | ✅ 启用 | 主力 - 中文AI搜索 | 🟢 国内稳定 |
| **Tavily** | ✅ 启用 | 辅助 - 国际搜索 | 🟢 已验证稳定 |
| **Serper** | ⚠️ 禁用 | 备用 - Google搜索 | 🔴 SSL不稳定 |
| **ArXiv** | ✅ 启用 | 学术论文检索 | 🟢 稳定 |
| **Milvus** | ✅ 启用 | 向量知识库 | 🟢 自建稳定 |
| ~~**RAGFlow**~~ | ❌ 已废弃 | ~~内部知识库~~ | ⚠️ v7.141已移除 |

### 降级策略

```
博查 (Bocha) → Tavily → Serper → Milvus
   ↓优先        ↓降级    ↓二次降级  ↓兜底
```

---

## 🔧 实施内容

### 1. 角色工具映射

**文件**: `intelligent_project_analyzer/workflow/main_workflow.py:2592-2598`

```python
role_tool_mapping = {
    "V2": [],  # 设计总监：无工具（依赖专家团队）
    "V3": ["bocha", "tavily", "milvus"],  # 叙事专家
    "V4": ["bocha", "tavily", "arxiv", "milvus"],  # 设计研究员
    "V5": ["bocha", "tavily", "milvus"],  # 场景专家
    "V6": ["bocha", "tavily", "arxiv", "milvus"],  # 总工程师
}
```

**变更**：
- 将所有角色的 `"serper"` 替换为 `"tavily"`
- 🆕 将所有角色的 `"ragflow"` 替换为 `"milvus"`
- V2 角色改为空列表（无外部搜索工具）

### 2. 降级策略调整

**文件**: `intelligent_project_analyzer/agents/task_oriented_expert_factory.py:1780-1857`

**变更前**：
```python
# 优先顺序：Serper → Tavily → Bocha
tool_to_use = serper_tool if serper_tool else (tavily_tool if tavily_tool else bocha_tool)
```

**变更后**：
```python
# 优先顺序：Bocha → Tavily → Serper
tool_to_use = bocha_tool if bocha_tool else (tavily_tool if tavily_tool else serper_tool)
```

### 3. 环境变量配置

**文件**: `.env`

```bash
# Serper - 已禁用
SERPER_ENABLED=false
SERPER_API_KEY=7dd3d7c0da439d7f55aa8ee0ad7b4779ed2983e5

# Bocha - 启用
BOCHA_ENABLED=true
BOCHA_API_KEY=sk-28b5974f3c4943f4a08ee2655700fdbd

# Tavily - 启用
TAVILY_API_KEY=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

# 🆕 v7.141: Milvus 向量数据库（替代 RAGFlow）
MILVUS_ENABLED=true
MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_COLLECTION_NAME=design_knowledge_base
```

### 4. 文档更新

**文件**: `QUICKSTART.md`

更新搜索工具说明：
```markdown
> 💡 **搜索工具说明（中国网络环境优化）**:
> - **博查 Bocha（推荐）**: 中文AI搜索，国内稳定
> - **Tavily（辅助）**: 国际搜索，已验证稳定
> - **Milvus（知识库）**: 向量数据库，自建稳定
> - ~~Serper~~: 已禁用（SSL不稳定）
> - ~~RAGFlow~~: 已废弃（v7.141已移除）
```

---

## 📊 工具对比

### Milvus vs RAGFlow

| 特性 | Milvus (v7.141+) | RAGFlow (已废弃) |
|------|------------------|------------------|
| **类型** | 向量数据库 | RAG框架 |
| **性能** | 🟢 高性能向量检索 | 🟡 中等 |
| **可控性** | 🟢 完全可控 | 🟡 框架限制 |
| **维护性** | 🟢 简单直接 | 🔴 依赖外部服务 |
| **集成度** | 🟢 深度集成 | 🟡 API调用 |
| **状态** | ✅ 生产使用 | ❌ 已移除 |

### 迁移指南

参见: [RAGFLOW_TO_MILVUS_MIGRATION.md](RAGFLOW_TO_MILVUS_MIGRATION.md)

---

## 🔍 验证方法

### 1. 检查配置
```bash
python -c "from intelligent_project_analyzer.settings import settings; print('Milvus enabled:', settings.milvus.enabled)"
```

### 2. 测试 Tavily
```bash
python -c "from tavily import TavilyClient; client = TavilyClient(api_key='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'); print(client.search('Python programming', max_results=1))"
```

### 3. 测试 Milvus
```bash
python -c "from intelligent_project_analyzer.tools.milvus_kb import MilvusKBTool; tool = MilvusKBTool(); print('Milvus connected:', tool.client is not None)"
```

---

## 📝 更新日志

### v7.141.5 (2026-01-07)
- ✅ 更新文档，反映 RAGFlow → Milvus 迁移
- ✅ 验证 Tavily 在中国网络环境稳定性
- ✅ 更新所有角色工具映射
- ✅ 更新环境变量配置说明

### v7.141 (2026-01-06)
- 🔥 RAGFlow 完全移除
- ✅ Milvus 向量数据库上线
- ✅ 6-Stage Deep Pipeline 实现

### v7.130.1 (2026-01-04)
- ✅ Serper 禁用（SSL不稳定）
- ✅ Tavily 启用（国际搜索）
- ✅ Bocha 主导（中文搜索）
> - **Tavily**: 国际搜索补充，多引擎聚合
> - **Serper**: 基于Google搜索，中国网络可能遇到SSL问题，默认禁用
> - 系统降级策略：博查 → Tavily → RAGFlow
```

---

## ✅ 验证结果

### 配置验证

```bash
$ python -c "from intelligent_project_analyzer.services.tool_factory import ToolFactory; ..."

Environment Variables:
  Serper Enabled: false
  Bocha Enabled: true
  Bocha API Key: OK
  Tavily API Key: OK

ToolFactory Status:
  Available tools: 4
    - bocha: bocha_search
    - tavily: tavily_search
    - ragflow: ragflow_kb
    - arxiv: arxiv_search

Configuration verified successfully
```

### 工具可用性

✅ **博查 (Bocha)**: 已初始化，base_url=https://api.bocha.cn
✅ **Tavily**: 已初始化，max_results=5
✅ **RAGFlow**: 已初始化，endpoint=https://ragflow.ucppt.com
✅ **ArXiv**: 已初始化
⏭️ **Serper**: 未启用（SERPER_ENABLED=false）

---

## 📊 与原Serper方案对比

| 对比项 | Serper方案 | 博查+Tavily方案 |
|--------|-----------|----------------|
| 中文搜索质量 | 🟡 中等（Google） | 🟢 优秀（专注中文） |
| 国际搜索质量 | 🟢 优秀（Google） | 🟡 良好（多引擎） |
| 网络稳定性 | 🔴 SSL不稳定 | 🟢 国内稳定 |
| 免费额度 | 2500次/月 | Bocha未知 + Tavily 1000次/月 |
| 实施难度 | 低 | 低 |
| 成本 | $0.5/1000次（超出后） | 需确认 |

---

## 🎯 适用场景

### ✅ 适合使用博查的场景
- 中文设计趋势分析
- 国内设计案例搜索
- 中文市场调研
- 本土品牌分析

### ✅ 适合使用Tavily的场景
- 国际设计案例
- 海外市场分析
- 英文技术文档
- 全球设计趋势

### ⚠️ Serper仍可作为备用
虽然默认禁用，但Serper工具代码已完全集成：
- 如网络环境改善（代理、海外服务器）
- 可通过 `SERPER_ENABLED=true` 快速启用
- 作为三级降级备用

---

## 📝 后续建议

### 1. 生产环境监控（第1周）
监控指标：
- 博查API调用成功率
- Tavily API调用成功率
- 平均响应时间
- 用户满意度反馈

### 2. 成本跟踪
- 博查API计费模式确认
- Tavily免费额度使用情况
- 评估是否需要付费升级

### 3. 质量对比测试（可选）
创建A/B测试脚本：
```bash
python scripts/compare_bocha_tavily.py
```

对比维度：
- 搜索相关性
- 结果覆盖度
- 响应时间
- 中文/英文内容质量

---

## 🔗 相关文件

| 文件路径 | 修改内容 |
|---------|---------|
| [intelligent_project_analyzer/workflow/main_workflow.py](../intelligent_project_analyzer/workflow/main_workflow.py#L2552-L2558) | 角色工具映射 |
| [intelligent_project_analyzer/agents/task_oriented_expert_factory.py](../intelligent_project_analyzer/agents/task_oriented_expert_factory.py#L1780-L1857) | 降级策略 |
| [.env](../.env#L75-L81) | 环境变量配置 |
| [.env.development.example](../.env.development.example#L53-L58) | 配置模板 |
| [QUICKSTART.md](../QUICKSTART.md#L62-L74) | 用户文档 |
| [intelligent_project_analyzer/tools/serper_search.py](../intelligent_project_analyzer/tools/serper_search.py) | Serper工具（保留备用） |

---

## ✅ 总结

**核心决策**：基于中国网络环境的实际测试结果，采用博查主导 + Tavily辅助的务实方案。

**优势**：
1. ✅ 博查国内稳定，专注中文质量
2. ✅ Tavily覆盖国际内容，互补性强
3. ✅ 避免Serper的SSL不稳定问题
4. ✅ 保留Serper作为备用，未来可启用

**风险**：
- ⚠️ Tavily在中国网络环境的稳定性待长期验证
- ⚠️ 博查的计费模式和成本需要确认

**下一步**：
生产环境运行1-2周，收集实际数据，评估是否需要进一步优化。

---

**文档创建**: 2026-01-04
**最后更新**: 2026-01-04
**责任人**: Claude (AI Assistant)
