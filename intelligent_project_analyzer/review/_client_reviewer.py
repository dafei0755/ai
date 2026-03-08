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
