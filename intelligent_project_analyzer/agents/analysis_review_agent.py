"""
分析审核智能体 (LangGraph StateGraph)

🔥 v7.16: 将 AnalysisReviewNode 升级为真正的 LangGraph Agent

核心功能:
1. 红蓝对抗 (Red-Blue Debate)
2. 甲方决策 (Client Review)
3. 生成最终裁定 (Final Ruling)
4. 改进建议输出 (Improvement Suggestions)

节点流转:
    red_blue_debate → client_review → generate_ruling → END
"""

from typing import TypedDict, Dict, Any, List, Optional, Literal
from loguru import logger
from datetime import datetime
import time

from langgraph.graph import StateGraph, START, END
from langgraph.types import Command

from ..utils.shared_agent_utils import PerformanceMonitor
from ..review.review_agents import (
    RedTeamReviewer,
    BlueTeamReviewer,
    ClientReviewer
)


# ============================================================================
# 状态定义
# ============================================================================

class AnalysisReviewState(TypedDict):
    """分析审核智能体状态"""
    
    # 输入
    agent_results: Dict[str, Any]  # 所有专家的分析结果
    requirements: Dict[str, Any]   # 项目需求
    review_iteration_round: int    # 当前审核轮次
    
    # 中间状态
    red_review: Dict[str, Any]     # 红队审核结果
    blue_review: Dict[str, Any]    # 蓝队审核结果
    red_blue_debate: Dict[str, Any]  # 红蓝对抗结果
    client_review: Dict[str, Any]  # 甲方审核结果
    
    # 输出
    final_ruling: str              # 最终裁定文档
    improvement_suggestions: List[Dict[str, Any]]  # 改进建议列表
    must_fix_count: int            # must_fix问题数量
    analysis_approved: bool        # 审核是否通过
    agents_to_improve: List[str]   # 需要整改的专家ID
    
    # 处理日志
    processing_log: List[str]


# ============================================================================
# 节点函数
# ============================================================================

def red_blue_debate_node(state: AnalysisReviewState) -> Dict[str, Any]:
    """
    红蓝对抗节点 - 发现问题并辩护
    
    红队：批判性审查，找问题
    蓝队：防御性辩护，过滤误判
    """
    logger.info("⚔️ 执行红蓝对抗节点")
    
    agent_results = state.get("agent_results", {})
    requirements = state.get("requirements", {})
    
    # 准备审核内容
    review_content = _prepare_review_content(agent_results, requirements)
    
    # 获取 LLM 模型（从配置或默认）
    llm_model = state.get("_llm_model")
    
    if not llm_model:
        logger.warning("⚠️ 未提供 LLM 模型，使用空结果")
        return {
            "red_review": {"issues": [], "overall_assessment": "未执行"},
            "blue_review": {"defenses": [], "overall_assessment": "未执行"},
            "red_blue_debate": {"issues": [], "validated_issues": []},
            "processing_log": ["⚠️ 红蓝对抗跳过：未提供LLM模型"]
        }
    
    # 执行红队审核
    logger.info("🔴 红队审核：批判性分析...")
    red_team = RedTeamReviewer(llm_model)
    red_review = red_team.review(review_content)
    
    # 执行蓝队审核（基于红队结果）
    logger.info("🔵 蓝队审核：防御性辩护...")
    blue_team = BlueTeamReviewer(llm_model)
    blue_review = blue_team.review(review_content, red_review)
    
    # 合成红蓝对抗结果
    red_issues = red_review.get("issues", [])
    blue_defenses = blue_review.get("defenses", [])
    
    # 计算验证后的问题（被蓝队认可的问题）
    validated_issues = []
    for issue in red_issues:
        issue_id = issue.get("id", "")
        # 查找蓝队是否认可这个问题
        defense = next(
            (d for d in blue_defenses if d.get("issue_id") == issue_id),
            None
        )
        if defense and defense.get("acknowledged", False):
            validated_issues.append({
                **issue,
                "blue_defense": defense.get("defense", ""),
                "final_severity": defense.get("adjusted_severity", issue.get("severity", "medium"))
            })
    
    red_blue_debate = {
        "red_review": red_review,
        "blue_review": blue_review,
        "issues": red_issues,
        "validated_issues": validated_issues,
        "total_issues": len(red_issues),
        "validated_count": len(validated_issues)
    }
    
    log_entry = f"⚔️ 红蓝对抗完成：红队发现{len(red_issues)}个问题，蓝队验证{len(validated_issues)}个"
    logger.info(log_entry)
    
    return {
        "red_review": red_review,
        "blue_review": blue_review,
        "red_blue_debate": red_blue_debate,
        "processing_log": [log_entry]
    }


def client_review_node(state: AnalysisReviewState) -> Dict[str, Any]:
    """
    甲方决策节点 - 基于红蓝对抗结果做最终决策
    """
    logger.info("👔 执行甲方决策节点")
    
    agent_results = state.get("agent_results", {})
    requirements = state.get("requirements", {})
    red_blue_debate = state.get("red_blue_debate", {})
    
    # 准备审核内容
    review_content = _prepare_review_content(agent_results, requirements)
    
    # 获取 LLM 模型
    llm_model = state.get("_llm_model")
    
    if not llm_model:
        logger.warning("⚠️ 未提供 LLM 模型，使用默认决策")
        return {
            "client_review": {
                "final_decision": "approve",
                "confidence": 0.5,
                "reasoning": "未执行LLM审核，默认通过"
            },
            "processing_log": ["⚠️ 甲方决策跳过：未提供LLM模型"]
        }
    
    # 执行甲方审核
    client_reviewer = ClientReviewer(llm_model)
    client_review = client_reviewer.review(
        review_content,
        red_blue_debate
    )
    
    final_decision = client_review.get("final_decision", "approve")
    log_entry = f"👔 甲方决策完成：{final_decision}"
    logger.info(log_entry)
    
    return {
        "client_review": client_review,
        "processing_log": [log_entry]
    }


def generate_ruling_node(state: AnalysisReviewState) -> Dict[str, Any]:
    """
    生成最终裁定节点 - 汇总审核结果，生成改进建议
    """
    logger.info("📋 生成最终裁定")
    
    red_blue_debate = state.get("red_blue_debate", {})
    client_review = state.get("client_review", {})
    review_iteration_round = state.get("review_iteration_round", 0)
    
    # 提取验证后的问题
    validated_issues = red_blue_debate.get("validated_issues", [])
    
    # 生成改进建议
    improvement_suggestions = []
    for issue in validated_issues:
        suggestion = {
            "issue_id": issue.get("id", ""),
            "agent_id": issue.get("agent_id", issue.get("responsible_agent", "")),
            "description": issue.get("description", ""),
            "suggestion": issue.get("recommendation", ""),
            "priority": issue.get("final_severity", "medium"),
            "category": issue.get("category", "quality")
        }
        
        # 标记 must_fix
        if issue.get("final_severity") in ["critical", "high"]:
            suggestion["priority"] = "must_fix"
        
        improvement_suggestions.append(suggestion)
    
    # 统计 must_fix 数量
    must_fix_count = len([s for s in improvement_suggestions if s.get("priority") == "must_fix"])
    
    # 提取需要整改的专家
    agents_to_improve = list(set(
        s.get("agent_id", "") for s in improvement_suggestions 
        if s.get("priority") == "must_fix" and s.get("agent_id")
    ))
    
    # 判断审核是否通过
    final_decision = client_review.get("final_decision", "approve")
    analysis_approved = (
        final_decision == "approve" or
        (must_fix_count == 0) or
        (review_iteration_round >= 1)  # 已达到最大迭代次数
    )
    
    # 生成裁定文档
    final_ruling = _generate_ruling_document(
        red_blue_debate,
        client_review,
        improvement_suggestions,
        analysis_approved
    )
    
    log_entry = f"📋 裁定生成完成：{must_fix_count}个must_fix问题，{'通过' if analysis_approved else '需整改'}"
    logger.info(log_entry)
    
    return {
        "final_ruling": final_ruling,
        "improvement_suggestions": improvement_suggestions,
        "must_fix_count": must_fix_count,
        "analysis_approved": analysis_approved,
        "agents_to_improve": agents_to_improve,
        "processing_log": [log_entry]
    }


# ============================================================================
# 辅助函数
# ============================================================================

def _prepare_review_content(agent_results: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, Any]:
    """准备审核内容"""
    return {
        "agent_results": agent_results,
        "requirements": requirements,
        "timestamp": datetime.now().isoformat()
    }


def _generate_ruling_document(
    red_blue_debate: Dict[str, Any],
    client_review: Dict[str, Any],
    improvement_suggestions: List[Dict[str, Any]],
    analysis_approved: bool
) -> str:
    """生成最终裁定文档"""
    
    must_fix = [s for s in improvement_suggestions if s.get("priority") == "must_fix"]
    should_fix = [s for s in improvement_suggestions if s.get("priority") != "must_fix"]
    
    ruling = f"""
# 分析审核裁定文档

## 审核结论
- **状态**: {'✅ 审核通过' if analysis_approved else '⚠️ 需要整改'}
- **甲方决策**: {client_review.get('final_decision', 'N/A')}
- **红蓝对抗问题数**: {red_blue_debate.get('total_issues', 0)}
- **验证后问题数**: {red_blue_debate.get('validated_count', 0)}

## Must-Fix 问题 ({len(must_fix)}项)
"""
    
    for i, issue in enumerate(must_fix, 1):
        ruling += f"""
### {i}. {issue.get('description', '未知问题')}
- **责任专家**: {issue.get('agent_id', '未知')}
- **建议**: {issue.get('suggestion', '无')}
"""
    
    ruling += f"""
## Should-Fix 建议 ({len(should_fix)}项)
"""
    
    for i, issue in enumerate(should_fix, 1):
        ruling += f"- {issue.get('description', '未知')}\n"
    
    return ruling


# ============================================================================
# 状态图构建
# ============================================================================

def build_analysis_review_graph() -> StateGraph:
    """
    构建分析审核状态图
    
    流程:
        START → red_blue_debate → client_review → generate_ruling → END
    """
    workflow = StateGraph(AnalysisReviewState)
    
    # 添加节点
    workflow.add_node("red_blue_debate", red_blue_debate_node)
    workflow.add_node("client_review", client_review_node)
    workflow.add_node("generate_ruling", generate_ruling_node)
    
    # 添加边
    workflow.add_edge(START, "red_blue_debate")
    workflow.add_edge("red_blue_debate", "client_review")
    workflow.add_edge("client_review", "generate_ruling")
    workflow.add_edge("generate_ruling", END)
    
    return workflow


# ============================================================================
# Agent 封装类
# ============================================================================

class AnalysisReviewAgent:
    """
    分析审核智能体 - LangGraph 封装
    
    使用方式:
        agent = AnalysisReviewAgent(llm_model)
        result = agent.execute(agent_results, requirements)
    """
    
    def __init__(self, llm_model, config: Optional[Dict[str, Any]] = None):
        """
        初始化分析审核智能体
        
        Args:
            llm_model: LLM模型实例
            config: 配置参数
        """
        self.llm_model = llm_model
        self.config = config or {}
        
        # 构建并编译状态图
        self._graph = build_analysis_review_graph().compile()
        
        logger.info("🚀 AnalysisReviewAgent (LangGraph) 已初始化")
    
    def execute(
        self,
        agent_results: Dict[str, Any],
        requirements: Dict[str, Any],
        review_iteration_round: int = 0
    ) -> Dict[str, Any]:
        """
        执行分析审核
        
        Args:
            agent_results: 所有专家的分析结果
            requirements: 项目需求
            review_iteration_round: 当前审核轮次
            
        Returns:
            审核结果字典
        """
        logger.info(f"🎯 AnalysisReviewAgent 开始审核 (轮次 {review_iteration_round})")
        start_time = time.time()
        
        # 准备初始状态
        initial_state = {
            "agent_results": agent_results,
            "requirements": requirements,
            "review_iteration_round": review_iteration_round,
            "_llm_model": self.llm_model,  # 传递LLM模型
            
            # 初始化中间状态
            "red_review": {},
            "blue_review": {},
            "red_blue_debate": {},
            "client_review": {},
            
            # 初始化输出
            "final_ruling": "",
            "improvement_suggestions": [],
            "must_fix_count": 0,
            "analysis_approved": False,
            "agents_to_improve": [],
            "processing_log": []
        }
        
        # 执行状态图
        try:
            final_state = self._graph.invoke(initial_state)
            
            # 提取结果
            result = {
                "final_ruling": final_state.get("final_ruling", ""),
                "improvement_suggestions": final_state.get("improvement_suggestions", []),
                "must_fix_count": final_state.get("must_fix_count", 0),
                "analysis_approved": final_state.get("analysis_approved", False),
                "agents_to_improve": final_state.get("agents_to_improve", []),
                "red_blue_debate": final_state.get("red_blue_debate", {}),
                "client_review": final_state.get("client_review", {}),
                "processing_log": final_state.get("processing_log", [])
            }
            
            # 记录性能指标
            PerformanceMonitor.record("AnalysisReviewAgent", time.time() - start_time, "v7.16")
            
            logger.info(f"✅ AnalysisReviewAgent 完成: {result['must_fix_count']} must_fix, approved={result['analysis_approved']}")
            return result
            
        except Exception as e:
            # 记录失败时的性能指标
            PerformanceMonitor.record("AnalysisReviewAgent", time.time() - start_time, "v7.16-error")
            
            logger.error(f"❌ AnalysisReviewAgent 执行失败: {e}")
            import traceback
            traceback.print_exc()
            
            # 返回安全的默认值
            return {
                "final_ruling": "审核执行失败",
                "improvement_suggestions": [],
                "must_fix_count": 0,
                "analysis_approved": True,  # 失败时默认通过，避免阻塞流程
                "agents_to_improve": [],
                "red_blue_debate": {},
                "client_review": {},
                "processing_log": [f"❌ 执行失败: {e}"],
                "error": str(e)
            }
    
    async def execute_async(
        self,
        agent_results: Dict[str, Any],
        requirements: Dict[str, Any],
        review_iteration_round: int = 0
    ) -> Dict[str, Any]:
        """异步执行分析审核"""
        # 当前实现与同步版本相同，后续可优化为真正异步
        return self.execute(agent_results, requirements, review_iteration_round)


# ============================================================================
# 向后兼容层
# ============================================================================

class AnalysisReviewNodeCompat:
    """
    向后兼容原 AnalysisReviewNode 接口
    
    用于平滑迁移，不修改 main_workflow.py 的调用方式
    """
    
    _agent: Optional[AnalysisReviewAgent] = None
    _llm_model = None
    
    @classmethod
    def initialize(cls, llm_model, config: Optional[Dict[str, Any]] = None):
        """初始化兼容层"""
        if cls._agent is None or cls._llm_model != llm_model:
            cls._llm_model = llm_model
            cls._agent = AnalysisReviewAgent(llm_model, config)
    
    @classmethod
    def execute(
        cls,
        state: Dict[str, Any],
        store=None,
        llm_model=None,
        config: Optional[Dict[str, Any]] = None
    ) -> Command:
        """
        兼容原 AnalysisReviewNode.execute() 接口
        
        返回 Command 对象以兼容 main_workflow.py
        """
        from ..core.state import AnalysisStage
        
        # 初始化
        if llm_model:
            cls.initialize(llm_model, config)
        
        if cls._agent is None:
            logger.error("AnalysisReviewAgent 未初始化")
            return Command(
                update={"analysis_approved": True},
                goto="detect_challenges"
            )
        
        # 提取参数
        agent_results = state.get("agent_results", {})
        requirements = state.get("structured_requirements", {})
        review_iteration_round = state.get("review_iteration_round", 0)
        
        # 执行审核
        result = cls._agent.execute(
            agent_results,
            requirements,
            review_iteration_round
        )
        
        # 构建状态更新
        updated_state = {
            "current_stage": AnalysisStage.ANALYSIS_REVIEW.value,
            "review_result": result,
            "final_ruling": result.get("final_ruling", ""),
            "improvement_suggestions": result.get("improvement_suggestions", []),
            "analysis_approved": result.get("analysis_approved", True),
            "last_review_decision": result.get("client_review", {}).get("final_decision", "approve")
        }
        
        # 判断是否需要重做
        must_fix_count = result.get("must_fix_count", 0)
        agents_to_improve = result.get("agents_to_improve", [])
        
        if must_fix_count > 0 and review_iteration_round < 1 and agents_to_improve:
            logger.warning(f"🔄 发现{must_fix_count}个must_fix问题，触发专家整改")
            
            # 构建反馈
            agent_feedback = {}
            for agent_id in agents_to_improve:
                agent_issues = [
                    imp for imp in result.get("improvement_suggestions", [])
                    if imp.get("agent_id") == agent_id and imp.get("priority") == "must_fix"
                ]
                agent_feedback[agent_id] = {
                    "must_fix_issues": agent_issues,
                    "iteration_round": review_iteration_round + 1
                }
            
            updated_state["specific_agents_to_run"] = agents_to_improve
            updated_state["agent_feedback"] = agent_feedback
            updated_state["review_iteration_round"] = review_iteration_round + 1
            updated_state["skip_role_review"] = True
            updated_state["skip_task_review"] = True
            updated_state["is_rerun"] = True
            
            return Command(update=updated_state, goto="batch_executor")
        
        # 正常流程：继续到挑战检测
        return Command(update=updated_state, goto="detect_challenges")
