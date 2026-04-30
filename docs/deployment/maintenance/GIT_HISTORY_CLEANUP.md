# Git 历史清理指南 - 删除泄露的敏感信息

⚠️ **警告**: 这些操作会重写 Git 历史，需要强制推送。请确保团队成员知晓。

## 方法一：BFG Repo-Cleaner（推荐，快速）

### 1. 下载 BFG
- 访问: https://rtyley.github.io/bfg-repo-cleaner/
- 下载 `bfg-1.14.0.jar` (或最新版本)
- 需要 Java 运行环境 (JRE 8+)

### 2. 创建密钥列表文件
创建 `passwords.txt` 文件，包含所有要删除的 key：
```
sk-or-v1-[REDACTED-KEY-1-ALREADY-REVOKED]
sk-or-v1-[REDACTED-KEY-2-ALREADY-REVOKED]
```

### 3. 克隆仓库镜像
```powershell
cd d:\11-20
git clone --mirror https://github.com/dafei0755/ai.git ai-mirror.git
cd ai-mirror.git
```

### 4. 运行 BFG 清理
```powershell
# 替换密钥为 ***REMOVED***
java -jar d:\path\to\bfg-1.14.0.jar --replace-text passwords.txt

# 或直接删除包含密钥的文件
java -jar d:\path\to\bfg-1.14.0.jar --delete-files BUG_FIX_SUMMARY.md
```

### 5. 清理过期数据
```powershell
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

### 6. 强制推送
```powershell
git push --force
```

### 7. 更新本地仓库
```powershell
cd d:\11-20\langgraph-design
git pull --force
```

---

## 方法二：git filter-branch（内置，较慢）

### 1. 备份仓库
```powershell
cd d:\11-20\langgraph-design
git clone . ../langgraph-design-backup
```

### 2. 删除文件历史
```powershell
git filter-branch --force --index-filter `
  "git rm --cached --ignore-unmatch docs/archive/BUG_FIX_SUMMARY.md" `
  --prune-empty --tag-name-filter cat -- --all
```

### 3. 清理引用
```powershell
git for-each-ref --format="delete %(refname)" refs/original | git update-ref --stdin
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

### 4. 强制推送
```powershell
git push origin --force --all
git push origin --force --tags
```

---

## 方法三：git filter-repo（推荐，但需安装）

### 1. 安装 git-filter-repo
```powershell
pip install git-filter-repo
```

### 2. 创建路径规则文件
创建 `paths-to-remove.txt`:
```
docs/archive/BUG_FIX_SUMMARY.md
```

### 3. 执行清理
```powershell
cd d:\11-20\langgraph-design
git filter-repo --invert-paths --paths-from-file paths-to-remove.txt --force
```

### 4. 重新添加远程仓库
```powershell
git remote add origin https://github.com/dafei0755/ai.git
git push origin --force --all
git push origin --force --tags
```

---

## 验证清理结果

### 1. 检查文件是否还存在
```powershell
git log --all --full-history -- "*BUG_FIX_SUMMARY.md"
# 应该返回空结果
```

### 2. 搜索密钥字符串
```powershell
git log --all -S "sk-or-v1-[REDACTED]"
# 应该返回空结果
```

### 3. 检查仓库大小
```powershell
git count-objects -vH
# 应该看到 size-pack 减小
```

---

## 团队协作注意事项

### 通知所有协作者
发送邮件/消息：
```
⚠️ 重要：Git 历史已重写

我们修复了一个安全问题，重写了 Git 历史。请按以下步骤更新本地仓库：

1. 提交或暂存所有本地更改
   git stash save "Before history rewrite"

2. 删除旧的仓库目录
   cd ..
   rm -rf langgraph-design

3. 重新克隆仓库
   git clone https://github.com/dafei0755/ai.git langgraph-design
   cd langgraph-design

4. 恢复之前的更改（如果需要）
   git stash pop

如有问题，请联系 @dafei0755
```

---

## 清理后的安全措施

### 1. 启用 GitHub Secret Scanning
- 访问: https://github.com/dafei0755/ai/settings/security_analysis
- 启用 "Secret scanning"
- 启用 "Push protection"

### 2. 添加 .gitattributes
创建 `.gitattributes` 文件：
```
*.env filter=git-crypt diff=git-crypt
.env.* filter=git-crypt diff=git-crypt
```

### 3. 定期审计
```powershell
# 每月运行一次
git log --all --full-history -- "*.env*"
git log --all -S "api_key" --all
git log --all -S "sk-" --all
```

---

## 常见问题

### Q: 强制推送后其他人的仓库会怎样？
A: 他们的本地仓库会与远程不一致，需要重新克隆或 `git pull --rebase`。

### Q: 如果有未合并的 Pull Request 怎么办？
A: PR 需要重新创建，因为 commit hash 已改变。

### Q: 清理会影响 GitHub Issues 和 Releases 吗？
A: 不会影响 Issues，但 Release 的 tag 可能需要重新打。

### Q: 如何确认密钥已完全删除？
A: 使用 GitHub 的 Secret Scanning API 或第三方工具如 TruffleHog。

---

## 应急联系方式

如果遇到问题：
1. 不要继续操作
2. 检查备份是否完整
3. 联系有经验的 Git 管理员
4. GitHub 支持: https://support.github.com/

---

**创建时间**: 2025-12-31
**最后更新**: 2025-12-31
**负责人**: @dafei0755
