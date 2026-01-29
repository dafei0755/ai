# Milvus Collection 重建和配额检查实施指南

## 版本: v7.141.3+
## 日期: 2026-01-06

---

## 一、迁移概述

### 迁移目标

将 Milvus Collection Schema 从 v7.141.2 升级到 v7.141.4，添加配额管理字段并启用配额检查功能。

### 新增字段（5个）

| 字段名 | 类型 | 默认值 | 说明 |
|-------|------|-------|------|
| `file_size_bytes` | INT64 | 0 | 文件大小（字节） |
| `created_at` | INT64 | 0 | 创建时间（Unix时间戳） |
| `expires_at` | INT64 | 0 | 过期时间（Unix时间戳，0=永不过期） |
| `is_deleted` | BOOL | False | 软删除标记 |
| `user_tier` | VARCHAR(20) | "free" | 用户会员等级 |

### 影响范围

- ✅ 后端 API: 文件上传接口添加配额检查
- ✅ Milvus Schema: 新增 5 个字段
- ⚠️ 数据迁移: **必须重建 Collection**（Schema 变更）
- ⏳ 前端: 需要添加配额超限提示

---

## 二、迁移前准备

### 1. 备份现有数据

**强烈建议备份**，即使迁移脚本内置备份功能。

```bash
# 方式 1: 使用迁移脚本备份（推荐）
python scripts/migrate_milvus_v7141.py --backup

# 方式 2: 手动导出数据
python scripts/export_milvus_data.py --output data/backups/manual_backup.json
```

### 2. 确认环境信息

```bash
# 检查 Python 版本
python --version  # 需要 3.10+

# 检查依赖
pip list | grep pymilvus  # 需要 2.3.0+
pip list | grep pydantic  # 需要 2.0+

# 检查 Milvus 服务
python -c "from pymilvus import connections; connections.connect(host='localhost', port=19530); print('✅ Milvus 连接成功')"
```

### 3. 获取当前数据量

```bash
# 访问管理后台
http://localhost:8000/api/admin/milvus/collection/stats

# 或使用 Python
python -c "
from pymilvus import Collection, connections
connections.connect(host='localhost', port=19530)
collection = Collection('design_knowledge_base')
print(f'当前文档数量: {collection.num_entities}')
"
```

---

## 三、迁移步骤（完整流程）

### 步骤 1: 备份现有数据

```bash
python scripts/migrate_milvus_v7141.py --backup
```

**预期输出**:
```
=======================================================================
Milvus Collection 迁移工具 - v7.141.2-v7.141.4
=======================================================================

🔌 连接到 Milvus: localhost:19530
✅ 连接成功

📦 开始备份 Collection: design_knowledge_base
🔍 查询现有数据...
💾 保存数据到: data/milvus_backups/backup_design_knowledge_base_20260106_143022.json
✅ 备份完成: 125 个文档
   备份文件: data/milvus_backups/backup_design_knowledge_base_20260106_143022.json
```

### 步骤 2: 删除旧 Collection

```bash
python scripts/migrate_milvus_v7141.py --drop-old
```

**预期输出**:
```
🗑️  删除旧 Collection: design_knowledge_base
✅ 删除成功
```

### 步骤 3: 创建新 Collection 并恢复数据

```bash
python scripts/migrate_milvus_v7141.py --backup --drop-old
```

**预期输出**:
```
🔨 创建新 Collection: design_knowledge_base
✅ Collection 创建成功
   字段数量: 17
   Schema 版本: v7.141.4

📊 创建向量索引...
✅ 索引创建成功

📥 从备份恢复数据: data/milvus_backups/backup_design_knowledge_base_20260106_143022.json
📋 备份文件包含 125 个文档
🔄 转换数据格式...
💾 批量插入数据（批次大小: 100）...
   进度: 100/125 (80.0%)
   进度: 125/125 (100.0%)
✅ 数据恢复完成: 125 个文档

🔍 验证迁移结果...
📋 Schema 验证:
   期望字段数: 17
   实际字段数: 17

📊 数据量验证:
   文档总数: 125

🎯 抽样检查新字段...
   样本 1:
     ID: 12345
     标题: 国家建筑设计规范
     可见性: public
     团队ID: (无)
     文件大小: 102400 bytes
     创建时间: 1704530522
     过期时间: 0 (永不过期)
     已删除: False
     会员等级: enterprise

✅ 迁移验证通过！

=======================================================================
✅ 迁移完成！

下一步:
  1. 启动后端服务: python -B scripts\run_server_production.py
  2. 导入文档: python scripts/import_milvus_data.py --source ./data/knowledge_docs
  3. 测试配额管理功能: 访问 http://localhost:3000/user/dashboard
=======================================================================
```

### 步骤 4: 验证迁移结果

```bash
# 方式 1: 使用管理后台
# 访问 http://localhost:8000/api/admin/milvus/collection/stats

# 方式 2: 使用 Python 脚本
python -c "
from pymilvus import Collection, connections
connections.connect(host='localhost', port=19530)
collection = Collection('design_knowledge_base')
collection.load()

# 检查字段
fields = [f.name for f in collection.schema.fields]
print('当前 Schema 字段:', fields)

# 抽样检查新字段
sample = collection.query(
    expr='id >= 0',
    output_fields=['title', 'file_size_bytes', 'created_at', 'expires_at', 'is_deleted', 'user_tier'],
    limit=3
)
for doc in sample:
    print(f'文档: {doc[\"title\"][:30]}, 文件大小: {doc[\"file_size_bytes\"]} bytes, 会员等级: {doc[\"user_tier\"]}')
"
```

---

## 四、配额检查功能测试

### 1. 启动后端服务

```bash
# Windows
python -B scripts\run_server_production.py

# Linux/Mac
python -B scripts/run_server.py
```

### 2. 测试文件大小检查（单文件上传）

**测试用例 1: 免费用户上传 6MB 文件（应失败）**

```bash
# 创建测试文件
python -c "
with open('test_large_file.txt', 'w') as f:
    f.write('A' * (6 * 1024 * 1024))  # 6 MB
"

# 测试上传 API
curl -X POST "http://localhost:8000/api/admin/milvus/import/file" \
  -F "file=@test_large_file.txt" \
  -F "owner_type=user" \
  -F "owner_id=user_123" \
  -F "user_tier=free"
```

**预期响应** (HTTP 413):
```json
{
  "detail": {
    "error": "file_size_exceeded",
    "message": "文件大小超过限制 (6.0/5 MB)",
    "file_size_mb": 6.0,
    "max_file_size_mb": 5,
    "user_tier": "free"
  }
}
```

**测试用例 2: 专业版用户上传 40MB 文件（应成功）**

```bash
curl -X POST "http://localhost:8000/api/admin/milvus/import/file" \
  -F "file=@test_large_file.txt" \
  -F "owner_type=user" \
  -F "owner_id=user_456" \
  -F "user_tier=professional"
```

**预期响应** (HTTP 200):
```json
{
  "success": true,
  "message": "成功导入 1 个文档",
  "total_documents": 1,
  "filename": "test_large_file.txt"
}
```

### 3. 测试配额超限检查（文档数量）

**准备工作: 创建 10 个文档（免费版上限）**

```bash
for i in {1..10}; do
  echo "测试文档 $i" > "test_doc_$i.txt"
  curl -X POST "http://localhost:8000/api/admin/milvus/import/file" \
    -F "file=@test_doc_$i.txt" \
    -F "owner_type=user" \
    -F "owner_id=user_quota_test" \
    -F "user_tier=free"
done
```

**测试第 11 个文档（应失败）**

```bash
echo "测试文档 11" > "test_doc_11.txt"
curl -X POST "http://localhost:8000/api/admin/milvus/import/file" \
  -F "file=@test_doc_11.txt" \
  -F "owner_type=user" \
  -F "owner_id=user_quota_test" \
  -F "user_tier=free"
```

**预期响应** (HTTP 403):
```json
{
  "detail": {
    "error": "quota_exceeded",
    "message": "配额已满，无法上传新文档",
    "errors": [
      "文档数量已达上限 (10/10)"
    ],
    "current_usage": {
      "document_count": 10,
      "storage_mb": 2.5
    },
    "quota_limit": {
      "max_documents": 10,
      "max_storage_mb": 50,
      "max_file_size_mb": 5
    },
    "user_tier": "free",
    "suggestions": [
      "删除不需要的文档以释放空间",
      "升级会员等级以提升配额"
    ]
  }
}
```

### 4. 测试配额警告（接近上限）

**上传第 9 个文档（应有警告日志）**

```bash
# 查看后端日志
tail -f logs/app.log | grep "配额警告"
```

**预期日志**:
```
⚠️ [配额警告] ['文档数量接近上限 (9/10, 90.0%)']
```

### 5. 测试系统知识库豁免

**测试公共知识库上传（不受配额限制）**

```bash
curl -X POST "http://localhost:8000/api/admin/milvus/import/file" \
  -F "file=@test_large_file.txt" \
  -F "owner_type=system" \
  -F "owner_id=public"
```

**预期响应** (HTTP 200，无配额检查):
```json
{
  "success": true,
  "message": "成功导入 1 个文档"
}
```

**预期日志**:
```
📚 [配额检查] 系统知识库，跳过配额检查
```

---

## 五、故障排查

### 问题 1: 迁移脚本提示 `no such column: visibility`

**原因**: 旧 Collection 不包含新字段

**解决方案**:
```bash
# 强制删除并重建
python scripts/migrate_milvus_v7141.py --drop-old

# 然后创建新 Collection
python scripts/migrate_milvus_v7141.py
```

### 问题 2: 配额检查未生效

**检查项**:
1. 确认配额配置文件存在: `config/knowledge_base_quota.yaml`
2. 确认配额检查已启用:
   ```yaml
   quota_check:
     enabled: true  # 确保为 true
   ```
3. 确认用户不在豁免列表中:
   ```yaml
   exempt_users:
     - "admin"
     - "system"
     # 不应包含测试用户 user_123
   ```

### 问题 3: 备份文件过大

**限制**: Milvus 单次查询最大 16384 个文档

**解决方案**:
```python
# 修改 migrate_milvus_v7141.py 的 backup_existing_collection 方法
# 分批查询和保存
batch_size = 10000
for offset in range(0, total_entities, batch_size):
    batch_results = collection.query(
        expr=f"id >= {offset}",
        output_fields=["*"],
        limit=batch_size
    )
    # 保存到不同的备份文件
```

### 问题 4: 导入后字段值为空

**检查项**:
1. 确认 `entities` 列表顺序与 Schema 字段顺序一致
2. 确认所有字段都有值（不能有 `None`）
3. 检查日志中的数据转换逻辑:
   ```
   🔄 转换数据格式...
   ```

### 问题 5: 前端未显示配额超限提示

**原因**: 前端尚未处理 HTTP 403/413 错误

**临时解决方案**: 查看浏览器控制台和网络请求

**后续任务**: 实施前端配额超限提示（Task 4）

---

## 六、回滚方案

如果迁移出现问题，可以回滚到旧版本：

### 步骤 1: 从备份恢复

```bash
# 找到最近的备份文件
ls -lt data/milvus_backups/

# 恢复备份
python scripts/migrate_milvus_v7141.py --restore data/milvus_backups/backup_design_knowledge_base_20260106_143022.json
```

### 步骤 2: 恢复旧代码

```bash
# 使用 Git 恢复到 v7.141.2
git checkout v7.141.2

# 或手动恢复修改的文件
git checkout HEAD~1 -- intelligent_project_analyzer/api/milvus_admin_routes.py
```

### 步骤 3: 重启服务

```bash
# 停止服务
pkill -f "run_server_production.py"

# 重新启动
python -B scripts/run_server_production.py
```

---

## 七、性能优化建议

### 1. 索引优化

```python
# 如果文档数量 > 10000，建议使用 IVF_PQ 索引
index_params = {
    "metric_type": "COSINE",
    "index_type": "IVF_PQ",
    "params": {
        "nlist": 1024,  # 聚类数量（文档数量的平方根）
        "m": 16,        # 压缩维度
        "nbits": 8
    }
}
collection.create_index(field_name="vector", index_params=index_params)
```

### 2. 批量插入优化

```python
# 调整批次大小（默认 100）
batch_size = 500  # 适合大文件
batch_size = 50   # 适合小文件
```

### 3. 配额检查缓存

```python
# 缓存用户配额查询结果（5分钟）
from functools import lru_cache
import time

@lru_cache(maxsize=1000)
def get_user_quota_cached(user_id: str, timestamp: int):
    # timestamp 用于缓存失效（每5分钟更新）
    quota_mgr = QuotaManager(collection=collection)
    return quota_mgr.check_quota(user_id, user_tier)

# 使用
current_5min_bucket = int(time.time() / 300)
quota_check = get_user_quota_cached(user_id, current_5min_bucket)
```

---

## 八、总结

**已完成**:
- ✅ Milvus Collection Schema 升级到 v7.141.4
- ✅ 新增 5 个配额管理字段
- ✅ 文件大小检查（单文件上传前）
- ✅ 配额超限检查（文档数量 + 存储空间）
- ✅ 系统知识库豁免配额限制
- ✅ 详细的错误响应和建议

**待完成**:
- ⏳ 前端配额超限提示（Task 4）
- ⏳ 端到端测试验证（Task 5）
- ⏳ 配额管理 UI（用户中心已有部分功能）

**关键文件**:
- 迁移脚本: `scripts/migrate_milvus_v7141.py`
- 配额配置: `config/knowledge_base_quota.yaml`
- 后端 API: `intelligent_project_analyzer/api/milvus_admin_routes.py`
- 配额管理服务: `intelligent_project_analyzer/services/quota_manager.py`

---

**创建日期**: 2026-01-06
**最后更新**: 2026-01-06
**相关版本**: v7.141.3, v7.141.4
