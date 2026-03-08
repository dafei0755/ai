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


