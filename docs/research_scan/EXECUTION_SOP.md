# 主题网站扫描执行 SOP

## 0. 默认策略
- 扫描模式: 两阶段（全网发现 + 重点站点深挖）
- 输出格式: 结构化 Markdown 报告
- 来源策略: 官方/一手优先，二手信息降级标注

## 1. 安装与准备
1. 使用 `skill-installer` 列出可安装技能（curated）。
2. 安装推荐技能:
   - `playwright`
   - `screenshot`
   - `notion-research-documentation`
3. 重启 Codex 使新技能生效。

## 2. 任务输入标准
每次任务都提供 `ScanTask` 字段:
- `topic`
- `time_window`
- `seed_sites`
- `languages`
- `max_depth_per_site`
- `exclusions`

详见: `docs/research_scan/SCAN_TASK_TEMPLATE.md`

## 3. 执行流程
1. 阶段 A: 全网发现
   - 按 `topic + time_window + languages` 进行多站检索。
   - 生成候选来源池并初步打分（T1/T2/T3）。
2. 阶段 B: 重点站点深挖
   - 对 `seed_sites` 和阶段 A 的高价值来源执行定向深挖。
   - 深度上限由 `max_depth_per_site` 控制。
3. 来源治理
   - 保留发布时间与抓取时间（绝对日期）。
   - 保留证据属性: `primary` / `secondary`。

## 4. 报告输出
按固定章节输出，详见 `docs/research_scan/REPORT_TEMPLATE.md`。

## 5. 交付前质检
使用 `docs/research_scan/QUALITY_GATE_CHECKLIST.md` 执行质量门禁。
