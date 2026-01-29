# Docker 镜像加速器配置指引

## 检测结果

✅ **Docker Desktop**: 正在运行
✅ **可用镜像加速器**: DaoCloud (https://docker.m.daocloud.io)

## 📋 自动生成的配置

已生成配置文件: `docker-daemon-config.json`

配置内容包含 4 个镜像加速器:
- DaoCloud (主要)
- 腾讯云镜像
- DockerProxy
- 百度云镜像

## 🔧 配置步骤 (3 步完成)

### 步骤 1: 打开 Docker Desktop 设置
1. 打开 Docker Desktop
2. 点击右上角 ⚙️ 齿轮图标
3. 选择左侧 **"Docker Engine"** 标签

### 步骤 2: 复制配置
打开文件 `docker-daemon-config.json`，将全部内容复制到 Docker Engine 编辑器中

或者直接复制以下内容:

```json
{
  "builder": {
    "gc": {
      "defaultKeepStorage": "20GB",
      "enabled": true
    }
  },
  "experimental": false,
  "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://mirror.ccs.tencentyun.com",
    "https://dockerproxy.com",
    "https://mirror.baidubce.com"
  ],
  "dns": [
    "8.8.8.8",
    "114.114.114.114"
  ]
}
```

### 步骤 3: 应用并重启
1. 点击右下角 **"Apply & Restart"** 按钮
2. 等待 Docker Desktop 重启完成 (约 30 秒)

## ✅ 验证配置

重启完成后，运行以下命令验证:

```bash
# 检查镜像加速器配置
docker info | findstr -i "registry"

# 拉取 Milvus 镜像
docker pull milvusdb/milvus:v2.4.0
```

## 🚀 启动服务

镜像拉取成功后，运行启动脚本:

```bash
python -B scripts\run_server_production.py
```

应该看到:
```
✅ [Milvus] 服务已运行
✅ [Milvus] 服务健康检查通过
```

## ❓ 如果配置后仍然失败

### 方案 A: 手动拉取镜像
```bash
# 直接从 DaoCloud 拉取
docker pull docker.m.daocloud.io/milvusdb/milvus:v2.4.0

# 重新标记镜像
docker tag docker.m.daocloud.io/milvusdb/milvus:v2.4.0 milvusdb/milvus:v2.4.0
```

### 方案 B: 检查 Docker Desktop 代理设置
Docker Desktop → Settings → Resources → Proxies
- 如果使用代理，确保代理正常工作
- 如果不使用代理，将代理设置改为 "System" 或 "Manual" 并留空

---

**配置文件位置**: `docker-daemon-config.json`
**详细文档**: `DOCKER_REGISTRY_MIRROR_SOLUTION.md`
