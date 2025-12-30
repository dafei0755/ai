# 系统文件清理指南

**创建日期**: 2025-12-10
**目的**: 明确哪些文件是系统运行必须的，哪些可以清理

---

## ✅ 系统运行必须文件

### 1. 核心代码目录（不可删除）

```
intelligent_project_analyzer/    # 后端核心代码
├── agents/                      # 智能体实现
├── api/                         # FastAPI服务
├── config/                      # 配置文件（YAML）
├── core/                        # 核心模块
├── interaction/                 # 人机交互
├── report/                      # 报告生成
├── review/                      # 审核模块
├── security/                    # 安全模块
├── services/                    # 服务层
└── workflow/                    # 工作流

frontend-nextjs/                 # 前端代码
├── app/                         # Next.js页面
├── components/                  # React组件
├── lib/                         # 工具库
├── public/                      # 静态资源
└── types/                       # TypeScript类型

scripts/                         # 工具脚本
└── *.py, *.ps1                  # 各种辅助脚本

tests/                           # 测试代码
├── test_*.py                    # 单元测试
└── outputs/                     # 测试输出
```

### 2. 配置文件（不可删除）

```
✅ .env                          # 环境变量（包含API密钥）
✅ .env.example                  # 环境变量模板
✅ .gitignore                    # Git忽略规则
✅ requirements.txt              # Python依赖
✅ package.json                  # Node.js依赖（在frontend-nextjs/）
```

### 3. 启动脚本（不可删除）

```
✅ start_services.bat            # 启动所有服务
✅ start_celery_worker.bat       # 启动Celery worker
✅ start_celery_flower.bat       # 启动Celery监控
```

### 4. 核心文档（不可删除）

```
✅ README.md                     # 项目主文档
✅ CLAUDE.md                     # Claude Code工作指南
```

---

## 🗑️ 可以清理的文件/目录

### 1. 运行时生成目录（可删除，会自动重建）

```
❌ __pycache__/                  # Python字节码缓存
   - 自动生成
   - 可随时删除
   - 运行时会自动重建

❌ data/                         # 运行时数据
   ├── uploads/                  # 用户上传文件
   └── debug/                    # 调试数据
   - 包含用户数据和调试信息
   - 可定期清理旧数据
   - 建议保留最近7天的数据

❌ logs/                         # 日志文件
   ├── api.log                   # API日志
   └── *.log                     # 其他日志
   - 自动生成
   - 可定期清理
   - 建议保留最近30天的日志

❌ reports/                      # 生成的报告
   ├── project_analysis_*.txt    # 文本报告
   └── project_analysis_*.pdf    # PDF报告
   - 用户生成的报告
   - 可定期清理
   - 建议保留最近30天的报告
```

### 2. 自动生成的依赖文件（可删除，会自动重建）

```
❌ package-lock.json             # Node.js依赖锁定文件
   - npm install时自动生成
   - 可删除后重新生成

❌ node_modules/                 # Node.js依赖包（在frontend-nextjs/）
   - npm install时自动生成
   - 占用空间大
   - 可删除后重新安装
```

### 3. 临时文档（可移动到docs/）

```
⚠️ BACKUP_20251210_SUMMARY.md   # 备份总结
   - 建议移动到 docs/maintenance/

⚠️ FILE_ORGANIZATION_PLAN.md    # 文件整理方案
   - 建议移动到 docs/maintenance/

⚠️ FRONTEND_MISSING_CONTENT_FIX.md  # 前端修复文档
   - 已有副本在 docs/frontend/
   - 可删除根目录的副本
```

---

## 📊 目录大小分析

### 占用空间较大的目录

```bash
# 检查各目录大小
du -sh */ 2>/dev/null | sort -hr
```

**预期结果**:
```
~500MB  node_modules/           # Node.js依赖（可删除重装）
~200MB  frontend-nextjs/        # 前端代码
~100MB  intelligent_project_analyzer/  # 后端代码
~50MB   data/                   # 运行时数据（可清理）
~20MB   logs/                   # 日志文件（可清理）
~10MB   reports/                # 报告文件（可清理）
~5MB    docs/                   # 文档
~1MB    tests/                  # 测试代码
```

---

## 🧹 清理建议

### 日常清理（每周）

```bash
# 1. 清理Python缓存
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# 2. 清理旧日志（保留最近7天）
find logs/ -name "*.log" -mtime +7 -delete 2>/dev/null

# 3. 清理旧报告（保留最近7天）
find reports/ -name "*.txt" -mtime +7 -delete 2>/dev/null
find reports/ -name "*.pdf" -mtime +7 -delete 2>/dev/null

# 4. 清理旧上传文件（保留最近7天）
find data/uploads/ -type f -mtime +7 -delete 2>/dev/null
```

### 深度清理（每月）

```bash
# 1. 清理所有运行时数据
rm -rf __pycache__/
rm -rf data/uploads/*
rm -rf data/debug/*
rm -rf logs/*.log
rm -rf reports/*.txt
rm -rf reports/*.pdf

# 2. 重新安装前端依赖（可选）
cd frontend-nextjs
rm -rf node_modules/
rm package-lock.json
npm install
```

### 发布前清理

```bash
# 1. 清理所有临时文件
rm -rf __pycache__/
rm -rf data/
rm -rf logs/
rm -rf reports/

# 2. 清理前端构建产物
cd frontend-nextjs
rm -rf .next/
rm -rf node_modules/
rm package-lock.json

# 3. 只保留必要文件
# - 源代码
# - 配置文件
# - 文档
# - 启动脚本
```

---

## ⚠️ 不要删除的文件

### 配置文件
```
❌ 不要删除 .env                # 包含API密钥和配置
❌ 不要删除 .gitignore          # Git配置
❌ 不要删除 requirements.txt    # Python依赖列表
```

### 配置目录
```
❌ 不要删除 intelligent_project_analyzer/config/
   - 包含所有YAML配置文件
   - 包含角色定义和提示词
   - 系统运行必需
```

### 数据库文件（如果有）
```
❌ 不要删除 *.db, *.sqlite      # 数据库文件
```

---

## 📋 清理检查清单

### 清理前检查
- [ ] 确认没有正在运行的服务
- [ ] 备份重要数据（如有需要）
- [ ] 确认要清理的文件类型

### 清理后验证
- [ ] 运行 `python -m pytest tests/` 确认测试通过
- [ ] 运行 `start_services.bat` 确认服务正常启动
- [ ] 访问前端页面确认功能正常

---

## 🔍 文件类型说明

### Python文件
```
✅ *.py                          # Python源代码（必须）
❌ *.pyc                         # Python字节码（可删除）
❌ __pycache__/                  # 字节码缓存（可删除）
```

### JavaScript/TypeScript文件
```
✅ *.js, *.jsx                   # JavaScript源代码（必须）
✅ *.ts, *.tsx                   # TypeScript源代码（必须）
❌ *.js.map                      # Source map（可删除）
❌ .next/                        # Next.js构建产物（可删除）
```

### 配置文件
```
✅ *.yaml, *.yml                 # YAML配置（必须）
✅ *.json                        # JSON配置（必须）
✅ *.env                         # 环境变量（必须）
```

### 文档文件
```
✅ README.md, CLAUDE.md          # 核心文档（必须）
⚠️ 其他*.md                      # 可移动到docs/
```

### 日志和报告
```
❌ *.log                         # 日志文件（可清理）
❌ *.txt (在reports/)            # 文本报告（可清理）
❌ *.pdf (在reports/)            # PDF报告（可清理）
```

---

## 💡 最佳实践

### 1. 定期清理
- 每周清理一次日志和临时文件
- 每月深度清理一次

### 2. 备份策略
- 重要数据定期备份
- 使用Git管理代码
- 配置文件单独备份

### 3. 监控空间
```bash
# 检查磁盘使用情况
du -sh * | sort -hr | head -10
```

### 4. 自动化清理
创建定时任务自动清理旧文件：
```bash
# Windows任务计划程序
# 或使用Python脚本定期清理
```

---

## 📝 总结

### 必须保留（10个核心文件）
```
✅ README.md
✅ CLAUDE.md
✅ requirements.txt
✅ .env
✅ .env.example
✅ .gitignore
✅ start_services.bat
✅ start_celery_worker.bat
✅ start_celery_flower.bat
✅ package-lock.json (可选)
```

### 必须保留（4个核心目录）
```
✅ intelligent_project_analyzer/
✅ frontend-nextjs/
✅ scripts/
✅ tests/
```

### 可以清理（4个运行时目录）
```
❌ __pycache__/
❌ data/
❌ logs/
❌ reports/
```

### 可以移动（3个临时文档）
```
⚠️ BACKUP_20251210_SUMMARY.md → docs/maintenance/
⚠️ FILE_ORGANIZATION_PLAN.md → docs/maintenance/
⚠️ FRONTEND_MISSING_CONTENT_FIX.md → 删除（已有副本）
```

---

**创建人**: Claude Code
**用途**: 系统维护和清理指南
**更新频率**: 根据需要更新
