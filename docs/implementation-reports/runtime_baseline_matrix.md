# Runtime Baseline Matrix

基线判定原则：行为正确性优先于文件数量、版本号和整理程度。

| 维度 | 判定 | 当前文件数 | V7 文件数 | 仅当前 | 仅V7 | 内容差异 | 结论 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 前端深度思考链路 | `V7-better` | 7 | 7 | 0 | 0 | 1 | 锁定 V7 为运行基线，仅把当前版本中的单点 UI 修复作为候选增量逐项验证。 |
| 后端流程编排 | `V7-better` | 21 | 21 | 0 | 0 | 5 | 保留 V7 路由和主流程，后续只回收经过验证的非结构性入口增强。 |
| 算法 / Prompt / 规则配置 | `V7-better` | 173 | 173 | 0 | 0 | 16 | 以 V7 配置为基线，后续仅对样例配置和文档化配置做回收。 |
| 控制后台 | `V7-better` | 31 | 31 | 0 | 0 | 4 | 优先保留 V7 的可用链路，再逐页核查当前新增后台入口是否真正闭环。 |
| 爬虫与外部数据系统 | `V7-better` | 37 | 37 | 0 | 0 | 0 | 以 V7 的爬虫链路为运行基线，新增文件一律按模块闭环验证后再回收。 |
| 环境配置与依赖 | `Current-better` | 9 | 9 | 0 | 0 | 2 | 优先回收文档化配置和样例文件；任何会改运行时行为的配置必须在 V7 上单独验证。 |
| 数据库与迁移 | `Current-better` | 13 | 13 | 0 | 0 | 0 | 迁移脚本可优先审查；模型与服务层禁止整包覆盖回 V7。 |
| 文档与治理 | `Current-better` | 42 | 39 | 3 | 0 | 6 | 回收治理文档时必须剥离与当前主干行为不一致的版本叙述。 |

## 判定说明

### 前端深度思考链路
- 判定: `V7-better`
- 依据: 用户已确认 V7 更接近主动调试结果；analysis 页面与当前版本存在实质差异。
- 执行建议: 锁定 V7 为运行基线，仅把当前版本中的单点 UI 修复作为候选增量逐项验证。
- 差异摘要: 当前 7 个文件, V7 7 个文件, 仅当前 0, 仅V7 0, 内容差异 1

代表性差异文件:
- `frontend-nextjs/app/analysis/[sessionId]/page.tsx`

### 后端流程编排
- 判定: `V7-better`
- 依据: 核心 interaction 节点与 V7 一致，但 server.py 与入口层存在漂移，用户反馈当前行为已部分回旧。
- 执行建议: 保留 V7 路由和主流程，后续只回收经过验证的非结构性入口增强。
- 差异摘要: 当前 21 个文件, V7 21 个文件, 仅当前 0, 仅V7 0, 内容差异 5

代表性差异文件:
- `intelligent_project_analyzer/api/server.py`
- `intelligent_project_analyzer/interaction/nodes/analysis_review.py`
- `intelligent_project_analyzer/interaction/nodes/progressive_questionnaire.py`
- `intelligent_project_analyzer/interaction/nodes/quality_preflight.py`
- `intelligent_project_analyzer/workflow/main_workflow.py`

### 算法 / Prompt / 规则配置
- 判定: `V7-better`
- 依据: 这部分直接决定行为正确性；按用户反馈 V7 更接近主动调试，当前版本存在后续整理造成的偏移风险。
- 执行建议: 以 V7 配置为基线，后续仅对样例配置和文档化配置做回收。
- 差异摘要: 当前 173 个文件, V7 173 个文件, 仅当前 0, 仅V7 0, 内容差异 16

代表性差异文件:
- `intelligent_project_analyzer/config/deliverable_role_constraints.yaml`
- `intelligent_project_analyzer/config/prompts/core_task_decomposer.yaml`
- `intelligent_project_analyzer/config/prompts/dynamic_project_director_v2.yaml`
- `intelligent_project_analyzer/config/prompts/gap_question_generator.yaml`
- `intelligent_project_analyzer/config/prompts/radar_dimensions.yaml`
- `intelligent_project_analyzer/config/prompts/requirements_analyst_lite.yaml`
- `intelligent_project_analyzer/config/prompts/requirements_analyst_phase1.yaml`
- `intelligent_project_analyzer/config/prompts/requirements_analyst_phase2.yaml`

### 控制后台
- 判定: `V7-better`
- 依据: 当前版本存在更多后台页和路由，但用户明确表示 V7 的控制后台更接近真实调试状态。
- 执行建议: 优先保留 V7 的可用链路，再逐页核查当前新增后台入口是否真正闭环。
- 差异摘要: 当前 31 个文件, V7 31 个文件, 仅当前 0, 仅V7 0, 内容差异 4

代表性差异文件:
- `frontend-nextjs/app/admin/crawler-monitor/page.tsx`
- `frontend-nextjs/app/admin/layout.tsx`
- `intelligent_project_analyzer/api/routes/crawler_monitor_routes.py`
- `intelligent_project_analyzer/api/routes/dimension_feedback.py`

### 爬虫与外部数据系统
- 判定: `V7-better`
- 依据: 当前 external_data_system 文件数更多，但用户判断 V7 更完整；更可能是当前版本有未闭环扩张而非真正稳定增强。
- 执行建议: 以 V7 的爬虫链路为运行基线，新增文件一律按模块闭环验证后再回收。
- 差异摘要: 当前 37 个文件, V7 37 个文件, 仅当前 0, 仅V7 0, 内容差异 0

### 环境配置与依赖
- 判定: `Current-better`
- 依据: 当前版本保留了更多配置样例和治理文件，可作为非运行时增强候选池。
- 执行建议: 优先回收文档化配置和样例文件；任何会改运行时行为的配置必须在 V7 上单独验证。
- 差异摘要: 当前 9 个文件, V7 9 个文件, 仅当前 0, 仅V7 0, 内容差异 2

代表性差异文件:
- `frontend-nextjs/next-env.d.ts`
- `frontend-nextjs/tsconfig.json`

### 数据库与迁移
- 判定: `Current-better`
- 依据: 当前版本包含更多治理导向的迁移与版本规则文件，但不能直接替换运行时模型层。
- 执行建议: 迁移脚本可优先审查；模型与服务层禁止整包覆盖回 V7。
- 差异摘要: 当前 13 个文件, V7 13 个文件, 仅当前 0, 仅V7 0, 内容差异 0

### 文档与治理
- 判定: `Current-better`
- 依据: 当前版本存在额外的版本治理、流程校验和发布文档，但不应反推运行时代码归属。
- 执行建议: 回收治理文档时必须剥离与当前主干行为不一致的版本叙述。
- 差异摘要: 当前 42 个文件, V7 39 个文件, 仅当前 3, 仅V7 0, 内容差异 6

代表性差异文件:
- `.github/PRE_RELEASE_CHECKLIST.md`
- `.github/workflows/ci.yml`
- `CHANGELOG.md`
- `EMERGENCY_RECOVERY.md`
- `QUICKSTART.md`
- `README.md`

当前版本独有样本:
- `.github/workflows/tag-guard.yml`
- `docs/releases/VERSIONING_POLICY.md`
- `docs/releases/signoff/release_signoff_v8.0.0_2026-02-27.md`
