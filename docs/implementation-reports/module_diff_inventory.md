# Module Diff Inventory

本清单用于指导 `V7` 修复时的取舍, 先锁主链, 再按候选增量池回收。

## 已确认的核心差异

- `frontend-nextjs/app/analysis/[sessionId]/page.tsx`: 当前与 V7 哈希不同, 属于前端主链入口, 禁止整包回收。
- `intelligent_project_analyzer/api/server.py`: 当前与 V7 存在明显入口层差异, 包括路由注册、启动逻辑和版本注入。
- `intelligent_project_analyzer/settings.py`: 当前引入 `PRODUCT_VERSION`, 属于治理性增强, 但会触及运行时配置入口。
- `intelligent_project_analyzer/__init__.py`: 当前改为从 `versioning.py` 读取版本, 不是优先回收项。
- `intelligent_project_analyzer/interaction/nodes/output_intent_detection.py`: 当前与 V7 一致。
- `intelligent_project_analyzer/interaction/nodes/questionnaire_summary.py`: 当前与 V7 一致。

## 允许作为候选增量池审查的文件

- `.github/workflows/tag-guard.yml`: 当前存在=True, V7存在=False, 状态=可审查
- `docs/releases/VERSIONING_POLICY.md`: 当前存在=True, V7存在=False, 状态=可审查
- `scripts/check_version_consistency.py`: 当前存在=True, V7存在=False, 状态=可审查
- `scripts/check_tag_naming.py`: 当前存在=True, V7存在=False, 状态=可审查
- `scripts/rollback_to_tag.py`: 当前存在=True, V7存在=False, 状态=可审查
- `scripts/generate_release_signoff.py`: 当前存在=True, V7存在=False, 状态=可审查

## 需要人工复核后才能考虑回收的文件

- `VERSION`: 当前存在=True, V7存在=False
- `intelligent_project_analyzer/versioning.py`: 当前存在=True, V7存在=False
- `intelligent_project_analyzer/__init__.py`: 当前存在=True, V7存在=True
- `intelligent_project_analyzer/settings.py`: 当前存在=True, V7存在=True
- `intelligent_project_analyzer/api/server.py`: 当前存在=True, V7存在=True

## 禁止整包覆盖的目录

- `frontend-nextjs`
- `intelligent_project_analyzer/api`
- `intelligent_project_analyzer/services`
- `intelligent_project_analyzer/interaction`
- `intelligent_project_analyzer/config/prompts`
- `intelligent_project_analyzer/external_data_system`

## 分维度差异样本

### 前端深度思考链路
- 判定: `V7-better`
- 内容差异样本:
  - `frontend-nextjs/app/analysis/[sessionId]/page.tsx`
- 回收建议: 锁定 V7 为运行基线，仅把当前版本中的单点 UI 修复作为候选增量逐项验证。

### 后端流程编排
- 判定: `V7-better`
- 内容差异样本:
  - `intelligent_project_analyzer/api/server.py`
  - `intelligent_project_analyzer/interaction/nodes/analysis_review.py`
  - `intelligent_project_analyzer/interaction/nodes/progressive_questionnaire.py`
  - `intelligent_project_analyzer/interaction/nodes/quality_preflight.py`
  - `intelligent_project_analyzer/workflow/main_workflow.py`
- 回收建议: 保留 V7 路由和主流程，后续只回收经过验证的非结构性入口增强。

### 算法 / Prompt / 规则配置
- 判定: `V7-better`
- 内容差异样本:
  - `intelligent_project_analyzer/config/deliverable_role_constraints.yaml`
  - `intelligent_project_analyzer/config/prompts/core_task_decomposer.yaml`
  - `intelligent_project_analyzer/config/prompts/dynamic_project_director_v2.yaml`
  - `intelligent_project_analyzer/config/prompts/gap_question_generator.yaml`
  - `intelligent_project_analyzer/config/prompts/radar_dimensions.yaml`
  - `intelligent_project_analyzer/config/prompts/requirements_analyst_lite.yaml`
  - `intelligent_project_analyzer/config/prompts/requirements_analyst_phase1.yaml`
  - `intelligent_project_analyzer/config/prompts/requirements_analyst_phase2.yaml`
  - `intelligent_project_analyzer/config/prompts/result_aggregator.yaml`
  - `intelligent_project_analyzer/config/prompts/review_agents.yaml`
- 回收建议: 以 V7 配置为基线，后续仅对样例配置和文档化配置做回收。

### 控制后台
- 判定: `V7-better`
- 内容差异样本:
  - `frontend-nextjs/app/admin/crawler-monitor/page.tsx`
  - `frontend-nextjs/app/admin/layout.tsx`
  - `intelligent_project_analyzer/api/routes/crawler_monitor_routes.py`
  - `intelligent_project_analyzer/api/routes/dimension_feedback.py`
- 回收建议: 优先保留 V7 的可用链路，再逐页核查当前新增后台入口是否真正闭环。

### 爬虫与外部数据系统
- 判定: `V7-better`
- 回收建议: 以 V7 的爬虫链路为运行基线，新增文件一律按模块闭环验证后再回收。

### 环境配置与依赖
- 判定: `Current-better`
- 内容差异样本:
  - `frontend-nextjs/next-env.d.ts`
  - `frontend-nextjs/tsconfig.json`
- 回收建议: 优先回收文档化配置和样例文件；任何会改运行时行为的配置必须在 V7 上单独验证。

### 数据库与迁移
- 判定: `Current-better`
- 回收建议: 迁移脚本可优先审查；模型与服务层禁止整包覆盖回 V7。

### 文档与治理
- 判定: `Current-better`
- 内容差异样本:
  - `.github/PRE_RELEASE_CHECKLIST.md`
  - `.github/workflows/ci.yml`
  - `CHANGELOG.md`
  - `EMERGENCY_RECOVERY.md`
  - `QUICKSTART.md`
  - `README.md`
- 仅当前样本:
  - `.github/workflows/tag-guard.yml`
  - `docs/releases/VERSIONING_POLICY.md`
  - `docs/releases/signoff/release_signoff_v8.0.0_2026-02-27.md`
- 回收建议: 回收治理文档时必须剥离与当前主干行为不一致的版本叙述。
