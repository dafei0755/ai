"""
领域分类器 - 判断是否属于空间设计领域
"""

import re
import json
from typing import Dict, Any, List, Optional
from loguru import logger


class DomainClassifier:
    """领域分类器 - 判断输入是否属于空间设计领域"""
    
    # 设计领域关键词
    DESIGN_KEYWORDS = {
        "空间设计": ["空间", "室内", "建筑", "景观", "展厅", "办公室", "住宅", "商业空间", "店铺", "餐厅", "酒店", "包房"],  # 🆕 添加"包房"
        "设计元素": ["布局", "动线", "材质", "色彩", "照明", "家具", "装饰", "软装", "硬装", "吊顶", "地面"],
        "设计风格": ["现代", "简约", "工业风", "新中式", "北欧", "轻奢", "极简", "复古", "日式", "欧式"],
        "设计阶段": ["方案设计", "概念设计", "施工图", "效果图", "深化设计", "软装设计", "平面图"],
        "空间类型": ["办公空间", "零售空间", "展览空间", "餐饮空间", "酒店空间", "会所", "公共空间", "咖啡厅", "咖啡馆", "客厅"],
        "设计需求": ["装修", "改造", "翻新", "设计方案", "空间规划", "功能分区", "氛围营造", "设计", "命名", "起名", "取名"],  # 🆕 添加命名类
        "技术要素": ["结构", "机电", "暖通", "智能化", "可持续", "BIM", "节能", "环保"],
        "用户体验": ["用户体验", "交互", "动线设计", "氛围", "舒适度", "视觉效果"],
        "商业要素": ["成本", "预算", "ROI", "招商", "运营", "品牌", "定位"],
        "实施要素": ["施工", "工期", "采购", "验收", "交付", "材料", "工艺"]
    }
    
    # 非设计领域关键词
    NON_DESIGN_KEYWORDS = {
        "编程开发": ["python", "代码", "编程", "算法", "数据库", "api", "前端", "后端", "java", "c++", "爬虫", "程序", "存储"],
        "医疗健康": ["疾病", "药物", "治疗", "医院", "手术", "病人", "医生", "诊断"],
        "法律金融": ["法律", "合同", "诉讼", "股票", "投资", "贷款", "证券", "理财"],
        "学术教育": ["论文", "考试", "课程", "作业", "毕业", "学位", "教材"],
        "娱乐游戏": ["游戏", "电影", "小说", "漫画", "动画", "娱乐"],
        "电商购物": ["淘宝", "京东", "购物", "快递", "物流", "下单"],
        "社交媒体": ["微信", "抖音", "微博", "朋友圈", "点赞", "转发"]
    }
    
    def __init__(self, llm_model=None):
        """
        初始化领域分类器
        
        Args:
            llm_model: LLM模型实例（用于辅助判断）
        """
        self.llm_model = llm_model
    
    def classify(self, user_input: str) -> Dict[str, Any]:
        """
        分类用户输入
        
        Args:
            user_input: 用户输入文本
            
        Returns:
            {
                "is_design_related": bool | "unclear",
                "confidence": float,  # 0-1
                "matched_categories": List[str],
                "rejection_reason": str,  # 如果拒绝
                "clarification_needed": bool,
                "suggested_questions": List[str]
            }
        """
        normalized_input = user_input.lower()

        # 1. 关键词匹配
        design_stats = self._analyze_keywords(normalized_input, self.DESIGN_KEYWORDS)
        non_design_stats = self._analyze_keywords(normalized_input, self.NON_DESIGN_KEYWORDS)

        design_strength = design_stats["strength"]
        non_design_strength = non_design_stats["strength"]

        logger.info(
            "📊 关键词命中: 设计=%s (hits=%s, categories=%s), 非设计=%s (hits=%s, categories=%s)",
            design_strength,
            design_stats["hits"],
            design_stats["categories"],
            non_design_strength,
            non_design_stats["hits"],
            non_design_stats["categories"]
        )
        
        # 2. LLM辅助判断
        llm_result = {"is_design": True, "confidence": 0.5, "categories": []}
        if self.llm_model:
            try:
                llm_result = self._llm_classify(user_input)
                logger.info(f"🤖 LLM判断: is_design={llm_result['is_design']}, confidence={llm_result.get('confidence', 0):.2f}")
            except Exception as e:
                logger.warning(f"⚠️ LLM分类失败: {e}")
        
        def _design_response(confidence: Optional[float] = None) -> Dict[str, Any]:
            final_conf = confidence if confidence is not None else self._compute_confidence(design_stats)
            matched_categories = list({*design_stats["categories"], *llm_result.get("categories", [])})
            return {
                "is_design_related": True,
                "confidence": round(final_conf, 2),
                "matched_categories": matched_categories
            }

        def _non_design_response(confidence: Optional[float] = None, reason: str = "输入内容不属于空间设计领域") -> Dict[str, Any]:
            final_conf = confidence if confidence is not None else self._compute_confidence(non_design_stats)
            return {
                "is_design_related": False,
                "confidence": round(final_conf, 2),
                "rejection_reason": reason,
                "matched_categories": non_design_stats["categories"],
                "detected_domain": non_design_stats["categories"][0] if non_design_stats["categories"] else "未知领域"
            }

        # 3. 综合决策
        # 🆕 规则0: 优先检查命名任务（不依赖LLM置信度）
        # ⚠️ 命名类任务视为设计相关（空间命名、品牌命名等）
        is_naming_task = any(kw in normalized_input for kw in ["命名", "起名", "取名", "名字", "叫什么"])

        if is_naming_task and design_strength >= 1:
            logger.info("🏷️ 检测到命名任务+设计关键词，放行处理")
            return _design_response(confidence=0.75)

        # 规则1: LLM明确判断为非设计类（高置信度）
        if not llm_result.get("is_design", True) and llm_result.get("confidence", 0) > 0.8:
            return _non_design_response(
                confidence=llm_result.get("confidence", 0.9),
                reason="LLM判断该内容不属于空间设计领域"
            )

        # 规则2: 非设计特征明显
        if non_design_strength >= 3 and design_strength == 0:
            return _non_design_response()
        if (
            non_design_strength >= 2
            and non_design_strength - design_strength >= 2
        ) or (
            non_design_strength >= 2
            and design_strength <= 2
            and len(design_stats["keywords"]) <= 1
        ):
            return _non_design_response()
        
        # 规则3: 设计特征明显
        if design_strength >= 3 and llm_result.get("is_design", True):
            confidence = max(
                self._compute_confidence(design_stats),
                llm_result.get("confidence", 0.0)
            )
            return _design_response(confidence)

        # 规则4: LLM高置信度判断为设计类（即使关键词得分低）
        # 修复：确保 confidence 是浮点数比较
        llm_confidence = float(llm_result.get("confidence", 0))
        if llm_result.get("is_design", True) and llm_confidence > 0.8:
            return _design_response(llm_confidence)

        # 规则5: 设计特征较弱但关键词有一定支持
        if design_strength >= 2 and llm_result.get("is_design", True):
            return _design_response()

        # 规则6: 边界情况，需要澄清
        return {
            "is_design_related": "unclear",
            "confidence": 0.5,
            "clarification_needed": True,
            "suggested_questions": [
                "您是否需要进行空间设计方面的分析？",
                "这个项目是否涉及建筑、室内或景观设计？",
                "您希望我帮您设计什么类型的空间？（如办公室、展厅、店铺等）"
            ]
        }
    
    def _analyze_keywords(self, text: str, keyword_dict: Dict[str, List[str]]) -> Dict[str, Any]:
        """分析关键词命中情况，返回命中统计数据"""
        categories = []
        matched_keywords = set()
        total_hits = 0

        for category, keywords in keyword_dict.items():
            hits = []
            for kw in keywords:
                kw_lower = kw.lower()
                if kw_lower and kw_lower in text:
                    hits.append(kw)

            if hits:
                categories.append(category)
                matched_keywords.update(hits)
                total_hits += len(hits)

        strength = total_hits + len(categories)

        return {
            "hits": total_hits,
            "categories": categories,
            "keywords": list(matched_keywords),
            "strength": strength
        }

    def _compute_confidence(self, stats: Dict[str, Any], base: float = 0.55) -> float:
        """根据命中情况计算置信度"""
        if stats["hits"] == 0 and not stats["categories"]:
            return 0.5

        confidence = base
        confidence += 0.1 * min(stats["hits"], 3)
        confidence += 0.05 * min(len(stats["categories"]), 4)

        return min(1.0, confidence)
    
    def _llm_classify(self, user_input: str) -> Dict[str, Any]:
        """使用LLM进行领域分类"""
        if not self.llm_model:
            return {"is_design": True, "confidence": 0.5, "categories": []}
        
        try:
            from langchain_core.messages import HumanMessage
            
            prompt = f"""你是空间设计领域分类专家。判断以下用户输入是否属于空间设计领域。

空间设计领域包括：
✅ 建筑设计、室内设计、景观设计
✅ 办公空间、零售空间、展厅空间、餐饮空间、住宅空间
✅ 空间规划、动线设计、装修方案
✅ 材料选择、色彩搭配、照明设计
✅ 家具布置、软装设计

不属于设计领域：
❌ 编程开发、医疗健康、法律金融
❌ 网站设计、APP设计（除非是展厅的数字界面）
❌ 平面设计、UI设计（除非与空间设计结合）

用户输入：
{user_input}

请以JSON格式输出：
{{
    "is_design": true/false,
    "confidence": 0.0-1.0,
    "categories": ["办公空间", "零售空间"等],
    "reasoning": "判断理由（50字内）"
}}

注意边界情况：
- "设计网站" → false（纯数字产品）
- "设计展厅的交互界面" → true（与空间设计结合）
- "办公室装修" → true（空间设计）
- "写代码" → false（编程）"""

            messages = [HumanMessage(content=prompt)]
            response = self.llm_model.invoke(messages)
            
            # 解析响应
            content = response.content if hasattr(response, 'content') else str(response)
            
            # 提取JSON
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result
            
            # 解析失败，返回保守结果
            return {"is_design": True, "confidence": 0.5, "categories": []}
            
        except Exception as e:
            logger.error(f"❌ LLM分类异常: {e}")
            return {"is_design": True, "confidence": 0.5, "categories": []}

    def _check_task_type_override(self, user_input: str) -> Optional[Dict[str, Any]]:
        """
        P0.2优化: 任务类型优先级判断（覆盖规则）

        某些任务类型无论描述多详细，复杂度都是固定的：
        - 命名类 → simple
        - 推荐类 → simple/medium

        解决问题：#22/#23 命名任务因含"文化"被误判为complex
        """
        text = user_input.lower()

        # 优先级1: 命名类（一票否决complex）
        naming_patterns = [
            r"[命名起名取名].*\d+[个间条]",  # 命名8间房
            r"\d+[个间条].*[命名起名取名]",  # 8间房命名（顺序相反）
            r"\d+个.*[名字命名]",
            r"门牌.*\d+个字"
        ]
        if any(re.search(p, text) for p in naming_patterns):
            # 即使含"文化"、"苏东坡"也判simple
            logger.info("🎯 任务类型覆盖: 检测到命名类任务，强制判定为simple")
            return {
                "complexity": "simple",
                "confidence": 0.9,
                "reasoning": "命名类任务（任务类型优先级覆盖）",
                "suggested_workflow": "quick_response",
                "suggested_experts": ["V3_叙事与体验专家_3-2", "V4_设计研究员_4-1"],
                "estimated_duration": "2-5分钟"
            }

        # 优先级2: 纯推荐类/列举类
        # 匹配: "需要10个概念主题", "给出10个设计概念", "推荐5个风格方案"等
        recommend_patterns = [
            r"推荐.*\d+个[主题概念风格方案]",  # 推荐10个主题
            r"给出.*\d+个[主题概念风格方案]",  # 给出10个概念
            r"需要\d+个.*[主题概念风格方案]",  # 需要10个概念主题
            r"\d+个.*[主题概念].*[主题概念]",  # 10个设计概念主题（中间可以有修饰词）
            r"\d+个[主题概念风格方案]"  #10个主题（紧凑版）
        ]
        if any(re.search(p, text) for p in recommend_patterns):
            logger.info("🎯 任务类型覆盖: 检测到推荐类任务，强制判定为simple")
            return {
                "complexity": "simple",
                "confidence": 0.85,
                "reasoning": "推荐类任务",
                "suggested_workflow": "quick_response",
                "suggested_experts": ["V4_设计研究员_4-1"],
                "estimated_duration": "2-5分钟"
            }

        return None  # 无覆盖，继续正常流程

    def assess_task_complexity(self, user_input: str) -> Dict[str, Any]:
        """
        评估任务复杂度，决定使用简单流程还是完整流程

        Args:
            user_input: 用户输入文本

        Returns:
            {
                "complexity": "simple" | "medium" | "complex",
                "confidence": float,
                "reasoning": str,
                "suggested_workflow": str,
                "suggested_experts": List[str],  # 🆕 推荐的专家组合
                "estimated_duration": str  # 预估时长
            }
        """
        # ========== P0.2优化: 任务类型优先级覆盖 ==========
        override_result = self._check_task_type_override(user_input)
        if override_result:
            return override_result

        text = user_input.lower()
        input_length = len(user_input)

        # ==================== 简单任务特征 ====================
        simple_patterns = {
            "命名类": [r"命名", r"起名", r"取名", r"叫什么", r"名字"],
            "推荐类": [r"推荐", r"建议", r"给我", r"列举", r"提供"],
            "数量限定": [r"\d+[个条种张份]", r"[几一二三四五六七八九十]+[个条种]"],
            "单一元素": [r"颜色", r"色彩", r"材质", r"字体", r"风格词", r"关键词"],
            "快速咨询": [r"什么是", r"如何理解", r"讲讲", r"解释"],
        }

        # ==================== 中等任务特征 ====================
        # 注意：面积大小不应影响复杂度，复杂度由需求维度决定
        medium_patterns = {
            "单一空间": [r"[一]个空间", r"[一]个房间", r"[一]个区域"],
            "功能明确": [r"接待区", r"会议室", r"茶室", r"书房", r"卧室"],
            "氛围营造": [r"氛围", r"感觉", r"调性", r"气质"],
            "改造优化": [r"改造", r"优化", r"提升", r"翻新"],
        }

        # ==================== 复杂项目特征 ====================
        # 注意：复杂度由技术难度、多系统、多空间、多维度决定，而非预算高低
        # 预算高只表示投资规模，不代表技术复杂
        complex_patterns = {
            # ========== 保留现有模式 ==========
            "多空间协调": [r"[2-9]个[空间房间包房]", r"多个[空间区域]", r"所有[房间空间]", r"整体[设计规划]", r"多空间联动"],
            "多系统集成": [r"智能化", r"中央空调", r"消防", r"弱电", r"机电", r"暖通", r"BIM", r"系统集成"],
            "复杂技术": [r"结构加固", r"承重", r"系统集成", r"联动", r"声学设计", r"特殊工艺"],
            "标准化复制": [r"连锁", r"标准化", r"复制", r"\d{2,}家店", r"落地手册", r"品牌连锁"],
            "多客群服务": [r"多种?客群", r"不同人群", r"多元用户", r"多类型用户", r"复合业态"],
            "文化维度": [r"文化", r"历史", r"传统", r"标杆", r"示范", r"城市更新", r"文化传承"],
            "跨领域协作": [r"跨界", r"融合", r"综合", r"一体化", r"全产业链"],

            # ========== 🆕 P0.1优化: 新增7个维度 ==========

            # 1. 大面积项目（解决#7/#15/#16误判）
            "大型项目面积": [
                r"\d{4,}[平方㎡]",  # 1000+平米
                r"\d+万[平方]?米",
                r"[2-9]\d{3}[平方㎡米]",  # 2000+
            ],

            # 2. 多功能复合（解决#15/#56误判）
            "多功能复合": [
                r"复合[空间业态功能]",
                r"[一]体化",
                r"综合[体业态功能]",
                r"兼顾.*兼顾",  # 多个"兼顾"
                r"多功能",
            ],

            # 3. 竞标/对标（解决#24/#16误判）
            "商业竞争": [
                r"竞标", r"投标", r"对标", r"对手", r"竞争",
                r"PK", r"差异化.*竞争", r"市场.*标杆"
            ],

            # 4. 特殊工艺技术（解决#45/#84/#85误判）
            "特殊技术工艺": [
                r"声学.*[系统设计]", r"隔音", r"绝对隔音", r"dB", r"杜比", r"全景声",
                r"供氧.*系统", r"弥散.*供氧", r"医疗级",
                r"防腐.*工艺", r"抗风.*构造", r"抗震.*加固",
                r"台风.*季", r"盐雾.*腐蚀", r"白蚁.*威胁",
                r"极端.*环境", r"海拔.*\d{4}"  # 高海拔
            ],

            # 5. 特殊用户需求（解决#6/#30/#49误判）
            "特殊用户群体": [
                r"自闭症", r"过敏.*症", r"失眠", r"焦虑",
                r"轮椅", r"无障碍", r"残疾", r"临终.*病房",
                r"婚姻.*危机", r"复合.*夫妻", r"再婚.*家庭",
                r"[3-9]代.*同堂", r"代际.*[关系交流]"
            ],

            # 6. 风格冲突/融合（解决#28/#29误判）
            # 重要：需要明确的融合/冲突关键词，避免误判简单的"涵盖多种风格"任务
            "风格冲突融合": [
                r"[中西新旧传统现代古典当代].*[融合结合].*[中西新旧传统现代古典当代]",  # 明确要求融合
                r"融合.*[风格文化]",  # 明确融合
                r"新旧.*[对撞碰撞]",  # 明确对撞
                r"[对撞碰撞].*[风格]",
                r"四合院.*[Ll]oft",  # 具体的冲突案例
                r"纽约.*[Ll]oft.*[中式传统四合院]",  # Loft+中式
                r"禅意.*派对"  # 具体的冲突案例
            ],

            # 7. 预算/时间约束（解决#76/#77/#83误判）
            "严格约束条件": [
                r"预算.*[有限紧张极低]",
                r"成本.*限制", r"低[成本预算].*高[要求品质]",
                r"3000元[\/每]平米", r"\d+万.*全包",  # 低预算标准
                r"工期.*\d+[天小时]", r"夜间.*施工",
                r"不闭店.*装修", r"快速.*[施工搭建]"
            ]
        }

        # 计算各维度得分
        simple_score = 0
        simple_matches = []
        for category, patterns in simple_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    simple_score += 1
                    simple_matches.append(category)
                    break  # 每个类别只计一次

        medium_score = 0
        medium_matches = []
        for category, patterns in medium_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    medium_score += 1
                    medium_matches.append(category)
                    break

        complex_score = 0
        complex_matches = []
        for category, patterns in complex_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    complex_score += 1
                    complex_matches.append(category)
                    break

        logger.info(f"📊 复杂度得分: 简单={simple_score}, 中等={medium_score}, 复杂={complex_score}")
        logger.info(f"   简单特征: {simple_matches}")
        logger.info(f"   中等特征: {medium_matches}")
        logger.info(f"   复杂特征: {complex_matches}")

        # ==================== 决策逻辑 ====================

        # 优先级1: 复杂项目的强特征（一票否决）
        if complex_score >= 2:
            return {
                "complexity": "complex",
                "confidence": 0.9,
                "reasoning": f"检测到复杂项目特征: {', '.join(complex_matches)}",
                "suggested_workflow": "full_analysis",
                "suggested_experts": ["all"],  # 完整流程
                "estimated_duration": "15-30分钟"
            }

        # 优先级2: 简单任务的明确特征
        # 重要：移除字数限制，只基于内容特征判断
        if simple_score >= 2 and complex_score == 0 and medium_score <= 1:
            # 智能推荐专家组合
            experts = self._recommend_experts_for_simple_task(user_input)
            return {
                "complexity": "simple",
                "confidence": 0.85,
                "reasoning": f"检测到简单任务特征: {', '.join(set(simple_matches))}",
                "suggested_workflow": "quick_response",
                "suggested_experts": experts,
                "estimated_duration": "2-5分钟"
            }

        # 优先级3: 中等复杂度
        if (medium_score >= 2 or (medium_score >= 1 and simple_score >= 1)) and complex_score <= 1:
            experts = self._recommend_experts_for_medium_task(user_input, medium_matches)
            return {
                "complexity": "medium",
                "confidence": 0.75,
                "reasoning": f"检测到中等任务特征: {', '.join(set(medium_matches))}",
                "suggested_workflow": "standard",
                "suggested_experts": experts,
                "estimated_duration": "6-12分钟"
            }

        # ========== P0.3+P0.4优化: 完全移除字数判定逻辑 ==========
        # 优先级4: 边界情况 - 有复杂特征
        # 重要原则：复杂度与描述长短无关，只与内容有关
        if complex_score >= 1:
            return {
                "complexity": "complex",
                "confidence": 0.8,  # 固定置信度，不受字数影响
                "reasoning": f"包含复杂特征: {', '.join(complex_matches)}",
                "suggested_workflow": "full_analysis",
                "suggested_experts": ["all"],
                "estimated_duration": "10-20分钟"
            }

        # 默认：中等复杂度（保守策略）
        return {
            "complexity": "medium",
            "confidence": 0.7,  # P0.4: 从0.6提高到0.7，减少不必要的二次验证
            "reasoning": "无法明确判断，使用标准流程确保质量",
            "suggested_workflow": "standard",
            "suggested_experts": ["v2", "v4", "v5"],  # 基础配置
            "estimated_duration": "8-15分钟"
        }

    def _recommend_experts_for_simple_task(self, user_input: str) -> List[str]:
        """
        为简单任务推荐专家组合

        🔥 重要：返回完整的角色ID（如 "V3_叙事与体验专家_3-2"），而不是简化ID（如 "v3"）
        这样可以确保与完整流程（ProjectDirector）选择相同的子角色，保持逻辑一致性

        参考 ProjectDirector 的"轻量级任务"配置：
        - 命名/主题策划/概念提炼 → V3_品牌叙事专家(3-2) + V4_设计研究员(4-1)
        """
        text = user_input.lower()
        experts = []

        # 命名、文化、诗词相关 → V3_品牌叙事专家(3-2) + V4_设计研究员(4-1)
        # 对应完整流程中 ProjectDirector 的"轻量级任务"配置
        if any(kw in text for kw in ["命名", "起名", "取名", "诗词", "诗意", "文化", "传统", "禅意", "意境"]):
            experts.extend([
                "V3_叙事与体验专家_3-2",  # 品牌叙事专家（擅长命名、品牌故事）
                "V4_设计研究员_4-1"        # 设计研究员（擅长案例对标）
            ])

        # 颜色、材质 → 暂时保留简化ID（需要确认V8配置后再更新）
        elif any(kw in text for kw in ["颜色", "色彩", "材质", "材料", "木材", "石材", "布料"]):
            experts.append("v8")
            # 如果提到文化风格，加上V4
            if any(kw in text for kw in ["中式", "日式", "禅", "茶室"]):
                experts.append("V4_设计研究员_4-1")

        # 风格解释 → V4
        elif any(kw in text for kw in ["什么是", "风格", "特点", "元素"]):
            experts.append("V4_设计研究员_4-1")

        # 关键词、主题词 → V3_品牌叙事专家
        elif any(kw in text for kw in ["关键词", "主题词", "描述词"]):
            experts.append("V3_叙事与体验专家_3-2")

        # 默认组合：品牌叙事 + 设计研究（与 ProjectDirector 一致）
        if not experts:
            experts = [
                "V3_叙事与体验专家_3-2",
                "V4_设计研究员_4-1"
            ]

        return experts

    def _recommend_experts_for_medium_task(self, user_input: str, medium_matches: List[str]) -> List[str]:
        """为中等任务推荐专家组合"""
        text = user_input.lower()
        experts = ["v2"]  # 中等任务必须有总监

        # 根据空间类型添加专家
        if any(kw in text for kw in ["咖啡", "餐厅", "茶室", "茶饮"]):
            experts.append("v10")  # 餐饮专家

        if any(kw in text for kw in ["办公", "工位", "会议室"]):
            experts.append("v7")  # 办公专家

        # 动线、分区
        if any(kw in text for kw in ["动线", "分区", "布局", "规划", "接待"]):
            experts.append("v5")  # 动线专家

        # 文化、风格
        if any(kw in text for kw in ["中式", "文化", "调性", "品牌", "氛围"]):
            experts.append("v4")  # 文化专家

        # 照明
        if any(kw in text for kw in ["灯光", "照明", "光线"]):
            experts.append("v6")  # 照明专家

        # 材质家具
        if any(kw in text for kw in ["材质", "家具", "软装"]):
            experts.append("v8")  # 材质专家

        # 确保至少3个专家
        if len(experts) < 3:
            if "v4" not in experts:
                experts.append("v4")
            if "v5" not in experts:
                experts.append("v5")

        return experts

