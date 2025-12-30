"""
策略生成服务 - 统一处理专家工作策略预览

提供配置驱动的策略生成，消除V2/V6重复逻辑
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from loguru import logger
from langchain_core.messages import SystemMessage, HumanMessage
import json


@dataclass
class ExpertConfig:
    """专家配置数据类"""
    prefix: str  # "V2_", "V6_"
    name: str  # "设计总监", "专业总工程师"
    agent_type: str  # "v2_design_research", "v6_implementation_plan"
    tools: List[str]  # ["ragflow"], ["tavily", "arxiv", "ragflow"]
    duration: str  # "30-40秒", "40-60秒"
    work_focus_description: str  # 工作重点描述（用于LLM生成）


class StrategyGenerator:
    """策略生成服务 - 统一处理V2/V6策略生成"""

    # 配置驱动：所有专家类型的配置（支持动态批次调度）
    # 2025-11-18 更新：添加 V3/V4/V5 支持，解决 KeyError 问题
    EXPERT_CONFIGS = {
        "V3": ExpertConfig(
            prefix="V3_",
            name="叙事与体验专家",
            agent_type="v3_narrative_expert",
            tools=["tavily", "ragflow"],
            duration="30-40秒",
            work_focus_description="基于第一批专家的分析结果，深化叙事与体验设计，构建人物画像和用户旅程，设计情感触点和体验节点"
        ),
        "V4": ExpertConfig(
            prefix="V4_",
            name="设计研究员",
            agent_type="v4_design_researcher",
            tools=["tavily", "arxiv", "ragflow"],
            duration="30-40秒",
            work_focus_description="基于第一批专家的分析结果，进行深度设计研究，研究设计方法论和前沿趋势，分析相关学术文献和行业案例"
        ),
        "V5": ExpertConfig(
            prefix="V5_",
            name="场景与行业专家",
            agent_type="v5_scenario_expert",
            tools=["tavily", "ragflow"],
            duration="30-40秒",
            work_focus_description="基于第一批专家的分析结果，深化场景与行业分析，研究行业趋势和市场动态，分析目标用户场景和使用模式"
        ),
        "V2": ExpertConfig(
            prefix="V2_",
            name="设计总监",
            agent_type="v2_design_director",
            tools=["ragflow"],
            duration="30-40秒",
            work_focus_description="基于第一批专家的分析结果，进行深度设计研究，分析当前设计趋势和最佳实践，综合多方信息提供设计方案建议"
        ),
        "V6": ExpertConfig(
            prefix="V6_",
            name="专业总工程师",
            agent_type="v6_chief_engineer",
            tools=["tavily", "arxiv", "ragflow"],
            duration="40-60秒",
            work_focus_description="基于第一批专家的分析结果，制定实施规划，研究项目管理和实施方法论，分析技术实施路径和资源需求"
        )
    }

    def __init__(self, role_manager, llm_model=None):
        """
        初始化策略生成器

        Args:
            role_manager: 角色管理器实例
            llm_model: LLM模型实例（用于动态生成搜索查询）
        """
        self.role_manager = role_manager
        self.llm_model = llm_model

    def generate_strategy_preview(
        self,
        expert_type: str,  # "V2" or "V6"
        agent_results: Dict[str, Any],
        project_task: str,
        character_narrative: str,
        state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        统一的策略生成方法 - 替代_generate_v2_strategy_preview和_generate_v6_strategy_preview

        通过expert_type参数区分V2/V6，逻辑完全共享

        Args:
            expert_type: 专家类型（"V2" 或 "V6"）
            agent_results: 第一批专家的结果
            project_task: 项目任务描述
            character_narrative: 人物叙事
            state: 当前状态

        Returns:
            专家的工作策略预览
        """
        config = self.EXPERT_CONFIGS[expert_type]

        # 1. 动态获取角色名称（通用逻辑）
        agent_name = self._get_expert_name(expert_type, state, config)

        # 2. 提取第一批专家的关键洞察（通用逻辑）
        dependencies, available_deps = self._extract_dependencies(agent_results)

        # 3. 生成搜索查询（通用逻辑，传入expert_type）
        search_queries = self._generate_search_queries(
            expert_type, project_task, character_narrative
        )

        # 4. 生成工作重点（动态生成）
        work_focus = self._generate_work_focus(
            expert_type, config, available_deps, 
            project_task, character_narrative, dependencies
        )

        return {
            "agent_name": agent_name,
            "agent_type": config.agent_type,
            "dependencies": dependencies,
            "dependency_list": available_deps,
            "search_queries": search_queries,
            "work_focus": work_focus,
            "tools_to_use": config.tools,
            "estimated_duration": config.duration
        }

    def _get_expert_name(self, expert_type: str, state: Dict[str, Any], config: ExpertConfig) -> str:
        """动态获取专家名称"""
        active_agents = state.get("active_agents", [])
        role_id = next((r for r in active_agents if r.startswith(config.prefix)), None)

        if role_id:
            try:
                # ✅ 使用 parse_full_role_id 正确解析完整角色ID
                base_type, role_id_num = self.role_manager.parse_full_role_id(role_id)
                role_config = self.role_manager.get_role_config(base_type, role_id_num)
                if role_config:
                    return role_config.get("name", config.name)
            except Exception as e:
                logger.warning(f"⚠️ 获取 {expert_type} 角色配置失败: {e}")

        return config.name

    def _extract_dependencies(self, agent_results: Dict[str, Any]) -> tuple:
        """提取依赖（通用逻辑）"""
        dependencies = {}
        available_deps = []

        for prefix in ["V3", "V4", "V5"]:
            key = next((k for k in agent_results.keys() if k.startswith(f"{prefix}_")), None)
            if key:
                dependencies[key] = self._extract_agent_insights(agent_results, key, prefix)
                available_deps.append(prefix)

        if not dependencies:
            dependencies["_no_dependencies"] = {"available": False, "note": "第一批专家未执行"}

        return dependencies, available_deps

    def _extract_agent_insights(
        self,
        agent_results: Dict[str, Any],
        agent_key: str,
        agent_label: str
    ) -> Dict[str, Any]:
        """提取单个专家的关键洞察"""
        if agent_key not in agent_results:
            return {
                "available": False,
                "message": f"{agent_label}分析结果未找到"
            }

        result = agent_results[agent_key]
        confidence = result.get("confidence", 0)

        # 从structured_data中提取关键发现
        key_findings = self._extract_key_findings_from_structured_data(result)
        top_findings = key_findings[:3] if isinstance(key_findings, list) else []

        return {
            "available": True,
            "confidence": f"{confidence:.0%}",
            "key_findings_count": len(key_findings),
            "top_findings": top_findings,
            "summary": f"已完成，置信度{confidence:.0%}，包含{len(key_findings)}个关键发现"
        }

    def _extract_key_findings_from_structured_data(self, result: Dict[str, Any]) -> List[str]:
        """从智能体结果的structured_data中提取关键发现"""
        key_findings = []
        structured_data = result.get("structured_data", {})

        if not isinstance(structured_data, dict):
            return key_findings

        # 提取前5个关键字段作为关键发现
        count = 0
        for key, value in structured_data.items():
            if count >= 5:
                break

            if key in ["raw_analysis", "tool_insights"]:
                continue

            if isinstance(value, dict):
                sub_items = list(value.items())[:2]
                if sub_items:
                    finding = f"{key}: " + ", ".join([f"{k}={str(v)[:50]}" for k, v in sub_items])
                    key_findings.append(finding)
                    count += 1
            elif isinstance(value, list):
                if value:
                    finding = f"{key}: " + ", ".join([str(item)[:50] for item in value[:2]])
                    key_findings.append(finding)
                    count += 1
            elif isinstance(value, str) and len(value) > 10:
                finding = f"{key}: {str(value)[:100]}"
                key_findings.append(finding)
                count += 1

        return key_findings

    def _generate_work_focus(
        self,
        expert_type: str,
        config: ExpertConfig,
        available_deps: List[str],
        project_task: str,
        character_narrative: str,
        dependencies: Dict[str, Any]
    ) -> List[str]:
        """生成工作重点 - 使用LLM动态生成"""
        if not self.llm_model:
            # 降级方案：使用通用描述
            deps_str = "、".join(available_deps) if available_deps else "项目需求"
            return [
                f"基于{deps_str}的分析结果，{config.work_focus_description}",
                "研究相关领域的最新趋势和最佳实践",
                "整合多方信息形成专业建议"
            ]

        try:
            # 构建依赖信息摘要
            deps_summary = ""
            if available_deps:
                deps_summary = "\n".join([
                    f"- {dep}: {dependencies.get(f'{dep}_', {}).get('summary', '已完成分析')}"
                    for dep in available_deps
                ])
            else:
                deps_summary = "无（第一批专家未执行）"

            prompt = f"""你是{config.name}，需要为当前项目生成3-5条具体的工作重点。

项目任务: {project_task}

人物叙事: {character_narrative}

第一批专家分析结果:
{deps_summary}

你的职责: {config.work_focus_description}

请生成3-5条具体的工作重点，要求：
1. 根据项目具体情况调整，不要通用表述
2. 如果有第一批专家结果，明确说明如何基于其结果深化
3. 包含具体的关键词和方向
4. 每条工作重点30-50字

输出JSON格式：
{{
  "work_focus": ["工作重点1", "工作重点2", "..."]
}}
"""

            messages = [
                SystemMessage(content=f"你是{config.name}，擅长根据项目需求制定具体的工作计划。"),
                HumanMessage(content=prompt)
            ]

            response = self.llm_model.invoke(messages, max_tokens=400, temperature=0.4)
            content = response.content.strip()
            
            # 解析JSON
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                result = json.loads(json_str)
                work_focus = result.get("work_focus", [])
                
                if work_focus and len(work_focus) >= 3:
                    logger.info(f"LLM generated {len(work_focus)} work focus items for {expert_type}")
                    return work_focus
            
            # 解析失败，使用降级方案
            logger.warning("Failed to parse work focus, using fallback")
            
        except Exception as e:
            logger.error(f"LLM work focus generation failed: {e}, using fallback")
        
        # 降级方案
        deps_str = "、".join(available_deps) if available_deps else "项目需求"
        return [
            f"基于{deps_str}的分析结果，{config.work_focus_description}",
            "研究相关领域的最新趋势和最佳实践",
            "整合多方信息形成专业建议"
        ]

    def _generate_search_queries(
        self,
        expert_type: str,
        project_task: str,
        character_narrative: str
    ) -> Dict[str, str]:
        """生成搜索查询 - 使用LLM完全动态生成"""
        if not self.llm_model:
            logger.warning("No LLM model available, using fallback search query generation")
            return self._generate_search_queries_fallback(expert_type, project_task, character_narrative)

        try:
            # 专家角色描述（仅用于提示LLM）
            role_descriptions = {
                "V3": {
                    "role": "叙事与体验专家",
                    "purpose": "叙事设计、用户体验和情感触点",
                    "search_focus": "空间叙事、用户旅程、情感体验"
                },
                "V4": {
                    "role": "设计研究员",
                    "purpose": "设计研究、方法论和行业案例",
                    "search_focus": "设计研究、学术文献、创新方法论"
                },
                "V5": {
                    "role": "场景与行业专家",
                    "purpose": "行业趋势、场景分析和用户生态",
                    "search_focus": "行业趋势、市场分析、用户行为"
                },
                "V2": {
                    "role": "设计总监",
                    "purpose": "设计方案、趋势和最佳实践",
                    "search_focus": "设计案例、空间设计、行业标杆"
                },
                "V6": {
                    "role": "专业总工程师",
                    "purpose": "项目管理、实施方法和工程管理",
                    "search_focus": "项目管理、施工技术、工程实施"
                }
            }

            config = role_descriptions.get(expert_type)
            if not config:
                logger.warning(f"未找到 {expert_type} 的角色描述，使用降级方案")
                return self._generate_search_queries_fallback(expert_type, project_task, character_narrative)

            prompt = f"""你是{config['role']}，需要为以下项目生成3个精准的搜索查询。

项目任务: {project_task}

人物叙事: {character_narrative}

你的职责: {config['purpose']}
搜索重点: {config['search_focus']}

请生成3个搜索查询，要求：
1. 根据项目的具体业态、风格、特色定制查询
2. 包含项目中的关键实体（品牌名、地点、特定需求）
3. 适当时包含当前年份({datetime.now().year})以获取最新信息
4. 一个查询可以用中文，一个用英文（获取国际案例），一个混合
5. 避免"商业空间"、"设计趋势"等过于宽泛的词汇
6. 让每个查询都有明确的搜索意图和预期结果

输出JSON格式，3个查询键名为: query_1, query_2, query_3
例：
{{
  "query_1": "具体项目相关的中文查询",
  "query_2": "specific project-related English query",
  "query_3": "混合或补充查询"
}}
"""

            messages = [
                SystemMessage(content=f"你是{config['role']}，擅长根据项目特点生成精准的搜索查询，避免使用通用词汇。"),
                HumanMessage(content=prompt)
            ]

            response = self.llm_model.invoke(messages, max_tokens=300, temperature=0.3)

            # 解析JSON响应
            content = response.content.strip()
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1

            if start_idx != -1 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                search_queries = json.loads(json_str)
                logger.info(f"LLM generated {expert_type} search queries: {search_queries}")
                return search_queries
            else:
                logger.warning("Failed to parse LLM response, using fallback")
                return self._generate_search_queries_fallback(expert_type, project_task, character_narrative)

        except Exception as e:
            logger.error(f"LLM {expert_type} search query generation failed: {e}, using fallback")
            return self._generate_search_queries_fallback(expert_type, project_task, character_narrative)

    def _generate_search_queries_fallback(
        self,
        expert_type: str,
        project_task: str,
        character_narrative: str
    ) -> Dict[str, str]:
        """降级方案：基于关键词提取生成搜索查询"""
        # 从项目任务中提取关键词
        keywords = []
        for token in project_task.split():
            if len(token) >= 2:
                keywords.append(token)
        
        base_keywords = " ".join(keywords[:3]) if keywords else "商业空间设计"
        current_year = datetime.now().year
        
        # 根据专家类型生成不同的查询组合
        query_patterns = {
            "V3": [
                f"{base_keywords} 空间叙事 用户体验",
                f"{base_keywords} 情感设计 体验节点",
                f"{base_keywords} spatial experience design"
            ],
            "V4": [
                f"{base_keywords} 设计研究 方法论",
                f"{base_keywords} design thinking {current_year}",
                f"{base_keywords} 创新设计 案例分析"
            ],
            "V5": [
                f"{base_keywords} 行业趋势 {current_year}",
                f"{base_keywords} 用户行为 场景分析",
                f"{base_keywords} market analysis trends"
            ],
            "V2": [
                f"{base_keywords} 设计案例 {current_year}",
                f"{base_keywords} 空间设计 最佳实践",
                f"{base_keywords} commercial design trends"
            ],
            "V6": [
                f"{base_keywords} 项目管理 {current_year}",
                f"{base_keywords} 施工技术 工程实施",
                f"{base_keywords} project implementation methodology"
            ]
        }
        
        queries = query_patterns.get(expert_type, [
            f"{base_keywords} 设计",
            f"{base_keywords} 研究 {current_year}",
            f"{base_keywords} design trends"
        ])
        
        return {
            "query_1": queries[0],
            "query_2": queries[1],
            "query_3": queries[2]
        }

    def _extract_keywords_simple(self, project_task: str, character_narrative: str) -> str:
        """简单的关键词提取（基于规则）"""
        text = f"{project_task} {character_narrative}".lower()

        common_keywords = [
            # 项目类型
            "商业", "住宅", "办公", "餐饮", "零售", "娱乐", "酒店", "展厅",
            # 风格
            "现代", "简约", "优雅", "古典", "工业", "北欧", "中式", "日式",
            # 特征
            "品质", "艺术", "文化", "时尚", "经典", "科技", "自然", "温馨"
        ]

        found_keywords = [kw for kw in common_keywords if kw in text]
        return " ".join(found_keywords[:3]) if found_keywords else "高端设计"
