# 2026-06-12 工作树安全整理报告

## 结论

当前工作树不适合直接清理、直接提交或直接回滚。本报告采集时，`git status --short` 共有 594 行；生成本报告后，工作树会额外增加本报告文件本身。

| 状态 | 数量 | 含义 |
|---|---:|---|
| `??` | 380 | 未跟踪文件或目录 |
| `M` | 107 | 已跟踪文件被修改 |
| `D` | 107 | 已跟踪文件被删除 |

安全原则：

1. 不执行 `git add .`。
2. 不执行 `git clean -fd`。
3. 不执行 `git reset --hard`。
4. 删除项先不处理，必须逐项确认。
5. 先按功能分批收敛，再决定提交、归档或忽略。

## 分组总览

| 分组 | 数量 | 处理建议 |
|---|---:|---|
| 保留并代码复核 | 166 | 逐模块检查、分批测试、分批提交 |
| 保留并文档复核 | 22 | 与 README / QUICKSTART / 架构文档一起归档提交 |
| 保留并测试复核 | 77 | 跟随对应功能提交，不单独大批量提交 |
| 归档或忽略 | 170 | 优先进入 `.gitignore` 或 `_archive/`，不入主提交 |
| 资料库人工确认 | 19 | `sf/` 新增或修改内容，必须人工确认价值和来源 |
| 其他人工确认 | 33 | 环境样例、根目录文档、临时目录等，逐项确认 |
| 高风险删除 | 107 | 暂停处理，确认是否主动删除或误删 |

以上分组数量合计 594，覆盖当前全部工作树状态。

## 保留并代码复核

数量：166。

主要范围：

- `intelligent_project_analyzer/`
- `frontend-nextjs/`
- 管理后台页面
- 方案高参入口服务
- 空间分类、知识治理、context packet、诚实边界、数据库治理相关服务

代表文件：

- `intelligent_project_analyzer/services/honesty_boundary_service.py`
- `intelligent_project_analyzer/config/honesty_boundary_policy.yaml`
- `intelligent_project_analyzer/services/scheme_advisor_context_intelligence.py`
- `intelligent_project_analyzer/services/scheme_advisor_entry_service.py`
- `intelligent_project_analyzer/api/admin_routes.py`
- `intelligent_project_analyzer/api/server.py`
- `frontend-nextjs/app/admin/layout.tsx`
- `frontend-nextjs/app/admin/knowledge-base/page.tsx`
- `frontend-nextjs/app/admin/space-classification/`
- `frontend-nextjs/app/admin/review-queue/`

建议拆分提交：

1. 管理后台治理页面和导航清理。
2. 空间分类 / 本体论 / 子域 / 激活包 / 知识包运行链路。
3. 方案高参入口体验和诚实边界。
4. 数据库和多用户空间治理。
5. Geo / quick notes / cockpit 等非核心链路。

## 保留并文档复核

数量：22。

主要范围：

- `README.md`
- `QUICKSTART.md`
- `docs/architecture/`
- `docs/development/`
- `docs/superpowers/plans/`
- `docs/system-completeness-audit/`

代表文件：

- `README.md`
- `QUICKSTART.md`
- `docs/architecture/方案高参-诚实边界与专业可信机制-honesty-boundary-policy.md`
- `docs/architecture/方案高参-系统地图-scheme-advisor-system-map.md`
- `docs/architecture/方案高参-维护者阅读路径-scheme-advisor-maintainer-reading-path.md`
- `docs/development/2026.6.11-下阶段开发进度安排.md`
- `docs/system-completeness-audit/`

建议：

- 文档类单独成批，不要和运行代码混在一个提交里。
- README / QUICKSTART 只保留入口导航和启动命令，不承载长篇架构说明。
- 架构文档保留中文正文，不只做中文注释。

## 保留并测试复核

数量：77。

主要范围：

- `tests/api/`
- `tests/services/`
- `tests/unit/`
- `frontend-nextjs/**/*.test.tsx`

代表文件：

- `tests/services/test_honesty_boundary_policy.py`
- `tests/services/test_formal_milk_tea_advisor_flow.py`
- `tests/services/test_scheme_advisor_triage_and_coverage.py`
- `tests/services/test_tea_space_golden_questions_p0.py`
- `tests/api/test_retired_admin_surfaces.py`
- `frontend-nextjs/app/admin/layout.test.tsx`

建议：

- 测试文件跟随功能提交。
- 先保留全部测试，避免清理时误删回归保护。
- 每个功能批次提交前跑对应测试，不一次性追求全量绿。

## 归档或忽略

数量：170。

主要范围：

- 临时脚本：`_patch*.py`、`_test*.py`、`_verify*.py`、`_scan*.py`
- 本地数据库：`*.db`
- Playwright 输出：`frontend-nextjs/.playwright-cli/`、`frontend-nextjs/output/playwright/`
- 上传缓存：`frontend-nextjs/.uploads/`
- 根目录临时文件：`old.txt`、`new_str.txt`、`temp.txt`
- `node_modules/`

代表项：

- `_patch_system_prompt.py`
- `_verify_v92_fixes.py`
- `_scan_archdaily_categories.py`
- `advisor_objects.db`
- `intelligent_project_analyzer.db`
- `frontend-nextjs/.playwright-cli/`
- `frontend-nextjs/output/playwright/`
- `frontend-nextjs/.uploads/`
- `node_modules/`

建议：

- 先补 `.gitignore`，再确认哪些已经被忽略。
- 需要保留证据的截图和 Playwright 结果可移动到 `_archive/`，但不要入主代码提交。
- 临时脚本默认不入库，除非明确转成正式 `scripts/` 工具。

## 资料库人工确认

数量：19。

主要范围：

- `sf/2026.3.22/`
- `sf/2026.4.18/`
- `sf/2026.5.16/`
- `sf/2026.5.23/`

代表项：

- `sf/2026.3.22/模拟问题集合.txt`
- `sf/2026.4.18/`
- `sf/2026.5.16/`
- `sf/2026.5.23/`
- `sf/2026.5.16.rar`
- `sf/2026.5.23.rar`

建议：

- `sf/` 是核心资料库，不要自动清理。
- 新增目录和压缩包需要确认：是否作为源资料保留、是否重复、是否需要迁移到正式知识资产流程。
- 与运行代码分开提交或归档。

## 其他人工确认

数量：33。

主要范围：

- 根目录说明文档
- 环境样例文件
- 本地工具配置
- 未归类目录

代表项：

- `.gitignore`
- `.env.example`
- `.env.development.example`
- `.env.production.example`
- `BACKUP_GUIDE.md`
- `README_TESTING.md`
- `CAPSULE_NAVIGATION_UPGRADE.md`
- `security-baseline-report.json`
- `requirements.server.tmp.txt`
- `ruff.toml`
- `mypy.ini`

建议：

- `.env*.example` 可以保留，但要检查是否含真实密钥。
- `ruff.toml`、`mypy.ini` 如果要引入质量门禁，需要单独验证。
- 根目录 Markdown 文档需要判断是否仍有效，避免项目入口文档过载。

## 高风险删除

数量：107。

主要范围：

- 管理后台已删除页面
- `sf/` 历史资料删除
- `sf/frameworks/` 删除
- `sf/备份/` 删除

代表项：

- `frontend-nextjs/app/admin/config/page.tsx`
- `frontend-nextjs/app/admin/crawler-monitor/page.tsx`
- `frontend-nextjs/app/admin/external-data/page.tsx`
- `sf/frameworks/*/README.md`
- `sf/备份/*.rar`
- `sf/2026.3.11/...`
- `sf/2026.4.18/...`

判断：

- 管理后台删除项可能是主动取消“外部数据管理 / 爬虫 / 日志查看 / 配置管理”的结果，但仍需和路由、导航、测试一起确认。
- `sf/` 删除项风险最高，不能直接接受删除。
- 压缩包删除也不能自动接受，可能是历史备份资料。

处理顺序：

1. 先确认管理后台删除项是否都有替代路由或测试覆盖。
2. 再确认 `sf/` 删除项是否是迁移后的重复资料。
3. 最后处理备份和压缩包。

## 建议的下一步

第一步：只处理忽略规则。

- 补充 `.gitignore`。
- 不删除任何文件。
- 重新运行 `git status --short`，看噪声是否下降。

### 2026-06-12 忽略规则处理结果

已补充 `.gitignore`，只覆盖本地生成物和临时产物，不覆盖正式 `docs/`、`tests/`、`scripts/` 或业务源码目录。

处理前：

- `git status --short`：595 项。

处理后：

- `git status --short`：426 项。
- 未跟踪项从 380 项降到 212 项。
- 已跟踪修改仍为 107 项。
- 已跟踪删除仍为 107 项。

本次减少 169 项状态噪声，主要来自：

- 根目录 `_*.py` 临时脚本。
- 本地数据库文件：`*.db`、`*.sqlite`、`*.sqlite3`。
- 根目录和前端的 `node_modules/`。
- Playwright 本地记录和截图输出。
- `frontend-nextjs/.uploads/` 上传缓存。
- pytest 临时目录。
- 本地安全扫描报告和临时 requirements 文件。

本次没有删除任何文件，没有提交，没有回滚。

第二步：收敛方案高参入口运行时基础批次。

经复核，不建议把这一批命名为单纯“诚实边界机制”。原因是 `scheme_advisor_context_intelligence.py` 和 `scheme_advisor_entry_service.py` 目前都是未跟踪整文件，里面承载的是方案高参入口机制、context intelligence、两轮确认、版本建议、知识包绑定等完整入口运行时能力。诚实边界是其中一个新增治理层，不是唯一改动。

建议候选批次名称：

- `方案高参入口运行时基础 + 诚实边界`

这个批次可以继续复核，但不能被误认为一个小范围补丁。

### 2026-06-12 诚实边界批次复核结果

已复核候选文件：

| 文件 | 当前 Git 状态 | 说明 |
|---|---|---|
| `intelligent_project_analyzer/config/honesty_boundary_policy.yaml` | `??` | 新增策略配置 |
| `intelligent_project_analyzer/services/honesty_boundary_service.py` | `??` | 新增策略服务 |
| `intelligent_project_analyzer/services/scheme_advisor_context_intelligence.py` | `??` | 未跟踪整文件，包含 context intelligence 入口能力，不只是诚实边界局部改动 |
| `intelligent_project_analyzer/services/scheme_advisor_entry_service.py` | `??` | 未跟踪整文件，包含方案高参入口流，不只是诚实边界局部改动 |
| `tests/services/test_honesty_boundary_policy.py` | `??` | 新增测试 |

验证结果：

```bash
pytest tests/services/test_honesty_boundary_policy.py \
  tests/services/test_scheme_advisor_triage_and_coverage.py \
  tests/services/test_formal_milk_tea_advisor_flow.py -q
```

结果：15 passed。

判断：

- 功能层面：诚实边界机制已通过相关回归。
- 版本管理层面：这批不能直接当成“只包含诚实边界”的小提交，因为两个核心入口服务文件目前是未跟踪整文件，提交时会把入口机制、context intelligence、两轮问诊等既有成果一起纳入。
- 安全做法：把这一批升级为“方案高参入口机制 + 诚实边界”候选批次，或先单独确认两个未跟踪整文件的来源和边界。

提交前需要确认：

1. `scheme_advisor_context_intelligence.py` 是否作为方案高参入口机制的一部分正式入库。
2. `scheme_advisor_entry_service.py` 是否作为方案高参入口机制的一部分正式入库。
3. 是否允许把诚实边界和入口机制放在同一个批次提交。
4. 如果不允许，需要先把入口机制本身单独作为一个批次收敛，再提交诚实边界增量。

### 2026-06-12 入口运行时基础依赖复核结果

已继续排查该批次的直接运行依赖，结论是：入口服务不是孤立文件，正式入库时至少需要把下列运行时基础一起纳入候选边界。

核心入口与诚实边界：

- `intelligent_project_analyzer/config/honesty_boundary_policy.yaml`
- `intelligent_project_analyzer/services/honesty_boundary_service.py`
- `intelligent_project_analyzer/services/scheme_advisor_context_intelligence.py`
- `intelligent_project_analyzer/services/scheme_advisor_entry_service.py`

直接服务依赖：

- `intelligent_project_analyzer/services/capability_plan_service.py`
- `intelligent_project_analyzer/services/knowledge_package_registry.py`
- `intelligent_project_analyzer/services/space_classification_service.py`
- `intelligent_project_analyzer/services/space_context_packet_service.py`
- `intelligent_project_analyzer/services/space_knowledge_coverage.py`
- `intelligent_project_analyzer/utils/ontology_loader.py`

配置、Registry 与激活包依赖：

- `intelligent_project_analyzer/config/scheme_advisor_intelligence.yaml`
- `intelligent_project_analyzer/config/scheme_advisor_entry_copy.yaml`
- `intelligent_project_analyzer/config/scheme_advisor_version_tiers.yaml`
- `intelligent_project_analyzer/config/space_knowledge_coverage.yaml`
- `intelligent_project_analyzer/config/knowledge_package_registry.yaml`
- `intelligent_project_analyzer/config/type_operating_profiles.yaml`
- `intelligent_project_analyzer/knowledge_base/ontology.yaml`
- `intelligent_project_analyzer/knowledge_base/activation_packs/`

建议随批次保留的回归测试：

- `tests/services/test_honesty_boundary_policy.py`
- `tests/services/test_scheme_advisor_entry_context_packet.py`
- `tests/services/test_scheme_advisor_triage_and_coverage.py`
- `tests/services/test_formal_milk_tea_advisor_flow.py`
- `tests/services/test_tea_space_golden_questions_p0.py`

补充验证：

```bash
python -m compileall intelligent_project_analyzer/services/scheme_advisor_entry_service.py \
  intelligent_project_analyzer/services/scheme_advisor_context_intelligence.py \
  intelligent_project_analyzer/services/honesty_boundary_service.py \
  intelligent_project_analyzer/services/capability_plan_service.py \
  intelligent_project_analyzer/services/knowledge_package_registry.py \
  intelligent_project_analyzer/services/space_classification_service.py \
  intelligent_project_analyzer/services/space_context_packet_service.py \
  intelligent_project_analyzer/services/space_knowledge_coverage.py \
  intelligent_project_analyzer/utils/ontology_loader.py
```

结果：通过。

```bash
pytest tests/services/test_honesty_boundary_policy.py \
  tests/services/test_scheme_advisor_entry_context_packet.py \
  tests/services/test_scheme_advisor_triage_and_coverage.py \
  tests/services/test_formal_milk_tea_advisor_flow.py -q
```

结果：19 passed。

```bash
pytest tests/services/test_tea_space_golden_questions_p0.py -q
```

结果：6 passed。

当前判断：

- 如果追求版本管理清晰，推荐先把“方案高参入口运行时基础”作为一个大但完整的批次收敛，再把后续 UI、管理后台、资料库分开。
- 如果追求最小提交，需要先确认这些未跟踪整文件是否都应该正式入库；否则无法可靠拆出一个真正独立的“诚实边界增量”。
- 本次仍然没有执行 `git add`、提交、删除、回滚。

第三步：处理管理后台清理批次。

- 确认被删除页面是否为主动下线。
- 跑管理后台相关测试。
- 单独提交。

第四步：处理 `sf/` 资料批次。

- 只做人工确认和归档，不自动删除。
- 如果资料仍有价值，移出代码提交批次，作为资料库治理单独处理。

## 禁止动作

在完成上述分组确认前，禁止执行：

```bash
git add .
git clean -fd
git reset --hard
git checkout -- .
```

如果需要恢复单个误删文件，只能针对明确文件路径执行，并先确认该文件不属于主动删除范围。
