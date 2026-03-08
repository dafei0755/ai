"""
分析路由模块 (MT-1 提取自 api/server.py)

Routes:
  POST /api/analysis/start
  POST /api/analysis/start-with-files
  POST /api/analysis/{session_id}/visual-reference/describe
  GET  /api/analysis/status/{session_id}
  POST /api/analysis/resume
  POST /api/analysis/followup
  GET  /api/analysis/result/{session_id}
  GET  /api/analysis/report/{session_id}
  GET  /api/analysis/report/{session_id}/download-pdf
  GET  /api/analysis/report/{session_id}/download-all-experts-pdf
"""
from __future__ import annotations

import json
import os
import time
import uuid
from collections import OrderedDict, defaultdict
from datetime import datetime
from typing import Any, Dict, List

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from langgraph.types import Command
from loguru import logger
from pydantic import BaseModel, Field

from intelligent_project_analyzer.agents.followup_agent import FollowupAgent
from intelligent_project_analyzer.api._server_proxy import server_proxy as _server
from intelligent_project_analyzer.services.file_processor import (
    build_combined_input,
    file_processor,
)
from intelligent_project_analyzer.services.geoip_service import get_geoip_service

from .deps import DEV_MODE, sessions_cache
from .helpers import (
    _derive_section_identity,
    _enrich_sections_with_agent_results,
    _format_agent_payload,
    _sanitize_structured_data,
)
from .models import (
    AnalysisRequest,
    AnalysisResult,
    AnalysisStatus,
    ChallengeDetectionResponse,
    ChallengeItemResponse,
    ComprehensiveAnalysisResponse,
    ConclusionsResponse,
    DeliberationProcessResponse,
    ExecutiveSummaryResponse,
    QuestionnaireResponseData,
    QuestionnaireResponseItem,
    RecommendationsSectionResponse,
    ReportResponse,
    ReportSectionResponse,
    RequirementsAnalysisResponse,
    ResumeRequest,
    ReviewFeedbackItemResponse,
    ReviewFeedbackResponse,
    ReviewRoundDataResponse,
    ReviewVisualizationResponse,
    SessionResponse,
    StructuredReportResponse,
)
from .pdf_generator import (
    generate_all_experts_pdf_fast,
    generate_report_pdf,
)
from .workflow_runner import run_workflow_async


router = APIRouter(tags=["analysis"])


@router.get("/api/analysis/result/{session_id}", response_model=AnalysisResult)
async def get_analysis_result(session_id: str):
    """
    获取分析结果

    获取已完成分析的完整结果
    """
    #  使用 Redis 获取会话
    sm = await get_session_manager()
    session = await sm.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    if session["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"分析尚未完成，当前状态: {session['status']}")

    # 兼容：不同版本的会话结构字段名可能不同
    results = session.get("results")
    agent_results = session.get("agent_results")
    final_report = session.get("final_report")
    final_result = session.get("final_result")

    return AnalysisResult(
        session_id=session_id,
        status=session["status"],
        results=results if results is not None else agent_results,
        final_report=final_report if final_report is not None else final_result,
        final_result=final_result,
        agent_results=agent_results,
    )


def _normalize_image_urls(generated_images_by_expert: Dict[str, Any] | None) -> Dict[str, Any] | None:
    """
     v7.123: 规范化图片URL字段，确保兼容性

    目的: 修复概念图显示黑色方块问题
    - 旧格式使用 "url" 字段
    - 新格式使用 "image_url" 字段
    - Base64格式直接可用

    确保所有图片数据包含 image_url 字段
    """
    if not generated_images_by_expert:
        return generated_images_by_expert

    logger.debug(" [v7.123] 规范化图片URL字段...")

    for expert_name, expert_data in generated_images_by_expert.items():
        if not isinstance(expert_data, dict):
            continue

        images = expert_data.get("images", [])
        if not isinstance(images, list):
            continue

        for img in images:
            if not isinstance(img, dict):
                continue

            # 如果是Base64 Data URL，保留
            if img.get("image_url", "").startswith("data:"):
                logger.debug(f"   {expert_name}: Base64格式，无需处理")
                continue

            # 如果有url但没有image_url，复制url到image_url
            if "url" in img and "image_url" not in img:
                img["image_url"] = img["url"]
                logger.debug(f"   {expert_name}: 添加image_url字段 (from url)")

            # 如果两者都不存在，标记错误
            if "image_url" not in img and "url" not in img:
                logger.error(f"   {expert_name}: 图片数据缺少URL - {img.get('id', 'unknown')}")
                img["image_url"] = ""  # 设置空值避免前端崩溃

    logger.debug(" [v7.123] 图片URL字段规范化完成")
    return generated_images_by_expert


@router.get("/api/analysis/report/{session_id}", response_model=ReportResponse)
async def get_analysis_report(session_id: str):
    """
    获取分析报告（专门为前端设计的端点）

    返回格式化的报告内容，适配前端 AnalysisReport 类型
    """
    #  使用 Redis 获取会话
    sm = await get_session_manager()
    session = await sm.get(session_id)

    #  v7.144: 如果 Redis 中没有会话，尝试从归档中获取
    if not session:
        logger.info(f" [v7.144] Redis 中未找到会话 {session_id}，尝试查询归档...")
        if _server.archive_manager:
            try:
                session = await _server.archive_manager.get_archived_session(session_id)
                if session:
                    logger.info(f" [v7.144] 从归档中找到会话 {session_id}")
            except Exception as e:
                logger.error(f" [v7.144] 查询归档失败: {e}")

    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    if session["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"分析尚未完成，当前状态: {session['status']}")

    # 获取报告文本路径
    pdf_path = session.get("pdf_path")
    report_text = ""

    #  v7.144: 修复 PDF 文件读取逻辑 - 读取同名的 .md 或 .txt 文件，而非 PDF 二进制文件
    if pdf_path and os.path.exists(pdf_path):
        try:
            # 尝试读取同名的 .md 文件
            txt_path = pdf_path.replace(".pdf", ".md")
            if not os.path.exists(txt_path):
                # 回退到 .txt 文件
                txt_path = pdf_path.replace(".pdf", ".txt")

            if os.path.exists(txt_path):
                with open(txt_path, encoding="utf-8") as f:
                    report_text = f.read()
                logger.info(f" [v7.144] 成功读取报告文本文件: {txt_path}")
            else:
                logger.warning(f"️ [v7.144] 未找到报告文本文件: {txt_path}")
                report_text = "报告文件读取失败，请查看结构化数据"
        except Exception as e:
            logger.warning(f"️ 无法读取报告文本文件: {e}")
            #  v7.52.5: 降级方案 - 不使用json.dumps，让FastAPI自动序列化
            # report_text 仅用于简短提示，实际数据在 structured_report 中
            report_text = "报告文件读取失败，请查看结构化数据"
    else:
        #  v7.52.5: 没有文件路径时，返回简短提示
        # structured_report 字段会包含完整数据，不需要json.dumps
        report_text = "请查看结构化报告内容"

    #  解析结构化报告数据
    structured_report = None
    final_report = session.get("final_report", {})

    if isinstance(final_report, dict) and final_report:
        try:
            #  Phase 1.4+ P4 & v7.0: 解析 core_answer（支持新旧两种格式）
            core_answer_data = None
            ca_raw = final_report.get("core_answer")
            if ca_raw and isinstance(ca_raw, dict):
                # 检测是否是 v7.0 格式（有 deliverable_answers 字段）
                if "deliverable_answers" in ca_raw:
                    #  v7.0 格式：直接传递整个结构
                    core_answer_data = ca_raw
                    deliverable_count = len(ca_raw.get("deliverable_answers", []))
                    logger.info(f" [v7.0] 解析到多交付物核心答案: {deliverable_count} 个交付物")
                else:
                    # 旧格式：转换为字典（保持向后兼容）
                    core_answer_data = {
                        "question": ca_raw.get("question", ""),
                        "answer": ca_raw.get("answer", ""),
                        "deliverables": ca_raw.get("deliverables", []),
                        "timeline": ca_raw.get("timeline", ""),
                        "budget_range": ca_raw.get("budget_range", ""),
                        # v7.0 向后兼容字段（为空）
                        "deliverable_answers": [],
                        "expert_support_chain": [],
                    }
                    logger.info(f" 解析到核心答案（旧格式）: {ca_raw.get('answer', '')[:50]}...")

            # 解析 executive_summary
            exec_summary_data = final_report.get("executive_summary", {})
            exec_summary = ExecutiveSummaryResponse(
                project_overview=exec_summary_data.get("project_overview", ""),
                key_findings=exec_summary_data.get("key_findings", []),
                key_recommendations=exec_summary_data.get("key_recommendations", []),
                success_factors=exec_summary_data.get("success_factors", []),
            )

            # 解析 sections（支持数组和字典两种格式）
            sections_data = final_report.get("sections", {})
            sections = []

            #  修复：sections可能是dict（key=section_id）或list格式
            if isinstance(sections_data, dict):
                # 字典格式：{"requirements_analysis": {...}, "design_research": {...}}
                for section_id, section_content in sections_data.items():
                    if isinstance(section_content, dict):
                        #  v7.52.5: content可能是dict或string
                        # 如果是字典，提取主要文本内容，不使用json.dumps
                        content_val = section_content.get("content", "")
                        if isinstance(content_val, dict):
                            # 尝试提取主要文本字段，而不是JSON字符串
                            if "text" in content_val:
                                content_val = content_val["text"]
                            elif "content" in content_val:
                                content_val = content_val["content"]
                            else:
                                # 如果实在需要展示结构化内容，用简短描述
                                content_val = f"[结构化内容: {len(content_val)} 个字段]"

                        raw_confidence = section_content.get("confidence", 0.0)
                        try:
                            confidence_value = float(raw_confidence)
                        except (TypeError, ValueError):
                            confidence_value = 0.0

                        sections.append(
                            ReportSectionResponse(
                                section_id=section_id,
                                title=section_content.get("title", section_id),
                                content=str(content_val) if content_val else "",
                                confidence=confidence_value,
                            )
                        )
            elif isinstance(sections_data, list):
                # 数组格式：[{section_id, title, content, confidence}, ...]
                for s in sections_data:
                    if isinstance(s, dict):
                        #  v7.52.5: content可能是dict或string
                        # 如果是字典，提取主要文本内容，不使用json.dumps
                        content_val = s.get("content", "")
                        if isinstance(content_val, dict):
                            # 尝试提取主要文本字段，而不是JSON字符串
                            if "text" in content_val:
                                content_val = content_val["text"]
                            elif "content" in content_val:
                                content_val = content_val["content"]
                            else:
                                # 如果实在需要展示结构化内容，用简短描述
                                content_val = f"[结构化内容: {len(content_val)} 个字段]"

                        raw_confidence = s.get("confidence", 0.0)
                        try:
                            confidence_value = float(raw_confidence)
                        except (TypeError, ValueError):
                            confidence_value = 0.0

                        sections.append(
                            ReportSectionResponse(
                                section_id=s.get("section_id", ""),
                                title=s.get("title", ""),
                                content=str(content_val) if content_val else "",
                                confidence=confidence_value,
                            )
                        )

            # 使用智能体原始输出补全章节
            sections = _enrich_sections_with_agent_results(sections, session)

            # 解析 comprehensive_analysis（兼容字段名差异）
            comp_data = final_report.get("comprehensive_analysis", {})
            comp_analysis = ComprehensiveAnalysisResponse(
                cross_domain_insights=comp_data.get("cross_domain_insights", []),
                integrated_recommendations=comp_data.get("integrated_recommendations")
                or comp_data.get("integration_recommendations", []),
                risk_assessment=comp_data.get("risk_assessment", []),
                implementation_roadmap=comp_data.get("implementation_roadmap", []),
            )

            # 解析 conclusions（兼容 summary 和 project_analysis_summary）
            concl_data = final_report.get("conclusions", {})
            conclusions = ConclusionsResponse(
                project_analysis_summary=concl_data.get("project_analysis_summary") or concl_data.get("summary", ""),
                next_steps=concl_data.get("next_steps", []),
                success_metrics=concl_data.get("success_metrics", []),
            )

            # 解析 review_feedback
            review_feedback = None
            rf_data = final_report.get("review_feedback")
            if rf_data and isinstance(rf_data, dict):

                def parse_feedback_items(items_data):
                    items = []
                    for item in items_data or []:
                        if isinstance(item, dict):
                            items.append(
                                ReviewFeedbackItemResponse(
                                    issue_id=item.get("issue_id", ""),
                                    reviewer=item.get("reviewer", ""),
                                    issue_type=item.get("issue_type", ""),
                                    description=item.get("description", ""),
                                    response=item.get("response", ""),
                                    status=item.get("status", ""),
                                    priority=str(item.get("priority", "medium")),
                                )
                            )
                    return items

                review_feedback = ReviewFeedbackResponse(
                    red_team_challenges=parse_feedback_items(rf_data.get("red_team_challenges")),
                    blue_team_validations=parse_feedback_items(rf_data.get("blue_team_validations")),
                    judge_rulings=parse_feedback_items(rf_data.get("judge_rulings")),
                    client_decisions=parse_feedback_items(rf_data.get("client_decisions")),
                    iteration_summary=rf_data.get("iteration_summary", ""),
                )

            # 解析 review_visualization
            review_viz = None
            rv_data = final_report.get("review_visualization")
            if rv_data and isinstance(rv_data, dict):
                rounds = []
                for rd in rv_data.get("rounds", []):
                    if isinstance(rd, dict):
                        rounds.append(
                            ReviewRoundDataResponse(
                                round_number=rd.get("round_number", 0),
                                red_score=rd.get("red_score", 0),
                                blue_score=rd.get("blue_score", 0),
                                judge_score=rd.get("judge_score", 0),
                                issues_found=rd.get("issues_found", 0),
                                issues_resolved=rd.get("issues_resolved", 0),
                                timestamp=rd.get("timestamp", ""),
                            )
                        )
                review_viz = ReviewVisualizationResponse(
                    rounds=rounds,
                    final_decision=rv_data.get("final_decision", ""),
                    total_rounds=rv_data.get("total_rounds", 0),
                    improvement_rate=float(rv_data.get("improvement_rate", 0.0)),
                )

            #  解析 challenge_detection（从 session state 中获取）
            challenge_detection = None
            cd_data = session.get("challenge_detection")
            if cd_data and isinstance(cd_data, dict):
                challenges_list = []
                raw_challenges = cd_data.get("challenges", [])
                must_fix_count = 0
                should_fix_count = 0

                for ch in raw_challenges:
                    if isinstance(ch, dict):
                        severity = ch.get("severity", "should-fix")
                        if severity == "must-fix":
                            must_fix_count += 1
                        else:
                            should_fix_count += 1

                        challenges_list.append(
                            ChallengeItemResponse(
                                expert_id=ch.get("expert_id", ""),
                                expert_name=ch.get("expert_name", ch.get("expert_id", "")),
                                challenged_item=ch.get("challenged_item", ""),
                                challenge_type=ch.get("challenge_type", ""),
                                severity=severity,
                                rationale=ch.get("rationale", ""),
                                proposed_alternative=ch.get("proposed_alternative", ""),
                                design_impact=ch.get("design_impact", ""),
                                decision=ch.get("decision", ""),
                            )
                        )

                # 获取处理摘要
                handling_data = session.get("challenge_handling", {})
                handling_summary = handling_data.get("summary", "") if isinstance(handling_data, dict) else ""

                challenge_detection = ChallengeDetectionResponse(
                    has_challenges=cd_data.get("has_challenges", False),
                    total_count=len(challenges_list),
                    must_fix_count=must_fix_count,
                    should_fix_count=should_fix_count,
                    challenges=challenges_list,
                    handling_summary=handling_summary,
                )

                if challenges_list:
                    logger.info(f" 挑战检测: {must_fix_count} must-fix, {should_fix_count} should-fix")

            #  修复：从 session.agent_results 提取 expert_reports（如果 final_report 里没有）
            expert_reports_data = final_report.get("expert_reports", {})
            if not expert_reports_data:
                # 从 agent_results 提取专家报告
                agent_results = session.get("agent_results", {})
                active_agents = session.get("active_agents", [])
                expert_reports_data = {}

                for role_id in active_agents:
                    # 跳过需求分析师和项目总监
                    if role_id in ["requirements_analyst", "project_director"]:
                        continue
                    # 只提取 V2-V6 专家的报告
                    if not any(role_id.startswith(prefix) for prefix in ["V2_", "V3_", "V4_", "V5_", "V6_"]):
                        continue

                    agent_result = agent_results.get(role_id, {})
                    if agent_result:
                        structured_raw = agent_result.get("structured_data", {})
                        structured_data, validation_warnings = _sanitize_structured_data(structured_raw)
                        content = agent_result.get("content", "")

                        if structured_data and content:
                            payload = OrderedDict()
                            payload["structured_data"] = structured_data
                            payload["narrative_summary"] = content
                            if validation_warnings:
                                payload["validation_warnings"] = validation_warnings
                            expert_reports_data[role_id] = json.dumps(payload, ensure_ascii=False, indent=2)
                        elif structured_data:
                            if validation_warnings:
                                payload = OrderedDict()
                                payload["structured_data"] = structured_data
                                payload["validation_warnings"] = validation_warnings
                                expert_reports_data[role_id] = json.dumps(payload, ensure_ascii=False, indent=2)
                            else:
                                expert_reports_data[role_id] = json.dumps(structured_data, ensure_ascii=False, indent=2)
                        elif content:
                            if validation_warnings:
                                payload = OrderedDict()
                                payload["narrative_summary"] = content
                                payload["validation_warnings"] = validation_warnings
                                expert_reports_data[role_id] = json.dumps(payload, ensure_ascii=False, indent=2)
                            else:
                                expert_reports_data[role_id] = content
                        elif validation_warnings:
                            payload = OrderedDict()
                            payload["validation_warnings"] = validation_warnings
                            expert_reports_data[role_id] = json.dumps(payload, ensure_ascii=False, indent=2)

                if expert_reports_data:
                    logger.info(f" 从agent_results提取了 {len(expert_reports_data)} 个专家报告")

            #  修复：如果sections仍为空，从agent_results动态填充
            if not sections:
                agent_results = session.get("agent_results") or {}
                if agent_results:
                    active_agents = session.get("active_agents") or list(agent_results.keys())

                    section_contributions: Dict[str, OrderedDict] = {}
                    section_titles: Dict[str, str] = {}
                    section_confidences: Dict[str, List[float]] = defaultdict(list)
                    section_sequence: List[str] = []

                    for role_id in active_agents:
                        if role_id in ["requirements_analyst", "project_director"]:
                            continue

                        agent_result = agent_results.get(role_id) or {}
                        payload = _format_agent_payload(agent_result)
                        if not payload:
                            continue

                        section_id, section_title = _derive_section_identity(role_id, agent_result)
                        source_name = agent_result.get("display_name") or agent_result.get("role_name") or role_id

                        section_contributions.setdefault(section_id, OrderedDict())
                        section_contributions[section_id][source_name] = payload

                        if section_title:
                            section_titles.setdefault(section_id, section_title)

                        if section_id not in section_sequence:
                            section_sequence.append(section_id)

                        raw_confidence = agent_result.get("confidence")
                        try:
                            if raw_confidence is not None:
                                section_confidences[section_id].append(float(raw_confidence))
                        except (TypeError, ValueError):
                            logger.debug(f"️ 无法解析 {role_id} 的置信度: {raw_confidence}")

                    for section_id in section_sequence:
                        payload = section_contributions.get(section_id)
                        if not payload:
                            continue

                        confidence_values = section_confidences.get(section_id, [])
                        if confidence_values:
                            confidence = max(confidence_values)
                        else:
                            confidence = 0.8

                        section_content = json.dumps(payload, ensure_ascii=False, indent=2)
                        sections.append(
                            ReportSectionResponse(
                                section_id=section_id,
                                title=section_titles.get(section_id, section_id),
                                content=section_content,
                                confidence=confidence,
                            )
                        )

                    if sections:
                        logger.info(f" 从agent_results动态填充了 {len(sections)} 个章节")

            #  Phase 1.4+ P3: 解析问卷回答数据
            questionnaire_data = None
            qr_raw = final_report.get("questionnaire_responses")
            if qr_raw and isinstance(qr_raw, dict):
                responses_list = []
                for resp_item in qr_raw.get("responses", []):
                    if isinstance(resp_item, dict):
                        responses_list.append(
                            QuestionnaireResponseItem(
                                question_id=resp_item.get("question_id", ""),
                                question=resp_item.get("question", ""),
                                answer=resp_item.get("answer", ""),
                                context=resp_item.get("context", ""),
                            )
                        )

                if responses_list:
                    questionnaire_data = QuestionnaireResponseData(
                        responses=responses_list,
                        timestamp=qr_raw.get("timestamp", ""),
                        analysis_insights=qr_raw.get("analysis_insights", ""),
                    )
                    logger.info(f" 解析到 {len(responses_list)} 条问卷回答")

            #  Phase 1.4+ v4.1: 解析洞察区块 - 已废弃（改用需求分析师的原始输出）
            # insights_raw = final_report.get("insights")
            # if insights_raw:
            #     # 支持 Pydantic 对象和 dict 两种格式
            #     if hasattr(insights_raw, 'model_dump'):
            #         insights_dict = insights_raw.model_dump()
            #     elif isinstance(insights_raw, dict):
            #         insights_dict = insights_raw
            #     else:
            #         insights_dict = {}
            #
            #     if insights_dict:
            #         insights_data = InsightsSectionResponse(
            #             key_insights=insights_dict.get("key_insights", []),
            #             cross_domain_connections=insights_dict.get("cross_domain_connections", []),
            #             user_needs_interpretation=insights_dict.get("user_needs_interpretation", "")
            #         )
            #         logger.info(f" 解析到洞察区块: {len(insights_data.key_insights)} 条关键洞察")

            #  Phase 1.4+ v4.1: 解析推敲过程
            deliberation_data = None
            deliberation_raw = final_report.get("deliberation_process")
            if deliberation_raw:
                if hasattr(deliberation_raw, "model_dump"):
                    #  Phase 0优化: 排除None和默认值
                    deliberation_dict = deliberation_raw.model_dump(exclude_none=True, exclude_defaults=True)
                elif isinstance(deliberation_raw, dict):
                    deliberation_dict = deliberation_raw
                else:
                    deliberation_dict = {}

                if deliberation_dict:
                    deliberation_data = DeliberationProcessResponse(
                        inquiry_architecture=deliberation_dict.get("inquiry_architecture", ""),
                        reasoning=deliberation_dict.get("reasoning", ""),
                        role_selection=deliberation_dict.get("role_selection", []),
                        strategic_approach=deliberation_dict.get("strategic_approach", ""),
                    )
                    logger.info(f" 解析到推敲过程: 架构={deliberation_data.inquiry_architecture}")

            #  Phase 1.4+ v4.1: 解析建议区块
            recommendations_data = None
            recommendations_raw = final_report.get("recommendations")
            if recommendations_raw:
                if hasattr(recommendations_raw, "model_dump"):
                    #  Phase 0优化: 排除None和默认值
                    recommendations_dict = recommendations_raw.model_dump(exclude_none=True, exclude_defaults=True)
                elif isinstance(recommendations_raw, dict):
                    recommendations_dict = recommendations_raw
                else:
                    recommendations_dict = {}

                if recommendations_dict:
                    recommendations_data = RecommendationsSectionResponse(
                        immediate_actions=recommendations_dict.get("immediate_actions", []),
                        short_term_priorities=recommendations_dict.get("short_term_priorities", []),
                        long_term_strategy=recommendations_dict.get("long_term_strategy", []),
                        risk_mitigation=recommendations_dict.get("risk_mitigation", []),
                    )
                    logger.info(f" 解析到建议区块: {len(recommendations_data.immediate_actions)} 条立即行动")

            #  解析需求分析结果（需求分析师原始输出）
            #  修复：应从 final_report 读取，而不是从 session.structured_requirements
            requirements_analysis_data = None
            requirements_analysis_raw = final_report.get("requirements_analysis")

            # 尝试从 final_report 顶层获取
            if requirements_analysis_raw and isinstance(requirements_analysis_raw, dict):
                requirements_analysis_data = RequirementsAnalysisResponse(
                    project_overview=requirements_analysis_raw.get("project_overview", ""),
                    core_objectives=requirements_analysis_raw.get("core_objectives", []),
                    project_tasks=requirements_analysis_raw.get("project_tasks", []),
                    narrative_characters=requirements_analysis_raw.get("narrative_characters", []),
                    physical_contexts=requirements_analysis_raw.get("physical_contexts", []),
                    constraints_opportunities=requirements_analysis_raw.get("constraints_opportunities", {}),
                    #  传递用户修改标识
                    has_user_modifications=session.get("has_user_modifications", False),
                    user_modification_summary=session.get("user_modification_summary"),
                )
                logger.info(f" 解析到需求分析结果（从 final_report）: {len(requirements_analysis_data.core_objectives)} 个核心目标")
            else:
                #  备用方案1：从 sections 数组中查找（针对已有会话）
                sections_data = final_report.get("sections", [])
                logger.debug(
                    f" [DEBUG] sections_data type: {type(sections_data)}, length: {len(sections_data) if isinstance(sections_data, list) else 'N/A'}"
                )

                if isinstance(sections_data, list):
                    for section in sections_data:
                        if isinstance(section, dict):
                            section_id = section.get("section_id", "")
                            logger.debug(f" [DEBUG] Checking section: {section_id}")

                            if section_id == "requirements_analysis":
                                content_str = section.get("content", "")
                                logger.info(
                                    f" Found requirements_analysis in sections, content length: {len(content_str)}"
                                )

                                if content_str:
                                    try:
                                        # 解析 JSON 字符串
                                        req_data = (
                                            json.loads(content_str) if isinstance(content_str, str) else content_str
                                        )

                                        #  修复：正确映射 requirements_analyst 的实际输出字段
                                        # requirements_analyst 输出的是完整的结构化数据，包含多个字段
                                        logger.debug(f" [FIELD MAPPING] req_data keys: {list(req_data.keys())}")
                                        logger.debug(
                                            f" [FIELD MAPPING] project_task: '{req_data.get('project_task', '')}' (len={len(req_data.get('project_task', ''))})"
                                        )
                                        logger.debug(
                                            f" [FIELD MAPPING] character_narrative: (len={len(req_data.get('character_narrative', ''))})"
                                        )
                                        logger.debug(
                                            f" [FIELD MAPPING] physical_context: (len={len(req_data.get('physical_context', ''))})"
                                        )

                                        #  v7.131: 安全处理 physical_context（可能是字符串或字典）
                                        physical_context_raw = req_data.get("physical_context", "")
                                        if isinstance(physical_context_raw, dict):
                                            context_parts = []
                                            if physical_context_raw.get("location"):
                                                context_parts.append(f"位置: {physical_context_raw['location']}")
                                            if physical_context_raw.get("space_type"):
                                                context_parts.append(f"空间类型: {physical_context_raw['space_type']}")
                                            if physical_context_raw.get("floor_height"):
                                                context_parts.append(f"层高: {physical_context_raw['floor_height']}")
                                            if physical_context_raw.get("area"):
                                                context_parts.append(f"面积: {physical_context_raw['area']}")
                                            physical_context_list = ["; ".join(context_parts)] if context_parts else []
                                        elif isinstance(physical_context_raw, str) and physical_context_raw:
                                            physical_context_list = [physical_context_raw]
                                        else:
                                            physical_context_list = []

                                        requirements_analysis_data = RequirementsAnalysisResponse(
                                            project_overview=req_data.get("project_overview")
                                            or req_data.get("project_task", ""),
                                            core_objectives=req_data.get("core_objectives", []),
                                            project_tasks=[req_data.get("project_task", "")]
                                            if req_data.get("project_task")
                                            else [],
                                            narrative_characters=[req_data.get("character_narrative", "")]
                                            if req_data.get("character_narrative")
                                            else [],
                                            physical_contexts=physical_context_list,
                                            constraints_opportunities={
                                                "resource_constraints": req_data.get("resource_constraints", ""),
                                                "regulatory_requirements": req_data.get("regulatory_requirements", ""),
                                                "space_constraints": req_data.get("space_constraints", ""),
                                                "core_tension": req_data.get("core_tension", ""),
                                                "design_challenge": req_data.get("design_challenge", ""),
                                            },
                                            #  传递用户修改标识
                                            has_user_modifications=session.get("has_user_modifications", False),
                                            user_modification_summary=session.get("user_modification_summary"),
                                        )
                                        logger.info(
                                            f" 解析到需求分析结果（从 sections）: {len(requirements_analysis_data.core_objectives)} 个核心目标"
                                        )
                                        logger.debug(
                                            f" [FIELD MAPPING] project_tasks after mapping: {len(requirements_analysis_data.project_tasks)} items"
                                        )
                                        logger.debug(
                                            f" [FIELD MAPPING] narrative_characters after mapping: {len(requirements_analysis_data.narrative_characters)} items"
                                        )
                                        logger.debug(
                                            f" [FIELD MAPPING] physical_contexts after mapping: {len(requirements_analysis_data.physical_contexts)} items"
                                        )
                                        break
                                    except (json.JSONDecodeError, TypeError) as e:
                                        logger.warning(f"️ 解析 sections 中的 requirements_analysis 失败: {e}")
                else:
                    logger.debug(f" [DEBUG] sections_data is not a list, type: {type(sections_data)}")

                #  备用方案2：如果以上都失败，尝试从 session.structured_requirements 读取（向后兼容）
                if not requirements_analysis_data:
                    structured_req = session.get("structured_requirements")
                    if structured_req and isinstance(structured_req, dict):
                        requirements_analysis_data = RequirementsAnalysisResponse(
                            project_overview=structured_req.get("project_overview", ""),
                            core_objectives=structured_req.get("core_objectives", []),
                            project_tasks=structured_req.get("project_tasks", []),
                            narrative_characters=structured_req.get("narrative_characters", []),
                            physical_contexts=structured_req.get("physical_contexts", []),
                            constraints_opportunities=structured_req.get("constraints_opportunities", {}),
                            #  传递用户修改标识
                            has_user_modifications=session.get("has_user_modifications", False),
                            user_modification_summary=session.get("user_modification_summary"),
                        )
                        logger.info(
                            f" 解析到需求分析结果（从 session.structured_requirements 备用）: {len(requirements_analysis_data.core_objectives)} 个核心目标"
                        )

            structured_report = StructuredReportResponse(
                inquiry_architecture=final_report.get("inquiry_architecture", ""),
                core_answer=core_answer_data,  #  添加核心答案
                insights=None,  #  已废弃：不再使用LLM综合洞察
                requirements_analysis=requirements_analysis_data,  #  添加需求分析结果（需求分析师原始输出）
                deliberation_process=deliberation_data,  #  Phase 1.4+ v4.1: 添加推敲过程
                recommendations=recommendations_data,  #  Phase 1.4+ v4.1: 添加建议
                executive_summary=exec_summary,
                sections=sections,
                comprehensive_analysis=comp_analysis,
                conclusions=conclusions,
                expert_reports=expert_reports_data,
                review_feedback=review_feedback,
                questionnaire_responses=questionnaire_data,  #  添加问卷数据
                review_visualization=review_viz,
                challenge_detection=challenge_detection,
                #  v7.4: 添加执行元数据汇总
                execution_metadata=final_report.get("metadata"),
                #  v3.0.26: 添加思维导图内容结构
                mindmap_content=final_report.get("mindmap_content"),
                # 深度思考模式概念图（集中生成）
                generated_images=final_report.get("generated_images"),
                image_prompts=final_report.get("image_prompts"),
                image_top_constraints=final_report.get("image_top_constraints"),
                #  v7.39: 添加专家概念图（深度思考pro模式）
                #  v7.123: 确保图片数据包含正确的URL字段
                generated_images_by_expert=_normalize_image_urls(final_report.get("generated_images_by_expert")),
                #  v7.154: 添加雷达图维度数据
                radar_dimensions=session.get("selected_dimensions") or session.get("selected_radar_dimensions"),
                radar_dimension_values=session.get("radar_dimension_values"),
            )

            logger.info(f" 成功解析结构化报告，包含 {len(sections)} 个章节")

        except Exception as e:
            logger.warning(f"️ 解析结构化报告失败: {e}，将返回 None")
            structured_report = None

    # 获取用户原始输入
    user_input = session.get("user_input", "")

    return ReportResponse(
        session_id=session_id,
        report_text=report_text,
        report_pdf_path=pdf_path,
        created_at=session.get("created_at", datetime.now().isoformat()),
        user_input=user_input,
        structured_report=structured_report,
    )


@router.get("/api/analysis/report/{session_id}/download-pdf")
async def download_report_pdf(session_id: str):
    """
    下载分析报告 PDF（v7.0 重构版）

    生成可编辑的 PDF 文件（文本可选中复制）

    包含 5 个核心章节：
    1. 用户原始需求
    2. 校准问卷回顾（过滤"未回答"）
    3. 需求洞察
    4. 核心答案（支持 v7.0 多交付物格式）
    5. 执行元数据

    不包含专家报告（专家报告有独立下载入口）
    """
    session = await _server.session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    if session["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"分析尚未完成，当前状态: {session['status']}")

    # 获取报告数据
    final_report = session.get("final_report", {})
    user_input = session.get("user_input", "")

    if not isinstance(final_report, dict) or not final_report:
        raise HTTPException(status_code=400, detail="报告数据不可用")

    try:
        pdf_bytes = generate_report_pdf(final_report, user_input)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=project_report_{session_id}.pdf"},
        )
    except Exception as e:
        logger.error(f" 生成 PDF 失败: {e}")
        raise HTTPException(status_code=500, detail=f"PDF 生成失败: {str(e)}")


@router.get("/api/analysis/report/{session_id}/download-all-experts-pdf")
async def download_all_experts_pdf(session_id: str):
    """
    下载所有专家报告的合并 PDF

    v7.1.3 升级：
    - 切换为 FPDF 原生生成引擎 (generate_all_experts_pdf_fast)
    - 速度提升 10x (10s -> <1s)
    - 移除 Playwright 依赖，更稳定
    """
    #  缓存检查 - 缓存命中直接返回
    cache_key = f"all_experts_pdf_fast_{session_id}"
    if cache_key in _server.pdf_cache:
        logger.info(f" PDF 缓存命中: {session_id}")
        pdf_bytes = _server.pdf_cache[cache_key]
        from urllib.parse import quote

        safe_filename = quote(f"all_expert_reports_{session_id}.pdf", safe="")
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_filename}"},
        )

    session = await _server.session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    if session["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"分析尚未完成，当前状态: {session['status']}")

    # 获取专家报告
    final_report = session.get("final_report", {})
    expert_reports = final_report.get("expert_reports", {}) if isinstance(final_report, dict) else {}

    if not expert_reports:
        raise HTTPException(status_code=400, detail="无专家报告数据")

    user_input = session.get("user_input", "")

    try:
        logger.info(f" 快速生成 PDF (FPDF): {session_id}")
        # 使用新的快速生成函数
        pdf_bytes = generate_all_experts_pdf_fast(expert_reports, user_input)

        #  缓存 PDF
        _server.pdf_cache[cache_key] = pdf_bytes
        logger.info(f" PDF 已缓存: {session_id} ({len(pdf_bytes)} bytes)")

        # 使用 URL 编码处理中文文件名
        from urllib.parse import quote

        safe_filename = quote(f"all_expert_reports_{session_id}.pdf", safe="")

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_filename}"},
        )
    except Exception as e:
        logger.error(f" 生成所有专家报告 PDF 失败: {e}")
        raise HTTPException(status_code=500, detail=f"PDF 生成失败: {str(e)}")


# =============================================================================
# MT-4: WebSocket 事件回放端点
# =============================================================================


class _EventReplayResponse(BaseModel):
    """GET /api/analysis/events/{session_id} 响应体。"""

    session_id: str
    after_seq: int
    events: list  # List[WSEvent]
    count: int


@router.get(
    "/api/analysis/events/{session_id}",
    summary="[MT-4] 获取 WebSocket 事件回放列表",
    description=("返回 session 内 seq > after_seq 的全部 WebSocket 事件。" "断线重连后由前端调用，用于补偿遗漏消息。"),
    tags=["MT-4: WebSocket 事件补偿"],
)
async def get_ws_events(
    session_id: str,
    after_seq: int = 0,
):
    """
    返回 WebSocket 事件回放列表。

    Parameters
    ----------
    session_id:
        会话 ID
    after_seq:
        客户端已收到的最后一个事件序号；返回 seq > after_seq 的全部事件。
        首次调用传 ``0`` 获取全部历史（有 TTL，最多 1h）。
    """
    from intelligent_project_analyzer.services.event_store import get_event_store

    events = await get_event_store().get_after(session_id, after_seq)
    return {
        "session_id": session_id,
        "after_seq": after_seq,
        "events": events,
        "count": len(events),
    }
