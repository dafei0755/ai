"""
搜索策略生成器

根据客户要求：
- 每位专家都有明确的任务，而不是自己随意搜索
- 各专家的搜索，均需要独立的策略
- 搜索关键词应该根据项目需求动态生成
"""

from typing import Dict, Any, Optional
from loguru import logger
from langchain_core.messages import SystemMessage, HumanMessage
import json


class SearchStrategyGenerator:
    """搜索策略生成器 - 为专家生成独立的搜索策略"""

    def __init__(self, llm_model=None):
        """
        初始化搜索策略生成器

        Args:
            llm_model: LLM模型实例（用于动态生成搜索查询）
        """
        self.llm_model = llm_model

    def generate_queries(
        self,
        agent_type: str,
        project_task: str,
        character_narrative: str,
        assigned_task: str,
        project_type: str = "auto"
    ) -> Dict[str, str]:
        """
        根据项目信息和分配的任务，动态生成搜索查询

        Args:
            agent_type: 专家类型 (V2, V3, V4, V5, V6)
            project_task: 项目任务描述
            character_narrative: 人物叙事
            assigned_task: 项目总监分配的任务
            project_type: 项目类型 (auto/interior_design/software/product)

        Returns:
            搜索查询字典
        """
        # 自动检测项目类型
        if project_type == "auto":
            project_type = self._detect_project_type(project_task)

        # 提取关键词
        keywords = self._extract_keywords(
            project_task,
            character_narrative
        )

        # 根据专家类型生成查询
        if agent_type == "V2":
            return self._generate_v2_queries(
                project_type, keywords, assigned_task
            )
        elif agent_type == "V3":
            return self._generate_v3_queries(
                project_type, keywords, assigned_task
            )
        elif agent_type == "V4":
            return self._generate_v4_queries(
                project_type, keywords, assigned_task
            )
        elif agent_type == "V5":
            return self._generate_v5_queries(
                project_type, keywords, assigned_task
            )
        elif agent_type == "V6":
            return self._generate_v6_queries(
                project_type, keywords, assigned_task
            )
        else:
            logger.warning(f"Unknown agent type: {agent_type}, using default queries")
            return self._generate_default_queries(
                project_type, keywords, assigned_task
            )
    
    def _detect_project_type(self, project_task: str) -> str:
        """检测项目类型"""
        task_lower = project_task.lower()

        if any(keyword in task_lower for keyword in ["室内设计", "空间设计", "住宅", "商业", "办公", "餐饮", "零售", "装修", "interior", "commercial"]):
            return "interior_design"
        elif any(keyword in task_lower for keyword in ["软件", "应用", "app", "系统", "平台", "software"]):
            return "software"
        elif any(keyword in task_lower for keyword in ["产品", "product", "服务", "service"]):
            return "product"
        else:
            return "general"

    def _extract_keywords(self, project_task: str, character_narrative: str) -> Dict[str, Any]:
        """提取关键词 - 使用LLM动态提取"""
        # 如果没有LLM,使用降级方案
        if not self.llm_model:
            logger.warning("No LLM model available, using fallback keyword extraction")
            return self._extract_keywords_fallback(project_task, character_narrative)

        try:
            # 使用LLM动态提取关键词
            prompt = f"""基于以下项目信息,提取关键词并分类。

项目任务: {project_task}

人物叙事: {character_narrative}

请提取以下4类关键词:
1. style: 设计风格(如现代、简约、优雅、工业、北欧、中式、日式等)
2. target_user: 目标用户(如独立女性、家庭、企业、年轻白领、青少年等)
3. features: 项目特征(如商业街区、零售空间、餐饮娱乐、住宅、办公等)
4. emotions: 情感关键词(如温馨、舒适、私密、自由、归属感等)

以JSON格式输出,格式如下:
{{
    "style": ["现代", "简约"],
    "target_user": ["家庭", "年轻白领"],
    "features": ["商业街区", "零售空间", "餐饮"],
    "emotions": ["活力", "舒适"]
}}

注意:
- 每类关键词2-5个即可
- 关键词要具体、精准
- 如果某类没有相关信息,返回空数组[]
"""

            messages = [
                SystemMessage(content="你是一个专业的设计关键词提取专家,擅长从项目描述中提取分类关键词。"),
                HumanMessage(content=prompt)
            ]

            response = self.llm_model.invoke(messages, max_tokens=300, temperature=0.3)

            # 解析JSON响应
            content = response.content.strip()
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1

            if start_idx != -1 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                keywords = json.loads(json_str)
                logger.info(f"LLM extracted keywords: {keywords}")
                return keywords
            else:
                logger.warning("Failed to parse LLM response, using fallback")
                return self._extract_keywords_fallback(project_task, character_narrative)

        except Exception as e:
            logger.error(f"LLM keyword extraction failed: {e}, using fallback")
            return self._extract_keywords_fallback(project_task, character_narrative)

    def _extract_keywords_fallback(self, project_task: str, character_narrative: str) -> Dict[str, Any]:
        """关键词提取降级方案 - 基于规则的简单匹配"""
        keywords = {
            "style": [],
            "target_user": [],
            "features": [],
            "emotions": []
        }

        # 扩展的风格关键词
        style_patterns = [
            "Audrey Hepburn", "赫本", "优雅", "简约", "现代", "古典", "工业", "北欧",
            "中式", "日式", "欧式", "美式", "轻奢", "混搭",
            "minimalist", "elegant", "modern", "classic"
        ]
        for pattern in style_patterns:
            if pattern in project_task or pattern in character_narrative:
                keywords["style"].append(pattern)

        # 扩展的目标用户关键词
        user_patterns = [
            "独立女性", "海归", "专业人士", "年轻人", "家庭", "企业",
            "白领", "青少年", "儿童", "老人", "情侣",
            "independent woman", "professional", "family"
        ]
        for pattern in user_patterns:
            if pattern in project_task or pattern in character_narrative:
                keywords["target_user"].append(pattern)

        # 新增: 项目特征关键词
        feature_patterns = [
            "商业", "住宅", "办公", "餐饮", "零售", "娱乐", "酒店", "展厅",
            "商业街区", "购物中心", "写字楼", "公寓", "别墅"
        ]
        for pattern in feature_patterns:
            if pattern in project_task or pattern in character_narrative:
                keywords["features"].append(pattern)

        # 扩展的情感关键词
        emotion_patterns = [
            "归属感", "私密", "温馨", "舒适", "自由", "独立",
            "活力", "时尚", "品质", "优雅",
            "belonging", "privacy", "comfort", "freedom"
        ]
        for pattern in emotion_patterns:
            if pattern in project_task or pattern in character_narrative:
                keywords["emotions"].append(pattern)

        return keywords
    
    def _generate_v2_queries(
        self,
        project_type: str,
        keywords: Dict[str, Any],
        assigned_task: str
    ) -> Dict[str, str]:
        """生成V2设计研究分析师的搜索查询"""
        queries = {}
        
        if project_type == "interior_design":
            # 室内设计项目
            style_str = " ".join(keywords["style"][:3])
            user_str = " ".join(keywords["target_user"][:2])
            
            queries["design_trends"] = f"室内设计趋势 {style_str} {user_str} 2024"
            queries["academic_research"] = f"interior design residential space {style_str}"
            queries["knowledge_base"] = f"室内设计指南 {style_str} 最佳实践"
        else:
            # 软件/产品设计项目
            queries["design_trends"] = f"UI UX design trends 2024 {' '.join(keywords['style'][:2])}"
            queries["academic_research"] = f"user experience design interface {' '.join(keywords['target_user'][:2])}"
            queries["knowledge_base"] = f"design guidelines best practices {assigned_task[:50]}"
        
        return queries
    
    def _generate_v3_queries(
        self,
        project_type: str,
        keywords: Dict[str, Any],
        assigned_task: str
    ) -> Dict[str, str]:
        """生成V3技术架构师的搜索查询"""
        queries = {}
        
        if project_type == "interior_design":
            # 室内设计项目 - 关注智能家居、照明、材料等技术
            queries["tech_trends"] = f"智能家居系统 照明控制 2024"
            queries["academic_research"] = f"smart home automation lighting control"
            queries["knowledge_base"] = f"智能家居技术 最佳实践"
        else:
            # 软件项目
            queries["tech_trends"] = f"software architecture patterns microservices 2024"
            queries["academic_research"] = f"software engineering architecture scalability"
            queries["knowledge_base"] = f"architecture patterns best practices {assigned_task[:50]}"
        
        return queries
    
    def _generate_v4_queries(
        self,
        project_type: str,
        keywords: Dict[str, Any],
        assigned_task: str
    ) -> Dict[str, str]:
        """生成V4用户体验设计师的搜索查询"""
        queries = {}
        
        user_str = " ".join(keywords["target_user"][:2])
        emotion_str = " ".join(keywords["emotions"][:2])
        
        if project_type == "interior_design":
            queries["ux_trends"] = f"居住体验设计 {user_str} {emotion_str} 2024"
            queries["case_studies"] = f"residential UX design {user_str} case studies"
            queries["knowledge_base"] = f"用户体验设计 居住空间 {emotion_str}"
        else:
            queries["ux_trends"] = f"UX design trends 2024 {user_str}"
            queries["case_studies"] = f"UX case studies user experience design {user_str}"
            queries["knowledge_base"] = f"用户体验设计 交互设计 {assigned_task[:50]}"
        
        return queries
    
    def _generate_v5_queries(
        self,
        project_type: str,
        keywords: Dict[str, Any],
        assigned_task: str
    ) -> Dict[str, str]:
        """生成V5商业分析师的搜索查询"""
        queries = {}
        
        user_str = " ".join(keywords["target_user"][:2])
        
        if project_type == "interior_design":
            queries["market_trends"] = f"室内设计市场趋势 {user_str} 2024"
            queries["competitor_analysis"] = f"interior design market analysis {user_str}"
            queries["revenue_models"] = f"室内设计商业模式 盈利模式"
        else:
            queries["market_trends"] = f"market trends business model 2024 {user_str}"
            queries["competitor_analysis"] = f"competitor analysis market research {user_str}"
            queries["revenue_models"] = f"revenue model monetization strategy"
        
        return queries
    
    def _generate_v6_queries(
        self,
        project_type: str,
        keywords: Dict[str, Any],
        assigned_task: str
    ) -> Dict[str, str]:
        """生成V6实施规划师的搜索查询"""
        queries = {}
        
        if project_type == "interior_design":
            queries["project_management"] = f"室内设计项目管理 施工流程 2024"
            queries["methodology"] = f"interior design project planning methodology"
            queries["risk_management"] = f"室内设计项目风险管理"
        else:
            queries["project_management"] = f"project management best practices 2024"
            queries["methodology"] = f"agile development DevOps implementation methodology"
            queries["risk_management"] = f"project risk management mitigation strategies"
        
        return queries
    
    def _generate_default_queries(
        self,
        project_type: str,
        keywords: Dict[str, Any],
        assigned_task: str
    ) -> Dict[str, str]:
        """生成默认搜索查询"""
        return {
            "general": f"{assigned_task[:100]} 2024",
            "research": f"{' '.join(keywords['style'][:2])} best practices",
            "knowledge_base": f"{assigned_task[:100]}"
        }

