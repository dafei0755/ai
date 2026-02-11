"""
人工审核节点 - 处理严重质量问题

当审核系统发现超过3个must_fix问题时，暂停流程，由用户裁决后续处理方式
"""

from typing import Dict, Any, Literal, Optional
from loguru import logger
from langgraph.types import interrupt, Command
from langgraph.store.base import BaseStore

from ...core.state import ProjectAnalysisState, AnalysisStage
from ...core.types import InteractionType


class ManualReviewNode:
    """
    人工审核节点 - 严重质量问题拦截器
    
    职责：
    1. 当发现>3个must_fix问题时，暂停流程
    2. 展示问题详情给用户
    3. 提供三种处理选项：继续/终止/选择性整改
    4. 根据用户决策路由到相应节点
    """
    
    @staticmethod
    def execute(
        state: ProjectAnalysisState,
        store: Optional[BaseStore] = None
    ) -> Command[Literal["batch_executor", "detect_challenges", "END"]]:
        """
        执行人工审核交互
        
        Args:
            state: 项目分析状态
            store: 存储接口
            
        Returns:
            Command对象，指向下一个节点
        """
        logger.info("=" * 100)
        logger.info("️ 触发人工审核节点 - 发现严重质量问题")
        logger.info("=" * 100)
        
        # 获取问题详情
        issues_count = state.get("critical_issues_count", 0)
        improvement_suggestions = state.get("improvement_suggestions", [])
        review_result = state.get("review_result") or {}  #  修复：确保不为 None
        
        # 提取must_fix问题
        must_fix_issues = [
            imp for imp in improvement_suggestions 
            if imp.get('priority') == 'must_fix'
        ]
        
        # 按严重性排序（如果有severity字段）
        must_fix_issues.sort(
            key=lambda x: {'critical': 3, 'high': 2, 'medium': 1, 'low': 0}.get(
                x.get('severity', 'medium'), 1
            ),
            reverse=True
        )
        
        # 准备用户审核数据
        review_data = {
            "interaction_type": "manual_review_required",
            "message": f" 审核系统发现 {issues_count} 个严重质量问题（超过阈值3个），需要您的裁决",
            "severity": "critical",
            "issues_summary": {
                "total_must_fix": issues_count,
                "critical_count": sum(1 for i in must_fix_issues if i.get('severity') == 'critical'),
                "high_count": sum(1 for i in must_fix_issues if i.get('severity') == 'high')
            },
            "top_issues": [
                {
                    "id": issue.get('issue_id', f"ISSUE_{idx+1}"),
                    "description": issue.get('description', '未提供描述')[:150],
                    "priority": issue.get('priority', 'must_fix'),
                    "severity": issue.get('severity', 'high'),
                    "deadline": issue.get('deadline', 'before_launch')
                }
                for idx, issue in enumerate(must_fix_issues[:10])  # 最多显示10个
            ],
            "options": {
                "continue": {
                    "label": "接受风险，继续生成报告",
                    "description": "忽略这些问题，直接生成报告供参考（不推荐）",
                    "risk": "high"
                },
                "abort": {
                    "label": "终止流程，要求专家全面整改",
                    "description": "重新执行所有有问题的专家，整改后再生成报告",
                    "risk": "low"
                },
                "selective_fix": {
                    "label": "选择性整改关键问题",
                    "description": "您手动选择最关键的3个问题进行整改",
                    "risk": "medium"
                }
            },
            "recommendation": "建议选择 'abort' 或 'selective_fix'，确保报告质量"
        }
        
        logger.info(f"\n 问题统计:")
        logger.info(f"   - 必须修复: {issues_count} 个")
        logger.info(f"   - Critical: {review_data['issues_summary']['critical_count']} 个")
        logger.info(f"   - High: {review_data['issues_summary']['high_count']} 个")
        logger.info(f"\n 前5个问题:")
        for issue in review_data['top_issues'][:5]:
            logger.info(f"   [{issue['id']}] {issue['description']}")
        
        # 暂停执行，等待用户裁决
        logger.info("\n️ 暂停流程，等待用户裁决...")
        user_decision = interrupt(review_data)
        logger.info(f" 收到用户裁决: {user_decision}")
        
        # 解析用户决策
        if isinstance(user_decision, dict):
            action = user_decision.get("action", "continue")
            selected_issues = user_decision.get("selected_issues", [])
        elif isinstance(user_decision, str):
            action = user_decision
            selected_issues = []
        else:
            logger.warning("️ 无效的用户响应，默认继续流程")
            action = "continue"
            selected_issues = []
        
        # 更新状态
        updated_state = {
            "current_stage": AnalysisStage.ANALYSIS_REVIEW.value,
            "interaction_history": state.get("interaction_history", []) + [{
                "type": InteractionType.MANUAL_REVIEW.value if hasattr(InteractionType, 'MANUAL_REVIEW') else "manual_review",
                "data": review_data,
                "response": user_decision,
                "timestamp": ManualReviewNode._get_timestamp()
            }]
        }
        
        # 根据用户决策路由
        if action == "abort":
            # 终止流程，触发全面整改
            logger.info(" 用户选择全面整改，提取需要重新执行的专家...")
            
            agents_to_rerun = ManualReviewNode._extract_agents_from_issues(
                must_fix_issues,
                review_result
            )
            
            if agents_to_rerun:
                logger.info(f" 需要整改的专家: {agents_to_rerun}")
                updated_state["agents_to_rerun"] = list(agents_to_rerun)
                updated_state["rerun_reason"] = f"人工审核要求整改{issues_count}个must_fix问题"
                updated_state["skip_second_review"] = True  # 整改后跳过审核
                updated_state["analysis_approved"] = False
                
                # 路由到专家重新执行
                return ManualReviewNode._route_to_batch_executor(updated_state)
            else:
                logger.error(" 未能提取专家ID，无法执行整改，继续流程")
                updated_state["manual_review_failed"] = True
                return Command(update=updated_state, goto="detect_challenges")
        
        elif action == "selective_fix":
            # 选择性整改
            logger.info(f" 用户选择整改 {len(selected_issues)} 个关键问题")
            
            if selected_issues:
                # 根据用户选择的问题提取专家
                selected_issue_objs = [
                    issue for issue in must_fix_issues 
                    if issue.get('issue_id') in selected_issues
                ]
                
                agents_to_rerun = ManualReviewNode._extract_agents_from_issues(
                    selected_issue_objs,
                    review_result
                )
                
                if agents_to_rerun:
                    logger.info(f" 需要整改的专家: {agents_to_rerun}")
                    updated_state["agents_to_rerun"] = list(agents_to_rerun)
                    updated_state["rerun_reason"] = f"人工审核要求选择性整改{len(selected_issues)}个关键问题"
                    updated_state["skip_second_review"] = True
                    updated_state["analysis_approved"] = False
                    
                    return ManualReviewNode._route_to_batch_executor(updated_state)
            
            logger.warning("️ 未选择有效问题或无法提取专家，继续流程")
            updated_state["manual_review_failed"] = True
            return Command(update=updated_state, goto="detect_challenges")
        
        else:  # continue
            # 接受风险，继续生成报告
            logger.warning("️ 用户选择接受风险，继续生成报告（报告可能存在严重缺陷）")
            updated_state["analysis_approved"] = False  # 标记为未通过，但继续
            updated_state["risk_accepted"] = True
            updated_state["requires_manual_review"] = False  # 清除标记
            
            return Command(update=updated_state, goto="detect_challenges")
    
    @staticmethod
    def _extract_agents_from_issues(
        issues: list[Dict[str, Any]],
        review_result: Dict[str, Any]
    ) -> set:
        """
        从问题列表中提取需要整改的专家ID
        
        Args:
            issues: must_fix问题列表
            review_result: 完整审核结果
            
        Returns:
            专家ID集合
        """
        agents_to_rerun = set()
        red_issues = review_result.get('red_team_review', {}).get('issues', [])
        
        for issue in issues:
            issue_id = issue.get('issue_id', '')
            # 从红队问题中查找对应的agent_id
            for red_issue in red_issues:
                if red_issue.get('id') == issue_id:
                    agent_id = red_issue.get('agent_id', '')
                    if agent_id:
                        agents_to_rerun.add(agent_id)
                        logger.debug(f"   问题 {issue_id} 关联专家: {agent_id}")
                    break
        
        return agents_to_rerun
    
    @staticmethod
    def _route_to_batch_executor(updated_state: Dict[str, Any]) -> Command[Literal["batch_executor", "project_director"]]:
        """
        路由到批次执行器，重新执行指定专家
        
        Args:
            updated_state: 更新后的状态
            
        Returns:
            Command对象
        """
        # 复用 analysis_review.py 的路由逻辑
        from .analysis_review import AnalysisReviewNode
        
        agents_to_rerun = updated_state.get("agents_to_rerun", [])
        if not agents_to_rerun:
            logger.error(" 没有需要重新执行的专家")
            return Command(update=updated_state, goto="detect_challenges")
        
        # 调用 analysis_review 的路由函数
        return AnalysisReviewNode._route_to_specific_agents(
            agents_to_rerun,
            updated_state
        )
    
    @staticmethod
    def _get_timestamp() -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()
