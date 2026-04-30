"""
P0-C3修复：API Key泄露清理方案

## 问题现状

### 1. 泄露的Keys（已撤销）
- Key 1: sk-or-v1-[REDACTED-b8b...df8f]
- Key 2: sk-or-v1-[REDACTED-d72...076]

**状态**: ✅ 这些keys已被OpenRouter自动禁用并已轮换

### 2. 出现位置
Git历史中的提交：
- 12ed941: feat: 添加Python后端完整源代码
- 642ea1c: Initial commit: v7.107 clean version
- 8e2df72: WordPress SSO v3.0.4 + Pricing Page Improvements

当前工作目录（未提交的文件）：
- docs/archive/BUG_FIX_SUMMARY.md
- SECURITY_INCIDENT_REPORT.md
- GIT_HISTORY_CLEANUP.md

### 3. 当前状态
✅ 已轮换密钥：.env 文件中使用的是新的keys（5866a302... 和 b4d986bf...）
✅ .gitignore 已配置：.env文件已被忽略
⚠️ 文档泄露：3个文档文件包含旧keys（未提交到Git，可直接清理）
❌ Git历史泄露：3个历史提交包含keys（需要清理）

---

## 修复方案

### 阶段1：清理工作目录中的泄露（立即执行）✅

由于包含泄露keys的文档文件尚未提交到Git，可以直接清理：

**选项A：移除泄露内容（推荐）**
- 从 docs/archive/BUG_FIX_SUMMARY.md 中移除keys
- 从 SECURITY_INCIDENT_REPORT.md 中移除keys
- 从 GIT_HISTORY_CLEANUP.md 中移除keys
- 用 `[REDACTED]` 或 `sk-or-v1-xxxx...xxxx` 替换

**选项B：删除文档（如果不需要）**
```bash
rm SECURITY_INCIDENT_REPORT.md
rm GIT_HISTORY_CLEANUP.md
# 保留 docs/archive/BUG_FIX_SUMMARY.md，但清理keys
```

### 阶段2：清理Git历史中的泄露（可选，影响较大）⚠️

**警告**：清理Git历史会：
- 重写所有提交的SHA
- 需要强制推送到远程仓库
- 可能影响其他协作者
- 不可逆操作

**方法1：使用git-filter-repo（推荐）**
```bash
# 1. 安装工具
pip install git-filter-repo

# 2. 备份仓库
cp -r .git .git-backup
git clone --mirror . ../langgraph-design-backup.git

# 3. 创建替换文件
cat > secrets.txt <<EOF
sk-or-v1-[REDACTED-KEY-1-ALREADY-REVOKED]==>sk-or-v1-[REDACTED-KEY-1]
sk-or-v1-[REDACTED-KEY-2-ALREADY-REVOKED]==>sk-or-v1-[REDACTED-KEY-2]
EOF

# 4. 执行替换
git filter-repo --replace-text secrets.txt --force

# 5. 强制推送（⚠️ 破坏性操作）
git push origin --force --all
git push origin --force --tags
```

**方法2：使用BFG Repo-Cleaner（更快）**
```bash
# 1. 下载 BFG
# https://rtyley.github.io/bfg-repo-cleaner/

# 2. 备份仓库
git clone --mirror . ../langgraph-design-backup.git

# 3. 创建替换文件
cat > replacements.txt <<EOF
sk-or-v1-[REDACTED-KEY-1-ALREADY-REVOKED]
sk-or-v1-[REDACTED-KEY-2-ALREADY-REVOKED]
EOF

# 4. 执行清理
java -jar bfg.jar --replace-text replacements.txt .

# 5. 清理和压缩
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# 6. 强制推送
git push origin --force --all
```

**方法3：删除并重新创建仓库（最简单但丢失历史）**
```bash
# 1. 备份当前代码
cp -r . ../langgraph-design-backup

# 2. 删除.git目录
rm -rf .git

# 3. 重新初始化
git init
git add .
git commit -m "Initial commit: clean version without leaked secrets"

# 4. 推送到新分支或强制覆盖
git remote add origin <your-repo-url>
git push origin main --force
```

---

## 验证步骤

### 1. 验证工作目录
```bash
# 搜索是否还有泄露的keys
grep -r "sk-or-v1-[REDACTED]" .
```

### 2. 验证Git历史
```bash
# 检查历史中是否还有keys
git log --all -S "sk-or-v1-[REDACTED]"

# 应该返回空结果
```

### 3. 使用自动化工具扫描
```bash
# 安装并运行 gitleaks
pip install gitleaks
gitleaks detect --source . --verbose

# 或使用 truffleHog
pip install truffleHog
trufflehog filesystem .
```

---

## 后续措施

### 1. 轮换密钥（已完成✅）
当前 .env 文件中使用的keys已经是新的：
- sk-or-v1-5866a302...
- sk-or-v1-b4d986bf...

### 2. 撤销泄露的密钥（推荐）
访问 OpenRouter 控制台撤销旧keys：
1. 登录 https://openrouter.ai/keys
2. 找到泄露的keys
3. 点击"Revoke"撤销

### 3. 设置CI/CD密钥扫描
```yaml
# .github/workflows/secrets-scan.yml
name: Secrets Scan

on: [push, pull_request]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0
      - name: Run Gitleaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### 4. 添加pre-commit hook
```bash
# .git/hooks/pre-commit
#!/bin/bash

# 检查是否包含API keys
if git diff --cached | grep -E "sk-or-v1-[a-f0-9]{64}"; then
    echo "❌ ERROR: Detected OpenRouter API key in commit!"
    echo "Please remove sensitive data before committing."
    exit 1
fi
```

---

## 决策建议

### 情况1：仓库未公开或仅内部使用
✅ **推荐行动**：
1. 清理工作目录中的文档（阶段1）
2. 撤销泄露的密钥
3. 不清理Git历史（影响较小）

### 情况2：仓库已公开或将公开
⚠️ **推荐行动**：
1. 清理工作目录中的文档（阶段1）
2. **必须**撤销泄露的密钥
3. **必须**清理Git历史（阶段2）
4. 设置CI/CD密钥扫描

### 情况3：密钥已被滥用
🚨 **紧急行动**：
1. **立即**撤销泄露的密钥
2. 检查OpenRouter账单是否有异常使用
3. 生成新密钥并更新所有环境
4. 清理工作目录和Git历史
5. 向团队通报事件

---

## 总结

**当前风险等级**: 🟡 中等
- ✅ 密钥已轮换（.env使用新keys）
- ✅ .gitignore已配置
- ⚠️ 文档泄露（未提交，易清理）
- ❌ Git历史泄露（3个提交）

**优先级**：
1. **立即**：清理工作目录文档中的keys（5分钟）
2. **高优**：撤销泄露的密钥（10分钟）
3. **中优**：清理Git历史（1-2小时，可选）
4. **低优**：设置CI/CD扫描（30分钟）

**预计时间**：
- 最小修复（阶段1）：15分钟
- 完整修复（阶段1+2）：2-3小时
"""
