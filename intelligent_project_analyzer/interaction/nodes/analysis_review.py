"""
分析结果审核节点 - 多视角自动化审核系统

实现红蓝对抗、评委裁决、甲方审核等多视角碰撞机制
系统自动执行，无需用户参与
"""

from typing import Any, Dict, List, Literal

from langgraph.store.base import BaseStore
from langgraph.types import Command
from loguru import logger

from ...core.state import AnalysisStage, ProjectAnalysisState
from ...review import MultiPerspectiveReviewCoordinator


class AnalysisReviewNode:
    """
    分析结果审核节点 - 多视角自动化审核系统

    实现红蓝对抗、评委裁决、甲方审核等多视角碰撞机制
    系统自动执行，无需用户参与
    """

    # 类级别的审核协调器实例（延迟初始化）
    _review_coordinator = None
    _llm_model = None

    @classmethod
    def initialize_coordinator(cls, llm_model, config: Dict[str, Any] | None = None):
        """初始化审核协调器"""
        if cls._review_coordinator is None or cls._llm_model != llm_model:
            cls._llm_model = llm_model
            cls._review_coordinator = MultiPerspectiveReviewCoordinator(llm_model=llm_model, config=config or {})
            logger.info("多视角审核协调器已初始化")

    @staticmethod
    def _get_agent_display_name(agent_type: str) -> str:
        """获取专家的显示名称"""
        agent_names = {
            "v2_design_research": "V2 设计研究分析师",
            "v3_technical_architecture": "V3 技术架构师",
            "v4_ux_design": "V4 用户体验设计师",
            "v5_business_model": "V5 商业分析师",
            "v6_implementation_plan": "V6 实施规划师",
        }
        return agent_names.get(agent_type, agent_type)

    @classmethod
    def execute(
        cls,
        state: ProjectAnalysisState,
        store: BaseStore | None = None,
        llm_model=None,
        config: Dict[str, Any] | None = None,
    ) -> Command[Literal["result_aggregator", "detect_challenges"]]:
        """
        执行递进式单轮审核 (v2.0)

        核心改进:
        1. 移除多轮迭代逻辑（不再rerun_specific/rerun_all）
        2. 递进式三阶段：红→蓝→评委→甲方
        3. 输出改进建议（improvement_suggestions）而非重新执行
        4. 记录final_ruling到state用于报告生成

        Args:
            state: 项目分析状态
            store: 存储接口
            llm_model: LLM模型实例
            config: 配置参数

        Returns:
            Command对象，指向下一个节点（detect_challenges或result_aggregator）
        """
        logger.info("=" * 100)
        logger.info(" 开始递进式单轮审核系统 (v2.0)")
        logger.info("=" * 100)

        # 初始化审核协调器
        if llm_model:
            cls.initialize_coordinator(llm_model, config)

        if cls._review_coordinator is None:
            logger.error("审核协调器未初始化，无法执行审核")
            return cls._simple_review_fallback(state)

        # 获取分析结果和需求
        agent_results = state.get("agent_results", {})
        requirements = state.get("structured_requirements", {})

        # 记录专家分析摘要
        cls._log_agent_summaries(agent_results)

        # 执行单轮审核（不再循环）
        logger.info("\n 启动递进式三阶段审核")
        review_result = cls._review_coordinator.conduct_review(
            agent_results=agent_results, requirements=requirements, current_round=1  # 固定为第1轮
        )

        # 获取审核结果
        final_ruling = review_result.get("final_ruling", "")
        improvement_suggestions = review_result.get("improvement_suggestions", [])
        client_review = review_result.get("client_review", {})
        final_decision = client_review.get("final_decision", "N/A")

        # 记录审核摘要
        cls._log_review_summary_v2(review_result)

        #  P0-2修复：检查是否有must_fix问题需要整改
        must_fix_improvements = [imp for imp in improvement_suggestions if imp.get("priority") == "must_fix"]

        # 检查当前审核轮次（避免无限循环）
        review_iteration_round = state.get("review_iteration_round", 0)

        must_fix_count = len(must_fix_improvements)
        logger.info(f" 审核结果统计：共{len(improvement_suggestions)}项改进建议，其中{must_fix_count}项must_fix")
        logger.info(f" 当前审核轮次：{review_iteration_round}")

        # 获取并更新审核历史
        review_history = state.get("review_history", [])
        # 避免重复添加（如果重试逻辑导致重复执行）
        # 简单策略：直接追加，result_aggregator会处理
        # 但为了更严谨，可以检查round是否已存在
        existing_rounds = {r.get("round") for r in review_history}
        if review_result.get("round") not in existing_rounds:
            review_history = review_history + [review_result]
        else:
            # 如果已存在（可能是重试），替换旧的
            review_history = [r for r in review_history if r.get("round") != review_result.get("round")] + [
                review_result
            ]
            # 重新排序
            review_history.sort(key=lambda x: x.get("round", 0))

        # 更新状态（记录审核结果）
        updated_state = {
            "current_stage": AnalysisStage.ANALYSIS_REVIEW.value,
            "review_result": review_result,
            "review_history": review_history,  #  新增：更新审核历史
            "final_ruling": final_ruling,
            "improvement_suggestions": improvement_suggestions,
            "last_review_decision": final_decision,
        }

        #  P0-2核心逻辑：触发专家重做（最多1次）
        if must_fix_count > 0 and review_iteration_round < 1:
            logger.warning(
                f" 发现{must_fix_count}个must_fix问题，触发专家整改流程（轮次{review_iteration_round} → {review_iteration_round + 1}）"
            )

            # 从审核结果中提取需要整改的专家ID
            agents_to_improve = cls._extract_agents_from_issues(must_fix_improvements, review_result)

            if agents_to_improve:
                logger.info(f" 需要整改的专家: {agents_to_improve}")

                #  P0-2：构建agent_feedback（告诉专家哪里需要修复）
                agent_feedback = {}
                for agent_id in agents_to_improve:
                    # 找到该专家的所有must_fix问题
                    agent_issues = [
                        imp
                        for imp in must_fix_improvements
                        if imp.get("agent_id") == agent_id or agent_id in imp.get("agent_id", "")
                    ]

                    # 获取专家的上一轮输出
                    agent_results = state.get("agent_results", {})
                    previous_output = agent_results.get(agent_id, {})

                    agent_feedback[agent_id] = {
                        "must_fix_issues": agent_issues,
                        "previous_output": previous_output,
                        "iteration_round": review_iteration_round + 1,
                        "feedback_summary": f"审核发现{len(agent_issues)}个must_fix问题，请针对性修复",
                    }

                    logger.info(f"   {agent_id}: {len(agent_issues)}个must_fix问题")

                # 更新状态
                updated_state["specific_agents_to_run"] = list(agents_to_improve)
                updated_state["agent_feedback"] = agent_feedback  #  P0-2关键字段
                updated_state["review_iteration_round"] = review_iteration_round + 1
                updated_state["skip_role_review"] = True  # 跳过角色审查
                updated_state["skip_task_review"] = True  # 跳过任务审查
                updated_state["is_rerun"] = True  # 标记为重做
                updated_state["analysis_approved"] = False

                #  路由决策：返回batch_executor重新执行专家
                logger.info("️ 路由到batch_executor，触发专家重做")
                return Command(update=updated_state, goto="batch_executor")
            else:
                logger.warning("️ 未能提取专家ID，继续正常流程")

        elif must_fix_count > 0 and review_iteration_round >= 1:
            # 已经重做过1次，不再继续（避免无限循环）
            logger.warning(f"️ 仍有{must_fix_count}个must_fix问题，但已达到最大迭代次数(1)，继续流程")
            updated_state["analysis_approved"] = False
            updated_state["max_iteration_reached"] = True

        else:
            # 无must_fix问题，审核通过
            logger.info(" 无must_fix问题，审核通过")
            updated_state["analysis_approved"] = True

        #  继续正常流程：挑战检测 → 报告生成
        logger.info(" [v3.5] 审核完成，启动专家主动性协议检测...")
        return Command(update=updated_state, goto="detect_challenges")

    @classmethod
    def _extract_agents_from_issues(
        cls, must_fix_improvements: List[Dict[str, Any]], review_result: Dict[str, Any]
    ) -> set:
        """
        从must_fix问题中提取需要整改的专家ID

         v7.154: 增强专家ID提取逻辑，支持 source_expert 字段和 recommendations

        Args:
            must_fix_improvements: must_fix改进建议列表
            review_result: 完整审核结果

        Returns:
            需要整改的专家ID集合
        """
        import re

        agents_to_improve = set()
        red_issues = review_result.get("red_team_review", {}).get("issues", [])

        #  v7.154 策略0: 从 recommendations 中提取 source_expert
        # 这是最可靠的来源，因为 recommendations 明确指定了专家
        recommendations = review_result.get("recommendations", {})
        if isinstance(recommendations, dict):
            rec_list = recommendations.get("recommendations", [])
        else:
            rec_list = []

        for rec in rec_list:
            source_expert = rec.get("source_expert", "")
            if source_expert:
                # 格式: "V2_设计总监_2-1" -> 提取 "V2" 或完整ID
                if source_expert.startswith("V") and "_" in source_expert:
                    # 提取层级前缀
                    layer_match = re.match(r"(V\d+)", source_expert)
                    if layer_match:
                        agents_to_improve.add(layer_match.group(1))
                        logger.debug(f"    [v7.154] 从 source_expert 提取专家: {layer_match.group(1)}")

        #  v7.154 策略0.5: 从 client_decisions 中提取
        client_decisions = review_result.get("client_review", {}).get("accepted_improvements", [])
        for decision in client_decisions:
            # 尝试从 description 中提取专家关键词
            description = decision.get("description", "")
            if description:
                # 匹配专家类型关键词
                expert_keywords = {
                    "设计": "V2",
                    "空间": "V2",
                    "布局": "V2",
                    "规划": "V2",
                    "叙事": "V3",
                    "故事": "V3",
                    "体验": "V3",
                    "文化": "V3",
                    "研究": "V4",
                    "案例": "V4",
                    "调研": "V4",
                    "对标": "V4",
                    "场景": "V5",
                    "商业": "V5",
                    "用户": "V5",
                    "行为": "V5",
                    "工程": "V6",
                    "技术": "V6",
                    "实施": "V6",
                    "材料": "V6",
                    "结构": "V6",
                }
                for keyword, layer in expert_keywords.items():
                    if keyword in description:
                        agents_to_improve.add(layer)
                        logger.debug(f"    [v7.154] 从 client_decision 描述中提取专家: {layer} (关键词: {keyword})")
                        break

        #  v7.11: 构建 issue_id -> agent_id 映射
        issue_agent_map = {}
        for red_issue in red_issues:
            issue_id = red_issue.get("id", "")
            agent_id = red_issue.get("agent_id", "") or red_issue.get("responsible_agent", "")
            if issue_id and agent_id:
                issue_agent_map[issue_id] = agent_id

        logger.debug(f" 红队问题映射: {issue_agent_map}")

        for improvement in must_fix_improvements:
            issue_id = improvement.get("issue_id", "")

            # 策略1: 直接从映射获取
            if issue_id and issue_id in issue_agent_map:
                agents_to_improve.add(issue_agent_map[issue_id])
                logger.debug(f"    问题 {issue_id} -> 专家: {issue_agent_map[issue_id]}")
                continue

            # 策略2: 从改进建议中直接获取agent_id（支持多种字段名）
            agent_id = (
                improvement.get("agent_id", "")
                or improvement.get("responsible_agent", "")
                or improvement.get("affected_expert", "")
                or improvement.get("source_agent", "")  #  v7.23
                or improvement.get("expert_id", "")  #  v7.23  #  v7.23
            )
            if agent_id:
                agents_to_improve.add(agent_id)
                logger.debug(f"    改进建议直接指定专家: {agent_id}")
                continue

            #  v7.23 策略2.5: 从 source 字段提取专家标识
            source = improvement.get("source", "")
            if source:
                # 匹配 "X-Y 专家名称" 格式，如 "4-1 设计研究员"
                source_match = re.search(r"(\d+-\d+)\s*(.+)", source)
                if source_match:
                    suffix = source_match.group(1)  # "4-1"
                    layer = suffix.split("-")[0]  # "4"
                    agents_to_improve.add(f"V{layer}")
                    logger.debug(f"    从source提取专家: V{layer} (来自 {source})")
                    continue

            # 策略3: 从description中提取专家标识（如"V4专家"、"V3_人物"等）
            description = improvement.get("description", "") or improvement.get("suggestion", "")
            if description:
                # 匹配 V2-V6 格式的专家标识
                pattern = r"(V[2-6](?:_[^\s,，]+)?)"
                matches = re.findall(pattern, description, re.IGNORECASE)
                for match in matches:
                    agents_to_improve.add(match.upper())
                    logger.debug(f"    从描述中提取专家: {match}")
                if matches:
                    continue

            #  v7.23 策略4: 从 category 或 type 推断专家层级
            category = improvement.get("category", "") or improvement.get("type", "")
            category_to_layer = {
                "design": "V2",
                "narrative": "V3",
                "research": "V4",
                "scenario": "V5",
                "engineering": "V6",
                "technical": "V6",
                "business": "V5",
                "user_experience": "V4",
                "ux": "V4",
                #  v7.24: 扩展类别映射
                "architecture": "V6",
                "visual": "V2",
                "space": "V2",
                "user": "V4",
                "customer": "V4",
                "story": "V3",
                "character": "V3",
                "persona": "V4",
                "flow": "V5",
                "experience": "V5",
                "material": "V6",
                "cost": "V6",
                "budget": "V6",
            }
            if category:
                category_lower = category.lower().replace("_", "")
                for key, layer in category_to_layer.items():
                    if key in category_lower:
                        agents_to_improve.add(layer)
                        logger.debug(f"    从类别'{category}'推断专家: {layer}")
                        break

            #  v7.24 策略5: 从 affected_sections 提取专家
            affected_sections = improvement.get("affected_sections", [])
            if isinstance(affected_sections, str):
                affected_sections = [affected_sections]
            for section in affected_sections:
                section.lower() if isinstance(section, str) else ""
                # 匹配 V2-V6 格式
                pattern = r"(V[2-6])"
                matches = re.findall(pattern, section, re.IGNORECASE)
                for match in matches:
                    agents_to_improve.add(match.upper())
                    logger.debug(f"    从affected_sections提取专家: {match}")

            #  v7.24 策略6: 从 suggestion 中提取专家关键词
            suggestion = improvement.get("suggestion", "")
            if suggestion:
                # 通用关键词到专家层级映射
                keyword_to_layer = {
                    "设计总监": "V2",
                    "空间": "V2",
                    "布局": "V2",
                    "规划": "V2",
                    "叙事": "V3",
                    "故事": "V3",
                    "人物": "V3",
                    "角色": "V3",
                    "研究": "V4",
                    "用户": "V4",
                    "体验": "V4",
                    "调研": "V4",
                    "场景": "V5",
                    "商业": "V5",
                    "运营": "V5",
                    "流程": "V5",
                    "工程": "V6",
                    "技术": "V6",
                    "实施": "V6",
                    "成本": "V6",
                    "材料": "V6",
                }
                for keyword, layer in keyword_to_layer.items():
                    if keyword in suggestion:
                        agents_to_improve.add(layer)
                        logger.debug(f"    从suggestion关键词'{keyword}'推断专家: {layer}")
                        break  # 只取第一个匹配

        if not agents_to_improve:
            logger.warning("️ 未能从must_fix问题中提取任何专家ID")
            logger.debug(f"   改进建议: {must_fix_improvements}")
            logger.debug(f"   红队问题: {red_issues}")
        else:
            logger.info(f" 提取到需要整改的专家: {agents_to_improve}")

        return agents_to_improve

    @classmethod
    def _log_agent_summaries(cls, agent_results: Dict[str, Any]):
        """记录专家分析摘要"""
        logger.info("\n 专家分析摘要:")
        for agent_type, result in agent_results.items():
            if agent_type in ["requirements_analyst", "project_director"]:
                continue
            if result and isinstance(result, dict):
                agent_name = cls._get_agent_display_name(agent_type)
                confidence = result.get("confidence", 0)
                logger.info(f"  - {agent_name}: 置信度 {confidence:.0%}")

    @classmethod
    def _route_to_specific_agents(
        cls, agents_to_rerun: List[str], updated_state: Dict[str, Any]
    ) -> Command[Literal["batch_executor", "project_director"]]:
        """
        路由到特定需要重新执行的专家

        支持两种ID格式：
        1. 固定ID: v3_technical_architecture, v4_ux_design, etc.
        2. 动态ID: V3_人物及叙事专家_3-1, V4_设计研究员_4-1, etc.

         修复：确保review_feedback被传递到state中
        """
        # 第一批专家: V3, V4, V5
        first_batch_fixed = {"v3_technical_architecture", "v4_ux_design", "v5_business_model"}
        first_batch_prefixes = {"V3", "V4", "V5"}

        # 第二批专家: V2, V6
        second_batch_fixed = {"v2_design_research", "v6_implementation_plan"}
        second_batch_prefixes = {"V2", "V6"}

        agents_set = set(agents_to_rerun)

        # 提取动态ID的前缀
        def extract_prefix(agent_id: str) -> str:
            if agent_id.startswith("V") and "_" in agent_id:
                return agent_id.split("_")[0]
            elif agent_id.startswith("v") and "_" in agent_id:
                return agent_id.split("_")[0].upper()
            return ""

        # 提取所有专家的前缀
        agent_prefixes = {extract_prefix(agent_id) for agent_id in agents_set}
        agent_prefixes.discard("")

        # 检查是否需要重新执行第一批
        needs_first_batch = bool((agents_set & first_batch_fixed) or (agent_prefixes & first_batch_prefixes))

        # 检查是否需要重新执行第二批
        needs_second_batch = bool((agents_set & second_batch_fixed) or (agent_prefixes & second_batch_prefixes))

        # 获取匹配的专家列表
        first_batch_agents = [
            agent_id
            for agent_id in agents_set
            if agent_id in first_batch_fixed or extract_prefix(agent_id) in first_batch_prefixes
        ]
        second_batch_agents = [
            agent_id
            for agent_id in agents_set
            if agent_id in second_batch_fixed or extract_prefix(agent_id) in second_batch_prefixes
        ]

        #  关键修复：记录审核反馈传递状态
        review_feedback = updated_state.get("review_feedback")
        if review_feedback:
            feedback_agents = list(review_feedback.get("feedback_by_agent", {}).keys())
            logger.info(f" 审核反馈已准备，包含{len(feedback_agents)}个专家的改进任务")
            logger.debug(f"   反馈专家列表: {feedback_agents}")
        else:
            logger.warning("️ 未找到review_feedback，专家将在无反馈的情况下重新执行")

        if needs_first_batch and needs_second_batch:
            # 两批都需要，先执行第一批
            logger.info(" 需要重新执行两批专家")
            logger.info(f"   第一批: {first_batch_agents}")
            logger.info(f"   第二批: {second_batch_agents}")

            updated_state["skip_role_review"] = True
            updated_state["skip_task_review"] = True
            updated_state["specific_agents_to_run"] = first_batch_agents
            updated_state["pending_second_batch"] = second_batch_agents
            updated_state["is_rerun"] = True  #  标记为整改重新执行
            #  review_feedback 已在 updated_state 中，会被自动传递

            return Command(update=updated_state, goto="batch_executor")
        elif needs_first_batch:
            logger.info(f" 重新执行第一批专家: {first_batch_agents}")
            updated_state["skip_role_review"] = True
            updated_state["skip_task_review"] = True
            updated_state["specific_agents_to_run"] = first_batch_agents
            updated_state["is_rerun"] = True  #  标记为整改重新执行
            #  review_feedback 已在 updated_state 中，会被自动传递

            return Command(update=updated_state, goto="batch_executor")
        elif needs_second_batch:
            logger.info(f" 重新执行第二批专家: {second_batch_agents}")
            updated_state["skip_role_review"] = True
            updated_state["skip_task_review"] = True
            updated_state["specific_agents_to_run"] = second_batch_agents
            updated_state["is_rerun"] = True  #  标记为整改重新执行
            #  review_feedback 已在 updated_state 中，会被自动传递

            return Command(update=updated_state, goto="batch_executor")
        else:
            logger.warning("️ 未找到匹配的专家批次，返回项目总监")
            return Command(update=updated_state, goto="project_director")

    @classmethod
    def _find_best_round(cls, review_history: List[Dict[str, Any]], best_score: float) -> int:
        """找到最佳评分对应的轮次"""
        for i, review in enumerate(review_history):
            if abs(review["final_decision"]["overall_score"] - best_score) < 0.01:
                return i + 1
        return len(review_history)

    @classmethod
    def _simple_review_fallback(cls, state: ProjectAnalysisState) -> Command[Literal["result_aggregator"]]:
        """简单审核降级方案（当审核协调器不可用时）"""
        logger.warning("使用简单审核降级方案")

        agent_results = state.get("agent_results", {})

        # 计算平均置信度
        confidences = []
        for agent_type, result in agent_results.items():
            if agent_type not in ["requirements_analyst", "project_director"]:
                if result and isinstance(result, dict):
                    confidences.append(result.get("confidence", 0))

        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        logger.info(f"平均置信度: {avg_confidence:.2%}")

        updated_state = {
            #  移除 current_stage 更新，避免与主流程冲突
            # "current_stage": AnalysisStage.ANALYSIS_REVIEW.value,
            "analysis_approved": avg_confidence >= 0.6,
            "last_review_score": avg_confidence * 100,
        }

        return Command(update=updated_state, goto="result_aggregator")

    @classmethod
    def _log_review_summary(cls, review_result: Dict[str, Any], current_round: int):
        """
        记录审核摘要到日志（自动化，无需用户确认）

        专注于记录具体问题和改进建议，而非评分
        """
        red_review = review_result.get("red_team_review", {})
        blue_review = review_result.get("blue_team_review", {})
        review_result.get("judge_review", {})
        client_review = review_result.get("client_review", {})
        final_decision = review_result.get("final_decision", {})

        logger.info(f"\n{'='*80}")
        logger.info(f" 第 {current_round} 轮审核摘要")
        logger.info(f"{'='*80}")

        # 红队发现的问题
        issues = red_review.get("issues_found", [])
        if issues:
            logger.info(f"\n 红队发现 {len(issues)} 个问题:")
            for i, issue in enumerate(issues[:5], 1):  # 只显示前5个
                issue_desc = issue if isinstance(issue, str) else issue.get("description", str(issue))
                logger.info(f"   {i}. {issue_desc[:100]}")

        # 蓝队亮点
        strengths = blue_review.get("strengths", [])
        if strengths:
            logger.info(f"\n 蓝队发现 {len(strengths)} 个亮点:")
            for i, strength in enumerate(strengths[:3], 1):  # 只显示前3个
                logger.info(f"   {i}. {strength[:100]}")

        # 甲方关注点
        concerns = client_review.get("concerns", [])
        if concerns:
            logger.info(f"\n 甲方 {len(concerns)} 个关注点:")
            for i, concern in enumerate(concerns[:3], 1):  # 只显示前3个
                logger.info(f"   {i}. {concern[:100]}")

        # 决策
        logger.info(f"\n 决策: {final_decision.get('decision', 'unknown')}")
        if final_decision.get("agents_to_rerun"):
            logger.info(f" 需要重新执行: {', '.join(final_decision['agents_to_rerun'])}")

        logger.info(f"{'='*80}\n")

    @classmethod
    def _log_review_summary_v2(cls, review_result: Dict[str, Any]):
        """
        记录递进式审核摘要（v2.0单轮版本）

        聚焦于最终裁定和改进建议，不再关注评分
        """
        red_review = review_result.get("red_team_review", {})
        blue_review = review_result.get("blue_team_review", {})
        judge_review = review_result.get("judge_review", {})
        client_review = review_result.get("client_review", {})
        review_result.get("final_ruling", "")

        logger.info(f"\n{'='*80}")
        logger.info(" 递进式审核摘要")
        logger.info(f"{'='*80}")

        # 红队发现的问题
        issues = red_review.get("issues", [])
        if issues:
            critical = sum(1 for i in issues if i.get("severity") == "critical")
            high = sum(1 for i in issues if i.get("severity") == "high")
            logger.info(f"\n 红队: 发现 {len(issues)} 个问题 ({critical} critical, {high} high)")
            for i, issue in enumerate(issues[:3], 1):
                logger.info(f"   {issue.get('id', 'N/A')}: {issue.get('description', '')[:80]}")

        # 蓝队验证结果
        validations = blue_review.get("validations", [])
        if validations:
            agree = sum(1 for v in validations if v.get("stance") == "agree")
            logger.info(f"\n 蓝队: 验证 {len(validations)} 个问题 (同意 {agree} 个)")

        strengths = blue_review.get("strengths", [])
        if strengths:
            logger.info(f"   发现 {len(strengths)} 个优势")

        # 评委裁决
        rulings = judge_review.get("rulings", [])
        if rulings:
            accepted = sum(1 for r in rulings if r.get("ruling") == "accept")
            logger.info(f"\n️ 评委: 裁决 {len(rulings)} 个问题 (确认 {accepted} 个)")

        # 甲方决策
        accepted_improvements = client_review.get("accepted_improvements", [])
        final_decision = client_review.get("final_decision", "N/A")
        logger.info(f"\n 甲方: {final_decision}")
        logger.info(f"   接受 {len(accepted_improvements)} 项改进建议")

        must_fix = sum(1 for a in accepted_improvements if a.get("business_priority") == "must_fix")
        if must_fix > 0:
            logger.info(f"   其中 {must_fix} 项标记为 must_fix")

        logger.info(f"{'='*80}\n")
