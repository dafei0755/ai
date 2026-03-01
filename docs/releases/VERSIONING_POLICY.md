# 版本治理规范（v8 起）

## 目标

解决以下问题：
- 文档版本与实际运行版本不一致
- 多模块多版本混用导致沟通和回滚混乱
- 改动后漏更新版本，无法快速定位发布状态

## 单一事实来源（SSOT）

- 唯一产品版本源：仓库根目录 `VERSION`
- 格式要求：`MAJOR.MINOR.PATCH`（SemVer）
- 从 `v8.0.0` 开始统一采用 SemVer

## 对外与对内版本

- 对外版本（用户可见）：`product_version`（来自 `VERSION`）
- 对内版本（诊断可选）：`api_version`、`frontend_version`、`schema_version`
- 禁止仅使用无语义字段名 `version` 表达多种含义

## 发布与回滚规则

1. 稳定发布只允许 Git Tag：`vX.Y.Z`
2. 备份标记使用 `backup/*`，不得与发布 Tag 混用
3. 回滚目标必须是“上一稳定 Tag”，不得直接回滚到临时提交
4. 回滚必须附带数据库/配置兼容说明

## 自动校验

- 使用 `scripts/check_version_consistency.py` 校验：
  - `VERSION` 是合法 SemVer
  - 后端和包版本从 `PRODUCT_VERSION` 派生
  - `README.md` 版本徽章与当前版本展示与 `VERSION` 一致

## 历史版本兼容

- `v7.xxx` 保留为历史里程碑标识（legacy）
- 不再作为主发布版本参与新发布流程
