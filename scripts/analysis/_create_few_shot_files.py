"""Create 3 few-shot example YAML files with UTF-8 encoding."""
import pathlib

BASE = pathlib.Path(r"d:\11-20\langgraph-design\intelligent_project_analyzer\config\prompts\few_shot_examples")

# ── File 1: functional_dominant_03.yaml ──
FILE1 = BASE / "functional_dominant_03.yaml"
FILE1.write_text(
    r"""# 示例:过敏儿童医疗级卧室设计
# 来源:q.txt Q32
# 类型:功能主导 (Functional Dominant) / 医疗级标准 + 儿童健康
# 特征:医疗级空气质量、过敏原控制、材料安全筛选、心理治愈环境、儿童成长适配

example:
  project_info:
    name: 过敏儿童医疗级卧室空间设计
    description: |
      深圳福田区90平方米三居室中一间15平方米儿童卧室的医疗级改造，
      业主5岁女儿患有重度尘螨过敏及轻度哮喘，现有卧室环境导致
      夜间频繁过敏发作。项目需建立医疗级空气质量控制体系、
      过敏原全面排除材料方案、心理舒缓治愈环境设计，
      同时满足5-12岁成长期功能适配需求。

    feature_vector:
      functional: 0.85
      technical: 0.70
      sustainable: 0.60
      experiential: 0.52
      aesthetic: 0.40
      material_innovation: 0.58
      social: 0.35
      symbolic: 0.30
      commercial: 0.20
      cultural: 0.15
      historical: 0.10
      regional: 0.15

    constraints:
      - 5岁重度尘螨过敏+轻度哮喘的医疗级环境要求
      - 15平方米有限面积需容纳睡眠+学习+游戏+储物功能
      - 所有材料需通过CMA认证VOC检测
      - 空气质量需满足PM2.5小于15微克每立方米、相对湿度40-60%
      - 设计需适配5-12岁成长期的功能变化需求

    goals:
      - 建立医疗级室内空气质量控制系统
      - 构建过敏原全面排除的材料白名单体系
      - 设计心理舒缓与治愈的空间环境
      - 实现5-12岁成长适配的灵活空间方案
      - 降低夜间过敏发作频率至零

  ideal_tasks:
    - id: task_1
      title: 搜索 儿童尘螨过敏的 医学环境控制标准、室内过敏原种类、空气质量健康指标、国际防过敏住宅案例
      description: |
        系统调研儿童尘螨过敏及哮喘的医学环境控制标准，理解室内过敏原
        分布规律与控制策略，调研国际防过敏住宅设计案例。
      task_type: research
      motivation: functional
      support_search: true
      dimensions:
        - 医学环境控制标准(WHO室内空气质量指南、中国GB/T 18883标准、Allergy UK标准)
        - 室内过敏原种类(尘螨、霉菌孢子、VOC控制)
        - 空气质量健康指标(PM2.5、CO2、相对湿度、换气次数)
        - 国际防过敏住宅案例(Allergy UK认证住宅、日本过敏友好住宅标准)
      priority: high
      execution_order: 1

    - id: task_2
      title: 搜索 医疗级室内材料的 VOC检测标准、防螨材料技术、抗菌表面处理、材料安全白名单构建方法
      description: |
        调研医疗级室内材料的安全标准体系，建立过敏儿童卧室专用的材料安全白名单构建方法论。
      task_type: research
      motivation: technical
      support_search: true
      dimensions:
        - VOC检测标准(甲醛、TVOC、苯系物检测要求)
        - 防螨材料技术(防螨织物、防螨涂层、物理屏障)
        - 抗菌表面处理(银离子抗菌、光触媒、铜离子抑菌)
        - 材料安全白名单(准入标准、检测报告、供应商审核)
      priority: high
      execution_order: 2

    - id: task_3
      title: 搜索 儿童治愈性空间的 色彩心理学研究、自然元素引入策略、安全感空间构建、感官舒缓设计
      description: |
        研究治愈性空间设计在儿童卧室中的应用，包括色彩心理学、自然元素引入、安全感空间构建。
      task_type: research
      motivation: experiential
      support_search: true
      dimensions:
        - 色彩心理学(低饱和蓝绿系舒缓效果、色彩面积控制)
        - 自然元素引入(室内无土水培植物、自然光模拟灯具)
        - 安全感空间构建(包裹感床帐、角落安全巢穴)
        - 感官舒缓设计(柔和触感材料、适宜色温2700-3000K)
      priority: high
      execution_order: 3

    - id: task_4
      title: 设计 医疗级空气质量控制系统的 新风净化方案、温湿度控制策略、空气检测装置、系统联动逻辑
      description: |
        设计15平方米儿童卧室的医疗级空气质量控制系统，包括新风净化双系统方案、
        温湿度精准控制、实时空气质量检测装置。
      task_type: design
      motivation: technical
      support_search: false
      dimensions:
        - 新风净化方案(新风系统+HEPA H13级四级过滤)
        - 温湿度控制策略(除湿机维持40-60%RH+温控22-26度)
        - 空气检测装置(PM2.5/甲醛/CO2/温湿度五参数实时监测)
        - 系统联动逻辑(自动开启净化器+自动除湿+加大新风)
      priority: high
      execution_order: 4

    - id: task_5
      title: 制定 过敏原全面排除的 材料选型白名单、黑名单排除清单、检测验收流程
      description: |
        制定过敏儿童卧室专用的材料选型方案，建立白名单和黑名单，定义检测验收流程。
      task_type: strategy
      motivation: functional
      support_search: false
      dimensions:
        - 材料白名单(实木E0级板材、水性漆、防螨面料、医用级硅藻泥)
        - 黑名单排除(密度板、油性漆、地毯、布艺窗帘、毛绒玩具)
        - 检测验收流程(施工完成通风30天+CMA检测+空气质量达标)
        - 供应商审核标准(CMA检测报告、批次追溯号、环保认证)
      priority: high
      execution_order: 5

    - id: task_6
      title: 设计 防螨寝具系统的 床垫选型方案、防螨床品体系、清洗维护周期
      description: |
        设计儿童卧室的全套防螨寝具系统，从床垫内芯到床品面料全链路防螨控制。
      task_type: design
      motivation: functional
      support_search: false
      dimensions:
        - 床垫选型(天然乳胶床垫防螨+防螨外套全包裹)
        - 防螨床品体系(防螨面料+60度可洗+抗菌处理)
        - 枕芯材质标准(乳胶枕替代羽绒、高度适配5岁儿童)
        - 清洗维护周期(床品周洗60度+床垫季度除螨+枕芯半年更换)
      priority: high
      execution_order: 6

    - id: task_7
      title: 设计 储物系统的 密封防尘方案、衣物收纳分区、玩具管理策略
      description: |
        设计防过敏原积聚的储物系统，所有收纳需具备密封防尘功能。
      task_type: design
      motivation: functional
      support_search: false
      dimensions:
        - 密封防尘方案(带门衣柜、抽屉密封条、收纳箱密封盖)
        - 衣物收纳分区(室外衣物隔离区和室内衣物区)
        - 玩具管理策略(硅胶/木质/塑料玩具准入、毛绒玩具禁入)
        - 过敏原隔离逻辑(外衣不入卧室、鞋类不入卧室)
      priority: high
      execution_order: 7

    - id: task_8
      title: 设计 15平方米儿童卧室的 功能分区方案、家具布局策略、空间效率优化
      description: |
        在15平方米有限面积内规划睡眠区、学习区、游戏区、储物区四大功能。
      task_type: design
      motivation: functional
      support_search: false
      dimensions:
        - 功能分区(睡眠区+学习区+游戏区+储物区+通道)
        - 家具布局(床靠墙、书桌靠窗、衣柜嵌入墙体)
        - 空间效率优化(床下储物、墙面书架、可折叠游戏桌)
        - 灵活性预留(可调节书桌高度、可拆换床架)
      priority: high
      execution_order: 8

    - id: task_9
      title: 制定 治愈性色彩与照明方案、舒缓色彩系统、助眠灯光策略
      description: |
        基于儿童色彩心理学研究，制定过敏儿童卧室的治愈性色彩与灯光方案。
      task_type: design
      motivation: experiential
      support_search: false
      dimensions:
        - 舒缓色彩系统(主色莫兰迪蓝绿+辅色暖米白+点缀柔和粉橙)
        - 昼夜光环境(白天5000K学习+傍晚3500K过渡+夜间2700K助眠)
        - 助眠灯光策略(渐暗模式30分钟+低蓝光夜灯)
        - 自然光优化(薄纱滤光+遮光帘双层)
      priority: medium
      execution_order: 9

    - id: task_10
      title: 设计 5-12岁成长适配方案、家具尺度变化策略、功能渐变规划
      description: |
        设计从5岁到12岁的成长适配方案，定义各年龄段的家具尺度变化和功能需求渐变。
      task_type: design
      motivation: functional
      support_search: false
      dimensions:
        - 家具尺度变化(书桌高度55到75cm可调、椅子高度可调)
        - 功能渐变规划(5-7岁游戏为主、8-10岁学习过渡、11-12岁独立空间)
        - 空间布局调整(游戏区缩小、学习区扩大)
        - 成长时间线(每2年一次软装微调)
      priority: medium
      execution_order: 10

    - id: task_11
      title: 分析 安全防护系统的 防撞设计方案、窗户安全措施、电气安全标准
      description: |
        针对5岁儿童的安全需求，设计全面的安全防护系统。
      task_type: analysis
      motivation: functional
      support_search: false
      dimensions:
        - 防撞设计(家具圆角、墙角软包、床边防坠栏)
        - 窗户安全(限位器、防坠网、儿童锁)
        - 电气安全(插座安全盖、电线暗装、低压LED)
        - 夜间安全(感应夜灯路径、床边呼叫按钮)
      priority: medium
      execution_order: 11

    - id: task_12
      title: 制定 施工过程环境控制规程、无尘施工标准、入住前检测流程
      description: |
        制定施工全过程的环境控制规程，确保施工期间不引入新的过敏原。
      task_type: strategy
      motivation: technical
      support_search: false
      dimensions:
        - 无尘施工标准(施工区域隔离、每日清洁、HEPA吸尘器)
        - 材料进场检测(批次CMA检测报告核验)
        - 通风排毒计划(施工完成后30天强制通风+检测)
        - 入住前检测流程(CMA五项检测+密闭舱法)
      priority: high
      execution_order: 12

    - id: task_13
      title: 制定 日常维护手册、清洁消毒周期表、设备保养计划
      description: |
        编制家长可执行的日常维护手册，包括清洁消毒任务清单和设备保养计划。
      task_type: strategy
      motivation: functional
      support_search: false
      dimensions:
        - 清洁消毒周期表(每日湿拖+每周床品洗+每月除螨+每季深度清洁)
        - 设备保养计划(净化器滤芯3月换+新风系统半年维护)
        - 空气质量监控(每日APP查看+季度专业检测)
        - 应急预案(过敏发作急救+通风操作+就医联系)
      priority: medium
      execution_order: 13

    - id: task_14
      title: 评估 整体方案的 医疗合规性验证、成本效益分析、家长可执行度
      description: |
        对整体设计方案进行综合评估，验证医疗级标准的合规性，分析投入产出。
      task_type: analysis
      motivation: functional
      support_search: false
      dimensions:
        - 医疗合规性(各项空气质量指标达标率、材料安全标准满足度)
        - 成本效益分析(改造总投入vs减少过敏就医费用)
        - 家长可执行度(日常维护时间控制、操作难度评估)
        - 长期健康效益(夜间过敏发作频率降低目标)
      priority: medium
      execution_order: 14

  quality_highlights:
    - 14任务医疗级深度 过敏医学标准到材料安全体系到环境控制系统到治愈性空间到维护方案
    - 空气质量控制体系 新风+HEPA四级过滤+温湿度精控+实时监测+智能联动
    - 材料安全白名单制 CMA认证准入+黑名单排除+施工过程检测+入住前全项验收
    - 防螨寝具全链路 乳胶床垫+防螨外套+防螨面料+60度周洗+季度深度除螨
    - 治愈性空间设计 莫兰迪色彩+助眠灯光+自然元素+安全感包裹+感官舒缓
    - 成长适配方案 5-12岁七年成长时间线+可调家具+功能渐变+软装微调策略

metadata:
  tags_matrix:
    space_type:
      - bedroom
      - family_residence
      - children_room
    scale: small
    design_direction:
      - functional
      - technical
      - sustainable
      - experiential
    user_profile:
      - family
      - children
      - special_needs
      - health_sensitive
    challenge_type:
      - technical_complexity
      - health_safety
      - material_specification
      - growth_adaptation
    methodology:
      - medical_research
      - technical_innovation
      - material_testing
      - evidence_based_design
    phase: concept_to_detailed
  discipline: interior_design
  urgency: 0.65
  innovation_quotient: 0.60
  commercial_sensitivity: 0.20
  cultural_depth: 0.15
  performance:
    specialty_score: 0.70
    recommended_strength: strong
  best_for:
    - "医疗级住宅空间设计"
    - "过敏体质儿童房设计"
    - "空气质量控制系统整合"
    - "材料安全标准筛选"
  not_suitable_for:
    - "商业空间设计"
    - "无健康特殊需求项目"
    - "大型公共建筑"
""".lstrip(),
    encoding="utf-8",
)
print(f"[1/3] Created {FILE1.name} ({FILE1.stat().st_size} bytes)")

# ── File 2: sustainable_dominant_02.yaml ──
FILE2 = BASE / "sustainable_dominant_02.yaml"
FILE2.write_text(
    r"""# 示例:三亚海边木结构抗腐餐厅设计
# 来源:q.txt Q86
# 类型:可持续主导 (Sustainable Dominant) / 材料耐久性 + 气候适应性
# 特征:滨海木结构、防腐体系、台风抗性、材料耐久、区域气候适应

example:
  project_info:
    name: 三亚海边木结构抗腐餐厅空间设计
    description: |
      三亚海棠湾300平方米海景餐厅设计，业主要求采用木结构为主的建筑形式，
      营造热带度假氛围。项目核心挑战在于高湿(年均RH 80%+)、高盐(距海500m)、
      强台风(年均3-5次)环境下木结构的耐久性与防腐性能保障，
      需建立完整的材料防护体系与全生命周期维护策略。

    feature_vector:
      sustainable: 0.60
      technical: 0.65
      material_innovation: 0.68
      functional: 0.58
      regional: 0.55
      aesthetic: 0.50
      commercial: 0.45
      experiential: 0.52
      cultural: 0.35
      social: 0.30
      historical: 0.25
      symbolic: 0.38

    constraints:
      - 距海500m高盐雾环境(年均NaCl沉降量高)
      - 年均台风3-5次(最大风力可达16级)
      - 年均相对湿度80%以上(霉菌滋生高风险)
      - 木结构需满足30年使用寿命要求
      - 300平方米餐厅需满足120座位容量

    goals:
      - 建立滨海木结构防腐防护完整体系
      - 设计抗台风结构系统与应急方案
      - 构建材料耐久性全生命周期管理策略
      - 实现热带度假氛围与结构安全的平衡
      - 控制初始投资与全生命周期成本平衡

  ideal_tasks:
    - id: task_1
      title: 搜索 滨海木结构建筑的 国际标杆案例、材料防腐技术、气候适应策略、使用寿命数据
      description: |
        调研国际滨海木结构建筑的成功案例，包括东南亚热带木建筑传统、
        澳大利亚滨海度假建筑、日本耐候性木结构设计，提取材料选型与防护策略。
      task_type: research
      motivation: sustainable
      support_search: true
      dimensions:
        - 国际标杆案例(东南亚传统木架构、澳大利亚滨海度假村、日本耐候木建筑)
        - 材料防腐技术(ACQ防腐处理、炭化木技术、铜唑防腐剂、硼化合物)
        - 气候适应策略(通风除湿设计、屋面排水优化、海风导流)
        - 使用寿命数据(各树种滨海环境耐久年限、维护周期与成本)
      priority: high
      execution_order: 1

    - id: task_2
      title: 搜索 热带滨海环境的 木材腐蚀机理、盐雾侵蚀特征、霉菌滋生条件、虫害防治策略
      description: |
        深入研究热带滨海环境对木结构的破坏机理，理解木材腐蚀的化学与生物过程，
        为防护体系设计提供科学依据。
      task_type: research
      motivation: technical
      support_search: true
      dimensions:
        - 木材腐蚀机理(真菌腐朽、化学降解、物理风化、紫外线老化)
        - 盐雾侵蚀特征(氯离子渗透、金属连接件腐蚀、表面结晶)
        - 霉菌滋生条件(含水率大于20%、温度20-35度、通风不良)
        - 虫害防治策略(白蚁防治、海洋钻孔虫、甲虫类防治)
      priority: high
      execution_order: 2

    - id: task_3
      title: 搜索 抗台风建筑结构的 设计规范、连接节点技术、风载荷计算、破坏性试验数据
      description: |
        研究抗台风建筑结构设计的规范与技术，包括木结构抗风连接节点设计、
        风载荷计算方法、台风破坏模式分析。
      task_type: research
      motivation: technical
      support_search: true
      dimensions:
        - 设计规范(GB 50005木结构设计规范、ASCE 7风载荷标准、海南地方规范)
        - 连接节点技术(抗拔锚栓、剪力连接板、胶合螺栓节点、金属抗风夹)
        - 风载荷计算(基本风压值、体型系数、高度变化系数、地面粗糙度)
        - 破坏性试验数据(木框架抗风测试、屋面掀翻机理、薄弱环节识别)
      priority: high
      execution_order: 3

    - id: task_4
      title: 设计 木材选型与防腐处理的 树种对比方案、防腐工艺流程、防腐等级标准、成本效益分析
      description: |
        基于滨海环境要求，设计木材选型方案，对比不同树种的耐久性与成本，
        制定防腐处理工艺流程与质量控制标准。
      task_type: design
      motivation: material_innovation
      support_search: false
      dimensions:
        - 树种对比方案(菠萝格vs柚木vs炭化松木vs防腐南方松vs塑木复合)
        - 防腐工艺流程(真空加压浸渍+表面涂层+端头封蜡三重防护)
        - 防腐等级标准(C4以上滨海环境等级、防腐剂载药量)
        - 成本效益分析(初始成本+维护成本+更换成本的30年全周期)
      priority: high
      execution_order: 4

    - id: task_5
      title: 设计 抗台风木结构体系的 主体结构方案、连接节点设计、屋面抗掀系统、应急加固预案
      description: |
        设计300平方米餐厅的抗台风木结构体系，包括主体框架、屋面系统、
        连接节点的详细设计方案。
      task_type: design
      motivation: technical
      support_search: false
      dimensions:
        - 主体结构方案(重型木框架+钢木混合节点、基础锚固系统)
        - 连接节点设计(不锈钢角码、预埋螺栓、胶合钢板连接)
        - 屋面抗掀系统(屋面板锚固+檐口加固+通风减压设计)
        - 应急加固预案(可拆卸挡风板、活动百叶关闭系统、台风前检查清单)
      priority: high
      execution_order: 5

    - id: task_6
      title: 设计 金属连接件防锈系统的 材质选型、防腐涂层、电化学防护、检查更换方案
      description: |
        设计木结构金属连接件的全面防锈系统，确保高盐环境下连接件的安全性。
      task_type: design
      motivation: technical
      support_search: false
      dimensions:
        - 材质选型(316L不锈钢、热镀锌钢、钛合金特殊部位)
        - 防腐涂层(富锌底漆+环氧中间漆+聚氨酯面漆三层)
        - 电化学防护(牺牲阳极法、绝缘垫片隔离异种金属)
        - 检查更换方案(年度检查+5年更换清单+紧固力矩标准)
      priority: high
      execution_order: 6

    - id: task_7
      title: 设计 通风除湿系统的 自然通风策略、机械除湿方案、地面防潮构造、屋面排水系统
      description: |
        设计滨海高湿环境下的综合除湿系统，控制木构件含水率在安全范围内。
      task_type: design
      motivation: sustainable
      support_search: false
      dimensions:
        - 自然通风策略(穿堂风设计、屋脊通风口、地面架空通风)
        - 机械除湿方案(工业除湿机配置、湿度传感器联动)
        - 地面防潮构造(架空层300mm+防潮膜+排水层)
        - 屋面排水系统(大坡度排水+防回流风帽+天沟加大)
      priority: high
      execution_order: 7

    - id: task_8
      title: 设计 热带度假氛围的 空间营造方案、材料美学表达、海景框景设计、室内外过渡空间
      description: |
        在满足结构安全前提下，设计热带度假氛围的空间方案，实现功能与美学平衡。
      task_type: design
      motivation: aesthetic
      support_search: false
      dimensions:
        - 空间营造方案(开放式半室外用餐区+室内空调区+景观平台)
        - 材料美学表达(木材自然纹理展示、防腐处理后的色泽管理)
        - 海景框景设计(景观面最大化开窗+防风门窗系统)
        - 室内外过渡空间(半开敞廊道+可开闭折叠门系统)
      priority: medium
      execution_order: 8

    - id: task_9
      title: 制定 餐厅功能布局的 座位容量方案、厨房动线设计、服务流线规划、设备防潮策略
      description: |
        设计300平方米餐厅的完整功能布局，满足120座位容量需求。
      task_type: design
      motivation: functional
      support_search: false
      dimensions:
        - 座位容量方案(室内80座+半室外40座+灵活调配机制)
        - 厨房动线设计(中央厨房+备餐区+出餐口+回收路线)
        - 服务流线规划(前厅动线+后厨动线+客流动线分离)
        - 设备防潮策略(不锈钢设备+密封电气箱+防潮排风)
      priority: medium
      execution_order: 9

    - id: task_10
      title: 制定 全生命周期维护策略的 定期检查规程、维修更换计划、成本预算周期、监测预警系统
      description: |
        建立木结构餐厅30年全生命周期的维护管理体系。
      task_type: strategy
      motivation: sustainable
      support_search: false
      dimensions:
        - 定期检查规程(月度巡查+季度专项+年度全面+台风后特检)
        - 维修更换计划(表面涂层3年重涂+结构件10年检测+连接件5年检查)
        - 成本预算周期(年维护费用占初装3-5%+储备更换基金)
        - 监测预警系统(含水率传感器+变形监测+腐蚀电位检测)
      priority: high
      execution_order: 10

    - id: task_11
      title: 分析 初始投资与全生命周期成本的 方案对比、敏感性分析、风险评估
      description: |
        对不同结构和材料方案进行全生命周期成本对比分析。
      task_type: analysis
      motivation: commercial
      support_search: false
      dimensions:
        - 方案对比(纯木方案vs钢木混合vs钢结构木饰面的30年总成本)
        - 敏感性分析(台风损失频率、材料价格波动、维护频率变化)
        - 风险评估(结构失效风险、营业中断损失、保险费用)
        - 投资回报(热带木结构品牌溢价、客单价提升、网红打卡效应)
      priority: medium
      execution_order: 11

    - id: task_12
      title: 整合 总体设计方案、结构施工详图要点、材料采购规范、质量验收标准
      description: |
        基于前期研究与设计成果，整合形成完整的设计方案文件体系。
      task_type: strategy
      motivation: functional
      support_search: false
      dimensions:
        - 总体设计方案(结构布局+功能分区+材料方案+设备系统)
        - 结构施工详图要点(关键节点详图+预埋件定位+安装顺序)
        - 材料采购规范(木材等级标准+防腐处理验收+金属件材质证明)
        - 质量验收标准(结构安全检测+防腐质量抽检+防水试验+整体验收)
      priority: high
      execution_order: 12

  quality_highlights:
    - 12任务覆盖滨海木结构全生命周期 标杆研究到材料选型到结构设计到维护管理
    - 防腐体系三重防护 真空加压浸渍+表面涂层+端头封蜡系统化方案
    - 抗台风结构完整闭环 主体框架+连接节点+屋面抗掀+应急预案
    - 金属连接件防锈系统 316L不锈钢+三层涂层+电化学防护+定期更换
    - 通风除湿综合策略 自然通风+机械除湿+架空防潮+屋面排水
    - 30年全生命周期成本分析 初始投资+年维护+更换储备+风险评估

metadata:
  tags_matrix:
    space_type:
      - restaurant
      - commercial
      - coastal_building
    scale: medium
    design_direction:
      - sustainable
      - technical
      - regional
      - aesthetic
    user_profile:
      - public
      - tourists
      - commercial_operator
    challenge_type:
      - material_durability
      - climate_adaptation
      - technical_complexity
      - typhoon_resistance
    methodology:
      - material_research
      - technical_innovation
      - regional_adaptation
      - lifecycle_analysis
    phase: concept_to_detailed
  discipline: architecture
  urgency: 0.50
  innovation_quotient: 0.60
  commercial_sensitivity: 0.55
  cultural_depth: 0.30
  performance:
    specialty_score: 0.65
    recommended_strength: medium
  best_for:
    - "滨海建筑设计"
    - "木结构防腐体系"
    - "极端气候应对设计"
    - "材料耐久性优化"
  not_suitable_for:
    - "内陆常规建筑"
    - "纯室内设计项目"
    - "无气候挑战项目"
""".lstrip(),
    encoding="utf-8",
)
print(f"[2/3] Created {FILE2.name} ({FILE2.stat().st_size} bytes)")

# ── File 3: social_dominant_02.yaml ──
FILE3 = BASE / "social_dominant_02.yaml"
FILE3.write_text(
    r"""# 示例:保障性住房高品质设计模型
# 来源:q.txt Q69
# 类型:社会主导 (Social Dominant) / 保障性住房 + 尊严设计
# 特征:低成本高品质、标准化模块化、社会公平设计、尊严感空间、可复制推广

example:
  project_info:
    name: 保障性住房高品质设计模型
    description: |
      深圳光明区保障性住房项目，户型面积60-90平方米，目标控制造价在
      2000元/平方米以内，同时实现不低于商品房80%的居住品质。
      项目需探索低成本高品质的平衡方法论，建立标准化模块设计体系，
      确保住户的居住尊严感，并形成可大规模复制推广的设计模型。

    feature_vector:
      social: 0.70
      functional: 0.65
      sustainable: 0.55
      aesthetic: 0.45
      commercial: 0.35
      technical: 0.40
      material_innovation: 0.38
      experiential: 0.48
      cultural: 0.30
      regional: 0.25
      historical: 0.15
      symbolic: 0.40

    constraints:
      - 造价控制在2000元/平方米以内
      - 户型面积60-90平方米(一居到三居)
      - 需满足不低于商品房80%的居住品质
      - 设计需可大规模标准化复制
      - 需通过政府保障性住房审核标准

    goals:
      - 建立低成本高品质的设计平衡模型
      - 构建4种标准户型+8个功能模块系统
      - 确保居住尊严感的空间品质表达
      - 形成可复制的保障性住房设计方法论
      - 实现政策对接与社会影响力

  ideal_tasks:
    - id: task_1
      title: 搜索 国内外保障性住房的 高品质设计标杆、低成本创新案例、尊严设计理论、政策标准
      description: |
        系统调研保障性住房的高品质设计案例，包括新加坡HDB组屋体系、
        维也纳社会住宅传统、日本公营住宅设计标准，提取低成本高品质的设计策略。
      task_type: research
      motivation: social
      support_search: true
      dimensions:
        - 高品质设计标杆(新加坡HDB优质组屋、维也纳社会住宅、智利Elemental增量住宅)
        - 低成本创新案例(模块化预制、集成卫浴、整体厨房、标准化内装)
        - 尊严设计理论(Universal Design原则、包容性设计、基本空间品质底线)
        - 政策标准(中国保障性住房面积标准、造价限额、配套要求)
      priority: high
      execution_order: 1

    - id: task_2
      title: 搜索 标准化住宅模块系统的 国际经验、预制装配技术、工业化内装、成本控制方法
      description: |
        调研住宅标准化与工业化的国际经验与技术路径。
      task_type: research
      motivation: technical
      support_search: true
      dimensions:
        - 国际经验(日本SI住宅体系、欧洲被动房标准化、新加坡PPVC技术)
        - 预制装配技术(预制构件标准化、模块化卫浴、整体厨房单元)
        - 工业化内装(干法施工、集成管线墙、标准化收纳模块)
        - 成本控制方法(规模化采购、简化工艺、减少湿作业、缩短工期)
      priority: high
      execution_order: 2

    - id: task_3
      title: 搜索 低成本材料创新的 性价比材料库、替代材料方案、材料组合策略、品质感提升技巧
      description: |
        研究在成本限制下提升材料品质感的策略。
      task_type: research
      motivation: material_innovation
      support_search: true
      dimensions:
        - 性价比材料库(国产优质替代进口、新型经济材料、再生材料应用)
        - 替代材料方案(仿石瓷砖替代天然石材、PVC地板替代实木、水磨石替代大理石)
        - 材料组合策略(少量精致材料+大面积经济材料的点缀法)
        - 品质感提升技巧(工艺精度补偿材料档次、色彩协调提升整体感)
      priority: high
      execution_order: 3

    - id: task_4
      title: 分析 目标住户群体的 家庭结构特征、生活行为模式、收纳需求层次、品质期望调研
      description: |
        调研保障性住房目标群体的真实需求，为设计提供用户洞察。
      task_type: analysis
      motivation: social
      support_search: false
      dimensions:
        - 家庭结构特征(青年夫妻、三口之家、三代同堂的比例与需求)
        - 生活行为模式(居家办公需求、儿童活动空间、老人日常起居)
        - 收纳需求层次(基本衣物收纳+厨房储物+杂物归整)
        - 品质期望调研(最在意的品质点排序 采光通风收纳隐私)
      priority: high
      execution_order: 4

    - id: task_5
      title: 设计 4种标准户型的 平面布局方案、面积效率优化、功能完整性验证、通风采光保障
      description: |
        设计一居(60平方米)、小两居(70平方米)、两居(80平方米)、三居(90平方米)
        四种标准户型，确保每种户型的功能完整性和居住舒适度。
      task_type: design
      motivation: functional
      support_search: false
      dimensions:
        - 平面布局方案(四种户型的功能分区、家具布置、动线组织)
        - 面积效率优化(实用率大于85%、零浪费走廊、多功能空间)
        - 功能完整性验证(厨卫齐全+收纳充足+起居完整+就寝私密)
        - 通风采光保障(每户至少两面采光+穿堂风可能+日照时数)
      priority: high
      execution_order: 5

    - id: task_6
      title: 设计 8个标准功能模块的 详细方案、尺寸标准、接口规范、成本控制
      description: |
        设计可组合的8个标准功能模块(厨房、卫生间、玄关、主卧、次卧、
        客厅、阳台、储物)的详细方案。
      task_type: design
      motivation: functional
      support_search: false
      dimensions:
        - 模块详细方案(每个模块的平面、立面、设备配置)
        - 尺寸标准(模数化尺寸、接口标准化、公差控制)
        - 接口规范(管线接口位置、预埋件标准、模块间连接)
        - 成本控制(每个模块目标成本、材料BOM清单、人工预估)
      priority: high
      execution_order: 6

    - id: task_7
      title: 制定 尊严设计标准的 空间品质底线、入户仪式感、公共空间品质、细节品质控制
      description: |
        定义保障性住房的尊严设计标准，确保低成本不等于低品质。
      task_type: design
      motivation: social
      support_search: false
      dimensions:
        - 空间品质底线(最小净高2.7m+最小卧室8平方米+最小厨房4平方米)
        - 入户仪式感(玄关空间+鞋柜+换鞋凳+挂钩的基本配置)
        - 公共空间品质(大堂整洁明亮+走廊宽度适当+电梯数量充足)
        - 细节品质控制(五金件品质+开关面板统一+收口工艺精度)
      priority: high
      execution_order: 7

    - id: task_8
      title: 设计 低成本高品质的 色彩系统、材料组合方案、照明策略、软装指导清单
      description: |
        在成本限制下构建提升空间品质感的视觉系统。
      task_type: design
      motivation: aesthetic
      support_search: false
      dimensions:
        - 色彩系统(以白色系为基底+局部彩色点缀+木色温暖搭配)
        - 材料组合方案(白色乳胶漆+仿木纹瓷砖+不锈钢配件)
        - 照明策略(基础筒灯+重点照明+面板灯带均匀照度)
        - 软装指导清单(基本家具推荐清单+色彩搭配指南+收纳建议)
      priority: medium
      execution_order: 8

    - id: task_9
      title: 制定 成本工程方案的 分项预算编制、价值工程分析、采购策略、成本红线管理
      description: |
        建立精准的成本控制体系，确保2000元/平方米造价目标可达。
      task_type: strategy
      motivation: commercial
      support_search: false
      dimensions:
        - 分项预算编制(土建+安装+装修+设备+管理费分项分配)
        - 价值工程分析(高成本低价值项目削减+低成本高价值项目加强)
        - 采购策略(集中采购降成本10%以上+战略供应商合作)
        - 成本红线管理(不可突破项目+弹性调整项目+紧急储备)
      priority: high
      execution_order: 9

    - id: task_10
      title: 设计 可变性预留方案的 家庭成长适配、空间灵活隔断、管线预留策略、一次硬装多次软装
      description: |
        设计适应家庭结构变化的空间可变性方案。
      task_type: design
      motivation: sustainable
      support_search: false
      dimensions:
        - 家庭成长适配(新婚到三口到三代的空间进化路径)
        - 空间灵活隔断(轻质隔墙预留+活动门体系+家具隔断)
        - 管线预留策略(多点位给排水预留+电路扩容空间+网络布线)
        - 一次硬装多次软装(硬装极简经典+软装可替换更新)
      priority: medium
      execution_order: 10

    - id: task_11
      title: 分析 社会影响力评估的 住户满意度预测、社会公平贡献、政策对接路径、可复制性评估
      description: |
        从社会价值维度评估设计方案的综合影响力。
      task_type: analysis
      motivation: social
      support_search: false
      dimensions:
        - 住户满意度预测(空间舒适度+功能完整度+品质感知度+邻里关系)
        - 社会公平贡献(缩小住房品质差距、提升低收入家庭生活质量)
        - 政策对接路径(符合国家保障房标准、地方配套政策、申报流程)
        - 可复制性评估(标准化程度+地域适配调整范围+实施门槛)
      priority: medium
      execution_order: 11

    - id: task_12
      title: 整合 保障性住房设计导则、标准户型图集、模块化设计手册、施工指导规范
      description: |
        整合形成可推广的保障性住房设计成果文件体系。
      task_type: strategy
      motivation: social
      support_search: false
      dimensions:
        - 设计导则(设计原则+品质标准+成本红线+尊严设计要求)
        - 标准户型图集(4种户型平面图+家具布置图+管线综合图)
        - 模块化设计手册(8个模块详图+接口规范+组合规则)
        - 施工指导规范(装配流程+质量控制+验收标准+工期计划)
      priority: high
      execution_order: 12

  quality_highlights:
    - 12任务社会主导分布 标杆研究25%+户型设计25%+成本控制25%+整合推广25%
    - 低成本高品质平衡 2000元/平方米造价限制下的品质最大化策略
    - 标准化模块系统 4种户型+8个功能模块的可组合体系
    - 尊严设计标准 空间品质底线+入户仪式感+细节品质控制
    - 成本工程方法 价值工程分析+集中采购+成本红线管理
    - 可复制推广性 标准化设计+地域适配框架+政策对接路径

metadata:
  tags_matrix:
    space_type:
      - apartment
      - residence
      - affordable_housing
    scale: small
    design_direction:
      - social
      - functional
      - sustainable
      - aesthetic
    user_profile:
      - family
      - low_income
      - young
      - elderly
    challenge_type:
      - budget_control
      - dignity_design
      - standardization
      - scalability
    methodology:
      - modular_design
      - cost_engineering
      - scalable_solution
      - value_engineering
    phase: concept_to_detailed
  discipline: architecture
  urgency: 0.55
  innovation_quotient: 0.50
  commercial_sensitivity: 0.35
  cultural_depth: 0.25
  performance:
    specialty_score: 0.55
    recommended_strength: medium
  best_for:
    - "保障性住房设计"
    - "低成本高品质平衡"
    - "标准化模块化设计"
    - "社会公平设计实践"
  not_suitable_for:
    - "高端定制住宅"
    - "商业空间设计"
    - "无成本约束项目"
""".lstrip(),
    encoding="utf-8",
)
print(f"[3/3] Created {FILE3.name} ({FILE3.stat().st_size} bytes)")

print("\n--- All 3 files created. Verifying YAML parsing... ---\n")

import yaml

for name in ["functional_dominant_03", "sustainable_dominant_02", "social_dominant_02"]:
    p = BASE / f"{name}.yaml"
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    print(f"{name}: OK, keys={list(data.keys())}")

print("\nDone!")
