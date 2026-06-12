# ConditionDimensionStatus｜条件维度状态表 v1.1

版本：v1.1  
日期：2026-06-03  
定位：规定 project_conditions 各维度在 Year-1 MVP 中是否主动追问、是否参与置信度、是否可休眠。  
性质：运行策略表，不是内容清单。

---

# 1｜状态定义

```text
active_mvp：
Year-1 默认启用。可进入首轮追问，可参与置信度，可触发 missing_slots。

active_light：
轻量启用。通常不作为第一轮硬追问，除非上下文高度相关。

dormant_by_default：
默认休眠。Schema 保留，但不主动追问，不参与默认置信度。用户明确提及、特定空间类型触发或边界案例需要时才激活。
```

---

# 2｜维度状态表

| condition_dimension | context_vector_field | status | first_round_followup | included_in_confidence | activation_rule |
|---|---|---|---|---|---|
| brand_stage | business_stage | active_mvp | 可追问 | 是 | 用户提及品牌、新店、升级、旗舰、标准店 |
| site_context | site_context | active_mvp | 必要时追问 | 是 | 用户提及商场、街边、社区、写字楼、乡村等 |
| area_scale | area_scale | active_mvp | 必要时追问 | 是 | 用户给出面积、户型、建筑规模；缺失则可追问 |
| investment_boundary | investment_boundary | active_mvp | 必要时追问 | 是 | 用户给出预算、成本、造价、租金、回本期 |
| service_mode | service_mode | active_mvp | 可追问 | 是 | 用户提及堂食、外带、外卖、预约、会员 |
| operation_pressure | operation_pressure | active_mvp | 可追问 | 是 | 用户提及高峰、翻台、人流、订单、排队 |
| experience_goal | experience_goal | active_light | 不默认强追问 | 条件性 | 用户提及私密、展示、社媒、疗愈、仪式感 |
| standardization_intensity | standardization_intensity | active_light | 不默认强追问 | 条件性 | 用户提及连锁、加盟、复制、标准店、模块化 |
| sustainability_constraint | sustainability_constraint | dormant_by_default | 不主动追问 | 否 | 用户明确提及 ESG、低碳、绿建、旧材再利用 |
| lifecycle_operation_mode | lifecycle_operation_mode | active_light | 不默认强追问 | 条件性 | 用户提及短期、长期、试运营、分期、季节性 |
| digital_integration_level | digital_integration_level | dormant_by_default | 不主动追问 | 否 | 用户明确提及智能、IoT、数字孪生、自动化 |
| privacy_requirement | privacy_requirement | dormant_by_default | 不主动追问 | 否 | 用户明确提及保密、隐私、金融、医疗、高管 |

---

# 3｜included_in_confidence 规则

```text
是：
默认参与分类置信度与下游路由判断。

条件性：
仅在用户明确提及、命中特定 project_type / subdomain / boundary_case 时参与置信度。

否：
默认不参与分类置信度，仅在激活后写入输出并提示其为附加约束。
```

---

# 4｜active_light 的上下文高度相关定义

```text
以下情况可激活 active_light：
1. 用户直接使用该维度相关关键词。
2. project_type / subdomain 高度依赖该维度。
3. boundary_case 澄清需要该维度。
4. activation_pack 明确要求该维度作为判断输入。
5. AdvisorAgent 判断该维度会改变下一句核心判断。
```

---

# 5｜dormant_by_default 激活规则

## 5.1｜sustainability_constraint

```text
激活关键词：
ESG、低碳、绿色建筑、可持续、旧材料再利用、装配式、可拆卸、碳排、绿色认证

自动激活空间：
总部办公
酒店
公共建筑
商业综合体
海外项目
政府 / 国企项目
大型城市更新项目
```

## 5.2｜digital_integration_level

```text
激活关键词：
智能控制、IoT、数字孪生、自动化、数据驱动、无人化、弱电系统、智能运营

自动激活空间：
科技办公
直播基地
数据中心
智能零售
汽车体验中心
总部办公
数字媒体空间
```

## 5.3｜privacy_requirement

```text
激活关键词：
保密、高管、私密、金融合规、医疗隐私、数据安全、独立门禁、客户私密接待

自动激活空间：
律所办公
金融办公
医疗诊所
心理咨询
高端私宅
总部高管层
政府 / 国企项目
```

---

# 6｜首轮追问纪律

```text
active_mvp：
允许进入第一轮追问，但单轮追问不得超过最关键的 3–5 个变量。

active_light：
原则上不进入第一轮硬追问，除非该变量会直接改变项目成立判断。

dormant_by_default：
不主动追问。只有用户明确提到，或边界案例必须澄清时才进入追问。
```

---

# 7｜封顶纪律

```text
如果 active_mvp 维度缺失：
  先判断是否属于物理硬约束或经营事实。
  如影响项目成立，可追问。
  如用户跳过，则进入 certainty_ceiling。

如果 active_light 维度缺失：
  不阻塞输出。
  以假设条件或选项形式表达。

如果 dormant 维度缺失：
  不视为缺口。
```
