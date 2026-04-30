# 02 TemporalBaseline 字段契约

> 本文档是 `TemporalBaseline` 对象的字段定义与版本化规则。
>
> 关联文档：`01-时间维度专项总览.md`

---

## 一、字段分级说明

| 级别 | 含义 | 采集节点 |
|------|------|---------|
| **L2 必填** | 在 Node3.S.0.6 编译时必须产出，否则 `TemporalBaseline` 不得冻结 | Node3.S.0.6 |
| **L3 建议** | 提升分析质量，缺失不阻断 | Node3.S.0.6 / Node4 |

---

## 二、字段契约（Pydantic 风格）

```python
class TemporalPhaseProfile(BaseModel):
    phase_id: str                    # L2 | T1/T2/T3/T4
    phase_name: str                  # L2 | 新建/稳定/老化/更新
    objective: str                   # L2 | 该阶段核心目标
    risks: list[str]                 # L2 | 该阶段主要风险
    triggers_to_next: list[str]      # L3 | 转入下一阶段触发条件

class TemporalBaselineMetadata(BaseModel):
    version: str                     # L2 | v1.0 / v1.x / provisional
    freeze_status: str               # L2 | provisional / frozen / invalidated
    frozen_at: Optional[str]         # L3 | 冻结时间戳
    source_refs: list[str]           # L2 | 来源（访谈/运营数据/经验库）
    confidence_level: str            # L2 | high / medium / low

class TemporalBaseline(BaseModel):
    project_id: str                                  # L2

    day_cycle_profile: dict                          # L2 | 晨/昼/暮/夜节律
    week_cycle_profile: dict                         # L2 | 工作日/周末差异
    season_cycle_profile: dict                       # L2 | 淡旺季/季节切换

    lifecycle_stages: list[TemporalPhaseProfile]     # L2 | T1-T4 生命周期阶段
    maintenance_windows: list[dict]                  # L2 | 维护窗口与停机策略

    experience_timeline_targets: dict                # L2 | 初见/久处/复访体验目标
    obsolescence_risks: list[str]                    # L2 | 风格/设备/运营过时风险
    temporal_assumptions: list[str]                  # L2 | 时间关键假设

    metadata: TemporalBaselineMetadata               # L2
```

---

## 三、最小必填字段清单（冻结门槛）

- `day_cycle_profile`
- `week_cycle_profile`
- `season_cycle_profile`
- `lifecycle_stages`（至少覆盖 T1/T2/T3/T4）
- `maintenance_windows`
- `experience_timeline_targets`
- `temporal_assumptions`
- `metadata.version`
- `metadata.freeze_status`

若任一缺失：标记 `BLOCKED`，不得冻结。

---

## 四、版本化规则

### 4.1 状态机

```text
provisional
  ↓（Node3.S.0.6 完整编译）
frozen v1.0
  ├─ v1.x（局部更新：维护窗口、季节参数微调）
  └─ invalidated（基础假设失效，回退 Node3 重新编译）
```

### 4.2 触发条件

| 变更类型 | 处理方式 |
|---|---|
| 维护窗口微调 | `v1.x` |
| 季节模式参数修订 | `v1.x` |
| 生命周期阶段重定义（如 T2/T3 边界重写） | 回退 Node3，重新编译并冻结 |
| 关键时间假设推翻 | `invalidated` + 回退 Node3 |

---

## 五、与下游对象接口声明

```python
# SPG 读取接口（示意）
spg.active_time_windows <- temporal.day_cycle_profile + week_cycle_profile
spg.seasonal_mode <- temporal.season_cycle_profile
spg.maintenance_access_windows <- temporal.maintenance_windows

# InitialDesignPack 读取接口（示意）
initial_design.lifecycle_decisions <- temporal.lifecycle_stages
initial_design.temporal_risks <- temporal.obsolescence_risks
initial_design.temporal_assumptions <- temporal.temporal_assumptions
```

---

## 六、与 GeoCoordinateBaseline 的并列关系

- `GeoCoordinateBaseline`：地点与场地约束真相源
- `TemporalBaseline`：时间与演化约束真相源

二者共同作用于对象链冻结，不存在主从替代关系。
