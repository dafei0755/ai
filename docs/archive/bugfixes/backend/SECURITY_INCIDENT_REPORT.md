# 安全事件报告 - API Key 泄露

**日期**: 2025-12-31
**级别**: 🚨 严重
**状态**: ✅ 已修复

## 事件概述

OpenRouter 发现我们的 API key 在 GitHub 公共仓库中被暴露：
- **文件**: `docs/archive/BUG_FIX_SUMMARY.md`
- **泄露的 key**: `sk-or-v1-...df8f` (已被 OpenRouter 自动禁用)
- **发现时间**: 2025-12-31 11:54

## 影响范围

- ❌ 泄露了 2 个 OpenRouter API key
- ✅ OpenRouter 已自动禁用泄露的 key
- ⚠️ GitHub 历史记录中仍存在敏感信息

## 已采取的措施

### 1. 立即响应 ✅
- [x] 已删除文件中的真实 API key，替换为占位符
- [x] 已将 `docs/archive/` 目录加入 `.gitignore`
- [x] 已添加 GitHub Actions 自动扫描 (TruffleHog)
- [x] 已添加 pre-commit hook (detect-secrets)

### 2. 待完成事项 ⏳

#### A. 清理 Git 历史（高优先级）
```powershell
# 方法1: 使用 BFG Repo-Cleaner（推荐，快速）
# 下载: https://rtyley.github.io/bfg-repo-cleaner/
java -jar bfg-1.14.0.jar --replace-text passwords.txt langgraph-design.git

# passwords.txt 内容:
sk-or-v1-[REDACTED-KEY-1-ALREADY-REVOKED]
sk-or-v1-[REDACTED-KEY-2-ALREADY-REVOKED]

# 方法2: 使用 git filter-branch（较慢但内置）
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch docs/archive/BUG_FIX_SUMMARY.md" \
  --prune-empty --tag-name-filter cat -- --all

# 强制推送清理后的历史
git push origin --force --all
git push origin --force --tags
```

#### B. 生成新的 API Key ⏳
1. 访问 [OpenRouter Keys](https://openrouter.ai/keys)
2. 删除所有旧的 key（如果还有）
3. 创建新的 API key
4. 更新 `.env` 文件：
   ```env
   OPENROUTER_API_KEY=sk-or-v1-NEW_KEY_HERE
   ```

#### C. 通知团队 📢
- [ ] 通知所有协作者不要使用旧的 key
- [ ] 确认没有其他地方使用泄露的 key
- [ ] 检查其他服务是否使用相同 key

## 预防措施

### 已实施
1. ✅ `.gitignore` 已更新，排除 `docs/archive/`
2. ✅ 添加 GitHub Actions 自动扫描
3. ✅ 添加 pre-commit hook

### 推荐流程

#### 1. 安装 pre-commit hook
```powershell
pip install pre-commit
pre-commit install

# 首次扫描建立基线
detect-secrets scan > .secrets.baseline
```

#### 2. 在 VS Code 中使用扩展
安装：[GitGuardian](https://marketplace.visualstudio.com/items?itemName=GitGuardian.gitguardian)

#### 3. 定期审计
```powershell
# 每月检查一次
git log --all --full-history -- "*.env*"
git log --all -S "sk-or-v1-" --source --all
```

## 经验教训

❌ **不要做**:
- 不要在文档中包含真实的 API key（即使是示例）
- 不要提交包含敏感信息的 debug 输出
- 不要认为"只是临时提交"就安全

✅ **应该做**:
- 始终使用环境变量
- 在文档中使用 `sk-xxx...` 占位符
- 使用 `.env.example` 作为模板
- 定期扫描仓库

## 参考资源

- [OpenRouter Security Best Practices](https://openrouter.ai/docs/security)
- [GitHub Secrets Scanning](https://docs.github.com/en/code-security/secret-scanning)
- [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/)
- [Git Filter-Branch](https://git-scm.com/docs/git-filter-branch)

---

**负责人**: @dafei0755
**最后更新**: 2025-12-31
