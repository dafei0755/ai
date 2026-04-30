"""
能力边界检测器 - v7.17 P2
程序化检测用户需求是否在系统能力范围内，减少 LLM 判断负担

核心功能：
1. 检测交付物类型是否在能力范围内
2. 自动转化超出能力的需求为可交付替代方案
3. 检测信息充足性（程序化规则）
4. 提供能力匹配度评分
"""

import re
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
from loguru import logger


# v7.220: 从 PROJECT_TYPE_REGISTRY 聚合关键词，不在此处手动维护
def _build_project_type_keywords() -> List[str]:
    """聚合 PROJECT_TYPE_REGISTRY 全部主关键词，替代手动维护的 INFO_ELEMENTS 列表。"""
    try:
        from intelligent_project_analyzer.services.project_type_detector import PROJECT_TYPE_REGISTRY
        return sorted({kw for entry in PROJECT_TYPE_REGISTRY.values() for kw in entry.get("keywords", [])})
    except ImportError:
        # 仅循环导入兜底，此列表不再手动维护
        return ["住宅", "公寓", "别墅", "办公", "商业", "餐厅", "酒店", "展厅", "店铺",
                "学校", "医院", "菜市场", "民宿", "诊所", "美术馆", "博物馆", "工作室", "旗舰店"]


def _build_commercial_keywords() -> List[str]:
    """聚合商业类 type 主关键词，用于商业项目复杂度推断。"""
    try:
        from intelligent_project_analyzer.services.project_type_detector import PROJECT_TYPE_REGISTRY
        commercial_ids = {
            "commercial_retail", "commercial_office", "commercial_hospitality",
            "commercial_dining", "commercial_enterprise", "brand_experience",
        }
        return [kw for tid, entry in PROJECT_TYPE_REGISTRY.items()
                if tid in commercial_ids
                for kw in entry.get("keywords", [])]
    except ImportError:
        return ["酒店", "餐厅", "商场", "办公楼", "展厅", "菜市场", "商业"]


class CapabilityLevel(Enum):
    """能力级别"""
    FULL = "full"           # 完全在能力范围内
    PARTIAL = "partial"     # 部分在能力范围内（需转化）
    OUTSIDE = "outside"     # 完全超出能力范围


@dataclass
class DeliverableCheck:
    """交付物检测结果"""
    original_type: str              # 原始交付物类型
    detected_keywords: List[str]    # 检测到的关键词
    capability_level: CapabilityLevel  # 能力级别
    within_capability: bool         # 是否在能力范围内
    transformed_type: Optional[str] = None  # 转化后的类型（如需要）
    transformation_reason: str = "" # 转化原因
    confidence: float = 1.0         # 检测置信度


@dataclass
class InfoSufficiencyCheck:
    """信息充足性检测结果"""
    is_sufficient: bool             # 信息是否充足
    score: float                    # 信息充足度评分 (0-1)
    present_elements: List[str]     # 已存在的信息元素
    missing_elements: List[str]     # 缺失的信息元素
    reason: str                     # 判断原因


class CapabilityDetector:
    """
    能力边界检测器
    
    使用程序化规则检测用户需求是否在系统能力范围内，
    在 LLM 调用前完成预筛选，减少 LLM 判断负担。
    """
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 系统能力定义（核心配置）
    # ═══════════════════════════════════════════════════════════════════════════
    
    # 系统核心能力 - 完全支持的交付物类型
    # 🆕 v7.620: 扩展细分类型识别（解决96%单一化问题）
    FULL_CAPABILITY_TYPES = {
        # 文案/创意类
        "naming_list": ["命名", "取名", "起名", "标题", "名称方案"],
        "brand_narrative": ["品牌故事", "叙事策略", "品牌叙事", "故事文案"],
        "copywriting_plan": ["文案策划", "文案方案", "广告文案", "宣传文案"],
        
        # 策略/指导类  
        "design_strategy": ["设计策略", "设计思路", "空间规划思路", "设计理念", "设计方向"],
        "concept_diagram": ["意向图", "概念图", "示意图", "参考图", "氛围板"],
        
        # 🆕 v7.620: 新增细分类型（基于50场景测试）
        "lighting_design": ["灯光设计", "照明方案", "光影设计", "灯光布局", "灯光", "照明"],
        "material_palette": ["材质选择", "材料方案", "色彩搭配", "材质板", "选材"],
        "spatial_planning": ["空间规划", "功能分区", "动线设计", "布局方案", "分区"],
        "furniture_specification": ["家具选型", "家具配置", "定制家具", "家具清单"],
        "technical_requirements": ["技术要求", "声学设计", "隔音方案", "新风系统", "智能家居"],
        
        "material_guidance": ["材料选择指导", "材料建议", "材质方向", "选材指南"],
        "selection_framework": ["选型框架", "选择标准", "评估维度", "决策框架"],
        "procurement_guidance": ["采购指南", "采购建议", "供应商建议"],
        "budget_framework": ["预算框架", "预算分配", "成本结构", "费用规划"],
        
        # 分析/研究类
        "analysis_report": ["分析报告", "研究报告", "调研报告", "诊断报告"],
        "research_summary": ["研究综述", "文献回顾", "案例研究", "趋势分析"],
        "evaluation_report": ["评估报告", "对比分析", "优劣分析"],
        "case_study": ["案例研究", "案例分析", "参考案例", "标杆案例"],
        
        # 方法论/流程类
        "strategy_plan": ["战略规划", "策略方案", "发展规划"],
        "implementation_guide": ["实施指南", "方法论", "操作手册", "执行计划"],
        "decision_framework": ["决策框架", "评估体系", "判断标准"],
        
        # 用户/场景类
        "user_persona": ["用户画像", "人物画像", "客户画像", "用户研究"],
        "scenario_design": ["场景设计", "场景规划", "使用场景", "体验场景"],
        "journey_map": ["用户旅程", "体验地图", "动线规划"],
        
        # 🆕 v7.900: 规划层级类（基于190场景扩展）
        "master_planning": ["总体规划", "整体规划", "规划框架", "空间策略", "策略框架"],
        "landscape_system": ["景观系统", "场地规划", "外部空间", "景观整合", "景观规划"],
        "urban_renewal": ["城市更新", "旧改", "微更新", "社区更新", "街区改造"],
        
        # 🆕 v7.900: 方法论/研究类
        "methodology_framework": ["方法论", "框架体系", "体系构建", "方法论框架", "理论框架"],
        "benchmark_analysis": ["标杆研究", "对标分析", "案例复盘", "竞品分析", "标杆分析"],
        "theoretical_research": ["系统分析", "深度研究", "理论探索", "底层逻辑", "研究框架"],
        
        # 🆕 v7.900: 运营/商业类
        "business_model": ["商业模式", "运营模型", "盈利模式", "商业闭环", "商业策略"],
        "operational_strategy": ["运营策略", "管理机制", "运维方案", "效率系统", "运营体系"],
        "tenant_strategy": ["招商策略", "租户组合", "业态规划", "品牌导入", "业态组合"],
    }
    
    # 超出能力的需求类型 → 转化规则
    CAPABILITY_TRANSFORMATIONS = {
        # 精确图纸类 → 策略类
        "cad_drawing": ("design_strategy", "CAD图纸需要专业制图软件，系统可提供设计策略指导"),
        "construction_drawing": ("design_strategy", "施工图需要专业资质，系统可提供设计思路"),
        "3d_rendering": ("design_strategy", "3D效果图需要专业渲染软件，系统可提供空间概念描述"),
        "floor_plan": ("design_strategy", "平面图需要CAD软件，系统可提供功能分区策略"),
        
        # 精确清单类 → 指导类
        "material_list": ("material_guidance", "精确材料清单需要供应商数据，系统可提供材料选择指导"),
        "product_list": ("selection_framework", "产品清单需要实时市场数据，系统可提供选型框架"),
        "procurement_list": ("procurement_guidance", "采购清单需要供应链数据，系统可提供采购决策指南"),
        "bom_list": ("material_guidance", "物料清单需要工程数据库，系统可提供材料方向指导"),
        
        # 精确估算类 → 框架类
        "cost_estimate": ("budget_framework", "精确成本估算需要实时报价，系统可提供预算框架"),
        "quotation": ("budget_framework", "报价单需要供应商询价，系统可提供成本结构分析"),
        "budget_detail": ("budget_framework", "详细预算需要市场调研，系统可提供预算分配建议"),
        
        # 技术规范类 → 决策框架类
        "technical_spec": ("selection_framework", "技术规范需要产品数据库，系统可提供评估维度"),
        "engineering_spec": ("implementation_guide", "工程规范需要专业标准，系统可提供实施指南"),
    }
    
    # 超出能力的关键词检测
    OUTSIDE_CAPABILITY_KEYWORDS = {
        # 精确图纸关键词
        "drawing": ["CAD", "施工图", "效果图", "3D渲染", "立面图", "剖面图", "节点图", "大样图", "dwg", "skp"],
        # 精确清单关键词
        "list": ["清单", "明细", "BOM", "采购单", "订货单", "品牌型号", "规格参数"],
        # 精确估算关键词
        "estimate": ["报价", "造价", "精确成本", "单价", "总价", "询价"],
        # 实时数据关键词
        "realtime": ["实时价格", "当前市价", "最新报价", "供应商联系方式"],
    }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 信息充足性检测规则
    # ═══════════════════════════════════════════════════════════════════════════
    
    # 信息元素检测规则（关键词 + 权重）
    # 🆕 v7.800: 从7个维度扩展到12个维度，基于85个真实场景分析
    INFO_ELEMENTS = {
        # ═══════════════════════════════════════════════════════════════
        # 核心维度（必须，权重 0.70）
        # ═══════════════════════════════════════════════════════════════
        "project_type": {
            # v7.220: 从 PROJECT_TYPE_REGISTRY 聚合主关键词，不再手动维护
            "keywords": _build_project_type_keywords(),
            "weight": 0.15,
            "description": "项目类型"
        },
        "user_identity": {
            "keywords": ["我是", "我们是", "业主", "客户", "用户", "家庭", "公司", "企业", "个人",
                        "创业者", "企业家", "高管", "合伙人", "律师", "程序员", "设计师"],
            "patterns": [r"\d+岁", r"(男|女)性", r"(单身|已婚|家庭)", r"(海归|留学)", r"富二代"],
            "weight": 0.10,
            "description": "用户身份"
        },
        "space_constraint": {
            "keywords": ["平米", "㎡", "平方", "面积", "户型", "层高", "朝向", "楼层", "建筑面积"],
            "patterns": [r"\d+\s*(平米|㎡|平方|平)", r"\d+\s*层", r"\d+\s*间"],
            "weight": 0.148,
            "description": "空间约束"
        },
        "budget_constraint": {
            "keywords": ["预算", "万元", "费用", "成本", "投资", "元/平米", "造价"],
            "patterns": [r"\d+\s*(万|W|w)", r"预算\s*\d+", r"\d+\s*元"],
            "weight": 0.10,
            "description": "预算约束"
        },
        
        # 🆕 特殊健康/医疗需求（权重 0.10）- 优先级极高
        "special_health_needs": {
            "keywords": ["自闭症", "过敏", "失眠", "焦虑", "抑郁", "轮椅", "无障碍",
                        "临终", "关怀", "产后", "康复", "医疗级", "治疗", "疗愈",
                        "残疾", "特殊需求", "健康问题", "正念", "冥想"],
            "patterns": [r"残疾", r"特殊.*需求", r"健康.*问题", r"过敏.*症"],
            "weight": 0.10,
            "description": "特殊健康/医疗需求"
        },
        
        # 🆕 技术规范/专业标准（权重 0.10）- 优先级极高
        "technical_standards": {
            "keywords": ["隔音", "声学", "杜比", "消防", "供氧", "新风", "智能化", "智能家居",
                        "防腐", "抗风", "防潮", "防白蚁", "紫外线", "传感器", "热力图",
                        "技术标准", "专业级", "工程规范", "全景声", "海拔", "极寒"],
            "patterns": [r"技术.*标准", r"专业.*级", r"工程.*规范", r"(海拔|高原)\s*\d+"],
            "weight": 0.10,
            "description": "技术规范/专业标准"
        },
        
        # ═══════════════════════════════════════════════════════════════
        # 扩展维度（重要，权重 0.25）
        # ═══════════════════════════════════════════════════════════════
        "functional_needs": {
            "keywords": ["需要", "希望", "想要", "功能", "用途", "场景", "使用",
                        "展示", "展览", "办公", "会议", "住宿", "娱乐", "收纳"],
            "weight": 0.042,
            "description": "功能需求"
        },
        "style_preference": {
            "keywords": ["风格", "喜欢", "偏好", "现代", "简约", "中式", "北欧", "日式", "侘寂", "极简",
                        "工业风", "文艺", "复古", "禅意", "新中式", "轻奢"],
            "weight": 0.016,
            "description": "风格偏好"
        },
        
        # 🆕 利益相关者冲突（权重 0.07）- 优先级高
        "stakeholder_conflicts": {
            "keywords": ["冲突", "矛盾", "博弈", "协调", "平衡", "多方", "各自",
                        "不同意见", "分歧", "合租", "再婚", "兼顾", "满足.*都"],
            "patterns": [r"vs\.?", r"(父亲|母亲).*(父亲|母亲)", r"(先生|太太).*(先生|太太)",
                        r"多.*利益", r"\d+方", r"合租"],
            "weight": 0.037,
            "description": "利益相关者冲突"
        },
        
        # 🆕 文化/精神层面（权重 0.05）- 优先级高
        "cultural_spiritual_context": {
            "keywords": ["乡愁", "象征", "精神", "文化", "传承", "哲学", "禅意",
                        "仪式", "心境", "存在", "虚无", "根", "归属", "诗意",
                        "美学", "底层洞察", "内心", "灵性", "重新开始"],
            "patterns": [r"文化.*传承", r"精神.*层面", r"底层.*洞察"],
            "weight": 0.026,
            "description": "文化/精神层面"
        },
        
        # ═══════════════════════════════════════════════════════════════
        # 可选维度（加分项，权重 0.05）
        # ═══════════════════════════════════════════════════════════════
        "time_constraint": {
            "keywords": ["工期", "周期", "时间", "月内", "年内", "尽快", "紧急"],
            "patterns": [r"\d+\s*(个月|周|天|年)", r"工期.*\d+"],
            "weight": 0.005,
            "description": "时间约束"
        },
        
        # 🆕 运营模式（权重 0.02）- 商业可行性关键
        "operational_model": {
            "keywords": ["分时复用", "自助", "坪效", "停留时间", "闭环",
                        "运营", "盈利", "商业模式", "客流", "翻台率", "无人"],
            "patterns": [r"分时.*复用", r"商业.*模式", r"运营.*策略"],
            "weight": 0.010,
            "description": "运营模式"
        },
        
        "regulatory_requirements": {
            "keywords": ["法规", "规范", "标准", "合规", "保护", "历史建筑", "消防规范"],
            "patterns": [r"历史.*建筑", r"文物.*保护", r"合规.*要求"],
            "weight": 0.003,
            "description": "法规约束"
        },
        
        # 🆕 v7.900: 行业/领域约束（权重 0.08）- 基于190场景P0优化
        "industry_context": {
            "keywords": ["酒店", "医院", "学校", "核电", "军事", "宗教", "金融",
                        "实验室", "数据中心", "展馆", "博物馆", "剧院", "诊所",
                        "银行", "科研", "教育", "医疗", "文化", "体育"],
            "patterns": [r"酒店.*品牌", r"医疗.*等级", r"实验室.*标准", r".*级.*医院"],
            "weight": 0.042,
            "description": "行业/领域约束"
        },
        
        # 🆕 v7.900: 多方协同需求（权重 0.06）
        "multi_stakeholder": {
            "keywords": ["协同", "多方", "跨界", "再婚", "合租", "共享", "联盟",
                        "联合", "协作", "跨专业", "跨学科", "多元", "融合"],
            "patterns": [r"vs[.。]?", r"(.*方|.*者|.*群).*(vs|与|和).*(.*方|.*者|.*群)",
                        r"多.*群体", r"跨.*背景", r"不同.*文化", r"\d+方"],
            "weight": 0.031,
            "description": "多方协同需求"
        },
        
        # 🆕 v7.900: 极端环境约束（权重 0.07）
        "extreme_environment": {
            "keywords": ["海拔", "沙漠", "极寒", "高温", "台风", "盐雾", "白蚁",
                        "辐射", "火山", "极昼", "极夜", "地震带", "高原", "极地",
                        "干旱", "洪水", "强风", "腐蚀", "严酷", "极端气候"],
            "patterns": [r"海拔\s*\d+", r"极.*气候", r"抗.*\d+级", r"零下.*度",
                        r"(海拔|高原)\s*\d+", r"台风.*\d+级"],
            "weight": 0.037,
            "description": "极端环境约束"
        },
        
        # ═══════════════════════════════════════════════════════════════
        # 🆕 v7.900.1: P3优化新增维度（基于190场景完整分析）
        # ═══════════════════════════════════════════════════════════════
        
        # 🆕 维度17: 品牌定位/学习对象（权重 0.03）
        "reference_target": {
            "keywords": ["品牌", "学习", "对标", "参考", "竞品", "标杆", "借鉴",
                        "季裕棠", "安藤忠雄", "HAY", "Tiffany", "HBA", "CCD", "杨邦胜",
                        "雅诗阁", "柏悦", "安缦", "隈研吾", "长谷川逸子", "王澍"],
            "patterns": [r"以.*为核心", r"对标.*", r"参考.*", r"学习.*风格", 
                        r"借鉴.*", r"致敬.*", r".*气质", r".*精神"],
            "weight": 0.016,
            "description": "品牌定位/学习对象"
        },
        
        # 🆕 维度18: 成本策略导向（权重 0.03）
        "cost_strategy": {
            "keywords": ["成本控制", "预算分配", "资金策略", "性价比", "投入产出",
                        "极致压缩", "坪效", "翻台率", "停留时间", "客单价",
                        "视觉杠杆", "重点投入", "分级投入", "成本优化"],
            "patterns": [r"预算.*仅", r"极低.*成本", r"成本.*策略", r"\d+元/㎡",
                        r"坪效.*", r"翻台.*", r"控制.*时间", r"提升.*效率"],
            "weight": 0.016,
            "description": "成本策略导向"
        },
        
        # 🆕 维度19: 研究/教育/展示目标（权重 0.04）
        "research_education_goal": {
            "keywords": ["博物馆", "展览", "教学", "培训", "研究", "实验", "体验",
                        "科研", "学术", "展示", "体验馆", "教育中心", "学习空间",
                        "交流中心", "知识", "认知", "探索", "发现", "互动展项",
                        "行为经济学", "神经科学", "社会学", "人类学", "博弈论"],
            "patterns": [r".*馆$", r".*中心$", r"研究.*实验", r"教学.*空间",
                        r"展示.*", r"体验.*", r"学术.*", r"科研.*"],
            "weight": 0.021,
            "description": "研究/教育/展示目标"
        },
    }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 🆕 v7.900 P2: 场景分类标签系统（基于190场景分析）
    # ═══════════════════════════════════════════════════════════════════════════
    SCENARIO_TYPES = {
        "spatial_design": {
            "keywords": ["住宅", "公寓", "别墅", "办公", "商业空间", "店铺", "餐厅", 
                        "酒店", "民宿", "展厅", "诊所", "美术馆", "卧室", "客厅", 
                        "厨房", "书房", "卫生间", "阳台", "玄关", "空间设计"],
            "patterns": [r"\d+\s*(平米|㎡|平方)", r"\d+\s*室\s*\d+\s*厅", r"层高", r"朝向"],
            "priority": 1,
            "description": "空间设计类"
        },
        "planning": {
            "keywords": ["总体规划", "整体规划", "区域规划", "城市设计", "策略框架",
                        "发展规划", "空间策略", "顶层设计", "布局规划", "分区规划",
                        "景观系统", "场地规划", "外部空间", "街区", "社区规划"],
            "patterns": [r"总体.*规划", r"整体.*策略", r"顶层.*设计"],
            "priority": 2,
            "description": "规划策略类"
        },
        "operational": {
            "keywords": ["运营", "管理", "商业模式", "盈利模式", "招商", "业态",
                        "运维", "效率", "成本控制", "绩效", "租赁", "定价",
                        "服务流程", "标准化", "管理制度", "坪效", "翻台率"],
            "patterns": [r"运营.*模式", r"商业.*策略", r"管理.*体系", r"盈利.*模型"],
            "priority": 3,
            "description": "运营管理类"
        },
        "research": {
            "keywords": ["研究", "分析", "调研", "评估", "诊断", "可行性",
                        "市场分析", "影响评估", "趋势", "对比", "标杆", "案例研究",
                        "竞品分析", "用户研究", "痛点分析", "需求洞察"],
            "patterns": [r".*研究", r".*分析", r".*评估", r"可行性.*报告"],
            "priority": 4,
            "description": "研究分析类"
        },
        "methodology": {
            "keywords": ["方法论", "框架", "体系", "理论", "标准", "规范",
                        "流程", "模型", "评价体系", "指标体系", "决策框架",
                        "评估标准", "操作指南", "实施方法", "系统构建"],
            "patterns": [r"方法.*论", r".*框架", r".*体系", r"标准.*体系"],
            "priority": 5,
            "description": "方法论/框架类"
        },
        "renovation": {
            "keywords": ["改造", "旧改", "更新", "升级", "优化", "微改造",
                        "翻新", "重构", "再设计", "焕新", "活化", "存量",
                        "老旧", "二次设计", "改建", "既有建筑"],
            "patterns": [r"旧.*改", r"存量.*改造", r"老旧.*更新", r"微.*改造"],
            "priority": 6,
            "description": "改造优化类"
        },
        "creative": {
            "keywords": ["命名", "取名", "起名", "品牌故事", "文案", "创意",
                        "叙事策略", "IP打造", "内容策划", "传播方案", "宣传"],
            "patterns": [r".*命名", r"品牌.*故事", r"文案.*策划"],
            "priority": 7,
            "description": "文案创意类"
        },
    }
    
    # 🆕 v7.800: 信息充足阈值优化（基于85个场景测试）
    # 从 0.40 提升到 0.50，减少误判"信息不足"
    # 从 2个最少元素提升到 3个，确保关键信息充足
    INFO_SUFFICIENT_THRESHOLD = 0.50  # 信息量评分超过此值认为充足（0.40→0.50）
    INFO_ELEMENT_MIN_COUNT = 3        # 至少需要的信息元素数量（2→3）
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 核心检测方法
    # ═══════════════════════════════════════════════════════════════════════════
    
    @classmethod
    def detect_deliverable_capability(cls, user_input: str) -> List[DeliverableCheck]:
        """
        检测用户输入中的交付物需求是否在系统能力范围内
        
        Args:
            user_input: 用户输入文本
            
        Returns:
            交付物检测结果列表
        """
        results = []
        text_lower = user_input.lower()
        
        # 1. 检测完全在能力范围内的交付物
        for deliverable_type, keywords in cls.FULL_CAPABILITY_TYPES.items():
            detected = [kw for kw in keywords if kw in user_input]
            if detected:
                results.append(DeliverableCheck(
                    original_type=deliverable_type,
                    detected_keywords=detected,
                    capability_level=CapabilityLevel.FULL,
                    within_capability=True,
                    confidence=min(len(detected) / 2, 1.0)
                ))
        
        # 2. 检测超出能力的关键词
        outside_detected = []
        for category, keywords in cls.OUTSIDE_CAPABILITY_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in text_lower or kw in user_input:
                    outside_detected.append((category, kw))
        
        # 3. 对超出能力的需求进行转化
        if outside_detected:
            # 按类别分组
            by_category = {}
            for category, kw in outside_detected:
                if category not in by_category:
                    by_category[category] = []
                by_category[category].append(kw)
            
            for category, keywords in by_category.items():
                # 确定转化类型
                transform_key = cls._get_transform_key(category, keywords)
                if transform_key and transform_key in cls.CAPABILITY_TRANSFORMATIONS:
                    transformed_type, reason = cls.CAPABILITY_TRANSFORMATIONS[transform_key]
                    results.append(DeliverableCheck(
                        original_type=transform_key,
                        detected_keywords=keywords,
                        capability_level=CapabilityLevel.PARTIAL,
                        within_capability=False,
                        transformed_type=transformed_type,
                        transformation_reason=reason,
                        confidence=0.8
                    ))
        
        # 4. 如果没有检测到任何交付物，返回默认
        if not results:
            results.append(DeliverableCheck(
                original_type="design_strategy",
                detected_keywords=["设计", "方案"],  # 默认假设
                capability_level=CapabilityLevel.FULL,
                within_capability=True,
                confidence=0.5  # 低置信度
            ))
        
        logger.info(f"[能力检测] 检测到 {len(results)} 个交付物需求")
        for r in results:
            status = "" if r.within_capability else f"️→{r.transformed_type}"
            logger.debug(f"  - {r.original_type}: {status} (关键词: {r.detected_keywords})")
        
        return results
    
    @classmethod
    def _get_transform_key(cls, category: str, keywords: List[str]) -> Optional[str]:
        """根据检测类别和关键词确定转化键"""
        keyword_mapping = {
            "drawing": {
                "CAD": "cad_drawing",
                "施工图": "construction_drawing",
                "效果图": "3d_rendering",
                "3D渲染": "3d_rendering",
                "立面图": "cad_drawing",
                "剖面图": "cad_drawing",
                "default": "cad_drawing"
            },
            "list": {
                "清单": "material_list",
                "BOM": "bom_list",
                "采购单": "procurement_list",
                "订货单": "procurement_list",
                "default": "material_list"
            },
            "estimate": {
                "报价": "quotation",
                "造价": "cost_estimate",
                "精确成本": "cost_estimate",
                "default": "cost_estimate"
            },
            "realtime": {
                "default": "cost_estimate"
            }
        }
        
        if category not in keyword_mapping:
            return None
        
        mapping = keyword_mapping[category]
        for kw in keywords:
            if kw in mapping:
                return mapping[kw]
        
        return mapping.get("default")
    
    @classmethod
    def _detect_implicit_info(cls, user_input: str) -> float:
        """
        检测输入中的隐含信息，进行智能推断加分
        
        基于v7.620质量测试发现：
        - "创业者" → 隐含高净值、时间紧张
        - "企业家" → 隐含预算充足
        - 特定人群词 → 隐含功能需求
        
        🆕 v7.900扩展:
        - 历史建筑 → 隐含结构限制+法规约束+文化表达
        - 临时项目 → 隐含时间紧+可拆卸+成本控制
        - 跨文化 → 隐含文化表达+国际标准
        
        Args:
            user_input: 用户输入文本
            
        Returns:
            加分值（0-0.3）
        """
        boost = 0.0
        
        # 高净值人群隐含信息
        high_net_worth_keywords = ["创业者", "企业家", "高管", "CEO", "董事长", "总裁", "投行", "金融", "合伙人"]
        if any(kw in user_input for kw in high_net_worth_keywords):
            boost += 0.20  # 提升加分（原15→20）
            logger.debug("  → 推断：高净值人群（预算充足）")
        
        # 特殊需求人群隐含功能
        special_needs = [
            ("自闭症", 0.15, "特殊医疗需求"),
            ("失眠", 0.12, "睡眠环境优化"),
            ("过敏", 0.10, "材料筛选要求"),
            ("电竞", 0.12, "专业设备需求"),
            ("直播", 0.08, "设备+声光需求"),
            ("瑜伽", 0.08, "功能区需求"),
            ("健身", 0.08, "功能区需求"),
            ("收藏", 0.10, "展示+收纳需求"),
            ("冥想", 0.08, "氛围设计需求")
        ]
        for keyword, score, desc in special_needs:
            if keyword in user_input:
                boost += score
                logger.debug(f"  → 推断：{desc}")
        
        # 大规模项目隐含详细需求
        import re
        area_match = re.search(r'(\d+)\s*(平米|㎡|平方)', user_input)
        if area_match:
            area = int(area_match.group(1))
            if area > 300:  # 大面积项目
                boost += 0.1
                logger.debug(f"  → 推断：大面积项目（{area}㎡）→ 复杂需求")
        
        # 商业项目隐含多方需求（v7.220: 关键词从 PROJECT_TYPE_REGISTRY 商业类型聚合）
        commercial_keywords = _build_commercial_keywords()
        if any(kw in user_input for kw in commercial_keywords):
            boost += 0.1
            logger.debug("  → 推断：商业项目（多维度约束）")
        
        # 🆕 v7.900: 历史建筑隐含信息
        historical_keywords = ["四合院", "老洋楼", "历史建筑", "文物", "保护建筑",
                             "百年老宅", "传统民居", "古镇", "历史街区", "老宅",
                             "古建筑", "文物保护", "历史遗存"]
        if any(kw in user_input for kw in historical_keywords):
            boost += 0.15
            logger.debug("  → 推断：历史建筑保护约束（结构+法规+文化）")
        
        # 🆕 v7.900: 临时性项目隐含信息
        import re
        temporary_patterns = [r"为期.*月", r"临时", r"快闪", r"拆除.*回收", r"可移动",
                            r"\d+个月.*拆除", r"活动.*\d+天"]
        if any(re.search(p, user_input) for p in temporary_patterns):
            boost += 0.12
            logger.debug("  → 推断：临时性项目（时间紧+可拆卸+成本控制）")
        
        # 🆕 v7.900: 国际/跨文化项目隐含信息
        international_keywords = ["跨国", "国际", "双国籍", "海归", "跨文化", "多元文化",
                                "一带一路", "跨信仰", "全球化", "全球", "外籍", "国际品牌"]
        if any(kw in user_input for kw in international_keywords):
            boost += 0.10
            logger.debug("  → 推断：跨文化项目（文化表达+国际标准）")
        
        return min(boost, 0.3)  # 最多加0.3分
    
    @classmethod
    def _detect_scenario_type(cls, user_input: str) -> List[Tuple[str, float]]:
        """
        🆕 v7.900 P2: 检测场景类型标签
        
        基于190场景分析，识别主要场景类型：
        - spatial_design: 空间设计类（住宅、办公、商业空间等）
        - planning: 规划策略类（总体规划、区域规划等）
        - operational: 运营管理类（运营模式、商业模式等）
        - research: 研究分析类（市场研究、可行性研究等）
        - methodology: 方法论类（框架体系、标准规范等）
        - renovation: 改造优化类（旧改、升级等）
        - creative: 文案创意类（命名、品牌故事等）
        
        Args:
            user_input: 用户输入文本
            
        Returns:
            场景类型列表，格式: [(type, confidence), ...]
            按confidence降序排列，confidence相同时按priority升序
        """
        import re
        
        # 定义核心标识词（这些词出现时给予额外加权）
        core_identifiers = {
            "creative": ["命名", "取名", "起名", "品牌故事", "文案"],
            "methodology": ["方法论", "框架体系", "理论框架", "标准体系", "方法论框架", "理论"],
            "planning": ["总体规划", "整体规划", "区域规划", "顶层设计"],
            "operational": ["运营模式", "商业模式", "盈利模式"],
            "research": ["可行性研究", "市场研究", "影响评估"],
        }
        
        detected_types = []
        
        for scenario_type, config in cls.SCENARIO_TYPES.items():
            keywords = config.get("keywords", [])
            patterns = config.get("patterns", [])
            priority = config.get("priority", 99)
            
            # 关键词匹配计分
            keyword_matches = [kw for kw in keywords if kw in user_input]
            keyword_score = len(keyword_matches) * 0.2
            
            # 核心标识词额外加分
            core_match = False
            core_boost = 0.0
            if scenario_type in core_identifiers:
                core_words = core_identifiers[scenario_type]
                if any(word in user_input for word in core_words):
                    core_boost = 0.3  # 核心标识词额外加0.3分
                    core_match = True
                    logger.debug(f"  → 核心标识: {scenario_type} 检测到核心词")
            
            # 正则模式匹配计分
            pattern_matches = 0
            for pattern in patterns:
                if re.search(pattern, user_input):
                    pattern_matches += 1
            pattern_score = pattern_matches * 0.3
            
            # 计算总分
            total_score = keyword_score + pattern_score + core_boost
            
            # 优先级加权（priority越小越重要）
            if total_score > 0:
                priority_boost = (10 - priority) * 0.05  # priority 1→0.45加分，priority 7→0.15加分
                confidence = min(total_score + priority_boost, 1.0)
                # 保存(type, confidence, priority, core_match)用于排序
                detected_types.append((scenario_type, confidence, priority, core_match))
                logger.debug(f"  → 场景类型: {scenario_type} (置信度: {confidence:.2f}, 匹配词: {keyword_matches[:3]})")
        
        # 排序逻辑：
        # 1. 置信度降序（高置信度优先）
        # 2. 置信度相同时，有核心标识的优先
        # 3. 都有或都没有核心标识时，按priority升序（优先级高的排前面）
        detected_types.sort(key=lambda x: (-x[1], not x[3], x[2]))
        
        # 移除priority和core_match，只返回(type, confidence)
        detected_types = [(t, c) for t, c, p, cm in detected_types]
        
        # 如果没检测到任何场景，默认为spatial_design
        if not detected_types:
            detected_types = [("spatial_design", 0.5)]
            logger.debug("  → 场景类型: spatial_design (默认)")
        
        return detected_types
    
    @classmethod
    def check_info_sufficiency(cls, user_input: str) -> InfoSufficiencyCheck:
        """
        程序化检测用户输入的信息充足性
        
        Args:
            user_input: 用户输入文本
            
        Returns:
            信息充足性检测结果
        """
        present_elements = []
        missing_elements = []
        total_score = 0.0
        
        for element_id, config in cls.INFO_ELEMENTS.items():
            keywords = config.get("keywords", [])
            patterns = config.get("patterns", [])
            weight = config.get("weight", 0.1)
            description = config.get("description", element_id)
            
            # 关键词匹配
            keyword_match = any(kw in user_input for kw in keywords)
            
            # 正则模式匹配
            pattern_match = False
            for pattern in patterns:
                if re.search(pattern, user_input):
                    pattern_match = True
                    break
            
            if keyword_match or pattern_match:
                present_elements.append(description)
                total_score += weight
            else:
                missing_elements.append(description)
        
        # 计算文本长度加成
        text_length = len(user_input)
        if text_length > 200:
            total_score += 0.1
        if text_length > 500:
            total_score += 0.1
        
        # 🆕 v7.620: 隐含信息推断（提升判断智能度）
        implicit_boost = cls._detect_implicit_info(user_input)
        total_score += implicit_boost
        if implicit_boost > 0:
            logger.debug(f"[隐含信息] 推断加分 +{implicit_boost:.2f}")
        
        # 🆕 v7.900 P1: 关键元素加权判断
        # 检测关键元素（高优先级维度）
        critical_element_names = [
            "特殊健康/医疗需求", 
            "技术规范/专业标准", 
            "极端环境约束", 
            "利益相关者冲突",
            "行业/领域约束",  # v7.900新增
            "多方协同需求"      # v7.900新增
        ]
        critical_elements_detected = [elem for elem in critical_element_names if elem in present_elements]
        
        # 关键元素调整阈值
        adjusted_threshold = cls.INFO_SUFFICIENT_THRESHOLD
        threshold_adjustment = 0.0
        
        if critical_elements_detected:
            # 有关键元素时，降低阈值要求（每个关键元素降低0.03）
            threshold_adjustment = min(len(critical_elements_detected) * 0.03, 0.10)
            adjusted_threshold = cls.INFO_SUFFICIENT_THRESHOLD - threshold_adjustment
            logger.debug(f"[关键元素] 检测到 {len(critical_elements_detected)} 个关键元素: {', '.join(critical_elements_detected[:2])}")
            logger.debug(f"[关键元素] 阈值调整: {cls.INFO_SUFFICIENT_THRESHOLD:.2f} → {adjusted_threshold:.2f} (-{threshold_adjustment:.2f})")
        
        # 判断是否充足（使用调整后的阈值）
        is_sufficient = (
            total_score >= adjusted_threshold and
            len(present_elements) >= cls.INFO_ELEMENT_MIN_COUNT
        )
        
        # 生成原因说明（v7.900: 包含关键元素信息）
        if is_sufficient:
            if critical_elements_detected:
                reason = f"信息充足（得分 {total_score:.2f}，包含 {len(present_elements)} 个元素，其中 {len(critical_elements_detected)} 个关键元素）"
            else:
                reason = f"信息充足（得分 {total_score:.2f}，包含 {len(present_elements)} 个关键元素）"
        else:
            if critical_elements_detected:
                reason = f"信息不足（得分 {total_score:.2f}，阈值已调整至 {adjusted_threshold:.2f}，缺少：{', '.join(missing_elements[:3])}）"
            else:
                reason = f"信息不足（得分 {total_score:.2f}，缺少：{', '.join(missing_elements[:3])}）"
        
        result = InfoSufficiencyCheck(
            is_sufficient=is_sufficient,
            score=min(total_score, 1.0),
            present_elements=present_elements,
            missing_elements=missing_elements,
            reason=reason
        )
        
        logger.info(f"[信息充足性] {' 充足' if is_sufficient else '️ 不足'} - {reason}")
        
        return result
    
    @classmethod
    def full_capability_check(cls, user_input: str) -> Dict[str, Any]:
        """
        完整的能力边界检测（综合交付物检测 + 信息充足性检测 + 场景分类）
        
        🆕 v7.900 P2: 新增场景类型检测
        
        Args:
            user_input: 用户输入文本
            
        Returns:
            综合检测结果字典，可直接用于 Phase1 的预处理
        """
        # 1. 交付物检测
        deliverable_checks = cls.detect_deliverable_capability(user_input)
        
        # 2. 信息充足性检测
        info_check = cls.check_info_sufficiency(user_input)
        
        # 🆕 v7.900 P2: 场景类型检测
        scenario_types = cls._detect_scenario_type(user_input)
        primary_scenario = scenario_types[0] if scenario_types else ("spatial_design", 0.5)
        
        # 3. 汇总需要转化的交付物
        transformations_needed = [
            {
                "original": check.original_type,
                "transformed_to": check.transformed_type,
                "reason": check.transformation_reason,
                "keywords": check.detected_keywords
            }
            for check in deliverable_checks
            if not check.within_capability and check.transformed_type
        ]
        
        # 4. 汇总在能力范围内的交付物
        capable_deliverables = [
            {
                "type": check.original_type,
                "keywords": check.detected_keywords,
                "confidence": check.confidence
            }
            for check in deliverable_checks
            if check.within_capability
        ]
        
        # 5. 计算整体能力匹配度
        total_checks = len(deliverable_checks)
        capable_count = sum(1 for c in deliverable_checks if c.within_capability)
        capability_score = capable_count / total_checks if total_checks > 0 else 1.0
        
        result = {
            "info_sufficiency": {
                "is_sufficient": info_check.is_sufficient,
                "score": info_check.score,
                "present_elements": info_check.present_elements,
                "missing_elements": info_check.missing_elements,
                "reason": info_check.reason
            },
            "deliverable_capability": {
                "capability_score": capability_score,
                "total_detected": total_checks,
                "capable_count": capable_count,
                "transformations_needed": len(transformations_needed)
            },
            # 🆕 v7.900 P2: 场景分类结果
            "scenario_classification": {
                "primary_type": primary_scenario[0],
                "primary_confidence": primary_scenario[1],
                "all_detected_types": [{"type": t, "confidence": c} for t, c in scenario_types[:3]],  # 最多返回前3个
                "description": cls.SCENARIO_TYPES.get(primary_scenario[0], {}).get("description", "未知场景类型")
            },
            "capable_deliverables": capable_deliverables,
            "transformations": transformations_needed,
            "recommended_action": cls._recommend_action(info_check, deliverable_checks),
            "pre_phase1_hints": cls._generate_hints(info_check, deliverable_checks)
        }
        
        logger.info(f"[完整检测] 信息: {'充足' if info_check.is_sufficient else '不足'}, "
                   f"能力匹配: {capability_score:.0%}, 转化需求: {len(transformations_needed)}, "
                   f"场景类型: {primary_scenario[0]} (置信度: {primary_scenario[1]:.2f})")
        
        return result
    
    @classmethod
    def _recommend_action(cls, info_check: InfoSufficiencyCheck, 
                          deliverable_checks: List[DeliverableCheck]) -> str:
        """根据检测结果推荐下一步行动"""
        if not info_check.is_sufficient:
            return "questionnaire_first"
        
        # 检查是否有完全超出能力的需求
        outside_count = sum(1 for c in deliverable_checks 
                          if c.capability_level == CapabilityLevel.OUTSIDE)
        if outside_count > 0:
            return "clarify_expectations"
        
        return "proceed_analysis"
    
    @classmethod
    def _generate_hints(cls, info_check: InfoSufficiencyCheck,
                        deliverable_checks: List[DeliverableCheck]) -> List[str]:
        """生成给 Phase1 LLM 的提示"""
        hints = []
        
        # 信息提示
        if info_check.is_sufficient:
            hints.append(f"[预检测] 信息充足，包含：{', '.join(info_check.present_elements)}")
        else:
            hints.append(f"[预检测] 信息不足，缺少：{', '.join(info_check.missing_elements[:3])}")
        
        # 能力提示
        for check in deliverable_checks:
            if not check.within_capability and check.transformed_type:
                hints.append(
                    f"[能力边界] 检测到超出能力的需求 '{check.detected_keywords}'，"
                    f"建议转化为 '{check.transformed_type}'"
                )
        
        return hints


# 便捷函数
def check_capability(user_input: str) -> Dict[str, Any]:
    """便捷函数：完整的能力边界检测"""
    return CapabilityDetector.full_capability_check(user_input)


def check_info_sufficient(user_input: str) -> bool:
    """便捷函数：快速检测信息是否充足"""
    return CapabilityDetector.check_info_sufficiency(user_input).is_sufficient
