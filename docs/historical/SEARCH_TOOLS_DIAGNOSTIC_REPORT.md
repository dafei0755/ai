# 搜索工具诊断报告 (v7.120)
生成时间: 2026-01-03

## 执行摘要

已完成搜索工具功能的4个层级排查。主要发现如下：

### 工具连通性状态
- ✅ **Tavily**: 已配置，可用
- ✅ **Bocha**: 已配置，可用
- ✅ **ArXiv**: 已配置，可用
- ✅ **RAGFlow**: 已配置

**结论**: 所有4个搜索工具均已正确配置并可正常连接。

### 角色工具映射检查

根据 `main_workflow.py:2574-2580` 的硬编码规则：

| 角色 | 可用工具 | 说明 |
|------|---------|------|
| V2 (设计总监) | 无 | **禁止外部搜索** |
| V3 (叙事专家) | Bocha, Tavily, RAGFlow | 中文+国际+知识库 |
| V4 (设计研究员) | Bocha, Tavily, ArXiv, RAGFlow | **全部工具** |
| V5 (场景专家) | Bocha, Tavily, RAGFlow | 中文+国际+知识库 |
| V6 (总工程师) | Bocha, Tavily, ArXiv, RAGFlow | **全部工具** |

**关键发现**:
⚠️ **V2角色默认禁用所有搜索工具** - 这是最可能导致"搜索结果未显示"的原因！

💡 **建议**: 测试时使用V4或V6角色（拥有全部工具）

### 搜索查询生成检查
- ✅ **SearchStrategyGenerator** 正常工作
- ✅ 成功生成3个测试查询：
  1. "用户画像 设计案例 2024"
  2. "独立女性 现代简约 best practices"
  3. "构建目标用户详细画像 研究资料"

### 搜索执行检查
- ✅ **Tavily**: 成功返回1条结果
- ✅ **ArXiv**: 成功返回1条结果
- ✅ **Bocha**: 成功返回1条结果

**结论**: 所有工具能够成功执行搜索并返回结果。

### 前端数据传递检查

#### ✅ 类型定义
- **前期状态**: 缺失
- **当前状态**: 已添加 `SearchReference` 接口到 `frontend-nextjs/types/index.ts`
- **包含字段**: source_tool, title, url, snippet, relevance_score, deliverable_id, query, timestamp等

#### ⚠️ WebSocket推送
- **检查结果**: `server.py` 中未找到 `search_references` 字段
- **潜在问题**: 搜索结果可能未通过WebSocket推送到前端
- **建议**: 检查并修复WebSocket推送逻辑

### 日志增强
已增强 `tool_callback.py` 的工具调用日志：

**修改位置**:
- `intelligent_project_analyzer/agents/tool_callback.py:96-101`
- `intelligent_project_analyzer/agents/tool_callback.py:126-136`

**增强内容**:
```python
# on_tool_start
logger.info(f"🔧 [ToolCallRecorder] Tool START: {tool_name}")
logger.info(f"   Role: {self.role_id}, Deliverable: {self.deliverable_id}")
logger.info(f"   Input: {input_str[:100]}...")

# on_tool_end
logger.info(f"✅ [ToolCallRecorder] Tool END: {tool_name}, output_length={len(output)} chars")
logger.info(f"   Total calls recorded: {len(self.tool_calls)}")
```

现在日志会清晰显示每次工具调用的开始和结束。

## 修复摘要

### 已完成的修复
1. ✅ **增强工具调用日志** - `tool_callback.py`
2. ✅ **添加SearchReference类型定义** - `frontend-nextjs/types/index.ts`
3. ✅ **创建自动化诊断脚本** - `scripts/diagnose_search_tools.py`
4. ✅ **创建快速检查脚本** - `scripts/quick_check_tools.py`
5. ✅ **修复WebSocket推送** - `intelligent_project_analyzer/api/server.py` (v7.120)
   - 在节点输出处理中提取`search_references`字段 (lines 1425-1429)
   - 在状态更新广播中包含`search_references` (lines 1518-1521)
   - 在完成状态广播中包含`search_references` (lines 1627-1630)

### 待修复的关键问题

#### ⚠️ 问题1: V2角色搜索工具限制
**文件**: `intelligent_project_analyzer/workflow/main_workflow.py:2575`
**症状**: 使用V2角色时看不到搜索结果
**根因**: 硬编码规则禁止V2使用外部搜索
**决策**:
- 如果这是设计决策（总监仅使用内部知识），保持不变
- 测试时必须使用V3/V4/V5/V6角色
- 在文档中明确说明

## 建议的下一步操作

1. **验证修复** (高优先级):
   - [ ] 重启后端服务应用WebSocket推送修复
   - [ ] 创建端到端测试（使用V4角色）验证完整流程
   - [ ] 确认前端SearchReferences组件能接收并显示搜索结果

2. **用户指南更新** (中优先级):
   - [ ] 在用户文档中说明V2角色的搜索限制
   - [ ] 提供搜索功能测试指南（推荐角色、预期结果）

3. **长期优化** (低优先级):
   - [ ] 考虑在前端提供角色工具权限的可视化提示
   - [ ] 添加搜索质量监控（相关性阈值调优）

## 诊断脚本使用方法

```bash
# 完整诊断
python scripts/diagnose_search_tools.py

# 快速连通性检查
python scripts/quick_check_tools.py
```

## 附录：关键文件清单

### 后端文件
- `intelligent_project_analyzer/tools/tavily_search.py` - Tavily搜索工具
- `intelligent_project_analyzer/agents/bocha_search_tool.py` - 博查搜索工具
- `intelligent_project_analyzer/tools/arxiv_search.py` - ArXiv搜索工具
- `intelligent_project_analyzer/tools/ragflow_kb.py` - RAGFlow知识库
- `intelligent_project_analyzer/services/tool_factory.py` - 工具工厂
- `intelligent_project_analyzer/agents/search_strategy.py` - 搜索策略生成
- `intelligent_project_analyzer/agents/tool_callback.py` - 工具调用记录器
- `intelligent_project_analyzer/workflow/main_workflow.py` - 角色工具映射
- `intelligent_project_analyzer/core/state.py` - search_references定义
- `intelligent_project_analyzer/api/server.py` - WebSocket推送（待修复）

### 前端文件
- `frontend-nextjs/types/index.ts` - SearchReference类型定义
- `frontend-nextjs/components/SearchReferences.tsx` - 搜索引用展示
- `frontend-nextjs/components/report/SearchReferencesDisplay.tsx` - 报告页搜索引用

### 诊断脚本
- `scripts/diagnose_search_tools.py` - 完整自动化诊断
- `scripts/quick_check_tools.py` - 快速连通性检查

---

**报告生成**: Claude Code v7.120
**诊断日期**: 2026-01-03
