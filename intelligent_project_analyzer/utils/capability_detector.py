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
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List

from loguru import logger


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
    transformed_type: str | None = None  # 转化后的类型（如需要）
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
    INFO_ELEMENTS = {
        "project_type": {
            "keywords": ["住宅", "公寓", "别墅", "办公", "商业", "餐厅", "酒店", "展厅", "店铺", "学校", "医院"],
            "weight": 0.2,
            "description": "项目类型"
        },
        "user_identity": {
            "keywords": ["我是", "我们是", "业主", "客户", "用户", "家庭", "公司", "企业", "个人"],
            "patterns": [r"\d+岁", r"(男|女)性", r"(单身|已婚|家庭)"],
            "weight": 0.15,
            "description": "用户身份"
        },
        "space_constraint": {
            "keywords": ["平米", "㎡", "平方", "面积", "户型", "层高", "朝向", "楼层"],
            "patterns": [r"\d+\s*(平米|㎡|平方|平)"],
            "weight": 0.2,
            "description": "空间约束"
        },
        "budget_constraint": {
            "keywords": ["预算", "万元", "费用", "成本", "投资"],
            "patterns": [r"\d+\s*(万|W|w)", r"预算\s*\d+"],
            "weight": 0.15,
            "description": "预算约束"
        },
        "time_constraint": {
            "keywords": ["工期", "周期", "时间", "月内", "年内", "尽快"],
            "patterns": [r"\d+\s*(个月|周|天|年)"],
            "weight": 0.1,
            "description": "时间约束"
        },
        "functional_needs": {
            "keywords": ["需要", "希望", "想要", "功能", "用途", "场景", "使用"],
            "weight": 0.1,
            "description": "功能需求"
        },
        "style_preference": {
            "keywords": ["风格", "喜欢", "偏好", "现代", "简约", "中式", "北欧", "日式", "侘寂", "极简"],
            "weight": 0.1,
            "description": "风格偏好"
        },
    }
    
    # 信息充足阈值（v7.620优化：0.5→0.45→0.40，提升sufficient判定率）
    INFO_SUFFICIENT_THRESHOLD = 0.40  # 信息量评分超过此值认为充足
    INFO_ELEMENT_MIN_COUNT = 2        # 至少需要的信息元素数量（降低3→2）
    
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
    def _get_transform_key(cls, category: str, keywords: List[str]) -> str | None:
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
        
        # 商业项目隐含多方需求
        commercial_keywords = ["酒店", "餐厅", "商场", "办公楼", "展厅", "菜市场", "商业"]
        if any(kw in user_input for kw in commercial_keywords):
            boost += 0.1
            logger.debug("  → 推断：商业项目（多维度约束）")
        
        return min(boost, 0.3)  # 最多加0.3分
    
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
        
        # 判断是否充足
        is_sufficient = (
            total_score >= cls.INFO_SUFFICIENT_THRESHOLD and
            len(present_elements) >= cls.INFO_ELEMENT_MIN_COUNT
        )
        
        # 生成原因说明
        if is_sufficient:
            reason = f"信息充足（得分 {total_score:.2f}，包含 {len(present_elements)} 个关键元素）"
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
        完整的能力边界检测（综合交付物检测 + 信息充足性检测）
        
        Args:
            user_input: 用户输入文本
            
        Returns:
            综合检测结果字典，可直接用于 Phase1 的预处理
        """
        # 1. 交付物检测
        deliverable_checks = cls.detect_deliverable_capability(user_input)
        
        # 2. 信息充足性检测
        info_check = cls.check_info_sufficiency(user_input)
        
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
            "capable_deliverables": capable_deliverables,
            "transformations": transformations_needed,
            "recommended_action": cls._recommend_action(info_check, deliverable_checks),
            "pre_phase1_hints": cls._generate_hints(info_check, deliverable_checks)
        }
        
        logger.info(f"[完整检测] 信息: {'充足' if info_check.is_sufficient else '不足'}, "
                   f"能力匹配: {capability_score:.0%}, 转化需求: {len(transformations_needed)}")
        
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
