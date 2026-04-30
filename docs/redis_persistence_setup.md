# Redis 持久化配置指南

**目标**: 防止Redis重启后数据丢失
**当前状态**: RDB和AOF均未启用

---

## 方案1: 修改现有Redis配置（推荐）

### 1.1 找到Redis配置文件

```bash
# 查找redis.conf位置
redis-cli CONFIG GET dir
redis-cli CONFIG GET config_file

# 或者查找文件
find / -name redis.conf 2>/dev/null
```

### 1.2 编辑redis.conf

添加或修改以下配置：

```conf
# ============ AOF持久化配置 ============
# 启用AOF (Append Only File)
appendonly yes

# AOF同步策略（推荐everysec）
# - always: 每次写入都同步（最安全但慢）
# - everysec: 每秒同步一次（推荐，兼顾性能和安全）
# - no: 由操作系统决定何时同步（最快但不安全）
appendfsync everysec

# AOF文件名
appendfilename "appendonly.aof"

# ============ RDB快照配置 ============
# RDB快照规则（作为AOF的补充）
save 900 1      # 15分钟内至少1个key改变
save 300 10     # 5分钟内至少10个key改变
save 60 10000   # 1分钟内至少10000个key改变

# RDB文件名
dbfilename dump.rdb

# ============ 数据目录 ============
# 数据文件存储目录（确保目录存在且有写权限）
dir /var/lib/redis

# ============ 其他配置 ============
# 后台保存失败时停止写入
stop-writes-on-bgsave-error yes

# 压缩RDB文件
rdbcompression yes

# RDB文件校验
rdbchecksum yes
```

### 1.3 创建数据目录

```bash
# 创建目录
sudo mkdir -p /var/lib/redis

# 设置权限
sudo chown redis:redis /var/lib/redis
sudo chmod 770 /var/lib/redis
```

### 1.4 重启Redis

```bash
# 重启Redis服务
sudo systemctl restart redis

# 或者
sudo service redis-server restart

# 验证配置
redis-cli CONFIG GET appendonly
redis-cli CONFIG GET dir
```

---

## 方案2: 使用Docker运行Redis（推荐）

### 2.1 停止现有Redis

```bash
# 如果Redis在Docker中运行
docker stop redis
docker rm redis

# 如果Redis作为服务运行
sudo systemctl stop redis
```

### 2.2 创建数据目录

```bash
# 在项目根目录创建Redis数据目录
cd /d/11-20/langgraph-design
mkdir -p redis_data
```

### 2.3 创建Redis配置文件

创建 `redis.conf` 文件：

```bash
cat > redis.conf << 'EOF'
# Redis持久化配置
appendonly yes
appendfsync everysec
save 900 1
save 300 10
save 60 10000
dir /data
dbfilename dump.rdb
appendfilename appendonly.aof
EOF
```

### 2.4 运行Docker容器

```bash
# 使用自定义配置运行Redis
docker run -d \
  --name redis \
  -p 6379:6379 \
  -v $(pwd)/redis_data:/data \
  -v $(pwd)/redis.conf:/usr/local/etc/redis/redis.conf \
  redis:7-alpine \
  redis-server /usr/local/etc/redis/redis.conf

# 或者使用命令行参数（简化版）
docker run -d \
  --name redis \
  -p 6379:6379 \
  -v $(pwd)/redis_data:/data \
  redis:7-alpine \
  redis-server --appendonly yes --appendfsync everysec
```

---

## 方案3: 使用docker-compose（最推荐）

### 3.1 创建docker-compose.yml

在项目根目录创建或修改 `docker-compose.yml`:

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    container_name: langgraph_redis
    ports:
      - "6379:6379"
    volumes:
      - ./redis_data:/data
      - ./redis.conf:/usr/local/etc/redis/redis.conf
    command: redis-server /usr/local/etc/redis/redis.conf
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

  # 可选：添加Redis Commander管理界面
  redis-commander:
    image: rediscommander/redis-commander:latest
    container_name: langgraph_redis_commander
    environment:
      - REDIS_HOSTS=local:redis:6379
    ports:
      - "8081:8081"
    depends_on:
      - redis
```

### 3.2 启动服务

```bash
# 启动
docker-compose up -d

# 查看日志
docker-compose logs -f redis

# 停止
docker-compose down
```

---

## 方案4: 运行时动态配置（临时）

如果不想重启Redis，可以运行时配置：

```bash
# 连接到Redis
redis-cli

# 启用AOF
CONFIG SET appendonly yes
CONFIG SET appendfsync everysec

# 配置RDB
CONFIG SET save "900 1 300 10 60 10000"

# 保存配置到文件（使其持久化）
CONFIG REWRITE

# 验证配置
CONFIG GET appendonly
CONFIG GET appendfsync
```

**注意**: 运行时配置需要Redis有写入配置文件的权限。

---

## 验证持久化配置

### 1. 使用健康检查API

```bash
curl http://127.0.0.1:8000/api/debug/redis
```

**期望结果**:
```json
{
  "mode": "redis",
  "status": "connected",
  "persistence": {
    "rdb_enabled": 1,
    "aof_enabled": 1,
    "last_save_time": "..."
  },
  "recommendation": "✅ Redis已连接，会话数据持久化存储"
}
```

### 2. 使用Redis CLI

```bash
redis-cli INFO persistence
```

**期望输出**:
```
# Persistence
loading:0
rdb_changes_since_last_save:0
rdb_bgsave_in_progress:0
rdb_last_save_time:...
aof_enabled:1
aof_rewrite_in_progress:0
```

### 3. 检查数据文件

```bash
# 检查AOF文件
ls -lh redis_data/appendonly.aof

# 检查RDB文件
ls -lh redis_data/dump.rdb

# 查看文件内容（仅供验证）
tail -f redis_data/appendonly.aof
```

---

## 测试持久化效果

### 测试步骤:

1. **创建测试会话**:
```bash
curl -X POST http://127.0.0.1:8000/api/analysis/start \
  -H "Content-Type: application/json" \
  -d '{"user_input": "测试Redis持久化"}'
```

2. **验证会话存在**:
```bash
curl http://127.0.0.1:8000/api/sessions
# 应该看到1个会话
```

3. **重启Redis**:
```bash
# Docker方式
docker restart redis

# 系统服务方式
sudo systemctl restart redis
```

4. **再次检查会话**:
```bash
curl http://127.0.0.1:8000/api/sessions
# 会话应该仍然存在
```

5. **检查数据文件**:
```bash
ls -lh redis_data/
# 应该看到 appendonly.aof 和 dump.rdb
```

---

## 故障排查

### 问题1: AOF写入失败

**错误**: `Can't open the append-only file: Permission denied`

**解决**:
```bash
# 检查目录权限
ls -ld redis_data/

# 修复权限
sudo chown -R 999:999 redis_data/  # Docker中Redis用户ID通常是999
chmod 770 redis_data/
```

### 问题2: RDB保存失败

**错误**: `Background saving error`

**解决**:
```bash
# 检查磁盘空间
df -h

# 禁用后台保存错误检查（临时）
redis-cli CONFIG SET stop-writes-on-bgsave-error no
```

### 问题3: 配置不生效

**原因**: Redis没有读取配置文件

**解决**:
```bash
# 启动时指定配置文件
redis-server /path/to/redis.conf

# 或使用Docker
docker run ... redis:7-alpine redis-server /usr/local/etc/redis/redis.conf
```

---

## 性能影响评估

### AOF性能影响:
- **everysec模式**: 几乎无影响（推荐）
- **always模式**: 写入性能降低50-80%
- **no模式**: 无影响但不安全

### RDB性能影响:
- **保存时**: CPU和内存使用增加（fork进程）
- **平时**: 无影响

### 磁盘空间:
- **AOF文件**: 通常比RDB大2-3倍
- **估算**: 1000个会话约50MB AOF + 20MB RDB

---

## 推荐配置总结

**生产环境**:
```conf
appendonly yes
appendfsync everysec
save 900 1
save 300 10
```

**开发环境**:
```conf
appendonly yes
appendfsync everysec
# 可以禁用RDB以节省磁盘
save ""
```

**高性能场景**:
```conf
appendonly yes
appendfsync no  # 交由OS决定
save 900 1     # 仅保留长时间快照
```

---

**文档创建时间**: 2025-11-29
**适用版本**: Redis 6.x / 7.x
**相关文档**: [会话归档功能实现指南](./session_archive_implementation.md)
