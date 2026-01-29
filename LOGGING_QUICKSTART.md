# 生产级日志系统 - 5分钟快速开始

**基于**: v7.120
**日期**: 2026-01-02

---

## 🚀 立即启用（3步骤）

### 步骤1: 创建环境配置（30秒）

```bash
# 复制配置文件
cp .env.development.example .env

# 或者直接创建
cat > .env << 'EOF'
ENVIRONMENT=development
LOG_LEVEL=DEBUG
STRUCTURED_LOGGING=false
ENABLE_DETAILED_LOGGING=true
SLOW_QUERY_THRESHOLD=2.0
EOF
```

### 步骤2: 在应用启动时初始化（1行代码）

在 `intelligent_project_analyzer/api/server.py` 或主程序入口添加：

```python
from intelligent_project_analyzer.config.logging_config import setup_logging

# 在应用启动最开始调用
setup_logging()

# 之后所有logger.xxx()都会自动使用新配置
```

### 步骤3: 运行并观察日志

```bash
python intelligent_project_analyzer/api/server.py
```

**完成！** 现有的所有日志（v7.119添加的）会自动：
- ✅ 根据环境调整级别
- ✅ 开发环境彩色输出
- ✅ 生产环境存储到文件
- ✅ 自动轮转和压缩

---

## 🎯 不同环境的配置

### 开发环境（推荐配置）

```bash
ENVIRONMENT=development
LOG_LEVEL=DEBUG
STRUCTURED_LOGGING=false          # 人类可读格式
ENABLE_DETAILED_LOGGING=true      # 显示完整payload
SLOW_QUERY_THRESHOLD=2.0
```

**效果**:
- 所有日志输出到控制台（彩色）
- 完整的DEBUG信息
- 不写入文件（不浪费磁盘）

### 生产环境（推荐配置）

```bash
ENVIRONMENT=production
LOG_LEVEL=INFO
STRUCTURED_LOGGING=true           # JSON格式
ENABLE_DETAILED_LOGGING=false     # 不记录敏感payload
LOG_SAMPLE_RATE=0.1              # 10%采样（降低性能影响）
SLOW_QUERY_THRESHOLD=3.0
```

**效果**:
- INFO日志保留7天（自动压缩）
- ERROR日志保留90天
- JSON格式便于ELK/Loki解析
- 性能影响 <5ms

---

## 📊 可选功能（按需启用）

### 功能1: 结构化日志

```python
from intelligent_project_analyzer.utils.logging_utils import StructuredLogger

structured_logger = StructuredLogger("my_component")
structured_logger.log(
    "info",
    "operation_completed",
    "Operation completed successfully",
    duration=1.23,
    result_count=10
)
```

### 功能2: 敏感信息脱敏

```python
from intelligent_project_analyzer.utils.logging_utils import LogDataSanitizer

# 自动脱敏api_key, token, password等
safe_data = LogDataSanitizer.sanitize({"api_key": "sk-1234567890"})
logger.debug(f"Request data: {safe_data}")
```

### 功能3: 性能监控

```python
from intelligent_project_analyzer.utils.monitoring import PerformanceMonitor

with PerformanceMonitor("tavily", "search", query="test") as monitor:
    results = tool.search("test")
    monitor.set_result_count(len(results))
# 自动记录执行时间和成功率
```

### 功能4: 健康检查API

```python
from intelligent_project_analyzer.utils.monitoring import HealthCheck

health = HealthCheck()
status = health.check_health()
# 返回: {"status": "healthy", "statistics": {...}}
```

---

## 🔍 查看日志

### 开发环境

```bash
# 直接看控制台输出（彩色、实时）
python api/server.py
```

### 生产环境

```bash
# 查看INFO日志
tail -f logs/info_$(date +%Y-%m-%d).log

# 查看ERROR日志
tail -f logs/error_$(date +%Y-%m-%d).log

# 分析JSON日志
cat logs/info_*.log | jq '.record.extra | select(.tool=="tavily")'

# 查找慢查询
grep "Slow query" logs/info_*.log
```

---

## ⚠️ 常见问题

### Q1: 生产环境日志太多怎么办？

**A**: 调整采样率

```bash
# 降低到5%采样
export LOG_SAMPLE_RATE=0.05

# 或在.env中
LOG_SAMPLE_RATE=0.05
```

### Q2: 想临时启用DEBUG日志排查问题

**A**: 临时环境变量

```bash
# 临时启用
export LOG_LEVEL=DEBUG
export ENABLE_DETAILED_LOGGING=true

# 运行应用
python api/server.py

# 运行完后取消
unset LOG_LEVEL
unset ENABLE_DETAILED_LOGGING
```

### Q3: 如何集成到现有监控系统？

**A**: 使用JSON日志 + Filebeat/Fluentd

```bash
# 1. 启用JSON格式
export STRUCTURED_LOGGING=true

# 2. 配置Filebeat（示例）
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /path/to/logs/info_*.log
  json.keys_under_root: true

output.elasticsearch:
  hosts: ["localhost:9200"]

# 3. 启动Filebeat
filebeat -e -c filebeat.yml
```

---

## 📚 更多信息

详细文档: [V7.120_PRODUCTION_LOGGING_SYSTEM.md](./V7.120_PRODUCTION_LOGGING_SYSTEM.md)

---

## 📍 日志定位速查表

> **快速回答**：普通思考、深度思考、搜索任务有几份日志？分别在哪？

### 一、日志文件总览

**主日志目录**：`logs/`

| 日志文件 | 用途 | 应用模式 | 轮转策略 | 保留时间 |
|---------|------|---------|---------|----------|
| **server.log** | 服务器主日志 | **所有模式共享** | 10 MB | 10天 |
| **errors.log** | 仅错误日志 | 所有模式 | 5 MB | 30天 |
| **auth.log** | 认证相关 | SSO/Token | 5 MB | 7天 |
| **tool_calls.jsonl** | 工具调用记录 | **搜索任务专用** | 100 MB | 90天 |
| **alerts.log** | 告警监控 | 系统级 | - | - |
| **performance_metrics.jsonl** | API性能指标 | 所有模式 | - | - |

**数据库持久化**：
- `data/archived_sessions.db` - 会话归档（表：`archived_sessions`, `archived_search_sessions`）
- `data/checkpoints/workflow.db` - LangGraph工作流检查点

---

### 二、不同模式的日志区分

#### 1️⃣ **普通思考模式**

**日志输出位置**：
- 主日志：`logs/server.log`
- 错误日志：`logs/errors.log`
- 工具调用：`logs/tool_calls.jsonl`（如使用搜索）

**日志标识特征**：
```log
2026-01-10 | INFO | thinking_mode: normal
2026-01-10 | INFO | 📋 问卷生成开始...
2026-01-10 | INFO | 🎯 专家角色选择完成
```

**如何过滤**：
```powershell
# 搜索普通思考模式日志
Get-Content logs\server.log | Select-String "thinking_mode: normal|普通思考"
```

---

#### 2️⃣ **深度思考模式**

**日志输出位置**：
- 主日志：`logs/server.log`（与普通模式共享）
- 错误日志：`logs/errors.log`
- 工具调用：`logs/tool_calls.jsonl`

**日志标识特征**：
```log
2026-01-10 | INFO | 🧠 启用深度思考模式：每个专家生成独立概念图
2026-01-10 | INFO | thinking_mode: deep
2026-01-10 | INFO | deep_thinking: true
```

**如何过滤**：
```powershell
# 搜索深度思考模式日志
Get-Content logs\server.log | Select-String "深度思考|deep_thinking|🧠"

# 查看深度思考的概念图生成记录
Get-Content logs\server.log | Select-String "独立概念图|concept_image.*deep"
```

---

#### 3️⃣ **搜索任务**

**日志输出位置**：
- 主日志：`logs/server.log`
- 搜索工具调用：`logs/tool_calls.jsonl` **（重要）**
- 性能指标：`logs/performance_metrics.jsonl`
- 数据库：`data/archived_sessions.db` 表 `archived_search_sessions`

**日志标识特征**：
```log
# server.log
2026-01-10 | INFO | 🔍 搜索工具：tavily_search
2026-01-10 | INFO | search_query: "现代简约风格设计"

# tool_calls.jsonl (JSONL格式)
{"tool_name":"tavily_search","query":"...","execution_time":1.23,"result_count":5}
{"tool_name":"arxiv_search","query":"...","execution_time":0.87,"result_count":3}
```

**如何过滤**：
```powershell
# 查看最近20次工具调用
Get-Content logs\tool_calls.jsonl -Tail 20

# 搜索特定工具的调用记录
Get-Content logs\tool_calls.jsonl | Select-String "tavily_search"

# 查看搜索任务的主日志
Get-Content logs\server.log | Select-String "搜索工具|search_query|🔍"
```

**数据库查询**：
```bash
# 查看归档的搜索会话
sqlite3 data/archived_sessions.db "SELECT session_id, is_deep_mode, total_rounds FROM archived_search_sessions LIMIT 10"
```

---

### 三、快速查询命令

#### Windows PowerShell 命令

```powershell
# 1. 查看实时主日志（最近100行）
Get-Content logs\server.log -Wait -Tail 100 -Encoding UTF8

# 2. 搜索特定会话ID的所有日志
Get-Content logs\server.log | Select-String "8pdwoxj8"

# 3. 查看今天的所有错误日志
Get-Content logs\errors.log | Select-String (Get-Date -Format "yyyy-MM-dd")

# 4. 统计工具调用次数
(Get-Content logs\tool_calls.jsonl | Select-String "tavily_search").Count

# 5. 查看最近10分钟的日志（需要PowerShell 7+）
$cutoff = (Get-Date).AddMinutes(-10).ToString("yyyy-MM-dd HH:mm")
Get-Content logs\server.log | Select-String -Pattern $cutoff -Context 0,100

# 6. 导出特定会话的完整日志
Get-Content logs\server.log | Select-String "SESSION_ID" | Out-File session_debug.txt

# 7. 查看深度思考模式的概念图生成日志
Get-Content logs\server.log | Select-String "独立概念图|concept.*generation" -Context 2,5

# 8. 监控搜索工具的实时调用
Get-Content logs\tool_calls.jsonl -Wait -Tail 10
```

#### Linux/Mac 命令

```bash
# 查看实时主日志
tail -f logs/server.log

# 搜索深度思考模式
grep -E "深度思考|deep_thinking" logs/server.log

# 查看工具调用统计
jq -s 'group_by(.tool_name) | map({tool: .[0].tool_name, count: length})' logs/tool_calls.jsonl

# 查看特定时间段的日志
awk '/2026-01-10 14:00/,/2026-01-10 15:00/' logs/server.log
```

---

### 四、日志配置代码位置索引

> 需要修改日志行为时，参考这些文件：

| 功能 | 文件路径 | 关键行号 | 说明 |
|-----|---------|---------|------|
| **主日志配置** | [app/utils/logger.py](app/utils/logger.py) | 71-107 | server.log, auth.log, errors.log轮转策略 |
| **工具调用记录器** | [app/utils/tool_call_tracker.py](app/utils/tool_call_tracker.py) | 60-128 | tool_calls.jsonl记录逻辑 |
| **性能监控** | [app/utils/monitoring.py](app/utils/monitoring.py) | 31-75 | performance_metrics.jsonl |
| **环境感知配置** | [app/utils/logger.py](app/utils/logger.py) | 15-50 | 开发/生产环境日志级别 |
| **会话归档** | [app/utils/archive_manager.py](app/utils/archive_manager.py) | 100-200 | archived_sessions.db写入 |
| **检查点配置** | [app/graph/checkpointer.py](app/graph/checkpointer.py) | - | LangGraph检查点持久化 |

---

### 五、三种模式的日志份数总结

**答案**：共 **3-5 份主要日志**（取决于模式）

| 模式 | 日志数量 | 日志清单 |
|-----|---------|----------|
| **普通思考** | **3份** | ① server.log<br>② errors.log<br>③ tool_calls.jsonl（如使用搜索） |
| **深度思考** | **3份** | ① server.log（内容更详细）<br>② errors.log<br>③ tool_calls.jsonl |
| **搜索任务** | **5份** | ① server.log<br>② errors.log<br>③ tool_calls.jsonl **（重要）**<br>④ performance_metrics.jsonl<br>⑤ archived_search_sessions 表 |

**共同存储位置**：
- 文件日志：`logs/` 目录
- 数据库：`data/archived_sessions.db` 和 `data/checkpoints/workflow.db`

---

### 六、常见调试场景

#### 场景1：搜索工具没有返回结果

```powershell
# 1. 检查工具调用是否成功
Get-Content logs\tool_calls.jsonl -Tail 50 | Select-String "tavily_search|bocha_search"

# 2. 查看主日志中的搜索记录
Get-Content logs\server.log | Select-String "搜索工具|search_query" -Context 3,3

# 3. 检查错误日志
Get-Content logs\errors.log -Tail 20
```

#### 场景2：深度思考模式概念图生成失败

```powershell
# 1. 确认是否启用深度思考模式
Get-Content logs\server.log | Select-String "🧠|deep_thinking: true"

# 2. 查看概念图生成日志
Get-Content logs\server.log | Select-String "concept.*generation|独立概念图" -Context 2,5

# 3. 检查相关错误
Get-Content logs\errors.log | Select-String "concept_image|ConceptImageGenerator"
```

#### 场景3：追踪特定会话的完整执行流程

```powershell
# 替换 SESSION_ID 为实际会话ID
$sessionId = "8pdwoxj8"

# 导出完整日志
Get-Content logs\server.log | Select-String $sessionId | Out-File "debug_$sessionId.log"

# 查看数据库记录
sqlite3 data/archived_sessions.db "SELECT * FROM archived_sessions WHERE session_id='$sessionId'"
```

---

### 七、日志系统架构图

```
┌────────────────────────────────────────────────────┐
│          LangGraph 日志系统架构                     │
└────────────────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
  ┌──────────┐   ┌──────────┐   ┌─────────────┐
  │ 控制台输出 │   │ 文件日志  │   │ 数据库持久化 │
  │(开发环境)  │   │(所有环境) │   │(会话/检查点) │
  └──────────┘   └──────────┘   └─────────────┘
                        │
       ┌────────────────┼────────────────┐
       ▼                ▼                ▼
 ┌──────────┐    ┌──────────┐    ┌─────────────┐
 │server.log│    │tool_calls│    │archived_    │
 │errors.log│    │.jsonl    │    │sessions.db  │
 │auth.log  │    │performance   │ │checkpoints/ │
 │alerts.log│    │_metrics  │    │workflow.db  │
 └──────────┘    └──────────┘    └─────────────┘
      ▲               ▲                ▲
      │               │                │
 ┌────┴────┐   ┌─────┴─────┐   ┌─────┴──────┐
 │普通思考  │   │深度思考    │   │搜索任务     │
 │深度思考  │   │(内容更详细)│   │(工具调用多) │
 │搜索任务  │   │           │   │            │
 └─────────┘   └───────────┘   └────────────┘
```

---

## 🎯 关键要点记忆卡片

### 记忆要点1：日志文件位置
```
✅ 所有模式共享：logs/server.log
✅ 搜索任务专用：logs/tool_calls.jsonl
✅ 数据库持久化：data/archived_sessions.db
```

### 记忆要点2：日志区分标识
```
✅ 普通思考：thinking_mode: normal
✅ 深度思考：🧠 或 deep_thinking: true
✅ 搜索任务：tool_name: tavily_search
```

### 记忆要点3：快速定位命令
```powershell
# 实时监控
Get-Content logs\server.log -Wait -Tail 100

# 搜索深度思考
Get-Content logs\server.log | Select-String "深度思考"

# 查看工具调用
Get-Content logs\tool_calls.jsonl -Tail 20
```

---

就这么简单！🎉
