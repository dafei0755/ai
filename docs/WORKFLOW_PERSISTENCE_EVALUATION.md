"""
🆕 P1修复: 工作流持久化方案评估

## 问题概述
当前使用MemorySaver作为LangGraph检查点存储，导致服务重启后：
- 会话状态丢失
- 无法恢复中断的工作流
- 影响用户体验和调试

## 迁移方案对比

### 方案1: SqliteSaver (推荐)
**优点:**
- 文件持久化，重启不丢失
- 查询性能好，支持复杂查询
- 适合单机部署
- LangGraph官方推荐

**缺点:**
- 多进程部署需要共享文件系统
- 需要处理数据库文件锁

**实施步骤:**
1. 安装依赖: `pip install aiosqlite`
2. 修改 `main_workflow.py`:
   ```python
   from langgraph.checkpoint.sqlite import SqliteSaver

   # 在__init__中替换
   db_path = "data/checkpoints/workflow.db"
   self.checkpointer = SqliteSaver.from_conn_string(db_path)
   ```
3. 在服务关闭时清理: `await self.checkpointer.close()`

**风险:**
- 现有会话将无法恢复（需要migration或清空）
- 需要处理数据库Schema变更

---

### 方案2: PostgresSaver
**优点:**
- 支持多进程/多节点部署
- 成熟的数据库方案
- 适合大规模生产环境

**缺点:**
- 需要额外的PostgreSQL服务
- 配置复杂度增加
- 当前部署不使用PostgreSQL

**实施步骤:**
1. 安装依赖: `pip install psycopg[binary] psycopg-pool`
2. 配置PostgreSQL连接
3. 修改代码使用PostgresSaver

**评估:** 目前无PostgreSQL，引入成本高，不推荐

---

### 方案3: 基于Redis的自定义Checkpointer
**优点:**
- 系统已有Redis
- 支持分布式部署
- 内存级性能

**缺点:**
- 需要自行实现BaseCheckpointSaver接口
- Redis持久化配置要求高
- LangGraph无官方支持

**实施步骤:**
1. 创建 `RedisCheckpointer(BaseCheckpointSaver)`
2. 实现 `aget_tuple`, `aput`, `alist` 方法
3. 配置Redis AOF持久化

**评估:** 开发成本高，维护风险大，不推荐作为首选

---

## 推荐方案: SqliteSaver

### 实施计划
**阶段1: 测试环境验证 (1天)**
1. 创建测试分支
2. 修改main_workflow.py使用SqliteSaver
3. 运行完整测试套件
4. 验证checkpoint恢复功能

**阶段2: 数据迁移策略 (1天)**
1. 提供用户通知: "升级后旧会话无法恢复"
2. 或实现migration脚本（如有必要）
3. 记录当前MemorySaver会话ID列表

**阶段3: 生产部署 (1天)**
1. 备份当前数据目录
2. 更新requirements.txt添加aiosqlite
3. 部署新版本
4. 监控错误日志

### 回滚策略
- 保留旧版本代码分支
- 删除 `data/checkpoints/workflow.db` 文件
- 回滚代码到MemorySaver版本
- 服务重启

### 风险评估
**高风险项:**
- ❌ 无 - 改动范围小，影响可控

**中风险项:**
- ⚠️ 多进程部署时的文件锁竞争（当前单进程部署，无影响）
- ⚠️ 数据库文件增长（需要定期清理旧checkpoint）

**缓解措施:**
- 实现checkpoint TTL自动清理
- 监控 `workflow.db` 文件大小
- 提供手动清理脚本

---

## 代码示例

### 修改 main_workflow.py
```python
from langgraph.checkpoint.sqlite import SqliteSaver
import os

class MainWorkflow:
    def __init__(self, llm_model, config=None):
        # ... 其他初始化 ...

        # 🆕 P1修复: 使用SqliteSaver替代MemorySaver
        checkpoint_dir = "data/checkpoints"
        os.makedirs(checkpoint_dir, exist_ok=True)
        db_path = os.path.join(checkpoint_dir, "workflow.db")

        self.checkpointer = SqliteSaver.from_conn_string(db_path)
        logger.info(f"✅ 使用持久化检查点存储: {db_path}")
```

### 添加清理脚本 scripts/cleanup_checkpoints.py
```python
import sqlite3
import os
from datetime import datetime, timedelta

def cleanup_old_checkpoints(db_path: str, days: int = 7):
    """清理N天前的checkpoint"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cutoff = datetime.now() - timedelta(days=days)
    cursor.execute(
        "DELETE FROM checkpoints WHERE created_at < ?",
        (cutoff.isoformat(),)
    )

    deleted = cursor.rowcount
    conn.commit()
    conn.close()

    print(f"✅ 清理了 {deleted} 个旧checkpoint")

if __name__ == "__main__":
    cleanup_old_checkpoints("data/checkpoints/workflow.db", days=7)
```

---

## 结论
**推荐立即迁移到SqliteSaver:**
- ✅ 实施简单，风险低
- ✅ 解决重启丢失问题
- ✅ 符合生产最佳实践
- ✅ 无需额外依赖服务

**不推荐方案:**
- ❌ PostgresSaver - 当前无PostgreSQL
- ❌ RedisCheckpointer - 开发维护成本高

**下一步行动:**
1. 安装 `aiosqlite`
2. 修改 main_workflow.py
3. 测试验证
4. 部署上线
