# Space Classification List｜空间分类清单 v1.2.1

版本：v1.2.1  
日期：2026-06-03  
定位：方案高参空间分类系统核心协议。  
性质：分类协议，不是知识内容目录，不是 activation pack 清单，不是任务书模板。  

## 0｜本版核心修正

```text
1. 文档命名保留中英文。
2. “餐饮 / 夜生活空间”统一改为“餐饮空间”。
3. activation_pack 明确为 derived_outputs，不再作为分类轴。
4. project_conditions 保持强类型键值对结构，并对齐 context_vector 字段。
5. industry_domain 定义为行业语境修正器，支持 derived / explicit / unknown。
6. subdomain 改为 primary + secondary + complement_roles 结构。
7. missing_slots 回归三类项目缺口，不混入 evidence / governance 缺口。
8. 增加 inferred_context.mep_complexity，由 subdomain / activation_pack / user_input 推导。
9. 增加 resolution_context，用于复合业态与边界案例消解。
10. system_links 增加 condition_to_context_vector_mapping_id。
```

---

# 1｜Core Classification Axes｜核心分类轴

## 1.1｜Project Type｜一级空间机制

定义：`project_type` 回答“这是什么大类空间机制”。  
规则：`project_type` 是父类空间机制，不承接所有细分业态。细分业态进入 `subdomain`。

### 01｜居住住宅类

```text
personal_residential｜个人住宅
residential_renovation｜存量住宅改造 / 二手房翻新
residential_collective｜集合住宅 / 公共住房
hybrid_residential_commercial｜住商混合 / 复合业态空间
```

### 02｜酒店民宿与度假类

```text
commercial_hospitality｜酒店民宿 / 度假
```

### 03｜餐饮类

```text
commercial_dining｜餐饮空间
```

### 04｜商业零售与品牌体验类

```text
commercial_retail｜商业零售 / 综合体
brand_experience｜品牌旗舰 / 体验店
real_estate_showcase｜地产样板房 / 售楼展示
automotive_showroom｜汽车展厅 / 4S店 / 改装
beauty_personal_care｜美容美发 / 生活美学门店
popup_temporary｜快闪 / 临时装置空间
```

### 05｜办公、企业与媒体类

```text
commercial_office｜办公 / 联合办公
commercial_enterprise｜企业空间 / 品牌展厅
digital_media_studio｜直播 / 拍摄 / 媒体基地
```

### 06｜文化、展陈与教育类

```text
public_cultural｜文化展陈 / 科教场馆
educational_facility｜教育建筑 / 校园
```

### 07｜医疗、康养与照护类

```text
healthcare_wellness｜医疗 / 康养 / 养老
```

### 08｜体育、娱乐、演艺与儿童类

```text
sports_entertainment_arts｜体育 / 健身 / 运动场馆
leisure_entertainment｜休闲娱乐 / 水会棋牌KTV
performing_arts｜演艺 / 剧场空间
wedding_banquet｜婚庆宴会 / 庆典空间
children_family｜亲子 / 早教 / 儿童空间
```

### 09｜城市更新、乡村与公共空间类

```text
urban_renewal_market｜城市更新 / 公共市场
urban_renewal_heritage｜城市更新 / 历史建筑活化
rural_construction｜乡建 / 新农村建设
community_public｜社区 / 公共服务空间
landscape_outdoor｜景观 / 公共户外空间
transportation_civic｜交通 / 市政 / 公共行政
```

### 10｜工业、宗教与专项功能类

```text
industrial_conversion｜工业 / 生产设施 / 厂房改造
religious_spiritual｜宗教 / 仪式 / 殡葬空间
special_function｜专项功能空间
```

---

## 1.2｜Subdomain｜细分业态

定义：`subdomain` 回答“这个项目具体是哪种业态”。  
规则：`subdomain` 是受控业态标签，不是完整本体真相；以 `primary_subdomain_id` 为主路由；复合项目允许 `secondary_subdomain_ids` 与 `complement_roles`。

```yaml
subdomain:
  primary_subdomain_id: ""
  secondary_subdomain_ids: []
  complement_roles:
    - subdomain_id: ""
      role: support | attractor | amenity | revenue | brand_expression | membership_service
```

### 01｜餐饮类细分

```text
tea_drink_store｜茶饮店
coffee_shop｜咖啡馆
chinese_restaurant｜中餐厅
hotpot_restaurant｜火锅店
bbq_restaurant｜烧烤店
japanese_restaurant｜日料店
western_restaurant｜西餐厅
fast_food｜快餐店
canteen｜食堂
bar_lounge｜酒吧 / Lounge
tea_room｜茶室
buffet_restaurant｜自助餐厅
bakery_cafe｜烘焙咖啡 / 面包店
dessert_shop｜甜品店
```

### 02｜酒店民宿与度假细分

```text
business_hotel｜商务酒店
boutique_hotel｜精品酒店
resort_hotel｜度假酒店
luxury_hotel｜奢华酒店
conference_hotel｜会议会展酒店
airport_hotel｜机场酒店
hot_spring_resort｜温泉度假酒店
serviced_apartment｜服务式公寓
urban_homestay｜城市民宿
rural_homestay｜乡村民宿
homestay_cluster｜民宿集群
camping_resort｜露营营地
treehouse_homestay｜树屋民宿
glamping_tent_hotel｜帐篷酒店
```

### 03｜办公与企业细分

```text
headquarters_office｜总部办公
startup_office｜创业办公室
coworking_space｜联合办公
technology_office｜科技公司办公
rnd_office｜研发办公
law_firm_office｜律所办公
financial_office｜金融办公
sales_office｜销售型办公
call_center｜客服 / 呼叫中心
government_office｜政府 / 国企办公
creative_studio_office｜设计创意办公
hybrid_office｜混合办公
industrial_park_office｜园区 / 产业办公
```

### 04｜商业零售与品牌体验细分

```text
fashion_retail｜服装零售
luxury_retail｜奢侈品零售
jewelry_store｜珠宝店
eyewear_store｜眼镜店
beauty_store｜美妆店
lifestyle_store｜生活方式店
select_shop｜买手店
supermarket｜超市 / 精品超市
convenience_store｜便利店
bookstore_retail｜书店 / 文化零售
home_lifestyle_store｜家居生活方式店
flagship_store｜品牌旗舰店
concept_store｜概念店
auto_showroom｜汽车展厅
auto_4s_store｜4S 店
auto_modification_store｜汽车改装店
beauty_salon｜美容院
hair_salon｜美发沙龙
nail_salon｜美甲店
aesthetic_lifestyle_store｜生活美学门店
popup_store｜快闪店
temporary_exhibition_space｜临时展陈空间
```

### 05｜医疗、康养与照护细分

```text
general_clinic｜综合诊所
dental_clinic｜牙科诊所
aesthetic_clinic｜医美诊所
tcm_clinic｜中医馆
rehabilitation_center｜康复中心
postpartum_center｜月子中心
elderly_care_center｜养老照护中心
senior_living_community｜养老社区
psychological_counseling｜心理咨询空间
wellness_center｜健康管理 / 体检中心
pet_hospital｜宠物医院
sensory_integration_center｜感统训练中心
hospice_care_center｜临终关怀中心
medical_laboratory｜医学实验室
```

### 06｜文化、展陈与教育细分

```text
museum｜博物馆
art_museum｜美术馆
gallery｜画廊
exhibition_center｜展览中心
visitor_center｜游客中心
science_center｜科学中心
library｜图书馆
public_culture_center｜公共文化中心
kindergarten｜幼儿园
primary_school｜小学
secondary_school｜中学
university_campus｜大学校园
training_center｜培训中心
study_tour_base｜研学基地
research_institute｜研究机构
campus_facility｜校园配套空间
```

### 07｜体育、娱乐、演艺与儿童细分

```text
fitness_gym｜健身房
sports_center｜体育中心
swimming_pool｜游泳馆 / 游泳池
climbing_gym｜攀岩馆
esports_center｜电竞馆
ktv｜KTV
mahjong_room｜棋牌室 / 麻将馆
bathhouse_spa｜水会 / 洗浴中心
escape_room｜密室逃脱
script_murder｜剧本杀
arcade_game_center｜电玩城 / 游戏厅
billiards_club｜台球厅
theater｜剧场
concert_hall｜音乐厅
cinema｜电影院
wedding_hall｜婚礼堂
banquet_hall｜宴会厅
children_playground｜儿童乐园
early_education_center｜早教中心
parent_child_restaurant｜亲子餐厅
```

### 08｜城市更新、乡村与公共空间细分

```text
public_market｜公共市场 / 菜市场
heritage_adaptive_reuse｜历史建筑活化
industrial_heritage_reuse｜工业遗存活化
old_street_renewal｜老街区更新
urban_village_renewal｜城中村更新
community_center｜社区中心
neighborhood_service_center｜邻里服务中心
elderly_canteen｜长者食堂
community_kitchen｜社区共享厨房
emergency_shelter｜应急避难空间
urban_living_room｜城市公共客厅
rural_public_space｜乡村公共空间
rural_homestay_cluster｜乡村民宿集群
agritourism_center｜农文旅中心
transport_hub｜交通枢纽
civic_service_center｜市政服务中心
```

### 09｜工业、生产与专项功能细分

```text
factory_conversion｜厂房改造
warehouse_conversion｜仓库改造
industrial_park_conversion｜工业园区改造
winery｜酒庄 / 酿酒空间
production_facility｜生产设施
digital_infrastructure_hub｜算力中心 / 数据机房 / 智能前置仓 / 自动化分拣空间
home_theater｜家庭影院 / 影音室
private_tea_room｜私人茶室
study_room｜书房
walk_in_closet｜衣帽间
wine_cellar｜酒窖
cigar_room｜雪茄室
meditation_room｜冥想室
yoga_room｜瑜伽房
recording_studio｜录音棚
private_gallery｜私人画廊
collection_room｜收藏室
esports_training_room｜电竞训练空间
pet_friendly_home｜宠物友好住宅
barrier_free_home｜无障碍住宅
religious_chapel｜礼拜堂 / 教堂
temple_space｜寺庙 / 佛堂
funeral_memorial_space｜殡葬 / 纪念空间
```

---

## 1.3｜Founding Type｜项目成立方式

定义：`founding_type` 回答“这个项目为什么成立”。  
规则：只表达 Why，不表达空间类型、空间范围、生命周期。

```text
operating_business｜经营性项目
flagship_demonstration｜旗舰示范 / 标杆样板
commercial_renewal｜商业更新 / 存量商业改造
asset_value_upgrade｜资产价值提升 / 存量资产盘活
personal_use｜自用 / 私人生活项目
family_legacy｜家族传承 / 家庭秩序重建
identity_expression｜身份表达 / 精神画像项目
healing_repair｜疗愈修复 / 情绪与关系支持
special_needs_care｜特殊需求照护 / 无障碍 / 医疗适配
urban_renewal｜城市更新 / 街区微更新
rural_revitalization｜乡村振兴 / 农文旅激活
organizational_efficiency｜组织效能 / 高精办公空间
public_service｜公共服务 / 民生与社区效益
cultural_institution｜文化机构 / 公共文化与展示
hybrid_composite｜复合性质项目
```

---

## 1.4｜Spatial Extent｜空间范围

```text
interior｜室内
building｜建筑 / 单体
site｜场地
cluster｜建筑群 / 园区 / 集群
district｜街区 / 片区
regional｜区域 / 全域
```

---

## 1.5｜Lifecycle｜项目阶段

```text
fitout｜装修 / 开店 / 精装
renovation｜改造 / 翻新 / 重装
adaptive_reuse｜活化 / 再生 / 适应性改造
newbuild｜新建
temporary｜快闪 / 临时 / 限时
operation_maintenance｜运营维护 / 微更新
```

---

## 1.6｜Industry Domain｜行业语境修正器

定义：`industry_domain` 回答“这个空间服务哪个行业语境”。  
规则：当 `subdomain` 已能稳定推导行业时，可自动派生；当空间业态与行业主体发生跨界变异时，必须显式激活。

```text
legal_service｜法律服务
technology_ai｜科技 / AI / 互联网
financial_service｜金融服务
healthcare_medical｜医疗健康
education_training｜教育培训
culture_art｜文化艺术
automotive｜汽车行业
retail_apparel_luxury｜时尚 / 奢侈品零售
eyewear_optical｜眼镜视光
pet_service｜宠物服务
food_beverage｜餐饮饮品
hospitality_tourism｜酒店旅游
real_estate_development｜地产开发
community_service｜社区服务
public_government｜公共政府
sports_fitness｜体育健身
entertainment_media｜娱乐媒体
beauty_wellness｜美容健康
education_childcare｜教育托育
cultural_creative｜文化创意
manufacturing_industrial｜制造工业
agriculture_rural｜农业乡村
digital_infrastructure｜数字基础设施
```

---

# 2｜Project Conditions｜结构化项目条件

```text
定义：
project_conditions 回答“这个项目有哪些影响设计判断的关键变量”。

规则：
project_conditions 直接对齐 context_vector 字段。
同一维度内部尽量互斥。
不同维度之间可以组合。
```

## 2.1｜brand_stage｜品牌阶段

```text
new_brand｜新品牌
existing_brand｜既有品牌
brand_upgrade｜品牌升级
flagship_store｜旗舰店
standard_store｜标准店
```

## 2.2｜site_context｜场地语境

```text
mall_store｜商场店
street_store｜街边店
community_store｜社区店
campus_store｜校园店
tourism_site｜文旅场地
transport_hub｜交通枢纽
office_building｜写字楼
industrial_park｜产业园区
residential_community｜社区底商
heritage_site｜历史建筑 / 老街区
rural_site｜乡村场地
```

## 2.3｜area_scale｜面积尺度

```text
micro_area｜微型面积
small_area｜小面积
medium_area｜中等面积
large_area｜大面积
super_large_area｜超大面积
unknown_area｜面积未知
```

## 2.4｜investment_boundary｜投资边界

```text
limited_budget｜预算有限
standard_budget｜标准预算
high_budget｜高预算
luxury_budget｜奢华预算
unknown_budget｜预算未知
```

## 2.5｜service_mode｜服务模式

```text
takeaway_priority｜外带优先
delivery_priority｜外卖优先
dine_in_priority｜堂食优先
balanced_channel｜均衡渠道
online_first｜线上优先
appointment_based｜预约制
membership_based｜会员制
```

## 2.6｜operation_pressure｜运营压力

```text
standard_flow｜标准流量
high_peak_pressure｜高峰压力强
fast_turnover｜高翻台
long_stay｜长停留
low_frequency_high_value｜低频高客单
high_frequency_low_value｜高频低客单
```

## 2.7｜experience_goal｜体验目标

```text
high_privacy｜高私密
high_display｜强展示
high_social_media｜强社媒传播
customized_experience｜强定制体验
sensory_soothing｜感官舒缓
high_interaction｜强互动
quiet_focus｜安静专注
ceremonial_experience｜强仪式感
```

## 2.8｜standardization_intensity｜标准化强度

```text
high_standardization｜高标准化
medium_standardization｜中等标准化
customized｜强定制
modular_repeatable｜模块化可复制
prototype_testing｜原型测试
```

## 2.9｜sustainability_constraint｜可持续约束

```text
none｜无明确可持续要求
green_building_certified｜绿色建筑认证
esg_limited｜ESG 指标限制
low_carbon_target｜低碳目标
circular_reuse｜循环再利用
dfma_modular_required｜装配式 / 可拆卸模块化要求
old_material_reuse｜旧材料再利用
energy_efficiency_priority｜能耗优先控制
```

## 2.10｜lifecycle_operation_mode｜运营周期

```text
temporary_operation｜短期运营
seasonal_operation｜季节性运营
long_term_operation｜长期运营
trial_operation｜试运营
phased_operation｜分期运营
```

## 2.11｜digital_integration_level｜数字化集成强度

```text
low_digital｜低数字化
standard_digital｜标准数字化
high_digital｜高数字化
iot_integrated｜IoT 集成
data_driven_operation｜数据驱动运营
digital_twin_required｜数字孪生要求
automation_priority｜自动化优先
```

## 2.12｜privacy_requirement｜隐私与安全要求

```text
standard_security｜标准安全
high_privacy_security｜高隐私安全
data_security_required｜数据安全要求
medical_privacy_required｜医疗隐私要求
financial_compliance_required｜金融合规要求
family_privacy_required｜家庭私密要求
```

---

# 3｜Derived Outputs｜派生输出

## 3.1｜activation_pack

```yaml
activation_pack:
  primary_pack_id: ""
  secondary_pack_ids: []
```

## 3.2｜inferred_context

```yaml
inferred_context:
  mep_complexity: low | standard | high | special | unknown
  mep_complexity_source: subdomain | activation_pack | user_input | unknown
```

## 3.3｜missing_slots

```yaml
missing_slots:
  physical_constraint_slots: []
  business_fact_slots: []
  subjective_preference_slots: []
```

## 3.4｜confidence_level

```text
high｜高置信
medium｜中置信
low｜低置信
conflict｜存在冲突
needs_clarification｜需要澄清
```

---

# 4｜Resolution Context｜边界消解上下文

```yaml
resolution_context:
  commission_scope: ""
  primary_revenue_subject: ""
  primary_user_group: ""
  decision_owner: ""
```

---

# 5｜Classification Output v1.2.1

```yaml
classification_output:
  schema_version: classification_output.v1.2.1

  canonical_axes:
    project_type_id: ""
    subdomain:
      primary_subdomain_id: ""
      secondary_subdomain_ids: []
      complement_roles:
        - subdomain_id: ""
          role: support | attractor | amenity | revenue | brand_expression | membership_service
    founding_type_id: ""
    spatial_extent_id: ""
    lifecycle_id: ""
    industry_domain:
      industry_domain_id: ""
      source: derived | explicit | unknown

  project_conditions:
    brand_stage: ""
    site_context: ""
    area_scale: ""
    investment_boundary: ""
    service_mode: ""
    operation_pressure: ""
    experience_goal: ""
    standardization_intensity: ""
    sustainability_constraint: ""
    lifecycle_operation_mode: ""
    digital_integration_level: ""
    privacy_requirement: ""

  inferred_context:
    mep_complexity: low | standard | high | special | unknown
    mep_complexity_source: subdomain | activation_pack | user_input | unknown

  resolution_context:
    commission_scope: ""
    primary_revenue_subject: ""
    primary_user_group: ""
    decision_owner: ""

  derived_outputs:
    activation_pack:
      primary_pack_id: ""
      secondary_pack_ids: []
    parent_project_type_id: ""
    boundary_case_ids: []
    confidence_level: high | medium | low | conflict
    needs_clarification: true | false
    missing_slots:
      physical_constraint_slots: []
      business_fact_slots: []
      subjective_preference_slots: []

  system_links:
    condition_to_context_vector_mapping_id: ""
    condition_to_lens_mapping_id: ""
    main_mapping_id: ""
    ontology_scope: ""
    knowledge_scope: ""
    task_brief_template: "DesignBrief_2_0"
```
