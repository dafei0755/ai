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


