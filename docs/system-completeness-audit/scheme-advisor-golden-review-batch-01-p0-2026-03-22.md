# 方案高参第一批 P0 人工复核包

- 来源：`docs\system-completeness-audit\scheme-advisor-golden-review-priority-2026-03-22.json`
- 生成时间：2026-06-14T23:02:49
- 用途：先复核 P0 高风险样本，并填写 `gold_expected_*` 字段。
- 边界：本文件是人工复核工作包，不自动写入正式 Registry、知识库或激活包。

## 汇总

- 样本数：29
- 锚点样本：1

| 优先级 | 数量 |
|---|---:|
| P0 | 28 |
| P1 | 1 |

## 问题族覆盖

| 问题族 | 数量 |
|---|---:|
| 住宅身份/家庭关系/情绪修复 | 5 |
| 商业运营闭环/效率与体验 | 4 |
| 文化产业/非遗/农业复合空间 | 4 |
| 未来/极端环境韧性空间 | 4 |
| 空间尺度与阶段封顶 | 4 |
| 类型边界低置信 | 4 |
| 非空间类型入口/设计决策论证 | 4 |

## 明细

| ID | 优先级 | 角色 | 问题族 | 当前类型 | 置信度 | 复核任务 |
|---:|---|---|---|---|---:|---|
| 50 | P0 | p0_high_risk | 住宅身份/家庭关系/情绪修复 | children_family | 0.32 | 确认住宅主轴是否是人物身份、家庭关系或情绪修复；重点校准核心矛盾。 |
| 28 | P0 | p0_high_risk | 住宅身份/家庭关系/情绪修复 | personal_residential | 0.44 | 确认住宅主轴是否是人物身份、家庭关系或情绪修复；重点校准核心矛盾。 |
| 145 | P0 | p0_high_risk | 住宅身份/家庭关系/情绪修复 | commercial_enterprise | 0.51 | 确认住宅主轴是否是人物身份、家庭关系或情绪修复；重点校准核心矛盾。 |
| 16 | P0 | p0_high_risk | 住宅身份/家庭关系/情绪修复 | rural_construction | 0.56 | 确认住宅主轴是否是人物身份、家庭关系或情绪修复；重点校准核心矛盾。 |
| 26 | P0 | p0_high_risk | 商业运营闭环/效率与体验 | commercial_hospitality | 0.59 | 确认商业目标、成本效率和体验表达的主次；避免只做风格化方案。 |
| 42 | P0 | p0_high_risk | 商业运营闭环/效率与体验 | commercial_hospitality | 0.59 | 确认商业目标、成本效率和体验表达的主次；避免只做风格化方案。 |
| 104 | P0 | p0_high_risk | 商业运营闭环/效率与体验 | leisure_entertainment | 0.59 | 确认商业目标、成本效率和体验表达的主次；避免只做风格化方案。 |
| 118 | P0 | p0_high_risk | 商业运营闭环/效率与体验 | brand_experience | 0.59 | 确认商业目标、成本效率和体验表达的主次；避免只做风格化方案。 |
| 161 | P0 | p0_high_risk | 文化产业/非遗/农业复合空间 | urban_renewal_heritage | 0.32 | 确认文化、产业、展示、体验、销售之间的主次关系；避免只按单一文化展陈处理。 |
| 123 | P0 | p0_high_risk | 文化产业/非遗/农业复合空间 | commercial_hospitality | 0.42 | 确认文化、产业、展示、体验、销售之间的主次关系；避免只按单一文化展陈处理。 |
| 152 | P0 | p0_high_risk | 文化产业/非遗/农业复合空间 | urban_renewal_heritage | 0.49 | 确认文化、产业、展示、体验、销售之间的主次关系；避免只按单一文化展陈处理。 |
| 169 | P0 | p0_high_risk | 文化产业/非遗/农业复合空间 | public_cultural | 0.54 | 确认文化、产业、展示、体验、销售之间的主次关系；避免只按单一文化展陈处理。 |
| 126 | P0 | p0_high_risk | 未来/极端环境韧性空间 | healthcare_wellness | 0.42 | 确认是否属于极端环境/韧性空间；重点补充基础生存系统、心理舒适和证据边界。 |
| 143 | P0 | p0_high_risk | 未来/极端环境韧性空间 | public_cultural | 0.42 | 确认是否属于极端环境/韧性空间；重点补充基础生存系统、心理舒适和证据边界。 |
| 97 | P0 | p0_high_risk | 未来/极端环境韧性空间 | real_estate_showcase | 0.49 | 确认是否属于极端环境/韧性空间；重点补充基础生存系统、心理舒适和证据边界。 |
| 43 | P0 | p0_high_risk | 未来/极端环境韧性空间 | automotive_showroom | 0.58 | 确认是否属于极端环境/韧性空间；重点补充基础生存系统、心理舒适和证据边界。 |
| 135 | P0 | p0_high_risk | 空间尺度与阶段封顶 | community_public | 0.22 | 确认空间尺度和项目阶段；重点判断是否只能输出定位/策略，而不能输出室内施工级细节。 |
| 172 | P0 | p0_high_risk | 空间尺度与阶段封顶 | landscape_outdoor | 0.22 | 确认空间尺度和项目阶段；重点判断是否只能输出定位/策略，而不能输出室内施工级细节。 |
| 147 | P0 | p0_high_risk | 空间尺度与阶段封顶 | community_public | 0.32 | 确认空间尺度和项目阶段；重点判断是否只能输出定位/策略，而不能输出室内施工级细节。 |
| 180 | P0 | p0_high_risk | 空间尺度与阶段封顶 | landscape_outdoor | 0.32 | 确认空间尺度和项目阶段；重点判断是否只能输出定位/策略，而不能输出室内施工级细节。 |
| 108 | P0 | p0_high_risk | 类型边界低置信 | digital_media_studio | 0.54 | 确认真实项目类型；判断是补 Type Alias、Registry 边界样本，还是保持未知并封顶。 |
| 187 | P0 | p0_high_risk | 类型边界低置信 | commercial_office | 0.58 | 确认真实项目类型；判断是补 Type Alias、Registry 边界样本，还是保持未知并封顶。 |
| 54 | P0 | p0_high_risk | 类型边界低置信 | public_cultural | 0.59 | 确认真实项目类型；判断是补 Type Alias、Registry 边界样本，还是保持未知并封顶。 |
| 101 | P0 | p0_high_risk | 类型边界低置信 | community_public | 0.59 | 确认真实项目类型；判断是补 Type Alias、Registry 边界样本，还是保持未知并封顶。 |
| 83 | P0 | p0_high_risk | 非空间类型入口/设计决策论证 |  | 0 | 确认这是否应进入空间分类；若不是，应标为设计决策论证，并限定输出为证据与判断框架。 |
| 69 | P0 | p0_high_risk | 非空间类型入口/设计决策论证 | personal_residential | 0.59 | 确认这是否应进入空间分类；若不是，应标为设计决策论证，并限定输出为证据与判断框架。 |
| 76 | P0 | p0_high_risk | 非空间类型入口/设计决策论证 | commercial_hospitality | 0.71 | 确认这是否应进入空间分类；若不是，应标为设计决策论证，并限定输出为证据与判断框架。 |
| 167 | P0 | p0_high_risk | 非空间类型入口/设计决策论证 | community_public | 0.83 | 确认这是否应进入空间分类；若不是，应标为设计决策论证，并限定输出为证据与判断框架。 |
| 2 | P1 | anchor_control | 住宅身份/家庭关系/情绪修复 | personal_residential | 0.9 | 锚点样本：确认深圳湾第一代创业者别墅应抓住身份表达、家族传承、内心回归，而不是城市更新或历史建筑活化。 |

## 文件

- JSON：`docs\system-completeness-audit\scheme-advisor-golden-review-batch-01-p0-2026-03-22.json`
- CSV：`docs\system-completeness-audit\scheme-advisor-golden-review-batch-01-p0-2026-03-22.csv`
