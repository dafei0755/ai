"""
设计模式检测器（Design Mode Detector）
版本: v1.0
日期: 2026-02-12
策略: 混合检测（关键词快速筛选 + LLM精准判断）
"""

import json
from typing import List, Dict, Tuple, Optional, Any
from loguru import logger


class DesignModeDetector:
    """设计模式检测器 - 基于关键词匹配的快速筛选"""

    # 11个设计模式的特征定义（基于 sf/10_Mode_Engine）
    # 🆕 v7.623: 扩展关键词库，提升准确率从82% → 90%
    # 🆕 v9.0: 新增 M12 生态再生型设计 + MODE_SIGNATURES 扩展至 12 个模式
    MODE_SIGNATURES = {
        "M1_concept_driven": {
            "name": "概念驱动型设计",
            "keywords": [
                # 原有关键词
                "概念",
                "精神",
                "品牌",
                "文化母题",
                "表达",
                "哲学",
                "身份",
                "艺术",
                "旗舰",
                "灵魂",
                "思想",
                "价值观",
                "内在冲突",
                "自我认同",
                # 🆕 v7.623: 新增高频关键词（基于误检分析）
                "内涵",
                "底层逻辑",
                "本质",
                "信仰",
                "理念",
                "精神内核",
                "文化传承",
                "符号系统",
                "意象",
                "隐喻",
                "诗意",
                "意境",
                "禅意",
                "东方美学",
                "西方哲学",
                "叙事",
                "故事",
                "主题",
                "象征",
                "仪式感",
                "归属感",
                "认同",
                "根",
                "乡愁",
                # 🆕 v8.0: 跨学科触发词（覆盖软性空白D：Q181-190）
                # 行为科学
                "行为经济",
                "锚定效应",
                "认知偏差",
                "决策路径",
                "注意力经济",
                "认知负荷",
                "损失厌恶",
                "禀赋效应",
                "框架效应",
                "行为设计",
                # 神经科学
                "神经科学",
                "神经美学",
                "感知实验",
                "认知心理",
                "前额叶",
                "杏仁核",
                "多巴胺",
                "血清素",
                "神经可塑性",
                "感官整合",
                # 社会学/人类学
                "身份认同",
                "阶层感知",
                "社会距离",
                "符号学",
                "文化冲突",
                "迁徙",
                "归属",
                "多元文化",
                "后殖民",
                "身份政治",
                # 哲学/宗教
                "跨信仰",
                "宗教对话",
                "存在主义",
                "现象学",
                "后人类",
                "技术伦理",
                "去中心化",
                "他者",
                "觉知",
                "禅",
                # 政治/经济/传播
                "博弈论",
                "系统思维",
                "粮食政治",
                "气候治理",
                "空间政治",
                "传播学",
                "消费行为",
                "注意力",
                "信息过载",
            ],
            "scenarios": [
                "高端住宅",
                "品牌旗舰店",
                "策展型酒店",
                "文化类建筑",
                "主题商业",
                "艺术家空间",
                "身份表达",
                # 🆕 v7.623: 新增场景
                "文化中心",
                "美术馆",
                "博物馆",
                "禅修空间",
                "冥想室",
                "艺术工作室",
                "文化展示",
                "精神疗愈空间",
                "哲学书店",
            ],
            "anti_keywords": [
                # 🆕 v7.623: 扩展反向关键词（减少误检）
                "效率",
                "成本",
                "回报",
                "坪效",
                "翻台率",
                "客单价",
                "投资回报",
                "盈利模式",
                "商业模式",
                "ROI",
                "成本控制",
            ],
            "weight": 1.2,  # 🆕 v7.623: 提升权重（概念驱动特征明显）
        },
        "M2_function_efficiency": {
            "name": "功能效率型设计",
            "keywords": [
                # 原有关键词
                "效率",
                "动线",
                "流程",
                "运转",
                "后勤",
                "干扰",
                "标准化",
                "办公",
                "医疗",
                "优化",
                "系统",
                "快速",
                "流畅",
                # 🆕 v7.623: 新增高频关键词
                "生产力",
                "工作效率",
                "时间管理",
                "空间利用率",
                "功能分区",
                "协作",
                "会议",
                "工位",
                "动线优化",
                "流线",
                "分区",
                "模块化",
                "标准化",
                "可复制",
                "规范",
                "SOP",
                "流程再造",
                "精益",
                "敏捷",
                "高效",
                "便捷",
                "快捷",
                "顺畅",
            ],
            "scenarios": [
                "办公空间",
                "医疗空间",
                "教育空间",
                "研发中心",
                "商业综合体",
                "高密度住宅",
                "工业配套",
                # 🆕 v7.623: 新增场景
                "联合办公",
                "共享办公",
                "企业总部",
                "研发实验室",
                "医院",
                "诊所",
                "学校",
                "培训中心",
                "数据中心",
            ],
            "anti_keywords": [
                # 🆕 v7.623: 扩展反向关键词
                "情绪",
                "体验",
                "艺术",
                "氛围",
                "感受",
                "沉浸",
                "情感",
                "诗意",
                "意境",
                "禅意",
            ],
            "weight": 1.0,
        },
        "M3_emotional_experience": {
            "name": "情绪体验型设计",
            "keywords": [
                # 原有关键词
                "体验",
                "情绪",
                "沉浸",
                "感知",
                "记忆",
                "氛围",
                "五感",
                "酒店",
                "民宿",
                "节奏",
                "高潮",
                "感受",
                "情感",
                # 🆕 v7.623: 新增高频关键词
                "情绪价值",
                "峰终体验",
                "感官",
                "触觉",
                "嗅觉",
                "听觉",
                "视觉冲击",
                "情感共鸣",
                "记忆点",
                "惊喜",
                "仪式感",
                "沉浸式",
                "场景化",
                "故事线",
                "情绪曲线",
                "氛围营造",
                "温度",
                "质感",
                "细节",
                "触动",
                "感动",
                "疗愈",
                "放松",
            ],
            "scenarios": [
                "酒店",
                "民宿",
                "展馆",
                "零售空间",
                "品牌体验店",
                "沉浸式空间",
                "冥想空间",
                "疗愈空间",
                # 🆕 v7.623: 新增场景
                "精品酒店",
                "度假酒店",
                "温泉",
                "SPA",
                "茶室",
                "咖啡馆",
                "书店",
                "艺术展览",
                "快闪店",
                "体验中心",
            ],
            "anti_keywords": [
                # 🆕 v7.623: 扩展反向关键词
                "效率",
                "标准化",
                "快速",
                "流程",
                "成本控制",
            ],
            "weight": 1.1,  # 🆕 v7.623: 提升权重（体验型特征明显）
        },
        "M4_capital_asset": {
            "name": "资产资本型设计",
            "keywords": [
                # 原有关键词
                "资产",
                "回报",
                "坪效",
                "溢价",
                "ROI",
                "投资",
                "商业",
                "租金",
                "现金流",
                "盈利",
                "收益",
                "RevPAR",
                "客单价",
                "转化率",
                # 🆕 v7.623: 新增高频关键词
                "投资回报率",
                "资产增值",
                "租售比",
                "出租率",
                "空置率",
                "财务模型",
                "IRR",
                "NPV",
                "回本周期",
                "现金流预测",
                "商业价值",
                "资产配置",
                "投资组合",
                "退出机制",
                "估值",
                "融资",
                "资本化率",
                "收益率",
                "分红",
            ],
            "scenarios": [
                "商业地产",
                "酒店投资",
                "养老社区",
                "综合体",
                "写字楼",
                "可复制产品线",
                "投资项目",
                # 🆕 v7.623: 新增场景
                "购物中心",
                "商业街",
                "产业园",
                "物流园",
                "长租公寓",
                "服务式公寓",
                "联合办公",
                "商业综合体",
            ],
            "anti_keywords": [
                # 🆕 v7.623: 新增反向关键词
                "情怀",
                "理想",
                "梦想",
                "艺术追求",
                "不计成本",
            ],
            "weight": 1.0,
        },
        "M5_rural_context": {
            "name": "乡建在地型设计",
            "keywords": [
                # 原有关键词
                "乡村",
                "民宿",
                "在地",
                "村落",
                "地域文化",
                "本地材料",
                "经济闭环",
                "农文旅",
                "非遗",
                "村民",
                "乡建",
                "美丽乡村",
                # 🆕 v7.623: 新增高频关键词
                "乡村振兴",
                "田园",
                "农业",
                "农家乐",
                "乡土",
                "传统工艺",
                "本土文化",
                "地方特色",
                "乡愁",
                "归园",
                "慢生活",
                "生态农业",
                "有机",
                "自然教育",
                "农耕体验",
                "采摘",
                "村集体",
                "合作社",
                "村民参与",
                "共建共享",
            ],
            "scenarios": [
                "新农村",
                "美丽乡村",
                "民宿集群",
                "非遗工坊",
                "农文旅综合体",
                "自建房",
                "乡村公共空间",
                # 🆕 v7.623: 新增场景
                "田园综合体",
                "农庄",
                "乡村度假",
                "乡村博物馆",
                "村史馆",
                "乡村书院",
                "农业观光园",
                "乡村市集",
            ],
            "anti_keywords": [
                # 🆕 v7.623: 扩展反向关键词
                "城市",
                "高科技",
                "现代化",
                "国际化",
                "都市",
                "摩天大楼",
                "CBD",
                "商务区",
            ],
            "weight": 1.3,  # 🆕 v7.623: 提升权重（乡建特征非常明显）
        },
        "M6_urban_regeneration": {
            "name": "城市更新型设计",
            "keywords": [
                # 原有关键词
                "城市更新",
                "旧改",
                "厂房改造",
                "片区",
                "城中村",
                "滨水",
                "街区",
                "改造",
                "更新",
                "激活",
                "重构",
                "IP",
                "公共界面",
                # 🆕 v7.623: 新增高频关键词
                "存量改造",
                "老旧小区",
                "历史街区",
                "工业遗产",
                "文化遗产",
                "微更新",
                "有机更新",
                "渐进式更新",
                "社区营造",
                "公共空间",
                "街道活力",
                "邻里关系",
                "社区参与",
                "保护性开发",
                "修缮",
                "活化",
                "再利用",
                "功能置换",
            ],
            "scenarios": [
                "老街区",
                "工业厂区",
                "城中村",
                "旧商场",
                "滨水空间",
                "文化片区",
                "旧办公楼",
                # 🆕 v7.623: 新增场景
                "老厂房",
                "仓库改造",
                "历史建筑",
                "老社区",
                "文化创意园",
                "艺术区",
                "老码头",
                "铁路遗址",
            ],
            "anti_keywords": [
                # 🆕 v7.623: 扩展反向关键词
                "新建",
                "空地",
                "拆除重建",
                "推倒重来",
                "全新",
            ],
            "weight": 1.2,  # 🆕 v7.623: 提升权重（更新特征明显）
        },
        "M7_tech_integration": {
            "name": "技术整合型设计",
            "keywords": [
                # 原有关键词
                "智能",
                "技术",
                "系统",
                "数据",
                "AI",
                "全屋智能",
                "传感",
                "自动化",
                "科技",
                "物联网",
                "迭代",
                "接口",
                "鸿蒙",
                # 🆕 v7.623: 新增高频关键词
                "人工智能",
                "机器学习",
                "大数据",
                "云计算",
                "5G",
                "智能家居",
                "智慧建筑",
                "BIM",
                "数字孪生",
                "元宇宙",
                "传感器",
                "智能控制",
                "语音控制",
                "人脸识别",
                "能源管理",
                "智能照明",
                "智能安防",
                "智能窗帘",
                "算法",
                "编程",
                "代码",
                "开发",
                "技术栈",
            ],
            "scenarios": [
                "AI企业",
                "智能住宅",
                "全屋智能别墅",
                "研发中心",
                "医疗科技",
                "数据中心",
                "互动展馆",
                # 🆕 v7.623: 新增场景
                "科技公司",
                "互联网企业",
                "智能展厅",
                "未来实验室",
                "智慧社区",
                "智能酒店",
                "无人超市",
                "智能工厂",
            ],
            "anti_keywords": [
                # 🆕 v7.623: 新增反向关键词
                "传统",
                "手工",
                "原始",
                "复古",
                "怀旧",
            ],
            "weight": 1.1,  # 🆕 v7.623: 提升权重（技术特征明显）
        },
        "M8_extreme_condition": {
            "name": "极端环境型设计",
            "keywords": [
                # 原有关键词
                "极端",
                "高海拔",
                "极寒",
                "极热",
                "盐雾",
                "沙漠",
                "海岛",
                "供氧",
                "西藏",
                "高原",
                "抗震",
                "抗风",
                "腐蚀",
                "紫外线",
                # 🆕 v7.623: 新增高频关键词
                "恶劣环境",
                "特殊气候",
                "高原反应",
                "缺氧",
                "低温",
                "高温",
                "强风",
                "台风",
                "地震",
                "海啸",
                "洪水",
                "防潮",
                "防腐",
                "防晒",
                "保温",
                "隔热",
                "通风",
                "特殊材料",
                "耐候性",
                "结构加固",
                "应急预案",
                "生存",
                "安全",
                "防护",
                "适应性",
                "韧性",
            ],
            "scenarios": [
                "西藏",
                "高原民宿",
                "林芝",
                "悬崖酒店",
                "海边",
                "海岛",
                "沙漠营地",
                "地下空间",
                "山地",
                # 🆕 v7.623: 新增场景
                "高原酒店",
                "雪山营地",
                "沙漠酒店",
                "海岛度假村",
                "极地科考站",
                "山顶建筑",
                "悬崖民宿",
                "海上平台",
                "地震带建筑",
                "台风区建筑",
                "高寒地区",
                "热带雨林",
            ],
            "anti_keywords": [
                # 🆕 v7.623: 新增反向关键词
                "温和气候",
                "舒适环境",
                "平原",
                "城市中心",
            ],
            "weight": 1.5,  # 🆕 v7.623: 大幅提升权重（极端环境特征极其明显）
        },
        "M9_social_structure": {
            "name": "社会结构型设计",
            "keywords": [
                # 原有关键词
                "多代同堂",
                "再婚",
                "合租",
                "养老",
                "代际",
                "隐私",
                "权力",
                "冲突",
                "家庭结构",
                "社交",
                "关系",
                "缓冲",
                # 🆕 v7.623: 新增高频关键词
                "家庭关系",
                "代际关系",
                "婆媳关系",
                "亲子关系",
                "独立性",
                "共享空间",
                "私密空间",
                "边界感",
                "领地",
                "社交距离",
                "互动",
                "沟通",
                "矛盾",
                "协调",
                "平衡",
                "老人",
                "儿童",
                "青少年",
                "成年人",
                "多元家庭",
                "单身",
                "丁克",
                "二胎",
                "三代",
                "四代",
                "大家庭",
            ],
            "scenarios": [
                "多代同堂",
                "再婚家庭",
                "合租",
                "养老社区",
                "联合办公",
                "高净值家庭",
                "干部培训",
                "高端医疗",
                # 🆕 v7.623: 新增场景
                "养老院",
                "老年公寓",
                "青年公寓",
                "共享住宅",
                "大家族住宅",
                "复合家庭",
                "社区中心",
                "邻里空间",
                "托老所",
                "日间照料",
                "长者食堂",
                "社区活动室",
            ],
            "anti_keywords": [
                # 🆕 v7.623: 新增反向关键词
                "单身公寓",
                "独居",
                "一人住",
                "极简生活",
            ],
            "weight": 1.3,  # 🆕 v7.623: 提升权重（社会关系特征明确）
        },
        "M10_future_speculation": {
            "name": "未来推演型设计",
            "keywords": [
                # 原有关键词
                "未来",
                "趋势",
                "演进",
                "预判",
                "可迭代",
                "长周期",
                "接口预留",
                "远程办公",
                "生活方式",
                "变化",
                "适配",
                # 🆕 v7.623: 新增高频关键词
                "前瞻性",
                "可持续",
                "灵活性",
                "适应性",
                "弹性空间",
                "模块化",
                "可变",
                "可扩展",
                "升级",
                "迭代",
                "演化",
                "预留",
                "接口",
                "兼容",
                "未来需求",
                "长远规划",
                "趋势预测",
                "场景推演",
                "情景规划",
                "战略布局",
                "新生活方式",
                "新工作模式",
                "新消费",
                "新零售",
            ],
            "scenarios": [
                "AI企业",
                "新型办公",
                "长周期项目",
                "政府战略项目",
                "智能住宅",
                "教育空间",
                "医疗空间",
                # 🆕 v7.623: 新增场景
                "未来社区",
                "实验性项目",
                "示范项目",
                "战略规划",
                "长期投资",
                "可持续建筑",
                "零碳建筑",
                "被动式建筑",
                "模块化住宅",
                "预制装配",
                "灵活办公",
                "混合办公",
            ],
            "anti_keywords": [
                # 🆕 v7.623: 新增反向关键词
                "传统",
                "固定",
                "不变",
                "短期",
                "临时",
                "应急",
            ],
            "weight": 1.0,  # 保持原权重（容易误判，不提升）
        },
        # 🆕 v8.0: 新增 M11 健康疗愈型设计（基于 MODE_COVERAGE_ANALYSIS 空白A修复）
        "M11_healthcare_healing": {
            "name": "健康疗愈型设计",
            "keywords": [
                # 核心疗愈词汇
                "疗愈",
                "康复",
                "治愈",
                "恢复",
                "心理安全",
                "焦虑",
                "医疗",
                "临床",
                "病房",
                "诊所",
                "医院",
                "护理",
                # 脆弱状态词汇
                "脆弱",
                "恐惧",
                "创伤",
                "临终",
                "安宁",
                "宁养",
                "心理健康",
                "心理干预",
                "情绪障碍",
                "压力缓解",
                # 功能需求词汇
                "无障碍",
                "轮椅",
                "康复训练",
                "辅助",
                "适老",
                "自闭症",
                "感统",
                "特殊儿童",
                "特殊需求",
                # 健康空间词汇
                "低刺激",
                "低VOC",
                "昼夜节律",
                "光节律",
                "生理节律",
                "正念",
                "冥想",
                "睡眠",
                "抗焦虑",
                "降压",
                "月子中心",
                "产后恢复",
                "养老",
                "老年照护",
                # 尊严相关
                "尊严",
                "羞耻",
                "消除恐惧",
                "安全感",
                "被接纳",
            ],
            "scenarios": [
                "医院",
                "诊所",
                "康复中心",
                "心理咨询室",
                "养老院",
                "老年公寓",
                "临终关怀",
                "安宁病房",
                "月子中心",
                "新生儿室",
                "儿科",
                "特需学校",
                "无障碍住宅",
                "适老化改造",
                "正念空间",
                "睡眠诊所",
                "心理干预中心",
                "青少年心理",
                "宠物医院",
                "动物医疗",
                "高压人员休息区",
            ],
            "anti_keywords": ["体验高潮", "情绪峰值", "惊喜", "震撼", "炫耀", "商业转化", "坪效", "翻台率", "溢价", "娱乐", "派对", "庆典", "亢奋"],
            "weight": 1.4,  # 高权重：疗愈场景特征非常明确，误判代价大
        },
        "M12_ecological_regeneration": {
            "name": "生态再生型设计",
            "keywords": [
                # 碳与能源
                "碳中和",
                "零碳",
                "碳足迹",
                "碳排放",
                "减碳",
                "脱碳",
                "碳汇",
                "净零",
                "净零碳",
                "正能量建筑",
                "正能建筑",
                "被动式",
                "被动房",
                # 生态修复
                "生态修复",
                "生态再生",
                "生态闭环",
                "生态正向",
                "地球正向",
                "生物多样性",
                "生物友好",
                "本土物种",
                "栖息地",
                "物种修复",
                # 循环材料
                "循环材料",
                "循环经济",
                "再生材料",
                "可再生材料",
                "可回收",
                "生物降解",
                "材料护照",
                "可拆解",
                "隐含碳",
                # 城市微气候
                "热岛效应",
                "微气候",
                "城市降温",
                "蒸腾作用",
                "透水铺装",
                "绿色屋顶",
                "垂直绿化",
                "雨水花园",
                "生物洼地",
                # 水资源
                "雨水收集",
                "灰水循环",
                "水资源闭环",
                "雨洪管理",
                # 认证
                "LEED",
                "BREEAM",
                "Living Building",
                "绿色建筑认证",
                # 再生设计
                "再生设计",
                "可持续设计",
                "星球边界",
            ],
            "scenarios": [
                "零碳建筑",
                "被动式建筑",
                "正能量建筑",
                "生态修复项目",
                "碳中和社区",
                "低碳园区",
                "绿色建筑认证",
                "可持续校园",
                "生态农业建筑",
                "城市森林",
                "绿色基础设施",
                "生物多样性修复",
                "热岛干预项目",
                "海绵城市",
                "循环材料建造",
            ],
            "anti_keywords": ["高能耗", "奢华不计成本", "一次性使用", "快速拆建", "人工造景", "进口奢石", "大面积硬化"],
            "weight": 1.2,  # 中高权重：关键词特征明确，但与 M5/M8 有部分重叠
        },
    }

    @classmethod
    def detect(
        cls, user_input: str, structured_requirements: Optional[Dict] = None
    ) -> List[Tuple[str, float, List[str]]]:
        """
        快速关键词检测（第一阶段筛选）

        🆕 v7.623: 优化检测算法
        - 支持词组匹配（权重2.0）
        - 支持反向关键词检测
        - 优化置信度计算

        Args:
            user_input: 用户输入文本
            structured_requirements: 结构化需求（可选，提供更多上下文）

        Returns:
            List[(mode_id, confidence, matched_keywords), ...]
            按置信度降序排列
        """
        detected_modes = []
        user_input.lower()

        # 如果有结构化需求，也纳入分析
        context_text = user_input
        if structured_requirements:
            project_type = structured_requirements.get("project_type", {})
            if isinstance(project_type, dict):
                context_text += " " + project_type.get("primary", "") + " "
                context_text += " ".join(project_type.get("secondary", []))

        context_lower = context_text.lower()

        for mode_id, signature in cls.MODE_SIGNATURES.items():
            score = 0.0
            matched_keywords = []

            # 1. 关键词匹配
            for kw in signature["keywords"]:
                if kw.lower() in context_lower:
                    matched_keywords.append(kw)
                    # 🆕 v7.623: 词组匹配权重更高
                    if len(kw) > 3:  # 词组（3字以上）
                        score += 1.5
                    else:  # 单字/双字
                        score += 1.0

            # 2. 场景匹配 (权重: 2.5 - 场景匹配更重要)
            for scenario in signature["scenarios"]:
                if scenario.lower() in context_lower:
                    score += 2.5  # 🆕 v7.623: 提升场景权重
                    matched_keywords.append(f"场景:{scenario}")

            # 3. 🆕 v7.623: 负向指标惩罚（更严格）
            anti_penalty = 0
            for anti_kw in signature.get("anti_keywords", []):
                if anti_kw.lower() in context_lower:
                    anti_penalty += 1.0  # 🆕 v7.623: 提升惩罚力度

            # 应用惩罚
            score = max(0, score - anti_penalty)

            # 4. 应用模式权重
            weighted_score = score * signature["weight"]

            # 5. 🆕 v7.623: 优化归一化置信度 (0-1, 6分为满分)
            confidence = min(weighted_score / 6.0, 1.0)

            # 6. 🆕 v7.623: 提升过滤阈值（减少误检）
            if confidence >= 0.30:  # 阈值: 30% (原25%)
                detected_modes.append((mode_id, confidence, matched_keywords))
                logger.debug(
                    f"[Mode Detection] {signature['name']} ({mode_id}): "
                    f"{confidence:.2f} (Matched: {matched_keywords[:3]}...)"
                )

        # 按置信度排序
        detected_modes.sort(key=lambda x: x[1], reverse=True)

        if detected_modes:
            logger.info(
                f"[Mode Detection] Detected {len(detected_modes)} modes, "
                f"Primary: {cls.MODE_SIGNATURES[detected_modes[0][0]]['name']} "
                f"({detected_modes[0][1]:.2f})"
            )
        else:
            logger.warning("[Mode Detection] No clear mode detected, using default mode")

        return detected_modes

    @classmethod
    def detect_primary_mode(cls, user_input: str) -> str:
        """返回主模式ID"""
        modes = cls.detect(user_input)
        if modes:
            return modes[0][0]
        # 默认返回功能效率型
        return "M2_function_efficiency"


class AdvancedModeDetector:
    """基于LLM的高级模式检测器（第二阶段精准判断）"""

    DETECTION_PROMPT_TEMPLATE = """你是一位资深的建筑/室内设计战略顾问。请基于以下项目需求，判断其属于哪种设计模式。

## 12种设计模式定义：

**M1-概念驱动型**: 精神表达优先，空间围绕核心概念展开，代表"思想"而非功能
**M2-功能效率型**: 系统效率优先，减少摩擦和干扰，追求"运转无感"
**M3-情绪体验型**: 感知节奏控制，五感调度系统，制造"让人忘记时间"的体验
**M4-资产资本型**: 资本回报优先，坪效/溢价/现金流，空间作为资产工具
**M5-乡建在地型**: 地域文化+经济闭环+本地材料，构建乡村结构而非风格
**M6-城市更新型**: 片区级重构，土地价值重构+公共界面+产业IP
**M7-技术整合型**: 技术改变空间结构逻辑，而非附加功能
**M8-极端环境型**: 生存优先，结构抗性+环境适应，先活下去再谈美学
**M9-社会结构型**: 社会关系组织，处理权力/隐私/冲突/代际关系
**M10-未来推演型**: 时间维度设计，预判趋势+长周期适配
**M11-健康疗愈型**: 空间作为疗愈工具，安全感优先，降低激活而非制造高潮，为脆弱状态的人提供尊严保护
**M12-生态再生型**: 以地球正向影响为首要设计驱动，碳足迹/循环材料/生态闭环/生物多样性，建筑主动修复生态而非仅减少破坏（注意：区别于M8极端环境的生存逻辑，M12是主动修复逻辑；区别于M5的文化在地逻辑，M12以碳与生态为首要约束）

## 候选模式（关键词初筛结果）：
{candidates}

## 用户需求：
{user_input}

## 你的任务：
1. 从候选模式中选择1-2个最匹配的
2. 给出置信度(0-1)
3. 说明判断理由（20字内）

## 输出JSON格式（严格遵守）：
```json
{{
    "primary_mode": "M1_concept_driven",
    "detected_modes": [
        {{"mode": "M1_concept_driven", "confidence": 0.9, "reason": "强调品牌精神表达"}},
        {{"mode": "M3_emotional_experience", "confidence": 0.6, "reason": "辅助情绪体验"}}
    ]
}}
```

⚠️ 注意：
- confidence必须是0-1之间的浮点数
- reason必须精炼（<20字）
- 只返回JSON，不要额外解释
- M11(健康疗愈) vs M3(情绪体验)：M11是"降低激活/安全恢复"，M3是"制造高潮/峰值体验"，不可混淆
"""

    @classmethod
    async def detect_with_llm(
        cls, user_input: str, candidates: List[Tuple[str, float, List[str]]], llm_client
    ) -> Dict[str, Any]:
        """
        使用LLM进行精准检测

        Args:
            user_input: 用户输入
            candidates: 关键词检测的候选结果 [(mode_id, confidence, keywords), ...]
            llm_client: LLM客户端实例

        Returns:
            {
                "primary_mode": str,
                "detected_modes": [{"mode": str, "confidence": float, "reason": str}, ...]
            }
        """
        # 构建候选列表描述
        candidates_str = "\n".join(
            [
                f"- {DesignModeDetector.MODE_SIGNATURES[m[0]]['name']} " f"({m[0]}): 初步置信度 {m[1]:.2f}"
                for m in candidates[:5]  # 最多5个候选
            ]
        )

        prompt = cls.DETECTION_PROMPT_TEMPLATE.format(candidates=candidates_str, user_input=user_input[:1000])  # 限制长度

        try:
            # 调用LLM
            response = await llm_client.chat.completions.create(
                model="gpt-4o-mini",  # 快速+便宜
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,  # 低温度确保稳定
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)

            logger.info(
                f"[LLM模式检测] 主模式: {result.get('primary_mode', 'N/A')}, " f"检测到{len(result.get('detected_modes', []))}个模式"
            )

            return result

        except Exception as e:
            logger.error(f"[LLM模式检测] 失败: {e}")
            # Fallback: 返回关键词检测结果
            return {
                "primary_mode": candidates[0][0] if candidates else "M2_function_efficiency",
                "detected_modes": [
                    {"mode": m[0], "confidence": m[1], "reason": "LLM失败,使用关键词检测"} for m in candidates[:2]
                ],
            }


class HybridModeDetector:
    """混合检测器: 关键词快速筛选 + LLM精准判断"""

    @classmethod
    async def detect(
        cls, user_input: str, structured_requirements: Optional[Dict] = None, llm_client=None, use_llm: bool = True
    ) -> List[Dict[str, Any]]:
        """
        混合策略检测

        Args:
            user_input: 用户输入
            structured_requirements: 结构化需求（可选）
            llm_client: LLM客户端（可选）
            use_llm: 是否使用LLM增强（默认True）

        Returns:
            [{"mode": str, "confidence": float, "reason": str, "detected_by": str}, ...]
        """
        logger.info("[混合模式检测] 开始检测...")

        # 第一阶段: 关键词快速过滤
        keyword_results = DesignModeDetector.detect(user_input, structured_requirements)

        if not keyword_results:
            logger.warning("[混合模式检测] 关键词检测无结果，返回默认模式")
            return [
                {"mode": "M2_function_efficiency", "confidence": 0.5, "reason": "默认功能效率型", "detected_by": "default"}
            ]

        # 第二阶段: LLM深度分析（可选）
        if use_llm and llm_client and len(keyword_results) >= 2:
            try:
                logger.info("[混合模式检测] 启动LLM精准判断...")
                llm_result = await AdvancedModeDetector.detect_with_llm(
                    user_input, keyword_results[:5], llm_client  # 传Top5候选
                )

                # 合并结果
                final_modes = []
                for mode_info in llm_result.get("detected_modes", []):
                    final_modes.append({**mode_info, "detected_by": "llm"})

                logger.info(f"[混合模式检测] LLM检测完成，识别{len(final_modes)}个模式")
                return final_modes

            except Exception as e:
                logger.warning(f"[混合模式检测] LLM检测失败，降级到关键词结果: {e}")

        # Fallback: 仅使用关键词结果
        logger.info("[混合模式检测] 使用关键词检测结果")
        return [
            {"mode": mode_id, "confidence": confidence, "reason": f"匹配{len(keywords)}个关键词", "detected_by": "keyword"}
            for mode_id, confidence, keywords in keyword_results[:3]  # Top3
        ]

    @classmethod
    def detect_sync(cls, user_input: str, structured_requirements: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        同步版本检测（仅关键词，快速）

        用于不支持async的场景
        """
        keyword_results = DesignModeDetector.detect(user_input, structured_requirements)

        if not keyword_results:
            return [
                {"mode": "M2_function_efficiency", "confidence": 0.5, "reason": "默认功能效率型", "detected_by": "default"}
            ]

        return [
            {"mode": mode_id, "confidence": confidence, "reason": f"匹配{len(keywords)}个特征", "detected_by": "keyword"}
            for mode_id, confidence, keywords in keyword_results[:3]
        ]


# 便捷函数
def detect_design_modes(user_input: str, structured_requirements: Optional[Dict] = None) -> List[Dict[str, Any]]:
    """
    便捷函数：同步检测设计模式（仅关键词）

    Returns:
        [{"mode": str, "confidence": float, "reason": str}, ...]
    """
    return HybridModeDetector.detect_sync(user_input, structured_requirements)


def get_mode_name(mode_id: str) -> str:
    """获取模式中文名"""
    return DesignModeDetector.MODE_SIGNATURES.get(mode_id, {}).get("name", mode_id)
