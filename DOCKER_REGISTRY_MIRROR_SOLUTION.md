# Docker 镜像拉取失败解决方案

**问题**: TLS handshake timeout - 国内访问 Docker Hub 网络问题
**错误**: `net/http: TLS handshake timeout`
**时间**: 2026-01-06 14:52

## 🔍 问题分析

### 错误详情
```
Error response from daemon: failed to resolve reference "docker.io/milvusdb/milvus:v2.4.0":
failed to do request: Head "https://registry-1.docker.io/v2/milvusdb/milvus/manifests/v2.4.0":
net/http: TLS handshake timeout
```

### 根本原因
- Docker Hub (registry-1.docker.io) 在国内访问不稳定
- TLS 握手超时，无法下载镜像
- 需要配置国内镜像加速器

---

## ✅ 解决方案 1: 配置 Docker 镜像加速器（推荐）

### 步骤 1: 打开 Docker Desktop 设置

1. 点击 Docker Desktop 右上角 **⚙️ 齿轮图标**
2. 选择左侧 **"Docker Engine"**

### 步骤 2: 配置镜像加速器

在 JSON 配置中添加 `registry-mirrors` 字段：

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
    "https://docker.1panel.live",
    "https://hub.rat.dev"
  ]
}
```

### 步骤 3: 应用配置

1. 点击右下角 **"Apply & Restart"**
2. 等待 Docker Desktop 重启完成

### 步骤 4: 验证配置

```bash
# 查看镜像加速器配置
docker info | findstr -i "registry"
```

应该看到：
```
Registry Mirrors:
  https://docker.m.daocloud.io/
  https://docker.1panel.live/
  https://hub.rat.dev/
```

---

## 🚀 解决方案 2: 手动拉取镜像（备用）

如果加速器配置后仍失败，可以手动拉取：

```bash
# 方法 A: 使用代理拉取
docker pull milvusdb/milvus:v2.4.0

# 方法 B: 从国内镜像源拉取（如果可用）
# 注意：需要先找到可用的国内镜像源
```

---

## 🔧 解决方案 3: 使用本地镜像文件（高级）

### 步骤 1: 从其他来源获取镜像

如果有其他可以访问 Docker Hub 的机器：

```bash
# 在可访问 Docker Hub 的机器上
docker pull milvusdb/milvus:v2.4.0
docker save milvusdb/milvus:v2.4.0 -o milvus-v2.4.0.tar

# 传输到目标机器后
docker load -i milvus-v2.4.0.tar
```

### 步骤 2: 验证镜像

```bash
docker images | findstr milvus
```

---

## 🎯 推荐的镜像加速器列表（2026 年可用）

### 国内公共镜像加速器

| 提供商 | 镜像地址 | 状态 |
|--------|----------|------|
| DaoCloud | https://docker.m.daocloud.io | ✅ 稳定 |
| 1Panel | https://docker.1panel.live | ✅ 稳定 |
| RatDev | https://hub.rat.dev | ✅ 稳定 |
| 阿里云 | https://[你的ID].mirror.aliyuncs.com | ✅ 需注册 |
| 腾讯云 | https://mirror.ccs.tencentyun.com | ✅ 可用 |

### 阿里云镜像加速器（需要注册）

1. 访问: https://cr.console.aliyun.com/cn-hangzhou/instances/mirrors
2. 登录阿里云账号
3. 获取专属加速器地址: `https://xxxxx.mirror.aliyuncs.com`
4. 添加到 Docker 配置中

---

## 📝 完整配置示例

### Docker Desktop GUI 配置

打开 Docker Desktop → Settings → Docker Engine，使用以下配置：

```json
{
  "builder": {
    "gc": {
      "defaultKeepStorage": "20GB",
      "enabled": true
    }
  },
  "experimental": false,
  "features": {
    "buildkit": true
  },
  "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://docker.1panel.live",
    "https://hub.rat.dev",
    "https://mirror.ccs.tencentyun.com"
  ],
  "dns": [
    "8.8.8.8",
    "114.114.114.114"
  ],
  "insecure-registries": [],
  "debug": false
}
```

---

## 🧪 测试步骤

### 1. 配置加速器后测试拉取

```bash
# 测试小镜像
docker pull hello-world

# 测试 Milvus 镜像
docker pull milvusdb/milvus:v2.4.0
```

### 2. 检查拉取速度

```bash
# 查看拉取进度
docker pull milvusdb/milvus:v2.4.0
```

应该看到正常的下载进度：
```
v2.4.0: Pulling from milvusdb/milvus
abcdef123456: Downloading [==>                ] 10.5MB/100MB
...
```

### 3. 启动 Milvus 服务

```bash
# 重新运行启动脚本
python -B scripts\run_server_production.py
```

---

## ⚠️ 常见问题

### Q1: 配置加速器后仍然超时

**解决方法**:
1. 检查防火墙/代理设置
2. 尝试不同的镜像加速器
3. 检查 DNS 配置（添加 `8.8.8.8` 到 Docker 配置）

### Q2: 镜像加速器不可用

**症状**:
```
Error response from daemon: Get https://docker.m.daocloud.io/v2/: dial tcp: lookup ...
```

**解决方法**:
- 删除不可用的加速器
- 只保留可用的加速器
- 定期检查加速器状态

### Q3: 部分镜像无法加速

某些私有镜像或特定版本可能无法通过加速器拉取，需要：
- 使用 VPN/代理
- 或者通过镜像导入方式

---

## 🔍 诊断命令

```bash
# 检查 Docker 配置
docker info

# 查看镜像加速器配置
docker info | findstr -i "registry"

# 测试网络连接
ping docker.m.daocloud.io

# 查看 Docker 日志
# Windows: C:\Users\[用户名]\AppData\Local\Docker\log.txt
# 或在 Docker Desktop → Troubleshoot → Logs

# 清理 Docker 缓存（如果需要）
docker system prune -a
```

---

## 📊 配置前后对比

### 配置前（直接访问 Docker Hub）
```
❌ registry-1.docker.io (超时)
   └─ TLS handshake timeout
```

### 配置后（使用镜像加速器）
```
✅ docker.m.daocloud.io (快速)
   ├─ 国内 CDN 加速
   ├─ 镜像同步最新
   └─ 稳定可靠
```

---

## 🎯 下一步

配置完成后：

1. **重新启动应用**
   ```bash
   python -B scripts\run_server_production.py
   ```

2. **验证 Milvus 容器启动**
   ```bash
   docker ps | findstr milvus
   ```

3. **检查服务健康状态**
   ```bash
   curl http://localhost:9091/healthz
   ```

---

## 🔗 相关文档

- [Docker 官方镜像加速器文档](https://docs.docker.com/registry/recipes/mirror/)
- [Milvus 安装指南](https://milvus.io/docs/install_standalone-docker.md)
- [诊断报告](MILVUS_STARTUP_FAILURE_DIAGNOSIS.md)
- [Docker 自启设置](DOCKER_DESKTOP_AUTO_START_GUIDE.md)

---

## 💡 预防措施

为避免将来遇到类似问题：

1. **保持镜像加速器配置**
   - 定期更新可用的加速器列表
   - 配置多个备用加速器

2. **考虑本地镜像缓存**
   - 定期备份常用镜像
   - 使用 `docker save/load` 管理镜像

3. **监控网络状态**
   - 检查是否有代理/VPN 干扰
   - 确保 DNS 解析正常

---

**最后更新**: 2026-01-06
**状态**: 待用户配置镜像加速器后验证
