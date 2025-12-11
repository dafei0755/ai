'use client';

import React, { useState } from 'react';
import ReportSectionCard from '@/components/report/ReportSectionCard';

/**
 * Phase 4 任务5 - 灵活输出架构端到端测试页面
 *
 * 测试目标：
 * 1. 验证130+字段中文映射正确性
 * 2. 验证Targeted模式蓝色高亮UI
 * 3. 验证13个嵌套模型特殊样式
 * 4. 验证Comprehensive模式层级展示
 */

// 测试场景1: V6-1 Targeted模式 - 结构体系选择
const testScenario1 = {
  section_name: "V6-1 结构与幕墙专家 - Targeted模式",
  content: JSON.stringify({
    output_mode: "targeted",
    user_question_focus: "如何选择结构体系？",
    confidence: 0.88,
    design_rationale: "基于项目类型和规模的结构体系比选",
    targeted_analysis: {
      structural_system_comparison: {
        recommended_system: "框架-剪力墙体系",
        reasoning: "综合考虑建筑高度（80m）、抗震设防烈度（8度）、大跨度空间需求",
        key_advantages: [
          "适应不规则平面布局",
          "满足大跨度空间（18m×24m展厅）",
          "抗震性能优越",
          "施工周期可控（16个月）"
        ],
        alternative_option: {
          system: "纯框架体系",
          trade_off: "经济性更优但抗震性能略差，不推荐"
        }
      }
    }
  })
};

// 测试场景2: V6-1 Comprehensive模式 - 完整技术方案（含KeyNodeAnalysis嵌套模型）
const testScenario2 = {
  section_name: "V6-1 结构与幕墙专家 - Comprehensive模式",
  content: JSON.stringify({
    output_mode: "comprehensive",
    user_question_focus: "完整的结构与幕墙技术方案",
    confidence: 0.92,
    design_rationale: "系统性技术可行性分析",
    feasibility_assessment: "项目可行性评估：总体可行，需重点关注地基处理和大跨度结构。地质条件良好（承载力350kPa），但局部有软土层需加固。建筑高度80m，属于B级高度，抗震设防烈度8度，需采用高性能结构体系。",
    structural_system_options: "结构体系选项：推荐方案A（框架-剪力墙体系）- 适应性强，抗震性能优越；备选方案B（纯框架体系）- 经济性好但抗震性能略差；不推荐方案C（框架-核心筒）- 平面布局受限。",
    facade_system_options: "幕墙体系选项：单元式玻璃幕墙+铝板幕墙组合。主立面采用单元式幕墙（U值1.8 W/㎡·K），裙房采用铝板幕墙（降低成本），顶部采用采光顶（ETFE膜结构）。",
    key_technical_nodes: [
      {
        node_name: "展厅大跨度结构",
        challenge: "18m×24m无柱大空间，荷载传递路径复杂，活荷载5.0kN/㎡",
        proposed_solution: "采用预应力钢桁架+型钢混凝土柱方案。跨度24m采用双向桁架（高度2.4m），跨度18m采用次桁架（高度1.8m）。柱距6m，柱截面800×800mm。",
        coordination_requirements: "需与机电专业协调：1)预留设备吊装口（3m×3m）；2)桁架下弦预留风管穿越孔；3)照明灯具吊点需结构配合。"
      },
      {
        node_name: "玻璃幕墙抗震设计",
        challenge: "8度抗震区，层间位移角1/800，幕墙变形适应性要求高",
        proposed_solution: "采用浮动连接+双道密封系统。横向预留±50mm变形量，竖向预留±30mm。幕墙分格3.0m×3.6m，采用Low-E中空玻璃（6+12A+6mm）。",
        coordination_requirements: "与结构专业确认：1)层间位移角计算值；2)幕墙连接件锚固深度；3)防雷接地方案。"
      }
    ],
    risk_analysis_and_recommendations: "风险分析与建议：1.地基承载力风险-软土层厚度3m，建议桩基础（钻孔灌注桩，桩长25m）；2.幕墙施工精度风险-建议先做1:1样板段验证；3.大跨度结构施工风险-建议采用分段吊装+临时支撑方案；4.工期风险-结构施工8个月，幕墙施工5个月，总工期16个月，建议预留2个月buffer。"
  })
};

// 测试场景3: V5-1 Comprehensive模式 - 家庭画像（含FamilyMemberProfile + DesignChallenge嵌套模型）
const testScenario3 = {
  section_name: "V5-1 居住场景专家 - Comprehensive模式",
  content: JSON.stringify({
    output_mode: "comprehensive",
    user_question_focus: "三口之家的居住空间设计",
    confidence: 0.90,
    design_rationale: "基于家庭成员画像的空间需求分析",
    family_profile_and_needs: "家庭画像：夫妻+6岁女儿，双职工家庭，重视教育和生活品质。父亲IT工程师（远程办公需求），母亲市场总监（偶尔带工作回家），女儿幼儿园大班（未来10年成长空间）。家庭年收入50万，购房预算500万，面积120㎡三居室。",
    lifestyle_deconstruction: "生活方式拆解：工作日快节奏（早7:00-晚19:00），父亲需居家办公2天/周，母亲需化妆梳妆空间，女儿需学习玩耍空间。周末家庭时光（亲子互动+朋友聚会），重视收纳整理（减少视觉混乱）。",
    spatial_requirements: "空间需求：1)主卧套房（含卫生间+梳妆区+衣帽间）；2)独立书房（双人工位+储物）；3)儿童房（睡眠+玩耍+学习三合一）；4)开放式厨客餐（家庭互动核心）；5)充足储物（分散式+集中式结合）。",
    family_member_profiles: [
      {
        member: "父亲（35岁，IT工程师）",
        daily_routine: "早7:00出门，晚19:00回家，周2天居家办公，周末偶尔加班（游戏研发项目）",
        spatial_needs: [
          "独立书房（远程办公+游戏，需隔音）",
          "储物空间（电子设备+手办收藏+技术书籍）",
          "健身空间（瑜伽垫+哑铃，早晨锻炼）"
        ],
        storage_needs: [
          "电子设备柜（笔记本3台+显示器2台+键盘鼠标+数据线）",
          "衣物收纳（商务装5套+休闲装10套+鞋柜）",
          "书籍收纳（技术书200本+小说50本+杂志）"
        ],
        privacy_level: "高（工作时需要独立安静空间，不被打扰）"
      },
      {
        member: "母亲（33岁，市场总监）",
        daily_routine: "早8:00出门，晚18:30回家，偶尔带工作回家（报告撰写），周末购物+聚会",
        spatial_needs: [
          "梳妆区（化妆+护肤，晨间30分钟）",
          "衣帽间（服装+包包+鞋，精致收纳）",
          "会客空间（偶尔家庭聚会，接待朋友）"
        ],
        storage_needs: [
          "化妆品收纳（护肤品50件+化妆品30件+工具，需分类+展示）",
          "服装收纳（挂放100件+叠放50件+鞋50双+包20个）",
          "箱包收纳（手袋10个+行李箱3个+随身包5个）"
        ],
        privacy_level: "中（需要个人空间但也享受家庭互动，梳妆时需隐私）"
      },
      {
        member: "女儿（6岁，幼儿园大班）",
        daily_routine: "早8:00上学，晚17:00放学，18:00-19:00做作业，19:00-20:00玩耍，20:30睡觉。周末兴趣班（舞蹈+英语）+家庭活动",
        spatial_needs: [
          "儿童房（睡眠+玩耍+学习，需可变性）",
          "玩具区（乐高+娃娃+绘本，易于整理）",
          "学习区（写字台+书架，培养学习习惯）"
        ],
        storage_needs: [
          "玩具收纳（大型玩具10件+小型玩具50件+绘本100本，分类整理，孩子可自行取放）",
          "衣物收纳（儿童衣柜，挂放30件+叠放50件+鞋10双）",
          "文具书籍收纳（绘本+学习用品+手工材料）"
        ],
        privacy_level: "低（需要父母陪伴和监护，但也需要独立玩耍空间）"
      }
    ],
    design_challenges_for_v2: [
      {
        challenge: "平衡工作与家庭空间",
        context: "父母都需要居家办公空间，但房屋面积有限（120㎡，实际使用面积约100㎡）",
        constraints: [
          "书房与主卧相邻，需隔音处理（降噪系数≥30dB）",
          "客厅需兼顾办公功能（母亲偶尔在客厅工作）",
          "儿童活动不能影响父母工作（动静分区）"
        ],
        priority: "高"
      },
      {
        challenge: "儿童成长空间的可变性",
        context: "孩子6岁，未来10年（6-16岁）空间需求会显著变化",
        constraints: [
          "儿童房需支持睡眠、玩耍、学习三种功能",
          "家具需可调整（床长度1.5m→2.0m，桌椅高度可调）",
          "玩具收纳需灵活（从大型玩具过渡到文具书籍）"
        ],
        priority: "中"
      },
      {
        challenge: "储物空间的最大化",
        context: "三口之家物品众多（衣物、书籍、电子设备、玩具），需系统性收纳方案",
        constraints: [
          "避免视觉杂乱（隐藏式储物为主）",
          "便于取放（常用物品在1.2m-1.5m高度）",
          "分类收纳（衣物/书籍/电子设备/玩具分区）"
        ],
        priority: "高"
      }
    ]
  })
};

// 测试场景4: V5-2 Comprehensive模式 - 零售KPI（含RetailKPI嵌套模型）
const testScenario4 = {
  section_name: "V5-2 商业零售运营专家 - Comprehensive模式",
  content: JSON.stringify({
    output_mode: "comprehensive",
    user_question_focus: "购物中心的空间设计如何支撑运营目标",
    confidence: 0.89,
    design_rationale: "基于零售KPI的空间策略设计",
    business_goal_analysis: "商业目标分析：目标年坪效4.0万元/㎡（行业平均3.2万元），年客流量300万人次（日均8,000人次），平均停留时长90分钟（行业平均70分钟），转化率35%（行业平均28%）。项目定位：城市综合体，总建筑面积12万㎡，其中商业6万㎡，办公4万㎡，公寓2万㎡。",
    customer_journey: "顾客旅程分析：停车（地下3层，2000车位）→ 入口（4个主入口+6个次入口）→ 中庭（1500㎡景观中庭，打卡点）→ 主力店（ZARA/优衣库/星巴克）→ 餐饮区（3F，占比25%）→ 娱乐区（5F影院+儿童乐园）→ 离开。平均动线长度600m，停留节点12个。",
    operational_efficiency: "运营效率分析：货物动线与顾客动线完全分离（后勤通道独立）。后勤面积占比12%（行业标准10-15%）。卸货区6个（早6:00-10:00集中配送）。垃圾处理独立通道（避免顾客感知）。员工通道与顾客通道分离（提升体验）。",
    key_performance_indicators: [
      {
        metric: "坪效（年销售额/营业面积）",
        target: "4.0万元/㎡/年",
        current_benchmark: "行业平均3.2万元/㎡/年，优秀项目5.0万元/㎡/年",
        spatial_strategy: "提升策略：1)增加体验业态占比至40%（餐饮25%+娱乐15%），减少传统零售至60%；2)优化动线可见性（主力店临街，次主力店分散引导动线）；3)打造网红打卡点（中庭景观+屋顶花园+艺术装置3处）；4)灵活铺位设计（支持快闪店+季节性调整）"
      },
      {
        metric: "客流量（日均）",
        target: "8,000人次/日",
        current_benchmark: "周边竞品商场A（6,500人次/日）、商场B（7,200人次/日）",
        spatial_strategy: "吸引策略：1)中庭景观设计（1500㎡水景+绿植，每月更换主题）；2)定期活动场地（预留300㎡活动区，周末市集+节日庆典）；3)打卡点设置（艺术装置3处+观景平台2处）；4)入口可达性优化（地铁直达+公交站3个+出租车上客区）"
      },
      {
        metric: "停留时长",
        target: "90分钟",
        current_benchmark: "行业平均70分钟，优秀项目120分钟",
        spatial_strategy: "延长策略：1)增加休息座椅（每500㎡设置一个休息区，共24处）；2)丰富业态组合（零售60%+餐饮25%+娱乐15%）；3)舒适环境营造（中央空调+柔和照明+背景音乐）；4)免费设施（WIFI+充电桩+婴儿车+轮椅）"
      },
      {
        metric: "转化率（进店/成交）",
        target: "35%",
        current_benchmark: "行业平均28%，优秀项目40%",
        spatial_strategy: "转化策略：1)主力店临街布局（提升进店率）；2)次主力店分散布局（引导顾客走完全程）；3)橱窗吸引力设计（每季度更换，专业陈列）；4)导视系统优化（清晰标识+电子地图+AR导航）"
      }
    ],
    design_challenges_for_v2: [
      {
        challenge: "动线设计平衡效率与体验",
        context: "需要引导顾客走完全程（提升坪效），但不能让顾客感到疲惫（影响体验）",
        constraints: [
          "单程动线不超过300m（避免疲劳）",
          "主力店间距不超过150m（维持吸引力）",
          "每100m设置一个休息点（座椅+饮水+WIFI）"
        ],
        priority: "高"
      }
    ]
  })
};

// 测试场景5: V2-1 Comprehensive模式 - decision_rationale验证
const testScenario5 = {
  section_name: "V2-1 居住空间设计总监 - Comprehensive模式",
  content: JSON.stringify({
    output_mode: "comprehensive",
    user_question_focus: "120㎡三居室的整体设计方案",
    confidence: 0.91,
    decision_rationale: "基于家庭叙事与空间效率的综合决策：优先满足工作与家庭平衡需求，其次考虑儿童成长可变性，第三考虑储物最大化。设计理念：'家是工作与生活的平衡器'。",
    project_vision_summary: "项目愿景：打造灵活、温馨、高效的三口之家生活空间。核心价值：让每个家庭成员都能在家中找到属于自己的舒适角落，同时保持家庭互动的温暖氛围。设计目标：工作效率+家庭温馨+成长陪伴。",
    narrative_translation: "叙事转译：从'工作与家庭的平衡'转译为'日间工作模式+夜间家庭模式'的空间切换。书房白天是办公室（专注+安静），晚上是家庭图书馆（亲子阅读）。客厅白天是母亲的临时工作区，晚上是家庭活动中心（玩耍+聚会）。",
    aesthetic_framework: "美学框架：现代简约+原木温暖色调+克制的装饰。色彩：白色墙面（扩大空间感）+橡木地板（温暖质感）+灰色瓷砖（耐用易打理）+局部绿色植物（生机活力）。材质：天然木材（环保+温馨）+哑光涂料（柔和不反光）+简约五金（黄铜+黑色）。",
    functional_planning: "功能规划：1)开放式厨客餐（45㎡）-家庭互动核心，岛台分隔厨房与客厅；2)主卧套房（20㎡含卫生间5㎡）-独立卫浴+梳妆区+衣帽间；3)儿童房（12㎡）-睡眠区+玩耍区+学习区三合一；4)书房（10㎡）-双人工位+书架墙+隔音门；5)次卧（10㎡）-客房/未来书房；6)公卫（4㎡）-干湿分离；7)储物（分散式：各房间衣柜+集中式：玄关柜+阳台柜）。",
    material_palette: "材料选择：地面-橡木地板（客餐厅+卧室，温暖脚感）+灰色瓷砖（厨卫+阳台，防水耐用）；墙面-白色乳胶漆（主色调，扩大空间）+局部木饰面（电视墙+床头墙，增加温度）；顶面-白色乳胶漆（简洁）+局部吊顶（隐藏中央空调+筒灯）；五金-黄铜把手（橱柜+衣柜，轻奢质感）+黑色龙头（厨卫，现代感）。"
  })
};

// 测试场景6: V3-2 Comprehensive模式 - TouchpointScript嵌套模型
const testScenario6 = {
  section_name: "V3-2 品牌叙事与顾客体验专家 - Comprehensive模式",
  content: JSON.stringify({
    output_mode: "comprehensive",
    user_question_focus: "轻奢服装品牌的空间体验设计",
    confidence: 0.88,
    design_rationale: "基于品牌DNA的情感化空间设计",
    brand_narrative_core: "品牌叙事核心：'优雅而不张扬，品质而有温度'。品牌定位：轻奢女装（价格带800-3000元/件），目标客群28-38岁都市女性。品牌价值观：真实、自信、有品位。品牌故事：创始人留学意大利，将欧洲优雅与东方含蓄融合，打造'低调的奢华'。",
    customer_archetype: "顾客原型：Linda，32岁，外企经理，年收入40万，追求品质生活，理性消费。她欣赏有设计感的服装，但不喜欢过度张扬的logo。她重视面料和剪裁，愿意为品质支付溢价。她希望购物是一种享受，而不是压力。她需要导购的专业建议，但不喜欢过度推销。",
    emotional_journey_map: "情感旅程：好奇（橱窗吸引）→ 探索（进店浏览）→ 触动（试穿体验）→ 决策（价格权衡）→ 满足（购买成交）→ 回味（离店后的美好记忆）。关键情感节点：入口第一印象（15秒决定是否进店）、试衣间体验（30分钟核心决策）、收银结账（最后印象，影响复购）。",
    key_touchpoint_scripts: [
      {
        touchpoint_name: "入口初印象",
        emotional_goal: "让顾客感到品牌的优雅与温度，产生进店欲望",
        sensory_script: "视觉：低调奢华的橱窗（暖色灯光2700K+精致陈列+留白美学+季节性主题）；听觉：轻柔的爵士乐（低音量，不干扰交谈）；触觉：温润的黄铜把手（推门的仪式感）；嗅觉：淡淡的香氛（无花果+雪松，记忆点）"
      },
      {
        touchpoint_name: "试衣体验",
        emotional_goal: "让顾客感到被尊重和重视，增强购买信心",
        sensory_script: "视觉：宽敞的试衣间（3㎡以上，不局促）+柔和照明（接近自然光，显肤色好）+全身镜（无畸变，真实呈现）+换衣凳（坐着换鞋，舒适）；听觉：隔音良好（隐私感）+轻柔音乐（延续氛围）；触觉：柔软的地毯（赤脚舒适）+厚实的帘子（质感+隐私）；服务：导购主动询问尺码（专业+不过度推销）+提供搭配建议（增值服务）+送水或咖啡（宾至如归）"
      },
      {
        touchpoint_name: "收银结账",
        emotional_goal: "让顾客感到购买决策是正确的，留下美好回忆，促进复购",
        sensory_script: "视觉：精致的包装（品牌logo烫金+丝带系法+礼品袋质感）+收银台整洁（无杂物，专业感）；听觉：真诚的感谢（'感谢您的信任，期待下次见面'）+清晰的说明（会员权益+退换货政策）；触觉：有质感的购物袋（厚实纸袋+绳子手感好）+会员卡（金属材质，仪式感）；服务：微笑送别（送到门口，挥手告别）+小礼品（试用装香水，增加惊喜）"
      }
    ],
    narrative_guidelines_for_v2: "叙事指导：空间设计应强化'优雅+温度'的品牌调性，避免过度装饰（保持克制）。建议：1)色彩-米白+驼色+黑色（经典不过时）；2)材质-木材+黄铜+大理石（天然+轻奢）；3)照明-2700K暖光+重点照明（突出商品）；4)陈列-留白美学（每组3-5件，不拥挤）；5)休息区-沙发+茶几+杂志（让顾客愿意停留）。"
  })
};

// 测试场景7: V6-2 Comprehensive模式 - 多种嵌套模型（SystemSolution + SmartScenario）
const testScenario7 = {
  section_name: "V6-2 机电与智能化专家 - Comprehensive模式",
  content: JSON.stringify({
    output_mode: "comprehensive",
    user_question_focus: "办公楼的机电与智能化设计",
    confidence: 0.90,
    design_rationale: "绿色建筑+智慧运营的机电策略",
    mep_overall_strategy: "机电整体策略：以节能、智能、舒适为核心。采用VRV多联机空调系统（节能30%）、LED智能调光照明（节能40%）、雨水回收系统（年回收500吨）、楼宇自控系统（BAS）。目标：绿色建筑二星认证、LEED金级认证。总能耗指标：≤80kWh/㎡/年（国标≤100）。",
    system_solutions: [
      {
        system_name: "暖通空调系统",
        recommended_solution: "VRV多联机系统 + 新风热回收",
        reasoning: "适应办公灵活分隔（可独立控制），节能效果好（比传统风机盘管节能30%），初投资适中（比水系统低20%），维护简便。新风系统采用全热交换器（热回收效率70%），新风量30m³/h/人（超国标25%）。",
        energy_consumption: "预计年耗电量：120kWh/㎡（暖通占总能耗的60%）。夏季制冷COP≥3.2，冬季制热COP≥3.6。采用变频技术，部分负荷时效率更高（节能15%）。"
      },
      {
        system_name: "照明系统",
        recommended_solution: "LED智能调光系统 + 人体感应 + 光感应",
        reasoning: "配合自然采光自动调节（靠窗3m区域），无人区域自动关闭（节能20%），人体感应开启（走廊+卫生间+设备间），总节能率40%。色温可调（4000K办公+3000K会议+2700K休息）。",
        energy_consumption: "预计年耗电量：15kWh/㎡（照明占总能耗的18%）。采用高效LED灯具（光效≥120lm/W），配合智能控制系统，节能效果显著。"
      },
      {
        system_name: "给排水系统",
        recommended_solution: "市政供水 + 雨水回收 + 中水回用",
        reasoning: "市政供水稳定（压力0.35MPa，满足需求）。雨水回收用于绿化浇灌+道路冲洗（年回收500吨，节水率20%）。中水回用系统处理卫生间污水，用于冲厕（年回用800吨，节水率30%）。",
        energy_consumption: "水泵能耗：5kWh/㎡/年。采用变频泵（节能25%）+分时段供水（夜间降压，减少泄漏）。"
      }
    ],
    smart_building_scenarios: [
      {
        scenario_name: "早晨开启模式",
        description: "工作日7:00-9:00，员工陆续到达，系统提前准备舒适环境",
        triggered_systems: [
          "空调预冷（6:30启动，9:00达到25℃）",
          "照明分区开启（公共区域6:50开启，办公区域人到开启）",
          "电梯高峰模式（增加运行台数，减少等待）",
          "新风系统全开（稀释夜间积累的CO2）"
        ],
        user_experience: "员工到达时，办公区已达到舒适温度（25℃±1℃），照明柔和，空气清新，电梯等待时间<30秒。"
      },
      {
        scenario_name: "会议室预定模式",
        description: "会议开始前15分钟，系统自动准备会议环境",
        triggered_systems: [
          "会议室空调启动（提前制冷/制热）",
          "灯光开启（色温3000K，适合投影）",
          "投影设备预热（10分钟预热时间）",
          "窗帘自动关闭（避免投影反光）",
          "新风加大（人员密集，提升新风量）"
        ],
        user_experience: "进入会议室即可开始会议，无需等待设备准备，温度舒适（24℃±1℃），照明适宜，投影清晰。"
      },
      {
        scenario_name: "节能夜间模式",
        description: "工作日19:00后，大部分员工离开，系统自动切换节能模式",
        triggered_systems: [
          "空调降温设定（夏季27℃→29℃，冬季20℃→18℃）",
          "照明自动关闭（无人区域5分钟后关闭）",
          "电梯减少运行台数（保留1台应急）",
          "新风减少风量（降至最小新风量30%）",
          "安防系统启动（监控+门禁+报警）"
        ],
        user_experience: "加班员工仍可正常使用（人体感应自动开启照明+空调），但整体能耗降低50%，节能显著。"
      }
    ],
    coordination_and_clash_points: "协调要点：1.空调风管与结构梁冲突-主梁600mm高，风管400mm高，净高不足2.6m→建议局部降板200mm或调整风管走向；2.强弱电桥架与喷淋管冲突-走廊吊顶内空间紧张→调整桥架走向（贴墙）+喷淋管避让；3.机电管井面积不足-原设计6㎡/层，实际需要8㎡/层→建议扩大管井面积或分2个管井；4.屋顶设备位置-冷却塔+新风机组+光伏板→需协调设备布局，避免遮挡+维修通道预留。",
    sustainability_and_energy_saving: "可持续策略：1.屋顶光伏系统（100kWp，年发电12万kWh，满足20%用电）；2.雨水回收系统（屋面+地面，年回收500吨，节水20%）；3.中水回用系统（年回用800吨，节水30%）；4.绿色建筑二星认证（节能、节水、节地、节材、室内环境）；5.LEED金级认证（能源、水资源、材料、室内环境质量）。预计总节能率：40%（比常规建筑），年节省运营成本：50万元。"
  })
};

const allScenarios = [
  testScenario1,
  testScenario2,
  testScenario3,
  testScenario4,
  testScenario5,
  testScenario6,
  testScenario7
];

export default function TestFlexibleOutputPage() {
  const [selectedScenario, setSelectedScenario] = useState(0);

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 to-gray-800 p-8">
      <div className="max-w-7xl mx-auto">
        {/* 页头 */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">
            Phase 4 任务5 - 灵活输出架构端到端测试
          </h1>
          <p className="text-gray-400">
            测试目标：验证130+字段映射、Targeted模式UI、13个嵌套模型样式
          </p>
        </div>

        {/* 场景选择器 */}
        <div className="bg-gray-800 rounded-lg p-6 mb-8 border border-gray-700">
          <h2 className="text-xl font-semibold text-white mb-4">选择测试场景</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {allScenarios.map((scenario, index) => (
              <button
                key={index}
                onClick={() => setSelectedScenario(index)}
                className={`p-4 rounded-lg border-2 transition-all ${
                  selectedScenario === index
                    ? 'border-blue-500 bg-blue-500/10'
                    : 'border-gray-600 bg-gray-700/50 hover:border-gray-500'
                }`}
              >
                <div className="text-left">
                  <div className="text-sm font-semibold text-blue-400 mb-1">
                    场景 {index + 1}
                  </div>
                  <div className="text-xs text-gray-300">
                    {scenario.section_name}
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* 测试验证清单 */}
        <div className="bg-gray-800 rounded-lg p-6 mb-8 border border-gray-700">
          <h2 className="text-xl font-semibold text-white mb-4">验证清单</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <h3 className="text-blue-400 font-medium mb-2">场景 1-2 (V6-1)</h3>
              <ul className="space-y-1 text-gray-400">
                <li>□ Targeted模式蓝色高亮</li>
                <li>□ KeyNodeAnalysis嵌套模型</li>
                <li>□ 字段中文映射正确</li>
              </ul>
            </div>
            <div>
              <h3 className="text-blue-400 font-medium mb-2">场景 3 (V5-1)</h3>
              <ul className="space-y-1 text-gray-400">
                <li>□ FamilyMemberProfile绿色卡片</li>
                <li>□ DesignChallenge橙色卡片</li>
                <li>□ 双栏布局正确</li>
              </ul>
            </div>
            <div>
              <h3 className="text-blue-400 font-medium mb-2">场景 4 (V5-2)</h3>
              <ul className="space-y-1 text-gray-400">
                <li>□ RetailKPI蓝色卡片</li>
                <li>□ 数字高亮显示</li>
                <li>□ 空间策略层级清晰</li>
              </ul>
            </div>
            <div>
              <h3 className="text-blue-400 font-medium mb-2">场景 5 (V2-1)</h3>
              <ul className="space-y-1 text-gray-400">
                <li>□ decision_rationale显示为"决策依据"</li>
                <li>□ V2特殊命名正确</li>
              </ul>
            </div>
            <div>
              <h3 className="text-blue-400 font-medium mb-2">场景 6 (V3-2)</h3>
              <ul className="space-y-1 text-gray-400">
                <li>□ TouchpointScript紫色卡片</li>
                <li>□ ✨图标显示</li>
                <li>□ 三层信息清晰</li>
              </ul>
            </div>
            <div>
              <h3 className="text-blue-400 font-medium mb-2">场景 7 (V6-2)</h3>
              <ul className="space-y-1 text-gray-400">
                <li>□ SystemSolution蓝绿卡片</li>
                <li>□ SmartScenario紫罗兰卡片</li>
                <li>□ 标签云显示正确</li>
              </ul>
            </div>
          </div>
        </div>

        {/* 报告卡片渲染 */}
        <div className="bg-gray-800 rounded-lg border border-gray-700">
          <ReportSectionCard
            section={{
              section_name: allScenarios[selectedScenario].section_name,
              content: allScenarios[selectedScenario].content,
              confidence: 0.9,
              role_id: `test-scenario-${selectedScenario + 1}`
            }}
          />
        </div>
      </div>
    </div>
  );
}
