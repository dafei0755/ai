# 会话 8pdwoxj8 报告空白问题完整诊断报告

**会话ID**: 8pdwoxj8-20260106154858-dc82c8eb
**诊断日期**: 2026-01-06
**问题等级**: P0 - 报告生成失败（架构层面）

---

## 执行摘要

通过诊断脚本 `scripts/diagnose_session_8pdwoxj8.py` 和数据库分析，确认了报告空白的根本原因：

**❌ 问题不是数据生成失败，而是数据归档不完整**

- ✅ **Checkpoint 数据库有完整数据**（strategic_analysis、agent_results 等）
- ❌ **归档数据库缺少关键字段**（只保存了 Redis 元数据）
- ❌ **Redis 与 Checkpoint 数据未同步**（架构设计问题）

---

## 诊断过程

### 1. 初步调查（用户报告）

**现象**：访问 `localhost:3001/report/8pdwoxj8-20260106154858-dc82c8eb` 显示空白页面

**初步假设**：会话异常终止

**验证结果**：❌ 假设错误
- 会话正常完成（15:48:58 - 15:56:10，约7分钟）
- 经历完整工作流阶段
- 无错误日志

### 2. 数据库分析

#### Checkpoint 数据库检查

```bash
python check_session_data.py
```

**结果**：
```
会话的writes记录 (按channel分组):
  strategic_analysis: 3 条
  structured_requirements: 3 条
  execution_batches: 2 条
  agent_results: 2 条
  final_report: 1 条
  total_batches: 2 条
```

**结论**：✅ **工作流数据确实生成了**

#### 归档数据库检查

```bash
python scripts/diagnose_session_8pdwoxj8.py
```

**结果**：
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

**结论**：❌ **归档数据不完整**

### 3. 代码追踪

#### 归档流程分析

**归档触发位置**：`intelligent_project_analyzer/api/server.py:1920`

```python
# 获取完整会话数据
final_session = await session_manager.get(session_id)  # ← 只从 Redis 获取
if final_session:
    await archive_manager.archive_session(
        session_id=session_id,
        session_data=final_session,  # ← 传入不完整的数据
        force=False
    )
```

**归档保存逻辑**：`intelligent_project_analyzer/services/session_archive_manager.py:210`

```python
# 序列化完整会话数据
session_json = json.dumps(session_data, ensure_ascii=False)
# ↑ 直接保存传入的 session_data，未从 checkpoint 恢复
```

**问题定位**：
1. `session_manager.get()` 只返回 Redis 中的数据
2. Redis 中没有 checkpoint 的工作流状态（strategic_analysis、agent_results 等）
3. 归档时直接保存 Redis 数据，导致关键字段缺失

---

## 根本原因

### 架构设计问题：Checkpoint 与 Redis 数据分离

```
┌─────────────────────────────────────────────────────────────┐
│                    工作流执行层                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  LangGraph Workflow                                  │    │
│  │  - 节点执行                                          │    │
│  │  - 状态更新                                          │    │
│  └─────────────────┬───────────────────────────────────┘    │
│                    │ 写入                                    │
│                    ▼                                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Checkpoint 数据库 (workflow.db)                     │    │
│  │  - strategic_analysis ✅                             │    │
│  │  - agent_results ✅                                  │    │
│  │  - execution_batches ✅                              │    │
│  │  - MessagePack 二进制格式                            │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘

            ❌ 未同步                ❌ 未同步

┌─────────────────────────────────────────────────────────────┐
│                    会话管理层                                │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Redis Session Manager                               │    │
│  │  - session_id ✅                                     │    │
│  │  - user_input ✅                                     │    │
│  │  - status ✅                                         │    │
│  │  - progress ✅                                       │    │
│  │  - strategic_analysis ❌                             │    │
│  │  - agent_results ❌                                  │    │
│  │  - JSON 格式                                         │    │
│  └─────────────────┬───────────────────────────────────┘    │
│                    │ 归档时读取                              │
│                    ▼                                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  归档数据库 (archived_sessions.db)                   │    │
│  │  - session_data: 不完整（只有 Redis 数据）❌         │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### 数据流转断裂点

**断裂点 1**：工作流 → Redis

```python
# intelligent_project_analyzer/workflow/main_workflow.py
# 工作流节点将数据写入 state
state["strategic_analysis"] = director_output  # ← 写入 checkpoint
state["agent_results"] = batch_results          # ← 写入 checkpoint

# ❌ 没有代码将这些数据同步到 Redis
```

**断裂点 2**：Redis → 归档

```python
# intelligent_project_analyzer/api/server.py
final_session = await session_manager.get(session_id)  # ← 只从 Redis 获取
await archive_manager.archive_session(
    session_id=session_id,
    session_data=final_session  # ← 不完整的数据
)
```

---

## v7.144 修复回顾

### 已实施的修复

v7.144 修复了**运行时数据覆盖**问题，但未触及架构层面：

1. ✅ questionnaire_summary 使用 WorkflowFlagManager 保护数据
2. ✅ project_director 支持 restructured_requirements
3. ✅ API 支持归档会话查询
4. ✅ PDF 文件读取逻辑修正

### v7.144 的局限性

**修复范围**：节点间数据流转（运行时）
**未覆盖**：Checkpoint ↔ Redis 同步（架构层面）

**影响**：
- ✅ 新会话的数据覆盖问题已解决
- ❌ 归档数据仍然不完整
- ❌ 已归档会话无法获取完整报告

---

## v7.145 修复方案

### 方案 A：实时同步（推荐）

**优点**：
- ✅ 归档时数据已完整
- ✅ Redis 可用于前端轮询
- ✅ 降低归档失败风险

**实现**：在工作流关键节点完成后同步

```python
# intelligent_project_analyzer/api/server.py

async def sync_checkpoint_to_redis(session_id: str):
    """从 checkpoint 同步关键数据到 Redis"""
    from langgraph.checkpoint.sqlite import SqliteSaver

    checkpointer = SqliteSaver.from_conn_string("data/checkpoints/workflow.db")
    checkpoint = checkpointer.get({"configurable": {"thread_id": session_id}})

    if checkpoint:
        state = checkpoint["channel_values"]
        sync_data = {
            "structured_requirements": state.get("structured_requirements"),
            "restructured_requirements": state.get("restructured_requirements"),
            "strategic_analysis": state.get("strategic_analysis"),
            "execution_batches": state.get("execution_batches"),
            "agent_results": state.get("agent_results"),
            "final_report": state.get("final_report"),
        }
        await session_manager.update(session_id, sync_data)
```

**调用时机**：
- project_director 完成后
- batch_executor 完成后
- result_aggregator 完成后
- 归档前（保险）

### 方案 B：归档时恢复（备选）

**优点**：
- ✅ 无需修改工作流代码
- ✅ 集中处理归档逻辑

**缺点**：
- ❌ 归档时额外开销（+50-200ms）
- ❌ Redis 数据仍不完整

**实现**：在归档管理器中从 checkpoint 恢复

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
            session_data.update({
                "structured_requirements": state.get("structured_requirements"),
                "restructured_requirements": state.get("restructured_requirements"),
                "strategic_analysis": state.get("strategic_analysis"),
                "execution_batches": state.get("execution_batches"),
                "agent_results": state.get("agent_results"),
                "final_report": state.get("final_report") or session_data.get("final_report"),
            })
            logger.info(f"✅ [v7.145] 从 checkpoint 恢复完整数据")
    except Exception as e:
        logger.warning(f"⚠️ checkpoint 恢复失败: {e}")

    # 继续原有归档逻辑
    ...
```

### 推荐：方案 A

**理由**：
1. Redis 数据完整性对前端轮询重要
2. 避免归档时的额外开销
3. 更符合数据流转的自然方向

---

## 历史数据恢复

### 问题

已归档的会话数据不完整，需要专门工具恢复。

### 恢复工具

**文件**：`scripts/recover_archived_sessions.py`

```python
async def recover_session_from_checkpoint(session_id: str) -> bool:
    """从 checkpoint 恢复已归档会话的完整数据"""
    from langgraph.checkpoint.sqlite import SqliteSaver

    # 1. 查询归档数据
    archived = await archive_manager.get_archived_session(session_id)
    if not archived:
        logger.error(f"归档会话不存在: {session_id}")
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

    # 4. 更新归档（强制覆盖）
    await archive_manager.archive_session(session_id, archived, force=True)
    logger.info(f"✅ 恢复会话数据: {session_id}")
    return True
```

### 使用方法

```bash
# 恢复单个会话
python scripts/recover_archived_sessions.py 8pdwoxj8-20260106154858-dc82c8eb

# 批量恢复所有不完整会话
python scripts/recover_archived_sessions.py --all

# 恢复最近N天的会话
python scripts/recover_archived_sessions.py --days 7
```

### 限制

**⚠️ 只能恢复 checkpoint 未被清理的会话**

Checkpoint 清理策略（当前）：
- 保留最近 100 个 checkpoint
- 或保留最近 7 天的 checkpoint

如果 checkpoint 已被清理，数据无法恢复。

---

## 验证计划

### 1. 单元测试

```python
# tests/test_checkpoint_redis_sync.py

async def test_sync_checkpoint_to_redis():
    """测试 checkpoint 数据同步到 Redis"""
    session_id = "test-session"

    # 模拟工作流执行，写入 checkpoint
    # ...

    # 同步到 Redis
    await sync_checkpoint_to_redis(session_id)

    # 验证 Redis 数据
    session = await session_manager.get(session_id)
    assert "strategic_analysis" in session
    assert "agent_results" in session
    assert session["agent_results"] is not None
```

### 2. 集成测试

```python
# tests/test_archive_completeness.py

async def test_archive_contains_checkpoint_data():
    """测试归档数据包含 checkpoint 内容"""
    # 1. 运行完整工作流
    session_id = await run_workflow("测试需求")

    # 2. 等待归档
    await asyncio.sleep(1)

    # 3. 查询归档数据
    archived = await archive_manager.get_archived_session(session_id)

    # 4. 验证完整性
    assert "strategic_analysis" in archived
    assert "agent_results" in archived
    assert archived["agent_results"] != {}
    assert len(archived["final_report"]) > 100
```

### 3. 手动验证

```bash
# 1. 启动服务
python -B scripts\run_server_production.py

# 2. 创建新会话（完成问卷流程）

# 3. 等待会话完成并归档

# 4. 运行诊断脚本
python scripts/diagnose_session_8pdwoxj8.py <新会话ID>

# 5. 检查诊断结果
# 期望：所有关键字段都存在
```

---

## 实施优先级

| 任务 | 优先级 | 预计时间 | 风险 |
|------|-------|---------|------|
| **P0 - 方案 A 实现** | 🔴 最高 | 4-6 小时 | 低 |
| **P0 - 单元测试** | 🔴 最高 | 2-3 小时 | 低 |
| **P1 - 恢复工具** | 🟡 高 | 3-4 小时 | 中 |
| **P1 - 集成测试** | 🟡 高 | 2-3 小时 | 低 |
| **P2 - 历史会话恢复** | 🟢 中 | 按需执行 | 高（checkpoint 可能已清理）|

### 风险评估

**实施风险**：
- 🟢 **低**：方案 A 仅增加数据同步，不影响工作流逻辑
- 🟡 **中**：恢复工具依赖 checkpoint 存在，可能部分失败

**性能影响**：
- 同步操作：+10-30ms（异步执行，不阻塞工作流）
- 归档操作：无额外开销（数据已在 Redis）

---

## 监控建议

### 1. 归档数据完整性监控

```python
# 定期检查归档会话的数据完整性
async def check_archive_integrity():
    """检查最近归档的会话数据完整性"""
    recent_sessions = await archive_manager.list_archived_sessions(limit=100)

    incomplete_count = 0
    for session in recent_sessions:
        data = json.loads(session["session_data"])
        if not all([
            data.get("strategic_analysis"),
            data.get("agent_results"),
            data.get("final_report")
        ]):
            incomplete_count += 1
            logger.warning(f"归档数据不完整: {session['session_id']}")

    if incomplete_count > 0:
        alert(f"⚠️ 发现 {incomplete_count} 个不完整归档会话")
```

### 2. Checkpoint 清理监控

```python
# 监控 checkpoint 清理，避免数据丢失
async def monitor_checkpoint_cleanup():
    """监控 checkpoint 清理情况"""
    checkpointer = SqliteSaver.from_conn_string("data/checkpoints/workflow.db")

    # 统计 checkpoint 数量
    count = checkpointer.count()

    if count > 1000:
        logger.warning(f"⚠️ Checkpoint 数量过多: {count}，考虑清理")

    # 检查最旧的 checkpoint
    oldest = checkpointer.get_oldest()
    age_days = (datetime.now() - oldest.timestamp).days

    if age_days > 7:
        logger.info(f"最旧 checkpoint: {age_days} 天前，可能影响历史会话恢复")
```

---

## 结论

### 问题本质

**v7.144 修复了运行时数据覆盖，但未解决架构层面的数据同步问题。**

- ✅ 工作流数据生成正常（checkpoint 有完整数据）
- ❌ 数据同步缺失（Redis 和归档不完整）
- ❌ 历史会话无法访问完整报告

### 解决方案

**v7.145 需实施 Checkpoint → Redis 实时同步**：

1. **修复新会话**：在关键节点完成后同步数据到 Redis
2. **恢复历史会话**：提供工具从 checkpoint 恢复归档数据
3. **监控机制**：定期检查归档完整性和 checkpoint 状态

### 影响范围

| 用户类型 | v7.144 状态 | v7.145 后 |
|---------|-----------|----------|
| **新会话用户** | ⚠️ 归档数据不完整 | ✅ 完整归档 |
| **历史会话用户** | ❌ 无法访问报告 | ✅ 工具恢复 |
| **开发团队** | ⚠️ 需手动调查 | ✅ 自动监控 |

---

**诊断完成日期**: 2026-01-06
**下一步行动**: 实施 v7.145 修复方案
**责任人**: 开发团队
**预计完成**: 2026-01-07
