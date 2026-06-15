# 2026-06-16 并行线程协作边界：Golden 复核线与茶饮专项线

本文用于约束当前两个并行开发线程，避免互相覆盖、重复修复或把一个线程的未稳定改动带入另一个线程。

## 一、当前结论

当前线程作为独立开发线推进，暂不与茶饮专项线程合并。

合并前必须分别确认：

1. Golden 复核线稳定。
2. 茶饮专项线稳定。
3. 共享文件冲突已逐项复核。
4. 两边的验证命令都跑通或明确记录未通过原因。

## 二、线程边界

### 1. Golden 复核线

本线程只处理：

- Golden 人工复核工作流。
- 缺金标工作单。
- `suggested_*` 与 `gold_expected_*` 双轨边界。
- 质量门禁。
- 复核进度、状态报告、runbook。
- 防止机器建议自动晋级为 gold。

主要文件范围：

- `scripts/*scheme_advisor_golden*`
- `scripts/sync_scheme_advisor_golden_review_from_workbench.py`
- `scripts/apply_scheme_advisor_golden_review.py`
- `scripts/check_scheme_advisor_golden_review_progress.py`
- `scripts/build_scheme_advisor_golden_review_status.py`
- `scripts/run_scheme_advisor_golden_quality_gate.py`
- `tests/*golden*`
- `docs/system-completeness-audit/scheme-advisor-*golden*`
- `intelligent_project_analyzer/services/scheme_advisor_golden_verifier.py`

### 2. 茶饮专项线

茶饮专项线程只处理：

- 茶饮空间识别。
- 茶饮黄金问题。
- 茶饮语义轴。
- 茶饮激活包、知识包、知识卡。
- 茶饮入口首轮响应和追问机制。
- 茶饮商业闭环测试。

主要文件范围：

- `sf/2026.5.23/茶饮空间黄金问题.txt`
- `intelligent_project_analyzer/config/registries/scheme_advisor_semantic_axes.yaml`
- `intelligent_project_analyzer/knowledge_base/activation_packs/tea_drink_store_pack.yaml`
- `intelligent_project_analyzer/config/scheme_advisor_entry_copy.yaml`
- `tests/services/test_scheme_advisor_pressure_semantic_axes.py`
- 茶饮知识资产、茶饮知识包、茶饮专题文档。

## 三、共享高风险文件

以下文件两条线程都可能触碰，合并前必须逐项看 diff，不允许自动覆盖：

- `intelligent_project_analyzer/services/scheme_advisor_entry_service.py`
- `intelligent_project_analyzer/services/scheme_advisor_semantic_axes.py`
- `intelligent_project_analyzer/services/scheme_advisor_pressure_runner.py`
- `intelligent_project_analyzer/services/space_classification_service.py`
- `intelligent_project_analyzer/services/project_type_detector.py`
- `intelligent_project_analyzer/config/scheme_advisor_intelligence.yaml`
- `intelligent_project_analyzer/config/scheme_advisor_entry_copy.yaml`
- `frontend-nextjs/components/ConversationMode/ConversationChat.tsx`
- `frontend-nextjs/components/ConversationMode/GuidanceCard.tsx`
- `frontend-nextjs/app/page.tsx`

规则：

1. 任一线程修改这些文件，必须在最终总结中列出。
2. 两边都修改同一文件时，不能用整文件覆盖。
3. 合并时按函数、配置段、测试意图逐块复核。
4. 如果冲突无法快速判断，先保留两边版本并新增合并清单，不做猜测式修复。

## 四、禁止动作

当前两线程并行期间禁止：

- 从 `backup/` 或历史快照整目录覆盖当前源码。
- 使用 `git reset --hard`、`git clean -fdx`、`git checkout -- .`。
- 为了让测试通过自动填写 `gold_expected_*`。
- 把茶饮测试失败放到 Golden 线程里顺手修。
- 把 Golden 门禁失败放到茶饮线程里绕过。
- 对共享高风险文件做无说明的大范围格式化。

## 五、合并前验证清单

### 1. Golden 复核线

```powershell
python -m pytest tests\services\test_scheme_advisor_golden_verifier.py tests\services\test_scheme_advisor_golden_annotation_artifacts.py tests\unit\test_scheme_advisor_sync_golden_review_from_workbench_script.py tests\unit\test_scheme_advisor_apply_golden_review_script.py tests\unit\test_scheme_advisor_golden_review_progress_script.py tests\unit\test_scheme_advisor_golden_review_status_script.py tests\unit\test_scheme_advisor_golden_quality_gate_script.py -q
```

当前没有人工金标时，以下命令返回退出码 1 是正确状态：

```powershell
python scripts\run_scheme_advisor_golden_quality_gate.py
```

正确状态应满足：

- `review_status = needs_human_review`
- `updated_rows = 0`
- `updated_items = 0`
- `copied_fields = 0`
- `policy = human_review_only_never_auto_fill_gold`

### 2. 茶饮专项线

茶饮专项线程至少需要验证：

```powershell
python -m pytest tests\services\test_scheme_advisor_pressure_semantic_axes.py -q
```

如果该测试失败，不能在 Golden 线程中修复。应记录为茶饮专项未完成项。

### 3. 集成验证

两条线都稳定后，再运行：

```powershell
python -m pytest tests\services\test_scheme_advisor_pressure_semantic_axes.py tests\services\test_scheme_advisor_golden_verifier.py tests\services\test_scheme_advisor_golden_annotation_artifacts.py tests\unit\test_scheme_advisor_sync_golden_review_from_workbench_script.py tests\unit\test_scheme_advisor_apply_golden_review_script.py tests\unit\test_scheme_advisor_golden_review_progress_script.py tests\unit\test_scheme_advisor_golden_review_status_script.py tests\unit\test_scheme_advisor_golden_quality_gate_script.py -q
```

## 六、每次问题闭环复盘格式

每解决一个问题，必须输出：

```text
已完成：
- ...

未完成：
- ...

验证：
- ...

是否影响另一线程：
- 是/否；如是，列文件和原因。

下一步：
- ...
```

这个格式用于防止重复、无效和钻细枝末节。

## 七、当前阻塞诊断：茶饮线程为什么暂停

2026-06-16 复核结果：

- 茶饮专项 worktree：`.worktrees/scheme-advisor-tea-space-thread`
- 该 worktree 基于提交：`5712cb1`
- 主工作树当前分支：`chore/git-cleanup-20260612`
- 关键基线状态：仍在主工作树的未提交混合改动中。

直接缺失不止三个文件。茶饮专项线程要运行压力测试，至少依赖以下共享基线：

```text
intelligent_project_analyzer/services/scheme_advisor_entry_service.py
intelligent_project_analyzer/services/scheme_advisor_context_intelligence.py
intelligent_project_analyzer/services/scheme_advisor_semantic_axes.py
intelligent_project_analyzer/services/scheme_advisor_pressure_runner.py
intelligent_project_analyzer/services/scheme_advisor_public_labels.py
intelligent_project_analyzer/config/scheme_advisor_entry_copy.yaml
intelligent_project_analyzer/config/scheme_advisor_intelligence.yaml
intelligent_project_analyzer/config/scheme_advisor_version_tiers.yaml
intelligent_project_analyzer/config/registries/scheme_advisor_semantic_axes.yaml
intelligent_project_analyzer/config/registries/scheme_advisor_public_labels.yaml
intelligent_project_analyzer/config/registries/space_axis_registry.yaml
tests/services/test_scheme_advisor_pressure_semantic_axes.py
tests/fixtures/scheme_advisor_semantic_axes_test.yaml
```

当前 `git log --all -- <上述文件>` 没有找到已提交历史，说明这些文件尚未形成可供其他 worktree 继承的稳定基线。

因此，茶饮线程暂停是正确行为。它不应：

- 从主工作树硬拷贝混合未提交文件。
- 在共享脏工作树里继续写茶饮补丁。
- 只复制 3 个显性缺失文件后继续推进。

## 八、解除阻塞的安全路径

推荐顺序：

1. 在本线程先整理“方案高参 P0 入口与压力测试共享基线”。
2. 只纳入能让入口运行时、语义轴、压力测试跑起来的最小文件集。
3. 不把 Golden 复核产物、茶饮专项补丁、前端样式修复和会员/爬虫清理混入同一提交。
4. 跑共享基线验证。
5. 形成明确提交或明确基线分支。
6. 茶饮专项线程从该提交或分支继续，不再依赖主工作树未提交状态。

建议拆分：

```text
提交 A：方案高参入口运行时与语义轴共享基线
提交 B：Golden 人工复核与质量门禁
提交 C：茶饮专项语义轴与茶饮黄金问题修复
```

其中提交 C 必须等待提交 A 稳定后再做。

## 九、提交 A 的暂存风险

2026-06-16 预检发现：共享基线候选文件里，多数文件是 `AM` 状态。

含义：

- `A`：文件已经有一个版本在暂存区。
- `M`：同一文件在工作区还有未暂存修改。

因此，不能直接提交当前 index。直接提交会把较旧的暂存版本提交出去，漏掉工作区里的最新修复。

如果批准形成“提交 A：方案高参入口运行时与语义轴共享基线”，必须先重新按最小文件集暂存当前工作区版本，再提交。

提交 A 候选最小文件集：

```text
intelligent_project_analyzer/services/scheme_advisor_entry_service.py
intelligent_project_analyzer/services/scheme_advisor_context_intelligence.py
intelligent_project_analyzer/services/scheme_advisor_semantic_axes.py
intelligent_project_analyzer/services/scheme_advisor_pressure_runner.py
intelligent_project_analyzer/services/scheme_advisor_public_labels.py
intelligent_project_analyzer/config/scheme_advisor_entry_copy.yaml
intelligent_project_analyzer/config/scheme_advisor_intelligence.yaml
intelligent_project_analyzer/config/scheme_advisor_version_tiers.yaml
intelligent_project_analyzer/config/registries/scheme_advisor_semantic_axes.yaml
intelligent_project_analyzer/config/registries/scheme_advisor_public_labels.yaml
intelligent_project_analyzer/config/registries/space_axis_registry.yaml
tests/services/test_scheme_advisor_pressure_semantic_axes.py
tests/fixtures/scheme_advisor_semantic_axes_test.yaml
```

提交 A 不应包含：

```text
docs/system-completeness-audit/scheme-advisor-*golden*
scripts/*golden*
frontend-nextjs/
会员、爬虫、地理、项目底盘、CSS 修复相关文件
茶饮专项补丁
```

提交 A 的目的不是让茶饮专项测试全部通过，而是让独立 worktree 能继承同一套入口运行时、语义轴 registry 和压力测试基线。茶饮专项修复应在提交 A 之后进入提交 C。
