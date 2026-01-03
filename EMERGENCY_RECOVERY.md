# 🚨 紧急恢复快速指南

> **程序出错？立即恢复到历史版本！**

---

## ⚡ 最快恢复方法（3分钟）

### 方法1：使用Git恢复到任意历史版本 ⭐ 推荐

```bash
# 1. 查看最近10个提交
git log --oneline -10

# 2. 恢复到指定版本（替换为实际的commit hash）
git checkout <commit-hash>

# 示例：恢复到昨天的版本
git checkout 86fa933

# 3. 如果要永久恢复（创建新分支）
git checkout -b recovery-20251231 86fa933

# 4. 如果要覆盖当前版本
git reset --hard 86fa933
```

**当前可用的版本**：
```bash
86fa933 - fix: 修复概念图生成失败问题
f10435a - revert: 撤销错误的需求确认修复
ab9a197 - docs: 添加前端版本不稳定根因分析报告
393d18e - fix: 删除不属于642ea1c的文件
fdfb351 - fix: 紧急恢复前端到 v7.107
```

---

### 方法2：从备份恢复完整项目

```cmd
# 运行恢复脚本
scripts\restore_backup_enhanced.bat

# 选择最近的备份版本
# 按提示操作即可
```

---

### 方法3：仅恢复单个文件

```bash
# 恢复指定文件到之前的版本
git checkout <commit-hash> -- path/to/file

# 示例：恢复前端配置
git checkout 86fa933 -- frontend-nextjs/app/page.tsx

# 示例：恢复后端API
git checkout 86fa933 -- intelligent_project_analyzer/api/server.py
```

---

## 🔍 常见错误场景快速恢复

### 场景1：前端崩溃无法启动

```bash
# 恢复到最后一个稳定版本 v7.107
cd frontend-nextjs
git checkout fdfb351 -- .

# 重新安装依赖
npm install

# 重新构建
npm run build
npm run dev
```

### 场景2：后端API报错

```bash
# 恢复后端代码
git checkout 86fa933 -- intelligent_project_analyzer/

# 重新安装依赖
pip install -r requirements.txt

# 重启服务
python -B -m uvicorn intelligent_project_analyzer.api.server:app --host 0.0.0.0 --port 8000 --reload
```

### 场景3：配置文件损坏

```bash
# 从备份恢复配置
copy backup\auto_backup_*\config\.env .env
copy backup\auto_backup_*\config\requirements.txt requirements.txt

# 或从Git恢复
git checkout HEAD -- .env.example
git checkout HEAD -- requirements.txt
```

### 场景4：数据库出错

```bash
# 恢复SQLite数据库
copy backup\auto_backup_*\data\*.db data\

# 恢复Redis数据
copy backup\auto_backup_*\data\redis_dump.rdb data\dump.rdb
```

---

## 📦 当前可用的备份版本

```cmd
# 查看所有备份
dir backup\auto_backup_* /o-d

# 查看备份信息
type backup\auto_backup_周三022512_134632\BACKUP_INFO.txt
```

**最近的备份**：
- `auto_backup_周三022512_134632` - 2025-12-31 13:46
- `auto_backup_周三022512_133807` - 2025-12-31 13:38
- `auto_backup_周三022512_100001` - 2025-12-31 10:00

---

## 🆘 完全灾难恢复（项目完全损坏）

### 步骤1：从GitHub克隆干净版本

```bash
# 备份当前损坏的项目
move D:\11-20\langgraph-design D:\11-20\langgraph-design_broken

# 重新克隆
cd D:\11-20
git clone https://github.com/dafei0755/ai.git langgraph-design
cd langgraph-design
```

### 步骤2：恢复到最后工作的版本

```bash
# 查看所有标签
git tag -l

# 恢复到稳定版本
git checkout v7.107-backup-20251231

# 或恢复到特定提交
git checkout 86fa933
```

### 步骤3：从备份恢复配置和数据

```bash
# 复制备份目录到新项目
xcopy D:\11-20\langgraph-design_broken\backup backup\ /E /I /Y

# 恢复配置
copy backup\auto_backup_*\config\.env .env

# 恢复数据库
copy backup\auto_backup_*\data\*.db data\
```

### 步骤4：重新安装依赖

```bash
# 后端
pip install -r requirements.txt

# 前端
cd frontend-nextjs
npm install
```

---

## 🔧 预防措施（避免下次出错）

### 1. 启用自动备份（强烈推荐）

```powershell
# 以管理员权限运行
PowerShell -ExecutionPolicy Bypass scripts\setup_backup_tasks.ps1
```

这将创建每天2次的自动备份（10:00 AM + 6:00 PM）

### 2. 重大修改前手动备份

```cmd
# 修改代码前先备份
scripts\backup_project.bat
```

### 3. 使用Git分支进行实验

```bash
# 创建实验分支
git checkout -b experiment-feature

# 如果失败，直接切回主分支
git checkout main
```

### 4. 定期推送到GitHub

```bash
# 每天工作结束后推送
git add .
git commit -m "feat: 完成XXX功能"
git push origin main
```

---

## 📞 紧急联系

如果以上方法都无法恢复，请：

1. **保留错误现场**：不要删除任何文件
2. **收集错误信息**：
   ```bash
   # 保存错误日志
   git status > error_status.txt
   git log -20 > error_log.txt
   ```
3. **提交Issue**：https://github.com/dafei0755/ai/issues
4. **附上以下信息**：
   - 错误描述
   - error_status.txt
   - error_log.txt
   - 最后执行的操作

---

## ✅ 快速检查清单

恢复后验证系统是否正常：

```bash
# [ ] Git状态正常
git status

# [ ] 后端可以启动
python -B -m uvicorn intelligent_project_analyzer.api.server:app --host 0.0.0.0 --port 8000

# [ ] 前端可以构建
cd frontend-nextjs && npm run build

# [ ] API正常响应
curl http://localhost:8000/health

# [ ] 前端页面可访问
# 浏览器打开 http://localhost:3000
```

---

## 🎯 记住这些命令

```bash
# 最重要的3个命令：

# 1. 查看历史版本
git log --oneline -10

# 2. 恢复到指定版本
git checkout <commit-hash>

# 3. 从备份恢复
scripts\restore_backup_enhanced.bat
```

---

<div align="center">

**保存这个文件！** 📌

出问题时直接打开此文件，按步骤操作即可！

</div>
