"""
结果聚合器

负责整合所有智能体的分析结果，生成最终报告结构
"""

import json
import time
from datetime import datetime
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore
from loguru import logger

from ..agents.base import LLMAgent
from ..core.prompt_manager import PromptManager
from ..core.state import AgentType, ProjectAnalysisState
from ..core.types import AnalysisResult, ReportSection
from ..utils.jtbd_parser import transform_jtbd_to_natural_language

# ============================================================================
# 从模型模块导入所有 Pydantic 数据类（保持向后兼容）
# ============================================================================
from ._aggregator_format_mixin import AggregatorFormatMixin
from ._aggregator_extraction_mixin import AggregatorExtractionMixin
from ._aggregator_deliverable_mixin import AggregatorDeliverableMixin
from ._result_models import (  # noqa: F401
    ComprehensiveAnalysis,
    Conclusions,
    CoreAnswer,
    CoreAnswerV7,
    DeliberationProcess,
    DeliverableAnswer,
    ExecutiveSummary,
    ExpertSupportChain,
    FinalReport,
    InsightsSection,
    QuestionnaireResponse,
    QuestionnaireResponses,
    RecommendationItem,
    RecommendationsSection,
    ReportSectionWithId,
    ReviewFeedback,
    ReviewFeedbackItem,
    ReviewRoundData,
    ReviewVisualization,
    V2DesignDirectorContent,
    V3NarrativeExpertContent,
    V4DesignResearcherContent,
    V5ScenarioExpertContent,
    V6ChiefEngineerContent,
    V7EmotionalInsightContent,
)


class ResultAggregatorAgent(AggregatorFormatMixin, AggregatorExtractionMixin, AggregatorDeliverableMixin, LLMAgent):
    """结果聚合器智能体"""

    def __init__(self, llm_model, config: Dict[str, Any] | None = None):
        super().__init__(
            agent_type=AgentType.RESULT_AGGREGATOR,
            name="结果聚合器",
            description="整合所有分析结果，生成结构化的最终报告",
            llm_model=llm_model,
            config=config,
        )

        # 初始化提示词管理器
        self.prompt_manager = PromptManager()

    def validate_input(self, state: ProjectAnalysisState) -> bool:
        """验证输入是否有效"""
        agent_results = state.get("agent_results") or {}  #  修复：确保不为 None
        return len(agent_results) > 0

    def prepare_messages(self, state: ProjectAnalysisState) -> List:
        """
        准备LLM消息 - 重写父类方法以使用正确的消息格式

         性能优化: 移除few-shot示例，直接使用structured output
         减少token消耗约60%，加速LLM响应
        """
        messages = []

        #  使用 SystemMessage 传递系统提示词
        system_prompt = self.get_system_prompt()
        messages.append(SystemMessage(content=system_prompt))

        #  性能优化: 直接使用structured output，无需few-shot示例
        task_description = self.get_task_description(state)
        messages.append(HumanMessage(content=task_description))

        return messages

    def get_system_prompt(self) -> str:
        """
        获取系统提示词 - 从外部配置加载

         修复: 简化提示词，聚焦核心任务
         优化: 明确 sections 字段的填充规则
        """
        # 尝试从外部配置加载
        prompt = self.prompt_manager.get_prompt("result_aggregator")

        # 如果配置不存在，抛出错误（不再使用硬编码 fallback）
        if not prompt:
            raise ValueError(
                " 未找到提示词配置: result_aggregator\n"
                "请确保配置文件存在: config/prompts/result_aggregator.yaml\n"
                "系统无法使用硬编码提示词，请检查配置文件。"
            )

        return prompt

    def get_task_description(self, state: ProjectAnalysisState) -> str:
        """
        获取具体任务描述 - v3.0版本（包含审核反馈、问卷回答、可视化数据）

         新增: review_feedback（审核反馈章节）
         新增: questionnaire_responses（用户访谈记录）
         新增: review_visualization（多轮审核可视化）
        """
        agent_results = state.get("agent_results") or {}
        structured_requirements = state.get("structured_requirements") or {}
        strategic_analysis = state.get("strategic_analysis") or {}  #  修复：确保不为 None

        #  获取审核结果（原有逻辑）
        final_ruling = state.get("final_ruling") or ""
        improvement_suggestions = state.get("improvement_suggestions") or []

        #  获取完整审核数据（新增）
        review_result = state.get("review_result") or {}  #  修复：确保不为 None
        review_history = state.get("review_history") or []  #  修复：确保不为 None

        #  获取问卷数据（LT-3: calibration_answers 已删除，统一从 questionnaire_responses 读取）
        calibration_questionnaire = state.get("calibration_questionnaire") or {}
        questionnaire_responses = state.get("questionnaire_responses") or {}
        questionnaire_summary = state.get("questionnaire_summary") or {}

        # 提取项目总监的战略分析信息
        query_type = strategic_analysis.get("query_type", "深度优先探询")
        query_type_reasoning = strategic_analysis.get("query_type_reasoning", "")

        # ========== 1. 构建审核反馈数据 ==========
        review_feedback_data = None
        if review_result or review_history:
            review_feedback_data = self._extract_review_feedback(review_result, review_history, improvement_suggestions)

        # ========== 2. 构建问卷回答数据 ==========
        questionnaire_data = None
        if questionnaire_summary or questionnaire_responses or calibration_questionnaire:
            questionnaire_data = self._extract_questionnaire_data(
                calibration_questionnaire, questionnaire_responses, questionnaire_summary
            )

        # ========== 3. 构建可视化数据 ==========
        visualization_data = None
        if review_history:
            visualization_data = self._extract_visualization_data(review_history, review_result)

        # 构建审核结果部分（原有逻辑，保留用于提示词）
        review_section = ""
        if final_ruling:
            review_section = f"""

##  审核系统的最终裁定

{final_ruling}

### 改进建议摘要
"""
            if improvement_suggestions:
                for idx, suggestion in enumerate(improvement_suggestions[:5], 1):
                    priority = suggestion.get("priority", "should_fix")
                    deadline = suggestion.get("deadline", "before_launch")
                    review_section += f"{idx}. [{priority}] {suggestion.get('issue_id', 'N/A')} - {deadline}\n"
            else:
                review_section += "无需改进，分析质量已达标。\n"

        # 构建新增数据部分
        additional_data_section = ""
        if review_feedback_data:
            additional_data_section += f"""

##  审核反馈数据（用于填充review_feedback字段）

{json.dumps(review_feedback_data, ensure_ascii=False, indent=2)}
"""

        if questionnaire_data:
            additional_data_section += f"""

##  问卷回答数据（用于填充questionnaire_responses字段）

{json.dumps(questionnaire_data, ensure_ascii=False, indent=2)}
"""

        if visualization_data:
            additional_data_section += f"""

##  可视化数据（用于填充review_visualization字段）

{json.dumps(visualization_data, ensure_ascii=False, indent=2)}
"""

        return f"""请整合以下分析结果，生成综合项目分析报告。

## 项目总监的作战计划

**探询架构类型：** {query_type}
**判定理由：** {query_type_reasoning}

## 项目基本信息

**项目概述：** {structured_requirements.get("project_overview", "暂无")}
**核心目标：** {json.dumps(structured_requirements.get("core_objectives", []), ensure_ascii=False)}

## V2-V6 专家的分析成果

{self._format_agent_results(agent_results)}
{review_section}
{additional_data_section}

## 任务要求

1. **识别探询架构**：使用上述探询架构类型（{query_type}）
2. **填充sections字段**：为每个专家创建对应的section条目
   - 使用专家标注的章节名称作为键（如 "design_research"）
   - 将专家的完整分析结果放入content字段
   - 保留专家的置信度
3. **整合审核结果**：如果存在最终裁定，请在综合分析中体现改进建议
4. **生成综合分析**：整合所有专家的洞察
5. **填充新增字段**（如果数据存在）：
   - review_feedback: 使用上面提供的审核反馈数据
   - questionnaire_responses: 使用上面提供的问卷回答数据
   - review_visualization: 使用上面提供的可视化数据
6. **输出格式**：纯JSON，不要添加markdown标记

️ 重要：必须为所有专家创建section条目，不要遗漏任何一个！

请立即生成JSON格式的报告。"""

    def execute(
        self, state: ProjectAnalysisState, config: RunnableConfig, store: BaseStore | None = None
    ) -> AnalysisResult:
        """执行结果聚合 - 使用结构化输出"""
        start_time = time.time()

        try:
            logger.info(f"Starting result aggregation for session {state.get('session_id')}")

            #  Phase 1.4: 发送初始进度更新
            self._update_progress(state, "准备整合专家分析结果", 0.0)

            # 验证输入
            if not self.validate_input(state):
                raise ValueError("Invalid input: no agent results found")

            # 准备消息
            self._update_progress(state, "构建聚合提示词", 0.1)
            messages = self.prepare_messages(state)

            #  性能优化: 精简JSON格式提醒（structured output已包含格式要求）
            json_format_reminder = SystemMessage(content="OUTPUT: Use structured JSON schema provided")
            messages.insert(1, json_format_reminder)

            # 使用 with_structured_output 强制 LLM 返回符合 Pydantic 模型的结构
            # ️ 注意: 由于 content 字段是 Dict[str, Any]（灵活字典），无法使用 strict mode
            # OpenAI strict mode 要求所有对象都设置 additionalProperties: false
            # 但 Dict[str, Any] 需要 additionalProperties: true 来允许任意键
            # 因此使用 function_calling 方法而不是 json_schema + strict
            logger.info("Using structured output with Pydantic model (function_calling method)")

            #  Phase 1.4: 进度更新
            self._update_progress(state, "配置结构化输出模型", 0.2)

            structured_llm = self.llm_model.with_structured_output(
                FinalReport,
                method="function_calling",  # 使用 function_calling 以支持灵活的 Dict[str, Any]
                include_raw=True,  # 官方推荐：处理复杂schema时避免抛出异常
            )
            logger.info("Successfully configured function_calling method")

            # 调用 LLM 并获取结构化输出
            #  修复: 添加更详细的错误处理，捕获超时和网络错误
            #  修复: 显式传递 max_tokens 和 request_timeout 参数
            #  新增: 添加重试逻辑以应对不稳定的API响应
            # 这些参数在 ChatOpenAI 初始化时设置，但为了确保它们被使用，我们在这里再次传递
            import os

            max_tokens = int(os.getenv("MAX_TOKENS", "32000"))
            request_timeout = int(os.getenv("LLM_TIMEOUT", "600"))
            max_retries = int(os.getenv("MAX_RETRIES", "3"))
            retry_delay = int(os.getenv("RETRY_DELAY", "5"))

            result = None
            last_error = None

            #  Phase 1.4: 进度更新
            agent_count = len(state.get("agent_results", {}))
            self._update_progress(state, f"调用LLM整合{agent_count}位专家的分析结果（预计60-90秒）", 0.3)

            #  重试循环
            for attempt in range(max_retries):
                try:
                    #  Phase 1.4: 进度更新（重试提示）
                    if attempt > 0:
                        self._update_progress(state, f"LLM调用重试中（第{attempt + 1}次尝试）", 0.3 + (attempt * 0.05))

                    logger.info(
                        f"Invoking LLM (attempt {attempt + 1}/{max_retries}) with max_tokens={max_tokens}, request_timeout={request_timeout}"
                    )

                    # 记录开始时间
                    start_time = time.time()

                    result = structured_llm.invoke(messages, max_tokens=max_tokens, request_timeout=request_timeout)

                    # 记录结束时间
                    elapsed_time = time.time() - start_time
                    logger.info(f"LLM invocation completed in {elapsed_time:.2f}s")

                    #  Phase 1.4: 进度更新
                    self._update_progress(state, "LLM响应完成，正在解析结果", 0.6)

                    # 成功，跳出重试循环
                    break

                except json.JSONDecodeError as e:
                    # JSON解析错误 - 通常是响应被截断或超时
                    last_error = e
                    logger.error(f"Attempt {attempt + 1}/{max_retries} - JSON parsing failed: {e}")
                    logger.error("This usually indicates a timeout or incomplete response from the API")

                    if attempt < max_retries - 1:
                        logger.info(f"Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    else:
                        logger.error(f"All {max_retries} attempts failed")
                        logger.info("Attempting to use fallback parsing method")
                        raise ValueError(
                            f"LLM response was incomplete or truncated after {max_retries} attempts. This may be due to timeout or network issues. Original error: {e}"
                        )

                except Exception as e:
                    # 其他错误（网络超时、API错误等）
                    last_error = e
                    logger.error(f"Attempt {attempt + 1}/{max_retries} - LLM invocation failed: {e}")

                    if attempt < max_retries - 1:
                        logger.info(f"Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    else:
                        logger.error(f"All {max_retries} attempts failed")
                        raise

            # 如果所有重试都失败了
            if result is None:
                raise ValueError(f"LLM invocation failed after {max_retries} attempts. Last error: {last_error}")

            # 检查是否有解析错误
            if result.get("parsing_error"):
                # 解析失败，使用备用方案
                logger.warning(f"Structured output parsing failed: {result['parsing_error']}")
                logger.info("Falling back to manual parsing")

                #  Phase 1.4: 进度更新
                self._update_progress(state, "结构化解析失败，使用备用解析方案", 0.65)

                raw_message = result["raw"]
                final_report = self._parse_final_report(raw_message.content, state)

                #  P0修复: 备用解析路径也必须提取真实数据
                #  v7.1.4: 确保无条件覆盖，避免与主路径重复
                logger.info("Fallback path: extracting real expert_reports from state")
                if "expert_reports" not in final_report or not final_report["expert_reports"]:
                    final_report["expert_reports"] = self._extract_expert_reports(state)
                final_report["challenge_resolutions"] = self._extract_challenge_resolutions(state)

                #  v7.5修复: fallback 路径也必须提取问卷数据
                # 原因：问卷数据提取逻辑原本只在成功解析路径，导致 fallback 时前端显示空问卷
                self._update_progress(state, "[Fallback] 提取校准问卷回答", 0.7)
                calibration_questionnaire = state.get("calibration_questionnaire") or {}
                questionnaire_responses_state = state.get("questionnaire_responses") or {}
                questionnaire_summary = state.get("questionnaire_summary") or {}

                if calibration_questionnaire or questionnaire_responses_state or questionnaire_summary:
                    real_questionnaire_data = self._extract_questionnaire_data(
                        calibration_questionnaire, questionnaire_responses_state, questionnaire_summary
                    )
                    if real_questionnaire_data and real_questionnaire_data.get("responses"):
                        final_report["questionnaire_responses"] = real_questionnaire_data
                        logger.info(
                            f" [Fallback] 已提取 questionnaire_responses: {len(real_questionnaire_data['responses'])} 条回答"
                        )
                    else:
                        logger.debug("ℹ️ [Fallback] 无问卷数据可提取")

                #  v7.5修复: fallback 路径也必须提取需求分析结果
                # 原因：需求分析师的输出需要正确传递到前端
                if "requirements_analysis" not in final_report or not final_report.get("requirements_analysis"):
                    structured_requirements = state.get("structured_requirements") or {}
                    if structured_requirements:
                        final_report["requirements_analysis"] = structured_requirements
                        logger.info(" [Fallback] 已提取 requirements_analysis")

                #  P2修复: 确保 raw_content 保存原始LLM响应
                final_report["raw_content"] = raw_message.content
                final_report["metadata"] = {
                    **final_report.get("metadata", {}),
                    "parsing_mode": "fallback",
                    "fallback_reason": str(result.get("parsing_error", "unknown")),
                }
            else:
                # 解析成功
                logger.info("Successfully received and parsed structured output from LLM")

                #  Phase 1.4: 进度更新
                self._update_progress(state, "结构化解析成功，正在验证数据完整性", 0.7)

                final_report_pydantic = result["parsed"]

                if final_report_pydantic is None:
                    logger.warning("Structured output parsing returned None, falling back to manual parsing")
                    self._update_progress(state, "解析结果为空，使用备用方案", 0.72)
                    raw_message = result.get("raw")
                    if raw_message:
                        final_report = self._parse_final_report(raw_message.content, state)
                        #  P0修复: 备用解析路径也必须提取真实数据
                        #  v7.1.4: 确保无条件覆盖，避免与主路径重复
                        logger.info("Fallback path (None parsed): extracting real expert_reports from state")
                        if "expert_reports" not in final_report or not final_report["expert_reports"]:
                            final_report["expert_reports"] = self._extract_expert_reports(state)
                        final_report["challenge_resolutions"] = self._extract_challenge_resolutions(state)

                        #  v7.5修复: fallback_none_parsed 路径也必须提取问卷和需求分析
                        self._update_progress(state, "[Fallback-None] 提取校准问卷回答", 0.74)
                        calibration_questionnaire = state.get("calibration_questionnaire") or {}
                        questionnaire_responses_state = state.get("questionnaire_responses") or {}
                        questionnaire_summary = state.get("questionnaire_summary") or {}

                        if calibration_questionnaire or questionnaire_responses_state or questionnaire_summary:
                            real_questionnaire_data = self._extract_questionnaire_data(
                                calibration_questionnaire, questionnaire_responses_state, questionnaire_summary
                            )
                            if real_questionnaire_data and real_questionnaire_data.get("responses"):
                                final_report["questionnaire_responses"] = real_questionnaire_data
                                logger.info(
                                    f" [Fallback-None] 已提取 questionnaire_responses: {len(real_questionnaire_data['responses'])} 条回答"
                                )

                        # 提取需求分析
                        if "requirements_analysis" not in final_report or not final_report.get("requirements_analysis"):
                            structured_requirements = state.get("structured_requirements") or {}
                            if structured_requirements:
                                final_report["requirements_analysis"] = structured_requirements
                                logger.info(" [Fallback-None] 已提取 requirements_analysis")

                        #  P2修复: 确保 raw_content 保存原始LLM响应
                        final_report["raw_content"] = raw_message.content
                        final_report["metadata"] = {
                            **final_report.get("metadata", {}),
                            "parsing_mode": "fallback_none_parsed",
                        }
                    else:
                        raise ValueError("LLM response parsed as None and no raw message available")
                else:
                    # 转换 Pydantic 模型为字典
                    #  Phase 0优化: 排除None和默认值以减少token消耗
                    final_report = final_report_pydantic.model_dump(exclude_none=True, exclude_defaults=True)

                #  新增: 检查 sections 是否为空，如果为空则手动填充
                if not final_report.get("sections") or len(final_report["sections"]) == 0:
                    logger.warning("LLM returned empty sections, manually populating from agent_results")
                    self._update_progress(state, "LLM未返回章节数据，正在手动填充", 0.75)
                    final_report["sections"] = self._manually_populate_sections(state)
                    logger.info(f"Manually populated {len(final_report['sections'])} sections")

                #  修复v4.0: 始终用真实数据覆盖 expert_reports
                # 原因：LLM 可能返回占位符文本如 "{...内容略...}"，必须用真实数据覆盖
                #  v7.1.4修复: 简化逻辑，无条件覆盖以避免重复
                logger.info("Overwriting expert_reports with actual expert content from state")
                self._update_progress(state, "提取专家原始报告", 0.8)
                real_expert_reports = self._extract_expert_reports(state)

                # 直接覆盖，无需检查占位符（避免重复赋值）
                final_report["expert_reports"] = real_expert_reports

                logger.info(f"Extracted {len(final_report['expert_reports'])} expert reports")

                #  修复：从 sections 中提取 requirements_analysis 并提升到顶层
                # 原因：requirements_analysis 被 _manually_populate_sections 放在了 sections 数组中
                # 但前端期望它在顶层（与 insights、deliberation_process 同级）
                sections_list = final_report.get("sections", [])
                if isinstance(sections_list, list):
                    for section in sections_list:
                        if isinstance(section, dict) and section.get("section_id") == "requirements_analysis":
                            # 提取 requirements_analysis 的 content（可能是JSON字符串）
                            content_str = section.get("content", "")
                            if content_str:
                                try:
                                    # 尝试解析为字典
                                    requirements_data = (
                                        json.loads(content_str) if isinstance(content_str, str) else content_str
                                    )
                                    final_report["requirements_analysis"] = requirements_data
                                    logger.info(" 已从 sections 提取 requirements_analysis 到顶层")
                                except json.JSONDecodeError:
                                    logger.warning(f"️ requirements_analysis 内容不是有效 JSON: {content_str[:100]}")
                            break

                #  v3.5.1: 添加挑战解决结果
                self._update_progress(state, "提取专家挑战解决结果", 0.85)
                final_report["challenge_resolutions"] = self._extract_challenge_resolutions(state)

                #  v4.1修复: 强制用真实问卷数据覆盖 questionnaire_responses
                # 原因：LLM 结构化输出可能返回 None（可选字段），导致前端显示"未回答"
                self._update_progress(state, "提取校准问卷回答", 0.87)
                calibration_questionnaire = state.get("calibration_questionnaire") or {}
                questionnaire_responses_state = state.get("questionnaire_responses") or {}
                questionnaire_summary = state.get("questionnaire_summary") or {}

                if calibration_questionnaire or questionnaire_responses_state or questionnaire_summary:
                    real_questionnaire_data = self._extract_questionnaire_data(
                        calibration_questionnaire, questionnaire_responses_state, questionnaire_summary
                    )
                    if real_questionnaire_data and real_questionnaire_data.get("responses"):
                        final_report["questionnaire_responses"] = real_questionnaire_data
                        logger.info(f" 已覆盖 questionnaire_responses: {len(real_questionnaire_data['responses'])} 条回答")
                    else:
                        logger.debug("ℹ️ 无问卷数据可覆盖")

                # 添加元数据
                self._update_progress(state, "生成报告元数据", 0.9)

                #  v7.4: 增强执行元数据，提升用户体验
                # 收集更多统计数据
                agent_results = state.get("agent_results", {})
                questionnaire_responses = final_report.get("questionnaire_responses", {})
                batches = state.get("batches", [])
                review_iterations = state.get("review_iterations", 0)

                # 计算问卷回答数量
                questionnaire_count = 0
                if questionnaire_responses:
                    responses = questionnaire_responses.get("responses", [])
                    questionnaire_count = len([r for r in responses if r.get("answer") and r.get("answer") != "未回答"])

                # 计算平均置信度
                confidence_values = []
                for _role_id, result in agent_results.items():
                    if isinstance(result, dict):
                        # 从任务导向专家输出中提取置信度
                        exec_meta = result.get("execution_metadata", {})
                        if exec_meta and isinstance(exec_meta, dict):
                            conf = exec_meta.get("confidence")
                            if conf is not None:
                                confidence_values.append(float(conf))

                avg_confidence = sum(confidence_values) / len(confidence_values) if confidence_values else None

                # 获取复杂度级别
                task_complexity = state.get("task_complexity", "complex")
                complexity_display = {"simple": "简单", "medium": "中等", "complex": "复杂"}.get(task_complexity, "复杂")

                # 计算分析耗时（如果有开始时间）
                analysis_duration = None
                created_at = state.get("created_at")
                if created_at:
                    try:
                        if isinstance(created_at, str):
                            analysis_start_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        else:
                            analysis_start_time = created_at
                        duration_seconds = (datetime.now() - analysis_start_time.replace(tzinfo=None)).total_seconds()
                        if duration_seconds < 60:
                            analysis_duration = f"{int(duration_seconds)}秒"
                        elif duration_seconds < 3600:
                            minutes = int(duration_seconds // 60)
                            seconds = int(duration_seconds % 60)
                            analysis_duration = f"{minutes}分{seconds}秒"
                        else:
                            hours = int(duration_seconds // 3600)
                            minutes = int((duration_seconds % 3600) // 60)
                            analysis_duration = f"{hours}时{minutes}分"
                    except Exception as e:
                        logger.debug(f"计算分析耗时失败: {e}")

                #  修复: 从 deliberation_process 中提取 inquiry_architecture
                inquiry_arch = "深度优先探询"  # 默认值
                deliberation = final_report.get("deliberation_process")
                if deliberation:
                    if isinstance(deliberation, dict):
                        inquiry_arch = deliberation.get("inquiry_architecture", inquiry_arch)
                    elif hasattr(deliberation, "inquiry_architecture"):
                        inquiry_arch = deliberation.inquiry_architecture or inquiry_arch
                # 也同步到顶层，方便其他地方使用
                final_report["inquiry_architecture"] = inquiry_arch

                final_report["metadata"] = {
                    "generated_at": datetime.now().isoformat(),
                    "session_id": state.get("session_id"),
                    "total_agents": len(agent_results),
                    "overall_confidence": self._calculate_overall_confidence(state),
                    "estimated_pages": self._estimate_report_pages(final_report),
                    "inquiry_architecture": inquiry_arch,
                    #  v7.4 新增字段
                    "total_batches": len(batches) if batches else 1,
                    "complexity_level": complexity_display,
                    "questionnaire_answered": questionnaire_count,
                    "review_rounds": review_iterations,
                    "confidence_average": avg_confidence,
                    "analysis_duration": analysis_duration,
                    # 专家分布统计
                    "expert_distribution": self._get_expert_distribution(agent_results),
                }

                # 保存原始 LLM 响应内容
                #  P2修复: 仅在未设置时才设置，避免覆盖备用路径的值
                if "raw_content" not in final_report or not final_report.get("raw_content"):
                    raw_msg = result.get("raw")
                    if raw_msg:
                        final_report["raw_content"] = raw_msg.content
                    else:
                        final_report["raw_content"] = str(final_report_pydantic)

            #  v7.0: 从责任者输出中提取交付物答案，覆盖 LLM 生成的 core_answer
            self._update_progress(state, "提取交付物责任者答案", 0.92)
            deliverable_metadata = state.get("deliverable_metadata") or {}

            if deliverable_metadata:
                logger.info(f" [v7.0] 检测到 {len(deliverable_metadata)} 个交付物元数据，开始提取责任者答案")
                extracted_core_answer = self._extract_deliverable_answers(state)

                # 覆盖 LLM 生成的 core_answer
                if extracted_core_answer.get("deliverable_answers"):
                    final_report["core_answer"] = extracted_core_answer
                    logger.info(
                        f" [v7.0] 已用责任者答案覆盖 core_answer: {len(extracted_core_answer['deliverable_answers'])} 个交付物"
                    )
                else:
                    logger.warning("️ [v7.0] 未提取到交付物答案，保留 LLM 生成的 core_answer")
            else:
                logger.info("ℹ️ [v7.0] 无交付物元数据，保留 LLM 生成的 core_answer")

            #  v7.108: 提取概念图数据并转换为前端格式
            self._update_progress(state, "提取概念图数据", 0.93)
            generated_images_by_expert = self._extract_generated_images_by_expert(state)
            if generated_images_by_expert:
                final_report["generated_images_by_expert"] = generated_images_by_expert
                total_images = sum(len(expert_data["images"]) for expert_data in generated_images_by_expert.values())
                logger.info(f" [v7.108] 已提取 {len(generated_images_by_expert)} 个专家的 {total_images} 张概念图")
            else:
                logger.debug("ℹ️ [v7.108] 无概念图数据可提取")

            #  v7.122: 统一处理搜索引用（去重、验证、聚合）
            self._update_progress(state, "处理搜索引用", 0.94)
            search_references = self._consolidate_search_references(state)
            if search_references:
                final_report["search_references"] = search_references
                logger.info(f" [v7.122] 已处理 {len(search_references)} 条搜索引用")
            else:
                logger.debug("ℹ️ [v7.122] 无搜索引用数据")

            # ── v8.0: 投射调度与多视角生成 ─────────────────────────────────
            self._update_progress(state, "启动多视角投射调度", 0.94)
            try:
                from ..services.projection_dispatcher import dispatch_projections_sync

                proj_result = dispatch_projections_sync(state=state, llm_model=self.llm_model)
                final_report["meta_axis_scores"] = proj_result.get("meta_axis_scores", {})
                final_report["active_projections"] = proj_result.get("active_projections", [])
                final_report["perspective_outputs"] = proj_result.get("perspective_outputs", {})
                final_report["projection_reports"] = {
                    k: v
                    for k, v in proj_result.get("perspective_outputs", {}).items()
                    if isinstance(v, dict) and v.get("status") == "completed"
                }
                logger.info(f"[投射调度] 生成 {len(final_report['projection_reports'])} 个视角报告")
            except Exception as _proj_err:
                logger.error(f"[投射调度] 失败，使用基础报告: {_proj_err}")

            # 创建分析结果
            self._update_progress(state, "构建最终分析结果", 0.95)
            result = self.create_analysis_result(
                content=str(final_report.get("executive_summary", {})),
                structured_data=final_report,
                confidence=self._calculate_overall_confidence(state),
                sources=["all_agents", "requirements_analysis", "comprehensive_analysis"],
            )

            end_time = time.time()
            self._track_execution_time(start_time, end_time)

            #  Phase 1.4: 最终进度更新
            self._update_progress(state, "终审聚合完成", 1.0)

            logger.info("Result aggregation completed successfully")
            return result

        except Exception as e:
            error = self.handle_error(e, "Result aggregation")
            raise error

