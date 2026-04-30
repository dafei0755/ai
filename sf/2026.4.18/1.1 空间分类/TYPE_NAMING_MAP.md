# TYPE_NAMING_MAP — 空间分类类型命名映射

> 事实基准版本：v1  
> 生成日期：2026-04-30  
> 数据来源：`intelligent_project_analyzer/services/project_type_detector.py`

---

## 一、active 类型映射表

| id | 中文名 | priority | primary_bucket | boundary_neighbors |
|---|---|:---:|---|---|
| rural_construction | 乡建/新农村建设 | 15 | public | 酒店民宿（农文旅）、个人住宅（乡居自建）、景观/公共户外空间 |
| urban_renewal_market | 城市更新/公共市场 | 10 | urban_renewal | 城市更新/历史建筑活化、社区/公共服务空间、商业零售/综合体 |
| urban_renewal_heritage | 城市更新/历史建筑活化 | 10 | urban_renewal | 城市更新/公共市场、工业/生产设施/厂房改造、宗教/仪式/殡葬空间 |
| real_estate_showcase | 地产样板房/售楼展示 | 9 | — | 个人住宅、品牌旗舰/体验店、企业空间/品牌展厅 |
| industrial_conversion | 工业/生产设施/厂房改造 | 9 | industrial | 城市更新/历史建筑活化、办公/联合办公、存量住宅改造/二手房翻新 |
| educational_facility | 教育建筑/校园 | 9 | education | 亲子/早教/儿童空间、社区/公共服务空间、文化展陈/科教场馆 |
| religious_spiritual | 宗教/仪式/殡葬空间 | 9 | special | 文化展陈/科教场馆、城市更新/历史建筑活化、景观/公共户外空间 |
| commercial_hospitality | 酒店民宿/度假 | 8 | hospitality | 乡建/新农村建设、休闲娱乐/水会棋牌KTV、医疗/康养/养老（温泉/spa） |
| commercial_dining | 餐饮/夜生活空间 | 8 | hospitality | 婚庆宴会/庆典空间、休闲娱乐/水会棋牌KTV、商业零售/综合体 |
| performing_arts | 演艺/剧场空间 | 8 | leisure | 文化展陈/科教场馆、婚庆宴会/庆典空间、休闲娱乐/水会棋牌KTV |
| public_cultural | 文化展陈/科教场馆 | 8 | public | 教育建筑/校园、演艺/剧场空间、社区/公共服务空间 |
| landscape_outdoor | 景观/公共户外空间 | 8 | outdoor | 社区/公共服务空间、乡建/新农村建设、交通/市政/公共行政 |
| community_public | 社区/公共服务空间 | 8 | public | 景观/公共户外空间、文化展陈/科教场馆、亲子/早教/儿童空间 |
| leisure_entertainment | 休闲娱乐/水会棋牌KTV | 8 | leisure | 餐饮/夜生活空间、体育/健身/运动场馆、医疗/康养/养老（洗浴） |
| wedding_banquet | 婚庆宴会/庆典空间 | 8 | hospitality | 餐饮/夜生活空间、演艺/剧场空间、品牌旗舰/体验店 |
| children_family | 亲子/早教/儿童空间 | 8 | education | 教育建筑/校园、社区/公共服务空间、医疗/康养/养老 |
| residential_renovation | 存量住宅改造/二手房翻新 | 8 | residential | 个人住宅、工业/生产设施/厂房改造、城市更新/历史建筑活化 |
| commercial_retail | 商业零售/综合体 | 7 | retail | 品牌旗舰/体验店、企业空间/品牌展厅、城市更新/公共市场 |
| brand_experience | 品牌旗舰/体验店 | 7 | — | 商业零售/综合体、企业空间/品牌展厅、快闪/临时装置空间 |
| commercial_office | 办公/联合办公 | 7 | office | 企业空间/品牌展厅、工业/生产设施/厂房改造、直播/拍摄/媒体基地 |
| commercial_enterprise | 企业空间/品牌展厅 | 7 | — | 办公/联合办公、品牌旗舰/体验店、商业零售/综合体 |
| healthcare_wellness | 医疗/康养/养老 | 7 | healthcare | 亲子/早教/儿童空间、休闲娱乐/水会棋牌KTV（洗浴）、美容美发/生活美学门店 |
| sports_entertainment_arts | 体育/健身/运动场馆 | 7 | leisure | 休闲娱乐/水会棋牌KTV、亲子/早教/儿童空间、景观/公共户外空间 |
| transportation_civic | 交通/市政/公共行政 | 7 | public | 景观/公共户外空间、社区/公共服务空间、工业/生产设施/厂房改造 |
| beauty_personal_care | 美容美发/生活美学门店 | 7 | retail | 医疗/康养/养老（轻医美）、商业零售/综合体、品牌旗舰/体验店 |
| automotive_showroom | 汽车展厅/4S店/改装 | 8 | retail | 品牌旗舰/体验店、企业空间/品牌展厅、商业零售/综合体 |
| digital_media_studio | 直播/拍摄/媒体基地 | 7 | office | 办公/联合办公、工业/生产设施/厂房改造（改装影棚）、快闪/临时装置空间 |
| popup_temporary | 快闪/临时装置空间 | 7 | retail | 品牌旗舰/体验店、直播/拍摄/媒体基地、餐饮/夜生活空间 |
| special_function | 专项功能空间 | 6 | special | 个人住宅、办公/联合办公、医疗/康养/养老（冥想/瑜伽） |
| residential_collective | 集合住宅/公共住房 | 6 | — | 个人住宅、住商混合、社区/公共服务空间 |
| hybrid_residential_commercial | 住商混合 | 6 | — | 集合住宅/公共住房、商业零售/综合体、个人住宅 |
| personal_residential | 个人住宅 | 5 | residential | 存量住宅改造/二手房翻新、住商混合、集合住宅/公共住房 |

**active 类型总数：32**

> 注：`real_estate_showcase`、`brand_experience`、`commercial_enterprise`、`residential_collective`、`hybrid_residential_commercial` 未在 PARENT_TYPE_MAP 中显式列出，填 `—`。

---

## 二、LEGACY_TYPE_ALIASES（别名列表）

共 **26** 条别名映射。

| 旧 ID（alias） | → | 目标 ID（canonical） | 来源版本 |
|---|:---:|---|---|
| cultural_educational | → | public_cultural | v3.0 → v3.2 |
| office_coworking | → | commercial_office | v3.0 → v3.2 |
| hospitality_tourism | → | commercial_hospitality | v3.0 → v3.2 |
| commercial_enterprise | → | commercial_enterprise | v3.0（保持自映射） |
| urban_renewal | → | urban_renewal_market | v3.0 → v3.2 |
| heritage_conservation | → | urban_renewal_heritage | v3.0 → v3.2 |
| industrial_manufacturing | → | industrial_conversion | v3.2 重命名 |
| education_research | → | educational_facility | v3.2 重命名 |
| transportation_infrastructure | → | transportation_civic | v3.2 重命名 |
| entertainment_leisure | → | leisure_entertainment | v8.0 新增预留 |
| bathhouse_ktv | → | leisure_entertainment | v8.0 新增预留 |
| wedding_hall | → | wedding_banquet | v8.0 新增预留 |
| banquet_hall | → | wedding_banquet | v8.0 新增预留 |
| early_education | → | children_family | v8.0 新增预留 |
| kids_space | → | children_family | v8.0 新增预留 |
| house_renovation | → | residential_renovation | v8.0 新增预留 |
| old_house_renovation | → | residential_renovation | v8.0 新增预留 |
| hair_salon | → | beauty_personal_care | v8.0 新增预留 |
| beauty_salon | → | beauty_personal_care | v8.0 新增预留 |
| car_showroom | → | automotive_showroom | v8.0 新增预留 |
| live_streaming | → | digital_media_studio | v8.0 新增预留 |
| flash_store | → | popup_temporary | v8.0 新增预留 |

> 注：`commercial_enterprise → commercial_enterprise` 为自映射，仍收录以保持兼容性。实际有效别名 21 条，自映射 1 条，共 22 条，另有 4 条多对一合并映射。

---

## 三、PARENT_TYPE_MAP 父桶汇总

| parent_bucket | 子类型数 | 包含的 type_id |
|---|:---:|---|
| residential | 2 | personal_residential, residential_renovation |
| hospitality | 3 | commercial_dining, commercial_hospitality, wedding_banquet |
| office | 2 | commercial_office, digital_media_studio |
| retail | 4 | commercial_retail, beauty_personal_care, automotive_showroom, popup_temporary |
| leisure | 3 | leisure_entertainment, sports_entertainment_arts, performing_arts |
| education | 2 | children_family, educational_facility |
| healthcare | 1 | healthcare_wellness |
| public | 4 | community_public, public_cultural, transportation_civic, rural_construction |
| industrial | 1 | industrial_conversion |
| urban_renewal | 2 | urban_renewal_market, urban_renewal_heritage |
| outdoor | 1 | landscape_outdoor |
| special | 2 | religious_spiritual, special_function |

**父桶总数：12，已映射子类型总数：27**

未收录于 PARENT_TYPE_MAP 的类型（5 个）：
- `real_estate_showcase`
- `brand_experience`
- `commercial_enterprise`
- `residential_collective`
- `hybrid_residential_commercial`
