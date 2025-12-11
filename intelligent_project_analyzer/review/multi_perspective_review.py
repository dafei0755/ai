"""
多视角审核协调器

协调红蓝对抗、评委、甲方等多个审核专家进行碰撞和决策
"""

from typing import Dict, Any, List, Optional, Tuple
from loguru import logger
from .review_agents import (
    RedTeamReviewer,
    BlueTeamReviewer,
    JudgeReviewer,
    ClientReviewer
)


class MultiPerspectiveReviewCoordinator:
    """多视角审核协调器"""
    
    def __init__(self, llm_model, config: Optional[Dict[str, Any]] = None):
        """
        初始化多视角审核协调器
        
        Args:
            llm_model: LLM模型实例
            config: 配置参数
        """
        self.llm_model = llm_model
        self.config = config or {}
        
        # 初始化审核专家
        self.red_team = RedTeamReviewer(llm_model)
        self.blue_team = BlueTeamReviewer(llm_model)
        self.judge = JudgeReviewer(llm_model)
        self.client = ClientReviewer(llm_model)
        
        # 审核配置
        self.min_pass_score = self.config.get("min_pass_score", 70)
        self.max_review_rounds = self.config.get("max_review_rounds", 3)
        
        logger.info("多视角审核协调器初始化完成")
    
    def conduct_review(
        self,
        agent_results: Dict[str, Any],
        requirements: Dict[str, Any],
        current_round: int = 1,
        previous_score: Optional[float] = None,
        review_history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        执行两阶段审核（P1-3简化版）

        核心改进：
        1. 简化为两阶段：红蓝对抗 → 甲方决策
        2. 去掉评委的形式主义层级
        3. 蓝队发挥实质作用（过滤误判）
        4. 最终输出可执行改进路线图（final_ruling）

        Args:
            agent_results: 所有专家的分析结果
            requirements: 项目需求
            current_round: 当前审核轮次（保留参数兼容性）

        Returns:
            审核结果，包含最终裁定和改进建议
        """
        logger.info(f"=" * 80)
        logger.info(f"开始两阶段审核（红蓝对抗 → 甲方决策）")
        logger.info(f"=" * 80)

        # 阶段1: 红蓝对抗（合并为一个环节）
        logger.info("\n⚔️ 阶段1: 红蓝对抗 - 发现问题并辩护")
        red_blue_debate = self._conduct_red_blue_debate(
            agent_results,
            requirements
        )

        # 阶段2: 甲方决策（基于红蓝对抗结果）
        logger.info("\n👔 阶段2: 甲方决策 - 最终拍板")
        client_review = self._conduct_client_review_v2(
            agent_results,
            requirements,
            red_blue_debate  # 传递红蓝对抗结果
        )

        # 生成最终裁定文档
        final_ruling = self._generate_final_ruling_v2(
            red_blue_debate,
            client_review
        )

        # 记录审核结果（保持向后兼容）
        review_result = {
            "round": current_round,
            "red_team_review": red_blue_debate.get("red_review", {}),  # 兼容旧字段
            "blue_team_review": red_blue_debate.get("blue_review", {}),  # 兼容旧字段
            "judge_review": {},  # 🗑️ 已废弃，保留空字典兼容
            "red_blue_debate": red_blue_debate,  # 🆕 新字段
            "client_review": client_review,
            "final_ruling": final_ruling,
            "improvement_suggestions": self._extract_improvement_suggestions(client_review),
            "timestamp": self._get_timestamp()
        }

        logger.info(f"\n" + "=" * 80)
        logger.info(f"两阶段审核完成")
        logger.info(f"最终决策: {client_review.get('final_decision', 'N/A')}")
        logger.info(f"改进项: {len(client_review.get('accepted_improvements', []))} 项")
        logger.info(f"=" * 80 + "\n")

        return review_result
    
    def _conduct_red_team_review(
        self,
        agent_results: Dict[str, Any],
        requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行红队审核 - 发现问题并编号
        
        Returns:
            红队审核结果（包含带ID的问题清单）
        """
        logger.info("红队开始批判性审核...")
        
        red_review = self.red_team.review(agent_results, requirements)
        
        # 🔧 P2修复: 统一使用improvements字段进行统计
        improvements = red_review.get('improvements', [])
        issues = red_review.get('issues', [])  # 保留旧字段兼容
        
        # 优先使用improvements统计，回退到issues
        issue_count = len(improvements) if improvements else len(issues)
        critical_count = len([i for i in improvements if i.get('priority') == 'high']) if improvements else sum(1 for issue in issues if issue.get('severity') == 'critical')
        high_count = red_review.get('critical_issues_count', critical_count)
        
        logger.info(f"红队发现 {issue_count} 个问题（{critical_count} critical, {high_count} high）")
        
        return red_review
    
    def _conduct_blue_team_review(
        self,
        agent_results: Dict[str, Any],
        requirements: Dict[str, Any],
        red_review: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行蓝队审核 - 逐一验证红队问题 + 发现优势
        
        Args:
            red_review: 红队审核结果（包含issues数组）
        
        Returns:
            蓝队审核结果（包含validations和strengths数组）
        """
        logger.info("蓝队开始验证红队问题...")
        
        # 传递红队问题清单给蓝队
        blue_review = self.blue_team.review(
            agent_results, 
            requirements,
            red_review=red_review  # 🆕 传递红队结果
        )
        
        validations = blue_review.get('validations', [])
        strengths = blue_review.get('strengths', [])
        agree_count = sum(1 for v in validations if v.get('stance') == 'agree')
        
        logger.info(f"蓝队回应 {len(validations)} 个问题（同意 {agree_count} 个），发现 {len(strengths)} 个优势")
        
        return blue_review
    
    def _conduct_judge_review(
        self,
        agent_results: Dict[str, Any],
        requirements: Dict[str, Any],
        red_review: Dict[str, Any],
        blue_review: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行评委裁决 - 对每个问题做出裁决并排序
        
        Args:
            agent_results: 专家分析结果
            requirements: 项目需求
            red_review: 红队审核结果
            blue_review: 蓝队审核结果
            
        Returns:
            评委审核结果（包含rulings和priority_ranking）
        """
        logger.info("评委开始专业裁决...")
        
        judge_review = self.judge.review(
            agent_results,
            requirements,
            red_review,
            blue_review
        )
        
        rulings = judge_review.get('rulings', [])
        accepted = sum(1 for r in rulings if r.get('ruling') == 'accept')
        rejected = sum(1 for r in rulings if r.get('ruling') == 'reject')
        
        logger.info(f"评委裁决完成: 确认 {accepted} 个问题, 拒绝 {rejected} 个问题")
        
        return judge_review
    
    def _conduct_client_review(
        self,
        agent_results: Dict[str, Any],
        requirements: Dict[str, Any],
        judge_review: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行甲方审核 - 基于评委裁决做最终业务决策
        
        Args:
            agent_results: 专家分析结果
            requirements: 项目需求
            judge_review: 评委裁决结果
            
        Returns:
            甲方审核结果（包含accepted_improvements和final_ruling）
        """
        logger.info("甲方开始最终决策...")
        
        # 传递评委裁决给甲方
        client_review = self.client.review(
            agent_results, 
            requirements,
            judge_review=judge_review  # 🆕 传递评委裁决
        )
        
        accepted = client_review.get('accepted_improvements', [])
        rejected = client_review.get('rejected_improvements', [])
        must_fix = sum(1 for a in accepted if a.get('business_priority') == 'must_fix')
        
        logger.info(f"甲方决策: 接受 {len(accepted)} 项改进（{must_fix} must_fix），拒绝 {len(rejected)} 项")
        
        return client_review
    
    def _generate_final_ruling(
        self,
        red_review: Dict[str, Any],
        blue_review: Dict[str, Any],
        judge_review: Dict[str, Any],
        client_review: Dict[str, Any]
    ) -> str:
        """
        生成最终裁定文档（汇总四阶段结果）
        
        Returns:
            最终裁定文本（可直接用于报告）
        """
        logger.info("生成最终裁定文档...")
        
        # 从甲方审核结果中获取final_ruling字段
        final_ruling = client_review.get('final_ruling', '')
        
        if not final_ruling:
            # 如果没有，手动生成简版
            accepted = client_review.get('accepted_improvements', [])
            final_ruling = f"""
## 📋 最终裁定

### 审核结论
{client_review.get('final_decision', 'N/A')}

### 改进要求
- 必须修复项: {sum(1 for a in accepted if a.get('business_priority') == 'must_fix')} 项
- 建议修复项: {sum(1 for a in accepted if a.get('business_priority') == 'should_fix')} 项
- 可选优化项: {sum(1 for a in accepted if a.get('business_priority') == 'nice_to_have')} 项

### 执行路线图
"""
            for idx, improvement in enumerate(accepted[:5], 1):  # 只取前5项
                final_ruling += f"{idx}. {improvement.get('issue_id', 'N/A')} - {improvement.get('deadline', 'N/A')}\n"
        
        return final_ruling.strip()
    
    def _extract_improvement_suggestions(
        self,
        client_review: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        从甲方审核结果中提取改进建议（用于state记录）
        
        Returns:
            改进建议列表
        """
        accepted = client_review.get('accepted_improvements', [])
        
        suggestions = []
        for improvement in accepted:
            suggestions.append({
                "issue_id": improvement.get('issue_id', ''),
                "priority": improvement.get('business_priority', 'should_fix'),
                "deadline": improvement.get('deadline', 'before_launch'),
                "description": improvement.get('reasoning', '')
            })
        
        return suggestions
    
    # ============================================
    # 以下方法已废弃 (v2.0 单轮审核不再使用)
    # ============================================
    
    def _make_final_decision(
        self,
        red_review: Dict[str, Any],
        blue_review: Dict[str, Any],
        judge_review: Dict[str, Any],
        client_review: Dict[str, Any],
        current_round: int,
        previous_score: Optional[float] = None,
        agent_results: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        综合所有审核意见，做出最终决策

        Args:
            red_review: 红队审核结果
            blue_review: 蓝队审核结果
            judge_review: 评委审核结果
            client_review: 甲方审核结果
            current_round: 当前轮次
            previous_score: 上一轮评分
            agent_results: 专家结果（用于转换 Fixed Mode 键名到动态角色 ID）

        Returns:
            最终决策
        """
        logger.info("综合所有审核意见，做出最终决策...")

        # 计算综合评分（加权平均）
        weights = {
            "red_team": 0.25,
            "blue_team": 0.25,
            "judge": 0.30,
            "client": 0.20
        }

        overall_score = (
            red_review['score'] * weights['red_team'] +
            blue_review['score'] * weights['blue_team'] +
            judge_review['score'] * weights['judge'] +
            client_review['score'] * weights['client']
        )

        # 收集所有需要重新执行的专家（Fixed Mode 键名）
        agents_to_rerun_fixed = set()

        # 红队建议
        if red_review.get('agents_to_rerun'):
            agents_to_rerun_fixed.update(red_review['agents_to_rerun'])

        # 评委裁决
        if judge_review.get('agents_to_rerun'):
            agents_to_rerun_fixed.update(judge_review['agents_to_rerun'])

        # 🔧 转换 Fixed Mode 键名到动态角色 ID
        agents_to_rerun = self._convert_fixed_to_dynamic_ids(
            agents_to_rerun_fixed,
            agent_results
        )
        
        # 决策逻辑
        decision = self._determine_decision(
            overall_score,
            judge_review['decision'],
            client_review['acceptance'],
            current_round,
            bool(agents_to_rerun),
            previous_score=previous_score
        )

        # 🔧 修复：如果决策是 approve，清空 agents_to_rerun 列表
        if decision == "approve":
            agents_to_rerun = set()  # 清空重新执行列表
            logger.info("✅ 决策为 approve，清空 agents_to_rerun 列表")

        final_decision = {
            "decision": decision,
            "overall_score": round(overall_score, 2),
            "individual_scores": {
                "red_team": red_review['score'],
                "blue_team": blue_review['score'],
                "judge": judge_review['score'],
                "client": client_review['score']
            },
            "agents_to_rerun": list(agents_to_rerun),
            "round": current_round,
            "reasoning": self._generate_decision_reasoning(
                overall_score,
                judge_review,
                client_review,
                agents_to_rerun
            )
        }

        return final_decision
    
    def _determine_decision(
        self,
        overall_score: float,
        judge_decision: str,
        client_acceptance: str,
        current_round: int,
        has_agents_to_rerun: bool,
        previous_score: Optional[float] = None,
        review_history: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        确定最终决策 - 🎯 问题导向，最多两轮
        
        核心理念：
        - 不关注评分，只关注是否有实际问题需要解决
        - 最多两轮：发现问题 → 改进 → 结束
        - 问题导向：有问题就改，没问题就过
        
        Returns:
            "approve" - 批准通过
            "rerun_specific" - 重新执行特定专家
        """
        # === 规则1: 达到第2轮 → 强制停止 ===
        if current_round >= 2:
            logger.info(f"✅ 规则1触发: 已完成第{current_round}轮审核，达到最大轮次(2)，停止迭代")
            return "approve"
        
        # === 规则2: 第1轮无问题 → 直接通过 ===
        if current_round == 1 and not has_agents_to_rerun:
            logger.info(f"✅ 规则2触发: 第1轮未发现需要改进的问题，直接通过")
            return "approve"
        
        # === 规则3: 第1轮有问题 → 允许一次改进 ===
        if current_round == 1 and has_agents_to_rerun:
            problem_count = len(has_agents_to_rerun) if isinstance(has_agents_to_rerun, (list, set)) else 1
            logger.info(f"🔄 规则3触发: 第1轮发现 {problem_count} 个专家需改进，启动第2轮")
            return "rerun_specific"
        
        # === 兜底 ===
        logger.info(f"✅ 兜底逻辑: 停止迭代")
        return "approve"
    
    def _generate_decision_reasoning(
        self,
        overall_score: float,
        judge_review: Dict[str, Any],
        client_review: Dict[str, Any],
        agents_to_rerun: set
    ) -> str:
        """生成决策理由"""
        reasoning_parts = []
        
        reasoning_parts.append(f"综合评分: {overall_score:.2f}")
        reasoning_parts.append(f"评委裁决: {judge_review['decision']}")
        reasoning_parts.append(f"甲方接受度: {client_review['acceptance']}")
        
        if agents_to_rerun:
            reasoning_parts.append(f"需要重新执行的专家: {', '.join(agents_to_rerun)}")
        
        return "; ".join(reasoning_parts)
    
    def _get_timestamp(self) -> str:
        """获取时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def generate_review_feedback(
        self,
        review_result: Dict[str, Any],
        agent_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        ✅ 重构：生成结构化、可执行的审核反馈
        
        从"笼统问题"改为"具体任务列表"
        
        Args:
            review_result: 审核结果
            agent_results: 当前专家结果
            
        Returns:
            结构化的反馈信息，包含每个专家的具体任务
        """
        red_review = review_result["red_team_review"]
        blue_review = review_result["blue_team_review"]
        judge_review = review_result["judge_review"]
        client_review = review_result["client_review"]
        
        # 按专家组织反馈
        feedback_by_agent = {}
        
        # 从红队改进点中提取任务
        if "improvements" in red_review:
            for imp in red_review["improvements"]:
                agent_id = imp.get("agent_id", "unknown")
                if agent_id == "unknown" or agent_id == "general":
                    continue
                
                if agent_id not in feedback_by_agent:
                    feedback_by_agent[agent_id] = {
                        "iteration_context": {
                            "round": review_result["round"],
                            "previous_output_summary": self._get_agent_summary(agent_results, agent_id),
                            "what_worked_well": [],
                            "what_needs_improvement": []
                        },
                        "specific_tasks": [],
                        "avoid_changes_to": []
                    }
                
                # 添加具体任务
                feedback_by_agent[agent_id]["specific_tasks"].append({
                    "task_id": len(feedback_by_agent[agent_id]["specific_tasks"]) + 1,
                    "category": imp.get("category", "improvement"),
                    "instruction": imp.get("issue", ""),
                    "example": imp.get("expected", ""),
                    "validation": f"需确保解决：{imp.get('issue', '')}",
                    "priority": imp.get("priority", "medium")
                })
                
                feedback_by_agent[agent_id]["iteration_context"]["what_needs_improvement"].append(
                    imp.get("issue", "")
                )
        
        # 从蓝队保留建议中提取优势
        if "keep_as_is" in blue_review:
            for keep in blue_review["keep_as_is"]:
                agent_id = keep.get("agent_id", "unknown")
                if agent_id == "unknown" or agent_id == "general":
                    continue
                
                if agent_id in feedback_by_agent:
                    feedback_by_agent[agent_id]["iteration_context"]["what_worked_well"].append(
                        keep.get("reason", "")
                    )
                    feedback_by_agent[agent_id]["avoid_changes_to"].append(
                        keep.get("aspect", "")
                    )
        
        # 从评委优先级改进中提取关键任务
        if "prioritized_improvements" in judge_review:
            for imp in judge_review["prioritized_improvements"]:
                agent_id = imp.get("agent_id", "unknown")
                if agent_id == "unknown" or agent_id == "general":
                    continue
                
                if agent_id in feedback_by_agent:
                    feedback_by_agent[agent_id]["specific_tasks"].append({
                        "task_id": len(feedback_by_agent[agent_id]["specific_tasks"]) + 1,
                        "category": "judge_priority",
                        "instruction": imp.get("task", ""),
                        "example": imp.get("rationale", ""),
                        "validation": f"评委优先级{imp.get('priority', '?')}",
                        "priority": "high" if imp.get("priority", 0) <= 2 else "medium"
                    })
        
        return {
            "round": review_result["round"],
            "overall_score": review_result["final_decision"]["overall_score"],
            "feedback_by_agent": feedback_by_agent,
            "general_feedback": {
                "red_team_summary": red_review.get("content", "")[:200],
                "blue_team_summary": blue_review.get("content", "")[:200],
                "judge_summary": judge_review.get("content", "")[:200],
                "client_summary": client_review.get("content", "")[:200]
            }
        }
    
    def _get_agent_summary(self, agent_results: Dict[str, Any], agent_id: str) -> str:
        """获取专家输出摘要"""
        result = agent_results.get(agent_id, {})
        if isinstance(result, dict):
            analysis = result.get("analysis", "")
            if isinstance(analysis, str):
                return analysis[:300] + "..." if len(analysis) > 300 else analysis
        return "（无输出摘要）"

    def _convert_fixed_to_dynamic_ids(
        self,
        fixed_ids: set,
        agent_results: Optional[Dict[str, Any]]
    ) -> set:
        """
        将 Fixed Mode 键名或前缀转换为动态角色 ID

        Args:
            fixed_ids: Fixed Mode 键名集合（如 {'v3_narrative_expert', 'v4_ux_design'}）
                      或前缀集合（如 {'V3_', 'V4_'}）
            agent_results: 专家结果字典（键是动态角色 ID）

        Returns:
            动态角色 ID 集合（如 {'V3_人物及叙事专家_3-1', 'V4_设计研究员_4-1'}）
        """
        if not agent_results:
            logger.warning("⚠️ No agent_results provided for ID conversion, returning empty set")
            return set()

        # 🔧 修复P1: 直接检查角色是否在active_agents中,而非通过前缀匹配
        # 这样可以准确识别动态角色ID (如 V3_叙事与体验专家_3-1)
        dynamic_ids = set()

        for fixed_id in fixed_ids:
            # 检查1: 是否为有效的动态角色ID
            if fixed_id in agent_results:
                dynamic_ids.add(fixed_id)
                logger.info(f"✅ 识别到有效角色: {fixed_id}")
                continue
            
            # 检查2: 是否为V前缀格式,尝试匹配完整角色ID
            if fixed_id.startswith('V'):
                # 尝试前缀匹配 (如 "V3_" 匹配 "V3_叙事与体验专家_3-1")
                prefix = fixed_id if fixed_id.endswith('_') else f"{fixed_id}_"
                found = False
                for role_id in agent_results.keys():
                    if role_id.startswith(prefix):
                        dynamic_ids.add(role_id)
                        found = True
                        logger.info(f"✅ 通过前缀匹配: {fixed_id} → {role_id}")
                        break
                if found:
                    continue
            
            # 无法识别
            logger.warning(f"⚠️ 无法识别角色ID: {fixed_id}")

        logger.info(f"🔄 Converted {len(fixed_ids)} fixed IDs to {len(dynamic_ids)} dynamic IDs")
        logger.debug(f"   Input IDs: {fixed_ids}")
        logger.debug(f"   Output IDs: {dynamic_ids}")

        return dynamic_ids

    # ============================================
    # 🆕 P1-3: 两阶段审核新方法
    # ============================================

    def _conduct_red_blue_debate(
        self,
        agent_results: Dict[str, Any],
        requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行红蓝对抗（合并为一个环节）

        流程：
        1. 红队找问题
        2. 蓝队辩护
        3. 合并结果：保留蓝队同意的问题，过滤误判

        Returns:
            红蓝对抗结果
        """
        # 红队找问题
        red_review = self._conduct_red_team_review(agent_results, requirements)

        # 蓝队辩护
        blue_review = self._conduct_blue_team_review(
            agent_results,
            requirements,
            red_review
        )

        # 合并结果：保留蓝队同意的问题，过滤误判
        validated_issues = []
        filtered_issues = []

        improvements = red_review.get("improvements", [])
        validations = blue_review.get("validations", [])

        for improvement in improvements:
            issue_id = improvement.get("issue_id", "")

            # 查找蓝队对该问题的验证
            blue_validation = None
            for validation in validations:
                if validation.get("issue_id") == issue_id:
                    blue_validation = validation
                    break

            if blue_validation:
                stance = blue_validation.get("stance", "agree")
                if stance == "agree":
                    # 蓝队同意，保留问题
                    validated_issues.append(improvement)
                else:
                    # 蓝队不同意，过滤误判
                    filtered_issues.append({
                        "issue_id": issue_id,
                        "issue": improvement.get("issue", ""),
                        "blue_defense": blue_validation.get("defense", ""),
                        "reason": "蓝队辩护成功，判定为误判"
                    })
                    logger.info(f"🛡️ 蓝队辩护成功，过滤误判：{issue_id}")
            else:
                # 蓝队未回应，默认保留
                validated_issues.append(improvement)

        logger.info(f"📊 红蓝对抗结果：")
        logger.info(f"   红队原始问题: {len(improvements)} 个")
        logger.info(f"   蓝队过滤误判: {len(filtered_issues)} 个")
        logger.info(f"   最终有效问题: {len(validated_issues)} 个")

        return {
            "red_review": red_review,
            "blue_review": blue_review,
            "validated_issues": validated_issues,  # 🆕 经过辩护的有效问题
            "filtered_issues": filtered_issues,    # 🆕 被过滤的误判
            "red_raw_issues": improvements,
            "blue_defenses": validations,
            "filtered_count": len(filtered_issues)
        }

    def _conduct_client_review_v2(
        self,
        agent_results: Dict[str, Any],
        requirements: Dict[str, Any],
        red_blue_debate: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行甲方审核 v2 - 基于红蓝对抗结果做最终决策

        Args:
            agent_results: 专家分析结果
            requirements: 项目需求
            red_blue_debate: 红蓝对抗结果（包含validated_issues）

        Returns:
            甲方审核结果
        """
        logger.info("甲方开始最终决策（基于红蓝对抗结果）...")

        # 构建伪judge_review（兼容旧的ClientReviewer接口）
        # 将validated_issues转换为judge_review格式
        validated_issues = red_blue_debate.get("validated_issues", [])

        pseudo_judge_review = {
            "rulings": [
                {
                    "issue_id": issue.get("issue_id", ""),
                    "ruling": "accept",  # 经过蓝队验证的问题都是accept
                    "priority": issue.get("priority", "medium"),
                    "rationale": issue.get("issue", "")
                }
                for issue in validated_issues
            ],
            "prioritized_improvements": validated_issues,
            "content": f"经过红蓝对抗，确认{len(validated_issues)}个有效问题"
        }

        # 调用原有的ClientReviewer（传递伪judge_review）
        client_review = self.client.review(
            agent_results,
            requirements,
            judge_review=pseudo_judge_review
        )

        accepted = client_review.get('accepted_improvements', [])
        rejected = client_review.get('rejected_improvements', [])
        must_fix = sum(1 for a in accepted if a.get('business_priority') == 'must_fix')

        logger.info(f"甲方决策: 接受 {len(accepted)} 项改进（{must_fix} must_fix），拒绝 {len(rejected)} 项")

        return client_review

    def _generate_final_ruling_v2(
        self,
        red_blue_debate: Dict[str, Any],
        client_review: Dict[str, Any]
    ) -> str:
        """
        生成最终裁定文档 v2（两阶段版本）

        Returns:
            最终裁定文本（可直接用于报告）
        """
        logger.info("生成最终裁定文档（两阶段版本）...")

        # 从甲方审核结果中获取final_ruling字段
        final_ruling = client_review.get('final_ruling', '')

        if not final_ruling:
            # 如果没有，手动生成简版
            accepted = client_review.get('accepted_improvements', [])
            validated_issues = red_blue_debate.get('validated_issues', [])
            filtered_issues = red_blue_debate.get('filtered_issues', [])

            final_ruling = f"""
## 📋 最终裁定（两阶段审核）

### 红蓝对抗结果
- 红队发现问题: {len(red_blue_debate.get('red_raw_issues', []))} 个
- 蓝队过滤误判: {len(filtered_issues)} 个
- 最终有效问题: {len(validated_issues)} 个

### 甲方决策
{client_review.get('final_decision', 'N/A')}

### 改进要求
- 必须修复项: {sum(1 for a in accepted if a.get('business_priority') == 'must_fix')} 项
- 建议修复项: {sum(1 for a in accepted if a.get('business_priority') == 'should_fix')} 项
- 可选优化项: {sum(1 for a in accepted if a.get('business_priority') == 'nice_to_have')} 项

### 执行路线图
"""
            for idx, improvement in enumerate(accepted[:5], 1):  # 只取前5项
                final_ruling += f"{idx}. {improvement.get('issue_id', 'N/A')} - {improvement.get('deadline', 'N/A')}\n"

        return final_ruling.strip()

