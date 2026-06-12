# ConditionToLensMapping｜条件到上下文与透镜映射表 v1.1

版本：v1.1  
日期：2026-06-03  
定位：将 `project_conditions` 对齐到已冻结的 `context_vector` 字段，并映射到 13 lens。  
性质：接口映射表，不是内容清单。

---

# 1｜字段说明

| 字段 | 说明 |
|---|---|
| condition_dimension | v1.2.1 中的项目条件维度 |
| context_vector_field | 对齐后的 context_vector 字段 |
| primary_lens | 主 lens |
| secondary_lens | 辅助 lens |
| status | active_mvp / active_light / dormant_by_default |
| example_missing_slots | 该维度缺失时可能触发的项目缺口 |
| advisor_action | AdvisorAgent 处理动作 |
| runtime_effect | 运行时影响 |

---

# 2｜Condition → Context Vector → Lens 映射表

| condition_dimension | context_vector_field | primary_lens | secondary_lens | status | advisor_action |
|---|---|---|---|---|---|
| brand_stage | business_stage | MarketBusiness | LifecycleEvolution / BrandCommunication | active_mvp | branch_answer_plus_followup |
| site_context | site_context | GeoContext | ComplianceConstraint / OperationFlow | active_mvp | branch_answer_plus_followup |
| area_scale | area_scale | FunctionProgram | CostInvestment / OperationFlow | active_mvp | certainty_ceiling_then_followup |
| investment_boundary | investment_boundary | CostInvestment | MarketBusiness | active_mvp | branch_answer_plus_followup |
| service_mode | service_mode | OperationFlow | MarketBusiness / UserExperience | active_mvp | branch_answer_plus_followup |
| operation_pressure | operation_pressure | OperationFlow | RiskFailure / UserExperience | active_mvp | branch_answer_plus_followup |
| experience_goal | experience_goal | UserExperience | CultureEmotion / BrandCommunication | active_light | option_menu |
| standardization_intensity | standardization_intensity | MarketBusiness | FunctionProgram / LifecycleEvolution | active_light | branch_answer_plus_followup |
| sustainability_constraint | sustainability_constraint | ComplianceConstraint | MaterialMEP / CostInvestment / LifecycleEvolution | dormant_by_default | activate_only_if_mentioned |
| lifecycle_operation_mode | lifecycle_operation_mode | LifecycleEvolution | CostInvestment / OperationFlow | active_light | branch_answer_plus_followup |
| digital_integration_level | digital_integration_level | OperationFlow | MaterialMEP / KnowledgeGovernance | dormant_by_default | activate_only_if_mentioned |
| privacy_requirement | privacy_requirement | ComplianceConstraint | UserExperience / RiskFailure | dormant_by_default | activate_only_if_mentioned |

---

# 3｜Missing Slot 示例

```yaml
brand_stage:
  business_fact_slots:
    - brand_status
    - brand_maturity
    - expansion_stage

site_context:
  physical_constraint_slots:
    - site_type
    - floor_level
    - public_corridor_width
    - frontage_condition
  business_fact_slots:
    - surrounding_competition
    - foot_traffic_pattern

area_scale:
  physical_constraint_slots:
    - usable_area
    - frontage_width
    - depth
    - ceiling_height
    - structural_columns

investment_boundary:
  business_fact_slots:
    - total_budget
    - equipment_budget
    - fitout_budget
    - rent_level
    - expected_payback_period

service_mode:
  business_fact_slots:
    - takeaway_ratio
    - delivery_ratio
    - dine_in_ratio
    - appointment_ratio
    - membership_ratio

operation_pressure:
  business_fact_slots:
    - peak_15min_volume
    - daily_order_volume
    - turnover_target
    - staff_count

experience_goal:
  subjective_preference_slots:
    - privacy_preference
    - display_priority
    - social_media_priority
    - atmosphere_keywords

standardization_intensity:
  business_fact_slots:
    - replication_target
    - franchise_requirement
    - modular_requirement
    - prototype_testing_goal

sustainability_constraint:
  physical_constraint_slots:
    - green_certification_requirement
    - material_reuse_requirement
    - energy_efficiency_requirement
    - dfma_requirement

lifecycle_operation_mode:
  business_fact_slots:
    - operation_duration
    - seasonal_pattern
    - trial_period
    - phased_opening_plan

digital_integration_level:
  physical_constraint_slots:
    - weak_current_requirement
    - network_requirement
    - iot_device_requirement
    - data_system_requirement

privacy_requirement:
  physical_constraint_slots:
    - access_control_requirement
    - acoustic_privacy_requirement
    - visual_privacy_requirement
  business_fact_slots:
    - data_compliance_requirement
    - medical_privacy_requirement
```

---

# 4｜MEP Complexity 派生规则

```text
MaterialMEP 不作为普世 project_condition 强制追问。
mep_complexity 由 subdomain、activation_pack、user_input 共同推导。
```

## 4.1｜mep_complexity 取值

```text
low｜低机电复杂度
standard｜标准机电复杂度
high｜高机电复杂度
special｜特殊机电复杂度
unknown｜未知
```

## 4.2｜典型推导

```yaml
mep_complexity_rules:
  tea_drink_store: high
  coffee_shop: standard
  hotpot_restaurant: special
  chinese_restaurant: high
  dental_clinic: special
  aesthetic_clinic: special
  general_clinic: special
  business_hotel: high
  resort_hotel: high
  office_space: standard
  digital_infrastructure_hub: special
  home_theater: special
```

## 4.3｜触发缺口

```yaml
if mep_complexity in [high, special]:
  missing_slots:
    physical_constraint_slots:
      - power_capacity
      - water_supply
      - drainage
      - ventilation
      - exhaust_condition
      - ac_load
      - weak_current_capacity
```

---

# 5｜Advisor Action 解释

```text
certainty_ceiling_then_followup：
  首轮必要时追问；若用户跳过或已进入输出阶段，则封顶并标注不确定边界。

branch_answer_plus_followup：
  先给分支性判断，再提出关键缺口追问。

option_menu：
  给用户提供选项菜单，不强制判断。

activate_only_if_mentioned：
  默认不问、不计入置信度；只有用户明确提及或特定空间类型触发时激活。
```
