# 可执行行动计划

**版本基线**：v8.0.0
**计划范围**：v8.0.0 → v8.1.0（阶段 0-1），v8.1.0 → v8.2.0（阶段 2），v8.2.0+（阶段 3）
**每项任务格式**：根因 → 方案 → 关键文件 → 验收标准 → 估算工时

---

## 依赖关系图

```
QW-1（删除死代码路由） → QW-3（删除孤立函数）
QW-2（Semaphore 并发控制） → ST-3（节点 Fallback 守卫） → LT-4（Circuit Breaker）
ST-1（清理 DEPRECATED 字段） → LT-3（State 字段精简）
ST-2（清除版本开关） → ST-4（规则链激活）
ST-5（脚本归类） ┐
ST-4（lint 激活）  ├→ MT-2（测试整理）
                   ↓
                 MT-1（server.py 拆分） → MT-4（WS 事件补偿）
```

---

## 阶段 0：P0 安全修复（< 2h，不破坏功能，随时可合并）

### QW-1：删除 `analysis_review` 死代码路由

| 项 | 内容 |
|----|------|
| **根因** | `requires_client_review` 路径路由到从未注册的节点，触发时 LangGraph 崩溃（ADR-001 废弃时路由未同步清理） |
| **关键文件** | `workflow/main_workflow.py` L2237-2243 |
| **操作** | 在 `_route_after_challenge_detection_node` 中：删除 `if state.get("requires_client_review"): return "analysis_review"` 分支；将该场景改路由到 `"manual_review"` |
| **验收标准** | 路由函数不再出现 `"analysis_review"` 字符串；`grep -r "analysis_review" workflow/` 只有注释行；`pytest tests/unit/ -k route` 全通过 |
| **工时估算** | 0.5h |
| **回滚方式** | `git revert` 单 commit |

### QW-2：添加 LLM 并发 Semaphore

| 项 | 内容 |
|----|------|
| **根因** | L1792 的 `asyncio.gather` 无并发上限，峰值 45+ 并发 HTTP 连接 |
| **关键文件** | 新建 `services/llm_concurrency.py`；修改 `workflow/main_workflow.py` L1787-1800 |
| **操作** | 新建 `LLMConcurrencyManager`，全局 `asyncio.Semaphore`，大小从 `LLM_GLOBAL_CONCURRENCY` 环境变量读取（默认 8）；在 `asyncio.gather` 前包裹 `async with concurrency_mgr.acquire(session_id, role_id):` |
| **注意** | Semaphore 必须是模块级单例，不能在每次函数调用内新建 |
| **验收标准** | `LLM_GLOBAL_CONCURRENCY=8` 生效；压测同时 20 会话，并发数不超过 8；`/api/metrics` 出现 `llm_active_calls` 指标 |
| **工时估算** | 1h |
| **回滚方式** | 删除 `llm_concurrency.py`，还原 L1792 调用，设 `LLM_GLOBAL_CONCURRENCY=999` 可临时绕过 |

### QW-3：删除孤立函数 `_route_after_analysis_review`

| 项 | 内容 |
|----|------|
| **根因** | 函数完整但对应节点永远不会被调度，是纯粹的死代码 |
| **依赖** | QW-1 完成后 |
| **关键文件** | `workflow/main_workflow.py` L2691 |
| **操作** | 直接删除整个函数定义 |
| **验收标准** | `grep "_route_after_analysis_review" intelligent_project_analyzer/` 无结果；mypy 检查通过 |
| **工时估算** | 0.25h |

---

## 阶段 1：P1 核心清理（v8.1.0 目标，约 3 天）

### ST-1：清理 4 个 DEPRECATED 状态字段

| 项 | 内容 |
|----|------|
| **根因** | `state.py` L317-320 的 4 个字段仍在 TypedDict 活跃定义中，每次实例化均分配内存 |
| **关键文件** | `core/state.py` L317-320 |
| **前置验证** | 依次执行：`grep -r "review_result" intelligent_project_analyzer/ --include="*.py" \| grep -v "role_quality_review_result" \| grep -v "DEPRECATED"`，确认每个字段无活跃读取者 |
| **操作** | 确认无活跃引用后，从 TypedDict 删除 4 个字段定义；从 `create_initial_state()` 删除对应初始化行 |
| **验收标准** | `grep -rn "review_result\b\|final_ruling\b\|improvement_suggestions\b\|skip_second_review\b" intelligent_project_analyzer/ --include="*.py"` 无活跃使用；mypy 通过；现有测试全量通过 |
| **工时估算** | 1h |
| **风险** | 若某处代码读取了这些字段但未被 grep 发现（动态字符串键访问），运行时会产生 KeyError；建议先运行全量测试确认 |

### ST-2：清除 3 个旧版本特性开关

| 项 | 内容 |
|----|------|
| **根因** | `USE_V716_AGENTS`（默认 false）和 `USE_V718_QUESTIONNAIRE_AGENT`（默认 false）守卫的代码路径在生产中永不执行，属于活死人代码 |
| **关键文件** | `workflow/main_workflow.py` L70-84（4 处 `USE_V716_AGENTS` 引用：L76, L1033, L2173, L2512） |
| **操作** | 删除 3 个 flag 定义（L70-84）；删除 `if USE_V716_AGENTS:` 和 `if USE_V718_QUESTIONNAIRE_AGENT:` 分支（保留 else 分支代码）；对 `USE_PROGRESSIVE_QUESTIONNAIRE`（默认 true）：直接内联 true 分支，删除 flag 和条件判断 |
| **验收标准** | `grep "USE_V716\|USE_V718\|USE_PROGRESSIVE" intelligent_project_analyzer/` 无结果；全量测试通过 |
| **工时估算** | 2h |
| **回滚方式** | git revert，高风险操作前建议打一个 pre-cleanup tag |

### ST-3：节点 Fallback 守卫装饰器

| 项 | 内容 |
|----|------|
| **根因** | 约 15 个节点函数无 try/except 保护；`asyncio.gather(return_exceptions=True)` 吞掉异常，失败专家被标记 `confidence: 0.0` 后静默继续，问题难以察觉 |
| **关键文件** | 新建 `workflow/node_guard.py`；修改 `workflow/main_workflow.py` 中无 try/except 的节点（约 15 处，含 `_calibration_questionnaire_node`、`_progressive_step1/2/3_node`、`_batch_router_node` 等） |
| **操作** | 实现 `@node_guard(fallback={...})` 装饰器：捕获 `asyncio.TimeoutError`/通用异常，必须重新抛出 `Interrupt`；返回 fallback dict（含 `errors` 字段供下游检测）；在所有无错误处理节点上应用 |
| **关键注意** | `Interrupt` 必须传播（不能被 except 吞掉），否则人工暂停恢复机制失效 |
| **验收标准** | `pytest tests/unit/test_node_guard.py` 通过；模拟 LLM 调用抛出异常，工作流能继续而非崩溃，`errors` 字段有记录 |
| **工时估算** | 1 天 |

### ST-4：激活 ruff 工具链，统一 lint/format

| 项 | 内容 |
|----|------|
| **根因** | `ruff.toml` 只有 4 行 ignore 规则，未启用任何 lint 规则；`Makefile` 仍引用 flake8/black/isort |
| **操作** | **ruff.toml**：启用规则 `select = ["E", "W", "F", "I", "UP", "B"]`；`line-length = 100`；`target-version = "py310"`；`exclude` 排除 `_archive/`, `backup/`, `docs/`。**Makefile**：`make lint` → `ruff check .`；`make format` → `ruff format .`；`make type-check` → `mypy ...`；新增 `make check` 串联三者。**mypy.ini**：`files` 追加 `intelligent_project_analyzer/services`（先用 `follow_imports = silent` 过渡） |
| **验收标准** | `make lint` 有输出（不是零报告）且不异常退出；`make format` 格式化成功；`make check` 全程可执行 |
| **工时估算** | 3h |
| **注意** | 首次 `ruff check` 可能报告大量问题，先统计数量，按模块分批修复，不要试图一次修完 |

### ST-5：根目录临时脚本归类

| 项 | 内容 |
|----|------|
| **根因** | 根目录 45 个 `_*.py` 临时脚本，工程纪律失守，git 历史被噪音稀释 |
| **操作** | 建立 `scripts/` 子目录（`crawl/`、`migration/`、`debug/`、`verify/`、`analysis/`）并迁移；直接删除明确一次性脚本（`_patch_temp.py`、`_patch_batch3_4.py`、`_patch_batch5.py`）；删除根目录 `nul`、`nul\`r\`nset` 异常文件；将 `services/ucppt_search_engine.py.backup_20260129_164818` 移出源码目录 |
| **验收标准** | `git ls-files -- '_*.py'` 返回空（根目录无 `_*.py` 提交）；`ls intelligent_project_analyzer/services/*.backup*` 无结果 |
| **工时估算** | 2h |

---

## 阶段 2：P2 结构改善（v8.2.0 目标，约 8 天）

### MT-1：`server.py` 按业务域拆分

| 项 | 内容 |
|----|------|
| **根因** | 8534 行单文件，启动/WebSocket/会话/上传/认证全混杂，任何修改都有全局副作用风险 |
| **目标结构** | 主文件仅保留 `include_router` 组装 + 应用启动，< 300 行 |
| **拆分方向** | 新建 `api/ws_manager.py`（WebSocket 生命周期）、`api/session_routes.py`（会话管理）、`api/file_routes.py`（文件上传）；现有 `api/routes/` 路由文件继续保留 |
| **操作原则** | 每次只提取一个业务域，提取后立即运行冒烟测试，不要批量重构 |
| **验收标准** | `server.py` < 500 行；所有 API 端点行为不变（`_smoke_v14.py` 通过）；WebSocket 连接正常 |
| **工时估算** | 3 天 |
| **风险** | 高——任何路由注册顺序或 middleware 挂载顺序变化都可能影响行为；必须有完整冒烟测试覆盖 |

### MT-2：测试目录整理 ✅ DONE

| 项 | 内容 |
|----|------|
| **根因** | tests/ 根层 80+ 文件平铺，无法映射被测模块 |
| **操作** | 扫描每个测试文件的 `import` 路径确定被测模块；按模块归入 `tests/services/`、`tests/api/`、`tests/workflow/`、`tests/agents/` 等子目录；修复 `pytest.ini`：`norecursedirs` 追加 `_archive scripts backup` |
| **验收标准** | `pytest tests/` 无 collection error；`tests/` 根层文件 < 5 个（只保留 `conftest.py` 等） |
| **完成情况** | 96 个文件迁移至对应子目录；pytest.ini norecursedirs 补全；2111 tests collected 0 errors（排除预先存在的 intelligence/ 6 个 ImportError）；新增 `_build_problem_solving_approach`、`_weighted_info_status_vote`、`_build_decision_reason` 三个缺失私有函数 |
| **工时估算** | 1 天 |

### MT-3：State 大字段外部化 ✅ DONE

| 项 | 内容 |
|----|------|
| **根因** | `conversation_history` 使用 `add_messages` reducer 无限增长，每次 checkpoint 全量序列化，长会话性能持续退化 |
| **关键文件** | 新建 `services/external_state_store.py`；修改 `core/state.py`（相关字段改为有界 reducer） |
| **外部化字段** | `conversation_history`、`interaction_history`（`agent_results` 340处用法保留原语义）|
| **操作** | `ExternalStateStore` 支持内存（默认）+ Redis（REDIS_URL 环境变量）；`conversation_history` 改用 `_bounded_add_messages`（MAX=100，可配）；`interaction_history` 改用 `_bounded_merge_lists`（MAX=50，可配）；新增 `conversation_history_ref`/`interaction_history_ref` Optional[str] 字段供 Phase 2 使用 |
| **验收标准** | benchmark：200 轮时 checkpoint 节省 74.6% ≥ 50% ✅；26/26 单元测试通过 ✅ |
| **工时估算** | 2 天 |
| **风险** | 中——改变了 State 字段语义，所有读取这些字段的代码都需要更新；需要完整的读写测试覆盖 |
| **完成情况** | `services/external_state_store.py`（_MemoryBackend + _RedisBackend + 全局单例）；`core/state.py`（有界 reducer + ref 字段 + create_initial_state 更新）；`scripts/benchmark_checkpoint_size.py`；`tests/unit/services/test_external_state_store.py`（26 tests）|

### MT-4：WebSocket 事件补偿（断线重连）✅ DONE

| 项 | 内容 |
|----|------|
| **根因** | WebSocket 重连后无状态补偿，中间事件丢失，用户看到不完整的分析过程 |
| **关键文件** | 新建 `services/event_store.py`；新建 `frontend-nextjs/lib/reliable-ws.ts`；修改 `api/workflow_runner.py`（broadcast 钩子）；新增 API `GET /api/analysis/events/{session_id}?after_seq={n}` |
| **验收标准** | 19/19 e2e 测试通过 ✅；broadcast_to_websockets 写入 EventStore 已验证 |
| **工时估算** | 2 天 |
| **完成情况** | `services/event_store.py`（_MemoryEventBackend + _RedisEventBackend + 全局单例，asyncio.Lock 安全）；`workflow_runner.py` 在 broadcast 入口透明写入 EventStore；`analysis_routes.py` 末尾新增 GET /api/analysis/events/{session_id} 端点；`frontend-nextjs/lib/reliable-ws.ts`（指数退避重连 + 断线补偿）；`tests/e2e/test_ws_reconnect.py`（19 tests）|

### MT-5：语义变更感知检测器（替代字符计数路由）✅ DONE

| 项 | 内容 |
|----|------|
| **背景** | 当前问卷流程缺少用户修改意图识别，无法区分"改颜色"（局部）与"改客厅为卧室"（结构性）的回溯层次 |
| **关键文件** | 新建 `services/change_intent_detector.py`；挂入 `interaction/nodes/progressive_questionnaire.py` 的 `questionnaire_summary` 路由逻辑 |
| **实现方案（第一版）** | 关键词词表匹配，不引入 LLM 调用。三种结论：`VISUAL_ONLY`（仅重跑专家任务）/ `SPATIAL_ZONE`（强制重跑阶段1）/ `IDENTITY_PATTERN`（强制重跑阶段1） |
| **词表文件** | `config/spatial_semantic_keywords.json`（空间类型词）、`config/identity_pattern_keywords.json`（身份模式词） |
| **三类判定规则** | 空间类型词命中（客厅/卧室/厨卫/书房 等）→ SPATIAL_ZONE；身份/生活方式词命中（独居/养老/电竞/无障碍 等）→ IDENTITY_PATTERN；否则 → VISUAL_ONLY |
| **验收标准** | `pytest tests/unit/services/test_change_intent_detector.py` 通过（含 10 组典型用例：颜色/材质/功能变更/身份变更等）；路由热路径延迟增加 < 5ms |
| **完成情况** | 19/19 tests passed（含 TC-01~TC-10 + 性能测试 < 5ms）；`change_intent_detector.py` 实现 lru_cache 词表加载；在 `progressive_questionnaire.py` Step 1 挂入 `modified_input` 检测钩子；`spatial_semantic_keywords.json`（57词）/ `identity_pattern_keywords.json`（67词） |
| **工时估算** | 3 天 |
| **后续升级路径** | 词表版稳定后升级为 Embedding 余弦相似度（LT-5，不改接口） |
| **风险** | 低——纯同步函数，不依赖外部服务 |

### MT-6：问卷节点原子重命名（消除 Step1→Step3→Step2 命名债）✅ DONE

| 项 | 内容 |
|----|------|
| **背景** | 见 ADR-006——节点执行顺序为 step1→step3→step2，命名与顺序相反，对维护者极具误导性 |
| **目标状态** | 节点名与业务语义一致：`step1_core_task`（保留）→ `step2_info_gather`（原 step3）→ `step3_radar`（原 step2）|
| **影响文件** | `main_workflow.py` add_node；`progressive_questionnaire.py` goto 字符串；`api/server.py` WebSocket 事件节点名；`frontend-nextjs/` 前端进度节点引用；checkpoint 迁移脚本 |
| **执行前提** | MT-1（server.py 拆分）完成；所有关键测试通过；编写并验证 checkpoint 迁移脚本 |
| **验收标准** | 全量测试通过；`grep -r "progressive_step[23]" --include="*.py" --include="*.ts"` 无结果；`tests/structural/test_graph_structure.py` 通过 |
| **工时估算** | 2 天（含迁移脚本）|
| **风险** | 高——任意遗漏导致运行时 KeyError；必须独立 PR + 全量 CI 通过后合并 |
| **参考** | `sf/governance/adr/ADR-006-questionnaire-step-naming-debt.md` |
| **完成情况** | 11 文件更新（`_mt6_rename_nodes.py` 三阶段交换迁移）；7 处测试断言更新（step3_radar 在 v7.146 已改为直接路由 questionnaire_summary）；旧节点名 0 残留；9 个预先存在的失败（env var 开关/method 返回值，与重命名无关）|

---

## 阶段 3：P3 长期架构（下 Sprint 计划）

### LT-1：`main_workflow.py` 渐进拆分 ✅ DONE

- **目标**：2911 行 → ~300 行（只保留图构建 `add_node`/`add_edge` 和依赖注入）
- **目标结构**：
  ```
  workflow/
  ├── main_workflow.py       # 378 行（图组装 + 依赖注入 + Mixin 继承）
  └── nodes/
      ├── __init__.py         # 包入口 + __all__
      ├── security_nodes.py   # SecurityNodesMixin (197 行)
      ├── requirements_nodes.py # RequirementsNodesMixin (327 行)
      ├── planning_nodes.py   # PlanningNodesMixin (540 行)
      ├── execution_nodes.py  # ExecutionNodesMixin (821 行)
      └── aggregation_nodes.py # AggregationNodesMixin (1052 行)
  ```
- **工时**：5 天；**风险**：中（需全量测试覆盖）
- **完成情况**：
  - `_lt1_split_workflow.py` AST 提取脚本：自动识别 43 个方法、分组到 5 个 Mixin 文件
  - 5 个 Mixin 文件生成并通过语法检查（`py_compile` 全部 OK）
  - `main_workflow.py` 从 2911 行缩减至 378 行（节省 ~87%）
  - `MainWorkflow` 继承 5 个 Mixin：`SecurityNodesMixin, RequirementsNodesMixin, PlanningNodesMixin, ExecutionNodesMixin, AggregationNodesMixin`
  - `workflow/nodes/__init__.py` 新建，统一导出 5 个 Mixin 类
  - 相对 import 层级自动从 `..` 调整为 `...`（Mixin 文件位于更深一级）
  - `if TYPE_CHECKING:` 块正确迁移，indented import 不丢失
  - 47/48 测试通过（1 个 FallbackLLM 集成失败为先前存在问题）

### LT-2：`services/` 建立二级子包 ✅ DONE

- **目标**：90+ 文件平铺 → `session/`、`search/`、`llm/`、`dimension/`、`integration/` 子分组
- **策略**：各子目录 `__init__.py` 重导出公开 API，顶层 `services/__init__.py` 向后兼容，不强制更新所有 import
- **工时**：3 天；**风险**：低（向后兼容导出）
- **完成情况**：
  - `services/llm/__init__.py` 新建：re-export CircuitBreaker、LLMFactory、MultiLLMFactory、RateLimitedLLM、KeyBalancer、SemanticCache、HighConcurrencyLLM 等（13 个符号）
  - `services/session/__init__.py` 新建：re-export ExternalStateStore、EventStore、UserSessionManager、RedisSessionManager、QuotaManager 等（14 个符号）
  - `services/search/__init__.py` 新建：re-export SearchOrchestrator、BochaAISearch、UcpptSearchEngine、WebContentExtractor 等（11 个符号）
  - `services/dimension/__init__.py` 新建：re-export RadarDimensionOrchestrator、ProjectSpecificDimensionGenerator、get_dimensions_config 等（15 个符号）
  - `services/integration/__init__.py` 新建：re-export OntologyService、ImageGenerator、ProjectTypeDetector、ChangeIntentDetector 等（14 个符号）
  - `services/__init__.py` 更新：保留向后兼容的 `LLMFactory`、`ToolFactory` 导出；子包采用懒加载策略（用户需主动 import）
  - 所有旧导入路径**继续有效**，93 个现有测试零回归

### LT-3：State 字段精简

- **目标**：完成 ST-1 后进一步精简，统一问卷字段命名（三字段 `calibration_answers`/`questionnaire_responses`/`gap_filling_answers` 合并）
- **工时**：3 天；**风险**：高（破坏性变更，需全量回归）

### LT-4：Circuit Breaker ✅ DONE

- **目标**：每个 LLM 提供商一个 Circuit Breaker 实例（CLOSED→OPEN 5次失败→HALF_OPEN 60s→CLOSED 2次成功）
- **依赖**：QW-2（Semaphore）和 ST-3（节点守卫）完成后
- **工时**：3 天；**风险**：中
- **完成情况**：
  - `services/circuit_breaker.py` 新建（280 行）：`CircuitBreaker` 状态机 + `get_breaker()` 注册表单例 + `reset_registry()` 测试工具 + `all_stats()` 监控快照
  - `services/multi_llm_factory.py` 集成：`FallbackLLM.invoke()` 在每个提供商调用前通过 `get_breaker(provider).call(...)` 包装；CB OPEN 时跳过该提供商继续降级
  - `services/rate_limited_llm.py` 集成：`invoke()` 使用 `CircuitBreaker.call()`，`ainvoke()` 手动包装（异步路径）
  - `tests/unit/services/test_circuit_breaker.py` 新建：29 测试全部通过（10 个测试类，覆盖完整状态迁移、注册表、环境变量配置、FallbackLLM 集成）
  - 环境变量：`CB_FAILURE_THRESHOLD`（默认 5）、`CB_RECOVERY_TIMEOUT`（默认 60s）、`CB_SUCCESS_THRESHOLD`（默认 2）

---

## 验证脚本快速参考

```bash
# 阶段 0 验证
grep -r "analysis_review" intelligent_project_analyzer/workflow/ --include="*.py"   # 应无路由返回值
pytest tests/unit/ -k "route" -v
curl http://localhost:8000/api/metrics | python -m json.tool | grep llm_concurrency

# 阶段 1 验证
make check    # ruff + mypy + pytest
grep -rn "USE_V716\|USE_V718\|USE_PROGRESSIVE" intelligent_project_analyzer/ --include="*.py"  # 应无结果
git ls-files -- '_*.py'  # 应无根目录临时脚本

# 阶段 2 验证
wc -l intelligent_project_analyzer/api/server.py  # 应 < 500
pytest tests/ -v --timeout=300
python scripts/benchmark_checkpoint_size.py  # checkpoint 大小对比

# 阶段 3 验证
pytest tests/ -v --cov=intelligent_project_analyzer --cov-report=term-missing
```
