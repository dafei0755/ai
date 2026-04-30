# Active Project Type Registry v1.0

**创建时间**: 2026-04-30
**源文件**: `intelligent_project_analyzer/services/project_type_detector.py`
**版本**: v8.1（项目类型检测器统一注册表）

---

## 概述

本文档确认首批 **active 类型 30 个**，不超过 50 个的预期约束。所有类型均取自 `PROJECT_TYPE_REGISTRY`，包含 ID、中文名、优先级等核心属性。

---

## 1. Active 类型表（按优先级降序）

| 优先级 | ID | 中文名 | Status | 备注 |
|--------|-----|--------|--------|------|
| **15** | rural_construction | 乡建/新农村建设 | active | 强优先，防止被住宅/酒店关键词稀释；min_secondary_hits=3 |
| **10** | urban_renewal_market | 城市更新/公共市场 | active | 菜市场、农贸市场改造 |
| **10** | urban_renewal_heritage | 城市更新/历史建筑活化 | active | 历史保护、适应性改造 |
| **9** | real_estate_showcase | 地产样板房/售楼展示 | active | 样板间、展示中心 |
| **9** | industrial_conversion | 工业/生产设施/厂房改造 | active | 厂房、酒庄、酿酒厂 |
| **9** | educational_facility | 教育建筑/校园 | active | 学校、幼儿园、图书馆 |
| **9** | religious_spiritual | 宗教/仪式/殡葬空间 | active | 寺庙、教堂、纪念馆；min_secondary_hits=1 |
| **8** | commercial_hospitality | 酒店民宿/度假 | active | 精品酒店、树屋民宿、露营基地 |
| **8** | commercial_dining | 餐饮/夜生活空间 | active | 餐厅、酒吧、火锅、烧烤 |
| **8** | performing_arts | 演艺/剧场空间 | active | 剧院、音乐厅、电影院 |
| **8** | public_cultural | 文化展陈/科教场馆 | active | 博物馆、美术馆、动物园 |
| **8** | landscape_outdoor | 景观/公共户外空间 | active | 公园、广场、滨水景观；min_secondary_hits=1 |
| **8** | community_public | 社区/公共服务空间 | active | 社区中心、邻里服务；min_secondary_hits=1 |
| **8** | leisure_entertainment | 休闲娱乐/水会棋牌KTV | active | KTV、棋牌、水会、密室逃脱 |
| **8** | wedding_banquet | 婚庆宴会/庆典空间 | active | 婚宴、宴会厅、庆典会所 |
| **8** | children_family | 亲子/早教/儿童空间 | active | 早教中心、儿童乐园、托育 |
| **8** | residential_renovation | 存量住宅改造/二手房翻新 | active | 二手房翻新、老房改造 |
| **8** | automotive_showroom | 汽车展厅/4S店/改装 | active | 4S店展厅、新能源体验店；min_secondary_hits=1 |
| **7** | commercial_retail | 商业零售/综合体 | active | 商场、购物中心、百货 |
| **7** | brand_experience | 品牌旗舰/体验店 | active | 旗舰店、概念店 |
| **7** | commercial_office | 办公/联合办公 | active | 写字楼、联合办公、孵化器 |
| **7** | commercial_enterprise | 企业空间/品牌展厅 | active | 企业总部、展厅、接待中心 |
| **7** | healthcare_wellness | 医疗/康养/养老 | active | 医院、诊所、康养中心、适老化改造 |
| **7** | sports_entertainment_arts | 体育/健身/运动场馆 | active | 体育馆、游泳馆、健身房、攀岩馆 |
| **7** | transportation_civic | 交通/市政/公共行政 | active | 机场、地铁站、法院、消防站 |
| **7** | beauty_personal_care | 美容美发/生活美学门店 | active | 美发沙龙、美容院、美甲 |
| **7** | digital_media_studio | 直播/拍摄/媒体基地 | active | 直播间、MCN机构、影棚 |
| **7** | popup_temporary | 快闪/临时装置空间 | active | 快闪店、pop-up、期间限定 |
| **6** | special_function | 专项功能空间 | active | 影音室、茶室、书房；min_secondary_hits=2 |
| **6** | residential_collective | 集合住宅/公共住房 | active | 公租房、保障房、人才公寓；min_secondary_hits=1 |
| **6** | hybrid_residential_commercial | 住商混合 | active | 混合用途（无关键词触发） |
| **5** | personal_residential | 个人住宅 | active | 默认兜底类型；公寓、别墅、自住住房 |

---

## 2. Alias_only 类型表

| 旧 ID | 指向 ID | 说明 |
|-------|---------|------|
| cultural_educational | public_cultural | v3.0 → v3.2 重命名 |
| office_coworking | commercial_office | 旧别名 |
| hospitality_tourism | commercial_hospitality | 旧别名 |
| commercial_enterprise | commercial_enterprise | 保持（沿用历史） |
| urban_renewal | urban_renewal_market | 拆分为市场/遗产两个子类 |
| heritage_conservation | urban_renewal_heritage | 精确化后的别名 |
| industrial_manufacturing | industrial_conversion | 更准确的命名 |
| education_research | educational_facility | 统一为学校/校园 |
| transportation_infrastructure | transportation_civic | 扩大范围至行政建筑 |
| entertainment_leisure | leisure_entertainment | v8.0 新分类的别名 |
| bathhouse_ktv | leisure_entertainment | v8.0 整合 |
| wedding_hall | wedding_banquet | v8.0 更规范命名 |
| banquet_hall | wedding_banquet | v8.0 更规范命名 |
| early_education | children_family | v8.0 整合 |
| kids_space | children_family | v8.0 整合 |
| house_renovation | residential_renovation | v8.0 新增类型的别名 |
| old_house_renovation | residential_renovation | v8.0 新增类型的别名 |
| hair_salon | beauty_personal_care | v8.0 新增类型的别名 |
| beauty_salon | beauty_personal_care | v8.0 新增类型的别名 |
| car_showroom | automotive_showroom | v8.0 新增类型的别名 |
| live_streaming | digital_media_studio | v8.0 新增类型的别名 |
| flash_store | popup_temporary | v8.0 新增类型的别名 |

**共计**: 22 条别名映射（无独立 active 条目）

---

## 3. 扩展候选池（暂不升为 active 的建议）

根据 `SPECIALTY_TAG_MAP` 和 PARENT_TYPE_MAP，以下候选应作为 **specialty_tag** 而非独立 active 类型维护：

### 3.1 餐饮细分（→commercial_dining + tag）
- `buffet` — 自助餐
- `bbq` — 烧烤
- `hotpot` — 火锅
- `cafe` — 咖啡馆
- `tea_bar` — 茶饮店

### 3.2 住宅细分（→personal_residential + tag）
- `flat_luxury` — 大平层
- `detached_villa` — 独栋别墅
- `stacked_mansion` — 叠拼
- `loft` — loft户型
- `duplex` — 跃层/复式
- `villa` — 别墅
- `apartment` — 公寓

### 3.3 酒店细分（→commercial_hospitality + tag）
- `boutique_hotel` — 精品酒店
- `treehouse` — 树屋民宿
- `capsule_hotel` — 胶囊酒店
- `b_and_b` — 民宿

### 3.4 办公细分（→commercial_office + tag）
- `co_working` — 共享办公
- `incubator` — 孵化器
- `makerspace` — 创客空间

### 3.5 娱乐细分（→leisure_entertainment + tag）
- `ktv` — KTV
- `escape_room` — 密室逃脱
- `mahjong_room` — 棋牌/麻将
- `spa_club` — 水会

### 3.6 医疗细分（→healthcare_wellness + tag）
- `dental` — 牙科
- `tcm` — 中医
- `age_friendly` — 适老化
- `elderly_care` — 养老
- `aesthetic_medicine` — 医美

### 3.7 教育细分（→educational_facility + tag）
- `kindergarten` — 幼儿园
- `early_childhood` — 早教

### 3.8 汽车细分（→automotive_showroom + tag）
- `auto_4s_showroom` — 4S店展厅
- `auto_showroom` — 汽车展厅

### 3.9 直播细分（→digital_media_studio + tag）
- `live_studio` — 直播间
- `mcn_studio` — MCN机构

### 3.10 快闪（→popup_temporary + tag）
- `popup` — 快闪店

### 3.11 婚宴细分（→wedding_banquet + tag）
- `wedding_banquet_hall` — 婚宴厅
- `banquet_hall` — 宴会厅

**共计**: 49 个 specialty_tag 候选（通过 SPECIALTY_TAG_MAP 维护）

---

## 4. 类型状态定义

| 状态 | 说明 | 示例 |
|------|------|------|
| **active** | 在 PROJECT_TYPE_REGISTRY 中的一级分类，参与关键词检测 | personal_residential, commercial_hospitality |
| **alias_only** | LEGACY_TYPE_ALIASES 中的别名，无独立检测，规范化→对应 active ID | urban_renewal → urban_renewal_market |
| **candidate** | 暂未激活、待审批的类型（通过 project_type_extensions.json 管理） | (管理员扩展) |
| **specialty_tag** | 一级类型的细粒度子标记（SPECIALTY_TAG_MAP 维护），不参与类型判断，仅作补充分类 | boutique_hotel (→commercial_hospitality) |
| **deprecated** | 已下线、不再使用的旧类型 | (无当前示例) |
| **merged** | 已合并入其他类型的旧分类 | entertainment_leisure → leisure_entertainment |

---

## 5. 类型检测流程

### 5.1 三级分类体系

```
一级：Project Type (ID)
      └─ 关键词驱动，优先级 5-15
      └─ 33 个 active 类型参与检测

二级：Parent Type (PARENT_TYPE_MAP)
      └─ 宽泛业态桶（residential/hospitality/office/retail 等）
      └─ 两阶段检测的第一阶段输入

三级：Specialty Tag (SPECIALTY_TAG_MAP)
      └─ 细粒度子类型（boutique_hotel/loft/kdv 等）
      └─ 不参与主类型判断，仅补充分类
```

### 5.2 检测流程（Steps 6-15）

1. **Step 6**: 别名预处理 — 规范化输入
2. **Step 9**: 提取 parent_type — 宽泛业态分类
3. **Step 10**: (预留) 两阶段粗筛
4. **Step 11**: 提取 specialty_tag — SPECIALTY_TAG_MAP 首次命中
5. **Step 13**: 否定词过滤 — 排除否定语境中的关键词命中
6. **Step 14**: 排他性权重 — 独占关键词 ×1.5，稀有词 ×1.2，通用词 ×1.0
7. **Step 15**: Top-2 融合 — 若第二名得分 ≥80% 第一名，返回 is_ambiguous=True

---

## 6. 统计汇总

| 指标 | 值 | 说明 |
|------|-----|------|
| **Active Types** | 33 | PROJECT_TYPE_REGISTRY 中的所有条目 |
| **优先级分布** | — | — |
| — P=15 | 1 | rural_construction |
| — P=10 | 2 | urban_renewal_* (2) |
| — P=9 | 5 | real_estate_showcase, industrial_conversion, educational_facility, religious_spiritual, (共4个) |
| — P=8 | 11 | commercial_*, performing_arts, public_cultural, landscape_outdoor, community_public, leisure_entertainment, wedding_banquet, children_family, residential_renovation, automotive_showroom |
| — P=7 | 10 | commercial_*, healthcare_wellness, sports_*, transportation_civic, beauty_*, digital_media_studio, popup_temporary |
| — P=6 | 3 | special_function, residential_collective, hybrid_residential_commercial |
| — P=5 | 1 | personal_residential (默认兜底) |
| **Alias_only** | 22 | LEGACY_TYPE_ALIASES 中的映射条目 |
| **Specialty_tag Candidates** | 49 | SPECIALTY_TAG_MAP 中的子标记 |
| **关键词池** | ~500+ | 一级类型关键词 + 次要关键词 |
| **≤50 约束** | ✓ | 33 active < 50 预期 |

---

## 7. 治理方向建议

### 7.1 短期（v8.1-v8.3）
- ✓ 第一批 33 个 active 类型稳定运行
- ✓ 49 个 specialty_tag 细化子分类体验
- 关注：低优先级类型 (P=5-6) 的实际命中率

### 7.2 中期（v8.4-v9.0）
- 根据实际使用反馈，评估是否需要将高频 specialty_tag 升为 active
- 收集"无法分类"的案例，评估扩展类型池
- 通过 `project_type_extensions.json` 试点管理员审批流程

### 7.3 长期（v9.0+）
- 建立类型分类体系的周期审计机制
- 支持多语言标签映射（中文、英文、日文等）
- 与知识图谱、项目库关联，形成多维属性体系

---

## 参考

**相关文件**:
- `intelligent_project_analyzer/services/project_type_detector.py` — 权威注册表定义
- `intelligent_project_analyzer/data/project_type_extensions.json` — 管理员扩展类型（不存在则为空）
- `PARENT_TYPE_MAP` — 二级业态分类映射
- `SPECIALTY_TAG_MAP` — 三级子标记映射

**版本历史**:
- v8.1: 统一注册表驱动、两阶段检测、排他性权重
- v8.0: 新增 8 个一级分类（v7.x → v8.0 升级）
- v7.x: 早期注册表（已向后兼容）

---

**本文档确认**: 首批 active 类型 33 个，≤50 约束满足 ✓
