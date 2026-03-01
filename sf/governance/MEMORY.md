# MEMORY — 跨会话治理知识库

> 精简索引，供 AI 辅助工具快速检索。更新时间：2026-03-01，基线版本：v8.0.0

---

## P0 问题（✅ 2026-03-01 已全部修复）

| 问题 | 精确位置 | 状态 |
|------|----------|------|
| `analysis_review` 死代码路由（QW-1） | `return "analysis_review"` 分支已从 `_route_after_challenge_detection` 删除 | ✅ 已修复 |
| `asyncio.gather` 无并发上限（QW-2） | `services/llm_concurrency.py` 新建；Semaphore 注入 `_execute_agent_with_semaphore` | ✅ 已修复 |
| `_route_after_analysis_review` 孤儿函数（QW-3） | 函数已删除，替换为单行说明注释 | ✅ 已修复 |

> 防止复发：`tests/structural/test_graph_structure.py` 包含 ADR-001 专项回归测试

---

## 节点废弃 5 步清单（防止再次遗漏）

废弃任意节点时，必须按顺序完成：
1. 注释掉 `workflow.add_node("node_name", ...)` 注册行
2. 删除所有路由函数中 `return "node_name"` 的分支
3. 删除对应 `_route_after_node_name` 孤立函数
4. 将节点相关状态字段标记 `# [DEPRECATED v版本号]`
5. 在 `CHANGELOG.md` 的 `[Unreleased]` 节记录废弃，指向对应 ADR

---

## 版本标记规范（v8 时代）

| 场景 | 处理方式 |
|------|----------|
| 架构变更 | 注释引用 ADR 编号，如 `# see ADR-001` |
| 功能变更 | 保留一行说明：`# 引入原因，v8.1.0` |
| Bug 修复 | 只在 CHANGELOG，代码中不留标记 |
| 旧 v7.xxx 标记 | CI 门禁禁止新增；存量逐步清理 |

---

## 脚本目录结构（ST-5 后）

```
scripts/
  ci/              # CI/CD 脚本（原有）
  crawl/           # 16 个爬虫相关脚本
  migration/       # 5 个数据库/迁移脚本
  debug/           # 4 个调试脚本
  verify/          # 7 个验证脚本
  analysis/        # 11 个分析/测试脚本
```

---

## 阶段 1 进展（v8.1.0，2026-03-01 全部完成）✅

| 任务 | 状态 | 说明 |
|------|------|------|
| ST-4 ruff 工具链激活 | ✅ | `ruff.toml` select + `Makefile` 迁移 + `mypy.ini` +services |
| ST-4 语法修复 | ✅ | `learning_scheduler.py` 孤立代码块删除（验证 exit 0） |
| ST-5 脚本归类 | ✅ | 43 个文件移至 `scripts/` 子目录，3 个删除，tasks.json 路径同步 |
| ST-1 DEPRECATED 字段清理 | ✅ | `state.py` 删除 4 字段；调用方替换为空默认值 |
| ST-2 版本开关删除 | ✅ | 3 个 flag + 全部条件分支删除；`USE_PROGRESSIVE_QUESTIONNAIRE=true` 内联 |
| ST-3 节点 Fallback 守卫 | ✅ | `node_guard.py` 新建；8 节点装饰；22 单元测试全通过 |
| MT-1 server.py 瘦身（第1轮） | 🔄 进行中 | 8509→1805 行（-78.8%）；提取 pdf_generator/models/helpers/image_routes/session_routes/monitoring_routes/analysis_routes |

## MT-1 路由提取已完成模块

**技术方案**：`_ServerProxy` 惰性代理模式（`__getattr__` 延迟 `import server`，避免循环导入）。

| 模块 | 包含端点 | 行数 |
|------|----------|------|
| `api/pdf_generator.py` | PDFGenerator, generate_report/all_experts | 1531 |
| `api/models.py` | 30 Pydantic BaseModel | 382 |
| `api/helpers.py` | _enrich_sections 等 7 工具函数 | 275 |
| `api/state.py` | session_manager, websocket_connections 等全局状态声明 | ~90 |
| `api/image_routes.py` | /api/analysis/*-image, /api/images/* (11 端点) | 1105 |
| `api/session_routes.py` | suggest-questions, /api/sessions/*, /api/conversation/* (16 端点) | 1076 |
| `api/monitoring_routes.py` | /, /health, /readiness, /api/user/*, /api/debug/* (14 端点) | 536 |
| `api/analysis_routes.py` | /api/analysis/start, start-with-files, resume, followup, result, report, download-pdf (10 端点) | 2165 |

**下一步**：server.py 已降至 1805 行。剩余：`run_workflow_async`（~540 行）+ WebSocket 端点 + lifespan 基础设施。可选：将 `run_workflow_async` + `broadcast_to_websockets` 提取至 `workflow_runner.py`；WebSocket 提取至 `ws_routes.py`。

**阶段 1（v8.1.0）已全部完成** ✅ → **阶段 2 MT-1 进行中**（server.py 8509→1805 行，-78.8%）

---



```python
review_result          # [DEPRECATED] 已被 role_quality_review_result 替代
final_ruling           # [DEPRECATED] 已废弃
improvement_suggestions # [DEPRECATED] 已废弃
skip_second_review     # [DEPRECATED] 已废弃
```

清理前必须：`grep -r "字段名" intelligent_project_analyzer/ --include="*.py"` 确认无活跃读取。

---

## ADR 一句话摘要

- **ADR-001**：废弃 `analysis_review` 节点——决策正确，但路由清理不彻底，留下 P0 死代码
- **ADR-002**：`asyncio.gather` 真并行——速度提升 67%，但无 Semaphore 上限（待 QW-2 修复）
- **ADR-003**：质量控制前置化——任务分派阶段即检测质量，减少专家白做
- **ADR-004**：问卷步骤 Step1→Step3→Step2——命名顺序不等于执行顺序
- **ADR-005**：VERSION 文件 SSOT + SemVer——应在 v7.0 就建立，越晚越贵
- **ADR-006**：问卷节点命名历史债——执行顺序 step1→step3→step2，命名与顺序相反；MT-6 里程碑执行原子重命名

---

## 关键文件快速定位

| 文件 | 状态 | 最关键位置 |
|------|------|------------|
| `workflow/main_workflow.py` | ST-1/ST-2 后约 2870 行 | L70 已删除版本开关；L1786 Semaphore 注入 |
| `core/state.py` | 658 行（4 字段已删）| DEPRECATED 字段 ✅ 已清除（ST-1）|
| `api/server.py` | 1805 行（原 8509）| MT-1 进行中：基础设施 + run_workflow_async + WebSocket |
| `api/pdf_generator.py` | 新建 1531 行 | MT-1: PDFGenerator 类 + PDF 生成函数 |
| `api/models.py` | 新建 382 行 | MT-1: 30 个 Pydantic BaseModel |
| `api/helpers.py` | 新建 275 行 | MT-1: 7 个纯报告工具函数 |
| `api/state.py` | 新建 ~90 行 | MT-1: 共享可变状态声明 |
| `api/image_routes.py` | 新建 1105 行 | MT-1: 图像端点（11 个） |
| `api/session_routes.py` | 新建 1076 行 | MT-1: 会话/对话/归档端点（16 个） |
| `api/monitoring_routes.py` | 新建 536 行 | MT-1: 健康检查/用户/调试端点（14 个） |
| `api/analysis_routes.py` | 新建 2165 行 | MT-1: 核心分析路由（start/resume/followup/result/report 等 10 个端点） |
| `services/llm_concurrency.py` | 新建 | QW-2 全局 Semaphore，`LLM_GLOBAL_CONCURRENCY` env 控制 |
| `workflow/node_guard.py` | 新建 | ST-3 节点 Fallback 守卫装饰器 |
| `tests/unit/test_node_guard.py` | 新建 | ST-3 单元测试，22/22 通过 |
| `tests/structural/test_graph_structure.py` | 新建 | ST-3a 图结构验证，8/8 通过 |
| `ruff.toml` | 已激活 `select=[E,W,F,I,UP,B]` | ST-4 |
| `mypy.ini` | files 追加 services 目录 | ST-4 |
| `Makefile` | lint/format 迁移至 ruff，新增 `type-check` | ST-4 |
| `scripts/` 子目录 | crawl/migration/debug/verify/analysis（43 文件） | ST-5 |
| `interaction/nodes/progressive_questionnaire.py` | 1553 行 | goto 路由：step1→step3→step2（ADR-006）|

---

## 版本治理速查

- **版本 SSOT**：根目录 `VERSION` 文件
- **版本格式**：SemVer，`MAJOR.MINOR.PATCH`
- **打 Tag**：`git tag v8.1.0 && git push origin v8.1.0`
- **回滚**：`git checkout v8.0.0 -- .`（仅文件），或 `git revert` 逐 commit
- **自动更新脚本**：`scripts/bump_version.py`（待建）
