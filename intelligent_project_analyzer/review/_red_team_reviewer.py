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


from ._reviewer_base import ReviewerRole

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


