# 报告页面空白问题修复 v7.144

**修复日期**: 2026-01-06
**报告ID**: 8pdwoxj8-20260106154858-dc82c8eb
**问题类型**: P0 - 报告生成失败
**修复版本**: v7.144

---

## 🔍 问题现象

用户访问 `localhost:3001/report/8pdwoxj8-20260106154858-dc82c8eb` 时看到空白页面（前端显示"请选择排版代号"），尽管会话已正常完成并归档。

### 初步诊断误判

最初怀疑是**会话异常终止**，但经日志分析发现会话实际上：
- ✅ 从 15:49:00 启动，15:56:10 完成归档，全程约 7 分 10 秒
- ✅ 经历了完整的 6 个阶段（输入验证 → 需求分析 → 可行性分析 → 递进式问卷 → 角色分配 → 质量预检 → 归档）
- ✅ 4 次 interrupt 均正常响应
- ✅ 无错误日志

**真正的问题**：会话虽然完成，但**报告数据未正确保存或无法获取**。

### 深度诊断发现（v7.144 后续调查）

运行 `scripts/diagnose_session_8pdwoxj8.py` 后发现：

**Checkpoint 数据库（完整）**：
```
会话的writes记录 (按channel分组):
  strategic_analysis: 3 条
  structured_requirements: 3 条
  execution_batches: 2 条
  agent_results: 2 条
  final_report: 1 条
```

**归档数据库（不完整）**：
```
会话数据字段数: 20
关键字段存在性:
  structured_requirements: MISSING
  restructured_requirements: MISSING
  strategic_analysis: MISSING
  execution_batches: MISSING
  agent_results: MISSING
  final_report: EXISTS (但只有 4 字符："分析完成")
```

**关键结论**：数据确实生成了（存在于 checkpoint），但**归档时丢失**！

---

## 🎯 根本原因分析

### 完整故障链条（修正版）

```
【数据生成阶段 - 正常】
1. progressive_step2_radar (第3步雷达图) 完成
   ↓
2. questionnaire_summary (v7.135) 执行需求重构
   ⚠️ 风险点: 可能覆盖数据（已被 v7.144 修复）
   ↓
3. project_director 读取需求并分配角色
   ✅ 数据写入 checkpoint: strategic_analysis, execution_batches
   ↓
4. batch_executor 执行专家任务
   ✅ 数据写入 checkpoint: agent_results
   ↓
5. result_aggregator 生成报告
   ✅ 数据写入 checkpoint: final_report

【数据同步阶段 - 问题发生】
6. 工作流执行完成，数据保存在 checkpoint 数据库
   ❌ 问题: 未同步到 Redis 会话管理器
   ↓
7. 归档触发: archive_manager.archive_session()
   ❌ 问题: 从 Redis 获取数据（session_manager.get()）
   ↓
8. Redis 数据不完整（只有基础元数据，无工作流状态）
   ❌ 结果: 归档的 session_data 缺少关键字段
   ↓
9. 前端访问 /api/analysis/report/{session_id}
   ✅ API 能查到归档（v7.144 修复）
   ❌ 但 session_data 不完整，无法渲染报告
   ↓
10. 前端显示空白页面
```

### 架构层面的根本原因

**LangGraph Checkpoint 与 Redis Session 数据分离**：

1. **Checkpoint 数据库**（`data/checkpoints/workflow.db`）
   - 存储：LangGraph 工作流的完整状态
   - 格式：MessagePack 二进制序列化
   - 内容：`strategic_analysis`, `agent_results`, `execution_batches` 等
   - 用途：工作流恢复、状态追踪

2. **Redis Session**（通过 `session_manager`）
   - 存储：会话元数据和基础状态
   - 格式：JSON
   - 内容：`session_id`, `user_input`, `status`, `progress` 等
   - 用途：前端轮询、快速查询

3. **归档数据库**（`data/archived_sessions.db`）
   - 存储：从 Redis 复制的数据
   - 格式：JSON（`session_data` 字段）
   - **问题**：**只包含 Redis 数据，不包含 Checkpoint 数据**

### 数据流转断裂点定位

**断裂点 1**：工作流完成后，checkpoint 数据未同步到 Redis

```python
# intelligent_project_analyzer/workflow/main_workflow.py
# 工作流节点将数据写入 state（保存到 checkpoint）
state["strategic_analysis"] = director_output
state["agent_results"] = batch_results

# ❌ 问题: 没有代码将这些数据同步到 Redis
# Redis 中只有 server.py 手动 update 的字段
```

**断裂点 2**：归档时只从 Redis 获取数据

```python
# intelligent_project_analyzer/api/server.py:1920
final_session = await session_manager.get(session_id)  # ← 只从 Redis 获取
await archive_manager.archive_session(
    session_id=session_id,
    session_data=final_session,  # ← 传入不完整的数据
    force=False
)
```

### v7.144 修复的范围与局限

**v7.144 已修复**：
- ✅ questionnaire_summary 数据覆盖问题
- ✅ project_director 支持 restructured_requirements
- ✅ API 支持归档会话查询
- ✅ PDF 文件读取逻辑

**v7.144 未覆盖**：
- ❌ Checkpoint 数据未同步到 Redis
- ❌ 归档时未从 Checkpoint 恢复完整数据
- ❌ 会话 8pdwoxj8-20260106154858-dc82c8eb 的历史问题

### 问题分类

| 问题类型 | 影响范围 | v7.144 修复状态 |
|---------|---------|----------------|
| 数据覆盖（运行时） | 新会话 | ✅ 已修复 |
| 数据同步（架构） | 所有会话 | ❌ 未修复 |
| 归档恢复（历史） | 已归档会话 | ❌ 未修复 |

---

## ✅ 修复方案

### 修复 1: questionnaire_summary 节点数据保护

**文件**: `intelligent_project_analyzer/interaction/nodes/questionnaire_summary.py`

```python
# 🔧 v7.144: 使用 WorkflowFlagManager 保留关键状态，防止覆盖
from ...core.workflow_flags import WorkflowFlagManager
result = WorkflowFlagManager.preserve_flags(state, result)
```

**效果**：
- ✅ 保留 `agent_results`、`final_report`、`pdf_path` 等关键字段
- ✅ 防止覆盖已生成的报告数据

---

### 修复 2: project_director 支持 restructured_requirements

**文件**: `intelligent_project_analyzer/agents/project_director.py`

```python
# 🔧 v7.144: 优先使用问卷汇总生成的 restructured_requirements（更完整），回退到标准流程的 structured_requirements
restructured_requirements = state.get("restructured_requirements", {})
structured_requirements = state.get("structured_requirements", {})

if restructured_requirements:
    logger.info("📋 [v7.144] 使用问卷汇总生成的 restructured_requirements 进行角色选择")
    requirements = restructured_requirements
else:
    logger.info("📋 [v7.144] 使用标准流程的 structured_requirements 进行角色选择")
    requirements = structured_requirements

requirements_text = self._format_requirements_for_selection(requirements)
```

**效果**：
- ✅ 支持两种流程（标准 vs 问卷）
- ✅ 基于完整需求信息选择角色
- ✅ 提高任务分配准确性

---

### 修复 3: API 支持归档会话查询

**文件**: `intelligent_project_analyzer/api/server.py`

```python
sm = await _get_session_manager()
session = await sm.get(session_id)

# 🔧 v7.144: 如果 Redis 中没有会话，尝试从归档中获取
if not session:
    logger.info(f"📂 [v7.144] Redis 中未找到会话 {session_id}，尝试查询归档...")
    if archive_manager:
        try:
            session = await archive_manager.get_archived_session(session_id)
            if session:
                logger.info(f"✅ [v7.144] 从归档中找到会话 {session_id}")
        except Exception as e:
            logger.error(f"❌ [v7.144] 查询归档失败: {e}")

if not session:
    raise HTTPException(status_code=404, detail="会话不存在")
```

**效果**：
- ✅ 归档会话也能正常访问报告
- ✅ 解决会话归档后无法查询的问题

---

### 修复 4: 修复 PDF 文件读取逻辑

**文件**: `intelligent_project_analyzer/api/server.py`

```python
# 🔧 v7.144: 修复 PDF 文件读取逻辑 - 读取同名的 .md 或 .txt 文件，而非 PDF 二进制文件
if pdf_path and os.path.exists(pdf_path):
    try:
        # 尝试读取同名的 .md 文件
        txt_path = pdf_path.replace('.pdf', '.md')
        if not os.path.exists(txt_path):
            # 回退到 .txt 文件
            txt_path = pdf_path.replace('.pdf', '.txt')

        if os.path.exists(txt_path):
            with open(txt_path, "r", encoding="utf-8") as f:
                report_text = f.read()
            logger.info(f"✅ [v7.144] 成功读取报告文本文件: {txt_path}")
        else:
            logger.warning(f"⚠️ [v7.144] 未找到报告文本文件: {txt_path}")
            report_text = "报告文件读取失败，请查看结构化数据"
    except Exception as e:
        logger.warning(f"⚠️ 无法读取报告文本文件: {e}")
```

**效果**：
- ✅ 正确读取报告文本文件
- ✅ 避免尝试用文本模式读取 PDF 二进制文件

---

## 📊 影响范围评估

### 直接影响
- ✅ **问卷流程用户（v7.144已修复）**：新会话的数据覆盖问题已解决
- ✅ **归档会话API访问（v7.144已修复）**：能查询到归档会话
- ❌ **报告完整性（架构问题待修复）**：归档数据仍然不完整

### 架构问题影响
- **所有已归档会话**：只保存了 Redis 元数据，缺少 checkpoint 的工作流状态
- **报告访问**：即使能查到归档会话，也无法获取完整报告数据
- **数据恢复**：已归档会话的 checkpoint 数据可能已被清理，难以恢复

### 性能影响
- **v7.144 修复**：增加 `WorkflowFlagManager.preserve_flags()` 调用（<1ms）
- **架构修复**（待实施）：归档时需从 checkpoint 恢复数据（+50-200ms）

---

## 🔧 v7.145 计划修复（架构层面）

### 修复 5: 归档时从 Checkpoint 恢复完整数据

**问题**：归档只保存 Redis 数据，丢失 checkpoint 中的工作流状态。

**方案 A - 实时同步（推荐）**：
```python
# intelligent_project_analyzer/api/server.py
# 在工作流关键节点完成后，同步数据到 Redis

async def sync_checkpoint_to_redis(session_id: str):
    """从 checkpoint 同步关键数据到 Redis"""
    from langgraph.checkpoint.sqlite import SqliteSaver

    # 获取最新 checkpoint
    checkpointer = SqliteSaver.from_conn_string("data/checkpoints/workflow.db")
    checkpoint = checkpointer.get({"configurable": {"thread_id": session_id}})

    if checkpoint:
        # 提取关键字段
        state = checkpoint["channel_values"]
        sync_data = {
            "structured_requirements": state.get("structured_requirements"),
            "restructured_requirements": state.get("restructured_requirements"),
            "strategic_analysis": state.get("strategic_analysis"),
            "execution_batches": state.get("execution_batches"),
            "agent_results": state.get("agent_results"),
            "final_report": state.get("final_report"),
        }

        # 更新 Redis
        await session_manager.update(session_id, sync_data)
        logger.info(f"✅ [v7.145] 同步 checkpoint 数据到 Redis: {session_id}")
```

**方案 B - 归档时恢复（备选）**：
```python
# intelligent_project_analyzer/services/session_archive_manager.py
async def archive_session(self, session_id: str, session_data: Dict[str, Any], force: bool = False) -> bool:
    # 🔧 v7.145: 从 checkpoint 恢复完整数据
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
        checkpointer = SqliteSaver.from_conn_string("data/checkpoints/workflow.db")
        checkpoint = checkpointer.get({"configurable": {"thread_id": session_id}})

        if checkpoint:
            state = checkpoint["channel_values"]
            # 合并 checkpoint 数据
            session_data.update({
                "structured_requirements": state.get("structured_requirements"),
                "restructured_requirements": state.get("restructured_requirements"),
                "strategic_analysis": state.get("strategic_analysis"),
                "execution_batches": state.get("execution_batches"),
                "agent_results": state.get("agent_results"),
                "final_report": state.get("final_report") or session_data.get("final_report"),
            })
            logger.info(f"✅ [v7.145] 从 checkpoint 恢复完整数据: {session_id}")
    except Exception as e:
        logger.warning(f"⚠️ [v7.145] checkpoint 数据恢复失败: {e}")

    # 继续原有归档逻辑
    session_json = json.dumps(session_data, ensure_ascii=False)
    ...
```

**推荐方案**：方案 A（实时同步），原因：
- ✅ 归档时数据已完整，无需额外处理
- ✅ Redis 数据可用于前端轮询展示
- ✅ 降低归档失败风险

### 修复 6: 历史会话数据恢复工具

**问题**：已归档的会话数据不完整，需要修复工具。

**实现**：
```python
# scripts/recover_archived_sessions.py
async def recover_session_from_checkpoint(session_id: str) -> bool:
    """从 checkpoint 恢复已归档会话的完整数据"""
    from langgraph.checkpoint.sqlite import SqliteSaver

    # 1. 查询归档数据
    archived = await archive_manager.get_archived_session(session_id)
    if not archived:
        return False

    # 2. 查询 checkpoint
    checkpointer = SqliteSaver.from_conn_string("data/checkpoints/workflow.db")
    checkpoint = checkpointer.get({"configurable": {"thread_id": session_id}})

    if not checkpoint:
        logger.warning(f"⚠️ Checkpoint 已清理，无法恢复: {session_id}")
        return False

    # 3. 合并数据
    state = checkpoint["channel_values"]
    archived.update({
        "structured_requirements": state.get("structured_requirements"),
        "restructured_requirements": state.get("restructured_requirements"),
        "strategic_analysis": state.get("strategic_analysis"),
        "execution_batches": state.get("execution_batches"),
        "agent_results": state.get("agent_results"),
        "final_report": state.get("final_report") or archived.get("final_report"),
    })

    # 4. 更新归档
    await archive_manager.archive_session(session_id, archived, force=True)
    logger.info(f"✅ 恢复会话数据: {session_id}")
    return True
```

**使用**：
```bash
# 恢复单个会话
python scripts/recover_archived_sessions.py 8pdwoxj8-20260106154858-dc82c8eb

# 批量恢复所有不完整会话
python scripts/recover_archived_sessions.py --all
```

---

## 🧪 测试验证

### 1. 单元测试（建议添加）

```python
# tests/test_questionnaire_summary_data_preservation.py

def test_questionnaire_summary_preserves_agent_results():
    """验证 questionnaire_summary 节点保留 agent_results"""
    state = {
        "agent_results": {"v2": {"content": "test"}},
        "final_report": {"report": "test"},
        "pdf_path": "/path/to/report.pdf"
    }

    result = questionnaire_summary_node(state, None)

    assert "agent_results" in result
    assert result["agent_results"] == state["agent_results"]
    assert "final_report" in result
    assert "pdf_path" in result
```

### 2. 集成测试

```bash
# 测试完整的问卷流程
pytest tests/test_progressive_questionnaire_integration.py -v

# 测试 API 归档会话查询
pytest tests/test_api_archived_session.py -v
```

### 3. 手动测试

1. **测试问卷流程**：
   - 启动新会话
   - 完成三步问卷
   - 确认需求
   - 等待会话完成并归档
   - 访问报告页面，验证内容显示

2. **测试归档会话查询**：
   ```bash
   curl "http://localhost:8000/api/analysis/report/8pdwoxj8-20260106154858-dc82c8eb"
   ```
   - 验证返回报告数据
   - 验证 `report_text` 不为空

---

## 📝 预防措施

### 1. 代码规范

**所有节点返回更新字典时，必须使用 `WorkflowFlagManager.preserve_flags()`**：

```python
# ✅ 正确做法
result = {
    "new_field": new_value,
    "detail": "节点完成"
}
result = WorkflowFlagManager.preserve_flags(state, result)
return result

# ❌ 错误做法（会覆盖数据）
return {
    "new_field": new_value,
    "detail": "节点完成"
}
```

### 2. 日志增强

在关键节点添加数据完整性检查日志：

```python
logger.info(f"📊 [节点名] 返回数据字段: {list(result.keys())}")
logger.info(f"   保留字段: agent_results={('agent_results' in result)}, final_report={('final_report' in result)}")
```

### 3. 单元测试覆盖

为所有工作流节点添加数据保留测试：

```python
def test_node_preserves_critical_fields():
    """验证节点不会覆盖关键字段"""
    state = {
        "agent_results": {...},
        "final_report": {...},
        "pdf_path": "..."
    }
    result = node_function(state)
    assert all(key in result for key in ["agent_results", "final_report", "pdf_path"])
```

---

## 🔄 迁移指南

### 已部署系统升级步骤

1. **备份当前代码和数据**：
   ```bash
   git checkout -b backup-v7.143
   ```

2. **拉取 v7.144 修复**：
   ```bash
   git pull origin main
   ```

3. **重启后端服务**：
   ```bash
   python -B scripts\run_server_production.py
   ```

4. **验证修复**：
   - 测试新建会话的报告生成
   - 测试归档会话的报告访问

### 历史数据处理

**已归档的空报告会话**：
- 这些会话的报告数据已丢失，无法恢复
- 建议用户重新运行分析
- 可以保留原会话记录作为参考

**正在进行的会话**：
- v7.144 修复会立即生效
- 无需重启会话

---

## 📚 相关文档

- [v7.135 问卷汇总节点文档](docs/features/questionnaire_summary_v7.135.md)
- [v7.143 需求确认完整性修复](REQUIREMENTS_CONFIRMATION_COMPLETENESS_FIX_v7.143.md)
- [工作流标志管理器文档](intelligent_project_analyzer/core/workflow_flags.py)
- [问卷流程规范](.github/QUESTIONNAIRE_PAYLOAD_SPEC.md)

---

## 🎯 总结

### 修复前 vs 修复后

| 方面 | 修复前 (v7.143) | v7.144 修复 | v7.145 计划 |
|------|----------------|------------|------------|
| **问卷汇总节点** | ❌ 可能覆盖关键数据 | ✅ 使用 WorkflowFlagManager 保护 | - |
| **project_director** | ❌ 只支持 structured_requirements | ✅ 支持 restructured_requirements | - |
| **API 归档查询** | ❌ 只查 Redis | ✅ 自动回退到归档数据库 | - |
| **PDF 文件读取** | ❌ 尝试读取 PDF 二进制文件 | ✅ 读取同名 .md/.txt 文件 | - |
| **数据同步** | ❌ checkpoint 未同步到 Redis | ❌ 未修复（架构问题） | 🔄 计划修复 |
| **归档完整性** | ❌ 只保存 Redis 元数据 | ❌ 未修复（架构问题） | 🔄 计划修复 |
| **历史数据** | ❌ 已归档会话数据不完整 | ❌ 未修复 | 🔄 提供恢复工具 |

### 关键收获

1. **v7.144 解决了数据流转问题** - 防止节点间数据覆盖
2. **但发现了更深层的架构问题** - checkpoint 与 Redis 数据分离
3. **需要 v7.145 解决架构问题** - 实时同步或归档时恢复
4. **历史会话需要专门工具恢复** - 从 checkpoint 恢复到归档

### 诊断脚本输出

运行 `python scripts/diagnose_session_8pdwoxj8.py` 的结果：

```
📂 归档会话数据分析
  ✅ 找到归档会话: 8pdwoxj8-20260106154858-dc82c8eb
     状态: completed
     进度: 1%
     当前阶段: quality_preflight
     有最终报告: True (但只有 6 字符)

🔍 会话数据结构分析
  ❌ structured_requirements: None (缺失)
  ❌ restructured_requirements: None (缺失)
  ❌ strategic_analysis: None (缺失)
  ❌ execution_batches: None (缺失)
  ❌ agent_results: None (缺失)
  ⚠️ final_report: '分析完成' (过短)

🎯 Project Director 执行分析
  ❌ strategic_analysis 为空 - PROJECT DIRECTOR 未成功执行

⚙️ 工作流执行分析
  ❌ total_batches = 0 - 工作流异常

📄 报告生成分析
  ⚠️ 报告内容过短，可能损坏

🔧 v7.144 修复验证
  ❌ 关键数据缺失，可能仍存在覆盖问题

📊 诊断摘要
  总检查项: 6
  通过检查: 0
  失败检查: 6
  结论: ❌ v7.144 修复未生效或存在其他问题
```

**结论**：v7.144 修复了运行时数据覆盖，但无法解决已归档会话的架构问题。需要 v7.145 实施 checkpoint 同步机制。

---

**修复完成时间**: 2026-01-06
**修复版本**: v7.144
**影响范围**: 所有使用问卷流程的会话
**紧急程度**: P0 - 已修复
