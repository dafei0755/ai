"""
问卷生成上下文

定义问卷生成所需的数据结构，替代直接访问 state 字典，提升可测试性。
"""

import re
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple
from loguru import logger


class KeywordExtractor:
    """
    智能关键词提取器

    从用户输入中提取关键概念、识别领域、检测用户提及的约束条件。
    用于生成针对性的问卷问题，避免通用模板问题。

    🔧 v7.4.1: 添加缓存机制，避免重复提取
    """

    # 🆕 缓存字典：{(user_input_hash, structured_data_hash): extraction_result}
    _cache: Dict[tuple, Dict[str, Any]] = {}
    _cache_max_size = 100  # 最大缓存条目数

    # 领域关键词库
    DOMAIN_KEYWORDS = {
        "tech_innovation": {
            "keywords": ["AI", "算法", "数据", "智能", "迭代", "敏捷", "模块化", "传感器",
                        "热力图", "物联网", "IoT", "自动化", "机器学习", "深度学习", "研发",
                        "科技", "互联网", "软件", "硬件", "芯片", "云计算", "大数据"],
            "label": "科技创新",
            "question_focus": ["技术实现路径", "数据驱动决策", "迭代周期", "协作模式"]
        },
        "hospitality": {
            "keywords": ["酒店", "客房", "大堂", "餐厅", "SPA", "度假", "民宿", "会所",
                        "宴会", "包房", "前台", "客服", "入住", "退房"],
            "label": "酒店餐饮",
            "question_focus": ["客户体验", "服务动线", "品牌调性", "运营效率"]
        },
        "office": {
            "keywords": ["办公", "工位", "会议室", "协作", "开放式", "独立办公", "共享办公",
                        "联合办公", "写字楼", "园区", "总部", "研发中心", "创业"],
            "label": "办公空间",
            "question_focus": ["工作模式", "协作需求", "专注需求", "企业文化"]
        },
        "retail": {
            "keywords": ["零售", "展示", "动线", "坪效", "门店", "旗舰店", "体验店",
                        "购物", "陈列", "橱窗", "收银", "仓储"],
            "label": "零售商业",
            "question_focus": ["客户动线", "展示效果", "品牌体验", "运营效率"]
        },
        "residential": {
            "keywords": ["住宅", "公寓", "别墅", "家", "居住", "卧室", "客厅", "厨房",
                        "卫生间", "阳台", "书房", "儿童房", "老人房"],
            "label": "住宅空间",
            "question_focus": ["生活方式", "家庭结构", "功能需求", "情感需求"]
        },
        "cultural_educational": {
            "keywords": ["学校", "教育", "培训", "图书馆", "博物馆", "展览", "艺术",
                        "文化", "画廊", "剧院", "音乐厅", "教室", "实验室"],
            "label": "文化教育",
            "question_focus": ["学习体验", "展示效果", "互动方式", "文化表达"]
        },
        "healthcare": {
            "keywords": ["医院", "诊所", "医疗", "健康", "康复", "养老", "护理",
                        "病房", "门诊", "手术室", "药房"],
            "label": "医疗健康",
            "question_focus": ["患者体验", "医疗流程", "安全卫生", "康复环境"]
        }
    }

    # 约束条件关键词
    CONSTRAINT_KEYWORDS = {
        "budget": ["预算", "成本", "费用", "万元", "投资", "造价", "报价", "价格", "经费"],
        "timeline": ["工期", "时间", "周期", "月", "天", "尽快", "紧急", "deadline", "交付"],
        "space": ["面积", "平米", "㎡", "平方", "空间不足", "有限", "狭小", "紧凑"],
        "regulation": ["规范", "消防", "物业", "审批", "合规", "标准", "法规"]
    }

    # 核心概念提取模式
    CONCEPT_PATTERNS = [
        r'"([^""]{2,20})"',  # 中文引号包裹的概念（左右引号配对）
        r'"([^"]{2,20})"',  # 英文引号包裹的概念
        r'「([^」]{2,20})」',  # 日式引号
        r'【([^】]{2,20})】',  # 方括号
        r'(?:具备|实现|打造|创建|设计)(?:一个)?[「"""]?([^，。,.\s""]{2,15})[」"""]?(?:的|属性|功能|特性)',  # 动词+概念
        r'(?:要求|需要|希望)[^，。]{0,10}([^，。,.\s""]{2,15})(?:的|属性|功能)',  # 需求+概念
    ]

    @classmethod
    def extract(cls, user_input: str, structured_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        从用户输入中提取关键信息

        Args:
            user_input: 用户原始输入文本
            structured_data: 需求分析师的结构化输出（可选）

        Returns:
            包含以下字段的字典：
            - keywords: 提取的关键词列表 [(keyword, weight), ...]
            - domain: 识别的领域 {"type": str, "label": str, "confidence": float}
            - core_concepts: 核心概念列表
            - user_mentioned_constraints: 用户提及的约束类型列表
            - question_focus: 建议的问题聚焦方向
        """
        if not user_input:
            return cls._empty_result()

        # 🆕 v7.4.1: 检查缓存
        cache_key = cls._generate_cache_key(user_input, structured_data)
        if cache_key in cls._cache:
            logger.debug(f"🔍 [KeywordExtractor] 使用缓存结果 (cache_key={cache_key[:16]}...)")
            return cls._cache[cache_key]

        # 1. 提取关键词（使用简单的词频+位置权重，避免依赖jieba）
        keywords = cls._extract_keywords_simple(user_input)

        # 2. 识别领域
        domain = cls._identify_domain(user_input, keywords)

        # 3. 提取核心概念
        core_concepts = cls._extract_core_concepts(user_input, structured_data)

        # 4. 检测用户提及的约束
        mentioned_constraints = cls._detect_constraints(user_input)

        # 5. 确定问题聚焦方向
        question_focus = cls._determine_question_focus(domain, core_concepts)

        result = {
            "keywords": keywords,
            "domain": domain,
            "core_concepts": core_concepts,
            "user_mentioned_constraints": mentioned_constraints,
            "question_focus": question_focus
        }

        logger.info(f"🔍 [KeywordExtractor] 领域识别: {domain['label']} (置信度: {domain['confidence']:.2f})")
        logger.info(f"🔍 [KeywordExtractor] 核心概念: {core_concepts[:5]}")
        logger.info(f"🔍 [KeywordExtractor] 用户约束: {mentioned_constraints}")

        # 🆕 v7.4.1: 存储到缓存
        cls._store_in_cache(cache_key, result)

        return result

    @classmethod
    def _generate_cache_key(cls, user_input: str, structured_data: Optional[Dict]) -> tuple:
        """
        生成缓存键

        Args:
            user_input: 用户输入
            structured_data: 结构化数据

        Returns:
            缓存键元组
        """
        import hashlib
        import json

        # 对 user_input 生成哈希
        input_hash = hashlib.md5(user_input.encode('utf-8')).hexdigest()

        # 对 structured_data 生成哈希（仅使用关键字段）
        if structured_data:
            # 只使用影响提取结果的关键字段
            key_fields = {
                "design_challenge": structured_data.get("design_challenge", ""),
                "project_task": structured_data.get("project_task", "")
            }
            data_str = json.dumps(key_fields, sort_keys=True, ensure_ascii=False)
            data_hash = hashlib.md5(data_str.encode('utf-8')).hexdigest()
        else:
            data_hash = "none"

        return (input_hash, data_hash)

    @classmethod
    def _store_in_cache(cls, cache_key: tuple, result: Dict[str, Any]) -> None:
        """
        存储结果到缓存

        Args:
            cache_key: 缓存键
            result: 提取结果
        """
        # 如果缓存已满，移除最旧的条目（FIFO）
        if len(cls._cache) >= cls._cache_max_size:
            # 移除第一个条目
            first_key = next(iter(cls._cache))
            del cls._cache[first_key]
            logger.debug(f"🔍 [KeywordExtractor] 缓存已满，移除最旧条目")

        cls._cache[cache_key] = result
        logger.debug(f"🔍 [KeywordExtractor] 结果已缓存 (cache_size={len(cls._cache)})")

    @classmethod
    def _extract_keywords_simple(cls, text: str) -> List[Tuple[str, float]]:
        """简单关键词提取（不依赖jieba）"""
        keywords = []

        # 从所有领域关键词中匹配
        for domain_info in cls.DOMAIN_KEYWORDS.values():
            for kw in domain_info["keywords"]:
                if kw.lower() in text.lower():
                    # 权重：出现位置越靠前权重越高
                    pos = text.lower().find(kw.lower())
                    weight = 1.0 - (pos / len(text)) * 0.5
                    keywords.append((kw, weight))

        # 提取引号内的词作为高权重关键词
        quoted_patterns = [
            r'"([^""]{2,20})"',  # 中文引号（左右配对）
            r'"([^"]{2,20})"',   # 英文引号
            r'「([^」]{2,20})」',  # 日式引号
            r'【([^】]{2,20})】'   # 方括号
        ]
        for pattern in quoted_patterns:
            try:
                matches = re.findall(pattern, text)
                for match in matches:
                    # 清理匹配结果，去除残留引号
                    clean_match = match.strip().strip('"').strip('"').strip('"')
                    if clean_match and len(clean_match) >= 2 and clean_match not in [k[0] for k in keywords]:
                        keywords.append((clean_match, 1.0))
            except re.error as e:
                logger.warning(f"⚠️ Regex error in keyword extraction (pattern: {pattern}): {e}")
                continue
            except Exception as e:
                logger.error(f"❌ Unexpected error in keyword extraction: {e}")
                continue

        # 按权重排序
        keywords.sort(key=lambda x: x[1], reverse=True)
        return keywords[:15]

    @classmethod
    def _identify_domain(cls, text: str, keywords: List[Tuple[str, float]]) -> Dict[str, Any]:
        """识别项目领域"""
        domain_scores = {}

        for domain_type, domain_info in cls.DOMAIN_KEYWORDS.items():
            score = 0
            matched_keywords = []
            for kw in domain_info["keywords"]:
                if kw.lower() in text.lower():
                    score += 1
                    matched_keywords.append(kw)

            if score > 0:
                domain_scores[domain_type] = {
                    "score": score,
                    "matched": matched_keywords,
                    "label": domain_info["label"],
                    "question_focus": domain_info["question_focus"]
                }

        if not domain_scores:
            return {"type": "general", "label": "通用", "confidence": 0.3, "question_focus": []}

        # 选择得分最高的领域
        best_domain = max(domain_scores.items(), key=lambda x: x[1]["score"])
        confidence = min(best_domain[1]["score"] / 5, 1.0)  # 5个关键词以上为满分

        return {
            "type": best_domain[0],
            "label": best_domain[1]["label"],
            "confidence": confidence,
            "matched_keywords": best_domain[1]["matched"],
            "question_focus": best_domain[1]["question_focus"]
        }

    @classmethod
    def _extract_core_concepts(cls, text: str, structured_data: Optional[Dict]) -> List[str]:
        """提取核心概念"""
        concepts = []

        # 从正则模式提取
        for pattern in cls.CONCEPT_PATTERNS:
            try:
                matches = re.findall(pattern, text)
                concepts.extend(matches)
            except re.error as e:
                logger.warning(f"⚠️ Regex error in concept extraction (pattern: {pattern[:50]}...): {e}")
                continue
            except Exception as e:
                logger.error(f"❌ Unexpected error in concept extraction: {e}")
                continue

        # 从结构化数据补充
        if structured_data:
            # 从 design_challenge 提取
            design_challenge = structured_data.get("design_challenge", "")
            if design_challenge:
                # 提取 [xxx] 格式的概念
                bracket_matches = re.findall(r'\[([^\]]{2,20})\]', design_challenge)
                concepts.extend(bracket_matches)

            # 从 project_task 提取
            project_task = structured_data.get("project_task", "")
            if project_task:
                bracket_matches = re.findall(r'\[([^\]]{2,20})\]', project_task)
                concepts.extend(bracket_matches)

        # 去重并保持顺序，清理残留引号
        seen = set()
        unique_concepts = []
        for c in concepts:
            # 清理残留引号和空白
            c_clean = c.strip().strip('"').strip('"').strip('"').strip('「').strip('」').strip()
            # 过滤无效概念
            if (c_clean
                and c_clean not in seen
                and len(c_clean) >= 2
                and not c_clean.endswith('"')  # 排除不完整的引号
                and not c_clean.startswith('"')):
                seen.add(c_clean)
                unique_concepts.append(c_clean)

        return unique_concepts[:10]

    @classmethod
    def _detect_constraints(cls, text: str) -> List[str]:
        """检测用户提及的约束条件"""
        mentioned = []

        for constraint_type, keywords in cls.CONSTRAINT_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    if constraint_type not in mentioned:
                        mentioned.append(constraint_type)
                    break

        return mentioned

    @classmethod
    def _determine_question_focus(cls, domain: Dict, core_concepts: List[str]) -> List[str]:
        """确定问题聚焦方向"""
        focus = domain.get("question_focus", []).copy()

        # 根据核心概念补充聚焦方向
        concept_focus_map = {
            "迭代": "迭代周期与灵活性",
            "模块化": "模块化程度与重组方式",
            "数据": "数据驱动决策",
            "智能": "智能化程度",
            "协作": "协作模式",
            "体验": "用户体验优先级",
            "品牌": "品牌表达方式"
        }

        for concept in core_concepts:
            for key, focus_item in concept_focus_map.items():
                if key in concept and focus_item not in focus:
                    focus.append(focus_item)

        return focus[:6]

    @classmethod
    def _empty_result(cls) -> Dict[str, Any]:
        """返回空结果"""
        return {
            "keywords": [],
            "domain": {"type": "general", "label": "通用", "confidence": 0.0, "question_focus": []},
            "core_concepts": [],
            "user_mentioned_constraints": [],
            "question_focus": []
        }


@dataclass
class QuestionContext:
    """
    问卷生成上下文

    封装问卷生成所需的所有数据，避免直接依赖 ProjectAnalysisState，
    使生成器可以独立测试。

    Attributes:
        project_task: 项目任务描述
        character_narrative: 角色叙事
        design_challenge: 设计挑战
        core_tension: 核心矛盾
        resource_constraints: 资源约束
        project_type: 项目类型 (personal_residential/hybrid_residential_commercial/commercial_enterprise)
        expert_handoff: 专家交接数据
        user_input: 用户原始输入
        structured_data: 完整的结构化数据（用于复杂场景）
        extracted_info: 🆕 智能提取的关键信息（领域、关键词、核心概念、用户约束）
    """

    project_task: str = ""
    character_narrative: str = ""
    design_challenge: str = ""
    core_tension: str = ""
    resource_constraints: str = ""
    project_type: str = ""
    expert_handoff: Dict[str, Any] = None
    user_input: str = ""
    structured_data: Dict[str, Any] = None
    extracted_info: Dict[str, Any] = None  # 🆕 智能提取的关键信息

    def __post_init__(self):
        """初始化默认值"""
        if self.expert_handoff is None:
            self.expert_handoff = {}
        if self.structured_data is None:
            self.structured_data = {}
        if self.extracted_info is None:
            self.extracted_info = {}

    @classmethod
    def from_state(cls, state: Dict[str, Any]) -> "QuestionContext":
        """
        从 ProjectAnalysisState 构建上下文

        Args:
            state: 项目分析状态字典

        Returns:
            QuestionContext 实例
        """
        agent_results = state.get("agent_results", {})
        requirements_result = agent_results.get("requirements_analyst", {})
        structured_data = requirements_result.get("structured_data", {})
        user_input = state.get("user_input", "")

        # 🆕 智能提取关键信息
        extracted_info = KeywordExtractor.extract(user_input, structured_data)

        return cls(
            project_task=structured_data.get("project_task", ""),
            character_narrative=structured_data.get("character_narrative", ""),
            design_challenge=structured_data.get("design_challenge", ""),
            core_tension=structured_data.get("core_tension", ""),
            resource_constraints=structured_data.get("resource_constraints", ""),
            project_type=structured_data.get("project_type", ""),
            expert_handoff=structured_data.get("expert_handoff", {}),
            user_input=user_input,
            structured_data=structured_data,
            extracted_info=extracted_info
        )

    # 🆕 便捷属性访问
    @property
    def domain(self) -> Dict[str, Any]:
        """获取识别的领域信息"""
        return self.extracted_info.get("domain", {"type": "general", "label": "通用"})

    @property
    def keywords(self) -> List[Tuple[str, float]]:
        """获取提取的关键词"""
        return self.extracted_info.get("keywords", [])

    @property
    def core_concepts(self) -> List[str]:
        """获取核心概念"""
        return self.extracted_info.get("core_concepts", [])

    @property
    def user_mentioned_constraints(self) -> List[str]:
        """获取用户提及的约束类型"""
        return self.extracted_info.get("user_mentioned_constraints", [])

    @property
    def question_focus(self) -> List[str]:
        """获取建议的问题聚焦方向"""
        return self.extracted_info.get("question_focus", [])
