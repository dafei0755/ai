"""
动态项目总监智能体 - Dynamic Project Director Agent

基于角色配置系统的项目总监,负责分析需求并选择合适的专业角色。
Project Director based on role configuration system.
"""

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Union

from langchain_core.exceptions import OutputParserException
from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger
from pydantic import BaseModel, Field, ValidationError, model_validator

from intelligent_project_analyzer.core.prompt_manager import PromptManager
from intelligent_project_analyzer.core.role_manager import RoleManager
from intelligent_project_analyzer.core.task_oriented_models import (
    DeliverableFormat,
    DeliverableSpec,
    Priority,
    TaskInstruction,
    generate_task_instruction_template,
)


from ._director_models import (
    format_for_log, TaskDetail, RoleObject, RoleSelection
)

class ChallengeDetector:
    """
    v3.5挑战检测器 - 检测专家输出中的challenge_flags并处理

    职责:
    1. 检测专家输出中的challenge_flags
    2. 分类挑战类型（deeper_insight/uncertainty_clarification/competing_frames）
    3. 决策处理方式（accept/revisit/synthesize/escalate）
    4. 记录挑战日志
    """

    def __init__(self):
        self.challenge_log = []

    def detect_challenges(self, expert_outputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        检测所有专家输出中的挑战标记

        Args:
            expert_outputs: 专家输出字典，格式为 {expert_role_id: expert_output}

        Returns:
            检测结果字典，包含:
            - has_challenges: bool
            - challenges: List[Dict]
            - challenge_summary: str
        """
        challenges = []

        for expert_role, output in expert_outputs.items():
            # 检查是否有challenge_flags字段
            if isinstance(output, dict) and "challenge_flags" in output:
                challenge_flags = output.get("challenge_flags")

                # 确保challenge_flags不为空
                if challenge_flags and isinstance(challenge_flags, list):
                    for challenge in challenge_flags:
                        #  P0修复: 支持字符串类型的JSON解析
                        if isinstance(challenge, str):
                            try:
                                import json

                                # 尝试解析JSON
                                parsed_challenge = json.loads(challenge)
                                if isinstance(parsed_challenge, dict):
                                    challenge = parsed_challenge
                                    logger.debug(f" 成功解析字符串类型的challenge: {challenge.get('challenged_item', '')}")
                                else:
                                    # 如果解析结果不是字典，抛出异常以触发fallback
                                    raise ValueError("Parsed JSON is not a dict")
                            except (json.JSONDecodeError, AttributeError, ValueError):
                                # Fallback: 将普通字符串视为挑战描述
                                logger.info(f"ℹ️ 将字符串视为简单挑战描述: {challenge[:50]}...")
                                challenge = {
                                    "challenged_item": "General Issue",
                                    "rationale": challenge,
                                    "reinterpretation": "N/A",
                                    "design_impact": "See rationale",
                                }

                        # 检查challenge是否为字典类型
                        if not isinstance(challenge, dict):
                            logger.warning(f"️ 跳过非字典类型的challenge: {type(challenge)}")
                            continue

                        # 添加专家角色信息
                        challenge_with_role = {
                            "expert_role": expert_role,
                            "challenged_item": challenge.get("challenged_item", ""),
                            "rationale": challenge.get("rationale", ""),
                            "reinterpretation": challenge.get("reinterpretation", ""),
                            "design_impact": challenge.get("design_impact", ""),
                        }
                        challenges.append(challenge_with_role)

                        # 记录到日志
                        self.challenge_log.append(
                            {
                                "timestamp": datetime.now().isoformat(),
                                "expert_role": expert_role,
                                "challenge": challenge_with_role,
                            }
                        )

                        logger.warning(f" 检测到挑战 from {expert_role}: {challenge.get('challenged_item')}")

        #  修复P1: 改进挑战检测逻辑,确保正确识别challenge_flags
        has_challenges = len(challenges) > 0

        result = {
            "has_challenges": has_challenges,
            "challenges": challenges,
            "challenge_summary": self._summarize_challenges(challenges) if has_challenges else "",
        }

        if has_challenges:
            logger.warning(f" [v3.5] 共检测到 {len(challenges)} 个挑战标记,触发反馈循环")
            for i, ch in enumerate(challenges, 1):
                logger.warning(f"    挑战{i}: {ch.get('expert_role')} 对 '{ch.get('challenged_item')}' 提出质疑")
        else:
            logger.info(" [v3.5] 未检测到挑战标记，专家接受需求分析师的洞察")

        return result

    def _summarize_challenges(self, challenges: List[Dict]) -> str:
        """生成挑战摘要"""
        summary_parts = []
        for i, challenge in enumerate(challenges, 1):
            summary_parts.append(
                f"{i}. **{challenge['expert_role']}** 挑战了 '{challenge['challenged_item']}':\n"
                f"   理由: {challenge['rationale'][:100]}...\n"
                f"   重新诠释: {challenge['reinterpretation'][:100]}..."
            )
        return "\n\n".join(summary_parts)

    def classify_challenge_type(self, challenge: Dict[str, Any]) -> str:
        """
        分类挑战类型

        Returns:
            challenge_type: "deeper_insight" | "uncertainty_clarification" | "competing_frames" | "other"
        """
        challenged_item = challenge.get("challenged_item", "").lower()
        rationale = challenge.get("rationale", "").lower()

        # 根据关键词判断类型
        if "更深" in rationale or "深刻" in rationale or "真正" in rationale:
            return "deeper_insight"
        elif "不确定" in challenged_item or "模糊" in challenged_item or "标记" in rationale:
            return "uncertainty_clarification"
        elif "框架" in challenged_item or "理解" in challenged_item or "诠释" in rationale:
            return "competing_frames"
        else:
            return "other"

    def decide_handling(self, challenge: Dict[str, Any], challenge_type: str) -> str:
        """
        决策挑战处理方式

        Args:
            challenge: 挑战详情
            challenge_type: 挑战类型

        Returns:
            handling_decision: "accept" | "revisit_ra" | "synthesize" | "escalate"
        """
        # 根据挑战类型决定处理方式
        if challenge_type == "deeper_insight":
            # 专家发现了更深的洞察 → 接受专家的重新诠释
            logger.info(" 决策: 接受专家的更深洞察")
            return "accept"

        elif challenge_type == "uncertainty_clarification":
            # 专家标记了不确定性需要澄清 → 回访需求分析师或用户
            logger.info(" 决策: 回访需求分析师或用户确认")
            return "revisit_ra"

        elif challenge_type == "competing_frames":
            # 存在竞争性框架 → 综合多个方案
            logger.info(" 决策: 综合多个诠释框架")
            return "synthesize"

        else:
            # 其他情况 → 交甲方裁决
            logger.info(" 决策: 交甲方裁决")
            return "escalate"

    def handle_challenges(self, detection_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理所有检测到的挑战

        Returns:
            handling_result: {
                "handling_decisions": List[Dict],  # 每个挑战的处理决策
                "requires_revisit": bool,          # 是否需要回访需求分析师
                "requires_synthesis": bool,        # 是否需要综合多方案
                "escalated_challenges": List[Dict] # 需要交甲方裁决的挑战
            }
        """
        if not detection_result["has_challenges"]:
            return {
                "handling_decisions": [],
                "requires_revisit": False,
                "requires_synthesis": False,
                "escalated_challenges": [],
            }

        handling_decisions = []
        requires_revisit = False
        requires_synthesis = False
        escalated_challenges = []

        for challenge in detection_result["challenges"]:
            # 分类
            challenge_type = self.classify_challenge_type(challenge)

            # 决策
            decision = self.decide_handling(challenge, challenge_type)

            handling_decisions.append({"challenge": challenge, "challenge_type": challenge_type, "decision": decision})

            # 更新标志
            if decision == "revisit_ra":
                requires_revisit = True
            elif decision == "synthesize":
                requires_synthesis = True
            elif decision == "escalate":
                escalated_challenges.append(challenge)

        result = {
            "handling_decisions": handling_decisions,
            "requires_revisit": requires_revisit,
            "requires_synthesis": requires_synthesis,
            "escalated_challenges": escalated_challenges,
        }

        logger.info(f" 挑战处理完成: 回访={requires_revisit}, 综合={requires_synthesis}, 升级={len(escalated_challenges)}")

        return result

    def get_challenge_log(self) -> List[Dict]:
        """获取完整的挑战日志"""
        return self.challenge_log


def _apply_accepted_reinterpretation(state: Dict[str, Any], challenge: Dict[str, Any]) -> None:
    """
    应用被接受的专家重新诠释 - Accept决策的闭环逻辑

    将专家的新洞察更新到state中，使其对后续分析和报告生成可见

    Args:
        state: 工作流状态（会被原地修改）
        challenge: 包含专家重新诠释的挑战详情
    """
    #  P0修复: 防御性检查
    if not isinstance(challenge, dict):
        logger.error(f" _apply_accepted_reinterpretation 收到非字典类型challenge: {type(challenge)}")
        return

    expert_role = challenge.get("expert_role", "unknown")
    challenged_item = challenge.get("challenged_item", "")
    reinterpretation = challenge.get("reinterpretation", "")
    design_impact = challenge.get("design_impact", "")

    # 初始化expert_driven_insights字段
    if "expert_driven_insights" not in state:
        state["expert_driven_insights"] = {}

    # 记录采纳的新洞察
    state["expert_driven_insights"][challenged_item] = {
        "original_interpretation": "需求分析师的初始判断",
        "expert_reinterpretation": reinterpretation,
        "accepted_from": expert_role,
        "design_impact": design_impact,
        "timestamp": datetime.now().isoformat(),
        "status": "accepted",
    }

    # 通知机制：记录洞察更新，供其他专家参考
    if "insight_updates" not in state:
        state["insight_updates"] = []

    state["insight_updates"].append(
        {
            "item": challenged_item,
            "new_interpretation": reinterpretation,
            "source": expert_role,
            "reason": "专家提出更深洞察，已被项目总监接受",
        }
    )

    logger.info(f" [Accept闭环] 采纳{expert_role}对'{challenged_item}'的重新诠释")


def _synthesize_competing_frames(state: Dict[str, Any], challenges: List[Dict[str, Any]]) -> None:
    """
    综合多个竞争性框架 - Synthesize决策的闭环逻辑

    当多个专家对同一事项提出不同诠释时，综合成混合方案

    Args:
        state: 工作流状态（会被原地修改）
        challenges: 需要综合的挑战列表
    """
    if not challenges:
        return

    # 提取所有竞争性框架
    competing_interpretations = []
    for challenge in challenges:
        competing_interpretations.append(
            {
                "expert": challenge.get("expert_role", "unknown"),
                "challenged_item": challenge.get("challenged_item", ""),
                "interpretation": challenge.get("reinterpretation", ""),
                "rationale": challenge.get("rationale", ""),
                "design_impact": challenge.get("design_impact", ""),
            }
        )

    # 分组：按challenged_item分组
    from collections import defaultdict

    grouped = defaultdict(list)
    for interp in competing_interpretations:
        grouped[interp["challenged_item"]].append(interp)

    # 为每个有竞争的项生成综合方案
    if "framework_synthesis" not in state:
        state["framework_synthesis"] = {}

    for item, interpretations in grouped.items():
        if len(interpretations) > 1:
            # 多个框架需要综合
            synthesis_summary = f"检测到{len(interpretations)}个竞争性框架:\n"
            for i, interp in enumerate(interpretations, 1):
                synthesis_summary += f"{i}. {interp['expert']}: {interp['interpretation'][:100]}...\n"

            state["framework_synthesis"][item] = {
                "competing_frames": interpretations,
                "synthesis_summary": synthesis_summary,
                "recommendation": "建议在报告中并列展示多个方案，根据具体情境选择",
                "requires_deep_analysis": True,
            }

            logger.info(f" [Synthesize闭环] 综合{len(interpretations)}个关于'{item}'的竞争性框架")

    # 标记需要综合
    state["has_competing_frameworks"] = True
    state["synthesis_required"] = True


def detect_and_handle_challenges_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    工作流节点：挑战检测与处理 + 闭环执行

    在所有专家完成输出后调用，检测challenge_flags并决策处理方式

     v3.5.1 新增闭环机制:
    - Accept决策: 更新expert_driven_insights
    - Synthesize决策: 综合竞争性框架
    - Escalate决策: 标记需要甲方裁决

    Args:
        state: 工作流状态，包含所有专家的输出

    Returns:
        更新的状态，包含挑战检测和处理结果
    """
    logger.info(" 开始检测专家挑战...")

    # 初始化检测器
    detector = ChallengeDetector()

    # 收集所有专家输出
    expert_outputs = {}

    #  修复：从正确的字段读取专家输出
    # 专家输出存储在 state["agent_results"] 中
    agent_results = state.get("agent_results", {})

    logger.debug(f" 开始扫描 {len(agent_results)} 个专家输出...")

    for agent_id, agent_data in agent_results.items():
        # agent_data 是 AgentExecutionResult 对象转换的字典
        if isinstance(agent_data, dict):
            # 提取 structured_data 字段（专家的结构化输出）
            structured_data = agent_data.get("structured_data", {})
            if structured_data:
                expert_outputs[agent_id] = structured_data
                logger.debug(f"    提取 {agent_id} 的输出 (包含 {len(structured_data.keys())} 个字段)")
            elif agent_data.get("challenge_flags"):
                # 兼容旧格式：challenge_flags 直接附着在 agent_data 上
                expert_outputs[agent_id] = agent_data
                logger.debug(f"    从 {agent_id} 捕获直连的 challenge_flags")
            else:
                logger.debug(f"   ️ {agent_id} 的 structured_data 为空")

    #  兼容批次聚合结果中的 challenge_flags（tests 直接写在 batch_results 中）
    batch_results = state.get("batch_results", {})
    for batch_id, batch_data in batch_results.items():
        if not isinstance(batch_data, dict):
            continue
        for agent_id, agent_payload in batch_data.items():
            if not isinstance(agent_payload, dict):
                continue

            candidate = (
                agent_payload.get("structured_data")
                if isinstance(agent_payload.get("structured_data"), dict)
                else agent_payload
            )
            if isinstance(candidate, dict) and candidate.get("challenge_flags"):
                if agent_id not in expert_outputs:
                    expert_outputs[agent_id] = candidate
                    logger.debug(f"    从 batch {batch_id} 捕获 {agent_id} 的 challenge_flags")

    # 检测挑战
    detection_result = detector.detect_challenges(expert_outputs)

    # 处理挑战
    handling_result = detector.handle_challenges(detection_result)

    # 更新state（只返回新增/修改的字段，避免与上游节点的状态更新冲突）
    updated_state = {
        "challenge_detection": detection_result,
        "challenge_handling": handling_result,
        "has_active_challenges": detection_result["has_challenges"],
        "requires_feedback_loop": handling_result["requires_revisit"],
    }

    #  执行闭环逻辑
    handling_decisions = handling_result.get("handling_decisions", [])

    # 1️⃣ Accept闭环: 应用被接受的重新诠释
    accepted_challenges = [d["challenge"] for d in handling_decisions if d["decision"] == "accept"]
    for challenge in accepted_challenges:
        _apply_accepted_reinterpretation(state, challenge)

    if accepted_challenges:
        updated_state["accepted_reinterpretations_count"] = len(accepted_challenges)
        logger.info(f" [Accept闭环] 应用了{len(accepted_challenges)}个专家的重新诠释")

    # 2️⃣ Synthesize闭环: 综合竞争性框架
    if handling_result.get("requires_synthesis"):
        synthesis_challenges = [d["challenge"] for d in handling_decisions if d["decision"] == "synthesize"]
        _synthesize_competing_frames(state, synthesis_challenges)
        updated_state["synthesis_required"] = True
        logger.info(f" [Synthesize闭环] 综合了{len(synthesis_challenges)}个竞争性框架")

    # 3️⃣ Escalate闭环: 标记需要甲方裁决的挑战
    escalated = handling_result.get("escalated_challenges", [])
    if escalated:
        # 格式化为审核系统能理解的问题格式
        escalated_issues = []
        for challenge in escalated:
            escalated_issues.append(
                {
                    "issue_id": f"CHALLENGE_{challenge.get('expert_role', 'unknown')}_{datetime.now().strftime('%H%M%S')}",
                    "type": "strategic_decision",
                    "severity": "high",
                    "description": f"{challenge.get('expert_role')}挑战了'{challenge.get('challenged_item')}'",
                    "expert_rationale": challenge.get("rationale", ""),
                    "reinterpretation": challenge.get("reinterpretation", ""),
                    "design_impact": challenge.get("design_impact", ""),
                    "requires_client_decision": True,
                }
            )

        updated_state["escalated_challenges"] = escalated_issues
        updated_state["requires_client_review"] = True
        logger.warning(f" [Escalate闭环] {len(escalated)}个挑战需要甲方裁决")

    # 如果需要回访，记录原因
    if handling_result["requires_revisit"]:
        logger.warning("️ 检测到需要回访需求分析师的挑战")
        updated_state["feedback_loop_reason"] = "Expert challenges require clarification"

    return updated_state
