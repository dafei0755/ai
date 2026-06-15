# 方案高参 Golden 质量闸人工复核运行说明

本文说明 `sf/2026.3.22/模拟问题集合.txt` 压力测试后的第一批 P0 golden 标注如何人工复核、如何写回、如何运行质量闸。

## 核心原则

- `gold_expected_*` 是人工复核后的基准答案，不是系统建议值。
- 机器可以生成候选建议，但不得由系统自动填写 gold。
- 质量闸失败不等于程序坏了；在 P0 gold 未填完之前，`gate_status: fail` 是正确状态。
- 每次填写 gold 后必须重新运行质量闸，不能只看单条样本是否合理。

## 相关文件

- 压力测试结果：`docs/system-completeness-audit/scheme-advisor-pressure-test-2026-03-22.json`
- golden 基础表：`docs/system-completeness-audit/scheme-advisor-190-golden-annotation-base-2026-03-22.json`
- Excel 友好基础表：`docs/system-completeness-audit/scheme-advisor-190-golden-annotation-base-2026-03-22.csv`
- 第一批 P0 复核表：`docs/system-completeness-audit/scheme-advisor-golden-review-batch-01-p0-2026-03-22.csv`
- 第一批 P0 机器建议：`docs/system-completeness-audit/scheme-advisor-golden-review-batch-01-p0-suggestions-2026-03-22.csv`
- 第一批 P0 复核工作单：`docs/system-completeness-audit/scheme-advisor-golden-review-workbench-2026-03-22.csv`
- 第一批 P0 缺金标复核工作单：`docs/system-completeness-audit/scheme-advisor-missing-gold-review-workbench-2026-03-22.csv`
- golden 更新副本：`docs/system-completeness-audit/scheme-advisor-190-golden-annotation-updated-2026-03-22.json`
- 质量闸报告：`docs/system-completeness-audit/scheme-advisor-golden-quality-gate-2026-03-22.json`

## 人工复核填写什么

第一批质量闸强制检查 3 个字段：

- `gold_expected_project_type`
- `gold_expected_core_tension`
- `gold_expected_output_depth`

复核人可以参考 `suggested_gold_expected_*` 字段，但必须按人判断填写到正式复核 CSV 的 `gold_expected_*` 字段。

正式 gold 字段只有在同一行 `review_decision` 明确为 `approved`、`通过`、`批准` 或 `确认` 后才会写入 golden 更新副本。未批准的草填字段只保留备注，不会进入质量闸。

## 建议操作顺序

1. 先运行质量闸，生成或刷新缺金标复核工作单。
2. 打开 `scheme-advisor-missing-gold-review-workbench-2026-03-22.csv`，对照候选值、建议值和中文填写口径。
3. 对每条 P0 样本确认项目类型、核心矛盾、输出深度。
4. 将人工确认结果填入 `gold_expected_project_type`、`gold_expected_core_tension`、`gold_expected_output_depth`。
5. 保留 `review_decision` 和 `review_note`，说明是批准、退回还是需要二次判断。
6. 用同步脚本把人工确认后的 gold 字段写入复核 CSV 副本。
7. 人工检查同步副本无误后，再替换或另存为正式复核 CSV：`scheme-advisor-golden-review-batch-01-p0-2026-03-22.csv`。
8. 用 `apply_review_csv_file` 将复核 CSV 写回 golden 更新副本。
9. 确认更新副本无误；不要覆盖基础表，基础表作为原始空白基准保留。
10. 运行质量闸脚本；质量闸默认读取 `scheme-advisor-190-golden-annotation-updated-2026-03-22.json`。

## 生成复核工作单

复核工作单把系统候选、机器建议和空白人工字段放在同一张表里，目的是减少人工来回对照文件的成本。它不会把 `suggested_gold_expected_*` 自动写入 `gold_expected_*`。

```powershell
python scripts/build_scheme_advisor_golden_review_workbench.py
```

默认输出：

```text
docs/system-completeness-audit/scheme-advisor-golden-review-workbench-2026-03-22.json
docs/system-completeness-audit/scheme-advisor-golden-review-workbench-2026-03-22.csv
docs/system-completeness-audit/scheme-advisor-golden-review-workbench-2026-03-22.md
```

质量闸会进一步生成只包含当前缺金标项的复核工作单，日常人工复核优先填写这一张：

```text
docs/system-completeness-audit/scheme-advisor-missing-gold-review-workbench-2026-03-22.json
docs/system-completeness-audit/scheme-advisor-missing-gold-review-workbench-2026-03-22.csv
docs/system-completeness-audit/scheme-advisor-missing-gold-review-workbench-2026-03-22.md
```

## 同步工作单到复核 CSV 副本

人工在缺金标工作单中填写 `gold_expected_*`、`review_decision` 和 `review_note` 后，使用同步脚本生成复核 CSV 副本。同步脚本只读取人工填写的正式字段，不读取 `suggested_gold_expected_*`。

```powershell
python scripts/sync_scheme_advisor_golden_review_from_workbench.py
```

默认输出：

```text
docs/system-completeness-audit/scheme-advisor-golden-review-batch-01-p0-synced-2026-03-22.csv
docs/system-completeness-audit/scheme-advisor-golden-review-workbench-sync-report-2026-03-22.json
```

当前工作单仍未填写人工 gold 时，`updated_rows` 应为 `0`。这表示没有发生自动晋级，不是程序错误。

## 写回命令

当前服务函数是 `apply_review_csv_file`。日常使用建议走脚本入口，它只输出更新副本，不直接覆盖正式 golden：

```powershell
python scripts/apply_scheme_advisor_golden_review.py
```

默认输出：

```text
docs/system-completeness-audit/scheme-advisor-190-golden-annotation-updated-2026-03-22.json
docs/system-completeness-audit/scheme-advisor-golden-review-apply-report-2026-03-22.json
```

写回脚本只会晋级已批准行的 `gold_expected_*` 字段。若只填写字段但未填写批准决定，报告中的 `review_rows_pending_decision` 会增加，正式 golden 不会被更新。

如需手工指定路径，可直接调用底层 verifier：

```powershell
python -m intelligent_project_analyzer.services.scheme_advisor_golden_verifier `
  --golden docs/system-completeness-audit/scheme-advisor-190-golden-annotation-base-2026-03-22.json `
  --review-csv docs/system-completeness-audit/scheme-advisor-golden-review-batch-01-p0-2026-03-22.csv `
  --updated-golden-output docs/system-completeness-audit/scheme-advisor-190-golden-annotation-updated-2026-03-22.json `
  --apply-report-output docs/system-completeness-audit/scheme-advisor-golden-review-apply-report-2026-03-22.json
```

## 检查复核进度

填写过程中可以先运行进度检查脚本，它只统计缺失字段，不会写回 golden：

```powershell
python scripts/check_scheme_advisor_golden_review_progress.py
```

输出报告：

```text
docs/system-completeness-audit/scheme-advisor-golden-review-completion-2026-03-22.json
```

当前 CSV 仍有必填 gold 字段缺失时，脚本会返回退出码 1。这个失败用于提醒复核还没完成，不代表程序异常。

## 运行质量闸

统一入口：

```powershell
python scripts/run_scheme_advisor_golden_quality_gate.py
```

当前 P0 gold 未填完时，脚本应返回退出码 1，并在报告中显示 `gate_status: fail`。

P0 gold 填写并写回后，脚本才应返回退出码 0。

质量闸读取的是 golden 更新副本，不读取基础表。基础表用于重新生成或审计，不作为人工复核后的运行验收来源。

## 生成总览状态

管理后台或人工总览可以读取汇总状态文件，不需要分别解析进度、写回和质量闸三个报告：

```powershell
python scripts/build_scheme_advisor_golden_review_status.py
```

输出报告：

```text
docs/system-completeness-audit/scheme-advisor-golden-review-status-2026-03-22.json
```

当前未完成人审时，`review_status` 应为 `needs_human_review`，`next_action` 应为 `fill_required_gold_fields`。

## 判断结果

- 退出码 0：质量闸通过，P0 必检 gold 字段已填写且当前压力测试结果匹配。
- 退出码 1：质量闸失败，需要查看 `scheme-advisor-golden-quality-gate-2026-03-22.json` 的 `failures`。
- 其它异常：通常是文件路径、JSON 格式、CSV 编码或运行环境问题，先排查命令和输入文件。

## 不允许的做法

- 不允许把机器建议直接批量复制成 gold。
- 不允许跳过 `review_decision` 和 `review_note`。
- 不允许只修某个失败样本而不回跑整批质量闸。
- 不允许为了让质量闸通过而降低 required fields。
