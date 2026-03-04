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


