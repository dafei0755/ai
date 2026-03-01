# 静态测试操作指南（系统化运行版）

## 1. 定位与结论

本项目的静态测试不是一次性动作，而是持续运行的质量门禁体系。
目标是把问题前置到开发和合并前，减少回归进入主干与发布环节。

---

## 2. 自动与手动的职责划分

### 自动执行（默认）

- `CI` 工作流（`.github/workflows/ci.yml`）
  - `push`/`pull_request` 自动触发（按路径分流）
  - `schedule` 每日 UTC 02:00 触发后端全量回归
  - 核心内容：根目录检查、后端 fast gate、前端构建、后端全量（按触发范围）
- `Automated Tests` 工作流（`.github/workflows/tests.yml`）
  - `push`/`pull_request` 自动触发（按路径分流）
  - `schedule` 每日 UTC 00:00 触发（含矩阵与安全扫描）
  - 核心内容：fast/full 测试、Ruff、Bandit/Safety、安全基线校验
- `Quality Trend Report`（`.github/workflows/quality-trend.yml`）
  - 每周一 UTC 01:30 自动生成趋势报告 artifact

### 手动执行（按场景）

- `workflow_dispatch` 手动触发指定范围：
  - `CI`: `gate_only` / `full_backend` / `all`
  - `Automated Tests`: `fast_only` / `full_matrix` / `both`
  - `run_flaky=true|false` 控制是否跑 flaky 隔离任务
- 发布前人工验收：
  - 参考 `.github/PRE_RELEASE_CHECKLIST.md`
- 风险治理人工决策：
  - 安全白名单：`config/security/security_allowlist.txt`
  - flaky 台账：`docs/testing/FLAKY_TESTS.md`

---

## 3. 实施节奏（时机与时间间隔）

1. 每次 PR/提交：自动跑 fast gate（静态检查与稳定回归子集）
2. 每天夜间：自动跑后端全量/矩阵/安全扫描
3. 每周：自动生成 CI 趋势报告，团队复盘失败率与时长
4. 每次发布前：手动触发全链路范围并执行发布清单

---

## 4. 如何操作（实操）

### 4.1 GitHub UI 手动触发

1. 进入仓库 `Actions`
2. 选择 `CI` 或 `Automated Tests`
3. 点击 `Run workflow`
4. 选分支与参数后执行

推荐参数：

- 快速验收：`CI=gate_only` + `Tests=fast_only, run_flaky=false`
- 后端回归：`CI=full_backend` + `Tests=full_matrix, run_flaky=false`
- 全链路验收：`CI=all` + `Tests=both, run_flaky=true`

### 4.2 本地静态体检（无 make 也可）

- 跨平台：`python scripts/ci/ci_doctor.py`
- Windows：`scripts\ci\ci_doctor.bat`

`ci_doctor` 会检查：

- workflow 关键字段是否齐全（触发、并发、关键 jobs）
- 覆盖率阈值是否符合当前策略（fast/full）
- 文档与配置是否一致（README/README_TESTING 与 workflow）

---

## 5. 职能边界

### 能做什么

- 尽早发现语法/规范/配置漂移问题
- 稳定拦截常见回归
- 前置发现依赖与安全风险
- 提供可量化的质量趋势

### 不能替代什么

- 不能替代真实业务场景下的动态行为验证
- 不能替代性能压测、容量压测和线上流量观测
- 不能自动替代风险审批（白名单与发布放行仍需人工）

---

## 6. 功效与收益

- 降低回归进入主干概率
- 降低无效 CI 成本（分流、并发取消、缓存）
- 缩短定位时间（分层门禁 + 标准化产物）
- 提升团队协作一致性（统一入口、统一阈值、统一验收）

---

## 7. 关联文件

- `.github/workflows/ci.yml`
- `.github/workflows/tests.yml`
- `.github/workflows/quality-trend.yml`
- `scripts/ci/ci_doctor.py`
- `.github/PRE_RELEASE_CHECKLIST.md`
- `docs/testing/FLAKY_TESTS.md`
- `config/security/security_allowlist.txt`
