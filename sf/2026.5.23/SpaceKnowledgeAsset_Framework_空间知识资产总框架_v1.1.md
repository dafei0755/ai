# SpaceKnowledgeAsset_Framework｜空间知识资产总框架 v1.1

> **版本**：v1.1  
> **日期**：2026-06-04  
> **性质**：方案高参全空间类型知识资产的总框架文件  
> **上位文件**：`AdvisorArchitecture_Skeleton_素材·转化·交付_v1.0`  
> **定位**：本文档不属于任何单一空间类型，不生产具体业态内容，而是规定所有空间知识如何判断归属、如何区分通用与专属、如何组织横向系统、意义表达、设计语法、转译方法，并如何进入 System-R、MainMapping 与设计任务书 2.0。

---

## 0｜v1.1 更新核心

v1.0 主要解决：

```text
通用知识 / 大类知识 / 业态知识 / 项目实例如何分层；
洗手间、楼梯、门窗、幕墙、灯光等横向系统如何不被单一业态吞掉；
A–Q 这类人读目录如何进入 System-R、MainMapping 与设计任务书章节。
```

v1.1 的关键更新是：

```text
1. 接入“素材 · 转化 · 交付”总骨架。
2. 明确本文件属于“素材层 + 转化方法资产”的知识治理文件，而不是方案高参总架构。
3. 新增 Meaning & Expression Knowledge｜意义与表达知识。
4. 新增 Design Grammar & Spatial Method｜设计语法与空间手法知识。
5. 新增 Translation Method Card｜转译方法卡。
6. 明确“转化方法入库，项目立意不入库”。
7. 明确主体轴相关知识的入库与项目画像边界。
8. 增加 source_role：被转化的源 / 转化的边界 / 转化的工具料。
```

---

## 0.1｜与总骨架的关系

本文件位于 `AdvisorArchitecture_Skeleton｜素材 · 转化 · 交付` 之下。

总骨架规定：

```text
素材层回答：有什么可用？
转化层回答：如何立意？
交付层回答：如何组织成产物？
主体轴回答：为谁、为何、谁说了算？
输出模式回答：这次应交付什么形态？
```

本文件只负责其中两部分：

```text
1. 素材层的知识资产治理。
2. 转化层中“可沉淀的方法资产”的治理。
```

本文件不负责：

```text
不负责现场立意。
不负责最终判断。
不负责输出模式选择。
不负责项目级任务书编排。
不替代 AdvisorAgent。
不替代设计任务书 2.0 编排机制。
```

最短定位：

```text
SpaceKnowledgeAsset Framework 管“可复用的料与方法”；
AdvisorAgent 管“这一次项目如何转化与判断”；
Design Brief 2.0 管“如何组织成交付物”。
```

---

## 0.2｜核心定盘

```text
茶饮不是知识宇宙本身。
茶饮只是空间知识宇宙里的一个专项包。

知识资产也不是方案高参的主语。
知识资产只是转化引擎可调用的料、边界、工具和方法。

方案高参的主语不是“素材库”；
方案高参的主语是“转化引擎”。
```

因此，本框架的核心任务不是做一个更大的百科，而是让任何一条知识在出生时就回答：

```text
它是什么料？
它能否复用？
它属于哪一层？
它是哪种知识物种？
它如何被生产？
它如何被转化调用？
它如何被映射到系统？
它是否只是某个项目的产物？
```

---

## 1｜总公式

v1.1 将 v1.0 公式升级为：

```text
空间知识资产 = source_role × 内容归属层 × 知识物种 × 生产方式 × 系统坐标 × 使用出口
```

对应核心字段：

```yaml
knowledge_asset_routing:
  source_role: source_to_translate | transformation_boundary | tool_material | translation_method | project_output
  layer: SpaceCore | Category | SpaceType | ProjectInstance
  species: DomainCard | CrossSystemCard | SpecCard | MechanismCard | MeaningExpressionCard | OperationCard | LensCard | XFactorSourceCard | TranslationMethodCard | CaseObject
  production_method: DR | MS | CL | SX
  grid_coordinate:
    primary_lens: ""
    secondary_lens: []
    layer: ""
  domain_applicability:
    primary_domain: universal | food_beverage | retail | hospitality | office | healthcare | tea_drink | custom
    secondary_domains: []
    exclusion: []
  task_brief_chapter: []
  output_usage: []
```

---

## 2｜source_role｜素材角色

v1.1 新增 `source_role`，用于区分一条知识在“素材 · 转化 · 交付”总骨架中的角色。

### 2.1 source_to_translate｜被转化的源

定义：转译引擎要编译的意义、人格、品牌、意象、学科、文化与精神资源。

典型对象：

```text
人格精神
品牌内核
大师方法
诗性意象
文学 / 音乐 / 自然意象
文化传统
哲学观念
社会学洞察
人类学观察
学科理论
生活方式
```

示例：

```text
Tiffany 的“被珍视感”
Audrey Hepburn 的克制、轻盈、自律、独立
劳斯莱斯定制体系
“月亮落在结冰的湖面上”
苏东坡式生活美学
行为经济学中的损失厌恶与锚定效应
```

入库纪律：

```text
原始源可以记录为 XFactorSourceCard 或 LensCard。
只有被提炼为可复用解码方法、转译模式或误用边界时，才成为正式知识资产。
```

---

### 2.2 transformation_boundary｜转化的边界

定义：不被编译，但限定转化全过程的约束条件。

典型对象：

```text
预算
法规
消防
结构
场地
机电
给排水
物业
工期
伦理
安全
隐私
气候
技术条件
尺度范围
学科边界
交付周期
```

示例：

```text
预算 3000 元/㎡，但要保留豪宅体面感。
历史建筑不能大拆大改，但要植入现代开放社交空间。
临终病房不能像医院，但必须满足医疗护理与家属陪伴。
数据安全指挥中心必须高安全、高冗余、长期运行。
```

入库纪律：

```text
边界类知识大多进入 SpecCard、ConstraintCard、MechanismCard 或 CrossSystemCard。
它们不产生立意，但会封顶、限制、触发追问或进入多约束求解。
```

---

### 2.3 tool_material｜转化的工具料

定义：转化过程中可调用的空间、技术、业态、系统、手法、案例、规格等资源。

典型对象：

```text
业态知识
空间分类
横向系统
空间构件
建筑构件
贯穿系统
材料
灯光
机电
动线
人体工学
案例
规格卡
测绘数据
设计手法
任务书章节模板
```

示例：

```text
洗手间系统
楼梯系统
照明系统
门窗界面系统
茶饮水吧台
酒店客房模块
办公会议系统
行为经济学展陈路径
```

入库纪律：

```text
工具料是知识资产主体。
必须标注 layer、species、production_method 与 grid_coordinate。
```

---

### 2.4 translation_method｜转化方法

定义：用于将“源”转化为空间手法、空间策略、空间立意的可复用方法。

典型对象：

```text
人格源转译方法
品牌源转译方法
大师方法源转译方法
诗性意象源转译方法
学科理论源转译方法
防滑检查方法
转译误用边界
```

入库纪律：

```text
转化方法可以入库。
转化产物不能入通用库。
```

---

### 2.5 project_output｜项目级产物

定义：某一个项目现场生成的具体立意、叙事、任务书、竞标策略、方法论交付成果、图谱快照。

典型对象：

```text
某项目概念主线
某项目品牌叙事
某项目体验脚本
某项目竞标策略
某项目设计任务书
某项目方法论成果
某项目规划策略
项目图谱快照
```

入库纪律：

```text
project_output 不进入通用知识库。
它只能进入 Project Archive / CaseObject / FeedbackEvent。
后续经整理加工，才可能提炼出可复用方法卡、机制卡或风险卡。
```

---

## 3｜内容归属层

本框架不新增新的 layer 坐标，直接沿用 System-R 与本体论中的四层结构。

```text
SpaceCore｜全空间通用层
Category｜行业大类共享层
SpaceType｜具体空间类型专项层
ProjectInstance｜项目 / 案例实例层
```

### 3.1 SpaceCore｜全空间通用层

定义：不依赖具体业态、空间类型或行业大类的知识。

典型内容：

```text
人体尺度
基础操作高度
无障碍基础尺寸
基础照明参数
防滑与防水基本原则
门窗开口逻辑
基础声学指标
基础材料物性
楼梯踏步与扶手尺度
洗手间基础程序
消防疏散基础逻辑
基础设计手法语汇
通用转译方法
```

写作纪律：

```text
SpaceCore 知识严禁带具体业态口吻。
不要写“茶饮店湿区地面”。
应该写“高频湿区地面”。
```

---

### 3.2 Category｜行业大类共享层

定义：不属于所有空间，但属于某个行业大类或空间大类共享的知识。

典型大类：

```text
FoodBeverage｜餐饮饮品大类
RetailService｜零售服务大类
Hospitality｜酒店住宿大类
OfficeWorkplace｜办公组织大类
HealthcareWellness｜医疗康养大类
EducationCulture｜教育文化大类
PublicCivic｜公共服务大类
ResidentialLiving｜居住生活大类
```

典型内容：

```text
餐饮给排水
餐饮洗消
食饮吧台耐糖水奶渍
外带取餐界面
排队外溢与门头转化
低客单高频坪效逻辑
酒店客房卫浴维护逻辑
办公会议室声学与弱电逻辑
医疗隐私与洁污分流逻辑
居住空间家庭权力调和模式
```

---

### 3.3 SpaceType｜具体空间类型专项层

定义：明确依赖某个具体空间类型、细分业态或专项项目语境的知识。

示例：

```text
TeaDrinkSpace｜茶饮空间
CoffeeSpace｜咖啡空间
BoutiqueHotel｜精品酒店
RuralHomestay｜乡村民宿
DentalClinic｜牙科诊所
HeadquartersOffice｜总部办公
LuxuryRetail｜奢侈品零售
```

典型内容：

```text
茶饮鲜果茶对冷链、切配、洗消的后场压力
咖啡吧台萃取设备与磨豆动线
牙科诊疗室洁污与器械消毒路径
酒店客房布草周转与翻房效率
办公混合工位与会议室配比
```

---

### 3.4 ProjectInstance｜项目 / 案例实例层

定义：具体项目、具体门店、具体品牌、具体失败案例或具体实测证据。

典型内容：

```text
霸王茶姬某门店案例
喜茶某阶段大店实验
某商场茶饮骑手堵门失败案例
某办公总部改造项目复盘
某酒店客房渗漏案例
某竞标提案结果
某项目任务书版本快照
```

纪律：

```text
ProjectInstance 只作为证据源或候选机制燃料。
不能未经整理加工直接上升为 SpaceType 或 Category 规律。
```

---

## 4｜知识物种

v1.1 在 v1.0 的基础上新增 MeaningExpressionCard、OperationCard、XFactorSourceCard、TranslationMethodCard。

### 4.1 DomainCard｜领域知识卡

定义：具体空间类型或行业大类的领域知识。

示例：

```text
茶饮出杯动线卡
咖啡吧台流程卡
酒店客房程序卡
办公会议室配比卡
牙科诊室洁污分流卡
```

---

### 4.2 CrossSystemCard｜横向系统卡

定义：横跨多个空间类型的通用系统能力。

示例：

```text
洗手间系统
入口 / 门厅系统
楼梯与垂直交通系统
门窗开口系统
幕墙与建筑表皮系统
照明系统
声学系统
给排水系统
消防疏散系统
无障碍系统
导视系统
清洁维护系统
安防门禁系统
```

---

### 4.3 SpecCard｜规格 / 测绘卡

定义：由测绘、设备规格、规范、厂家资料、施工图或实测产生的确定性规格知识。

示例：

```text
吧台高度规格卡
设备碰撞域规格卡
洗手间厕位尺寸卡
楼梯踏步尺寸卡
灯具照度参数卡
门窗洞口与开启半径卡
```

---

### 4.4 MechanismCard｜机制卡

定义：解释变量之间因果关系的知识。

示例：

```text
外卖占比改变取餐系统身份的机制
低客单高频压缩座位投入的机制
品牌势能改变空间投资回报的机制
总部供应链能力压缩单店后场的机制
```

---

### 4.5 MeaningExpressionCard｜意义与表达卡

定义：用于沉淀可复用的品牌、调性、格调、品位、故事、体验、概念、文化、情绪、生活方式等意义结构与转译边界。

它不存放某个项目的具体品牌故事，而存放可复用的表达模式、误用边界与转译路径。

子类：

```text
BrandMeaningCard｜品牌意义卡
ToneCard｜调性卡
TasteBoundaryCard｜品位边界卡
GradeCard｜格调卡
ConceptKernelCard｜概念内核卡
NarrativeArcCard｜叙事弧线卡
ExperienceScriptCard｜体验脚本卡
SymbolTranslationCard｜符号转译卡
LifestyleSceneCard｜生活方式场景卡
```

质量标准：

```text
可辩护性
出处谱系
适用语境
误用边界
转译路径
评审标准
反装饰化规则
```

不适用：

```text
不要把某项目的漂亮文案入库。
不要把某品牌的临时概念当作通用知识。
不要把“高级感”“松弛感”“东方感”这类大词裸写成结论。
```

---

### 4.6 OperationCard｜设计语法与空间手法卡

定义：记录设计师对空间素材施加的操作原语、作用方式、意图、代价、误用风险与正反案例。

典型内容：

```text
节奏
比例
尺度
构成
关系
层级
序列
过渡
对比
密度
边界
焦点
留白
开合
虚实
框景
借景
压缩与释放
```

核心字段：

```yaml
operation_card:
  operation_name: ""
  operation_type: rhythm | proportion | scale | composition | relationship | sequence | boundary | focus | other
  applies_to: []
  design_intent: ""
  spatial_effect: ""
  cost_or_tradeoff: ""
  misuse_risks: []
  positive_examples: []
  negative_examples: []
  related_lens: []
```

纪律：

```text
手法可以结构化，但不能公式化成死规则。
手法卡存“意图-作用-代价-误用-案例”，不存固定答案。
不要把黄金比例、每几米停顿、某个光比写成全场景硬规则。
```

---

### 4.7 LensCard｜跨学科透镜卡

定义：不属于某一空间类型、不属于某个物理构件，而是用于解释用户行为、消费心理、文化符号、代际差异、社会关系、情绪场景的跨学科认知透镜。

典型内容：

```text
人类学
社会学
行为心理
消费文化
符号学
现象学
美学
哲学
代际研究
社交货币
身份表达
疗愈心理
地域文化
消费仪式
生活方式叙事
```

纪律：

```text
LensCard 不应塞进 TeaSpace、HotelSpace、OfficeSpace 等单一空间类型知识包。
它应挂在 UserExperience、CultureEmotion、BrandCommunication、MarketBusiness 等 lens 下，被不同空间调用。
```

---

### 4.8 XFactorSourceCard｜美学机制源卡

定义：记录可被转译引擎调用的美学、文学、音乐、自然、艺术、电影、时尚、品牌、文化等灵感来源。

它不是灵感图库。它只记录可提炼的机制。

字段：

```yaml
xfactor_source_card:
  source_name: ""
  source_type: literature | music | art | nature | fashion | film | architecture | brand | culture | other
  raw_quality: ""
  extractable_pattern: []
  not_to_copy: []
  possible_translation_paths: []
  misuse_risks: []
```

纪律：

```text
原始灵感不是知识。
提炼出的机制才是知识。
```

---

### 4.9 TranslationMethodCard｜转译方法卡

定义：记录从某类源到空间手法、空间策略、空间概念的通用转译方法。

五类优先模板：

```text
PersonalitySource｜人格 / 精神源
BrandSource｜品牌源
MasterMethodSource｜大师方法源
PoeticImagerySource｜诗性意象源
DisciplineTheorySource｜学科理论源
```

通用字段：

```yaml
translation_method_card:
  source_type: PersonalitySource | BrandSource | MasterMethodSource | PoeticImagerySource | DisciplineTheorySource
  source_name: ""
  decoding_method: []
  invariant_structure: []
  spatial_method_mapping: []
  applicable_context: []
  unsuitable_context: []
  misreading_risks: []
  anti_literal_rules: []
  positive_examples: []
  negative_examples: []
  defensibility_basis: ""
```

纪律：

```text
转译方法卡可以入库。
某项目转译出的概念主线不能入通用库。
```

---

### 4.10 CaseObject｜案例对象

定义：具体项目、具体品牌、具体案例或具体失败事件。

示例：

```text
霸王茶姬 CaseObject
喜茶 CaseObject
某商场骑手堵门 CaseObject
某酒店卫浴渗漏 CaseObject
某豪宅预算失控案例
某竞标失败案例
```

---

## 5｜生产方式

沿用 System-R 的四类生产方式。

```text
DR｜Deep Research
MS｜Measurement Survey 测绘
CL｜CaseLab 案例拆解
SX｜System Contract 系统契约
```

### 5.1 默认推断关系

| production_method | 高概率 layer | 高概率 species | 说明 |
|---|---|---|---|
| MS | SpaceCore / Category | SpecCard / CrossSystemCard | 测绘通常产生物理、人体、设备、材料、灯光等通用或大类共享知识 |
| DR | Category / SpaceType | DomainCard / MechanismCard / MeaningExpressionCard | 深度研究通常产生行业事实、机制、趋势、商业逻辑、文化语义 |
| CL | ProjectInstance / SpaceType | CaseObject / MechanismCard / TranslationMethodCard | 案例拆解先是实例，经过提炼后可能生成机制卡或方法卡 |
| SX | SpaceCore / KnowledgeGovernance | 系统契约 | 字段、映射、审计、版本、治理规则 |

### 5.2 运行纪律

```text
production_method 不是装饰字段。
它是判断知识应该如何生产、如何审核、如何进入系统的前置依据。
```

---

## 6｜横向系统能力包索引

横向系统能力包不是 project_type，不是 subdomain，也不是某个业态的内容模块。它们是所有空间项目可能调用的功能系统、技术系统、空间构件或专业系统。

### 6.1 空间构件系统

```text
CrossSystem-01｜Restroom_System｜洗手间系统
CrossSystem-02｜Entrance_Lobby_System｜入口 / 门厅系统
CrossSystem-03｜Vertical_Circulation_System｜垂直交通系统
CrossSystem-04｜Stair_System｜楼梯系统
CrossSystem-05｜Elevator_Escalator_System｜电梯 / 扶梯系统
CrossSystem-06｜Corridor_System｜走廊系统
CrossSystem-07｜Waiting_System｜等候系统
CrossSystem-08｜Reception_System｜接待系统
CrossSystem-09｜Storage_System｜储藏系统
CrossSystem-10｜Cleaning_Janitor_System｜清洁间系统
CrossSystem-11｜Mother_Baby_System｜母婴系统
CrossSystem-12｜Accessibility_System｜无障碍系统
```

### 6.2 技术专业系统

```text
CrossSystem-13｜Lighting_System｜照明系统
CrossSystem-14｜Acoustic_System｜声学系统
CrossSystem-15｜HVAC_Comfort_System｜暖通舒适系统
CrossSystem-16｜Plumbing_Drainage_System｜给排水系统
CrossSystem-17｜Electrical_Power_System｜强电系统
CrossSystem-18｜Weak_Current_IT_System｜弱电与网络系统
CrossSystem-19｜Fire_Egress_System｜消防疏散系统
CrossSystem-20｜Security_Access_System｜安防门禁系统
CrossSystem-21｜BMS_IoT_System｜楼宇智能 / IoT 系统
```

### 6.3 建筑界面系统

```text
CrossSystem-22｜Door_Window_Interface_System｜门窗开口系统
CrossSystem-23｜Facade_CurtainWall_System｜幕墙与建筑表皮系统
CrossSystem-24｜Partition_System｜隔墙 / 隔断系统
CrossSystem-25｜Acoustic_Envelope_System｜声学围护系统
CrossSystem-26｜Fire_Compartment_System｜防火分隔系统
```

### 6.4 运营后勤系统

```text
CrossSystem-27｜Waste_System｜垃圾与废弃物系统
CrossSystem-28｜Cleaning_Maintenance_System｜清洁维护系统
CrossSystem-29｜Backstage_Storage_System｜后场储藏系统
CrossSystem-30｜Laundry_Linen_System｜洗衣 / 布草系统
CrossSystem-31｜Logistics_Loading_System｜卸货 / 补货系统
CrossSystem-32｜Queue_System｜排队系统
CrossSystem-33｜Wayfinding_System｜导视系统
```

### 6.5 感官体验系统

```text
CrossSystem-34｜Color_System｜色彩系统
CrossSystem-35｜Scent_Air_System｜气味与空气系统
CrossSystem-36｜Thermal_Comfort_System｜热舒适系统
CrossSystem-37｜Material_Tactility_System｜材料触感系统
CrossSystem-38｜Atmosphere_System｜氛围系统
CrossSystem-39｜Visual_Display_System｜展示系统
```

---

## 7｜意义与表达知识

Meaning & Expression Knowledge 解决：

```text
空间表达什么意义、情绪、身份、文化和品牌价值？
```

它不替代 CrossSystem，也不替代 DesignGrammar。

```text
CrossSystem 解决空间的物理能力。
MeaningExpression 解决空间的精神能力。
DesignGrammar 解决空间如何被组织出来。
```

### 7.1 子系统

```text
01｜Brand Meaning｜品牌意义系统
02｜Tone System｜调性系统
03｜Taste System｜品位系统
04｜Cultural Grade｜格调系统
05｜Aesthetic Grammar｜审美语法系统
06｜Inspiration System｜灵感来源系统
07｜Concept Kernel｜概念内核系统
08｜Narrative System｜空间叙事系统
09｜Experience Script｜体验脚本系统
10｜Emotional Field｜情绪场系统
11｜Symbol & Semiotics｜符号与象征系统
12｜Social Identity & Lifestyle｜身份与生活方式系统
```

### 7.2 变量清单

```text
品牌
调性
格调
品位
气质
风格
审美
意境
概念
灵感
故事
叙事
体验
情绪
氛围
仪式
记忆点
社交货币
生活方式
身份表达
文化转译
地域性
时代感
高级感
松弛感
洁净感
精致感
亲密感
安全感
归属感
陌生感
先锋性
日常感
奢华感
克制感
传播性
打卡性
符号系统
隐喻系统
材料诗性
光影气质
声音气质
气味记忆
触感记忆
服务语气
空间人格
```

### 7.3 入库边界

可入库：

```text
可复用的品牌人格类型
可复用的叙事结构
可复用的体验脚本模式
可复用的概念转译方法
可复用的误用边界
可复用的评审标准
```

不可直接入库：

```text
某项目的品牌故事
某项目的概念口号
某项目的专属体验脚本
某一次竞标的叙事文案
```

---

## 8｜设计语法与空间手法知识

Design Grammar & Spatial Method 解决：

```text
设计师如何把功能、品牌、情绪、材料、光线、动线、尺度这些要素组织成空间？
```

它是操作层，不是素材层。

```text
前三者是 Substance：业态、构件、意义源。
DesignGrammar 是 Operation：对素材施加的操作。
```

### 8.1 基础操作原语

```text
Rhythm｜节奏
Proportion｜比例
Scale｜尺度
Composition｜构成
Relationship｜关系
Hierarchy｜层级
Sequence｜序列
Transition｜过渡
Contrast｜对比
Density｜密度
Boundary｜边界
Focus｜焦点
Order｜秩序
Void｜留白
Transparency｜透明 / 渗透
Compression & Release｜压缩与释放
Framing｜框景
Borrowing｜借景
```

### 8.2 手法三层

```text
1. 操作语汇表
   可命名、可定义、可沉淀。

2. 手法 × 素材应用知识
   可沉淀、可辩护，是设计师默会知识显性化的核心。

3. 现场调度判断
   不入库，属于 AdvisorAgent 现场判断。
```

### 8.3 手法卡纪律

```text
手法卡不直接给最终方案。
手法卡记录操作原理、适用意图、作用对象、代价、误用风险、正反案例。

手法可沉淀的是“法理与范例”；
不可沉淀的是“此时此地的具体值”。
```

---

## 9｜转译方法知识

Translation Method Knowledge 解决：

```text
如何从“源”走向“空间”？
```

它是 MeaningExpression 与 DesignGrammar 之间的桥。

### 9.1 五类源

```text
1. PersonalitySource｜人格 / 精神源
2. BrandSource｜品牌源
3. MasterMethodSource｜大师方法源
4. PoeticImagerySource｜诗性意象源
5. DisciplineTheorySource｜学科理论源
```

### 9.2 四步转译

```text
① 解码：源 → 不变结构
② 映射：不变结构 → 手法
③ 约束求解：手法意图 → 项目空间策略
④ 防滑检查：避免退化成符号、装饰、伪高级、伪国风
```

### 9.3 入库规则

```text
转译方法卡入库。
项目立意不入库。
```

示例：

```text
“如何转译品牌源”的方法可入库。
“这个项目的品牌概念主线”不入通用库。

“如何转译诗性意象”的方法可入库。
“月亮落在结冰湖面上这个书房的具体概念方案”不入通用库。
```

---

## 10｜主体轴知识处理

主体轴回答：

```text
为谁？为何？谁说了算？
```

主体轴不是普通项目条件，而是转译引擎的缰绳。

### 10.1 Subject Psyche｜主体精神结构

可入库：

```text
代际精神结构研究
阶层心理研究
性别身份研究
职业人格研究
生活阶段研究
疗愈需求类型
身份表达类型
```

不入库：

```text
某一个业主的具体精神画像
某一个家庭的具体心理矛盾
某一个项目中的个人隐私内容
```

这些进入项目图谱，不进入通用知识库。

---

### 10.2 Stakeholder Power｜权力与决策关系

可入库：

```text
多主体审美冲突调和方法
家庭权力关系空间调节方法
主客关系空间编码方法
公共 / 私密等级处理方法
决策链与使用方错位识别方法
```

不入库：

```text
某个家庭谁说了算
某个业主的预算权与审美权
某个企业项目的内部权力图
```

这些进入项目图谱，不进入通用知识库。

---

## 11｜引用与修正机制

### 11.1 depends_on

定义：领域知识依赖某张通用卡、横向系统卡、意义表达卡或设计手法卡。

```yaml
depends_on:
  - CrossSystem_Lighting_001
  - Operation_Rhythm_001
  - Meaning_Tone_Restrained_001
```

### 11.2 overrides

定义：具体业态或具体项目条件在通用知识基础上的修正、限制、强化或例外。

```yaml
overrides:
  - condition: "tea_drink_store + high_peak_pressure"
    rule: "取餐区灯光需兼顾叫号屏可读性与出杯台识别。"
```

### 11.3 additional_rules

定义：领域层新增规则，不直接推翻母卡，但增加特定场景约束。

```yaml
additional_rules:
  - "若鲜果类 SKU 占比高，洗消区与垃圾暂存需按高频湿作业处理。"
```

### 11.4 conflict_resolution

定义：当母卡与领域修正发生冲突时的优先规则。

```yaml
conflict_resolution:
  rule: "法规与安全优先于业态体验；物理硬约束优先于品牌表达；领域修正不能突破 SpaceCore 母卡的安全底线。"
```

---

## 12｜卡级归属决策规则

每条来源、研究包、测绘产物、案例拆解结果进入整理加工时，必须先回答四个问题：

```text
问题一：它在素材 · 转化 · 交付骨架中是什么角色？
问题二：它属于哪个内容归属层？
问题三：它属于哪个知识物种？
问题四：它是否只是某个项目的产物？
```

### 12.1 归属判断尺

```text
换成咖啡、办公、酒店还成立吗？

所有空间都成立 → SpaceCore
只在餐饮 / 零售 / 酒店 / 办公等大类成立 → Category
只有茶饮 / 咖啡 / 牙科 / 民宿等具体空间类型成立 → SpaceType
只属于某个品牌、某个门店、某个项目 → ProjectInstance
```

### 12.2 语言污染检查

```text
如果判为 SpaceCore，正文不得出现具体业态词。
如果判为 Category，正文必须说明适用大类。
如果判为 SpaceType，正文必须说明该空间类型的特化原因。
如果判为 ProjectInstance，正文必须保留来源与快照日期。
```

### 12.3 单实例不预抽母卡

```text
只有一个业态实例时，不急于物理抽出母卡。
但必须在卡片出生时标对 layer、species 与 domain_applicability。
等第二个业态出现时，再通过查询抽出母卡。
```

---

## 13｜MainMapping 与任务书出口

所有正式知识资产最终必须通过 MainMapping 映射到：

```text
primary_lens
secondary_lens
layer
production_method
task_brief_chapter
output_usage
evidence_type
status
```

典型任务书章节包括：

```text
02 项目成立判断与终局标准
03 决策方 / 使用方 / 运营方分析
06 功能需求与行为场景
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

---

## 14｜与输出模式选择器的关系

本框架不定义输出产品。

输出模式选择属于交付层。

但知识资产必须能够支撑不同内部输出模式：

```text
DesignBrief｜设计任务书
ConceptFramework｜概念框架
Methodology｜方法论
CompetitionStrategy｜竞标策略
ResearchFramework｜研究框架
ConceptMatrix｜概念矩阵
PlanningStrategy｜规划策略
ProductLineStrategy｜空间产品线策略
ScenarioPrototype｜未来情景原型
UpgradeRoadmap｜能力升级路径
OperationalPlaybook｜运营打法
```

对外当前仍统一进入：

```text
DesignBrief_2_0｜设计任务书 2.0
```

---

## 15｜与空间分类系统的关系

空间分类系统回答：

```text
这是什么项目？
```

知识资产框架回答：

```text
这个项目会调用哪些知识？这些知识应该放在哪里？
```

总关系：

```text
classification_output
→ context_vector
→ activation_pack
→ cross_system_packs
→ domain_specific_cards
→ meaning_expression_cards
→ operation_cards
→ translation_method_cards
→ MainMapping
→ AdvisorAgent
→ Design Brief 2.0
```

---

## 16｜与 System-R 的关系

System-R 是契约层，不是内容层。

本框架规定“知识有哪些物种、属于哪一层、如何避免污染”。

System-R 规定“这些知识如何被命名、结构化、标注、映射、审计、入系统与迭代”。

二者关系：

```text
SpaceKnowledgeAsset Framework = 内容归属与知识物种框架。
System-R = 入系统契约。
```

任何知识进入系统前，仍必须服从：

```text
grid_coordinate
production_method
source_refs
evidence_level
time_validity
transferability
task_brief_chapter
版本、去重、冲突、升降级机制
```

---

## 17｜与 AdvisorAgent 的关系

本框架提供：

```text
知识资产
素材
方法卡
约束候选
风险候选
语义源
手法源
案例证据
```

AdvisorAgent 负责：

```text
判断头号风险
承接主体诉求
在约束内组织路径
对结论封顶
避免硬猜
避免讨好
避免怯懦
组织最终回答
```

纪律：

```text
知识资产不替 AdvisorAgent 做现场判断。
知识资产提供判断燃料。
AdvisorAgent 负责现场编译。
```

---

## 18｜最小执行动作

### 18.1 第一阶段不做的事

```text
不立刻重写所有 TeaSpace 内容。
不立刻展开全部横向系统全文档。
不立刻把所有文科变量制成完整卡库。
不立刻重构 System-R。
不把设计任务书 2.0 降级为众多平级产品之一。
```

### 18.2 第一阶段必须做的事

```text
1. 新写卡必须标 source_role、layer、species、production_method。
2. SpaceCore 卡必须使用通用语言。
3. Category 卡必须说明适用大类。
4. SpaceType 卡必须说明特化原因。
5. ProjectInstance 必须保留来源、快照与不可直接上提提醒。
6. 项目级立意、概念、故事、任务书不入通用库。
7. 转化方法可以入库，但必须包含误用边界与防滑规则。
```

---

## 19｜最终纪律

```text
不要让具体业态吞掉横向系统。
不要让案例变成规律。
不要让跨学科透镜混进项目域。
不要把 SpaceCore 写出茶饮口吻。
不要在只有一个实例时过度抽象成母卡。
不要把项目立意当成通用知识。
不要把文科知识硬套理科证伪 schema。
不要把设计手法硬编码成固定参数。
不要让素材库取代转化引擎成为系统主语。
```

```text
先标归属，再写卡。
先用通用语言，再做领域修正。
先建索引，不急于全文展开。
方法可沉淀，立意不可预制。
```

---

## 20｜最终收口

本框架 v1.1 的意义，不是让知识资产变得更大，而是让知识资产第一次服务于真正的系统中轴：

```text
转化。
```

空间知识资产不是目的。它是料、边界、工具与方法。

```text
素材层回答有什么可用；
转化层回答如何立意；
交付层回答如何组织成产物。
```

因此，本框架最终定位为：

```text
方案高参素材层与转化方法层的知识治理底盘。
```

最短一句：

```text
知识资产不再追求“更全”；
知识资产必须服务“更会转化”。
```

---

## 附录 A｜v1.0 → v1.1 主要更新

| 更新项 | v1.0 | v1.1 |
|---|---|---|
| 上位关系 | 知识资产总框架 | 接入“素材 · 转化 · 交付”总骨架 |
| 核心公式 | layer × species × production_method × grid_coordinate × task_brief | source_role × layer × species × production_method × grid_coordinate × task_brief |
| 意义表达 | 主要由 LensCard 承接 | 新增 MeaningExpressionCard 体系 |
| 设计手法 | 未独立 | 新增 OperationCard / DesignGrammar |
| 灵感源 | 未独立 | 新增 XFactorSourceCard |
| 转译方法 | 未独立 | 新增 TranslationMethodCard |
| 主体轴 | 未显式 | 增加主体轴知识处理边界 |
| 入库判据 | 通用 / 专属 / 实例 | 素材入库、转化方法入库、项目产物不入库 |
| 输出模式 | 任务书章节映射 | 增加内部多输出模式支撑，但对外仍归 DesignBrief_2_0 |

---

## 附录 B｜后续配套文件建议

```text
1. TranslationMethodCards_五类源转译方法卡模板_v1.0
2. OutputModeSelector_输出模式选择器_v1.0
3. CrossSystem_Pack_Index_横向系统能力包索引_v1.0
4. MeaningExpression_CardSchema_意义表达卡模板_v1.0
5. OperationCard_设计语法与空间手法卡模板_v1.0
```

