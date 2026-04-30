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

就这么简单！🎉
