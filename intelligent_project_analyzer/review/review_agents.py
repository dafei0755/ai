"""
多视角审核专家系统

实现红蓝对抗、评委等多视角碰撞机制
"""

import json
import re
from typing import Any, Dict, List, Tuple

import httpcore

#  v7.8: 导入异常类型用于LLM服务连接异常处理
import openai
from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

from ..core.prompt_manager import PromptManager


class ReviewerRole:
    """审核专家角色基类"""

    def __init__(self, role_name: str, perspective: str, llm_model):
        self.role_name = role_name
        self.perspective = perspective
        self.llm_model = llm_model

    def review(self, agent_results: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, Any]:
        """
        审核专家分析结果

        Args:
            agent_results: 所有专家的分析结果
            requirements: 项目需求

        Returns:
            审核结果
        """
        try:
            return self._review_impl(agent_results, requirements)
        except (openai.APIConnectionError, httpcore.ConnectError, ConnectionError) as e:
            logger.error(f" LLM服务连接异常: {e}")
            return {
                "reviewer": self.role_name,
                "perspective": self.perspective,
                "content": "LLM服务连接异常，请稍后重试。",
                "improvements": [],
                "critical_issues_count": 0,
                "total_improvements": 0,
                "issues_found": [],
                "risk_level": "未知",
                "agents_to_rerun": [],
                "score": 0,
            }
        except Exception as e:
            logger.error(f" 审核专家review异常: {e}")
            raise

    def _review_impl(self, agent_results: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def _validate_and_fix_agent_ids(
        self, improvements: List[Dict[str, Any]], agent_ids: List[str], agent_results: Dict[str, Any]
    ):
        """
        验证并修正从JSON解析出的agent_id（通用方法，供所有审核专家使用）

        Args:
            improvements: 改进项列表，每项包含 agent_id 字段
            agent_ids: 有效的 agent_id 列表
            agent_results: 专家结果字典，用于提取 role_name 映射
        """
        # 构建 role_name 到 agent_id 的映射表
        role_name_map = {}
        for agent_id, result in agent_results.items():
            if isinstance(result, dict):
                role_name = result.get("role_name") or result.get("dynamic_role_name")
                if role_name:
                    role_name_map[role_name.lower()] = agent_id

        for imp in improvements:
            current_id = imp.get("agent_id", "")
            if current_id in agent_ids:
                continue  # 已是有效 ID，跳过

            # 尝试修复无效的 agent_id
            fixed_id = None

            # 1. 尝试通过 role_name 匹配
            if current_id.lower() in role_name_map:
                fixed_id = role_name_map[current_id.lower()]

            # 2. 尝试前缀匹配（如 "V3" 匹配 "V3_叙事专家_xxx"）
            if not fixed_id:
                for aid in agent_ids:
                    if aid.startswith(current_id) or current_id in aid:
                        fixed_id = aid
                        break

            # 3. 尝试部分关键词匹配
            if not fixed_id:
                current_lower = current_id.lower()
                for aid in agent_ids:
                    if current_lower in aid.lower():
                        fixed_id = aid
                        break

            if fixed_id:
                logger.debug(f" 修正 agent_id: {current_id} → {fixed_id}")
                imp["agent_id"] = fixed_id
            else:
                # 如果无法匹配，标记为 unknown
                logger.warning(f"️ 无法匹配 agent_id: {current_id}，保留原值")


class RedTeamReviewer(ReviewerRole):
    """红队审核专家 - 攻击方视角"""

    def __init__(self, llm_model):
        super().__init__(role_name="红队审核专家", perspective="攻击方视角 - 挑战和质疑分析结果", llm_model=llm_model)

        # 初始化提示词管理器
        self.prompt_manager = PromptManager()

    def _review_impl(self, agent_results: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f" {self.role_name} 开始审核")

        # 从外部配置加载审核提示词
        system_prompt = self.prompt_manager.get_reviewer_prompt(
            reviewer_role="red_team", role_name=self.role_name, perspective=self.perspective
        )

        # 如果配置不存在，抛出错误（不再使用硬编码 fallback）
        if not system_prompt:
            raise ValueError(
                " 未找到审核提示词配置: red_team\n"
                "请确保配置文件存在: config/prompts/review_agents.yaml\n"
                "并包含 reviewers.red_team.prompt_template 字段"
            )

        # 准备分析结果摘要
        results_summary = self._format_results_for_review(agent_results)

        user_prompt = f"""项目需求：
{requirements.get('project_task', '')}

专家分析结果：
{results_summary}

请从红队攻击方视角进行审核，找出所有问题和风险。
请严格按照 System Prompt 中定义的 JSON 格式输出。"""

        # 调用LLM
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]

        response = self.llm_model.invoke(messages)

        #  新格式：从"评分"改为"具体改进点"
        improvements = self._extract_improvements(response.content, agent_results)

        review_result = {
            "reviewer": self.role_name,
            "perspective": self.perspective,
            "content": response.content,
            "improvements": improvements,  #  新增：具体改进点列表
            "critical_issues_count": len([i for i in improvements if i.get("priority") == "high"]),
            "total_improvements": len(improvements),
            # 保留旧字段用于兼容
            "issues_found": [i.get("issue", "") for i in improvements],
            "risk_level": self._extract_risk_level(response.content),
            "agents_to_rerun": list(set([i.get("agent_id") for i in improvements if i.get("agent_id")])),
            "score": self._calculate_score_from_improvements(improvements),  # 从改进点反推评分
        }

        logger.info(
            f" {self.role_name} 审核完成，发现 {review_result['total_improvements']} 个改进点（{review_result['critical_issues_count']} 个高优先级）"
        )

        return review_result

    def review_role_selection(
        self, selected_roles: List[Dict[str, Any]], requirements: Dict[str, Any], strategy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        审核角色选择方案（红队批判视角）

        Args:
            selected_roles: 已选择的角色列表
            requirements: 项目需求
            strategy: 项目策略

        Returns:
            {
                "issues": [
                    {
                        "id": "R1",
                        "description": "问题描述",
                        "severity": "critical" | "high" | "medium" | "low",
                        "evidence": "证据",
                        "impact": "影响"
                    }
                ],
                "summary": "审核摘要"
            }
        """
        logger.info(f" {self.role_name} 开始审核角色选择")

        # 从外部配置加载角色选择审核提示词
        system_prompt = self.prompt_manager.get_reviewer_prompt(
            reviewer_role="role_selection_red_team", role_name=self.role_name, perspective=self.perspective
        )

        # 如果没有专门的角色选择提示词，使用默认提示词
        if not system_prompt:
            system_prompt = self._get_default_role_selection_prompt()

        # 准备角色选择摘要
        roles_summary = self._format_roles_for_review(selected_roles)

        user_prompt = f"""项目需求：
{requirements.get('project_task', '')}

项目策略：
{strategy.get('strategy_summary', '未提供策略信息')}

已选择的角色：
{roles_summary}

请从红队批判视角审核角色选择方案，找出潜在问题和风险。
请严格按照 JSON 格式输出：
{{
    "issues": [
        {{
            "id": "R1",
            "description": "问题描述",
            "severity": "critical" | "high" | "medium" | "low",
            "evidence": "证据",
            "impact": "影响"
        }}
    ],
    "summary": "审核摘要"
}}"""

        # 调用LLM
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]

        response = self.llm_model.invoke(messages)

        # 解析响应
        issues = self._extract_role_selection_issues(response.content)

        review_result = {
            "reviewer": self.role_name,
            "perspective": self.perspective,
            "content": response.content,
            "issues": issues,
            "summary": f"红队发现 {len(issues)} 个角色选择问题",
        }

        logger.info(f" {self.role_name} 角色选择审核完成，发现 {len(issues)} 个问题")

        return review_result

    def _format_roles_for_review(self, selected_roles: List[Dict[str, Any]]) -> str:
        """格式化角色列表用于审核"""
        summary_parts = []

        for i, role in enumerate(selected_roles, 1):
            if isinstance(role, dict):
                role_name = role.get("role_name") or role.get("dynamic_role_name", "未知角色")
                role_id = role.get("role_id", "")
                description = role.get("description", "")

                summary_parts.append(f"{i}. {role_name} (ID: {role_id})")
                if description:
                    summary_parts.append(f"   描述: {description[:100]}...")

        return "\n".join(summary_parts) if summary_parts else "无角色信息"

    def _get_default_role_selection_prompt(self) -> str:
        """获取默认的角色选择审核提示词"""
        return """你是角色选择质量审核专家（红队），负责批判性审核角色选择方案。

审核维度：
1. 角色覆盖完整性：是否覆盖所有需求维度？
2. 角色适配性：每个角色是否适合当前项目？
3. 角色协同性：角色之间是否能有效协作？
4. 潜在风险：是否存在明显的能力缺口或冗余？

输出格式：JSON
{
    "issues": [
        {
            "id": "R1",
            "description": "问题描述",
            "severity": "critical" | "high" | "medium" | "low",
            "evidence": "证据",
            "impact": "影响"
        }
    ],
    "summary": "审核摘要"
}"""

    def _extract_role_selection_issues(self, content: str) -> List[Dict[str, Any]]:
        """从审核内容中提取角色选择问题"""
        issues = []

        try:
            import json
            import re

            # 尝试提取 JSON 块
            json_str = content
            json_match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                start = content.find("{")
                end = content.rfind("}")
                if start != -1 and end != -1:
                    json_str = content[start : end + 1]

            # 尝试解析
            parsed_data = None
            try:
                parsed_data = json.loads(json_str)
            except json.JSONDecodeError:
                # 尝试修复常见错误
                fixed_str = re.sub(r",\s*}", "}", json_str)
                fixed_str = re.sub(r",\s*]", "]", fixed_str)
                parsed_data = json.loads(fixed_str)

            # 提取 issues
            if isinstance(parsed_data, dict) and "issues" in parsed_data:
                raw_issues = parsed_data["issues"]
                if isinstance(raw_issues, list):
                    for item in raw_issues:
                        if isinstance(item, dict):
                            issues.append(
                                {
                                    "id": item.get("id", f"R{len(issues)+1}"),
                                    "description": item.get("description", "未描述问题"),
                                    "severity": item.get("severity", "medium"),
                                    "evidence": item.get("evidence", ""),
                                    "impact": item.get("impact", ""),
                                }
                            )

                    if issues:
                        logger.info(f" 成功解析 JSON 格式的角色选择审核结果 ({len(issues)} 个问题)")
                        return issues

        except Exception as e:
            logger.warning(f"️ JSON 解析失败，回退到文本提取: {e}")

        # 回退到文本提取
        for line in content.split("\n"):
            if any(keyword in line for keyword in ["问题", "风险", "缺少", "缺乏", "不足", "冗余"]):
                issues.append(
                    {
                        "id": f"R{len(issues)+1}",
                        "description": line.strip(),
                        "severity": "medium",
                        "evidence": "",
                        "impact": "",
                    }
                )

        return issues[:10]  # 最多返回10个问题

    def _format_results_for_review(self, agent_results: Dict[str, Any]) -> str:
        """
        格式化分析结果用于审核

         v7.12: 增强格式化，明确显示每个专家的完整ID便于红队引用
        """
        summary_parts = []

        #  v7.12: 添加专家ID列表，便于红队引用
        summary_parts.append("【专家ID列表（审核时请使用这些完整ID）】")
        for agent_type, result in agent_results.items():
            if agent_type in ["requirements_analyst", "project_director"]:
                continue
            if result and isinstance(result, dict):
                role_name = result.get("role_name", "") or result.get("dynamic_role_name", agent_type)
                summary_parts.append(f"- {agent_type}: {role_name}")
        summary_parts.append("")

        # 原有的分析结果摘要
        summary_parts.append("【专家分析结果摘要】")
        for agent_type, result in agent_results.items():
            if agent_type in ["requirements_analyst", "project_director"]:
                continue

            if result and isinstance(result, dict):
                confidence = result.get("confidence", 0)
                role_name = result.get("role_name", "") or result.get("dynamic_role_name", "")
                summary_parts.append(f"- [{agent_type}] {role_name}: 置信度{confidence:.0%}")

        return "\n".join(summary_parts)

    def _extract_issues(self, content: str) -> List[str]:
        """从审核内容中提取问题列表"""
        # 简单实现：查找包含"问题"、"风险"等关键词的行
        issues = []
        for line in content.split("\n"):
            if any(keyword in line for keyword in ["问题", "风险", "漏洞", "缺陷", "不足"]):
                issues.append(line.strip())
        return issues[:10]  # 最多返回10个问题

    def _extract_risk_level(self, content: str) -> str:
        """提取风险等级"""
        content_lower = content.lower()
        if "高风险" in content or "high risk" in content_lower:
            return "高"
        elif "中风险" in content or "medium risk" in content_lower:
            return "中"
        else:
            return "低"

    def _extract_agents_to_rerun(self, content: str) -> List[str]:
        """提取需要重新执行的专家（使用动态角色 ID 前缀匹配）"""
        agents = []
        # 使用前缀映射来匹配动态角色 ID
        agent_prefixes = {
            "v2": "V2_",  # 匹配所有 V2_ 开头的角色
            "v3": "V3_",  # 匹配所有 V3_ 开头的角色
            "v4": "V4_",  # 匹配所有 V4_ 开头的角色
            "v5": "V5_",  # 匹配所有 V5_ 开头的角色
            "v6": "V6_",  # 匹配所有 V6_ 开头的角色
        }

        content_lower = content.lower()
        for keyword, prefix in agent_prefixes.items():
            if keyword in content_lower and ("重新" in content or "再次" in content):
                # 返回前缀，让调用者从 active_agents 中筛选
                agents.append(prefix)

        return agents

    def _extract_improvements(self, content: str, agent_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
         改进：从审核内容中提取结构化的改进点，支持动态角色ID匹配

        输出格式：
        [
            {
                "agent_id": "V3_叙事与体验专家_3-1",  # 动态ID
                "category": "user_persona",
                "issue": "用户画像缺少年龄分布数据",
                "expected": "补充目标用户的年龄段（如25-35岁）",
                "priority": "high"  # high/medium/low
            }
        ]
        """
        improvements = []
        agent_ids = list(agent_results.keys())

        #  P2修复: 优先尝试解析 JSON 格式
        try:
            import json
            import re

            # 尝试提取 JSON 块
            json_str = content
            json_match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 如果没有代码块，尝试查找第一个 { 和最后一个 }
                start = content.find("{")
                end = content.rfind("}")
                if start != -1 and end != -1:
                    json_str = content[start : end + 1]

            # 尝试解析
            parsed_data = None
            try:
                parsed_data = json.loads(json_str)
            except json.JSONDecodeError:
                # 尝试修复常见错误：尾部逗号
                try:
                    fixed_str = re.sub(r",\s*}", "}", json_str)
                    fixed_str = re.sub(r",\s*]", "]", fixed_str)
                    parsed_data = json.loads(fixed_str)
                except Exception:
                    pass

            # 处理红队标准格式 {"issues": [...]}
            if isinstance(parsed_data, dict) and "issues" in parsed_data:
                raw_issues = parsed_data["issues"]
                if isinstance(raw_issues, list):
                    for item in raw_issues:
                        if not isinstance(item, dict):
                            continue

                        # 映射字段到内部标准格式
                        improvements.append(
                            {
                                "agent_id": item.get("agent_id", "unknown"),
                                "category": item.get("dimension", "general"),
                                "issue": item.get("description", "未描述问题"),
                                "expected": item.get("impact", ""),
                                "priority": item.get("severity", "medium"),
                            }
                        )

                    if improvements:
                        logger.info(f" 成功解析 JSON 格式的审核结果 ({len(improvements)} 个问题)")
                        # 如果成功解析了JSON，直接返回，不再进行文本匹配
                        # 但需要确保 agent_id 是有效的，如果无效（如简写），尝试修正
                        self._validate_and_fix_agent_ids(improvements, agent_ids, agent_results)
                        return improvements

        except Exception as e:
            logger.warning(f"️ JSON 解析失败，回退到文本提取: {e}")

        # === 回退到文本提取逻辑 ===

        # 从内容中提取问题
        issues = self._extract_issues(content)

        #  过滤掉疑似 JSON 源码的行
        # 如果行包含 "key": 结构，很可能是 JSON 解析失败后的残留
        filtered_issues = []
        for issue in issues:
            if re.search(r'"\w+":', issue) or re.search(r"'\w+':", issue):
                logger.debug(f"️ 忽略疑似 JSON 源码行: {issue[:50]}...")
                continue
            filtered_issues.append(issue)
        issues = filtered_issues

        #  P1修复: 构建角色ID到role_name的映射表
        role_name_map = {}
        for agent_id, result in agent_results.items():
            if isinstance(result, dict):
                # 尝试多种可能的路径提取role_name
                role_name = None

                # 路径1: 直接从result根级别（正确路径）
                if "role_name" in result:
                    role_name = result["role_name"]
                # 路径2: 兼容旧格式 - 从dynamic_role_name字段
                elif "dynamic_role_name" in result:
                    role_name = result["dynamic_role_name"]
                # 路径3: 从structured_data字段
                elif "structured_data" in result:
                    structured = result["structured_data"]
                    if isinstance(structured, dict):
                        role_name = structured.get("role_name") or structured.get("dynamic_role_name", "")
                # 路径4: 从result字段（嵌套）
                elif "result" in result:
                    nested_result = result["result"]
                    if isinstance(nested_result, str):
                        # 尝试解析JSON字符串
                        try:
                            import json

                            parsed = json.loads(nested_result)
                            role_name = parsed.get("role_name") or parsed.get("dynamic_role_name", "")
                        except Exception:
                            pass
                    elif isinstance(nested_result, dict):
                        role_name = nested_result.get("role_name") or nested_result.get("dynamic_role_name", "")

                if role_name:
                    role_name_map[agent_id] = role_name.lower()
                    logger.debug(f"   映射 {agent_id} → {role_name}")

        logger.debug(f" 构建角色名称映射: {len(role_name_map)} 个角色")

        # 构建角色关键词映射表（支持动态ID匹配）
        role_keywords = {
            # V2: 设计总监
            "V2": ["设计总监", "design director", "设计方向", "整体设计", "v2", "v2_", "总监", "director"],
            # V3: 叙事与体验专家
            "V3": ["叙事", "narrative", "体验", "experience", "用户画像", "人物", "场景", "v3", "v3_", "叙事专家"],
            # V4: 设计研究员
            "V4": ["设计研究", "design research", "研究员", "案例", "参考", "灵感", "v4", "v4_", "研究"],
            # V5: 场景专家
            "V5": ["场景", "scenario", "空间", "体验场景", "行为", "v5", "v5_", "行业", "场景专家"],
            # V6: 总工程师
            "V6": ["总工", "chief engineer", "工程", "实施", "技术", "v6", "v6_", "工程师", "可行性", "经济"],
        }

        for i, issue in enumerate(issues):
            #  P1修复: 增强的智能匹配算法
            matched_agent = None
            issue_lower = issue.lower()

            # 方法1: 直接匹配完整agent_id
            for agent_id in agent_ids:
                if agent_id.lower() in issue_lower or agent_id.replace("_", " ").lower() in issue_lower:
                    matched_agent = agent_id
                    logger.debug(f" 通过完整ID匹配: {agent_id}")
                    break

            # 方法2: 通过dynamic_role_name模糊匹配
            if not matched_agent:
                for agent_id, dynamic_name in role_name_map.items():
                    if agent_id not in agent_ids:
                        continue
                    # 提取关键词（去除"专家""师"等后缀）
                    name_keywords = dynamic_name.replace("专家", "").replace("师", "").replace("与", " ").split()
                    # 匹配任意关键词（长度>=2以避免误匹配）
                    if any(kw in issue_lower for kw in name_keywords if len(kw) >= 2):
                        matched_agent = agent_id
                        logger.debug(f" 通过dynamic_role_name匹配: {agent_id} ({dynamic_name})")
                        break

            # 方法3: 通过角色关键词匹配前缀（保留原有逻辑作为备用）
            if not matched_agent:
                for prefix, keywords in role_keywords.items():
                    if any(keyword.lower() in issue_lower for keyword in keywords):
                        # 找到对应前缀的agent
                        for agent_id in agent_ids:
                            if agent_id.startswith(prefix):
                                matched_agent = agent_id
                                logger.debug(f" 通过关键词匹配: {agent_id} (前缀={prefix})")
                                break
                        if matched_agent:
                            break

            # 方法4: 如果问题笼统（如"整体设计"），分配给所有相关专家
            if not matched_agent and any(kw in issue for kw in ["整体", "全局", "所有", "通用"]):
                # 选择第一个专家作为代表
                matched_agent = agent_ids[0] if agent_ids else "unknown"
                logger.debug(f"️ 笼统问题，分配给: {matched_agent}")

            # 方法5: 如果仍未匹配，分配给第一个专家
            if not matched_agent and agent_ids:
                matched_agent = agent_ids[0]
                logger.warning(f"️ 问题'{issue[:30]}...'未能精确匹配，分配给{matched_agent}")

            # 判断优先级
            priority = "high" if any(kw in issue for kw in ["缺少", "缺乏", "没有", "不足", "不明确", "严重"]) else "medium"
            if any(kw in issue for kw in ["建议", "可以", "应该", "优化"]) and "缺" not in issue:
                priority = "low"

            improvements.append(
                {
                    "agent_id": matched_agent or "unknown",
                    "category": f"improvement_{i+1}",
                    "issue": issue.strip(),
                    "expected": f"针对'{issue[:20]}...'进行改进",
                    "priority": priority,
                }
            )

        # 统计匹配情况
        matched_count = len([imp for imp in improvements if imp["agent_id"] != "unknown"])
        logger.info(f" Agent ID匹配: {matched_count}/{len(improvements)} 个问题成功匹配到专家")

        return improvements

    def _calculate_score_from_improvements(self, improvements: List[Dict[str, Any]]) -> int:
        """
         新增：从改进点数量反推评分（用于兼容旧系统）

        逻辑：
        - 0个高优先级问题 → 85+
        - 1-2个高优先级问题 → 70-84
        - 3+个高优先级问题 → <70
        """
        high_count = len([i for i in improvements if i.get("priority") == "high"])
        total_count = len(improvements)

        if high_count == 0 and total_count <= 2:
            return 85
        elif high_count <= 1 and total_count <= 5:
            return 75
        elif high_count <= 2:
            return 65
        else:
            return 55

    def _extract_score(self, content: str) -> int:
        """提取评分（保留用于兼容）"""
        import re

        # 查找类似 "评分：75分" 或 "75/100" 的模式
        patterns = [r"评分[：:]\s*(\d+)", r"(\d+)\s*分", r"(\d+)\s*/\s*100"]

        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                score = int(match.group(1))
                return min(100, max(0, score))

        return 50  # 默认评分


class BlueTeamReviewer(ReviewerRole):
    """蓝队审核专家 - 防守方视角"""

    def __init__(self, llm_model):
        super().__init__(role_name="蓝队审核专家", perspective="防守方视角 - 验证和支持分析结果", llm_model=llm_model)
        self.prompt_manager = PromptManager()

    def review(
        self,
        agent_results: Dict[str, Any],
        requirements: Dict[str, Any],
        red_review: Dict[str, Any] | None = None,  #  接收红队问题清单
    ) -> Dict[str, Any]:
        """蓝队审核 - 验证红队问题，识别分析优势"""

        logger.info(f" {self.role_name} 开始审核")

        # 从外部配置加载审核提示词
        system_prompt = self.prompt_manager.get_reviewer_prompt(
            reviewer_role="blue_team", role_name=self.role_name, perspective=self.perspective
        )

        # 如果配置不存在，抛出错误（不再使用硬编码 fallback）
        if not system_prompt:
            raise ValueError(
                " 未找到审核提示词配置: blue_team\n"
                "请确保配置文件存在: config/prompts/review_agents.yaml\n"
                "并包含 reviewers.blue_team.prompt_template 字段"
            )

        results_summary = self._format_results_for_review(agent_results)

        #  P1修复：构建红队问题清单用于蓝队响应
        red_team_issues = ""
        if red_review:
            improvements = red_review.get("improvements", [])
            issues = red_review.get("issues_found", [])
            if improvements:
                red_team_issues = "\n\n红队发现的问题（请逐一响应）：\n"
                for i, imp in enumerate(improvements, 1):
                    agent_id = imp.get("agent_id", "unknown")
                    issue = imp.get("issue", "")
                    priority = imp.get("priority", "medium")
                    red_team_issues += f"{i}. [{priority}] {agent_id}: {issue}\n"
            elif issues:
                red_team_issues = "\n\n红队发现的问题（请逐一响应）：\n"
                for i, issue in enumerate(issues, 1):
                    red_team_issues += f"{i}. {issue}\n"

        user_prompt = f"""项目需求：
{requirements.get('project_task', '')}

专家分析结果：
{results_summary}{red_team_issues}

请从蓝队防守方视角进行审核，验证分析质量。
{'请针对红队提出的每个问题，给出您的立场（同意/不同意/部分同意）和理由。' if red_team_issues else ''}
请严格按照 System Prompt 中定义的 JSON 格式输出。"""

        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]

        response = self.llm_model.invoke(messages)

        #  P1-4修复：正确解析validations数组（包含stance、reasoning等字段）
        validations, strengths = self._parse_blue_team_response_v2(response.content, agent_results, red_review)

        review_result = {
            "reviewer": self.role_name,
            "perspective": self.perspective,
            "content": response.content,
            "validations": validations,  #  P1-4：完整的validations数组（包含stance、reasoning）
            "strengths": strengths,  #  P1-4：优势列表
            # 保留旧字段用于兼容
            "keep_as_is": [
                {"agent_id": s.get("agent_id"), "aspect": s.get("dimension"), "reason": s.get("description")}
                for s in strengths
            ],
            "enhancement_suggestions": [],  # 已废弃，保留空数组兼容
            "quality_level": self._extract_quality_level(response.content),
            "score": self._calculate_blue_score(strengths, []),
        }

        logger.info(f" {self.role_name} 审核完成，验证{len(validations)}个问题，发现{len(strengths)}个优势")

        return review_result

    def review_role_selection(
        self,
        selected_roles: List[Dict[str, Any]],
        requirements: Dict[str, Any],
        strategy: Dict[str, Any],
        red_review: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """
        审核角色选择方案（蓝队验证视角）

        验证红队发现的问题，过滤误判，识别角色选择的优势

        Args:
            selected_roles: 已选择的角色列表
            requirements: 项目需求
            strategy: 项目策略
            red_review: 红队审核结果

        Returns:
            {
                "validations": [
                    {
                        "red_issue_id": "R1",
                        "stance": "agree" | "disagree" | "partially_agree",
                        "reasoning": "验证理由",
                        "improvement_suggestion": "改进建议"
                    }
                ],
                "strengths": [
                    {
                        "aspect": "优势方面",
                        "evidence": "证据",
                        "value": "价值"
                    }
                ],
                "summary": "审核摘要"
            }
        """
        logger.info(f" {self.role_name} 开始验证角色选择")

        # 从外部配置加载角色选择审核提示词
        system_prompt = self.prompt_manager.get_reviewer_prompt(
            reviewer_role="role_selection_blue_team", role_name=self.role_name, perspective=self.perspective
        )

        # 如果没有专门的角色选择提示词，使用默认提示词
        if not system_prompt:
            system_prompt = self._get_default_role_selection_validation_prompt()

        # 准备角色选择摘要
        roles_summary = self._format_roles_for_review(selected_roles)

        # 准备红队问题清单
        red_team_issues = ""
        if red_review:
            issues = red_review.get("issues", [])
            if issues:
                red_team_issues = "\n\n红队发现的问题（请逐一验证）：\n"
                for i, issue in enumerate(issues, 1):
                    issue_id = issue.get("id", f"R{i}")
                    description = issue.get("description", "")
                    severity = issue.get("severity", "medium")
                    red_team_issues += f"{i}. [{issue_id}] {severity}: {description}\n"

        user_prompt = f"""项目需求：
{requirements.get('project_task', '')}

项目策略：
{strategy.get('strategy_summary', '未提供策略信息')}

已选择的角色：
{roles_summary}{red_team_issues}

请从蓝队验证视角审核角色选择方案：
1. 逐一验证红队提出的问题（同意/不同意/部分同意）
2. 过滤误判和过度批评
3. 识别角色选择的优势

请严格按照 JSON 格式输出：
{{
    "validations": [
        {{
            "red_issue_id": "R1",
            "stance": "agree" | "disagree" | "partially_agree",
            "reasoning": "验证理由",
            "improvement_suggestion": "改进建议"
        }}
    ],
    "strengths": [
        {{
            "aspect": "优势方面",
            "evidence": "证据",
            "value": "价值"
        }}
    ],
    "summary": "审核摘要"
}}"""

        # 调用LLM
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]

        response = self.llm_model.invoke(messages)

        # 解析响应
        validations, strengths = self._extract_role_selection_validations(response.content, red_review)

        review_result = {
            "reviewer": self.role_name,
            "perspective": self.perspective,
            "content": response.content,
            "validations": validations,
            "strengths": strengths,
            "summary": f"蓝队验证 {len(validations)} 个问题，发现 {len(strengths)} 个优势",
        }

        logger.info(f" {self.role_name} 角色选择验证完成，验证 {len(validations)} 个问题，发现 {len(strengths)} 个优势")

        return review_result

    def _format_roles_for_review(self, selected_roles: List[Dict[str, Any]]) -> str:
        """格式化角色列表用于审核"""
        summary_parts = []

        for i, role in enumerate(selected_roles, 1):
            if isinstance(role, dict):
                role_name = role.get("role_name") or role.get("dynamic_role_name", "未知角色")
                role_id = role.get("role_id", "")
                description = role.get("description", "")

                summary_parts.append(f"{i}. {role_name} (ID: {role_id})")
                if description:
                    summary_parts.append(f"   描述: {description[:100]}...")

        return "\n".join(summary_parts) if summary_parts else "无角色信息"

    def _get_default_role_selection_validation_prompt(self) -> str:
        """获取默认的角色选择验证提示词"""
        return """你是角色选择质量审核专家（蓝队），负责验证红队发现的问题。

任务：
1. 逐一验证红队提出的问题
2. 过滤误判和过度批评
3. 识别角色选择的优势

输出格式：JSON
{
    "validations": [
        {
            "red_issue_id": "R1",
            "stance": "agree" | "disagree" | "partially_agree",
            "reasoning": "验证理由",
            "improvement_suggestion": "改进建议"
        }
    ],
    "strengths": [
        {
            "aspect": "优势方面",
            "evidence": "证据",
            "value": "价值"
        }
    ],
    "summary": "审核摘要"
}"""

    def _extract_role_selection_validations(
        self, content: str, red_review: Dict[str, Any] | None
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """从审核内容中提取角色选择验证结果"""
        validations = []
        strengths = []

        try:
            import json
            import re

            # 尝试提取 JSON 块
            json_str = content
            json_match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                start = content.find("{")
                end = content.rfind("}")
                if start != -1 and end != -1:
                    json_str = content[start : end + 1]

            # 尝试解析
            parsed_data = None
            try:
                parsed_data = json.loads(json_str)
            except json.JSONDecodeError:
                # 尝试修复常见错误
                fixed_str = re.sub(r",\s*}", "}", json_str)
                fixed_str = re.sub(r",\s*]", "]", fixed_str)
                parsed_data = json.loads(fixed_str)

            # 提取 validations
            if isinstance(parsed_data, dict) and "validations" in parsed_data:
                raw_validations = parsed_data["validations"]
                if isinstance(raw_validations, list):
                    for item in raw_validations:
                        if isinstance(item, dict):
                            validations.append(
                                {
                                    "red_issue_id": item.get("red_issue_id", ""),
                                    "stance": item.get("stance", "agree"),
                                    "reasoning": item.get("reasoning", ""),
                                    "improvement_suggestion": item.get("improvement_suggestion", ""),
                                }
                            )

            # 提取 strengths
            if isinstance(parsed_data, dict) and "strengths" in parsed_data:
                raw_strengths = parsed_data["strengths"]
                if isinstance(raw_strengths, list):
                    for item in raw_strengths:
                        if isinstance(item, dict):
                            strengths.append(
                                {
                                    "aspect": item.get("aspect", ""),
                                    "evidence": item.get("evidence", ""),
                                    "value": item.get("value", ""),
                                }
                            )

            if validations or strengths:
                logger.info(f" 成功解析 JSON 格式的角色选择验证结果 ({len(validations)} 个验证, {len(strengths)} 个优势)")
                return validations, strengths

        except Exception as e:
            logger.warning(f"️ JSON 解析失败，回退到默认处理: {e}")

        # 回退：如果有红队审核结果，默认同意所有问题
        if red_review:
            issues = red_review.get("issues", [])
            for issue in issues:
                validations.append(
                    {
                        "red_issue_id": issue.get("id", ""),
                        "stance": "agree",
                        "reasoning": "蓝队未明确回应，默认同意红队判断",
                        "improvement_suggestion": "",
                    }
                )

        return validations, strengths

    def _parse_blue_team_response(
        self, content: str, agent_results: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """解析蓝队响应（优先JSON，回退到文本）"""
        keep_as_is = []
        enhancements = []

        try:
            # 尝试提取JSON
            json_str = content
            json_match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                start = content.find("{")
                end = content.rfind("}")
                if start != -1 and end != -1:
                    json_str = content[start : end + 1]

            # 尝试修复常见错误
            try:
                parsed_data = json.loads(json_str)
            except json.JSONDecodeError:
                fixed_str = re.sub(r",\s*}", "}", json_str)
                fixed_str = re.sub(r",\s*]", "]", fixed_str)
                parsed_data = json.loads(fixed_str)

            # 提取优势 (strengths -> keep_as_is)
            if "strengths" in parsed_data and isinstance(parsed_data["strengths"], list):
                for item in parsed_data["strengths"]:
                    if isinstance(item, dict):
                        keep_as_is.append(
                            {
                                "agent_id": item.get("agent_id", "general"),
                                "aspect": item.get("dimension", "strength"),
                                "reason": item.get("description", ""),
                            }
                        )

            # 提取改进建议 (validations -> enhancements)
            if "validations" in parsed_data and isinstance(parsed_data["validations"], list):
                for item in parsed_data["validations"]:
                    if isinstance(item, dict) and item.get("improvement_suggestion"):
                        enhancements.append(
                            {
                                "agent_id": "general",
                                "aspect": "enhancement",
                                "suggestion": item.get("improvement_suggestion", ""),
                            }
                        )

            if keep_as_is or enhancements:
                logger.info(f" 成功解析 BlueTeam JSON: {len(keep_as_is)} strengths, {len(enhancements)} enhancements")
                return keep_as_is, enhancements

        except Exception as e:
            logger.warning(f"️ BlueTeam JSON 解析失败，回退到文本提取: {e}")

        # 回退到文本提取
        return self._extract_keep_as_is(content, agent_results), self._extract_enhancements(content, agent_results)

    def _format_results_for_review(self, agent_results: Dict[str, Any]) -> str:
        """格式化分析结果"""
        summary_parts = []
        for agent_type, result in agent_results.items():
            if agent_type in ["requirements_analyst", "project_director"]:
                continue
            if result and isinstance(result, dict):
                confidence = result.get("confidence", 0)
                summary_parts.append(f"- {agent_type}: 置信度{confidence:.0%}")
        return "\n".join(summary_parts)

    def _extract_keep_as_is(self, content: str, agent_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
         新增：提取应保留的内容

        输出格式：
        [
            {
                "agent_id": "v3_narrative_expert",
                "aspect": "narrative_structure",
                "reason": "空间叙事结构清晰，情感递进合理"
            }
        ]
        """
        keep_list = []
        strengths = self._extract_strengths(content)
        agent_ids = list(agent_results.keys())

        for i, strength in enumerate(strengths):
            # 尝试匹配agent_id
            matched_agent = None
            for agent_id in agent_ids:
                if any(
                    keyword in strength.lower() for keyword in [agent_id.lower(), agent_id.replace("_", " ").lower()]
                ):
                    matched_agent = agent_id
                    break

            keep_list.append(
                {"agent_id": matched_agent or "general", "aspect": f"strength_{i+1}", "reason": strength.strip()}
            )

        return keep_list

    def _extract_enhancements(self, content: str, agent_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
         新增：提取增强建议

        输出格式：
        [
            {
                "agent_id": "v3_narrative_expert",
                "aspect": "sensory_design",
                "suggestion": "增加嗅觉和听觉的多感官设计"
            }
        ]
        """
        enhancements = []

        # 从内容中提取建议
        for line in content.split("\n"):
            if any(keyword in line for keyword in ["建议", "可以", "应该", "增加", "优化"]):
                enhancements.append({"agent_id": "general", "aspect": "enhancement", "suggestion": line.strip()})

        return enhancements[:5]  # 最多迕5个

    def _calculate_blue_score(self, keep_as_is: List, enhancements: List) -> int:
        """
         新增：从保留内容和增强建议反推评分

        逻辑：
        - 优势多、建议少 → 高分
        - 优势少、建议多 → 低分
        """
        strength_count = len(keep_as_is)
        enhancement_count = len(enhancements)

        if strength_count >= 5 and enhancement_count <= 2:
            return 85
        elif strength_count >= 3 and enhancement_count <= 3:
            return 78
        elif strength_count >= 2:
            return 70
        else:
            return 60

    def _extract_strengths(self, content: str) -> List[str]:
        """提取优势列表"""
        strengths = []
        for line in content.split("\n"):
            if any(keyword in line for keyword in ["优势", "亮点", "优点", "出色", "优秀"]):
                strengths.append(line.strip())
        return strengths[:10]

    def _extract_quality_level(self, content: str) -> str:
        """提取质量等级"""
        if "优秀" in content:
            return "优秀"
        elif "良好" in content:
            return "良好"
        elif "一般" in content:
            return "一般"
        else:
            return "良好"

    def _extract_score(self, content: str) -> int:
        """提取评分"""
        import re

        patterns = [r"评分[：:]\s*(\d+)", r"(\d+)\s*分", r"(\d+)\s*/\s*100"]
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return min(100, max(0, int(match.group(1))))
        return 70  # 默认评分

    def _parse_blue_team_response_v2(
        self, content: str, agent_results: Dict[str, Any], red_review: Dict[str, Any] | None = None
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
         P1-4：解析蓝队响应 v2 - 正确提取validations和strengths
         v7.12：增强JSON预处理，处理markdown代码块和常见格式问题

        返回:
            (validations, strengths)
            - validations: 对红队问题的逐一回应（包含stance、reasoning等）
            - strengths: 发现的优势列表
        """
        validations = []
        strengths = []

        try:
            #  v7.12: 增强预处理 - 移除markdown代码块标记
            cleaned_content = content.strip()

            # 移除所有markdown代码块标记（包括```json, ```JSON, ``` 等变体）
            if re.search(r"^```(?:json|JSON)?\s*", cleaned_content):
                cleaned_content = re.sub(r"^```(?:json|JSON)?\s*", "", cleaned_content)
            cleaned_content = re.sub(r"\s*```$", "", cleaned_content)
            # 处理中间的代码块
            code_block_match = re.search(r"```(?:json|JSON)?\s*([\s\S]*?)\s*```", cleaned_content, re.DOTALL)
            if code_block_match:
                cleaned_content = code_block_match.group(1)

            # 尝试提取JSON
            json_str = cleaned_content
            if not json_str.strip().startswith("{"):
                start = cleaned_content.find("{")
                end = cleaned_content.rfind("}")
                if start != -1 and end != -1:
                    json_str = cleaned_content[start : end + 1]

            # 尝试修复常见错误
            try:
                parsed_data = json.loads(json_str)
            except json.JSONDecodeError:
                fixed_str = re.sub(r",\s*}", "}", json_str)
                fixed_str = re.sub(r",\s*]", "]", fixed_str)
                #  v7.12: 额外修复 - 处理单引号
                fixed_str = fixed_str.replace("'", '"')
                parsed_data = json.loads(fixed_str)

            #  P1-4：提取validations数组（完整字段）
            if "validations" in parsed_data and isinstance(parsed_data["validations"], list):
                for item in parsed_data["validations"]:
                    if isinstance(item, dict):
                        validations.append(
                            {
                                "issue_id": item.get("red_issue_id", ""),  # 对应的红队问题ID
                                "stance": item.get("stance", "agree"),  # agree/disagree/partially_agree
                                "reasoning": item.get("reasoning", ""),  # 为什么同意/不同意
                                "defense": item.get("reasoning", ""),  # 辩护理由（兼容字段）
                                "severity_adjustment": item.get("severity_adjustment", ""),
                                "improvement_suggestion": item.get("improvement_suggestion", ""),
                            }
                        )

            #  P1-4：提取strengths数组（完整字段）
            if "strengths" in parsed_data and isinstance(parsed_data["strengths"], list):
                for item in parsed_data["strengths"]:
                    if isinstance(item, dict):
                        strengths.append(
                            {
                                "id": item.get("id", ""),
                                "agent_id": item.get("agent_id", "general"),
                                "dimension": item.get("dimension", "strength"),
                                "description": item.get("description", ""),
                                "evidence": item.get("evidence", ""),
                                "value": item.get("value", ""),
                            }
                        )

            if validations or strengths:
                logger.info(f" 成功解析 BlueTeam JSON v2: {len(validations)} validations, {len(strengths)} strengths")
                return validations, strengths

        except Exception as e:
            logger.warning(f"️ BlueTeam JSON v2 解析失败，回退到文本提取: {e}")

        # 回退到文本提取（生成默认validations）
        if red_review:
            improvements = red_review.get("improvements", [])
            for imp in improvements:
                validations.append(
                    {
                        "issue_id": imp.get("issue_id", ""),
                        "stance": "agree",  # 默认同意
                        "reasoning": "蓝队未明确回应，默认同意红队判断",
                        "defense": "",
                        "severity_adjustment": "",
                        "improvement_suggestion": "",
                    }
                )

        # 提取strengths（回退）
        strengths_text = self._extract_strengths(content)
        for i, strength in enumerate(strengths_text):
            strengths.append(
                {
                    "id": f"B{i+1}",
                    "agent_id": "general",
                    "dimension": "strength",
                    "description": strength,
                    "evidence": "",
                    "value": "",
                }
            )

        return validations, strengths


class JudgeReviewer(ReviewerRole):
    """评委审核专家 - 中立评判视角"""

    def __init__(self, llm_model):
        super().__init__(role_name="评委审核专家", perspective="中立评判视角 - 综合评估和裁决", llm_model=llm_model)
        self.prompt_manager = PromptManager()

    def review(
        self,
        agent_results: Dict[str, Any],
        requirements: Dict[str, Any],
        red_team_review: Dict[str, Any] | None = None,
        blue_team_review: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """评委审核 - 综合红蓝双方意见进行裁决"""

        logger.info(f"️ {self.role_name} 开始审核")

        # 从外部配置加载审核提示词
        system_prompt = self.prompt_manager.get_reviewer_prompt(
            reviewer_role="judge", role_name=self.role_name, perspective=self.perspective
        )

        # 如果配置不存在，抛出错误（不再使用硬编码 fallback）
        if not system_prompt:
            raise ValueError(
                " 未找到审核提示词配置: judge\n"
                "请确保配置文件存在: config/prompts/review_agents.yaml\n"
                "并包含 reviewers.judge.prompt_template 字段"
            )

        results_summary = self._format_results_for_review(agent_results)

        # 整合红蓝双方意见
        debate_summary = ""
        if red_team_review:
            debate_summary += f"\n红队意见：\n{red_team_review.get('content', '')[:500]}\n"
        if blue_team_review:
            debate_summary += f"\n蓝队意见：\n{blue_team_review.get('content', '')[:500]}\n"

        user_prompt = f"""项目需求：
{requirements.get('project_task', '')}

专家分析结果：
{results_summary}

红蓝对抗意见：
{debate_summary}

请作为评委进行综合评判。
请严格按照 System Prompt 中定义的 JSON 格式输出。"""

        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]

        response = self.llm_model.invoke(messages)

        #  新格式：尝试解析JSON，失败则回退
        prioritized_improvements = self._parse_judge_response(
            response.content, agent_results, red_team_review, blue_team_review
        )

        review_result = {
            "reviewer": self.role_name,
            "perspective": self.perspective,
            "content": response.content,
            "prioritized_improvements": prioritized_improvements,  #  新增：优先级排序的改进点
            "consensus_issues": [],  #  新增：共识问题（简化实现）
            "conflicting_views": [],  #  新增：争议点（简化实现）
            # 保留旧字段用于兼容
            "decision": self._extract_decision(response.content),
            "agents_to_rerun": list(
                set(
                    [
                        i.get("agent_id")
                        for i in prioritized_improvements
                        if i.get("agent_id") and i.get("agent_id") != "general"
                    ]
                )
            ),
            "improvement_requirements": [i.get("task", "") for i in prioritized_improvements],
            "score": self._calculate_judge_score(prioritized_improvements),
        }

        logger.info(f"️ {self.role_name} 审核完成，裁决: {review_result['decision']}，{len(prioritized_improvements)}个优先级改进点")

        return review_result

    def _parse_judge_response(
        self,
        content: str,
        agent_results: Dict[str, Any],
        red_review: Dict[str, Any] | None,
        blue_review: Dict[str, Any] | None,
    ) -> List[Dict[str, Any]]:
        """解析评委响应（优先JSON，回退到文本）"""
        improvements = []

        try:
            # 尝试提取JSON
            json_str = content
            json_match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                start = content.find("{")
                end = content.rfind("}")
                if start != -1 and end != -1:
                    json_str = content[start : end + 1]

            # 尝试修复常见错误
            try:
                parsed_data = json.loads(json_str)
            except json.JSONDecodeError:
                fixed_str = re.sub(r",\s*}", "}", json_str)
                fixed_str = re.sub(r",\s*]", "]", fixed_str)
                parsed_data = json.loads(fixed_str)

            # 提取改进点 (rulings -> improvements)
            if "rulings" in parsed_data and isinstance(parsed_data["rulings"], list):
                rulings_map = {r.get("red_issue_id"): r for r in parsed_data["rulings"] if isinstance(r, dict)}

                # 如果有 priority_ranking，按顺序处理
                ranking = parsed_data.get("priority_ranking", [])
                if not isinstance(ranking, list):
                    ranking = list(rulings_map.keys())

                # 确保所有 ruling 都被处理
                for rid in ranking:
                    if rid not in rulings_map:
                        continue
                    ruling = rulings_map[rid]
                    if ruling.get("ruling") in ["accept", "modify"]:
                        # 尝试从 action_required 中推断 agent_id
                        action = ruling.get("action_required", "")

                        improvements.append(
                            {
                                "priority": len(improvements) + 1,
                                "agent_id": "unknown",  # 暂时无法精确关联
                                "task": action,
                                "rationale": ruling.get("reasoning", ""),
                            }
                        )

                # 处理未在 ranking 中的 rulings
                for rid, ruling in rulings_map.items():
                    if rid not in ranking and ruling.get("ruling") in ["accept", "modify"]:
                        improvements.append(
                            {
                                "priority": len(improvements) + 1,
                                "agent_id": "unknown",
                                "task": ruling.get("action_required", ""),
                                "rationale": ruling.get("reasoning", ""),
                            }
                        )

            if improvements:
                logger.info(f" 成功解析 Judge JSON: {len(improvements)} improvements")
                return improvements

        except Exception as e:
            logger.warning(f"️ Judge JSON 解析失败，回退到文本提取: {e}")

        # 回退到文本提取
        return self._extract_prioritized_improvements(content, agent_results, red_review, blue_review)

    def _format_results_for_review(self, agent_results: Dict[str, Any]) -> str:
        """格式化分析结果"""
        summary_parts = []
        for agent_type, result in agent_results.items():
            if agent_type in ["requirements_analyst", "project_director"]:
                continue
            if result and isinstance(result, dict):
                confidence = result.get("confidence", 0)
                summary_parts.append(f"- {agent_type}: 置信度{confidence:.0%}")
        return "\n".join(summary_parts)

    def _extract_decision(self, content: str) -> str:
        """提取裁决结果"""
        if "通过" in content and "不通过" not in content:
            if "有条件" in content:
                return "有条件通过"
            return "通过"
        elif "不通过" in content:
            return "不通过"
        else:
            return "有条件通过"

    def _extract_agents_to_rerun(self, content: str) -> List[str]:
        """提取需要重新执行的专家（使用动态角色 ID 前缀匹配）"""
        agents = []
        # 使用前缀映射来匹配动态角色 ID
        agent_prefixes = {
            "v2": "V2_",  # 匹配所有 V2_ 开头的角色
            "v3": "V3_",  # 匹配所有 V3_ 开头的角色
            "v4": "V4_",  # 匹配所有 V4_ 开头的角色
            "v5": "V5_",  # 匹配所有 V5_ 开头的角色
            "v6": "V6_",  # 匹配所有 V6_ 开头的角色
        }

        content_lower = content.lower()
        for keyword, prefix in agent_prefixes.items():
            if keyword in content_lower and ("重新" in content or "再次" in content):
                # 返回前缀，让调用者从 active_agents 中筛选
                agents.append(prefix)

        return agents

    def _extract_prioritized_improvements(
        self,
        content: str,
        agent_results: Dict[str, Any],
        red_review: Dict[str, Any] | None,
        blue_review: Dict[str, Any] | None,
    ) -> List[Dict[str, Any]]:
        """
         新增：提取优先级排序的改进点

        输出格式：
        [
            {
                "priority": 1,
                "agent_id": "v3_narrative_expert",
                "task": "补充用户画像的量化数据",
                "rationale": "红队和甲方都提到缺少数据支撑"
            }
        ]
        """
        improvements = []

        # 从红队改进点中提取高优先级问题
        if red_review and "improvements" in red_review:
            for imp in red_review["improvements"]:
                if imp.get("priority") == "high":
                    improvements.append(
                        {
                            "priority": len(improvements) + 1,
                            "agent_id": imp.get("agent_id", "unknown"),
                            "task": imp.get("issue", ""),
                            "rationale": f"红队高优先级问题: {imp.get('expected', '')}",
                        }
                    )

        # 从评委内容中提取额外的改进要求
        improvement_lines = self._extract_improvement_lines(content)
        for line in improvement_lines[:3]:  # 最多3个
            improvements.append(
                {"priority": len(improvements) + 1, "agent_id": "general", "task": line, "rationale": "评委裁决"}
            )

        return improvements

    def _calculate_judge_score(self, improvements: List[Dict[str, Any]]) -> int:
        """
         新增：从改进点数量反推评分
        """
        count = len(improvements)
        if count == 0:
            return 90
        elif count <= 2:
            return 80
        elif count <= 4:
            return 72
        else:
            return 65

    def _extract_improvement_lines(self, content: str) -> List[str]:
        """提取改进要求行"""
        improvements = []
        for line in content.split("\n"):
            if any(keyword in line for keyword in ["改进", "优化", "完善", "补充", "加强"]):
                improvements.append(line.strip())
        return improvements[:10]

    def _extract_improvements(self, content: str) -> List[str]:
        """提取改进要求"""
        improvements = []
        for line in content.split("\n"):
            if any(keyword in line for keyword in ["改进", "优化", "完善", "补充", "加强"]):
                improvements.append(line.strip())
        return improvements[:10]

    def _extract_score(self, content: str) -> int:
        """提取评分"""
        import re

        patterns = [r"评分[：:]\s*(\d+)", r"(\d+)\s*分", r"(\d+)\s*/\s*100"]
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return min(100, max(0, int(match.group(1))))
        return 60  # 默认评分


class ClientReviewer(ReviewerRole):
    """甲方审核专家 - 客户需求视角"""

    def __init__(self, llm_model):
        super().__init__(role_name="甲方审核专家", perspective="客户需求视角 - 业务价值和实用性", llm_model=llm_model)
        self.prompt_manager = PromptManager()

    def review(
        self,
        agent_results: Dict[str, Any],
        requirements: Dict[str, Any],
        judge_review: Dict[str, Any] | None = None,  #  接收评委裁决
    ) -> Dict[str, Any]:
        """甲方审核 - 基于评委裁决做出业务决策"""

        logger.info(f" {self.role_name} 开始审核")

        # 从外部配置加载审核提示词
        system_prompt = self.prompt_manager.get_reviewer_prompt(
            reviewer_role="client", role_name=self.role_name, perspective=self.perspective
        )

        # 如果配置不存在，抛出错误（不再使用硬编码 fallback）
        if not system_prompt:
            raise ValueError(
                " 未找到审核提示词配置: client\n"
                "请确保配置文件存在: config/prompts/review_agents.yaml\n"
                "并包含 reviewers.client.prompt_template 字段"
            )

        results_summary = self._format_results_for_review(agent_results)

        user_prompt = f"""项目需求：
{requirements.get('project_task', '')}

业务目标：
{requirements.get('business_goals', '提升业务效率和用户体验')}

专家分析结果：
{results_summary}

请从甲方客户视角进行审核。

输出格式：
1. 业务价值评估
2. 成本效益分析
3. 实施可行性评估
4. 主要关注点和疑虑
5. 是否接受方案（接受/有保留接受/不接受）
6. 总体评分（0-100分）"""

        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]

        response = self.llm_model.invoke(messages)

        #  新格式：从"接受度评分"改为"业务需求缺口"
        business_gaps = self._extract_business_gaps(response.content, agent_results)

        review_result = {
            "reviewer": self.role_name,
            "perspective": self.perspective,
            "content": response.content,
            "business_gaps": business_gaps,  #  新增：业务需求缺口列表
            "market_concerns": [],  #  新增：市场关注点（简化实现）
            "feasibility_concerns": [],  #  新增：可行性关注点（简化实现）
            # 保留旧字段用于兼容
            "business_value": self._extract_business_value(response.content),
            "acceptance": self._extract_acceptance(response.content),
            "concerns": [g.get("gap", "") for g in business_gaps],
            "score": self._calculate_client_score(business_gaps),
        }

        logger.info(f" {self.role_name} 审核完成，接受度: {review_result['acceptance']}，{len(business_gaps)}个业务缺口")

        return review_result

    def _format_results_for_review(self, agent_results: Dict[str, Any]) -> str:
        """格式化分析结果"""
        summary_parts = []
        for agent_type, result in agent_results.items():
            if agent_type in ["requirements_analyst", "project_director"]:
                continue
            if result and isinstance(result, dict):
                confidence = result.get("confidence", 0)
                summary_parts.append(f"- {agent_type}: 置信度{confidence:.0%}")
        return "\n".join(summary_parts)

    def _extract_business_gaps(self, content: str, agent_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
         新增：提取业务需求缺口

        输出格式：
        [
            {
                "aspect": "budget",
                "gap": "缺少成本分解和ROI预测",
                "impact": "无法评估投资回报",
                "required_info": "分项预算明细 + 3年ROI预测模型"
            }
        ]
        """
        gaps = []
        concerns = self._extract_concerns(content)

        for concern in concerns:
            # 简单实现：将关注点转换为缺口格式
            gaps.append(
                {
                    "aspect": "business_requirement",
                    "gap": concern,
                    "impact": "影响业务决策",
                    "required_info": f"需要补充：{concern}",
                }
            )

        return gaps[:5]  # 最多5个

    def _calculate_client_score(self, gaps: List[Dict[str, Any]]) -> int:
        """
         新增：从业务缺口数量反推评分
        """
        count = len(gaps)
        if count == 0:
            return 85
        elif count <= 2:
            return 75
        elif count <= 4:
            return 68
        else:
            return 60

    def _extract_business_value(self, content: str) -> str:
        """提取业务价值评估"""
        for line in content.split("\n"):
            if "业务价值" in line or "商业价值" in line:
                return line.strip()
        return "业务价值待评估"

    def _extract_acceptance(self, content: str) -> str:
        """提取接受度"""
        if "接受" in content and "不接受" not in content:
            if "保留" in content:
                return "有保留接受"
            return "接受"
        elif "不接受" in content:
            return "不接受"
        else:
            return "有保留接受"

    def _extract_concerns(self, content: str) -> List[str]:
        """提取关注点和疑虑"""
        concerns = []
        for line in content.split("\n"):
            if any(keyword in line for keyword in ["关注", "疑虑", "担心", "风险", "问题"]):
                concerns.append(line.strip())
        return concerns[:10]

    def _extract_score(self, content: str) -> int:
        """提取评分"""
        import re

        patterns = [r"评分[：:]\s*(\d+)", r"(\d+)\s*分", r"(\d+)\s*/\s*100"]
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return min(100, max(0, int(match.group(1))))
        return 65  # 默认评分
