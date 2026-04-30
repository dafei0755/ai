# 人工治理操作手册（一次性/每次发布）

本手册覆盖 3 项必须人工执行的动作：

1. 分支保护开关配置（一次性手工）
2. 风险白名单审批（按需）
3. 发布放行签字（每次发布）

---

## 1) 分支保护开关配置（一次性手工）

操作路径：

`GitHub Repo -> Settings -> Branches -> Add branch protection rule`

目标分支：

- `main`

必须开启：

- Require a pull request before merging
- Require approvals（>=1）
- Dismiss stale approvals
- Require status checks to pass
- Require branches to be up to date
- Include administrators
- Disable force push / delete

建议 required checks：

- `CI / check-root-directory`
- `CI / backend-gate`
- `Automated Tests / test-fast`
- `Automated Tests / lint`
- `Automated Tests / security`

执行完成后：

- 在 `docs/deployment/BRANCH_PROTECTION_SETUP_CHECKLIST.md` 勾选并记录截图。

---

## 2) 风险白名单审批（按需）

触发条件：

- 安全基线校验失败，出现新增风险；
- 或团队申请将某风险临时豁免。

审批流程：

1. 创建 Issue：`Security Allowlist Approval` 模板。
2. 填写风险信息（来源、ID、文件、影响范围、到期日）。
3. 安全责任人 + 技术负责人双签（2人）。
4. 审批通过后，更新 `config/security/security_allowlist.txt`。
5. 关联修复计划与回收日期（必须）。

硬性规则：

- 不允许永久豁免；必须有到期复审日期。
- 无审批单不得修改 allowlist。

---

## 3) 发布放行签字（每次发布）

触发条件：

- 每次准备进入腾讯云生产发布窗口前。

放行流程：

1. 创建 Issue：`Release Signoff` 模板。
2. 填写版本、发布窗口、回滚方案、负责人。
3. 附上证据：
   - `CI=all` 运行链接
   - `Automated Tests=both` 运行链接
   - 安全报告与 `security-baseline-report.json`
4. 按 `.github/PRE_RELEASE_CHECKLIST.md` 逐项确认。
5. 产品/技术/运维签字后，才允许执行生产发布。

硬性规则：

- 任一 `P0` 未通过：禁止发布。
- 无签字单：禁止发布。

---

## 4) 责任分工（建议）

- 分支保护配置：仓库管理员
- 白名单审批：安全负责人 + 技术负责人
- 发布签字：发布经理 + 技术负责人 + 运维负责人

---

## 5) 关联资产

- `docs/deployment/BRANCH_PROTECTION_SETUP_CHECKLIST.md`
- `config/security/security_allowlist.txt`
- `.github/PRE_RELEASE_CHECKLIST.md`
- `docs/deployment/TENCENT_CLOUD_TESTING_CHECKLIST.md`
