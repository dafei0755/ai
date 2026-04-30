# Phase 4 任务5 - 端到端测试计划

**日期**: 2025-12-05
**版本**: v1.0-test-ready
**状态**: 📋 测试准备中

---

## 一、测试目标

### 1.1 核心验证目标

✅ **字段映射正确性**: 130+字段的中文显示正确
✅ **Targeted模式UI**: 蓝色高亮显示，视觉差异化明显
✅ **Comprehensive模式UI**: 层级清晰，嵌套模型美化
✅ **13个嵌套模型**: 每个模型独特样式正确渲染
✅ **响应式设计**: 移动端/桌面端自适应
✅ **性能表现**: 渲染速度流畅，无卡顿

---

## 二、测试场景设计

### 测试场景1: V6-1 Targeted模式 - 结构体系选择

**场景描述**: 用户询问"如何选择结构体系？"，V6-1返回Targeted模式响应

**预期数据结构**:
```json
{
  "output_mode": "targeted",
  "user_question_focus": "如何选择结构体系？",
  "confidence": 0.88,
  "design_rationale": "基于项目类型和规模的结构体系比选",
  "targeted_analysis": {
    "structural_system_comparison": {
      "recommended_system": "框架-剪力墙体系",
      "reasoning": "综合考虑建筑高度（80m）、抗震设防烈度（8度）、大跨度空间需求",
      "key_advantages": [
        "适应不规则平面布局",
        "满足大跨度空间（18m×24m展厅）",
        "抗震性能优越",
        "施工周期可控（16个月）"
      ],
      "alternative_option": {
        "system": "纯框架体系",
        "trade_off": "经济性更优但抗震性能略差，不推荐"
      }
    }
  }
}
```

**UI验证点**:
1. ✅ `targeted_analysis` 显示为蓝色高亮区域
2. ✅ 左侧有4px蓝色竖线
3. ✅ 标题"针对性分析"显示正确
4. ✅ 圆形勾选图标显示
5. ✅ 内容缩进清晰
6. ✅ 与其他字段有明显垂直间距

---

### 测试场景2: V6-1 Comprehensive模式 - 完整技术方案

**场景描述**: 用户要求完整的结构与幕墙分析，V6-1返回Comprehensive模式

**预期数据结构**:
```json
{
  "output_mode": "comprehensive",
  "user_question_focus": "完整的结构与幕墙技术方案",
  "confidence": 0.92,
  "design_rationale": "系统性技术可行性分析",
  "feasibility_assessment": "项目可行性评估：总体可行，需重点关注地基处理和大跨度结构...",
  "structural_system_options": "结构体系选项：方案A（框架-剪力墙）推荐，方案B（纯框架）备选...",
  "facade_system_options": "幕墙体系选项：单元式玻璃幕墙+铝板幕墙组合...",
  "key_technical_nodes": [
    {
      "node_name": "展厅大跨度结构",
      "challenge": "18m×24m无柱大空间，荷载传递路径复杂",
      "proposed_solution": "预应力钢桁架+型钢混凝土柱，跨度24m采用双向桁架",
      "coordination_requirements": "需与机电专业协调预留设备吊装口"
    },
    {
      "node_name": "玻璃幕墙抗震",
      "challenge": "8度抗震区，层间位移角1/800，幕墙变形适应性",
      "proposed_solution": "浮动连接+双道密封，预留±50mm变形量",
      "coordination_requirements": "与结构专业确认层间位移计算值"
    }
  ],
  "risk_analysis_and_recommendations": "风险分析：1. 地基承载力不足风险-建议桩基础；2. 幕墙施工精度风险-建议1:1样板段..."
}
```

**UI验证点**:
1. ✅ `feasibility_assessment` 显示为"可行性评估"
2. ✅ `structural_system_options` 显示为"结构体系选项"
3. ✅ `facade_system_options` 显示为"幕墙体系选项"
4. ✅ `key_technical_nodes` 数组渲染为KeyNodeAnalysis嵌套模型卡片
5. ✅ 每个嵌套模型有靛蓝色边框 + 对比布局
6. ✅ `risk_analysis_and_recommendations` 显示为"风险分析与建议"
7. ✅ 层级缩进清晰，标题加粗
8. ✅ design_rationale（注意不是decision_rationale）正确显示

---

### 测试场景3: V5-1 Comprehensive模式 - 家庭画像与嵌套模型

**场景描述**: 居住场景专家分析三口之家的空间需求

**预期数据结构**:
```json
{
  "output_mode": "comprehensive",
  "user_question_focus": "三口之家的居住空间设计",
  "confidence": 0.90,
  "design_rationale": "基于家庭成员画像的空间需求分析",
  "family_profile_and_needs": "家庭画像：夫妻+6岁女儿，双职工家庭，重视教育和生活品质...",
  "lifestyle_deconstruction": "生活方式拆解：工作日快节奏，周末家庭时光，重视亲子互动...",
  "spatial_requirements": "空间需求：主卧套房、儿童房、书房、开放式厨客餐一体...",
  "family_member_profiles": [
    {
      "member": "父亲（35岁，IT工程师）",
      "daily_routine": "早7:00出门，晚19:00回家，周末居家办公",
      "spatial_needs": [
        "独立书房（远程办公+游戏）",
        "储物空间（电子设备+手办）",
        "健身空间（瑜伽垫+哑铃）"
      ],
      "storage_needs": [
        "电子设备柜（笔记本+显示器+配件）",
        "衣物收纳（商务装+休闲装）",
        "书籍收纳（技术书+小说）"
      ],
      "privacy_level": "高（需要独立安静空间）"
    },
    {
      "member": "母亲（33岁，市场总监）",
      "daily_routine": "早8:00出门，晚18:30回家，偶尔带工作回家",
      "spatial_needs": [
        "梳妆区（化妆+护肤）",
        "衣帽间（服装+包包+鞋）",
        "会客空间（偶尔家庭聚会）"
      ],
      "storage_needs": [
        "化妆品收纳（分类+展示）",
        "服装收纳（挂放+叠放+鞋柜）",
        "箱包收纳（手袋+行李箱）"
      ],
      "privacy_level": "中（需要个人空间但也享受家庭互动）"
    },
    {
      "member": "女儿（6岁，幼儿园大班）",
      "daily_routine": "早8:00上学，晚17:00放学，周末兴趣班+家庭活动",
      "spatial_needs": [
        "儿童房（睡眠+玩耍+学习）",
        "玩具区（乐高+娃娃+绘本）",
        "学习区（写字台+书架）"
      ],
      "storage_needs": [
        "玩具收纳（分类整理，易于取放）",
        "衣物收纳（儿童衣柜+鞋柜）",
        "文具书籍收纳（绘本+学习用品）"
      ],
      "privacy_level": "低（需要父母陪伴和监护）"
    }
  ],
  "design_challenges_for_v2": [
    {
      "challenge": "平衡工作与家庭空间",
      "context": "父母都需要居家办公空间，但房屋面积有限（120㎡）",
      "constraints": [
        "书房与主卧相邻，需隔音",
        "客厅需兼顾办公功能",
        "儿童活动不能影响父母工作"
      ],
      "priority": "高"
    },
    {
      "challenge": "儿童成长空间的可变性",
      "context": "孩子6岁，未来10年空间需求会变化",
      "constraints": [
        "儿童房需支持睡眠、玩耍、学习三种功能",
        "家具需可调整（床、桌椅高度）",
        "玩具收纳需灵活（从大型玩具到文具）"
      ],
      "priority": "中"
    }
  ]
}
```

**UI验证点**:
1. ✅ `family_profile_and_needs` 显示为"家庭画像与需求"
2. ✅ `family_member_profiles` 数组渲染为FamilyMemberProfile嵌套模型
3. ✅ 每个成员卡片有绿色边框 + 👤图标
4. ✅ 双栏布局："空间需求" | "储物需求"
5. ✅ 成员名称（父亲/母亲/女儿）显示为卡片标题
6. ✅ `daily_routine` 显示为灰色文本
7. ✅ `design_challenges_for_v2` 数组渲染为DesignChallenge嵌套模型
8. ✅ 每个挑战卡片有橙色边框 + ⚠️图标
9. ✅ `priority` 字段显示为"优先级"并带颜色标识

---

### 测试场景4: V5-2 Comprehensive模式 - 零售KPI嵌套模型

**场景描述**: 商业零售专家分析商场的运营指标

**预期数据结构**:
```json
{
  "output_mode": "comprehensive",
  "user_question_focus": "购物中心的空间设计如何支撑运营目标",
  "confidence": 0.89,
  "design_rationale": "基于零售KPI的空间策略设计",
  "business_goal_analysis": "商业目标分析：年坪效4万元/㎡，客流量300万人次/年，停留时长90分钟...",
  "customer_journey": "顾客旅程：停车→入口→中庭→主力店→餐饮→离开，平均动线600m...",
  "operational_efficiency": "运营效率：货物动线与顾客动线分离，后勤通道占比12%...",
  "key_performance_indicators": [
    {
      "metric": "坪效（年销售额/营业面积）",
      "target": "4.0万元/㎡/年",
      "current_benchmark": "行业平均3.2万元/㎡/年",
      "spatial_strategy": "提升策略：增加体验业态（餐饮+娱乐）占比至40%，优化动线提升可见性"
    },
    {
      "metric": "客流量（日均）",
      "target": "8,000人次/日",
      "current_benchmark": "周边商场6,500人次/日",
      "spatial_strategy": "吸引策略：打造中庭景观+定期活动，设置打卡点，优化入口可达性"
    },
    {
      "metric": "停留时长",
      "target": "90分钟",
      "current_benchmark": "行业平均70分钟",
      "spatial_strategy": "延长策略：增加休息座椅（每500㎡一个休息区），丰富业态组合"
    },
    {
      "metric": "转化率（进店/成交）",
      "target": "35%",
      "current_benchmark": "行业平均28%",
      "spatial_strategy": "转化策略：主力店临街布局，次主力店分散布局引导动线"
    }
  ],
  "design_challenges_for_v2": [
    {
      "challenge": "动线设计平衡效率与体验",
      "context": "需要引导顾客走完全程，但不能让顾客感到疲惫",
      "constraints": [
        "单程动线不超过300m",
        "主力店间距不超过150m",
        "每100m设置一个休息点"
      ],
      "priority": "高"
    }
  ]
}
```

**UI验证点**:
1. ✅ `business_goal_analysis` 显示为"商业目标分析"
2. ✅ `key_performance_indicators` 数组渲染为RetailKPI嵌套模型
3. ✅ 每个KPI卡片有蓝色边框 + 📊图标
4. ✅ `metric` 显示为大标题
5. ✅ `target` 数字高亮显示（大号字体）
6. ✅ `current_benchmark` 显示为对比基准
7. ✅ `spatial_strategy` 显示为"空间策略"并有缩进
8. ✅ 数字格式正确（带千分位逗号）

---

### 测试场景5: V2-1 Comprehensive模式 - decision_rationale字段

**场景描述**: 居住空间设计总监的完整设计方案

**预期数据结构**:
```json
{
  "output_mode": "comprehensive",
  "user_question_focus": "120㎡三居室的整体设计方案",
  "confidence": 0.91,
  "decision_rationale": "基于家庭叙事与空间效率的综合决策",
  "project_vision_summary": "项目愿景：打造灵活、温馨、高效的三口之家生活空间...",
  "narrative_translation": "叙事转译：从'工作与家庭的平衡'转译为'日间工作模式+夜间家庭模式'的空间切换...",
  "aesthetic_framework": "美学框架：现代简约+原木温暖色调+克制的装饰...",
  "functional_planning": "功能规划：开放式厨客餐（45㎡）、主卧套房（20㎡）、儿童房（12㎡）、书房（10㎡）...",
  "material_palette": "材料选择：橡木地板+白色墙面+灰色瓷砖+黄铜五金..."
}
```

**UI验证点**:
1. ✅ **关键**: `decision_rationale` 显示为"决策依据"（而非"设计原理"）
2. ✅ V2系列特殊命名正确映射
3. ✅ `project_vision_summary` 显示为"项目愿景摘要"
4. ✅ `narrative_translation` 显示为"叙事转译"
5. ✅ 所有字段层级清晰，标题加粗

---

### 测试场景6: V3-2 Comprehensive模式 - TouchpointScript嵌套模型

**场景描述**: 品牌叙事专家分析轻奢品牌店铺的顾客体验

**预期数据结构**:
```json
{
  "output_mode": "comprehensive",
  "user_question_focus": "轻奢服装品牌的空间体验设计",
  "confidence": 0.88,
  "design_rationale": "基于品牌DNA的情感化空间设计",
  "brand_narrative_core": "品牌叙事核心：'优雅而不张扬，品质而有温度'...",
  "customer_archetype": "顾客原型：28-38岁都市女性，追求品质生活，理性消费...",
  "emotional_journey_map": "情感旅程：好奇→探索→触动→决策→满足→回味...",
  "key_touchpoint_scripts": [
    {
      "touchpoint_name": "入口初印象",
      "emotional_goal": "让顾客感到品牌的优雅与温度，产生进店欲望",
      "sensory_script": "视觉：低调奢华的橱窗（暖色灯光+精致陈列）；听觉：轻柔的爵士乐；触觉：温润的黄铜把手"
    },
    {
      "touchpoint_name": "试衣体验",
      "emotional_goal": "让顾客感到被尊重和重视，增强购买信心",
      "sensory_script": "视觉：宽敞的试衣间（3㎡以上）+柔和照明+全身镜；嗅觉：淡淡的香氛；服务：导购主动询问尺码，不过度推销"
    },
    {
      "touchpoint_name": "收银结账",
      "emotional_goal": "让顾客感到购买决策是正确的，留下美好回忆",
      "sensory_script": "视觉：精致的包装（品牌logo烫金+丝带）；听觉：真诚的感谢；触觉：有质感的购物袋"
    }
  ],
  "narrative_guidelines_for_v2": "叙事指导：空间设计应强化'优雅+温度'的品牌调性，避免过度装饰..."
}
```

**UI验证点**:
1. ✅ `brand_narrative_core` 显示为"品牌叙事核心"
2. ✅ `customer_archetype` 显示为"顾客原型"
3. ✅ `key_touchpoint_scripts` 数组渲染为TouchpointScript嵌套模型
4. ✅ 每个触点卡片有紫色边框 + ✨图标
5. ✅ `touchpoint_name` 显示为标题
6. ✅ `emotional_goal` 有"情感目标："前缀
7. ✅ `sensory_script` 有"感官脚本："前缀
8. ✅ 三层信息层级清晰

---

### 测试场景7: V6-2 Comprehensive模式 - 多种嵌套模型混合

**场景描述**: 机电智能化专家提供系统方案和智慧场景

**预期数据结构**:
```json
{
  "output_mode": "comprehensive",
  "user_question_focus": "办公楼的机电与智能化设计",
  "confidence": 0.90,
  "design_rationale": "绿色建筑+智慧运营的机电策略",
  "mep_overall_strategy": "机电整体策略：采用VRV空调+LED照明+雨水回收+楼宇自控...",
  "system_solutions": [
    {
      "system_name": "暖通空调系统",
      "recommended_solution": "VRV多联机系统 + 新风热回收",
      "reasoning": "适应办公灵活分隔，节能效果好（比传统风机盘管节能30%），初投资适中",
      "energy_consumption": "预计年耗电量：120kWh/㎡"
    },
    {
      "system_name": "照明系统",
      "recommended_solution": "LED智能调光系统 + 人体感应",
      "reasoning": "配合自然采光自动调节，无人区域自动关闭，节能率40%",
      "energy_consumption": "预计年耗电量：15kWh/㎡"
    }
  ],
  "smart_building_scenarios": [
    {
      "scenario_name": "早晨开启模式",
      "description": "7:00-9:00，员工陆续到达",
      "triggered_systems": ["空调预冷", "照明分区开启", "电梯高峰模式"],
      "user_experience": "员工到达时，办公区已达到舒适温度（25℃）"
    },
    {
      "scenario_name": "会议室预定模式",
      "description": "会议开始前15分钟",
      "triggered_systems": ["会议室空调启动", "灯光开启", "投影设备预热", "窗帘自动关闭"],
      "user_experience": "进入会议室即可开始会议，无需等待设备"
    }
  ],
  "coordination_and_clash_points": "协调要点：1. 空调风管与结构梁冲突→建议降板200mm；2. 强弱电桥架与喷淋冲突→调整桥架走向...",
  "sustainability_and_energy_saving": "可持续策略：屋顶光伏（100kWp）、雨水回收（年回收500吨）、绿色建筑二星..."
}
```

**UI验证点**:
1. ✅ `system_solutions` 数组渲染为SystemSolution嵌套模型
2. ✅ 每个系统卡片有蓝绿色边框 + ⚙️图标
3. ✅ `system_name` 显示为标题
4. ✅ `reasoning` 有明确的视觉层级
5. ✅ `smart_building_scenarios` 数组渲染为SmartScenario嵌套模型
6. ✅ 每个场景卡片有紫罗兰边框 + 🤖图标
7. ✅ `triggered_systems` 显示为标签云（横向排列）
8. ✅ 两种嵌套模型样式差异明显

---

## 三、验证清单

### 3.1 字段映射验证（130+字段）

**V6工程师系列**:
- [ ] feasibility_assessment → 可行性评估
- [ ] structural_system_options → 结构体系选项
- [ ] facade_system_options → 幕墙体系选项
- [ ] key_technical_nodes → 关键技术节点
- [ ] mep_overall_strategy → 机电整体策略
- [ ] system_solutions → 系统方案
- [ ] smart_building_scenarios → 智慧建筑场景
- [ ] craftsmanship_strategy → 工艺策略
- [ ] key_material_specifications → 关键材料规格
- [ ] cost_estimation_summary → 成本估算摘要
- [ ] value_engineering_options → 价值工程选项

**V5场景专家系列**:
- [ ] scenario_deconstruction → 场景拆解
- [ ] operational_logic → 运营逻辑
- [ ] family_profile_and_needs → 家庭画像与需求
- [ ] business_goal_analysis → 商业目标分析
- [ ] key_performance_indicators → 关键绩效指标

**V2设计总监系列**:
- [ ] decision_rationale → 决策依据（仅V2系列）
- [ ] design_rationale → 设计原理（V3-V6系列）
- [ ] master_plan_strategy → 总体规划策略
- [ ] project_vision_summary → 项目愿景摘要
- [ ] narrative_translation → 叙事转译

**V3叙事专家系列**:
- [ ] individual_narrative_core → 个体叙事核心
- [ ] brand_narrative_core → 品牌叙事核心
- [ ] spatial_narrative_concept → 空间叙事概念
- [ ] customer_archetype → 顾客原型
- [ ] emotional_journey_map → 情感旅程地图

**V4研究者系列**:
- [ ] research_focus → 研究焦点
- [ ] methodology → 研究方法
- [ ] key_findings → 核心发现
- [ ] trend_analysis → 趋势分析

### 3.2 嵌套模型验证（13个模型）

- [ ] **TouchpointScript**: 紫色 + ✨图标 + 三层信息
- [ ] **FamilyMemberProfile**: 绿色 + 👤图标 + 双栏布局
- [ ] **RetailKPI**: 蓝色 + 📊图标 + 数字高亮
- [ ] **DesignChallenge**: 橙色 + ⚠️图标 + 优先级标识
- [ ] **SubprojectBrief**: 青色 + 面积标签 + 优先级颜色
- [ ] **TechnicalOption**: 靛蓝 + 优劣对比
- [ ] **KeyNodeAnalysis**: 靛蓝 + 挑战/方案对比
- [ ] **SystemSolution**: 蓝绿 + ⚙️图标 + 推荐方案高亮
- [ ] **SmartScenario**: 紫罗兰 + 🤖图标 + 标签云
- [ ] **MaterialSpec**: 琥珀色 + 规格列表
- [ ] **NodeDetail**: 靛蓝 + 节点详情
- [ ] **CostBreakdown**: 翠绿 + 百分比大号显示
- [ ] **VEOption**: 黄绿 + 对比网格

### 3.3 UI特性验证

**Targeted模式特殊渲染**:
- [ ] 蓝色半透明背景（bg-blue-500/10）
- [ ] 4px蓝色左侧竖线（border-l-4 border-blue-500）
- [ ] 圆形勾选SVG图标
- [ ] "针对性分析"标题（text-base font-semibold text-blue-400）
- [ ] 垂直间距明显（my-4）
- [ ] 与普通字段视觉差异明显

**Comprehensive模式层级展示**:
- [ ] 字段标题加粗（font-medium text-blue-400）
- [ ] 内容缩进（pl-2）
- [ ] 字段间距清晰（space-y-4）
- [ ] 嵌套对象递归渲染正确

**响应式设计**:
- [ ] 桌面端（>768px）：完整布局
- [ ] 平板端（768px-1024px）：自适应布局
- [ ] 移动端（<768px）：单列布局，图标适配

### 3.4 性能验证

- [ ] 渲染速度流畅（<100ms初始渲染）
- [ ] 滚动无卡顿
- [ ] 大量嵌套数据（100+字段）无性能问题
- [ ] 章节折叠/展开响应迅速

---

## 四、测试执行步骤

### 4.1 准备阶段

1. **创建测试数据文件**（已在本文档中提供）
2. **启动前端开发服务器**: `npm run dev`
3. **打开浏览器开发者工具**: F12 → Console + Elements
4. **准备截图工具**: 用于记录测试结果

### 4.2 执行阶段

**方法A: 模拟后端响应（推荐）**
- 在`ReportSectionCard.tsx`中临时添加测试数据
- 或创建测试页面直接渲染测试数据
- 验证UI渲染正确性

**方法B: 实际后端测试**
- 运行完整后端服务
- 发起真实请求
- 验证完整数据流

### 4.3 验证阶段

对每个测试场景：
1. ✅ 视觉检查：样式、颜色、图标
2. ✅ 文本检查：中文映射正确性
3. ✅ 交互检查：折叠/展开功能
4. ✅ 响应式检查：不同屏幕尺寸
5. ✅ 性能检查：渲染时间
6. ✅ 截图记录：保存验证结果

### 4.4 问题记录

发现问题时记录：
- **问题描述**: 具体现象
- **复现步骤**: 如何触发
- **预期表现**: 应该如何
- **实际表现**: 当前如何
- **优先级**: 高/中/低
- **修复建议**: 可能的解决方案

---

## 五、成功标准

### 5.1 核心标准（必须100%通过）

✅ **字段映射正确率**: 130+字段 100%正确显示中文
✅ **嵌套模型识别率**: 13个模型 100%正确识别
✅ **Targeted模式区分度**: 明显的蓝色高亮，与普通字段可区分
✅ **Comprehensive模式清晰度**: 层级清晰，易于阅读
✅ **响应式兼容性**: 移动端/桌面端都能正常显示

### 5.2 质量标准（优秀标准）

✅ **视觉一致性**: 配色、间距、字体统一
✅ **性能表现**: 渲染<100ms，滚动流畅
✅ **用户体验**: 直观、美观、专业
✅ **代码质量**: 无TypeScript错误，无控制台警告

---

## 六、测试数据文件

测试数据已整合在本文档的"二、测试场景设计"部分，共7个完整场景，涵盖：
- ✅ V6-1 Targeted + Comprehensive
- ✅ V5-1 Comprehensive（FamilyMemberProfile + DesignChallenge）
- ✅ V5-2 Comprehensive（RetailKPI）
- ✅ V2-1 Comprehensive（decision_rationale验证）
- ✅ V3-2 Comprehensive（TouchpointScript）
- ✅ V6-2 Comprehensive（SystemSolution + SmartScenario）

---

## 七、预期测试时间

| 阶段 | 时间 | 说明 |\n|-----|------|------|\n| 准备阶段 | 15分钟 | 创建测试页面/数据注入 |\n| 场景1-3测试 | 30分钟 | 核心场景验证 |\n| 场景4-7测试 | 30分钟 | 扩展场景验证 |\n| 响应式测试 | 15分钟 | 不同设备测试 |\n| 问题修复 | 可变 | 根据发现的问题 |\n| **总计** | **约1.5小时** | **（无重大问题时）** |\n\n---

**文档版本**: v1.0-test-ready
**创建时间**: 2025-12-05
**下次更新**: 测试执行完成后
