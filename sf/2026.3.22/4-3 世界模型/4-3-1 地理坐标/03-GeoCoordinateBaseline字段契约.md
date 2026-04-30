# 03 GeoCoordinateBaseline 字段契约

> 本文档是 `GeoCoordinateBaseline` 对象的完整字段定义，包含字段类型、必填/选填、来源标注、分级说明与版本化规则。
>
> 等价别名：`GeoContextBaseline`（部分参考文档用法，指同一对象）
>
> 关联文档：`01-地理坐标专项总览.md` / `02-七层地理智能提取框架.md`

---

## 一、字段分级说明

| 级别 | 含义 | 采集节点 |
|------|------|---------|
| **L1 强制** | 必须在 Node1 完成采集，否则门禁阻断 | Node1 |
| **L2 必填** | 在 3.S.0 编译时必须产出，否则 `GeoCoordinateBaseline` 不得冻结 | Node3.S.0 |
| **L3 建议** | 提升分析质量，条件允许时填写，缺失不阻断 | Node3.S.0 或 Phase 2+ |
| **L4 远期** | Phase 2 起逐步接入自动化数据源 | Phase 2+ |

---

## 二、完整字段契约（Pydantic 风格定义）

```python
class GeoPin(BaseModel):
    """Node1 阶段强制完成的最小锚定信息"""
    lat: float                        # L1 强制 | 纬度 (WGS84)
    lng: float                        # L1 强制 | 经度 (WGS84)
    address_label: str                # L1 强制 | 用户确认的地址/地点名称
    admin_region: str                 # L1 强制 | 行政区划（省/市/区/县）
    place_name: str                   # L1 强制 | 地点标志名（可为楼盘/景区/片区名）
    precision_level: str              # L1 强制 | poi / building / site / district / city
    input_method: str                 # L1 强制 | map_pin / address_text / geocoder / manual
    user_confirmed: bool              # L1 强制 | 用户是否明确确认点位 (True=项目态)
    

class PhysicalContext(BaseModel):
    """第一层：物理地理"""
    elevation_m: float                # L2 必填 | 海拔（米）
    terrain_type: str                 # L2 必填 | mountain / coastal / plain / urban / hillside
    climate_zone: str                 # L2 必填 | 气候带（温带/亚热带/高原/热带等）
    annual_temp_range: tuple          # L2 必填 | (年均最低气温, 年均最高气温) °C
    annual_precipitation_mm: float    # L3 建议 | 年均降水量（毫米）
    humidity_level: str               # L2 必填 | 低 / 中 / 高 / 极高
    dominant_wind_direction: str      # L3 建议 | 主导风向（N/NE/E/SE/S/SW/W/NW）
    sunshine_hours_annual: float      # L3 建议 | 年日照时数
    landscape_resources: list[str]    # L2 必填 | ["山景", "森林", "湖景"] / ["海景", "城市天际线"]
    seasonal_pattern: str             # L2 必填 | 四季变化特征与极端季节描述
    local_material_base: list[str]    # L3 建议 | 本地常用建材（花岗岩/青砖/竹/木等）
    disaster_risks: list[str]         # L3 建议 | 地质灾害风险（地震带/泥石流风险区等）


class AccessibilityContext(BaseModel):
    """第二层：到达与可达（交叉校验新增层）"""
    distance_to_airport_min: int      # L2 必填 | 最近机场车程（分钟）
    distance_to_highspeed_rail_min: int  # L2 必填 | 最近高铁站车程（分钟）
    distance_to_city_center_min: int  # L2 必填 | 距核心城区车程（分钟）
    last_5km_quality: str             # L2 必填 | excellent / good / poor（路况/景观过渡）
    primary_arrival_mode: str         # L2 必填 | self_drive / shuttle / public_transit / walk
    parking_capacity_level: str       # L3 建议 | 充裕 / 适中 / 紧张
    drop_off_experience: str          # L3 建议 | 落客点体验描述
    arrival_fatigue: str              # L2 必填 | 低 / 中 / 高（影响首感设计优先级）
    first_impression_window: str      # L2 必填 | 从落车到进门的主要体验节点描述


class UrbanSemantic(BaseModel):
    """第三层：城市语义"""
    city_tier: str                    # L2 必填 | 一线/新一线/省会/旅游城市/特色小镇
    district_type: str                # L2 必填 | CBD/文旅目的地/老城核心/度假区/产业园区
    demographic_signal: str           # L2 必填 | 主力客群职业画像与消费水平描述
    emotional_tone: list[str]         # L2 必填 | 情绪气质关键词（山野沉浸/云端顶级/松弛疗愈/都市封面）
    landmark_proximity: list[str]     # L3 建议 | 3km内主要景点/商圈关系
    area_development_stage: str       # L3 建议 | 成长期/成熟期/饱和期
    place_identity_tags: list[str]    # L2 必填 | 系统识别的地点身份标签（供下游直接引用）


class CulturalDNA(BaseModel):
    """第四层：文化基因"""
    regional_culture: str             # L2 必填 | 地域文化主题（巴蜀/岭南/江南/西北/少数民族等）
    historical_context: str           # L3 建议 | 建筑历史/场地记忆/文化遗产级别
    vernacular_architecture: str      # L3 建议 | 传统建筑形制与构造工艺特征
    craft_traditions: list[str]       # L3 建议 | 可借用的地方工艺母题（竹编/青砖/夯土/刺绣等）
    taboo_styles: list[str]           # L2 必填 | 风格禁区列表（**硬约束，强制传播至SPG**）
    cultural_pressure: str            # L2 必填 | strong/moderate/weak（地方性强度）
    narrative_potential: str          # L3 建议 | 地点文化叙事张力与可挖掘深度评估


class MarketContext(BaseModel):
    """第五层：市场环境"""
    competitive_density: str          # L2 必填 | 低/中/高（直接竞品分布密度）
    competitors: list[dict]           # L3 建议 | [{"name": str, "level": str, "distance_km": float}]
    substitute_substitution: str      # L2 必填 | 周边强势餐饮/娱乐/景区对本项目的替代程度
    price_band: str                   # L2 必填 | 周边消费价格带与本项目定价空间
    traveler_itinerary_type: str      # L2 必填 | destination / transit / urban_cover（旅行者的串联方式）
    avg_stay_duration_days: float     # L3 建议 | 预期平均停留时长（天）
    seasonality: dict                 # L2 必填 | {"peak_months": [], "off_months": [], "peak_off_ratio": float}
    demand_drivers: list[str]         # L2 必填 | 主要需求驱动力（自然/文化/商务/社交/疗愈）
    competitive_gap: str              # L2 必填 | 周边市场未被填满的体验空白（差异化切入点）


class ConstraintsAndOpportunities(BaseModel):
    """第六层：约束与机会"""
    hard_geo_constraints: list[str]   # L2 必填 | 气候/地形带来的不可更改设计限制
    regulatory_constraints: list[str] # L2 必填 | 法规约束（风貌管控/退界限高/历史保护/消防特殊要求）
    supply_chain_constraints: list[str]  # L3 建议 | 材料运输/施工可行性限制（偏远地区）
    unique_opportunities: list[str]   # L2 必填 | 该地点设计上不可复制的优势
    risk_flags: list[dict]            # L2 必填 | [{"risk": str, "level": str, "mitigation": str}]
    # 说明：taboo_styles 在 cultural_dna 中定义，此处不重复，但约束卡必须引用


class WorldModelAnchor(BaseModel):
    """第七层：世界模型锚点"""
    place_identity: str               # L2 必填 | 地点不可替代身份的简洁命题（1-2句话）
    core_proposition: str             # L2 必填 | "在这里做空间，最不能绕开的核心问题是什么"
    with_the_grain_actions: list[str] # L2 必填 | 顺势设计动作（顺地点之势的设计方向）
    against_the_grain_risks: list[str]  # L2 必填 | 逆势风险（违背地点身份的设计方向）
    preliminary_problem_frame: str    # L2 必填 | 交付给 3.S.1 的主线问题雏形


class GeoCoordinateBaselineMetadata(BaseModel):
    """元数据层：版本与来源追溯"""
    version: str                      # L1 强制 | 格式：v1.0 / v1.x / provisional
    freeze_status: str                # L1 强制 | provisional / frozen / invalidated
    frozen_at: Optional[str]          # 冻结时间戳（ISO 8601）
    source_refs: list[str]            # 数据来源（用户文本/地图API/人工研究）
    geo_source: str                   # 坐标来源：map_pin / geocoder / manual_input
    poi_snapshot_at: Optional[str]    # POI数据快照时间（用于版本追溯）
    climate_snapshot_at: Optional[str]  # 气候数据快照时间
    competition_snapshot_at: Optional[str]  # 竞品数据快照时间
    confidence_level: str             # high / medium / low（整体数据置信度）
    manual_confirmed_by_user: bool    # 用户是否手动确认关键结论
    data_completeness: dict           # {"L1": 100%, "L2": 80%, "L3": 40%} 完整度报告


class GeoCoordinateBaseline(BaseModel):
    """
    地理坐标基线对象（世界模型第一输入状态）
    
    别名：GeoContextBaseline（部分文档使用）
    采集节点：geo_pin @ Node1（L1强制），其余字段 @ Node3.S.0（L2/L3）
    消费者：AlignedBrief / SPG / WorkMap / FloorPlanIR（间接）
    版本化：v1.0初次冻结 / v1.x局部更新 / DerivedProject（地点根本性变更）
    """
    project_id: str                              # 关联项目 ID
    geo_pin: GeoPin                              # L1 锚点层
    physical_context: PhysicalContext            # L1 第一层：物理地理
    accessibility_context: AccessibilityContext  # 第二层：到达与可达
    urban_semantic: UrbanSemantic                # 第三层：城市语义
    cultural_dna: CulturalDNA                    # 第四层：文化基因
    market_context: MarketContext                # 第五层：市场环境
    constraints_and_opportunities: ConstraintsAndOpportunities  # 第六层
    world_model_anchor: WorldModelAnchor         # 第七层：世界模型锚点
    metadata: GeoCoordinateBaselineMetadata      # 元数据
```

---

## 三、字段分级汇总表

| 字段 | 级别 | 采集节点 | 说明 |
|------|------|---------|------|
| `geo_pin.*`（全部5字段 + method + confirmed）| L1 强制 | Node1 | 缺失则门禁阻断 |
| `physical_context.elevation_m` | L2 必填 | Node3.S.0 | |
| `physical_context.terrain_type` | L2 必填 | Node3.S.0 | |
| `physical_context.climate_zone` | L2 必填 | Node3.S.0 | |
| `physical_context.humidity_level` | L2 必填 | Node3.S.0 | |
| `physical_context.landscape_resources` | L2 必填 | Node3.S.0 | |
| `physical_context.seasonal_pattern` | L2 必填 | Node3.S.0 | |
| `accessibility_context.arrival_fatigue` | L2 必填 | Node3.S.0 | 驱动首感设计优先级 |
| `accessibility_context.distance_to_*` | L2 必填 | Node3.S.0 | |
| `accessibility_context.first_impression_window` | L2 必填 | Node3.S.0 | |
| `urban_semantic.emotional_tone` | L2 必填 | Node3.S.0 | 直接进 SPG 风格锚点 |
| `urban_semantic.demographic_signal` | L2 必填 | Node3.S.0 | |
| `urban_semantic.place_identity_tags` | L2 必填 | Node3.S.0 | |
| `cultural_dna.taboo_styles` | **L2 强制（硬约束级）** | Node3.S.0 | 传播至SPG，有治理规则保障 |
| `cultural_dna.cultural_pressure` | L2 必填 | Node3.S.0 | |
| `market_context.seasonality` | L2 必填 | Node3.S.0 | |
| `market_context.competitive_gap` | L2 必填 | Node3.S.0 | |
| `market_context.demand_drivers` | L2 必填 | Node3.S.0 | |
| `constraints_and_opportunities.hard_geo_constraints` | L2 必填 | Node3.S.0 | |
| `constraints_and_opportunities.regulatory_constraints` | L2 必填 | Node3.S.0 | |
| `constraints_and_opportunities.unique_opportunities` | L2 必填 | Node3.S.0 | |
| `constraints_and_opportunities.risk_flags` | L2 必填 | Node3.S.0 | |
| `world_model_anchor.core_proposition` | L2 必填 | Node3.S.0 | 主线问题起点 |
| `world_model_anchor.preliminary_problem_frame` | L2 必填 | Node3.S.0 | 交付给3.S.1 |
| `physical_context.annual_precipitation_mm` | L3 建议 | Phase 2+ | 外部数据源自动填充 |
| `physical_context.local_material_base` | L3 建议 | Phase 2+ | |
| `market_context.competitors` | L3 建议 | 人工或Phase 2+ | |
| `cultural_dna.craft_traditions` | L3 建议 | 人工 | |
| `metadata.poi_snapshot_at` | L1+（有POI数据时） | 自动记录 | |

---

## 四、版本化规则

### 4.1 版本状态机

```
provisional
  │ (用户完成地图点选确认)
  ↓
draft（3.S.0 编译进行中）
  │ (L2 字段全部产出 + 用户确认关键结论)
  ↓
frozen v1.0（正式冻结，进入对象链）
  │
  ├── v1.x（局部字段补充，不触发重编译）
  │     └── 例：发现新竞品 → competition_snapshot_at更新 → v1.1
  │
  └── DerivedProject（地点根本性变更）
        └── 重新生成 v1.0，评估对AlignedBrief/SPG/WorkMap的影响
```

### 4.2 版本变更触发判断

| 变更类型 | 处理方式 |
|---------|---------|
| 补充市场数据/新竞品 | `v1.x` 局部更新，标注字段级 diff |
| 季节性数据更新 | `v1.x` 更新 `metadata.climate_snapshot_at` |
| 发现地点遗漏信息 | `v1.x` 补充，标注 `added_at` |
| 用户微调点位（同建筑群内） | `v1.x`，评估是否影响L2字段 |
| 选址迁移（不同区域/城市） | `DerivedProject`，重走3.S.0 |

### 4.3 历史版本保留规则

- 所有 `v1.x` 记录均保留，不覆盖
- `DerivedProject` 时，旧版本标记为 `invalidated`，但物理保留用于审计
- 当 `GeoCoordinateBaseline` 版本升级，必须通知所有消费者（`AlignedBrief / SPG / WorkMap`）评估影响

---

## 五、特殊字段说明

### 5.1 `taboo_styles`（风格禁区）—— 最强约束字段

- **治理地位**：本字段是整个 `GeoCoordinateBaseline` 中唯一具备"阻断级别"传播力的字段
- **传播路径**：`taboo_styles` → SPG `style_boundary`（硬约束）→ InitialDesignPack（硬约束）
- **覆盖权限**：无任何下游节点有权静默覆盖此字段内容；如需例外需走书面变更申请并记录原因
- **示例值**：`["欧式尖顶", "地中海白墙蓝顶", "Heavy Industrial风格"]`（峨眉山七里坪）

### 5.2 `emotional_tone`（情绪气质）—— emotional_tone 字段说明

- 来源：参考4（交叉校验采纳）
- 作用：直接为 SPG `strategy_scopes` 提供感知锚词，是视觉化呈现的隐性策略来源
- 推荐词汇来源：城市语义层综合判断（不是主观风格偏好）
- 示例值：`["山野沉浸", "松弛疗愈"]`（七里坪）/ `["云端顶级", "都市封面"]`（深圳湾壹号）

### 5.3 `preliminary_problem_frame`（主线问题雏形）—— 地理驱动的解题入口

- 作用：这不是最终解题思路，而是基于地理坐标推导出的"问题框架起点"
- 使用方式：3.S.1 解题思路必须读取此字段，在其基础上展开完整一主两辅框架
- 不得跳过：若此字段为空，`GeoCoordinateBaseline` 视为不完整，3.S.1 不得启动

---

## 六、与现有对象链的接口声明

```python
# AlignedBrief 读取接口
class AlignedBrief(BaseModel):
    geo_baseline_ref: str             # 引用 GeoCoordinateBaseline.project_id + version
    target_audience: str              # 从 geo_baseline.urban_semantic.demographic_signal 填入
    constraints: list[str]            # 从 geo_baseline.constraints_and_opportunities 填入
    success_criteria: str             # 包含 geo_baseline.market_context.competitive_gap

# SPG 读取接口
class SpatialProgramGraph(BaseModel):
    geo_baseline_ref: str             # 引用 GeoCoordinateBaseline
    style_boundary: list[str]         # 从 geo_baseline.cultural_dna.taboo_styles 强制填入
    strategy_scopes: list[str]        # 从 geo_baseline.world_model_anchor + urban_semantic.emotional_tone
    zone_geo_constraints: dict        # 从 geo_baseline.physical_context + accessibility_context

# WorkMap 读取接口
class WorkMap(BaseModel):
    geo_baseline_ref: str             # 引用 GeoCoordinateBaseline
    geo_driven_specialist_seats: list[str]   # 由 geo_baseline 触发的特殊专业席位
    geo_derived_tasks: list[str]      # 由 unique_opportunities 派生的专题任务
    risk_priority_override: list[str] # 由 risk_flags 影响的优先级排序
```
