# 方案高参 190 题黄金标注底表（待人工复核）

- 来源：`docs\system-completeness-audit\scheme-advisor-pressure-test-2026-03-22.json`
- 生成时间：2026-06-14T22:46:49
- 用途：把逐题压力测试转成可复核的黄金标注基准，后续优化不得按单题硬编码。
- 注意：候选字段由规则预填，只用于人工复核，不自动写入正式 Registry、知识库或激活包。

## 汇总

- 总题数：190
- 建议人工复核：126

### 问题族分布

| 问题族 | 数量 |
|---|---:|
| 常规空间分类复核 | 48 |
| 住宅身份/家庭关系/情绪修复 | 47 |
| 空间尺度与阶段封顶 | 30 |
| 商业运营闭环/效率与体验 | 21 |
| 未来/极端环境韧性空间 | 16 |
| 文化产业/非遗/农业复合空间 | 11 |
| 非空间类型入口/设计决策论证 | 11 |
| 类型边界低置信 | 6 |

### 允许输出深度分布

| 输出深度 | 数量 |
|---|---:|
| 通用方法论级：可给空间逻辑，需声明非专科覆盖 | 72 |
| 方案框架级：可进入结构化设计建议 | 71 |
| 策略框架级：可给定位/功能/运营逻辑，不输出室内施工级细节 | 31 |
| 条件判断级：先补类型/尺度/阶段，避免直接给确定方案 | 11 |
| 决策论证级：可给判断框架与证据清单，不输出空间方案 | 5 |

## 标注字段

- `id`
- `source_id`
- `prompt_excerpt`
- `current_project_type`
- `current_project_type_name`
- `confidence`
- `warning_codes`
- `semantic_space_domains`
- `semantic_input_intents`
- `semantic_subject_profiles`
- `semantic_founding_drivers`
- `semantic_site_resources`
- `semantic_lifecycle`
- `semantic_critical_constraints`
- `candidate_spatial_extent`
- `candidate_project_stage`
- `candidate_user_intent`
- `candidate_core_tension`
- `candidate_allowed_output_depth`
- `remediation_family`
- `needs_human_review`
- `gold_expected_project_type`
- `gold_expected_spatial_extent`
- `gold_expected_project_stage`
- `gold_expected_core_tension`
- `gold_expected_output_depth`
- `review_decision`
- `review_note`

## 代表性待复核样本

| ID | 当前类型 | 置信度 | 问题族 | 候选尺度 | 候选阶段 | 核心矛盾候选 | 输出深度 |
|---:|---|---:|---|---|---|---|---|
| 83 |  | 0 | 非空间类型入口/设计决策论证 | 待人工复核 | 施工深化/论证 | 短期成本与长期价值是否成立 | 决策论证级：可给判断框架与证据清单，不输出空间方案 |
| 135 | community_public | 0.22 | 空间尺度与阶段封顶 | 园区/场地级 | 概念方案 | 前期定位、功能组合与长期运营模型是否成立 | 策略框架级：可给定位/功能/运营逻辑，不输出室内施工级细节 |
| 50 | children_family | 0.32 | 住宅身份/家庭关系/情绪修复 | 住宅/单项目级 | 概念方案 | 情绪支持、隐私边界与日常使用秩序 | 条件判断级：先补类型/尺度/阶段，避免直接给确定方案 |
| 161 | urban_renewal_heritage | 0.32 | 文化产业/非遗/农业复合空间 | 园区/场地级 | 前期定位/规划 | 商业效率、成本边界与品牌体验的取舍 | 条件判断级：先补类型/尺度/阶段，避免直接给确定方案 |
| 126 | healthcare_wellness | 0.42 | 未来/极端环境韧性空间 | 城市/片区级 | 概念方案 | 情绪支持、隐私边界与日常使用秩序 | 条件判断级：先补类型/尺度/阶段，避免直接给确定方案 |
| 108 | digital_media_studio | 0.54 | 类型边界低置信 | 待人工复核 | 概念方案 | 项目目标、核心使用者与现实边界 | 条件判断级：先补类型/尺度/阶段，避免直接给确定方案 |
| 26 | commercial_hospitality | 0.59 | 商业运营闭环/效率与体验 | 城市/片区级 | 竞标策略 | 商业效率、成本边界与品牌体验的取舍 | 方案框架级：可进入结构化设计建议 |
| 62 | digital_media_studio | 0.6 | 常规空间分类复核 | 待人工复核 | 施工深化/论证 | 项目目标、核心使用者与现实边界 | 通用方法论级：可给空间逻辑，需声明非专科覆盖 |

## 文件

- 完整 JSON：`docs\system-completeness-audit\scheme-advisor-190-golden-annotation-base-2026-03-22.json`
- 可用 Excel 打开的 CSV：`docs\system-completeness-audit\scheme-advisor-190-golden-annotation-base-2026-03-22.csv`
- 低置信归因 JSON：`docs\system-completeness-audit\scheme-advisor-low-confidence-attribution-2026-03-22.json`
