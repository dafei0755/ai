# System-R｜系统契约层 v1.0

版本：v1.0  
日期：2026-06-02  
定位：茶饮空间知识资产进入系统前的全局契约层。System-R 不属于茶饮内容模块，不参与具体专题扩写，而是规定所有内容如何被命名、结构化、标注、映射、审计、入系统与迭代。

## 0. 核心口径

```text
System-R 是契约层，不是内容层。
A–Q 是茶饮空间内容。
R 是 A–Q 如何进入系统的规则。
```

任何 Deep Research、测绘、案例拆解或专家经验产物，进入整理加工与入系统阶段前，必须服从 System-R。

## 1. System-R 清单

| 编号 | 名称 | 作用 |
|---|---|---|
| R01 | 对象词典与实体命名规范 | 统一空间对象、设备对象、动作对象、人群对象、约束对象的命名与 ID。 |
| R02 | 槽位体系与模块字段规范 | 规定水吧台、制冰储冰、取餐、自提、骑手、洗消等模块内部必须记录的变量。 |
| R03 | 知识卡字段标准 | 规定知识卡、风险卡、案例卡、机制卡、规格卡等基础字段。 |
| R04 | grid_coordinate 标注规则 | 规定所有知识资产必须映射到 lens × layer 坐标。 |
| R05 | source_refs 与证据等级规范 | 规定来源记录、证据等级、引用链、证据冲突处理方式。 |
| R06 | time_validity 与半衰期字段 | 规定慢变量、中变量、快变量与复核周期。 |
| R07 | 可验证判断字段 | 规定候选判断、证伪条件、观测指标、复核时间。 |
| R08 | 设计任务书 2.0 章节映射规则 | 规定知识资产如何映射到任务书 17 章。 |
| R09 | Coverage Audit Matrix 覆盖审计表 | 规定以 13 lens × 4 layer 为基准审计覆盖缺口。 |
| R10 | 版本、去重、冲突、升降级机制 | 规定知识资产如何修正、废弃、升级、降级。 |
| R11 | ResearchDossier 输出契约 | 规定 Deep Research 研究包必须输出哪些结构化内容。 |
| R12 | 测绘数据模板与规格卡模板 | 规定人体工学、设备、材料、灯光、家具等测绘产物格式。 |
| R13 | CaseObject 案例对象模板 | 规定标杆案例、失败案例、门店案例的采集与拆解字段。 |
| R14 | 多约束冲突求解接口规则 | 规定多个约束同时出现时如何进入 AdvisorAgent 判断链。 |
| R15 | production_method 生产方式字段规范 | 规定 DR / MS / CL / SX 四类生产方式的标注。 |

## 2. grid_coordinate 字段

```yaml
grid_coordinate:
  primary_lens: ""
  secondary_lens: []
  layer: SpaceCore | Category | SpaceType | ProjectInstance
```

## 3. production_method 字段

```yaml
production_method:
  type: DR | MS | CL | SX
  note: ""
```

### 3.1 DR｜Deep Research
用于行业事实、商业模型、选址语境、运营机制、案例线索、趋势变化等研究包生产。

### 3.2 MS｜Measurement Survey 测绘
用于人体工学、尺寸、设备规格、材料构造、灯光声学、家具界面等确定性数据生产。

### 3.3 CL｜CaseLab 案例拆解
用于标杆、失败、闭店、动线事故、传播案例、生命周期案例等案例对象拆解。

### 3.4 SX｜System Contract 系统契约
用于字段、命名、映射、审计、版本、去重、升降级等系统规则。

## 4. 知识卡基础字段

```yaml
knowledge_card:
  id: ""
  title: ""
  card_type: ""
  source_refs: []
  evidence_level: ""
  grid_coordinate:
    primary_lens: ""
    secondary_lens: []
    layer: ""
  production_method: ""
  time_validity:
    variable_type: slow | medium | fast
    review_cycle: ""
  transferability:
    level: SpaceCore | Category | SpaceType | ProjectInstance
    limitation: ""
  output_usage: []
  task_brief_chapter: []
  verifiable_judgment:
    statement: ""
    what_would_prove_it_right: ""
    what_would_prove_it_wrong: ""
    expected_observation: ""
    review_time: ""
```

## 5. ResearchDossier 输出契约

每份 ResearchDossier 不能只交付长文，必须在结尾提供结构化卡桩。

```yaml
research_dossier_output:
  source_status: ResearchDossier
  related_module: ""
  possible_card_stub:
    suggested_card_type: ""
    suggested_grid_coordinate:
      primary_lens: ""
      secondary_lens: []
      layer: ""
    possible_missing_slot: []
  threshold_band:
    area_range: ""
    order_volume: ""
    peak_15min_cups: ""
    delivery_ratio: ""
    sku_count: ""
    power_capacity: ""
    drainage_condition: ""
    confidence: observed | inferred | weak | unknown
  verifiable_judgment_candidate:
    statement: ""
    what_would_prove_it_wrong: ""
    expected_observation: ""
  transferability_boundary:
    transferable_to: []
    not_transferable_when: []
```

## 6. 测绘规格卡模板

```yaml
measurement_spec_card:
  id: ""
  entity_name: ""
  entity_type: space_object | equipment_object | action_object | material_object | sensory_object
  physical_size:
    width: ""
    depth: ""
    height: ""
  operation_clearance: ""
  maintenance_clearance: ""
  mep_requirement:
    power: ""
    water_supply: ""
    drainage: ""
    ventilation: ""
  ergonomic_note: ""
  collision_domain: ""
  source_refs: []
  confidence: observed | manufacturer_spec | inferred | unknown
```

## 7. CaseObject 模板

```yaml
case_object:
  id: ""
  case_type: benchmark | failure | store_prototype | overseas | lifecycle
  case_name: ""
  brand: ""
  city_region: ""
  snapshot_date: ""
  source_refs: []
  raw_dimensions: []
  observable_phenomena: []
  possible_mechanism_links: []
  possible_risk_links: []
  extraction_status: raw_collected | decomposed | card_stub_created | reviewed
```

## 8. 设计任务书 2.0 章节映射规则

所有正式知识资产必须至少映射到一个任务书章节。

```text
02 项目成立判断与终局标准
03 决策方 / 使用方 / 运营方分析
04 业态逻辑与商业模型
05 场地 / 建筑 / 地域条件
06 功能需求与行为场景
07 核心矛盾识别与设计取舍
08 概念主线与空间叙事
09 文化 / 品牌 / 生活方式转译
10 功能拓扑与平面思路
11 动线 / 视线 / 空间节奏
12 材料 / 色彩 / 氛围与感官物性指标
13 风险清单与待验证事项
14 多专业边界与一票否决项
15 设计取舍账本
16 后续设计任务分解与评审标准
17 项目图谱
```

## 9. 运行纪律

```text
来源进入收集池。
卡片产生于整理加工。
正式知识进入系统仓。
价值验证发生在使用反馈。
```

```text
R 层只规定规则。
R 层不生产茶饮内容。
R 层不替 AdvisorAgent 做现场判断。
```
