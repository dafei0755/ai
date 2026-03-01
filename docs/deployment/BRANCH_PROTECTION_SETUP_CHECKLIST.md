# Branch Protection 配置清单（GitHub）

> 说明：分支保护属于仓库设置项，不能通过代码仓库自动修改。请按本清单手工配置一次。

## 目标分支

- `main`

## 必开项（P0）

- [ ] Require a pull request before merging
- [ ] Require approvals（建议至少 1 个）
- [ ] Dismiss stale pull request approvals when new commits are pushed
- [ ] Require status checks to pass before merging
- [ ] Require branches to be up to date before merging
- [ ] Include administrators（管理员也受保护规则约束）

## 建议必选状态检查（P0）

- [ ] `CI / check-root-directory`
- [ ] `CI / backend-gate`
- [ ] `CI / frontend-tests`（前端改动场景）
- [ ] `Automated Tests / test-fast`
- [ ] `Automated Tests / lint`
- [ ] `Automated Tests / security`

## 可选状态检查（P1）

- [ ] `Automated Tests / test-matrix-full`（仅稳定期或发版前强制）
- [ ] `Automated Tests / flaky-isolated`（建议不设为阻断）

## 限制与权限（P0）

- [ ] Restrict who can push to matching branches（如有需要）
- [ ] Do not allow bypassing the above settings
- [ ] Do not allow force pushes
- [ ] Do not allow deletions

## 验证步骤

1. 创建测试 PR（包含后端变更）
2. 确认受保护分支要求状态检查全部出现且未通过前不可合并
3. 模拟失败检查，确认 PR 无法合并
4. 修复后确认可合并

## 维护建议

- 每次新增关键 workflow/job 后，评估是否加入 required checks。
- 每月复审一次保护规则，避免“新增门禁未纳入保护”。
