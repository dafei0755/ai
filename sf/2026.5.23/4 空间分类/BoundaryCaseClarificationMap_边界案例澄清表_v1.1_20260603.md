# BoundaryCaseClarificationMap｜边界案例澄清表 v1.1

版本：v1.1  
日期：2026-06-03  
定位：为空间分类系统中的高歧义输入提供触发、澄清、回退与优先级规则。  
性质：歧义保护协议，不是空间类型清单。

---

# 0｜全局处理顺序

当多个 boundary_case 同时触发时，按以下优先级处理：

```text
1. host_scope_conflict｜宿主关系与委托范围冲突
2. spatial_extent_lifecycle_conflict｜空间范围与项目阶段冲突
3. project_type_subdomain_conflict｜一级类型与细分业态冲突
4. mixed_use_project｜多业态复合
5. cross_industry_space｜跨行业语境
6. compliance_or_security_conflict｜合规、安全、隐私边界
7. activation_pack_conflict｜多知识包激活冲突
8. soft_preference_conflict｜体验偏好冲突
```

---

# 1｜边界案例字段模板

```yaml
boundary_case:
  case_id: ""
  priority: 0
  trigger_patterns:
    keyword_hits: []
    axis_conditions: []
    confidence_conditions: []
    co_occurrence_rules: []
  conflict_axes: []
  clarification_flow:
    round_1:
      question: ""
      target_axis: ""
    round_2:
      question: ""
      target_axis: ""
  fallback_output:
    confidence_level: low | conflict
    needs_clarification: true
    missing_slots:
      physical_constraint_slots: []
      business_fact_slots: []
      subjective_preference_slots: []
    activation_pack:
      primary_pack_id: ""
      secondary_pack_ids: []
    advisor_action: branch_answer_plus_followup | certainty_ceiling | option_menu
```

---

# 2｜边界案例清单

## BC-01｜mixed_use_project｜复合业态项目

```yaml
case_id: mixed_use_project
priority: 40
trigger_patterns:
  keyword_hits: ["复合", "一体", "同时", "兼", "混合", "多功能"]
  axis_conditions:
    - "count(subdomain.primary + subdomain.secondary) >= 2"
  co_occurrence_rules:
    - "commercial_dining + commercial_office"
    - "commercial_retail + coffee_shop"
    - "office + private_tea_room"
conflict_axes:
  - subdomain
  - activation_pack
  - commission_scope
clarification_flow:
  round_1:
    question: "本次设计的主委托范围是什么？"
    target_axis: commission_scope
  round_2:
    question: "哪个功能承担主要收入或主要使用目标？"
    target_axis: primary_revenue_subject
fallback_output:
  confidence_level: conflict
  needs_clarification: true
  missing_slots:
    business_fact_slots:
      - commission_scope
      - primary_revenue_subject
  activation_pack:
    primary_pack_id: hybrid_composite_pack
    secondary_pack_ids: []
  advisor_action: branch_answer_plus_followup
```

## BC-02｜cross_industry_space｜跨行业空间

```yaml
case_id: cross_industry_space
priority: 50
trigger_patterns:
  axis_conditions:
    - "industry_domain.source == explicit"
    - "industry_domain_id != default_industry_domain_for_subdomain"
  co_occurrence_rules:
    - "coffee_shop + automotive"
    - "tea_drink_store + technology_ai"
    - "retail_store + healthcare_medical"
conflict_axes:
  - subdomain
  - industry_domain
  - activation_pack
clarification_flow:
  round_1:
    question: "这个空间的主目标是经营收入、品牌体验，还是配套服务？"
    target_axis: primary_revenue_subject
  round_2:
    question: "行业属性会不会改变合规、动线、设备或隐私要求？"
    target_axis: industry_domain
fallback_output:
  confidence_level: medium
  needs_clarification: true
  missing_slots:
    business_fact_slots:
      - primary_revenue_subject
      - industry_domain_role
  activation_pack:
    primary_pack_id: ""
    secondary_pack_ids: []
  advisor_action: branch_answer_plus_followup
```

## BC-03｜space_with_multiple_hosts｜多宿主空间

```yaml
case_id: space_with_multiple_hosts
priority: 20
trigger_patterns:
  keyword_hits: ["楼里", "园区内", "学校里", "医院里", "写字楼里", "商场里"]
  axis_conditions:
    - "host_project_type_id exists"
    - "subdomain.primary_subdomain_id differs from host_project_type_id"
conflict_axes:
  - project_type
  - subdomain
  - host_context
clarification_flow:
  round_1:
    question: "本次委托是设计宿主空间整体，还是设计其中的一个独立业态？"
    target_axis: commission_scope
fallback_output:
  confidence_level: medium
  needs_clarification: true
  missing_slots:
    business_fact_slots:
      - host_context
      - commission_scope
  activation_pack:
    primary_pack_id: ""
    secondary_pack_ids: []
  advisor_action: branch_answer_plus_followup
```

## BC-04｜subdomain_project_type_conflict｜业态与一级类型冲突

```yaml
case_id: subdomain_project_type_conflict
priority: 30
trigger_patterns:
  axis_conditions:
    - "subdomain.parent_project_type_id != project_type_id"
    - "host_context is unknown"
conflict_axes:
  - project_type
  - subdomain
clarification_flow:
  round_1:
    question: "这个业态是项目主体，还是嵌入在另一个空间中的配套功能？"
    target_axis: subdomain_role
fallback_output:
  confidence_level: low
  needs_clarification: true
  missing_slots:
    business_fact_slots:
      - subdomain_role
      - host_context
  activation_pack:
    primary_pack_id: ""
    secondary_pack_ids: []
  advisor_action: branch_answer_plus_followup
```

## BC-05｜industry_domain_subdomain_overlap｜行业语境与细分业态重叠

```yaml
case_id: industry_domain_subdomain_overlap
priority: 55
trigger_patterns:
  axis_conditions:
    - "industry_domain.source == derived"
    - "industry_domain_id == default_industry_domain_for_subdomain"
conflict_axes:
  - industry_domain
  - subdomain
clarification_flow:
  round_1:
    question: "行业语境是否会额外改变设计判断，还是仅由业态自动派生？"
    target_axis: industry_domain
fallback_output:
  confidence_level: high
  needs_clarification: false
  missing_slots: {}
  activation_pack:
    primary_pack_id: ""
    secondary_pack_ids: []
  advisor_action: certainty_ceiling
```

## BC-06｜residential_business_mixed｜住商混合项目

```yaml
case_id: residential_business_mixed
priority: 45
trigger_patterns:
  keyword_hits: ["前店后宅", "下店上居", "自住兼经营", "工作室住宅", "商住一体"]
  co_occurrence_rules:
    - "personal_residential + operating_business"
    - "residential + commercial_dining"
    - "residential + commercial_retail"
conflict_axes:
  - project_type
  - founding_type
  - spatial_extent
clarification_flow:
  round_1:
    question: "本次设计以居住为主，还是以经营空间为主？"
    target_axis: primary_revenue_subject
  round_2:
    question: "居住与经营是否需要物理分离、分时使用或独立出入口？"
    target_axis: physical_constraint_slots
fallback_output:
  confidence_level: conflict
  needs_clarification: true
  missing_slots:
    business_fact_slots:
      - primary_revenue_subject
    physical_constraint_slots:
      - independent_entrance
      - privacy_boundary
  activation_pack:
    primary_pack_id: hybrid_residential_commercial_pack
    secondary_pack_ids: []
  advisor_action: branch_answer_plus_followup
```

## BC-07｜heritage_commercial_reuse｜历史建筑商业活化

```yaml
case_id: heritage_commercial_reuse
priority: 22
trigger_patterns:
  keyword_hits: ["历史建筑", "老建筑", "保护建筑", "老粮仓", "老厂房", "老街区", "文保"]
  co_occurrence_rules:
    - "heritage_site + operating_business"
    - "adaptive_reuse + commercial_retail"
    - "adaptive_reuse + commercial_dining"
conflict_axes:
  - lifecycle
  - spatial_extent
  - compliance_constraint
clarification_flow:
  round_1:
    question: "该建筑是否涉及文保、历史风貌、结构保护或消防改造限制？"
    target_axis: physical_constraint_slots
  round_2:
    question: "商业功能是否需要新增重机电、排烟、排水或高客流承载？"
    target_axis: physical_constraint_slots
fallback_output:
  confidence_level: medium
  needs_clarification: true
  missing_slots:
    physical_constraint_slots:
      - heritage_protection_level
      - fire_upgrade_limit
      - structure_modification_limit
      - mep_upgrade_limit
  activation_pack:
    primary_pack_id: heritage_adaptive_reuse_pack
    secondary_pack_ids: []
  advisor_action: branch_answer_plus_followup
```

## BC-08｜brand_space_not_retail｜品牌空间但非零售

```yaml
case_id: brand_space_not_retail
priority: 60
trigger_patterns:
  keyword_hits: ["品牌空间", "体验中心", "会员中心", "品牌会客厅", "NIO House", "品牌之家"]
  axis_conditions:
    - "project_type_id == brand_experience"
    - "operating_business not explicit"
conflict_axes:
  - project_type
  - subdomain
  - founding_type
clarification_flow:
  round_1:
    question: "这个空间的主要目标是销售转化、品牌体验、会员服务，还是客户接待？"
    target_axis: primary_revenue_subject
fallback_output:
  confidence_level: medium
  needs_clarification: true
  missing_slots:
    business_fact_slots:
      - primary_revenue_subject
      - sales_function_ratio
  activation_pack:
    primary_pack_id: brand_experience_pack
    secondary_pack_ids: []
  advisor_action: branch_answer_plus_followup
```

## BC-09｜office_vs_enterprise_showroom｜办公与企业展厅边界

```yaml
case_id: office_vs_enterprise_showroom
priority: 35
trigger_patterns:
  keyword_hits: ["总部", "展厅", "接待", "企业展示", "办公", "会客"]
  co_occurrence_rules:
    - "commercial_office + commercial_enterprise"
conflict_axes:
  - project_type
  - subdomain
  - founding_type
clarification_flow:
  round_1:
    question: "本次设计主要服务日常办公，还是客户展示接待？"
    target_axis: commission_scope
fallback_output:
  confidence_level: medium
  needs_clarification: true
  missing_slots:
    business_fact_slots:
      - commission_scope
      - visitor_ratio
  activation_pack:
    primary_pack_id: office_space_pack
    secondary_pack_ids:
      - enterprise_showroom_pack
  advisor_action: branch_answer_plus_followup
```

## BC-10｜healthcare_vs_wellness｜医疗健康与疗愈康养边界

```yaml
case_id: healthcare_vs_wellness
priority: 25
trigger_patterns:
  keyword_hits: ["疗愈", "康养", "健康管理", "诊所", "心理", "冥想", "医疗"]
  co_occurrence_rules:
    - "healthcare_wellness + healing_repair"
    - "wellness_center + medical_privacy_required"
conflict_axes:
  - project_type
  - subdomain
  - privacy_requirement
clarification_flow:
  round_1:
    question: "该空间是否涉及医疗诊疗、医疗隐私或执业许可？"
    target_axis: compliance_constraint
fallback_output:
  confidence_level: medium
  needs_clarification: true
  missing_slots:
    physical_constraint_slots:
      - medical_license_requirement
      - sanitation_requirement
    business_fact_slots:
      - service_scope
  activation_pack:
    primary_pack_id: healthcare_wellness_pack
    secondary_pack_ids: []
  advisor_action: branch_answer_plus_followup
```

---

# 3｜Generic Conflict Rules｜通用冲突检测

```yaml
generic_conflict_rules:
  - rule_id: site_lifecycle_conflict
    if:
      site_context: heritage_site
      lifecycle: newbuild
    then:
      boundary_case_id: heritage_commercial_reuse

  - rule_id: temporary_vs_long_term_conflict
    if:
      lifecycle: temporary
      lifecycle_operation_mode: long_term_operation
    then:
      boundary_case_id: spatial_extent_lifecycle_conflict

  - rule_id: high_privacy_vs_high_display_conflict
    if:
      experience_goal:
        - high_privacy
        - high_display
    then:
      boundary_case_id: soft_preference_conflict

  - rule_id: dormant_dimension_mentioned
    if:
      user_input_mentions:
        - ESG
        - IoT
        - 数据安全
        - 医疗隐私
    then:
      activate_corresponding_dormant_dimension: true
```

---

# 4｜运行纪律

```text
boundary_case 不直接给 project_type 加分。
boundary_case 只负责识别歧义、触发澄清、降低置信、生成缺口。
```

```text
如果多个 boundary_case 同时触发，先按优先级排序。
优先处理宿主关系、委托范围、空间范围、项目阶段。
再处理业态复合、跨行业语境、多知识包冲突。
最后处理偏好冲突。
```

```text
无法消解时，不硬猜。
输出 conflict 或 low confidence。
把关键缺口写入 missing_slots。
交给 AdvisorAgent 执行分支回答与追问。
