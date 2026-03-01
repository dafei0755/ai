# 系统治理现状报告（体检报告）

**项目**：Intelligent Project Analyzer
**版本基线**：v8.0.0
**调研时间**：2026-02-28
**调研方式**：代码层面只读审计，所有问题均有代码行号佐证

---

## 执行摘要

### 系统健康评分

| 级别 | 数量 | 含义 |
|------|------|------|
| **P0** | 2 | 已知高概率触发崩溃，必须在下一次迭代前修复 |
| **P1** | 6 | 已影响可维护性，应在 v8.1.0 内处理完 |
| **P2** | 4 | 结构性债务，计划性处理 |
| **P3** | 2 | 长期优化，不阻塞迭代 |

### 技术债务总量估算

| 阶段 | 任务 | 估算工时 |
|------|------|----------|
| 阶段 0（P0 修复） | 3 项快速修复 | 1.75h |
| 阶段 1（P1 清理） | 5 项核心清理 | ~3 天 |
| 阶段 2（P2 改善） | 4 项结构改善 | ~8 天 |
| 阶段 3（P3 长期） | 4 项架构优化 | ~14 天 |
| **合计** | | **约 20-26 人天** |

---

## 第一章：架构现状快照

### 1.1 技术栈

| 层级 | 技术 | 选型评价 |
|------|------|----------|
| 工作流编排 | LangGraph 0.2.57+ | ✅ 选型正确，状态机 + checkpoint 是正确方向 |
| Web 框架 | FastAPI 0.115+ | ✅ 合适 |
| 前端 | Next.js 14 App Router | ✅ 合适（注：package.json 版本 14.2.5，README 徽章写的 15，不一致） |
| 持久化 | SQLite（LangGraph checkpoint）+ Redis（会话缓存） | ⚠️ SQLite 是否满足生产规模待评估 |
| 监控 | Grafana + Loki + Prometheus + Loguru | ✅ 生产级可观测性 |
| 旧前端 | Streamlit（`intelligent_project_analyzer/frontend/`） | ❌ 已被 Next.js 替代，未清理 |

### 1.2 工作流拓扑

- **总节点数**：35+ 个（含注释掉的节点）
- **实际注册节点**：约 32 个（`analysis_review` 节点已注释，见下方）
- **主文件规模**：`workflow/main_workflow.py` 2911 行

### 1.3 节点可达性分析

| 节点 | 状态 | 位置 | 根因 |
|------|------|------|------|
| `analysis_review` | ❌ **不可达**（节点已注释，路由仍存在） | `main_workflow.py` L229：注释掉的 `add_node` | ADR-001 废弃决策，但路由函数未同步清理 |
| `user_question` | ⚠️ 触发路径受限 | `pdf_generator` 后硬编码 END | 编排设计问题 |

**P0 死代码确认**：

```python
# main_workflow.py L2237-2243 （_route_after_challenge_detection_node 内）
if state.get("requires_client_review"):
    return "analysis_review"   # ← L2242: 路由到从未注册的节点
```

```python
# main_workflow.py L229（节点注册已注释）
# workflow.add_node("analysis_review", self._analysis_review_node)
```

触发条件：`requires_client_review == True`。触发后果：LangGraph `NodeNotFoundError` 崩溃。

### 1.4 关键文件规模

| 文件 | 实测行数 | 问题 |
|------|----------|------|
| `intelligent_project_analyzer/api/server.py` | ~8534 行 | 启动/WebSocket/会话/上传/认证全混杂，反模式极端案例 |
| `intelligent_project_analyzer/workflow/main_workflow.py` | 2911 行 | 节点定义 + 路由逻辑 + 状态方法共存 |
| `intelligent_project_analyzer/core/state.py` | 662 行 | 含 4 个 DEPRECATED 字段未清理 |
| `intelligent_project_analyzer/services/`（目录） | 90+ 文件平铺 | 无二级分组，职责边界模糊 |

---

## 第二章：技术债务清单

### P0：必须立即修复（已知崩溃风险）

> **✅ 2026-03-01 全部修复完成**

#### P0-1：`analysis_review` 死代码路由 — ✅ 已修复

- **位置**：`workflow/main_workflow.py`（原 L2242，已删除）
- **修复**：QW-1 删除 `return "analysis_review"` 分支；QW-3 删除 `_route_after_analysis_review` 孤立函数
- **防止复发**：`tests/structural/test_graph_structure.py` 包含 ADR-001 回归测试

#### P0-2：`asyncio.gather` 无并发上限 — ✅ 已修复

- **位置**：`workflow/main_workflow.py`（原 L1792）
- **修复**：QW-2 新建 `services/llm_concurrency.py`（全局 Semaphore），默认 8；注入 `_execute_agent_with_semaphore`
- **控制参数**：`LLM_GLOBAL_CONCURRENCY` 环境变量

---

### P1：应在 v8.1.0 内处理

#### P1-1：`_route_after_analysis_review` 孤立函数 — ✅ 已修复（QW-3）

- **位置**：`workflow/main_workflow.py`（原 L2691，已删除）
- **修复**：函数已删除，替换为单行说明注释

#### P1-2：4 个 DEPRECATED 状态字段 — ✅ 已修复（ST-1，2026-03-01）

- **修复**：`state.py` 删除 4 个字段定义及 `create_initial_state()` 初始化行
- **调用方清理**：`manual_review.py` 和 `result_aggregator.py` 中读取替换为确定空默认値；删除两处 `skip_second_review=True` 写入

#### P1-3：3 个旧版本特性开关（活死人代码） — ✅ 已修复（ST-2，2026-03-01）

- **修复**：删除 3 个 flag 定义（L72-86）及全部条件分支；内联 `USE_PROGRESSIVE_QUESTIONNAIRE=true` 分支；保留 `USE_MULTI_ROUND_QUESTIONNAIRE` 参考注释
- **安全保护**：`git tag pre-st2-cleanup` 打完后执行；flag 活跃代码引用全部清零验证
- **结构测试**：8/8 全通过 ✅

#### P1-3b：~15 个节点无 Fallback 保护 — ✅ 已修复（ST-3，2026-03-01）

- **问题**：`asyncio.gather(return_exceptions=True)` 吸掉异常；`_calibration_questionnaire_node`、`_progressive_step1/2/3_node`、`_questionnaire_summary_node`、`_output_intent_detection_node`、`_manual_review_node`、`_user_question_node` 共 8 个节点无 try/except
- **修复**：新建 `workflow/node_guard.py`，实现 `@node_guard(fallback={...})` 装饰器；`GraphInterrupt` 必须重新抛出（不能被吸掉）；其他异常返回 fallback dict，`errors` 字段供下游检测
- **测试**：`tests/unit/test_node_guard.py`，22/22 通过 ✅
- **节点装饰**：28 个节点 0 个无保护 ✅

#### P1-4：`server.py` 单文件 8534 行 — 🚧 MT-1 进行中（2026-03-01）

- **位置**：`intelligent_project_analyzer/api/server.py`
- **问题**：启动、WebSocket 生命周期、会话管理、文件上传、认证全部混杂。任何修改都有引发全局副作用的风险。虽然 `routes/` 子目录已开始拆分，但执行不彻底
- **进度**：8509 → **1805 行**（**-6704 行，-78.8%**）；已提取：
  - `api/pdf_generator.py`（1531 行，PDFGenerator + PDF 生成函数）
  - `api/models.py`（382 行，30 个 Pydantic BaseModel）
  - `api/helpers.py`（275 行，7 个纯报告工具函数）
  - `api/state.py`（~90 行，共享可变状态声明）
  - `api/image_routes.py`（1105 行，图像生成/管理 11 个端点）
  - `api/session_routes.py`（1076 行，会话/对话/归档 16 个端点）
  - `api/monitoring_routes.py`（536 行，健康检查/用户/调试 14 个端点）
  - `api/analysis_routes.py`（2165 行，核心分析 10 个端点：start/resume/followup/result/report/download-pdf）
- **剩余**：server.py 1805 行（基础设施 + `run_workflow_async` + WebSocket 端点 + lifespan）
- **方案**：路由模块用 `_ServerProxy` 惰性代理访问 `session_manager` 等全局状态（避免循环导入）
- **测试**：30/30 结构+单元测试全通过 ✅
- **修复工时**：3 天（MT-1）

#### P1-5：`ruff.toml` 形同虚设 — ✅ 已修复（ST-4，2026-03-01）

- **修复**：`ruff.toml` 新增 `select = ["E","W","F","I","UP","B"]`，`line-length = 100`，`target-version = "py310"`；`Makefile` 迁移到 `ruff check`/`ruff format`
- **发现附带问题**：`services/learning_scheduler.py` 存在语法错误（孤立代码块）——已一并修复
- **剩余**：2739 个 lint 问题（主要 UP045/F401），需按模块分批修复

#### P1-6：`mypy` 覆盖范围仅 2 个目录 — ✅ 已扩展（ST-4，2026-03-01）

- **修复**：`mypy.ini` `files` 追加 `intelligent_project_analyzer/services`

---

### P2：计划性处理

#### P2-1：根目录 45 个 `_*.py` 临时脚本 — ✅ 已完成（ST-5，2026-03-01）

- **修复**：建立 `scripts/` 子目录（`crawl/`、`migration/`、`debug/`、`verify/`、`analysis/`）；43 个脚本归类迁移，3 个一次性 patch 脚本删除；`services/*.backup*` 移到 `backup/` 目录；`tasks.json` 路径引用同步更新

#### P2-2：`tests/` 根层 80+ 文件平铺

- **问题**：约 80 个测试文件直接平铺在 `tests/` 根目录，与已有 `tests/services/`、`tests/agents/` 等子目录混用
- **影响**：无法清晰映射被测模块，测试覆盖情况不可见
- **修复工时**：1 天（MT-2）

#### P2-3：测试覆盖率仅 11%

- **状态**：Phase 5 目标已从 20-25% 下调至 14%，说明测试债务在主动妥协而非偿还
- **最危险**：`services/` 90+ 文件几乎无单元测试覆盖，任何重构都是盲目操作
- **修复工时**：持续（prioritize services/ 核心服务）

#### P2-4：State 大字段无限增长

- **位置**：`core/state.py`，`conversation_history` 使用 `add_messages` reducer 无限增长
- **问题**：每次 checkpoint 全量序列化，随会话延长性能持续下降
- **建议**：外部化到 Redis，State 中只保留 ref_key
- **修复工时**：2 天（MT-3）

---

### P3：长期架构优化

#### P3-1：`main_workflow.py` 拆分

- **目标**：2911 行 → 约 300 行（只做图组装）
- **方向**：按工作流阶段分拆到 `workflow/nodes/` 和 `workflow/routers/`
- **修复工时**：5 天（LT-1）

#### P3-2：`services/` 建立二级子包

- **目标**：90+ 文件平铺 → `session/`、`search/`、`llm/`、`dimension/`、`integration/` 子分组
- **修复工时**：3 天（LT-2）

---

## 第三章：版本治理现状

### 3.1 SSOT 机制

- **状态**：✅ 已建立，`VERSION` 文件为唯一版本源，v8.0.0 起采用 SemVer
- **有效性**：有效，但缺少配套的 `bump_version.py` 自动化脚本

### 3.2 旧版本标记遗留

- **`v7.xxx` 标记数量**：整个 `intelligent_project_analyzer/` 包内保守估计 **500+ 处**
- **问题**：大量注释仍是 `# v7.xxx 修改...`，形成认知噪音，误导维护者
- **特性开关**：`USE_V716_AGENTS`（默认 false）、`USE_V718_QUESTIONNAIRE_AGENT`（默认 false）守卫的代码在生产中永不执行

---

## 第四章：质量控制架构

### 4.1 三层质量控制现状

| 层级 | 节点 | 状态 |
|------|------|------|
| 输入验证 | `security_check_node` | ✅ 正常 |
| 任务分派审核 | `role_task_unified_review` | ✅ 正常（ADR-003 前置化结果） |
| 挑战检测 | `challenge_detection_node` | ⚠️ 路由到 `analysis_review`（P0 死代码） |

### 4.2 已废弃审核节点的遗留影响

- `analysis_review` 节点逻辑：质量审核前置化（ADR-003）后，该后置节点理论上已无必要
- 但路由函数仍保留了进入该节点的路径，形成 P0 风险

---

## 第五章：风险矩阵

| 风险 | 触发概率 | 触发影响 | 优先级 |
|------|----------|----------|--------|
| `analysis_review` 路由触发 | 低（需 `requires_client_review=True`） | 极高（运行时崩溃，会话丢失） | **P0** |
| 高并发无 Semaphore 限制 | 高（任意多用户并发） | 高（LLM 限流 + 超时） | **P0** |
| DEPRECATED 字段被误用于新逻辑 | 中 | 中（状态字段错误，难排查） | P1 |
| v7.xxx 标记误导维护者 | 高 | 低（理解错误，无功能影响） | P1 |
| server.py 全局副作用 | 中（每次修改） | 高（难以隔离影响范围） | P1 |
| services/ 无界依赖导致循环 import | 低（当前尚未发生） | 高（运行时 ImportError） | P2 |
| State 无限增长导致 checkpoint OOM | 中（长会话） | 中（性能退化） | P2 |

---

## 附录：已验证的积极架构决策

以下架构决策是正确的，不需要修改：

1. **LangGraph Send API + SqliteSaver**：状态机 + checkpoint 是 LLM 工作流的正确模式
2. **`asyncio.gather` 真并行**（ADR-002）：已验证 67% 速度提升
3. **质量控制前置化**（ADR-003）：合并 `role_selection_quality_review` 到 `role_task_unified_review`
4. **双道安全校验**（输入 + 输出）：安全层独立成模块 `security/`
5. **外部数据子系统独立**：`external_data_system/` 独立解耦，含自洽的 spiders/tasks/api/models
6. **生产级监控**：Grafana + Loki + Prometheus 体系完整
