"""
领域验证节点 - 深度领域一致性检查
"""

from typing import Dict, Any, Optional, Union
from loguru import logger
from langgraph.types import interrupt, Command
from langgraph.store.base import BaseStore

from intelligent_project_analyzer.core.state import ProjectAnalysisState
from intelligent_project_analyzer.security.domain_classifier import DomainClassifier
from intelligent_project_analyzer.security.violation_logger import ViolationLogger


class DomainValidatorNode:
    """领域验证节点 - 在需求分析后验证领域一致性"""
    
    @staticmethod
    def execute(
        state: ProjectAnalysisState,
        store: Optional[BaseStore] = None,
        llm_model = None
    ) -> Union[Dict[str, Any], Command]:
        """
        执行深度领域验证（返回状态更新字典或 Command）
        
        检查逻辑:
        1. 检查需求分析结果是否偏离设计领域
        2. 验证项目类型与目标匹配度
        3. 如发现偏离，interrupt让用户确认
        4. 路由决策: 继续 / 调整 / 拒绝
        
        Args:
            state: 项目分析状态
            store: 存储接口
            llm_model: LLM模型实例
            
        Returns:
            Dict: 状态更新字典（由静态 edge 路由到 calibration_questionnaire）
            Command: 仅在拒绝时返回 Command(goto="input_rejected")
        """
        logger.info("=" * 100)
        logger.info("🔍 领域验证:深度一致性检查")
        logger.info("=" * 100)
        
        # 从 agent_results 中提取 requirements_analyst 的结果
        agent_results = state.get("agent_results", {})
        requirements_analyst_result = agent_results.get("requirements_analyst", {})
        
        # 获取 structured_data 字段
        requirements_result = requirements_analyst_result.get("structured_data", {})
        
        # 兼容旧版本: 如果 agent_results 中没有,尝试直接从 structured_requirements 获取
        if not requirements_result:
            requirements_result = state.get("structured_requirements", {})
        
        user_input = state.get("user_input", "")
        session_id = state.get("session_id", "")
        
        logger.info(f"🔍 [DEBUG] requirements_result keys: {list(requirements_result.keys()) if requirements_result else 'None'}")
        
        # 初始化检测器
        domain_classifier = DomainClassifier(llm_model=llm_model)
        violation_logger = ViolationLogger()
        
        # === 检查需求分析结果 ===
        # 提取项目描述、目标、关键需求
        project_summary = DomainValidatorNode._extract_project_summary(requirements_result)
        
        if not project_summary:
            logger.error("❌ 需求分析结果为空，无法继续")
            return {
                "error": "Requirements analysis result is empty",
                "calibration_skipped": True
            }
        
        logger.info(f"📄 项目摘要: {project_summary[:200]}...")
        
        # 重新分类项目内容
        domain_result = domain_classifier.classify(project_summary)
        
        # === 情况1：明确非设计类（漂移检测） ===
        if domain_result["is_design_related"] == False:
            logger.error("🚨 领域漂移检测：需求分析结果偏离设计领域")
            
            # 记录漂移尝试
            violation_logger.log({
                "session_id": session_id,
                "violation_type": "domain_drift",
                "details": domain_result,
                "user_input": user_input[:200],
                "analysis_summary": project_summary[:200]
            })
            
            # Interrupt：让用户确认是否调整
            drift_data = {
                "interaction_type": "domain_drift_alert",
                "message": "⚠️ 检测到需求可能偏离空间设计领域",
                "drift_details": {
                    "original_input": user_input[:300],
                    "analysis_summary": project_summary[:300],
                    "detected_domain": domain_result.get("detected_domain", "未知领域"),
                    "non_design_categories": domain_result.get("matched_non_design_categories", [])
                },
                "options": {
                    "adjust": "我想调整需求，回到设计领域",
                    "continue": "我确认这是设计类需求，请继续",
                    "reject": "确实不是设计类，终止分析"
                }
            }
            
            user_response = interrupt(drift_data)
            
            # 处理用户选择
            if isinstance(user_response, dict):
                action = user_response.get("action", "reject")
                adjustment = user_response.get("adjustment", "")
            elif isinstance(user_response, str):
                action = user_response if user_response in ["adjust", "continue", "reject"] else "reject"
                adjustment = user_response
            else:
                action = "reject"
                adjustment = ""
            
            if action == "reject":
                logger.info("❌ 用户确认终止分析")
                return Command(
                    update={
                        "rejection_reason": "domain_drift_confirmed",
                        "rejection_message": "分析过程中发现需求偏离空间设计领域，已终止分析。"
                    },
                    goto="input_rejected"
                )
            
            elif action == "adjust" and adjustment:
                logger.info("🔄 用户提供调整意见，重新分析需求")
                return Command(
                    update={
                        "user_input": adjustment,
                        "original_input": user_input,
                        "drift_adjustment": True
                    },
                    goto="requirements_analyst"  # 返回需求分析
                )
            
            # action == "continue"：用户坚持继续，标记为风险项
            logger.warning("⚠️ 用户坚持继续，标记为领域风险项")
            return Command(
                update={
                    "domain_risk_flag": True,
                    "domain_risk_details": domain_result
                },
                goto="END"  # 继续后续流程
            )
        
        # === 情况2：领域不明确 ===
        if domain_result["is_design_related"] == "unclear":
            logger.info("⚠️ 领域一致性不明确，置信度不足")
            
            # 如果输入预检时置信度已经很高，这里不再打断
            input_confidence = state.get("domain_confidence", 0)
            if input_confidence >= 0.7:
                logger.info("✅ 输入预检置信度高，信任初始判断")
                logger.info("🔄 [DEBUG] High input confidence, continuing to calibration_questionnaire")
                return {}
            
            # 否则，让用户确认
            unclear_data = {
                "interaction_type": "domain_unclear",
                "message": "需求的领域归属不太明确，需要您确认一下：",
                "analysis_summary": project_summary[:300],
                "questions": [
                    "这个项目是否涉及空间设计（建筑/室内/景观）？",
                    "您希望我从设计角度还是其他角度分析？"
                ],
                "options": {
                    "design": "是的，这是空间设计项目",
                    "other": "不是，请终止分析"
                }
            }
            
            user_response = interrupt(unclear_data)
            
            if isinstance(user_response, dict):
                action = user_response.get("action", "other")
            elif isinstance(user_response, str):
                action = user_response if user_response in ["design", "other"] else "other"
            else:
                action = "other"
            
            if action == "other":
                return Command(
                    update={
                        "rejection_reason": "domain_unclear_rejected",
                        "rejection_message": "无法确认需求属于空间设计领域，已终止分析。"
                    },
                    goto="input_rejected"
                )
            
            # 用户确认为设计类
            logger.info("✅ 用户确认为设计类，继续流程")
            logger.info("🔄 [DEBUG] User confirmed design domain, continuing to calibration_questionnaire")
            return {"domain_user_confirmed": True}
        
        # === 情况3：确认为设计类 ===
        logger.info(f"✅ 领域验证通过 (置信度: {domain_result.get('confidence', 0):.2f})")
        if domain_result.get('matched_categories'):
            logger.info(f"   匹配类别: {domain_result['matched_categories']}")
        
        logger.info("🔄 [DEBUG] Domain validation passed, continuing to calibration_questionnaire")
        return {
            "domain_validation_passed": True,
            "validated_confidence": domain_result.get("confidence", 0)
        }
    
    @staticmethod
    def _extract_project_summary(requirements_result: Dict) -> str:
        """从需求分析结果中提取项目摘要"""
        if not requirements_result:
            return ""
        
        # 尝试提取关键字段
        summary_parts = []
        
        # V3.5 新格式字段
        # 项目任务 (JTBD)
        if "project_task" in requirements_result:
            task = requirements_result["project_task"]
            if task:
                summary_parts.append(f"项目任务: {task}")
        
        # 项目概述
        if "project_overview" in requirements_result:
            overview = requirements_result["project_overview"]
            if overview:
                summary_parts.append(f"项目概述: {overview}")
        
        # 核心目标
        if "core_objectives" in requirements_result:
            objs = requirements_result["core_objectives"]
            if isinstance(objs, list):
                summary_parts.append(f"核心目标: {', '.join(objs[:3])}")
            elif isinstance(objs, str):
                summary_parts.append(f"核心目标: {objs}")
        
        # 设计挑战
        if "design_challenge" in requirements_result:
            challenge = requirements_result["design_challenge"]
            if challenge:
                summary_parts.append(f"设计挑战: {challenge}")
        
        # 物理环境
        if "physical_context" in requirements_result:
            context = requirements_result["physical_context"]
            if context:
                summary_parts.append(f"物理环境: {context}")
        
        # 兼容旧格式 (v3.4及之前)
        if not summary_parts:
            # 旧项目基本信息
            if "project_info" in requirements_result:
                info = requirements_result["project_info"]
                if isinstance(info, dict):
                    summary_parts.append(f"项目名称: {info.get('name', '')}")
                    summary_parts.append(f"项目类型: {info.get('type', '')}")
                    summary_parts.append(f"项目描述: {info.get('description', '')}")
            
            # 旧核心需求
            if "core_requirements" in requirements_result:
                reqs = requirements_result["core_requirements"]
                if isinstance(reqs, list):
                    summary_parts.append(f"核心需求: {', '.join(reqs[:5])}")
                elif isinstance(reqs, str):
                    summary_parts.append(f"核心需求: {reqs}")
            
            # 旧目标
            if "objectives" in requirements_result:
                objs = requirements_result["objectives"]
                if isinstance(objs, list):
                    summary_parts.append(f"目标: {', '.join(objs[:3])}")
                elif isinstance(objs, str):
                    summary_parts.append(f"目标: {objs}")
        
        # 如果所有字段都提取失败，直接转字符串
        if not summary_parts:
            summary_parts.append(str(requirements_result)[:500])
        
        return " | ".join(summary_parts)
