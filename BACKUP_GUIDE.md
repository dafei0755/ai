# 🗄️ 项目备份与恢复指南

> 完整的前后端代码多版本备份系统
> 保留最近10个版本 | Git完整历史 | 自动化恢复

---

## 📋 目录

- [备份架构](#备份架构)
- [快速开始](#快速开始)
- [备份系统](#备份系统)
- [恢复系统](#恢复系统)
- [Redis持久化配置](#redis持久化配置)
- [备份验证](#备份验证)
- [常见问题](#常见问题)

---

## 🏗️ 备份架构

### 三层备份策略

```
┌─────────────────────────────────────────────────┐
│  层级1: 本地增量备份（每天2次）                  │
│  → backup/auto_backup_YYYYMMDD_HHMMSS/          │
│  → 保留最近10个版本（滚动删除）                 │
└─────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────┐
│  层级2: Git完整历史（repo.bundle）              │
│  → 包含所有分支、标签和提交历史                 │
│  → 可完整恢复到任意历史版本                     │
└─────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────┐
│  层级3: 云存储异地备份（可选）                  │
│  → 阿里云OSS / AWS S3                          │
│  → 保留30天滚动历史                             │
└─────────────────────────────────────────────────┘
```

### 备份内容清单

#### ✅ 完整备份的内容

- **前端代码** (完整)
  - `frontend-nextjs/app/` - Next.js页面路由
  - `frontend-nextjs/components/` - React组件
  - `frontend-nextjs/lib/` - 工具库
  - `frontend-nextjs/types/` - TypeScript类型
  - `frontend-nextjs/contexts/` - Context状态
  - `frontend-nextjs/hooks/` - 自定义Hooks
  - 所有配置文件 (`package.json`, `tsconfig.json`, 等)

- **后端代码** (完整)
  - `intelligent_project_analyzer/agents/` - 智能体实现
  - `intelligent_project_analyzer/api/` - FastAPI服务
  - `intelligent_project_analyzer/workflow/` - LangGraph工作流
  - `intelligent_project_analyzer/services/` - 业务服务
  - `intelligent_project_analyzer/core/` - 核心模块
  - `intelligent_project_analyzer/interaction/` - 人机交互
  - `intelligent_project_analyzer/review/` - 审核系统
  - `intelligent_project_analyzer/report/` - 报告生成
  - `intelligent_project_analyzer/tools/` - 工具集成
  - `intelligent_project_analyzer/utils/` - 工具函数

- **配置文件**
  - `.env` - 环境变量
  - `.env.example` - 示例配置
  - `requirements.txt` - Python依赖
  - `intelligent_project_analyzer/config/` - 完整配置目录

- **核心文档**
  - `README.md` - 项目说明
  - `CLAUDE.md` - 架构文档
  - `CHANGELOG.md` - 更新日志
  - `.github/DEVELOPMENT_RULES*.md` - 开发规范

- **Git完整历史**
  - `repo.bundle` - 所有分支和标签
  - `git_diff.patch` - 未提交的更改
  - `git_log.txt` - 提交日志
  - `git_branches.txt` - 分支列表
  - `git_tags.txt` - 标签列表

- **数据库文件**
  - `data/*.db` - SQLite数据库
  - `data/dump.rdb` - Redis RDB快照
  - `data/appendonly.aof` - Redis AOF日志

#### ❌ 不备份的内容（节省空间）

- `node_modules/` - Node.js依赖（可重新安装）
- `.next/` - Next.js构建产物
- `__pycache__/` - Python缓存
- `venv/` - Python虚拟环境
- `data/archived_images/` - 归档图片
- `data/followup_images/` - 跟进图片
- `data/generated_images/` - 生成图片
- `data/uploads/` - 用户上传文件
- `logs/` - 日志文件
- `htmlcov/` - 测试覆盖率报告

---

## 🚀 快速开始

### 1. 配置定时备份（推荐）

```powershell
# 以管理员权限运行PowerShell
PowerShell -ExecutionPolicy Bypass scripts\setup_backup_tasks.ps1
```

这将创建两个定时任务：
- **ProjectBackup-Morning** - 每天上午10:00执行
- **ProjectBackup-Evening** - 每天下午18:00执行

### 2. 手动执行备份

```cmd
# 运行备份脚本
scripts\backup_project.bat
```

### 3. 验证备份

```bash
# 验证最新备份
python scripts\verify_backup.py

# 验证所有备份
python scripts\verify_backup.py --all
```

### 4. 恢复备份

```cmd
# 使用增强版恢复脚本（推荐）
scripts\restore_backup_enhanced.bat

# 或使用基础版
scripts\restore_backup.bat
```

---

## 🗂️ 备份系统

### 备份脚本：`scripts/backup_project.bat`

#### 执行流程（8个步骤）

```
1. 备份配置文件 (.env, requirements.txt, package.json)
2. 备份核心文档 (README, CLAUDE, CHANGELOG)
3. 备份配置目录 (intelligent_project_analyzer/config)
4. 备份后端Python模块（完整）
5. 备份前端Next.js代码（完整）
6. 备份数据库和Redis数据
7. 创建Git完整历史（repo.bundle）
8. 生成版本索引和元数据
9. 清理旧备份（保留最近10个）
```

#### 备份命名规则

```
backup/auto_backup_YYYYMMDD_HHMMSS/
                    ^^^^^^^^^^^^^^^^
                    年月日_时分秒

示例：
auto_backup_20251231_133807/  # 2025年12月31日 13:38:07
```

#### 版本管理

- **保留策略**：最近10个备份
- **自动清理**：超过10个时自动删除最旧的
- **版本索引**：`backup/VERSION_INDEX.json`
- **元数据**：每个备份包含 `version_metadata.json`

#### 备份目录结构

```
backup/
├── VERSION_INDEX.json              # 版本索引文件
├── backup_log.txt                  # 备份日志
├── auto_backup_20251231_133807/    # 最新备份
│   ├── BACKUP_INFO.txt             # 备份清单
│   ├── version_metadata.json       # 版本元数据
│   ├── repo.bundle                 # Git完整历史 ⭐
│   ├── git_diff.patch              # Git差异
│   ├── git_log.txt                 # 提交日志
│   ├── git_branches.txt            # 分支列表
│   ├── git_tags.txt                # 标签列表
│   ├── git_current_commit.txt      # 当前提交
│   ├── config/                     # 配置文件
│   │   ├── .env
│   │   ├── requirements.txt
│   │   └── analyzer/               # 分析器配置
│   ├── docs/                       # 核心文档
│   ├── python/                     # 后端代码
│   │   ├── agents/
│   │   ├── api/
│   │   ├── workflow/
│   │   └── ...
│   ├── frontend/                   # 前端代码
│   │   ├── app/
│   │   ├── components/
│   │   └── ...
│   └── data/                       # 数据库文件
│       ├── *.db                    # SQLite
│       ├── redis_dump.rdb          # Redis RDB
│       └── redis_appendonly.aof    # Redis AOF
└── auto_backup_20251230_180001/    # 之前的备份...
```

#### 版本元数据示例

```json
{
  "backup_time": "2025-12-31 13:38:07",
  "backup_dir": "d:\\11-20\\langgraph-design\\backup\\auto_backup_20251231_133807",
  "timestamp": "20251231_133807",
  "git_commit": "86fa933af2e1b4c8d9f7a5e3c2b1a9d8e7f6c5b4",
  "git_branch": "main",
  "has_bundle": true
}
```

---

## 🔄 恢复系统

### 增强版恢复脚本：`scripts/restore_backup_enhanced.bat`

#### 执行流程（8个步骤）

```
1. 从Git bundle恢复完整仓库历史 ⭐
   → 创建临时目录
   → git clone repo.bundle
   → 可选：替换当前项目

2. 恢复配置文件
   → .env
   → requirements.txt
   → package.json

3. 恢复后端Python代码（完整）

4. 恢复前端Next.js代码（完整）

5. 恢复配置目录

6. 恢复数据库文件（可选）

7. 重新安装依赖（可选）
   → pip install -r requirements.txt
   → npm install

8. 应用Git差异（可选）
```

#### 恢复模式

##### 1. 完整恢复（推荐）

```cmd
scripts\restore_backup_enhanced.bat
```

- 交互式选择备份版本
- 从Git bundle恢复完整历史
- 自动重建虚拟环境
- 安装所有依赖

##### 2. 部分恢复

```cmd
scripts\restore_backup.bat
```

- 仅恢复文件，不处理Git历史
- 不自动安装依赖
- 适用于快速恢复单个文件

#### 恢复后验证

```bash
# 1. 检查Git状态
git status
git log -10

# 2. 验证配置文件
cat .env
cat frontend-nextjs/.env.local

# 3. 检查依赖
pip list
cd frontend-nextjs && npm list --depth=0

# 4. 启动服务测试
start_backend_enhanced.bat
cd frontend-nextjs && npm run dev
```

---

## 🔧 Redis持久化配置

### 配置文件：`config/redis.conf`

#### 双持久化策略（推荐）

```conf
# RDB快照（定时保存）
save 900 1      # 15分钟内至少1个key变化
save 300 10     # 5分钟内至少10个key变化
save 60 10000   # 1分钟内至少10000个key变化

dbfilename dump.rdb
dir ./data
rdbcompression yes

# AOF追加日志（实时保存）
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec    # 每秒同步一次（推荐）
```

#### 启动Redis（使用配置文件）

```bash
# Windows (使用WSL或Docker)
docker run -d \
  -p 6379:6379 \
  -v d:/11-20/langgraph-design/config/redis.conf:/etc/redis/redis.conf \
  -v d:/11-20/langgraph-design/data:/data \
  redis:alpine redis-server /etc/redis/redis.conf

# Linux/Mac
redis-server config/redis.conf
```

#### Redis数据备份

备份脚本会自动备份以下文件：
- `data/dump.rdb` → `backup/*/data/redis_dump.rdb`
- `data/appendonly.aof` → `backup/*/data/redis_appendonly.aof`

#### Redis数据恢复

```bash
# 方法1: 从备份恢复
copy backup\auto_backup_*\data\redis_dump.rdb data\dump.rdb
copy backup\auto_backup_*\data\redis_appendonly.aof data\appendonly.aof

# 方法2: 使用恢复脚本（自动）
scripts\restore_backup_enhanced.bat
# 选择"是否恢复数据库文件？(Y/N)" → Y
```

---

## ✅ 备份验证

### 验证脚本：`scripts/verify_backup.py`

#### 验证项目

```python
# 自动检查以下项目：
1. 目录结构完整性
   - config/
   - docs/
   - python/
   - frontend/

2. Git bundle完整性
   - git bundle verify repo.bundle
   - 检查bundle大小

3. 关键文件存在性
   - BACKUP_INFO.txt
   - version_metadata.json
   - requirements.txt
   - package.json

4. 版本元数据有效性
   - 备份时间
   - Git提交hash
   - Git分支

5. 代码文件数量
   - Python文件 ≥ 50个
   - TypeScript文件 ≥ 30个
```

#### 使用方法

```bash
# 验证最新备份
python scripts\verify_backup.py

# 验证所有备份
python scripts\verify_backup.py --all
```

#### 输出示例

```
============================================================
验证备份: auto_backup_20251231_133807
============================================================

[1/6] 检查目录结构...
  ✓ 检查完成

[2/6] 验证Git bundle...
  ✓ Git bundle完整性验证通过
  → Bundle大小: 125.34 MB

[3/6] 检查关键文件...
  ✓ 检查完成

[4/6] 验证版本元数据...
  → 备份时间: 2025-12-31 13:38:07
  → Git提交: 86fa933a
  → Git分支: main

[5/6] 统计代码文件...
  → Python文件: 96 个
  → TypeScript文件: 81 个

[6/6] 生成验证报告...

============================================================
验证结果汇总
============================================================

✓ 通过检查 (15 项):
  • 目录存在: config/
  • 目录存在: docs/
  • 目录存在: python/
  • 目录存在: frontend/
  • Git bundle验证通过
  ... 共 15 项

⚠ 警告 (0 项):

✗ 错误 (0 项):

============================================================
✅ 验证通过：备份完整且可用
============================================================
```

---

## ❓ 常见问题

### Q1: 备份大小是多少？

**A**: 典型的备份大小：
- **代码备份**: 150-200 MB（包含Git bundle）
- **完整备份**（含数据库）: 200-300 MB
- **10个版本总计**: 约 2-3 GB

### Q2: 如何恢复到特定的历史提交？

**A**: 使用Git bundle恢复：

```bash
# 1. 恢复备份
scripts\restore_backup_enhanced.bat
# 选择包含Git bundle的备份

# 2. 查看提交历史
git log --oneline -20

# 3. 恢复到特定提交
git checkout <commit-hash>

# 或创建新分支
git checkout -b recovery-branch <commit-hash>
```

### Q3: 可以只恢复前端或后端吗？

**A**: 可以手动恢复：

```bash
# 只恢复前端
xcopy backup\auto_backup_*\frontend frontend-nextjs\ /E /I /Y

# 只恢复后端
xcopy backup\auto_backup_*\python intelligent_project_analyzer\ /E /I /Y

# 只恢复配置
copy backup\auto_backup_*\config\.env .env
```

### Q4: 备份失败了怎么办？

**A**: 检查以下事项：

```bash
# 1. 检查磁盘空间
dir backup

# 2. 检查Git状态
git status

# 3. 查看备份日志
type backup\backup_log.txt

# 4. 手动运行备份（查看详细错误）
scripts\backup_project.bat
```

### Q5: 如何备份到云存储？

**A**: 使用 rclone 或云服务CLI：

```bash
# 安装rclone
winget install rclone

# 配置云存储（以阿里云OSS为例）
rclone config

# 同步备份到云端
rclone sync backup/ aliyun:project-backups/langgraph-design/ \
  --exclude "*.log" \
  --progress

# 定时任务中添加云端同步
# 在backup_project.bat末尾添加：
# rclone sync %BACKUP_DIR% aliyun:project-backups/latest/
```

### Q6: 如何迁移到新机器？

**A**: 完整迁移步骤：

```bash
# 旧机器上
# 1. 执行最新备份
scripts\backup_project.bat

# 2. 复制整个backup目录到新机器
# 或上传到云存储

# 新机器上
# 3. 克隆项目（获取脚本）
git clone https://github.com/dafei0755/ai.git

# 4. 复制备份目录
# 将backup/放到项目根目录

# 5. 执行完整恢复
scripts\restore_backup_enhanced.bat
# 选择最新备份
# 选择"是"恢复Git历史
# 选择"是"安装依赖
```

### Q7: Pre-commit Hook导致备份不完整？

**A**: 临时禁用hook：

```bash
# 在备份前执行
git config core.hooksPath /dev/null

# 备份完成后恢复
git config --unset core.hooksPath

# 或修改.git/hooks/pre-commit
# 在脚本开头添加：
# exit 0
```

---

## 📋 维护建议

### 每日

- [x] 自动备份（上午10:00 + 下午18:00）
- [x] 检查备份日志 `backup\backup_log.txt`

### 每周

- [ ] 验证最新备份 `python scripts\verify_backup.py`
- [ ] 检查备份数量（应为10个）
- [ ] 测试恢复流程（在测试环境）

### 每月

- [ ] 执行完整恢复演练
- [ ] 验证所有备份 `python scripts\verify_backup.py --all`
- [ ] 清理无效备份
- [ ] 更新备份策略（如需要）

---

## 🔗 相关文档

- [README.md](README.md) - 项目说明
- [CLAUDE.md](CLAUDE.md) - 完整架构
- [CHANGELOG.md](CHANGELOG.md) - 更新日志
- [.github/DEVELOPMENT_RULES_CORE.md](.github/DEVELOPMENT_RULES_CORE.md) - 开发规范

---

## 📞 技术支持

遇到问题？
- 📖 查看 [FAQ](#常见问题)
- 🐛 提交 [Issue](https://github.com/dafei0755/ai/issues)
- 💬 参与 [讨论](https://github.com/dafei0755/ai/discussions)

---

<div align="center">

**版本**: v2.0 | **更新时间**: 2025-12-31

🔐 保护您的代码资产 | 🔄 随时恢复任意版本

</div>
