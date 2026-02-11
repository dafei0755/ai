"""
挑战检测智能体 (LangGraph StateGraph)

 v7.16: 将 detect_challenges_node 升级为真正的 LangGraph Agent
 v7.16.1: 添加性能监控和共享工具函数

核心功能:
1. 扫描专家输出 (Scan Outputs)
2. 分类挑战类型 (Classify Challenges)
3. 决定路由 (Route Decision)

节点流转:
    scan_outputs → classify_challenges → route_decision → END
"""

from typing import TypedDict, Dict, Any, List, Optional, Literal
from loguru import logger
from datetime import datetime
import time

from langgraph.graph import StateGraph, START, END

# 导入共享工具函数
from ..utils.shared_agent_utils import (
    PerformanceMonitor,
    extract_challenge_flags,
    classify_challenges as shared_classify_challenges
)


# ============================================================================
# 状态定义
# ============================================================================

class ChallengeDetectionState(TypedDict):
    """挑战检测智能体状态"""
    
    # 输入
    agent_results: Dict[str, Any]   # 所有专家的分析结果
    batch_results: Dict[str, Any]   # 批次结果
    
    # 中间状态
    raw_challenges: List[Dict]      # 原始挑战列表
    classified_challenges: List[Dict]  # 分类后的挑战
    
    # 输出
    challenge_detection: Dict[str, Any]   # 挑战检测结果
    challenge_handling: Dict[str, Any]    # 挑战处理结果
    has_active_challenges: bool           # 是否有活跃挑战
    requires_feedback_loop: bool          # 是否需要反馈循环
    requires_client_review: bool          # 是否需要甲方审核
    requires_manual_review: bool          # 是否需要人工审核
    escalated_challenges: List[Dict]      # 升级的挑战列表
    feedback_loop_reason: str             # 反馈循环原因
    
    # 处理日志
    processing_log: List[str]


# ============================================================================
# 节点函数
# ============================================================================

def scan_outputs_node(state: ChallengeDetectionState) -> Dict[str, Any]:
    """
    扫描专家输出节点 - 提取所有挑战标记
    """
    logger.info(" 执行专家输出扫描节点")
    
    agent_results = state.get("agent_results", {})
    batch_results = state.get("batch_results", {})
    
    raw_challenges = []
    
    # 扫描 agent_results
    for agent_id, result in agent_results.items():
        if not isinstance(result, dict):
            continue
        
        # 检查 challenge_flags
        challenge_flags = result.get("challenge_flags", [])
        if challenge_flags:
            for flag in challenge_flags:
                raw_challenges.append({
                    "agent_id": agent_id,
                    "type": "challenge_flag",
                    "content": flag,
                    "source": "agent_results"
                })
        
        # 检查 proactivity_protocol
        proactivity = result.get("proactivity_protocol", {})
        if proactivity:
            identified = proactivity.get("challenge_identified", False)
            if identified:
                raw_challenges.append({
                    "agent_id": agent_id,
                    "type": "proactivity_challenge",
                    "content": proactivity.get("challenge_description", ""),
                    "hypothesis": proactivity.get("hypothesis", ""),
                    "proposed_action": proactivity.get("proposed_action", ""),
                    "source": "proactivity_protocol"
                })
        
        # 检查执行元数据中的问题
        exec_meta = result.get("execution_metadata", {})
        if exec_meta:
            issues = exec_meta.get("issues_encountered", [])
            for issue in issues:
                raw_challenges.append({
                    "agent_id": agent_id,
                    "type": "execution_issue",
                    "content": issue,
                    "source": "execution_metadata"
                })
    
    # 扫描 batch_results
    for batch_id, batch_data in batch_results.items():
        if isinstance(batch_data, dict):
            for agent_id, result in batch_data.items():
                if isinstance(result, dict):
                    flags = result.get("challenge_flags", [])
                    for flag in flags:
                        raw_challenges.append({
                            "agent_id": agent_id,
                            "batch_id": batch_id,
                            "type": "batch_challenge",
                            "content": flag,
                            "source": "batch_results"
                        })
    
    log_entry = f" 扫描完成: 发现 {len(raw_challenges)} 个原始挑战"
    logger.info(log_entry)
    
    return {
        "raw_challenges": raw_challenges,
        "processing_log": [log_entry]
    }


def classify_challenges_node(state: ChallengeDetectionState) -> Dict[str, Any]:
    """
    分类挑战节点 - 对挑战进行分类和优先级排序
    """
    logger.info(" 执行挑战分类节点")
    
    raw_challenges = state.get("raw_challenges", [])
    
    classified = []
    
    for challenge in raw_challenges:
        content = str(challenge.get("content", "")).lower()
        challenge_type = challenge.get("type", "unknown")
        
        # 分类规则
        severity = "low"
        category = "general"
        requires_escalation = False
        
        # 严重性判断
        if any(kw in content for kw in ["critical", "严重", "必须", "紧急", "阻塞"]):
            severity = "high"
            requires_escalation = True
        elif any(kw in content for kw in ["important", "重要", "应该", "建议"]):
            severity = "medium"
        
        # 类别判断
        if any(kw in content for kw in ["需求", "requirement", "用户", "甲方"]):
            category = "requirement_clarification"
        elif any(kw in content for kw in ["技术", "technical", "实现", "可行性"]):
            category = "technical_feasibility"
        elif any(kw in content for kw in ["冲突", "矛盾", "不一致"]):
            category = "consistency_issue"
        elif any(kw in content for kw in ["信息", "缺失", "不足", "unclear"]):
            category = "information_gap"
        
        classified.append({
            **challenge,
            "severity": severity,
            "category": category,
            "requires_escalation": requires_escalation
        })
    
    # 按严重性排序
    severity_order = {"high": 0, "medium": 1, "low": 2}
    classified.sort(key=lambda x: severity_order.get(x.get("severity", "low"), 2))
    
    log_entry = f" 分类完成: {len([c for c in classified if c.get('severity') == 'high'])} high, {len([c for c in classified if c.get('severity') == 'medium'])} medium, {len([c for c in classified if c.get('severity') == 'low'])} low"
    logger.info(log_entry)
    
    return {
        "classified_challenges": classified,
        "processing_log": [log_entry]
    }


def route_decision_node(state: ChallengeDetectionState) -> Dict[str, Any]:
    """
    路由决策节点 - 决定后续处理路径
    """
    logger.info(" 执行路由决策节点")
    
    classified = state.get("classified_challenges", [])
    
    # 统计
    high_severity = [c for c in classified if c.get("severity") == "high"]
    medium_severity = [c for c in classified if c.get("severity") == "medium"]
    escalation_needed = [c for c in classified if c.get("requires_escalation")]
    
    # 决策逻辑
    has_active_challenges = len(classified) > 0
    requires_feedback_loop = False
    requires_client_review = False
    requires_manual_review = False
    feedback_loop_reason = ""
    
    # 规则1: 超过3个high严重性问题 → 人工审核
    if len(high_severity) > 3:
        requires_manual_review = True
        feedback_loop_reason = f"发现{len(high_severity)}个严重问题，需要人工介入"
    
    # 规则2: 需要升级的挑战 → 甲方审核
    elif len(escalation_needed) > 0:
        requires_client_review = True
        feedback_loop_reason = f"{len(escalation_needed)}个挑战需要甲方裁决"
    
    # 规则3: 需求澄清类挑战 → 反馈循环
    elif any(c.get("category") == "requirement_clarification" for c in classified):
        requires_feedback_loop = True
        feedback_loop_reason = "存在需求澄清问题，需要回访需求分析师"
    
    # 构建检测结果
    challenge_detection = {
        "has_challenges": has_active_challenges,
        "challenges": classified,
        "high_count": len(high_severity),
        "medium_count": len(medium_severity),
        "total_count": len(classified)
    }
    
    challenge_handling = {
        "requires_revisit": requires_feedback_loop,
        "requires_escalation": requires_client_review,
        "requires_manual": requires_manual_review,
        "reason": feedback_loop_reason
    }
    
    log_entry = f" 路由决策: manual={requires_manual_review}, client={requires_client_review}, feedback={requires_feedback_loop}"
    logger.info(log_entry)
    
    return {
        "challenge_detection": challenge_detection,
        "challenge_handling": challenge_handling,
        "has_active_challenges": has_active_challenges,
        "requires_feedback_loop": requires_feedback_loop,
        "requires_client_review": requires_client_review,
        "requires_manual_review": requires_manual_review,
        "escalated_challenges": escalation_needed,
        "feedback_loop_reason": feedback_loop_reason,
        "processing_log": [log_entry]
    }


# ============================================================================
# 状态图构建
# ============================================================================

def build_challenge_detection_graph() -> StateGraph:
    """
    构建挑战检测状态图
    
    流程:
        START → scan_outputs → classify_challenges → route_decision → END
    """
    workflow = StateGraph(ChallengeDetectionState)
    
    # 添加节点
    workflow.add_node("scan_outputs", scan_outputs_node)
    workflow.add_node("classify_challenges", classify_challenges_node)
    workflow.add_node("route_decision", route_decision_node)
    
    # 添加边
    workflow.add_edge(START, "scan_outputs")
    workflow.add_edge("scan_outputs", "classify_challenges")
    workflow.add_edge("classify_challenges", "route_decision")
    workflow.add_edge("route_decision", END)
    
    return workflow


# ============================================================================
# Agent 封装类
# ============================================================================

class ChallengeDetectionAgent:
    """
    挑战检测智能体 - LangGraph 封装
    
    使用方式:
        agent = ChallengeDetectionAgent()
        result = agent.execute(state)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化挑战检测智能体"""
        self.config = config or {}
        
        # 构建并编译状态图
        self._graph = build_challenge_detection_graph().compile()
        
        logger.info(" ChallengeDetectionAgent (LangGraph) 已初始化")
    
    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行挑战检测
        
        Args:
            state: 项目分析状态
            
        Returns:
            挑战检测结果字典
        """
        logger.info(" ChallengeDetectionAgent 开始执行")
        
        # 准备初始状态
        initial_state = {
            "agent_results": state.get("agent_results", {}),
            "batch_results": state.get("batch_results", {}),
            
            # 初始化中间状态
            "raw_challenges": [],
            "classified_challenges": [],
            
            # 初始化输出
            "challenge_detection": {},
            "challenge_handling": {},
            "has_active_challenges": False,
            "requires_feedback_loop": False,
            "requires_client_review": False,
            "requires_manual_review": False,
            "escalated_challenges": [],
            "feedback_loop_reason": "",
            "processing_log": []
        }
        
        # 执行状态图
        try:
            final_state = self._graph.invoke(initial_state)
            
            result = {
                "challenge_detection": final_state.get("challenge_detection", {}),
                "challenge_handling": final_state.get("challenge_handling", {}),
                "has_active_challenges": final_state.get("has_active_challenges", False),
                "requires_feedback_loop": final_state.get("requires_feedback_loop", False),
                "requires_client_review": final_state.get("requires_client_review", False),
                "requires_manual_review": final_state.get("requires_manual_review", False),
                "escalated_challenges": final_state.get("escalated_challenges", []),
                "feedback_loop_reason": final_state.get("feedback_loop_reason", ""),
                "processing_log": final_state.get("processing_log", [])
            }
            
            logger.info(f" ChallengeDetectionAgent 完成: {result['challenge_detection'].get('total_count', 0)} 个挑战")
            return result
            
        except Exception as e:
            logger.error(f" ChallengeDetectionAgent 执行失败: {e}")
            import traceback
            traceback.print_exc()
            
            # 返回安全的默认值
            return {
                "challenge_detection": {"has_challenges": False, "challenges": []},
                "challenge_handling": {"requires_revisit": False},
                "has_active_challenges": False,
                "requires_feedback_loop": False,
                "requires_client_review": False,
                "requires_manual_review": False,
                "escalated_challenges": [],
                "feedback_loop_reason": "",
                "processing_log": [f" 执行失败: {e}"],
                "error": str(e)
            }


# ============================================================================
# 向后兼容函数
# ============================================================================

def detect_and_handle_challenges_v2(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    向后兼容函数 - 替换原有的 detect_and_handle_challenges_node
    
     v7.16.1: 添加性能监控
    """
    start_time = time.time()
    agent = ChallengeDetectionAgent()
    result = agent.execute(state)
    
    # 记录性能指标
    execution_time = time.time() - start_time
    PerformanceMonitor.record("ChallengeDetectionAgent", execution_time, "v7.16")
    
    return result
