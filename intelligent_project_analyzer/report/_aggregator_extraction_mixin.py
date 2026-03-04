"""
ResultAggregator 数据提取 Mixin
由 scripts/refactor/_split_mt12_result_aggregator.py 自动生成 (MT-12)
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from ..workflow.state import ProjectAnalysisState


class AggregatorExtractionMixin:
    """Mixin — ResultAggregator 数据提取 Mixin"""
    def _has_placeholder_content(self, expert_reports: Dict[str, str]) -> bool:
        """
        检测 expert_reports 内容是否为占位符

        LLM 有时会返回类似 "{...内容略，详见原始输入...}" 的占位符文本
        这种情况需要用真实数据覆盖

        Returns:
            True 如果包含占位符内容，False 如果内容有效
        """
        if not expert_reports:
            return True

        placeholders = ["...内容略", "内容略，详见", "详见原始输入", "...(truncated)", "暂无报告内容", "(omitted)", "省略", "略..."]

        for role_id, content in expert_reports.items():
            if isinstance(content, str):
                for placeholder in placeholders:
                    if placeholder in content:
                        logger.debug(f"Detected placeholder in {role_id}: '{placeholder}'")
                        return True

        return False


    def _extract_expert_reports(self, state: ProjectAnalysisState) -> Dict[str, str]:
        """
        提取专家原始报告用于附录

        返回格式：
        {
            "V2_设计总监_2-1": "完整的原始报告内容...",
            "V3_人物及叙事专家_3-1": "完整的原始报告内容...",
            ...
        }

         修复: 支持 Dynamic Mode，使用动态角色 ID（如 "V2_设计总监_2-1"）
         优化: 使用 dynamic_role_name 作为显示名称（如 "V5_商业零售运营专家_5-2"）
        """
        agent_results = state.get("agent_results", {})
        active_agents = state.get("active_agents", [])
        strategic_analysis = state.get("strategic_analysis", {})
        selected_roles = strategic_analysis.get("selected_roles", []) if isinstance(strategic_analysis, dict) else []
        expert_reports = {}

        #  构建 role_id -> dynamic_role_name 的映射
        role_display_names = {}
        for role in selected_roles:
            if isinstance(role, dict):
                rid = role.get("role_id", "")
                dynamic_name = role.get("dynamic_role_name", "")
                if rid and dynamic_name:
                    role_display_names[rid] = dynamic_name

        logger.debug(f" Extracting expert reports from {len(active_agents)} active agents")
        logger.debug(f" Role display names mapping: {role_display_names}")

        for role_id in active_agents:
            # 跳过需求分析师和项目总监（不需要在附录中）
            if role_id in ["requirements_analyst", "project_director"]:
                continue

            # 只提取 V2-V6 专家的报告
            if not any(role_id.startswith(prefix) for prefix in ["V2_", "V3_", "V4_", "V5_", "V6_"]):
                continue

            agent_result = agent_results.get(role_id, {})
            if agent_result:
                # 提取完整的内容
                content = agent_result.get("content", "")
                structured_data = agent_result.get("structured_data", {})

                #  v7.9.2: 智能提取实际内容,与前端逻辑一致
                # 检测 TaskOrientedExpertOutput 结构,提取 deliverable_outputs
                if structured_data and isinstance(structured_data, dict):
                    # 检查是否有 task_execution_report 嵌套结构
                    ter = structured_data.get("task_execution_report")
                    if ter and isinstance(ter, dict):
                        deliverable_outputs = ter.get("deliverable_outputs")
                        if deliverable_outputs and isinstance(deliverable_outputs, list):
                            # 只提取交付物内容,忽略元数据
                            extracted_content = {"deliverable_outputs": deliverable_outputs}
                            # 可选: 添加额外信息(但不包括元数据)
                            if ter.get("task_completion_summary"):
                                extracted_content["task_completion_summary"] = ter["task_completion_summary"]
                            if ter.get("additional_insights"):
                                extracted_content["additional_insights"] = ter["additional_insights"]
                            if ter.get("execution_challenges"):
                                extracted_content["execution_challenges"] = ter["execution_challenges"]

                            report_content = json.dumps(extracted_content, ensure_ascii=False, indent=2)
                        else:
                            # 没有 deliverable_outputs,使用整个 structured_data
                            report_content = json.dumps(structured_data, ensure_ascii=False, indent=2)
                    else:
                        # 没有 task_execution_report,使用整个 structured_data
                        report_content = json.dumps(structured_data, ensure_ascii=False, indent=2)
                elif content:
                    report_content = content
                else:
                    report_content = "暂无报告内容"

                #  使用 dynamic_role_name 构建显示名称
                # 格式: "4-1 潮玩风格案例研究员"
                display_name = role_id

                #  v7.25: 从完整格式 role_id 提取短格式后缀用于查找
                # role_id 格式: "V2_设计总监_2-1" -> 短格式: "2-1"
                # role_display_names 的 key 是短格式 "2-1"
                import re

                suffix_match = re.search(r"(\d+-\d+)$", role_id)
                short_role_id = suffix_match.group(1) if suffix_match else role_id

                # 尝试用短格式查找 dynamic_role_name
                if short_role_id in role_display_names:
                    dynamic_name = role_display_names[short_role_id]
                    display_name = f"{short_role_id} {dynamic_name}"
                    logger.debug(f" [v7.25] 使用动态名称: {role_id} → {display_name}")
                elif role_id in role_display_names:
                    # 兼容：也支持完整格式作为 key
                    dynamic_name = role_display_names[role_id]
                    if suffix_match:
                        display_name = f"{short_role_id} {dynamic_name}"
                    else:
                        display_name = dynamic_name

                expert_reports[display_name] = report_content
                logger.debug(f" Extracted expert report: {display_name} ({len(report_content)} chars)")

        logger.info(f" Extracted {len(expert_reports)} expert reports: {list(expert_reports.keys())}")
        return expert_reports


    def _manually_populate_sections(self, state: ProjectAnalysisState) -> List[Dict[str, Any]]:
        """
        手动从 agent_results 中提取并填充 sections

        这是一个兜底方案，当 LLM 返回空 sections 时使用

         修复: 支持 Dynamic Mode，使用动态角色 ID（如 "V2_设计总监_2-1"）
         修复: 返回List而不是Dict,以匹配新的数据结构
        """
        agent_results = state.get("agent_results", {})
        active_agents = state.get("active_agents", [])
        sections = []  # 改为列表
        sections_dict: Dict[str, Dict[str, Any]] = {}

        section_order = [
            "requirements_analysis",
            "design_research",
            "technical_architecture",
            "ux_design",
            "business_model",
            "implementation_plan",
        ]

        logger.debug(f" agent_results keys: {list(agent_results.keys())}")
        logger.debug(f" active_agents: {active_agents}")

        # 章节类型到标题的映射
        section_titles = {
            "requirements_analysis": "需求分析",
            "design_research": "设计研究",
            "technical_architecture": "技术架构",
            "ux_design": "用户体验设计",
            "business_model": "商业模式",
            "implementation_plan": "实施规划",
        }

        # 1. 处理需求分析师（固定键名）
        requirements_result = agent_results.get("requirements_analyst", {})
        if requirements_result and requirements_result.get("structured_data"):
            # 将structured_data转换为字符串格式
            structured_data = requirements_result.get("structured_data", {})
            content_str = json.dumps(structured_data, ensure_ascii=False, indent=2)

            sections_dict["requirements_analysis"] = {
                "section_id": "requirements_analysis",  # 添加section_id
                "title": section_titles["requirements_analysis"],
                "content": content_str,  # 使用字符串格式
                "confidence": requirements_result.get("confidence", 0.5),
            }
            logger.debug(" Manually populated section: requirements_analysis from requirements_analyst")

        # 2. 处理 V2-V6 专家（Dynamic Mode 使用动态角色 ID）
        # 根据角色 ID 前缀映射到章节类型
        role_prefix_to_section = {
            "V2_": "technical_architecture",
            "V3_": "ux_design",
            "V4_": "design_research",
            "V5_": "business_model",
            "V6_": "implementation_plan",
        }

        for role_id in active_agents:
            # 跳过需求分析师（已处理）
            if role_id == "requirements_analyst":
                continue

            # 根据前缀确定章节类型
            section_key = None
            for prefix, section_type in role_prefix_to_section.items():
                if role_id.startswith(prefix):
                    section_key = section_type
                    break

            if not section_key:
                logger.warning(f"️ Unknown role prefix for {role_id}, skipping")
                continue

            # 从 agent_results 中获取数据
            agent_result = agent_results.get(role_id, {})
            section_entry = sections_dict.get(section_key)
            if section_entry is None:
                section_entry = {
                    "section_id": section_key,
                    "title": section_titles[section_key],
                    "content": "",
                    "confidence": 0.0,
                }
                sections_dict[section_key] = section_entry

            if agent_result and agent_result.get("structured_data"):
                structured_data = agent_result.get("structured_data", {})
                content_str = json.dumps(structured_data, ensure_ascii=False, indent=2)

                if not section_entry["content"] or section_entry["content"].startswith("暂无"):
                    section_entry["content"] = content_str
                    confidence_value = agent_result.get("confidence", 0.5)
                    try:
                        section_entry["confidence"] = float(confidence_value)
                    except (TypeError, ValueError):
                        section_entry["confidence"] = 0.5
                else:
                    logger.debug(
                        "ℹ️ Section {} already populated, skipping additional content from {}",
                        section_key,
                        role_id,
                    )
                logger.debug(f" Manually populated section: {section_key} from {role_id}")
            else:
                if not section_entry["content"]:
                    section_entry["content"] = f"暂无{section_titles[section_key]}数据"
                    section_entry["confidence"] = 0.0
                logger.warning(f"️ No data found for {role_id}, created empty section for {section_key}")

        for section_id in section_order:
            if section_id in sections_dict:
                sections.append(sections_dict[section_id])

        for section_id, payload in sections_dict.items():
            if section_id not in section_order:
                sections.append(payload)

        logger.info(
            " Manually populated %d sections: %s",
            len(sections),
            [section["section_id"] for section in sections],
        )
        return sections


    def _extract_challenge_resolutions(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        """
         v3.5.1: 提取挑战解决结果

        从state中提取专家挑战的闭环处理结果，用于报告生成

        Returns:
            {
                "accepted_reinterpretations": [...],  # Accept决策的结果
                "synthesized_frameworks": [...],      # Synthesize决策的结果
                "escalated_to_client": [...],         # Escalate决策的结果
                "summary": {...}                      # 统计摘要
            }
        """
        # 提取各类闭环结果
        expert_driven_insights = state.get("expert_driven_insights", {})
        framework_synthesis = state.get("framework_synthesis", {})
        escalated_challenges = state.get("escalated_challenges", [])

        # 统计
        accepted_count = len(expert_driven_insights)
        synthesized_count = len(framework_synthesis)
        escalated_count = len(escalated_challenges)

        # 如果没有任何挑战解决，返回空结构
        if accepted_count == 0 and synthesized_count == 0 and escalated_count == 0:
            return {"has_challenges": False, "summary": "所有专家接受需求分析师的洞察，无挑战标记"}

        # 格式化Accept决策结果
        accepted_reinterpretations = []
        for item, insight in expert_driven_insights.items():
            accepted_reinterpretations.append(
                {
                    "challenged_item": item,
                    "expert": insight.get("accepted_from", "unknown"),
                    "reinterpretation": insight.get("expert_reinterpretation", ""),
                    "design_impact": insight.get("design_impact", ""),
                    "timestamp": insight.get("timestamp", ""),
                }
            )

        # 格式化Synthesize决策结果
        synthesized_frameworks = []
        for item, synthesis in framework_synthesis.items():
            synthesized_frameworks.append(
                {
                    "challenged_item": item,
                    "competing_count": len(synthesis.get("competing_frames", [])),
                    "synthesis_summary": synthesis.get("synthesis_summary", ""),
                    "recommendation": synthesis.get("recommendation", ""),
                }
            )

        # 格式化Escalate决策结果
        escalated_items = []
        for challenge in escalated_challenges:
            escalated_items.append(
                {
                    "issue_id": challenge.get("issue_id", ""),
                    "description": challenge.get("description", ""),
                    "expert_rationale": challenge.get("expert_rationale", ""),
                    "requires_client_decision": challenge.get("requires_client_decision", True),
                }
            )

        return {
            "has_challenges": True,
            "accepted_reinterpretations": accepted_reinterpretations,
            "synthesized_frameworks": synthesized_frameworks,
            "escalated_to_client": escalated_items,
            "summary": {
                "total_challenges": accepted_count + synthesized_count + escalated_count,
                "accepted_count": accepted_count,
                "synthesized_count": synthesized_count,
                "escalated_count": escalated_count,
                "closure_rate": f"{(accepted_count + synthesized_count) / max(1, accepted_count + synthesized_count + escalated_count) * 100:.1f}%",
            },
        }


    def _calculate_overall_confidence(self, state: ProjectAnalysisState) -> float:
        """计算整体置信度"""
        agent_results = state.get("agent_results", {})

        if not agent_results:
            return 0.0

        confidences = [
            result.get("confidence", 0)
            for result in agent_results.values()
            if result and isinstance(result.get("confidence"), int | float)
        ]

        if not confidences:
            return 0.0

        # 计算加权平均置信度
        return sum(confidences) / len(confidences)


    def _get_expert_distribution(self, agent_results: Dict[str, Any]) -> Dict[str, int]:
        """
        获取专家分布统计

         v7.154: 修复模式匹配逻辑，支持完整格式 role_id

        Args:
            agent_results: 专家执行结果

        Returns:
            按专家层级（V2-V7）分类的数量统计
        """
        distribution = {
            "V2_设计总监": 0,
            "V3_领域专家": 0,
            "V4_研究专家": 0,
            "V5_创新专家": 0,
            "V6_实施专家": 0,
            "V7_情感专家": 0,  #  v7.154: 添加 V7 支持
        }

        for role_id in agent_results.keys():
            if isinstance(role_id, str):
                #  v7.154: 支持多种格式
                # 格式1: "2-1" (短格式)
                # 格式2: "V2_设计总监_2-1" (完整格式)

                if role_id.startswith("V2_") or "2-" in role_id:
                    distribution["V2_设计总监"] += 1
                elif role_id.startswith("V3_") or "3-" in role_id:
                    distribution["V3_领域专家"] += 1
                elif role_id.startswith("V4_") or "4-" in role_id:
                    distribution["V4_研究专家"] += 1
                elif role_id.startswith("V5_") or "5-" in role_id:
                    distribution["V5_创新专家"] += 1
                elif role_id.startswith("V6_") or "6-" in role_id:
                    distribution["V6_实施专家"] += 1
                elif role_id.startswith("V7_") or "7-" in role_id:
                    distribution["V7_情感专家"] += 1

        # 只返回有值的分布
        return {k: v for k, v in distribution.items() if v > 0}


    def _estimate_report_pages(self, report: Dict[str, Any]) -> int:
        """估算报告页数"""
        # 基于内容量估算页数
        total_content = 0

        # 计算各部分内容量
        # sections 现在是 List[ReportSectionWithId]，不是字典
        sections = report.get("sections", [])
        for section in sections:
            content = section.get("content", "") if isinstance(section, dict) else ""
            total_content += len(str(content))

        # 添加其他部分
        total_content += len(str(report.get("executive_summary", {})))
        total_content += len(str(report.get("comprehensive_analysis", {})))
        total_content += len(str(report.get("conclusions", {})))

        # 估算页数（假设每页约2000字符）
        estimated_pages = max(10, total_content // 2000)

        return min(estimated_pages, 50)  # 限制在10-50页之间


    def _extract_review_feedback(
        self,
        review_result: Dict[str, Any],
        review_history: List[Dict[str, Any]],
        improvement_suggestions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        提取审核反馈数据

        Args:
            review_result: 当前审核结果
            review_history: 审核历史记录
            improvement_suggestions: 改进建议列表

        Returns:
            格式化的审核反馈数据
        """

        red_team_challenges = []
        blue_team_validations = []
        judge_rulings = []
        client_decisions = []

        # 从审核历史中提取数据（支持多轮审核）
        for round_data in review_history:
            round_num = round_data.get("round", 1)

            # 提取红队质疑点
            red_review = round_data.get("red_team_review", {})
            if isinstance(red_review, dict):
                improvements = red_review.get("improvements", [])
                for imp in improvements:
                    red_team_challenges.append(
                        {
                            "issue_id": imp.get("issue_id", f"R{round_num}-{len(red_team_challenges)+1}"),
                            "reviewer": f"红队（第{round_num}轮）",
                            "issue_type": "风险",
                            "description": imp.get("issue", ""),
                            "response": imp.get("suggested_action", "待处理"),
                            "status": "已修复"
                            if imp.get("issue_id") in [s.get("issue_id") for s in improvement_suggestions]
                            else "待处理",
                            "priority": imp.get("priority", "medium"),
                        }
                    )

            # 提取蓝队验证结果
            blue_review = round_data.get("blue_team_review", {})
            if isinstance(blue_review, dict):
                #  蓝队有两种数据：keep_as_is（优势）和 enhancements（优化建议）
                keep_as_is = blue_review.get("keep_as_is", [])
                for item in keep_as_is:
                    blue_team_validations.append(
                        {
                            "issue_id": item.get("red_issue_id", f"B{round_num}-{len(blue_team_validations)+1}"),
                            "reviewer": f"蓝队（第{round_num}轮）",
                            "issue_type": "验证",
                            "description": item.get("defense", ""),
                            "response": item.get("evidence", "已验证"),
                            "status": "已验证",
                            "priority": "medium",
                        }
                    )

                enhancements = blue_review.get("enhancements", [])
                for enh in enhancements:
                    blue_team_validations.append(
                        {
                            "issue_id": enh.get("enhancement_id", f"B{round_num}-{len(blue_team_validations)+1}"),
                            "reviewer": f"蓝队（第{round_num}轮）",
                            "issue_type": "优化",
                            "description": enh.get("enhancement", ""),
                            "response": enh.get("value_add", "已采纳"),
                            "status": "已采纳",
                            "priority": enh.get("priority", "medium"),
                        }
                    )

            # 提取评委裁决
            judge_review = round_data.get("judge_review", {})
            if isinstance(judge_review, dict):
                prioritized = judge_review.get("prioritized_improvements", [])
                for item in prioritized:
                    #  正确的字段映射：task -> description, rationale -> response
                    judge_rulings.append(
                        {
                            "issue_id": item.get("issue_id", f"J{round_num}-{len(judge_rulings)+1}"),
                            "reviewer": f"评委（第{round_num}轮）",
                            "issue_type": "建议",
                            "description": item.get("task", ""),  #  从 task 字段提取
                            "response": item.get("rationale", ""),  #  从 rationale 字段提取
                            "status": "已修复" if item.get("priority", 999) <= 2 else "待定",  #  priority 是数字
                            "priority": "high" if item.get("priority", 999) <= 2 else "medium",
                        }
                    )

            # 提取甲方决策
            client_review = round_data.get("client_review", {})
            if isinstance(client_review, dict):
                accepted = client_review.get("accepted_improvements", [])
                for acc in accepted:
                    client_decisions.append(
                        {
                            "issue_id": acc.get("issue_id", f"C{round_num}-{len(client_decisions)+1}"),
                            "reviewer": f"甲方（第{round_num}轮）",
                            "issue_type": "决策",
                            "description": acc.get("issue", ""),
                            "response": acc.get("implementation_plan", ""),
                            "status": "已采纳",
                            "priority": acc.get("priority", "high"),
                        }
                    )

        # 生成迭代总结
        total_issues = len(red_team_challenges)
        resolved_issues = len([x for x in red_team_challenges if x["status"] == "已修复"])
        iteration_summary = f"""
## 审核迭代过程总结

**总审核轮次**: {len(review_history)}轮
**红队发现问题数**: {total_issues}个
**蓝队验证优化点**: {len(blue_team_validations)}个
**评委裁决项目**: {len(judge_rulings)}个
**甲方最终决策**: {len(client_decisions)}个
**问题解决率**: {resolved_issues}/{total_issues} ({resolved_issues/max(1, total_issues)*100:.1f}%)

### 改进效果
通过多轮审核，项目质量显著提升：
- 风险识别与应对：红队发现的{total_issues}个潜在风险中，{resolved_issues}个已完成修复
- 价值增强：蓝队提出的{len(blue_team_validations)}个优化建议已全部采纳
- 专业裁决：评委团队提供{len(judge_rulings)}个专业建议，确保技术方案可行性
- 最终决策：甲方审核通过{len(client_decisions)}个关键改进措施

### 关键改进亮点
{self._format_key_improvements(improvement_suggestions[:3])}
"""

        return {
            "red_team_challenges": red_team_challenges,
            "blue_team_validations": blue_team_validations,
            "judge_rulings": judge_rulings,
            "client_decisions": client_decisions,
            "iteration_summary": iteration_summary.strip(),
        }


    def _extract_questionnaire_data(
        self,
        calibration_questionnaire: Dict[str, Any],
        questionnaire_responses: Dict[str, Any],
        questionnaire_summary: Dict[str, Any] | None = None,
    ) -> Dict[str, Any] | None:
        """
        提取问卷回答数据

        Args:
            calibration_questionnaire: 校准问卷
            questionnaire_responses: 用户回答

        Returns:
            格式化的问卷数据，如果所有问题都未回答则返回 None

         修复: 过滤掉未回答的问题，避免前端显示"未回答"
         v7.5 修复: 增加对 entries 中 answer 字段的支持（前端提交格式）
        """
        from datetime import datetime

        summary_entries = []
        if questionnaire_summary and questionnaire_summary.get("entries"):
            summary_entries = questionnaire_summary.get("entries", [])
        elif questionnaire_responses.get("entries"):
            summary_entries = questionnaire_responses.get("entries", [])

        responses = []

        if summary_entries:
            logger.debug(f" [问卷提取] 从 entries 提取，共 {len(summary_entries)} 项")
            for idx, entry in enumerate(summary_entries, 1):
                #  v7.5 修复: 同时检查 value 和 answer 字段（前端提交格式兼容）
                answer_value = entry.get("value") or entry.get("answer")
                #  修复: 跳过未回答的问题
                if answer_value is None or answer_value == "" or answer_value == []:
                    continue

                answer_str = self._stringify_answer(answer_value)
                #  修复: 再次检查格式化后的答案
                if answer_str == "未回答" or answer_str == "":
                    continue

                responses.append(
                    {
                        "question_id": entry.get("id") or entry.get("question_id", f"Q{idx}"),
                        "question": entry.get("question", ""),
                        "answer": answer_str,
                        "context": entry.get("context", ""),
                    }
                )
        else:
            questions = calibration_questionnaire.get("questions", [])
            answers = questionnaire_responses.get("answers", {})
            logger.debug(f" [问卷提取] 从 questions/answers 提取，{len(questions)} 问题，{len(answers)} 答案")

            for idx, q in enumerate(questions, 1):
                question_id = q.get("id", f"Q{idx}")
                raw_answer = answers.get(question_id) or answers.get(f"q{idx}")

                #  修复: 跳过未回答的问题
                if raw_answer is None or raw_answer == "" or raw_answer == []:
                    continue

                answer_str = self._stringify_answer(raw_answer)
                #  修复: 再次检查格式化后的答案
                if answer_str == "未回答" or answer_str == "":
                    continue

                responses.append(
                    {
                        "question_id": question_id,
                        "question": q.get("question", ""),
                        "answer": answer_str,
                        "context": q.get("context", ""),
                    }
                )

        #  修复: 如果所有问题都未回答，返回 None（前端会隐藏整个问卷区块）
        if not responses:
            logger.info(" 所有问卷问题都未回答，返回 None（前端将隐藏问卷区块）")
            return None

        timestamp = (
            (questionnaire_summary or {}).get("submitted_at")
            or questionnaire_responses.get("submitted_at")
            or questionnaire_responses.get("timestamp")
            or datetime.now().isoformat()
        )

        notes = (questionnaire_summary or {}).get("notes") or questionnaire_responses.get("notes", "")

        # 生成洞察分析
        analysis_insights = self._analyze_questionnaire_insights(responses)

        logger.info(f" 提取到 {len(responses)} 个有效问卷回答")

        return {"responses": responses, "timestamp": timestamp, "notes": notes, "analysis_insights": analysis_insights}

    @staticmethod

    def _stringify_answer(value: Any) -> str:
        """将问卷答案格式化为易读字符串"""
        if value is None:
            return "未回答"

        if isinstance(value, list | tuple | set):
            cleaned = [str(item).strip() for item in value if str(item).strip()]
            return "、".join(cleaned) if cleaned else "未回答"

        if isinstance(value, dict):
            try:
                serialized = json.dumps(value, ensure_ascii=False)
            except (TypeError, ValueError):
                serialized = str(value)
            return serialized.strip() or "未回答"

        text = str(value).strip()
        return text or "未回答"


    def _extract_visualization_data(
        self, review_history: List[Dict[str, Any]], review_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        提取可视化数据

        Args:
            review_history: 审核历史记录
            review_result: 最终审核结果

        Returns:
            格式化的可视化数据
        """
        from datetime import datetime

        rounds = []
        for round_data in review_history:
            round_num = round_data.get("round", 1)

            # 提取各方评分
            red_review = round_data.get("red_team_review", {})
            blue_review = round_data.get("blue_team_review", {})
            judge_review = round_data.get("judge_review", {})

            red_score = red_review.get("score", 0) if isinstance(red_review, dict) else 0
            blue_score = blue_review.get("score", 0) if isinstance(blue_review, dict) else 0
            judge_score = judge_review.get("score", 0) if isinstance(judge_review, dict) else 0

            issues_found = len(red_review.get("improvements", [])) if isinstance(red_review, dict) else 0
            issues_resolved = len(blue_review.get("enhancements", [])) if isinstance(blue_review, dict) else 0

            rounds.append(
                {
                    "round_number": round_num,
                    "red_score": red_score,
                    "blue_score": blue_score,
                    "judge_score": judge_score,
                    "issues_found": issues_found,
                    "issues_resolved": issues_resolved,
                    "timestamp": round_data.get("timestamp", datetime.now().isoformat()),
                }
            )

        # 计算改进率
        if rounds:
            first_round_score = rounds[0]["red_score"]
            last_round_score = rounds[-1]["judge_score"]
            improvement_rate = (last_round_score - first_round_score) / max(1, first_round_score)
        else:
            improvement_rate = 0.0

        # 获取最终决策
        client_review = review_result.get("client_review", {})
        final_decision = "通过"
        if isinstance(client_review, dict):
            decision = client_review.get("final_decision", "approved")
            if decision == "approved":
                final_decision = "通过"
            elif decision == "conditional_approval":
                final_decision = "有条件通过"
            else:
                final_decision = "拒绝"

        return {
            "rounds": rounds,
            "final_decision": final_decision,
            "total_rounds": len(rounds),
            "improvement_rate": round(improvement_rate, 2),
        }


    def _format_key_improvements(self, improvements: List[Dict[str, Any]]) -> str:
        """格式化关键改进点"""
        if not improvements:
            return "无需改进，分析质量已达标。"

        formatted = []
        for idx, imp in enumerate(improvements, 1):
            formatted.append(
                f"{idx}. **{imp.get('issue_id', 'N/A')}**: {imp.get('issue', '未知问题')} "
                f"（优先级: {imp.get('priority', 'medium')}）"
            )

        return "\n".join(formatted)


    def _analyze_questionnaire_insights(self, responses: List[Dict[str, Any]]) -> str:
        """从问卷回答中提取关键洞察"""
        if not responses:
            return "无有效问卷数据。"

        insights = ["## 用户需求关键洞察", "", f"基于{len(responses)}个问题的深入访谈，我们提取了以下关键洞察：", ""]

        # 简单分析：提取非空回答的数量
        answered = [r for r in responses if r.get("answer") and r["answer"] != "未回答"]
        insights.append(f"- **回答完整度**: {len(answered)}/{len(responses)} ({len(answered)/len(responses)*100:.1f}%)")

        # 如果有回答，提取前3个关键回答
        if answered:
            insights.append("- **关键回答**:")
            for r in answered[:3]:
                insights.append(f"  - {r.get('question', '未知问题')[:50]}...")
                insights.append(f"    > {r.get('answer', '未知回答')[:100]}...")

        return "\n".join(insights)


    def _extract_generated_images_by_expert(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        """
         v7.108: 从 agent_results[role_id]['concept_images'] 提取并转换为前端期望格式

        前端期望格式:
        {
            "2-1": {  # role_id作为key
                "expert_name": "V2 设计总监",
                "images": [
                    {
                        "id": "2-1_1_143022_abc",
                        "image_url": "/generated_images/session_id/...",  # 注意：后端用url，前端用image_url
                        "prompt": "...",
                        "aspect_ratio": "16:9",
                        ...
                    }
                ]
            }
        }
        """
        generated_images_by_expert = {}
        agent_results = state.get("agent_results", {})

        for role_id, result in agent_results.items():
            if not result:
                continue

            # 跳过需求分析师和项目总监（他们不生成概念图）
            if role_id in ["requirements_analyst", "project_director"]:
                continue

            # 从专家结果中提取concept_images
            concept_images = result.get("concept_images", [])
            if not concept_images:
                continue

            # 获取专家名称
            expert_name = result.get("expert_name", role_id)

            # 转换为前端格式：将 url 字段映射为 image_url
            converted_images = []
            for img_data in concept_images:
                converted_img = dict(img_data)  # 复制原数据

                # 字段映射：url -> image_url (前端期望)
                if "url" in converted_img:
                    converted_img["image_url"] = converted_img.pop("url")

                # 确保id字段存在（使用deliverable_id作为备选）
                if "id" not in converted_img and "deliverable_id" in converted_img:
                    converted_img["id"] = converted_img["deliverable_id"]

                converted_images.append(converted_img)

            # 添加到结果字典
            generated_images_by_expert[role_id] = {"expert_name": expert_name, "images": converted_images}

        return generated_images_by_expert

    # =========================================================================
    #  v7.0: 多交付物核心答案提取方法
    # =========================================================================

