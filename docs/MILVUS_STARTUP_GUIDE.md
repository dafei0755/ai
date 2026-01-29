# Milvus服务启动指南

**日期**: 2026-01-06
**目标**: 启动Milvus向量数据库服务
**当前问题**: Docker守护进程未运行

---

## 问题诊断

```
错误: failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine
原因: Docker Desktop未启动
```

---

## 解决方案

### 步骤 1: 启动Docker Desktop

**Windows系统**:
1. 在开始菜单搜索 "Docker Desktop"
2. 点击启动Docker Desktop
3. 等待Docker图标显示为绿色（表示已就绪）
4. 通常需要1-2分钟启动时间

**验证Docker已启动**:
```bash
docker --version
docker ps
```

如果看到类似输出，说明Docker已就绪：
```
CONTAINER ID   IMAGE     COMMAND   CREATED   STATUS    PORTS     NAMES
```

---

### 步骤 2: 拉取Milvus镜像

```bash
docker pull milvusdb/milvus:v2.4.0
```

**预计时间**: 2-5分钟（取决于网络速度）

**预期输出**:
```
v2.4.0: Pulling from milvusdb/milvus
...
Status: Downloaded newer image for milvusdb/milvus:v2.4.0
```

---

### 步骤 3: 启动Milvus Standalone

**命令**:
```bash
docker run -d ^
  --name milvus-standalone ^
  -p 19530:19530 ^
  -p 9091:9091 ^
  -v milvus_data:/var/lib/milvus ^
  -e ETCD_USE_EMBED=true ^
  -e COMMON_STORAGETYPE=local ^
  milvusdb/milvus:v2.4.0
```

**参数说明**:
- `-d`: 后台运行
- `--name milvus-standalone`: 容器名称
- `-p 19530:19530`: Milvus服务端口（gRPC）
- `-p 9091:9091`: Milvus管理端口
- `-v milvus_data:/var/lib/milvus`: 数据持久化
- `-e ETCD_USE_EMBED=true`: 使用嵌入式etcd
- `-e COMMON_STORAGETYPE=local`: 使用本地存储

**预期输出**:
```
f8d3c8e9a1b2c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9
```
（这是容器ID）

---

### 步骤 4: 验证Milvus服务状态

**检查容器是否运行**:
```bash
docker ps | findstr milvus
```

**预期输出**:
```
f8d3c8e9a1b2   milvusdb/milvus:v2.4.0   "/tini -- milvus ru…"   10 seconds ago   Up 9 seconds   0.0.0.0:9091->9091/tcp, 0.0.0.0:19530->19530/tcp   milvus-standalone
```

**检查容器日志**:
```bash
docker logs milvus-standalone --tail 50
```

**成功启动的标志**:
日志中应包含类似内容：
```
[INFO] [proxy/proxy.go:...] Proxy server started successfully
[INFO] [datanode/data_node.go:...] DataNode started successfully
```

---

### 步骤 5: 测试Milvus连接

**使用Python测试**:
```bash
cd d:\11-20\langgraph-design
python scripts/check_milvus_schema.py
```

**预期输出（成功）**:
```
======================================================================
Milvus Schema 检查工具 - v7.141.4
======================================================================

🔌 连接到 Milvus: localhost:19530
✅ 连接成功

⚠️  Collection 'design_knowledge_base' 不存在
建议: 直接运行迁移脚本创建新Collection
```

**预期输出（需要迁移）**:
```
✅ Collection 'design_knowledge_base' 存在
⚠️  缺失字段:
  - file_size_bytes
  - created_at
  - expires_at
  - is_deleted
  - user_tier

建议: 运行迁移脚本
```

---

## 常见问题

### Q1: Docker Desktop启动失败

**错误**: "Docker Desktop requires Windows 10 Pro/Enterprise"

**解决**:
- 如果是Windows 10 Home，需要安装WSL 2
- 参考: https://docs.docker.com/desktop/windows/install/

---

### Q2: 端口19530被占用

**错误**:
```
Error starting userland proxy: listen tcp4 0.0.0.0:19530: bind: Only one usage of each socket address
```

**解决**:
```bash
# 检查端口占用
netstat -ano | findstr :19530

# 如果被占用，修改端口映射
docker run -d ^
  --name milvus-standalone ^
  -p 19531:19530 ^
  -p 9092:9091 ^
  -v milvus_data:/var/lib/milvus ^
  -e ETCD_USE_EMBED=true ^
  -e COMMON_STORAGETYPE=local ^
  milvusdb/milvus:v2.4.0

# 同时修改 .env 文件
# MILVUS_PORT=19531
```

---

### Q3: 容器启动后立即停止

**检查日志**:
```bash
docker logs milvus-standalone
```

**常见原因**:
1. 内存不足（Milvus需要至少4GB RAM）
2. 磁盘空间不足
3. 配置错误

**解决**:
```bash
# 分配更多内存（在Docker Desktop设置中）
# Settings → Resources → Memory → 至少8GB

# 清理无用容器释放空间
docker system prune -a
```

---

### Q4: Milvus启动很慢

**正常情况**: 首次启动需要1-2分钟

**检查启动进度**:
```bash
# 实时查看日志
docker logs -f milvus-standalone
```

**启动完成的标志**:
```
[INFO] Milvus Proxy started successfully
```

---

## 快速命令参考

```bash
# 启动Milvus（如果容器已存在但停止）
docker start milvus-standalone

# 停止Milvus
docker stop milvus-standalone

# 重启Milvus
docker restart milvus-standalone

# 删除Milvus容器（数据会保留在volume中）
docker rm milvus-standalone

# 删除数据（谨慎！）
docker volume rm milvus_data

# 查看Milvus资源使用
docker stats milvus-standalone

# 进入Milvus容器
docker exec -it milvus-standalone bash
```

---

## 下一步

Milvus启动成功后，执行：

### 1. Schema检查
```bash
cd d:\11-20\langgraph-design
python scripts/check_milvus_schema.py
```

### 2. 数据迁移（如果需要）
```bash
python scripts/migrate_milvus_v7141.py --backup --drop-old
```

### 3. 测试验证
```bash
pytest tests/test_quota_enforcement_e2e.py -v
```

---

## 使用docker-compose启动（备选方案）

如果您更喜欢使用docker-compose：

**创建 docker-compose.yml**:
```yaml
version: '3.5'

services:
  etcd:
    container_name: milvus-etcd
    image: quay.io/coreos/etcd:v3.5.5
    environment:
      - ETCD_AUTO_COMPACTION_MODE=revision
      - ETCD_AUTO_COMPACTION_RETENTION=1000
      - ETCD_QUOTA_BACKEND_BYTES=4294967296
      - ETCD_SNAPSHOT_COUNT=50000
    volumes:
      - etcd_data:/etcd
    command: etcd -advertise-client-urls=http://127.0.0.1:2379 -listen-client-urls http://0.0.0.0:2379 --data-dir /etcd

  minio:
    container_name: milvus-minio
    image: minio/minio:RELEASE.2023-03-20T20-16-18Z
    environment:
      MINIO_ACCESS_KEY: minioadmin
      MINIO_SECRET_KEY: minioadmin
    volumes:
      - minio_data:/minio_data
    command: minio server /minio_data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3

  standalone:
    container_name: milvus-standalone
    image: milvusdb/milvus:v2.4.0
    command: ["milvus", "run", "standalone"]
    environment:
      ETCD_ENDPOINTS: etcd:2379
      MINIO_ADDRESS: minio:9000
    volumes:
      - milvus_data:/var/lib/milvus
    ports:
      - "19530:19530"
      - "9091:9091"
    depends_on:
      - "etcd"
      - "minio"

volumes:
  etcd_data:
  minio_data:
  milvus_data:
```

**启动命令**:
```bash
docker-compose up -d
```

**查看状态**:
```bash
docker-compose ps
```

**停止服务**:
```bash
docker-compose down
```

---

**创建日期**: 2026-01-06
**适用版本**: Milvus 2.4.0+
**相关文档**: [NEXT_STEPS_v7.141.3.md](NEXT_STEPS_v7.141.3.md)
