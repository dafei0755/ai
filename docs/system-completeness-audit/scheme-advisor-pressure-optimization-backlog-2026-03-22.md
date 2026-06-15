# 方案高参压测优化待办清单

- 生成时间: `2026-06-15T18:56:46`
- 压测总数: 190
- 压测通过: 190
- 阻断失败: 0
- 有告警样本: 0

## 治理边界

- 可以在这里做：生成候选清单、补回归测试、补 Type Alias 候选、补 Registry 候选、生成知识卡草稿。
- 需要人工复核：正式新增项目类型或子域、正式批准知识卡、正式上线 Activation Pack、将模型推断写入运行时事实。
- 硬边界：不得自动写入正式 Registry 或知识库；候选必须人工复核后沉淀。

## 总览

| 项目 | 数量 | 优先级 |
|---|---:|---|
| 低置信样本复核 | 0 | P0 |
| Registry 覆盖缺口类型 | 22 | P1 |
| 知识缺口类型 | 22 | P1 |
| 激活包候选类型 | 13 | P2 |
| 激活包可优先定义聚类 | 7 | P2 |

## P0 低置信样本复核

无。

## P1 Registry 覆盖缺口

| 类型 | 数量 | 样本编号 | 候选类型 | 审核队列 | 治理方式 | 晋级规则 | 验证门槛 | 建议动作 |
|---|---:|---|---|---|---|---|---|---|
| personal_residential | 24 | 2, 6, 7, 8, 12, 20, 22, 28, 31, 33, 37, 38 | registry_boundary_candidate | space_registry_review | registry_governed | human_review_required | 补充候选后必须跑 190 条回归压测，不得新增低置信或错误路由。 | 补 Registry 覆盖、Type Alias 和边界样本 |
| community_public | 10 | 35, 69, 96, 109, 114, 121, 132, 159, 160, 167 | registry_boundary_candidate | space_registry_review | registry_governed | human_review_required | 补充候选后必须跑 190 条回归压测，不得新增低置信或错误路由。 | 补 Registry 覆盖、Type Alias 和边界样本 |
| special_function | 9 | 27, 34, 46, 120, 126, 142, 147, 182, 190 | registry_boundary_candidate | space_registry_review | registry_governed | human_review_required | 补充候选后必须跑 190 条回归压测，不得新增低置信或错误路由。 | 补 Registry 覆盖、Type Alias 和边界样本 |
| commercial_retail | 8 | 18, 51, 61, 87, 156, 157, 162, 183 | registry_boundary_candidate | space_registry_review | registry_governed | human_review_required | 补充候选后必须跑 190 条回归压测，不得新增低置信或错误路由。 | 补 Registry 覆盖、Type Alias 和边界样本 |
| commercial_office | 6 | 25, 48, 88, 105, 140, 179 | registry_boundary_candidate | space_registry_review | registry_governed | human_review_required | 补充候选后必须跑 190 条回归压测，不得新增低置信或错误路由。 | 补 Registry 覆盖、Type Alias 和边界样本 |
| urban_renewal_heritage | 6 | 30, 77, 93, 151, 152, 178 | registry_boundary_candidate | space_registry_review | registry_governed | human_review_required | 补充候选后必须跑 190 条回归压测，不得新增低置信或错误路由。 | 补 Registry 覆盖、Type Alias 和边界样本 |
| commercial_hospitality | 5 | 4, 42, 76, 85, 92 | registry_boundary_candidate | space_registry_review | registry_governed | human_review_required | 补充候选后必须跑 190 条回归压测，不得新增低置信或错误路由。 | 补 Registry 覆盖、Type Alias 和边界样本 |
| public_cultural | 5 | 70, 143, 148, 170, 188 | registry_boundary_candidate | space_registry_review | registry_governed | human_review_required | 补充候选后必须跑 190 条回归压测，不得新增低置信或错误路由。 | 补 Registry 覆盖、Type Alias 和边界样本 |
| rural_construction | 5 | 3, 16, 153, 158, 165 | registry_boundary_candidate | space_registry_review | registry_governed | human_review_required | 补充候选后必须跑 190 条回归压测，不得新增低置信或错误路由。 | 补 Registry 覆盖、Type Alias 和边界样本 |
| commercial_dining | 4 | 24, 79, 86, 168 | registry_boundary_candidate | space_registry_review | registry_governed | human_review_required | 补充候选后必须跑 190 条回归压测，不得新增低置信或错误路由。 | 补 Registry 覆盖、Type Alias 和边界样本 |
| commercial_enterprise | 3 | 94, 99, 116 | registry_boundary_candidate | space_registry_review | registry_governed | human_review_required | 补充候选后必须跑 190 条回归压测，不得新增低置信或错误路由。 | 补 Registry 覆盖、Type Alias 和边界样本 |
| healthcare_wellness | 3 | 44, 80, 115 | registry_boundary_candidate | space_registry_review | registry_governed | human_review_required | 补充候选后必须跑 190 条回归压测，不得新增低置信或错误路由。 | 补 Registry 覆盖、Type Alias 和边界样本 |
| digital_media_studio | 2 | 55, 62 | registry_boundary_candidate | space_registry_review | registry_governed | human_review_required | 补充候选后必须跑 190 条回归压测，不得新增低置信或错误路由。 | 补 Registry 覆盖、Type Alias 和边界样本 |
| landscape_outdoor | 2 | 172, 176 | registry_boundary_candidate | space_registry_review | registry_governed | human_review_required | 补充候选后必须跑 190 条回归压测，不得新增低置信或错误路由。 | 补 Registry 覆盖、Type Alias 和边界样本 |
| religious_spiritual | 2 | 75, 186 | registry_boundary_candidate | space_registry_review | registry_governed | human_review_required | 补充候选后必须跑 190 条回归压测，不得新增低置信或错误路由。 | 补 Registry 覆盖、Type Alias 和边界样本 |
| urban_renewal_market | 2 | 9, 174 | registry_boundary_candidate | space_registry_review | registry_governed | human_review_required | 补充候选后必须跑 190 条回归压测，不得新增低置信或错误路由。 | 补 Registry 覆盖、Type Alias 和边界样本 |
| brand_experience | 1 | 181 | registry_boundary_candidate | space_registry_review | registry_governed | human_review_required | 补充候选后必须跑 190 条回归压测，不得新增低置信或错误路由。 | 补 Registry 覆盖、Type Alias 和边界样本 |
| children_family | 1 | 72 | registry_boundary_candidate | space_registry_review | registry_governed | human_review_required | 补充候选后必须跑 190 条回归压测，不得新增低置信或错误路由。 | 补 Registry 覆盖、Type Alias 和边界样本 |
| educational_facility | 1 | 106 | registry_boundary_candidate | space_registry_review | registry_governed | human_review_required | 补充候选后必须跑 190 条回归压测，不得新增低置信或错误路由。 | 补 Registry 覆盖、Type Alias 和边界样本 |
| popup_temporary | 1 | 56 | registry_boundary_candidate | space_registry_review | registry_governed | human_review_required | 补充候选后必须跑 190 条回归压测，不得新增低置信或错误路由。 | 补 Registry 覆盖、Type Alias 和边界样本 |
| real_estate_showcase | 1 | 97 | registry_boundary_candidate | space_registry_review | registry_governed | human_review_required | 补充候选后必须跑 190 条回归压测，不得新增低置信或错误路由。 | 补 Registry 覆盖、Type Alias 和边界样本 |
| residential_collective | 1 | 73 | registry_boundary_candidate | space_registry_review | registry_governed | human_review_required | 补充候选后必须跑 190 条回归压测，不得新增低置信或错误路由。 | 补 Registry 覆盖、Type Alias 和边界样本 |

## P1 知识缺口候选

| 类型 | 数量 | 样本编号 | 候选类型 | 审核队列 | 治理方式 | 晋级规则 | 验证门槛 | 建议动作 |
|---|---:|---|---|---|---|---|---|---|
| personal_residential | 24 | 2, 6, 7, 8, 12, 20, 22, 28, 31, 33, 37, 38 | knowledge_card_candidate | knowledge_asset_review | knowledge_governed | human_review_required | 候选卡必须有来源、适用边界和不可使用边界；审核通过前不得进入 runtime recall。 | 生成候选知识卡，进入人工审核后再批准入库 |
| community_public | 10 | 35, 69, 96, 109, 114, 121, 132, 159, 160, 167 | knowledge_card_candidate | knowledge_asset_review | knowledge_governed | human_review_required | 候选卡必须有来源、适用边界和不可使用边界；审核通过前不得进入 runtime recall。 | 生成候选知识卡，进入人工审核后再批准入库 |
| special_function | 9 | 27, 34, 46, 120, 126, 142, 147, 182, 190 | knowledge_card_candidate | knowledge_asset_review | knowledge_governed | human_review_required | 候选卡必须有来源、适用边界和不可使用边界；审核通过前不得进入 runtime recall。 | 生成候选知识卡，进入人工审核后再批准入库 |
| commercial_retail | 8 | 18, 51, 61, 87, 156, 157, 162, 183 | knowledge_card_candidate | knowledge_asset_review | knowledge_governed | human_review_required | 候选卡必须有来源、适用边界和不可使用边界；审核通过前不得进入 runtime recall。 | 生成候选知识卡，进入人工审核后再批准入库 |
| commercial_office | 6 | 25, 48, 88, 105, 140, 179 | knowledge_card_candidate | knowledge_asset_review | knowledge_governed | human_review_required | 候选卡必须有来源、适用边界和不可使用边界；审核通过前不得进入 runtime recall。 | 生成候选知识卡，进入人工审核后再批准入库 |
| urban_renewal_heritage | 6 | 30, 77, 93, 151, 152, 178 | knowledge_card_candidate | knowledge_asset_review | knowledge_governed | human_review_required | 候选卡必须有来源、适用边界和不可使用边界；审核通过前不得进入 runtime recall。 | 生成候选知识卡，进入人工审核后再批准入库 |
| commercial_hospitality | 5 | 4, 42, 76, 85, 92 | knowledge_card_candidate | knowledge_asset_review | knowledge_governed | human_review_required | 候选卡必须有来源、适用边界和不可使用边界；审核通过前不得进入 runtime recall。 | 生成候选知识卡，进入人工审核后再批准入库 |
| public_cultural | 5 | 70, 143, 148, 170, 188 | knowledge_card_candidate | knowledge_asset_review | knowledge_governed | human_review_required | 候选卡必须有来源、适用边界和不可使用边界；审核通过前不得进入 runtime recall。 | 生成候选知识卡，进入人工审核后再批准入库 |
| rural_construction | 5 | 3, 16, 153, 158, 165 | knowledge_card_candidate | knowledge_asset_review | knowledge_governed | human_review_required | 候选卡必须有来源、适用边界和不可使用边界；审核通过前不得进入 runtime recall。 | 生成候选知识卡，进入人工审核后再批准入库 |
| commercial_dining | 4 | 24, 79, 86, 168 | knowledge_card_candidate | knowledge_asset_review | knowledge_governed | human_review_required | 候选卡必须有来源、适用边界和不可使用边界；审核通过前不得进入 runtime recall。 | 生成候选知识卡，进入人工审核后再批准入库 |
| commercial_enterprise | 3 | 94, 99, 116 | knowledge_card_candidate | knowledge_asset_review | knowledge_governed | human_review_required | 候选卡必须有来源、适用边界和不可使用边界；审核通过前不得进入 runtime recall。 | 生成候选知识卡，进入人工审核后再批准入库 |
| healthcare_wellness | 3 | 44, 80, 115 | knowledge_card_candidate | knowledge_asset_review | knowledge_governed | human_review_required | 候选卡必须有来源、适用边界和不可使用边界；审核通过前不得进入 runtime recall。 | 生成候选知识卡，进入人工审核后再批准入库 |
| digital_media_studio | 2 | 55, 62 | knowledge_card_candidate | knowledge_asset_review | knowledge_governed | human_review_required | 候选卡必须有来源、适用边界和不可使用边界；审核通过前不得进入 runtime recall。 | 生成候选知识卡，进入人工审核后再批准入库 |
| landscape_outdoor | 2 | 172, 176 | knowledge_card_candidate | knowledge_asset_review | knowledge_governed | human_review_required | 候选卡必须有来源、适用边界和不可使用边界；审核通过前不得进入 runtime recall。 | 生成候选知识卡，进入人工审核后再批准入库 |
| religious_spiritual | 2 | 75, 186 | knowledge_card_candidate | knowledge_asset_review | knowledge_governed | human_review_required | 候选卡必须有来源、适用边界和不可使用边界；审核通过前不得进入 runtime recall。 | 生成候选知识卡，进入人工审核后再批准入库 |
| urban_renewal_market | 2 | 9, 174 | knowledge_card_candidate | knowledge_asset_review | knowledge_governed | human_review_required | 候选卡必须有来源、适用边界和不可使用边界；审核通过前不得进入 runtime recall。 | 生成候选知识卡，进入人工审核后再批准入库 |
| brand_experience | 1 | 181 | knowledge_card_candidate | knowledge_asset_review | knowledge_governed | human_review_required | 候选卡必须有来源、适用边界和不可使用边界；审核通过前不得进入 runtime recall。 | 生成候选知识卡，进入人工审核后再批准入库 |
| children_family | 1 | 72 | knowledge_card_candidate | knowledge_asset_review | knowledge_governed | human_review_required | 候选卡必须有来源、适用边界和不可使用边界；审核通过前不得进入 runtime recall。 | 生成候选知识卡，进入人工审核后再批准入库 |
| educational_facility | 1 | 106 | knowledge_card_candidate | knowledge_asset_review | knowledge_governed | human_review_required | 候选卡必须有来源、适用边界和不可使用边界；审核通过前不得进入 runtime recall。 | 生成候选知识卡，进入人工审核后再批准入库 |
| popup_temporary | 1 | 56 | knowledge_card_candidate | knowledge_asset_review | knowledge_governed | human_review_required | 候选卡必须有来源、适用边界和不可使用边界；审核通过前不得进入 runtime recall。 | 生成候选知识卡，进入人工审核后再批准入库 |
| real_estate_showcase | 1 | 97 | knowledge_card_candidate | knowledge_asset_review | knowledge_governed | human_review_required | 候选卡必须有来源、适用边界和不可使用边界；审核通过前不得进入 runtime recall。 | 生成候选知识卡，进入人工审核后再批准入库 |
| residential_collective | 1 | 73 | knowledge_card_candidate | knowledge_asset_review | knowledge_governed | human_review_required | 候选卡必须有来源、适用边界和不可使用边界；审核通过前不得进入 runtime recall。 | 生成候选知识卡，进入人工审核后再批准入库 |

## P2 激活包建设优先队列

| 排名 | 类型 | 空间主轴 | 样本数 | 平均置信度 | 分数 | 成熟度 | 样本编号 | 建议动作 |
|---:|---|---|---:|---:|---:|---|---|---|
| 1 | public_cultural | cultural_public_experience | 12 | 0.823 | 136 | 优先定义包范围 | 45, 54, 70, 103, 107, 122, 125, 127, 134, 149, 170, 189 | 先做激活包范围定义、适用边界、核心追问和最小知识卡清单。 |
| 2 | personal_residential | private_residential_life_order | 17 | 0.768 | 135 | 优先定义包范围 | 6, 7, 10, 11, 12, 20, 31, 33, 37, 38, 41, 66 | 先做激活包范围定义、适用边界、核心追问和最小知识卡清单。 |
| 3 | commercial_retail | retail_brand_conversion | 10 | 0.848 | 117 | 优先定义包范围 | 18, 61, 84, 87, 155, 156, 157, 162, 164, 183 | 先做激活包范围定义、适用边界、核心追问和最小知识卡清单。 |
| 4 | community_public | public_service_inclusive_reuse | 10 | 0.741 | 115 | 优先定义包范围 | 109, 112, 114, 121, 128, 132, 133, 135, 159, 160 | 先做激活包范围定义、适用边界、核心追问和最小知识卡清单。 |
| 5 | urban_renewal_heritage | urban_renewal_public_regeneration | 10 | 0.745 | 115 | 优先定义包范围 | 30, 40, 57, 77, 93, 151, 152, 161, 166, 178 | 先做激活包范围定义、适用边界、核心追问和最小知识卡清单。 |
| 6 | commercial_office | workplace_identity_productivity | 9 | 0.807 | 106 | 优先定义包范围 | 25, 48, 64, 74, 88, 105, 140, 185, 187 | 先做激活包范围定义、适用边界、核心追问和最小知识卡清单。 |
| 7 | healthcare_wellness | healthcare_wellness_support | 7 | 0.842 | 87 | 优先定义包范围 | 44, 47, 58, 80, 110, 119, 175 | 先做激活包范围定义、适用边界、核心追问和最小知识卡清单。 |
| 8 | personal_residential | healthcare_wellness_support | 5 | 0.844 | 67 | 候选池继续补证 | 39, 63, 65, 102, 145 | 继续补同类样本、边界样本和知识卡证据，暂不直接上线。 |
| 9 | commercial_hospitality | hospitality_culture_operation | 5 | 0.71 | 64 | 候选池继续补证 | 4, 17, 26, 42, 173 | 继续补同类样本、边界样本和知识卡证据，暂不直接上线。 |
| 10 | personal_residential | brand_cultural_narrative | 4 | 0.69 | 54 | 候选池继续补证 | 5, 28, 59, 111 | 继续补同类样本、边界样本和知识卡证据，暂不直接上线。 |
| 11 | commercial_enterprise | workplace_identity_productivity | 3 | 0.793 | 46 | 候选池继续补证 | 89, 99, 113 | 继续补同类样本、边界样本和知识卡证据，暂不直接上线。 |
| 12 | rural_construction | rural_living_regeneration | 3 | 0.82 | 46 | 候选池继续补证 | 153, 158, 165 | 继续补同类样本、边界样本和知识卡证据，暂不直接上线。 |
| 13 | educational_facility | education_growth_safety | 3 | 0.763 | 45 | 候选池继续补证 | 91, 106, 163 | 继续补同类样本、边界样本和知识卡证据，暂不直接上线。 |
| 14 | personal_residential | residential_conflict_lifestyle_balance | 3 | 0.742 | 45 | 候选池继续补证 | 8, 22, 50 | 继续补同类样本、边界样本和知识卡证据，暂不直接上线。 |
| 15 | landscape_outdoor | landscape_public_value | 3 | 0.58 | 42 | 继续观察 | 172, 176, 180 | 只保留为观察信号，等待更多同类样本或更稳定分类证据。 |
| 16 | commercial_hospitality | sports_wellness_social | 2 | 0.745 | 35 | 继续观察 | 1, 92 | 只保留为观察信号，等待更多同类样本或更稳定分类证据。 |
| 17 | public_cultural | mission_critical_resilience | 2 | 0.71 | 34 | 继续观察 | 136, 138 | 只保留为观察信号，等待更多同类样本或更稳定分类证据。 |
| 18 | public_cultural | experimental_public_experience | 2 | 0.65 | 33 | 继续观察 | 148, 188 | 只保留为观察信号，等待更多同类样本或更稳定分类证据。 |
| 19 | commercial_enterprise | brand_cultural_narrative | 2 | 0.62 | 32 | 继续观察 | 116, 124 | 只保留为观察信号，等待更多同类样本或更稳定分类证据。 |
| 20 | community_public | public_resilience_modular_support | 2 | 0.59 | 32 | 继续观察 | 69, 117 | 只保留为观察信号，等待更多同类样本或更稳定分类证据。 |
| 21 | commercial_dining | brand_cultural_narrative | 1 | 0.9 | 28 | 继续观察 | 24 | 只保留为观察信号，等待更多同类样本或更稳定分类证据。 |
| 22 | commercial_dining | urban_public_value_cluster | 1 | 0.9 | 28 | 继续观察 | 168 | 只保留为观察信号，等待更多同类样本或更稳定分类证据。 |
| 23 | personal_residential | private_residential_identity_legacy | 1 | 0.9 | 28 | 继续观察 | 2 | 只保留为观察信号，等待更多同类样本或更稳定分类证据。 |
| 24 | rural_construction | hospitality_culture_operation | 1 | 0.9 | 28 | 继续观察 | 3 | 只保留为观察信号，等待更多同类样本或更稳定分类证据。 |
| 25 | commercial_dining | climate_resilience_construction | 1 | 0.83 | 27 | 继续观察 | 86 | 只保留为观察信号，等待更多同类样本或更稳定分类证据。 |
| 26 | community_public | material_sustainability_value | 1 | 0.83 | 27 | 继续观察 | 167 | 只保留为观察信号，等待更多同类样本或更稳定分类证据。 |
| 27 | healthcare_wellness | healthcare_culture_experience | 1 | 0.732 | 25 | 继续观察 | 98 | 只保留为观察信号，等待更多同类样本或更稳定分类证据。 |
| 28 | commercial_hospitality | material_sustainability_value | 1 | 0.71 | 24 | 继续观察 | 76 | 只保留为观察信号，等待更多同类样本或更稳定分类证据。 |
| 29 | community_public | urban_public_value_cluster | 1 | 0.63 | 23 | 继续观察 | 171 | 只保留为观察信号，等待更多同类样本或更稳定分类证据。 |
| 30 | public_cultural | public_learning_visitor_experience | 1 | 0.636 | 23 | 继续观察 | 60 | 只保留为观察信号，等待更多同类样本或更稳定分类证据。 |
| 31 | commercial_enterprise | mission_critical_resilience | 1 | 0.59 | 22 | 继续观察 | 130 | 只保留为观察信号，等待更多同类样本或更稳定分类证据。 |
| 32 | commercial_hospitality | mission_critical_resilience | 1 | 0.58 | 22 | 继续观察 | 123 | 只保留为观察信号，等待更多同类样本或更稳定分类证据。 |
| 33 | commercial_office | urban_public_value_cluster | 1 | 0.59 | 22 | 继续观察 | 179 | 只保留为观察信号，等待更多同类样本或更稳定分类证据。 |
| 34 | public_cultural | public_resilience_modular_support | 1 | 0.59 | 22 | 继续观察 | 139 | 只保留为观察信号，等待更多同类样本或更稳定分类证据。 |
| 35 | public_cultural | sustainable_energy_prototype | 1 | 0.58 | 22 | 继续观察 | 143 | 只保留为观察信号，等待更多同类样本或更稳定分类证据。 |
| 36 | public_cultural | retail_brand_conversion | 1 | 0.56 | 21 | 继续观察 | 169 | 只保留为观察信号，等待更多同类样本或更稳定分类证据。 |
| 37 | rural_construction | private_residential_life_order | 1 | 0.56 | 21 | 继续观察 | 16 | 只保留为观察信号，等待更多同类样本或更稳定分类证据。 |

## P2 激活包候选

| 类型 | 数量 | 样本编号 | 候选类型 | 审核队列 | 治理方式 | 晋级规则 | 验证门槛 | 建议动作 |
|---|---:|---|---|---|---|---|---|---|
| personal_residential | 30 | 2, 5, 6, 7, 8, 10, 11, 12, 20, 22, 28, 31 | activation_pack_candidate | activation_pack_review | knowledge_governed | frequency_and_value_then_human_review | 激活包候选必须先证明高频、商业价值和知识成熟度，再由人工批准上线。 | 进入激活包候选池，按高频和业务价值排期 |
| public_cultural | 20 | 45, 54, 60, 70, 103, 107, 122, 125, 127, 134, 136, 138 | activation_pack_candidate | activation_pack_review | knowledge_governed | frequency_and_value_then_human_review | 激活包候选必须先证明高频、商业价值和知识成熟度，再由人工批准上线。 | 进入激活包候选池，按高频和业务价值排期 |
| community_public | 14 | 69, 109, 112, 114, 117, 121, 128, 132, 133, 135, 159, 160 | activation_pack_candidate | activation_pack_review | knowledge_governed | frequency_and_value_then_human_review | 激活包候选必须先证明高频、商业价值和知识成熟度，再由人工批准上线。 | 进入激活包候选池，按高频和业务价值排期 |
| commercial_office | 10 | 25, 48, 64, 74, 88, 105, 140, 179, 185, 187 | activation_pack_candidate | activation_pack_review | knowledge_governed | frequency_and_value_then_human_review | 激活包候选必须先证明高频、商业价值和知识成熟度，再由人工批准上线。 | 进入激活包候选池，按高频和业务价值排期 |
| commercial_retail | 10 | 18, 61, 84, 87, 155, 156, 157, 162, 164, 183 | activation_pack_candidate | activation_pack_review | knowledge_governed | frequency_and_value_then_human_review | 激活包候选必须先证明高频、商业价值和知识成熟度，再由人工批准上线。 | 进入激活包候选池，按高频和业务价值排期 |
| urban_renewal_heritage | 10 | 30, 40, 57, 77, 93, 151, 152, 161, 166, 178 | activation_pack_candidate | activation_pack_review | knowledge_governed | frequency_and_value_then_human_review | 激活包候选必须先证明高频、商业价值和知识成熟度，再由人工批准上线。 | 进入激活包候选池，按高频和业务价值排期 |
| commercial_hospitality | 9 | 1, 4, 17, 26, 42, 76, 92, 123, 173 | activation_pack_candidate | activation_pack_review | knowledge_governed | frequency_and_value_then_human_review | 激活包候选必须先证明高频、商业价值和知识成熟度，再由人工批准上线。 | 进入激活包候选池，按高频和业务价值排期 |
| healthcare_wellness | 8 | 44, 47, 58, 80, 98, 110, 119, 175 | activation_pack_candidate | activation_pack_review | knowledge_governed | frequency_and_value_then_human_review | 激活包候选必须先证明高频、商业价值和知识成熟度，再由人工批准上线。 | 进入激活包候选池，按高频和业务价值排期 |
| commercial_enterprise | 6 | 89, 99, 113, 116, 124, 130 | activation_pack_candidate | activation_pack_review | knowledge_governed | frequency_and_value_then_human_review | 激活包候选必须先证明高频、商业价值和知识成熟度，再由人工批准上线。 | 进入激活包候选池，按高频和业务价值排期 |
| rural_construction | 5 | 3, 16, 153, 158, 165 | activation_pack_candidate | activation_pack_review | knowledge_governed | frequency_and_value_then_human_review | 激活包候选必须先证明高频、商业价值和知识成熟度，再由人工批准上线。 | 进入激活包候选池，按高频和业务价值排期 |
| commercial_dining | 3 | 24, 86, 168 | activation_pack_candidate | activation_pack_review | knowledge_governed | frequency_and_value_then_human_review | 激活包候选必须先证明高频、商业价值和知识成熟度，再由人工批准上线。 | 进入激活包候选池，按高频和业务价值排期 |
| educational_facility | 3 | 91, 106, 163 | activation_pack_candidate | activation_pack_review | knowledge_governed | frequency_and_value_then_human_review | 激活包候选必须先证明高频、商业价值和知识成熟度，再由人工批准上线。 | 进入激活包候选池，按高频和业务价值排期 |
| landscape_outdoor | 3 | 172, 176, 180 | activation_pack_candidate | activation_pack_review | knowledge_governed | frequency_and_value_then_human_review | 激活包候选必须先证明高频、商业价值和知识成熟度，再由人工批准上线。 | 进入激活包候选池，按高频和业务价值排期 |

## P3 基础框架观察池

| 类型 | 数量 | 样本编号 | 候选类型 | 审核队列 | 治理方式 | 晋级规则 | 验证门槛 | 建议动作 |
|---|---:|---|---|---|---|---|---|---|
| special_function | 12 | 27, 34, 36, 46, 120, 126, 142, 147, 150, 182, 184, 190 | coverage_watch_signal | coverage_watch_pool | runtime_rule | aggregate_before_candidate | 观察池只累计信号；达到频次和风险阈值后才生成 Registry 或知识候选。 | 保留在基础空间推理框架观察池，继续累计样本；暂不直接立项建设专科激活包。 |
| personal_residential | 5 | 32, 49, 82, 131, 141 | coverage_watch_signal | coverage_watch_pool | runtime_rule | aggregate_before_candidate | 观察池只累计信号；达到频次和风险阈值后才生成 Registry 或知识候选。 | 保留在基础空间推理框架观察池，继续累计样本；暂不直接立项建设专科激活包。 |
| digital_media_studio | 4 | 55, 62, 90, 108 | coverage_watch_signal | coverage_watch_pool | runtime_rule | aggregate_before_candidate | 观察池只累计信号；达到频次和风险阈值后才生成 Registry 或知识候选。 | 保留在基础空间推理框架观察池，继续累计样本；暂不直接立项建设专科激活包。 |
| brand_experience | 3 | 29, 118, 181 | coverage_watch_signal | coverage_watch_pool | runtime_rule | aggregate_before_candidate | 观察池只累计信号；达到频次和风险阈值后才生成 Registry 或知识候选。 | 保留在基础空间推理框架观察池，继续累计样本；暂不直接立项建设专科激活包。 |
| community_public | 3 | 35, 96, 101 | coverage_watch_signal | coverage_watch_pool | runtime_rule | aggregate_before_candidate | 观察池只累计信号；达到频次和风险阈值后才生成 Registry 或知识候选。 | 保留在基础空间推理框架观察池，继续累计样本；暂不直接立项建设专科激活包。 |
| healthcare_wellness | 3 | 53, 115, 146 | coverage_watch_signal | coverage_watch_pool | runtime_rule | aggregate_before_candidate | 观察池只累计信号；达到频次和风险阈值后才生成 Registry 或知识候选。 | 保留在基础空间推理框架观察池，继续累计样本；暂不直接立项建设专科激活包。 |
| commercial_office | 2 | 81, 100 | coverage_watch_signal | coverage_watch_pool | runtime_rule | aggregate_before_candidate | 观察池只累计信号；达到频次和风险阈值后才生成 Registry 或知识候选。 | 保留在基础空间推理框架观察池，继续累计样本；暂不直接立项建设专科激活包。 |
| popup_temporary | 2 | 56, 144 | coverage_watch_signal | coverage_watch_pool | runtime_rule | aggregate_before_candidate | 观察池只累计信号；达到频次和风险阈值后才生成 Registry 或知识候选。 | 保留在基础空间推理框架观察池，继续累计样本；暂不直接立项建设专科激活包。 |
| real_estate_showcase | 2 | 19, 97 | coverage_watch_signal | coverage_watch_pool | runtime_rule | aggregate_before_candidate | 观察池只累计信号；达到频次和风险阈值后才生成 Registry 或知识候选。 | 保留在基础空间推理框架观察池，继续累计样本；暂不直接立项建设专科激活包。 |
| religious_spiritual | 2 | 75, 186 | coverage_watch_signal | coverage_watch_pool | runtime_rule | aggregate_before_candidate | 观察池只累计信号；达到频次和风险阈值后才生成 Registry 或知识候选。 | 保留在基础空间推理框架观察池，继续累计样本；暂不直接立项建设专科激活包。 |
| urban_renewal_market | 2 | 9, 174 | coverage_watch_signal | coverage_watch_pool | runtime_rule | aggregate_before_candidate | 观察池只累计信号；达到频次和风险阈值后才生成 Registry 或知识候选。 | 保留在基础空间推理框架观察池，继续累计样本；暂不直接立项建设专科激活包。 |
| automotive_showroom | 1 | 43 | coverage_watch_signal | coverage_watch_pool | runtime_rule | aggregate_before_candidate | 观察池只累计信号；达到频次和风险阈值后才生成 Registry 或知识候选。 | 保留在基础空间推理框架观察池，继续累计样本；暂不直接立项建设专科激活包。 |
| children_family | 1 | 72 | coverage_watch_signal | coverage_watch_pool | runtime_rule | aggregate_before_candidate | 观察池只累计信号；达到频次和风险阈值后才生成 Registry 或知识候选。 | 保留在基础空间推理框架观察池，继续累计样本；暂不直接立项建设专科激活包。 |
| commercial_enterprise | 1 | 94 | coverage_watch_signal | coverage_watch_pool | runtime_rule | aggregate_before_candidate | 观察池只累计信号；达到频次和风险阈值后才生成 Registry 或知识候选。 | 保留在基础空间推理框架观察池，继续累计样本；暂不直接立项建设专科激活包。 |
| commercial_hospitality | 1 | 85 | coverage_watch_signal | coverage_watch_pool | runtime_rule | aggregate_before_candidate | 观察池只累计信号；达到频次和风险阈值后才生成 Registry 或知识候选。 | 保留在基础空间推理框架观察池，继续累计样本；暂不直接立项建设专科激活包。 |
| commercial_retail | 1 | 51 | coverage_watch_signal | coverage_watch_pool | runtime_rule | aggregate_before_candidate | 观察池只累计信号；达到频次和风险阈值后才生成 Registry 或知识候选。 | 保留在基础空间推理框架观察池，继续累计样本；暂不直接立项建设专科激活包。 |
| hybrid_residential_commercial | 1 | 23 | coverage_watch_signal | coverage_watch_pool | runtime_rule | aggregate_before_candidate | 观察池只累计信号；达到频次和风险阈值后才生成 Registry 或知识候选。 | 保留在基础空间推理框架观察池，继续累计样本；暂不直接立项建设专科激活包。 |
| leisure_entertainment | 1 | 104 | coverage_watch_signal | coverage_watch_pool | runtime_rule | aggregate_before_candidate | 观察池只累计信号；达到频次和风险阈值后才生成 Registry 或知识候选。 | 保留在基础空间推理框架观察池，继续累计样本；暂不直接立项建设专科激活包。 |
| public_cultural | 1 | 52 | coverage_watch_signal | coverage_watch_pool | runtime_rule | aggregate_before_candidate | 观察池只累计信号；达到频次和风险阈值后才生成 Registry 或知识候选。 | 保留在基础空间推理框架观察池，继续累计样本；暂不直接立项建设专科激活包。 |
| residential_collective | 1 | 73 | coverage_watch_signal | coverage_watch_pool | runtime_rule | aggregate_before_candidate | 观察池只累计信号；达到频次和风险阈值后才生成 Registry 或知识候选。 | 保留在基础空间推理框架观察池，继续累计样本；暂不直接立项建设专科激活包。 |
| sports_entertainment_arts | 1 | 95 | coverage_watch_signal | coverage_watch_pool | runtime_rule | aggregate_before_candidate | 观察池只累计信号；达到频次和风险阈值后才生成 Registry 或知识候选。 | 保留在基础空间推理框架观察池，继续累计样本；暂不直接立项建设专科激活包。 |
| urban_renewal_heritage | 1 | 68 | coverage_watch_signal | coverage_watch_pool | runtime_rule | aggregate_before_candidate | 观察池只累计信号；达到频次和风险阈值后才生成 Registry 或知识候选。 | 保留在基础空间推理框架观察池，继续累计样本；暂不直接立项建设专科激活包。 |
