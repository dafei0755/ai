"""
ResultAggregator 格式化 & 兜底报告 Mixin
由 scripts/refactor/_split_mt12_result_aggregator.py 自动生成 (MT-12)
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from ..workflow.state import ProjectAnalysisState


class AggregatorFormatMixin:
    """Mixin — ResultAggregator 格式化 & 兜底报告 Mixin"""
    def _update_progress(self, state: ProjectAnalysisState, detail: str, progress: float):
        """
         Phase 1.4: 更新进度到状态（用于WebSocket推送）

        Args:
            state: 当前状态
            detail: 进度详情描述
            progress: 进度值（0.0-1.0）
        """
        try:
            # 更新状态中的进度信息
            state["current_stage"] = "终审聚合"
            state["detail"] = detail
            state["progress"] = progress

            logger.info(f" [终审聚合] {detail} ({progress*100:.0f}%)")
        except Exception as e:
            # 进度更新失败不应阻塞主流程
            logger.warning(f"️ 进度更新失败: {e}")


    def _format_agent_results(self, agent_results: Dict[str, Any]) -> str:
        """格式化智能体结果用于聚合输出 - 支持TaskOrientedExpertOutput结构"""
        if not agent_results:
            return "(no agent results available)"

        formatted_blocks: List[str] = []

        for agent_id, result in agent_results.items():
            if not result:
                continue

            # 检查是否为TaskOrientedExpertOutput结构
            structured_output = result.get("structured_output")
            if structured_output and isinstance(structured_output, dict):
                # 新的任务导向输出格式
                formatted_block = self._format_task_oriented_output(agent_id, result, structured_output)
            else:
                # 传统格式（向后兼容）
                formatted_block = self._format_legacy_output(agent_id, result)

            if formatted_block:
                formatted_blocks.append(formatted_block)

        return "\n\n".join(formatted_blocks) if formatted_blocks else "(no agent results available)"


    def _format_task_oriented_output(
        self, agent_id: str, result: Dict[str, Any], structured_output: Dict[str, Any]
    ) -> str:
        """
        格式化TaskOrientedExpertOutput结构的专家输出

        Args:
            agent_id: 专家ID
            result: 完整的专家执行结果
            structured_output: TaskOrientedExpertOutput结构化数据

        Returns:
            str: 格式化的输出字符串
        """
        lines = []

        #  V7情感洞察专家特殊处理
        if agent_id.startswith("7-") or agent_id.startswith("V7_"):
            expert_name = result.get("expert_name", "V7_情感洞察专家")
            confidence = structured_output.get("confidence", 0.0)

            lines.append(f"### {expert_name} ({agent_id}) - 人性维度洞察")
            lines.append(f"**分析置信度**: {confidence:.1%}")
            lines.append("")

            # 提取情感字段
            emotional_fields = {
                "emotional_landscape": "情绪地图",
                "spiritual_aspirations": "精神追求",
                "psychological_safety_needs": "心理安全需求",
                "ritual_behaviors": "仪式行为洞察",
                "memory_anchors": "记忆锚点识别",
            }

            for field_key, field_name in emotional_fields.items():
                field_value = structured_output.get(field_key)
                if field_value:
                    lines.append(f"**{field_name}**:")
                    if isinstance(field_value, dict):
                        for k, v in field_value.items():
                            lines.append(f"  - {k}: {v}")
                    elif isinstance(field_value, list):
                        for item in field_value:
                            if isinstance(item, dict):
                                lines.append(f"  - {json.dumps(item, ensure_ascii=False)}")
                            else:
                                lines.append(f"  - {item}")
                    else:
                        lines.append(f"  {field_value}")
                    lines.append("")

            # targeted_analysis特殊处理
            targeted = structured_output.get("targeted_analysis")
            if targeted:
                lines.append("**专项情感分析**:")
                lines.append(json.dumps(targeted, ensure_ascii=False, indent=2))
                lines.append("")

            return "\n".join(lines).strip()

        # 原有V2-V6专家处理逻辑
        # 专家基本信息
        expert_summary = structured_output.get("expert_summary", {})
        expert_name = expert_summary.get("expert_name", result.get("expert_name", agent_id))
        objective = expert_summary.get("objective_statement", "未指定目标")

        lines.append(f"### {expert_name} ({agent_id}) - 任务导向输出")
        lines.append(f"**完成目标**: {objective}")
        lines.append("")

        # 任务结果
        task_results = structured_output.get("task_results", [])
        if task_results:
            lines.append("**交付物结果**:")
            for i, deliverable in enumerate(task_results, 1):
                name = deliverable.get("deliverable_name", f"交付物{i}")
                content = deliverable.get("content", "")
                format_type = deliverable.get("format", "analysis")
                completeness = deliverable.get("completeness_score", 0.0)
                methodology = deliverable.get("methodology", "未指定")

                lines.append(f"  {i}. **{name}** ({format_type}, 完成度: {completeness:.1%})")
                lines.append(f"     方法: {methodology}")

                # 内容摘要（限制长度）
                if content:
                    if len(content) > 500:
                        content_preview = content[:500] + "..."
                    else:
                        content_preview = content
                    lines.append(f"     内容: {content_preview}")
                lines.append("")

        # 协议执行状态
        protocol_execution = structured_output.get("protocol_execution", {})
        if protocol_execution:
            final_status = protocol_execution.get("final_status", "unknown")
            confidence_level = protocol_execution.get("confidence_level", 0.0)
            lines.append(f"**协议执行状态**: {final_status} (信心水平: {confidence_level:.1%})")

            # 自主行动
            autonomy_actions = protocol_execution.get("autonomy_actions_taken", [])
            if autonomy_actions:
                lines.append("**采取的自主行动**:")
                for action in autonomy_actions[:3]:  # 限制显示前3个
                    lines.append(f"  - {action}")
                if len(autonomy_actions) > 3:
                    lines.append(f"  - ... (共{len(autonomy_actions)}项)")

            # 挑战和重新解释
            challenges = protocol_execution.get("challenges_raised", [])
            reinterpretations = protocol_execution.get("reinterpretations_made", [])
            if challenges:
                lines.append(f"**提出挑战**: {len(challenges)}项")
            if reinterpretations:
                lines.append(f"**重新解释**: {len(reinterpretations)}项")
            lines.append("")

        # 验证清单
        validation_checklist = structured_output.get("validation_checklist", [])
        if validation_checklist:
            met_criteria = sum(1 for item in validation_checklist if item.get("status") == "met")
            total_criteria = len(validation_checklist)
            lines.append(f"**质量验证**: {met_criteria}/{total_criteria} 项标准满足")
            lines.append("")

        # 原始输出引用（如果需要）
        if result.get("analysis"):
            analysis = result["analysis"]
            if len(analysis) > 200:
                analysis_preview = analysis[:200] + "..."
            else:
                analysis_preview = analysis
            lines.append(f"**原始输出预览**: {analysis_preview}")
            lines.append("")

        return "\n".join(lines).strip()


    def _format_legacy_output(self, agent_id: str, result: Dict[str, Any]) -> str:
        """
        格式化传统格式的专家输出（向后兼容）
        """
        role_name = result.get("role_name", result.get("expert_name", agent_id))
        confidence = result.get("confidence", 0.0)

        structured_data = result.get("structured_data", {})
        if isinstance(structured_data, dict):
            structured_str = json.dumps(structured_data, ensure_ascii=False, indent=2)
            if len(structured_str) > 2000:
                structured_str = structured_str[:2000] + "\n... (truncated)"
        else:
            structured_str = str(structured_data)

        narrative = result.get("analysis") or result.get("content") or ""
        if isinstance(narrative, str) and len(narrative) > 2000:
            narrative = narrative[:2000] + "\n... (truncated)"
        if not narrative:
            narrative = "_No narrative summary provided._"

        return "\n".join(
            [
                f"### {role_name} ({agent_id}) - 传统格式",
                f"confidence: {confidence:.2f}",
                "structured_data:",
                structured_str or "{}",
                "narrative_summary:",
                narrative,
            ]
        )


    def _parse_final_report(self, llm_response: str, state: ProjectAnalysisState) -> Dict[str, Any]:
        """解析最终报告结构"""
        try:
            # 尝试提取JSON部分
            start_idx = llm_response.find("{")
            end_idx = llm_response.rfind("}") + 1

            if start_idx != -1 and end_idx > start_idx:
                json_str = llm_response[start_idx:end_idx]
                final_report = json.loads(json_str)
            else:
                # 如果没有找到JSON，创建基础结构
                final_report = self._create_fallback_report(llm_response, state)

            # 添加元数据
            final_report["metadata"] = {
                "generated_at": datetime.now().isoformat(),
                "session_id": state.get("session_id"),
                "total_agents": len(state.get("agent_results", {})),
                "overall_confidence": self._calculate_overall_confidence(state),
                "estimated_pages": self._estimate_report_pages(final_report),
            }

            return final_report

        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON from final report, using fallback structure")
            return self._create_fallback_report(llm_response, state)


    def _create_fallback_report(self, content: str, state: ProjectAnalysisState) -> Dict[str, Any]:
        """
        创建备用的报告结构

         v7.154: 增强 fallback 路径，从专家报告中提取实际内容而非占位符
        """
        structured_requirements = state.get("structured_requirements", {})
        agent_results = state.get("agent_results", {})
        active_agents = state.get("active_agents", [])
        strategic_analysis = state.get("strategic_analysis", {})

        #  P1修复: 使用动态角色ID提取内容，而非硬编码的agent key
        # 辅助函数：根据动态role_id提取内容
        def extract_content_by_role_prefix(prefix: str) -> Dict[str, Any]:
            """根据角色前缀从动态role_id中提取structured_data"""
            for role_id in active_agents:
                if role_id.startswith(prefix):
                    agent_result = agent_results.get(role_id, {})
                    if isinstance(agent_result, dict):
                        return agent_result.get("structured_data", agent_result.get("content", {}))
            return {}

        # 辅助函数：根据动态role_id提取confidence
        def extract_confidence_by_role_prefix(prefix: str) -> float:
            """根据角色前缀从动态role_id中提取confidence"""
            for role_id in active_agents:
                if role_id.startswith(prefix):
                    agent_result = agent_results.get(role_id, {})
                    if isinstance(agent_result, dict):
                        return agent_result.get("confidence", 0.0)
            return 0.0

        #  v7.154: 从专家报告中提取关键发现
        def extract_key_findings() -> List[str]:
            """从专家报告中提取关键发现"""
            findings = []
            for role_id in active_agents:
                if not any(role_id.startswith(prefix) for prefix in ["V2_", "V3_", "V4_", "V5_", "V6_", "V7_"]):
                    continue
                agent_result = agent_results.get(role_id, {})
                if not isinstance(agent_result, dict):
                    continue

                # 从 structured_data 中提取
                structured_data = agent_result.get("structured_data", {})
                if isinstance(structured_data, dict):
                    ter = structured_data.get("task_execution_report", {})
                    if isinstance(ter, dict):
                        # 提取 additional_insights
                        insights = ter.get("additional_insights", [])
                        if isinstance(insights, list):
                            for insight in insights[:2]:
                                if isinstance(insight, str) and insight and len(insight) > 10:
                                    findings.append(insight[:150])
                        # 提取 task_completion_summary
                        summary = ter.get("task_completion_summary", "")
                        if isinstance(summary, str) and summary and len(summary) > 20:
                            findings.append(summary[:150])

                # 从 analysis 字段提取
                analysis = agent_result.get("analysis", "")
                if isinstance(analysis, str) and analysis and len(analysis) > 50:
                    # 提取第一句话作为发现
                    first_sentence = analysis.split("。")[0]
                    if first_sentence and len(first_sentence) > 10:
                        findings.append(first_sentence[:150])

                if len(findings) >= 5:
                    break

            return findings[:5] if findings else ["基于多智能体分析的综合发现"]

        #  v7.154: 从专家报告中提取建议
        def extract_key_recommendations() -> List[str]:
            """从专家报告中提取关键建议"""
            recommendations = []
            for role_id in active_agents:
                if not any(role_id.startswith(prefix) for prefix in ["V2_", "V3_", "V4_", "V5_", "V6_", "V7_"]):
                    continue
                agent_result = agent_results.get(role_id, {})
                if not isinstance(agent_result, dict):
                    continue

                structured_data = agent_result.get("structured_data", {})
                if isinstance(structured_data, dict):
                    ter = structured_data.get("task_execution_report", {})
                    if isinstance(ter, dict):
                        # 提取 execution_challenges 作为建议
                        challenges = ter.get("execution_challenges", [])
                        if isinstance(challenges, list):
                            for challenge in challenges[:2]:
                                if isinstance(challenge, str) and challenge:
                                    recommendations.append(f"注意: {challenge[:100]}")
                                elif isinstance(challenge, dict):
                                    desc = challenge.get("description", challenge.get("challenge", ""))
                                    if desc:
                                        recommendations.append(f"注意: {desc[:100]}")

                if len(recommendations) >= 5:
                    break

            return recommendations[:5] if recommendations else ["基于分析结果的核心建议"]

        #  v7.154: 提取跨领域洞察
        def extract_cross_domain_insights() -> List[str]:
            """提取跨领域洞察"""
            insights = []
            expert_summaries = []

            for role_id in active_agents:
                if not any(role_id.startswith(prefix) for prefix in ["V2_", "V3_", "V4_", "V5_", "V6_", "V7_"]):
                    continue
                agent_result = agent_results.get(role_id, {})
                if not isinstance(agent_result, dict):
                    continue

                role_name = agent_result.get("role_name", role_id)
                analysis = agent_result.get("analysis", "")
                if analysis and len(analysis) > 50:
                    expert_summaries.append(f"{role_name}: {analysis[:100]}")

            if expert_summaries:
                insights.append(f"综合{len(expert_summaries)}位专家的分析视角")
                for summary in expert_summaries[:3]:
                    insights.append(summary)

            return insights if insights else ["跨领域的关键洞察"]

        #  对所有可能包含 JTBD 公式的字段进行转换
        transformed_requirements = structured_requirements.copy()

        # 转换 project_overview（最重要）
        if "project_overview" in transformed_requirements:
            transformed_requirements["project_overview"] = transform_jtbd_to_natural_language(
                transformed_requirements["project_overview"]
            )

        # 转换 project_task（JTBD 公式来源）
        if "project_task" in transformed_requirements:
            transformed_requirements["project_task"] = transform_jtbd_to_natural_language(
                transformed_requirements["project_task"]
            )

        # 转换 core_objectives（可能包含 JTBD 公式）
        if "core_objectives" in transformed_requirements and isinstance(
            transformed_requirements["core_objectives"], list
        ):
            transformed_requirements["core_objectives"] = [
                transform_jtbd_to_natural_language(obj) if isinstance(obj, str) else obj
                for obj in transformed_requirements["core_objectives"]
            ]

        #  v7.26.2: 提取用户核心问题和交付物
        user_input = state.get("user_input", "")
        user_question = user_input[:100] + "..." if len(user_input) > 100 else user_input

        # 从专家结果中提取交付物名称
        deliverable_names = []
        for role_id in active_agents:
            if any(role_id.startswith(prefix) for prefix in ["V2_", "V3_", "V4_", "V5_", "V6_", "V7_"]):
                agent_result = agent_results.get(role_id, {})
                if isinstance(agent_result, dict):
                    structured = agent_result.get("structured_data", {})
                    if isinstance(structured, dict):
                        ter = structured.get("task_execution_report", {})
                        if isinstance(ter, dict):
                            outputs = ter.get("deliverable_outputs", [])
                            for output in outputs:
                                if isinstance(output, dict):
                                    name = output.get("deliverable_name", output.get("name", ""))
                                    if name and name not in deliverable_names:
                                        deliverable_names.append(name)

        if not deliverable_names:
            deliverable_names = ["综合分析报告", "专家建议汇总"]

        #  v7.154: 提取实际内容而非占位符
        key_findings = extract_key_findings()
        key_recommendations = extract_key_recommendations()
        cross_domain_insights = extract_cross_domain_insights()

        #  v7.154: 从 strategic_analysis 提取推敲过程
        query_type = "深度优先探询"
        query_type_reasoning = ""
        role_selection = []
        if isinstance(strategic_analysis, dict):
            query_type = strategic_analysis.get("query_type", "深度优先探询")
            query_type_reasoning = strategic_analysis.get("query_type_reasoning", "")
            selected_roles = strategic_analysis.get("selected_roles", [])
            for role in selected_roles[:5]:
                if isinstance(role, dict):
                    role_name = role.get("dynamic_role_name", role.get("role_id", ""))
                    reason = role.get("selection_reason", "")
                    if role_name:
                        role_selection.append(f"{role_name}: {reason[:50]}" if reason else role_name)

        return {
            "executive_summary": {
                "project_overview": transform_jtbd_to_natural_language(
                    structured_requirements.get("project_overview", "")
                ),
                "key_findings": key_findings,
                "key_recommendations": key_recommendations,
                "success_factors": [
                    f"专家团队协作: {len(active_agents)}位专家参与分析",
                    "多维度视角: 涵盖设计、研究、叙事等多个领域",
                    "结构化输出: 提供可执行的交付物清单",
                ],
            },
            #  v7.26.2: 添加 core_answer 字段（fallback 路径必须）
            "core_answer": {
                "question": user_question or "用户咨询问题",
                "answer": structured_requirements.get("project_overview", "请查看各专家的详细分析报告"),
                "deliverables": deliverable_names[:5],
                "timeline": "请参考工程师专家的实施规划",
                "budget_range": "请参考工程师专家的成本估算",
            },
            #  v7.26.2: 添加 insights 字段（fallback 路径必须）
            "insights": {
                "key_insights": key_findings[:3]
                if key_findings
                else [structured_requirements.get("project_overview", "基于用户需求的综合分析")],
                "cross_domain_connections": cross_domain_insights[:3],
                "user_needs_interpretation": structured_requirements.get("project_task", "用户需求的深度解读"),
            },
            #  v7.154: 增强 deliberation_process 字段
            "deliberation_process": {
                "inquiry_architecture": query_type,
                "reasoning": query_type_reasoning[:200] if query_type_reasoning else "基于用户需求进行多维度分析",
                "role_selection": role_selection if role_selection else [f"选择了 {len(active_agents)} 位专家进行协同分析"],
                "strategic_approach": f"采用{query_type}策略，综合{len(active_agents)}位专家的专业视角进行深度分析",
            },
            "sections": {
                ReportSection.REQUIREMENTS_ANALYSIS.value: {
                    "title": "需求分析",
                    "content": transformed_requirements,
                    "confidence": 0.8,
                },
                ReportSection.DESIGN_RESEARCH.value: {
                    "title": "设计研究",
                    "content": extract_content_by_role_prefix("V4_"),  # V4是设计研究
                    "confidence": extract_confidence_by_role_prefix("V4_"),
                },
                ReportSection.TECHNICAL_ARCHITECTURE.value: {
                    "title": "技术架构",
                    "content": extract_content_by_role_prefix("V2_"),  # V2是设计总监/技术
                    "confidence": extract_confidence_by_role_prefix("V2_"),
                },
                ReportSection.UX_DESIGN.value: {
                    "title": "用户体验设计",
                    "content": extract_content_by_role_prefix("V3_"),  # V3是叙事/体验
                    "confidence": extract_confidence_by_role_prefix("V3_"),
                },
                ReportSection.BUSINESS_MODEL.value: {
                    "title": "商业模式",
                    "content": extract_content_by_role_prefix("V5_"),  # V5是场景专家
                    "confidence": extract_confidence_by_role_prefix("V5_"),
                },
                ReportSection.IMPLEMENTATION_PLAN.value: {
                    "title": "实施规划",
                    "content": extract_content_by_role_prefix("V6_"),  # V6是工程师
                    "confidence": extract_confidence_by_role_prefix("V6_"),
                },
            },
            "comprehensive_analysis": {
                "cross_domain_insights": cross_domain_insights,
                "integrated_recommendations": key_recommendations,
                "risk_assessment": [challenge for challenge in key_recommendations if "注意" in challenge]
                or ["请参考各专家报告中的风险提示"],
                "implementation_roadmap": [f"交付物: {name}" for name in deliverable_names[:5]],
            },
            "conclusions": {
                "project_analysis_summary": structured_requirements.get("project_overview", "项目分析总结"),
                "next_steps": key_recommendations[:3] if key_recommendations else ["下一步行动建议"],
                "success_metrics": [
                    f"完成{len(deliverable_names)}项核心交付物",
                    f"获得{len(active_agents)}位专家的专业分析",
                    "形成可执行的实施方案",
                ],
            },
            "raw_content": content,
        }

