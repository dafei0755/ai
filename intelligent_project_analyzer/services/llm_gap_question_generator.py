"""
LLM Gap Question Generator
v7.105: LLM 驱动的任务信息完整性补充问题生成器

功能：
- 替代硬编码问题模板
- 根据用户输入和缺失维度动态生成针对性问题
- 紧密结合项目上下文
- 失败时自动回退到硬编码问题

依赖：
- gap_question_generator.yaml 配置文件
- TaskCompletenessAnalyzer 作为回退方案
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

#  v7.131: 导入LLM重试工具
from ..utils.llm_retry import LLMRetryConfig, ainvoke_llm_with_retry


class LLMGapQuestionGenerator:
    """基于 LLM 生成任务信息补充问题"""

    # 输出意向 → 追问需求描述映射（v7.210）
    # 结构：{projection_key: {project_type: description}}
    # project_type: premium_residential / rural / commercial / general
    PROJECTION_DESCRIPTIONS: Dict[str, Dict[str, str]] = {
        "design_professional": {
            "general": (
                "设计专业报告 → 需明确：设计策略方向、空间关系优先级、技术约束边界、"
                "交付深度（概念/方案/深化）"
            ),
        },
        "investor_operator": {
            "premium_residential": (
                "投资运营分析 → 需明确：自用为主还是计划出租/托管、"
                "是否委托品牌管理公司、预期年化回报率或租金收益预期"
            ),
            "rural": (
                "投资运营分析 → 需明确：运营主体（村集体/承包方/品牌方）、"
                "乡村旅游商业模式、目标客群定位、投资规模与回报预期"
            ),
            "commercial": (
                "投资运营分析 → 需明确：运营主体与品牌授权模式、"
                "租金收益模型与资产回报率、目标客群定位"
            ),
            "general": (
                "投资运营分析 → 需明确：运营主体与管理模式、"
                "商业目标与投资回报预期、目标客群定位"
            ),
        },
        "government_policy": {
            "rural": (
                "政策汇报方案 → 需明确：政策背景（乡村振兴/文旅政策）、"
                "审批路径、合规约束、社会效益指标"
            ),
            "general": (
                "政策汇报方案 → 需明确：相关政策背景与合规要求、"
                "审批路径、社会效益指标"
            ),
        },
        "construction_execution": {
            "rural": (
                "施工深化方案 → 需明确：施工条件（交通/基础设施）、"
                "在地材料来源与工匠资源可获得性、技术约束、工期要求"
            ),
            "general": (
                "施工深化方案 → 需明确：施工条件与现场限制、"
                "材料供应与技术约束、工期要求"
            ),
        },
        "aesthetic_critique": {
            "general": (
                "美学评论文本 → 需明确：文化叙事的核心立场（保护性/转化性/批判性）、"
                "精神性意图与美学参照系的取舍逻辑（仅引用用户原话中出现的参照对象）、叙事深度层级"
            ),
        },
    }

    def __init__(self):
        """初始化生成器，加载配置文件（v7.220: 项目类型委托 ProjectTypeDetector）"""
        self.config = self._load_config()
        self.system_prompt = self.config.get("system_prompt", "")
        self.user_template = self.config.get("user_prompt_template", "")
        self.generation_config = self.config.get("generation_config", {})
        self.last_generation_metadata: Dict[str, Any] = {
            "generation_source": "unknown",
            "error_code": None,
            "error_message": None,
        }
        # v7.220: 项目类型检测统一由 ProjectTypeDetector 负责，移除本地 yaml 关键词加载
        # v7.211: 从 output_projections.yaml 加载 gap_dimensions，替代硬编码 PROJECTION_DESCRIPTIONS
        self._dynamic_gap_dimensions: Dict[str, Dict[str, str]] = self._load_gap_dimensions_from_projections()

    def _classify_error_code(self, error: Exception) -> str:
        """区分认证失败与一般模型/运行时失败。"""
        msg = str(error).lower()
        if "401" in msg and (
            "authentication" in msg
            or "invalid_api_key" in msg
            or "incorrect api key" in msg
            or "user not found" in msg
            or "unauthorized" in msg
        ):
            return "LLM_AUTH_401"
        if "empty" in msg or "空问题" in msg or "空问题列表" in msg:
            return "LLM_EMPTY_RESULT"
        return "LLM_RUNTIME_ERROR"

    def _load_gap_dimensions_from_projections(self) -> Dict[str, Dict[str, str]]:
        """
        从 output_projections.yaml 加载每种投射类型的 gap_dimensions。
        返回: {projection_key: {space_type: description_str}}
        """
        projections_path = Path(__file__).parent.parent / "config" / "output_projections.yaml"
        result: Dict[str, Dict[str, str]] = {}
        try:
            with open(projections_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            for proj_key, proj_data in data.get("projections", {}).items():
                gap_dims = proj_data.get("gap_dimensions", {})
                if not isinstance(gap_dims, dict):
                    continue
                type_map: Dict[str, str] = {}
                for space_type, dims in gap_dims.items():
                    if isinstance(dims, list):
                        type_map[space_type] = "、".join(str(d) for d in dims)
                    elif isinstance(dims, str):
                        type_map[space_type] = dims
                if type_map:
                    result[proj_key] = type_map
            logger.info(f"[LLMGapQuestionGenerator] gap_dimensions 加载成功: {len(result)} 种投射")
        except Exception as e:
            logger.warning(f"[LLMGapQuestionGenerator] output_projections.yaml 加载失败，将使用 PROJECTION_DESCRIPTIONS fallback: {e}")
        return result

    def _load_config(self) -> Dict[str, Any]:
        """
        加载配置文件

        Returns:
            配置字典
        """
        config_path = Path(__file__).parent.parent / "config" / "prompts" / "gap_question_generator.yaml"
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                logger.info(f" [LLMGapQuestionGenerator] 配置文件加载成功: {config_path}")
                return config
        except Exception as e:
            logger.error(f" [LLMGapQuestionGenerator] 配置文件加载失败: {e}")
            return {}

    def _detect_project_type(self, user_input: str) -> str:
        """
        v7.220: 委托 PROJECT_TYPE_REGISTRY 单一权威来源（ProjectTypeDetector）检测项目类型。
        返回值为 project_type_detector.py 中注册的 type ID，如 personal_residential、rural_construction。
        """
        from intelligent_project_analyzer.services.project_type_detector import detect_project_type
        return detect_project_type(user_input)

    def _calculate_target_count(self, missing_dimensions: List[str]) -> int:
        """
        根据缺失维度数量计算目标问题数

        Args:
            missing_dimensions: 缺失维度列表

        Returns:
            目标问题数量
        """
        count = len(missing_dimensions)
        strategy = self.generation_config.get("question_count_strategy", {})
        by_missing = strategy.get("by_missing_dimensions", {})

        if count <= 2:
            min_q, max_q = by_missing.get("1-2", [3, 5])
        elif count <= 4:
            min_q, max_q = by_missing.get("3-4", [6, 8])
        else:
            min_q, max_q = by_missing.get("5+", [9, 10])

        # 返回中间值
        target = (min_q + max_q) // 2
        logger.info(f"[LLMGapQuestionGenerator] 缺失 {count} 个维度，目标生成 {target} 个问题")
        return target

    async def generate(
        self,
        user_input: str,
        confirmed_tasks: List[Dict[str, Any]],
        missing_dimensions: List[str],
        covered_dimensions: List[str],
        existing_info_summary: str,
        completeness_score: float,
        llm: Optional[Any] = None,
        # v7.200: 输出意向参数（向后兼容，默认 None）
        active_projections: Optional[List[str]] = None,
        detected_identity_modes: Optional[List[Dict]] = None,
        output_framework_signals: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """
        生成任务信息补充问题

        Args:
            user_input: 用户原始输入
            confirmed_tasks: Step 1 确认的任务列表
            missing_dimensions: 缺失维度列表
            covered_dimensions: 已覆盖维度列表
            existing_info_summary: 已有信息摘要
            completeness_score: 完整性评分 (0-1)
            llm: LLM 实例（可选）
            active_projections: 已确认的输出投射列表（v7.200 新增）
            detected_identity_modes: 检测到的身份模式（v7.200 新增）
            output_framework_signals: 输出框架信号（v7.200 新增）

        Returns:
            问题列表 [{"id": "", "question": "", "type": "", ...}]
        """
        try:
            self.last_generation_metadata = {
                "generation_source": "llm",
                "error_code": None,
                "error_message": None,
            }

            # 计算目标问题数量
            target_count = self._calculate_target_count(missing_dimensions)

            # v7.200: 按分组构建任务摘要，避免 [:5] 只覆盖同类任务
            task_summary = self._build_grouped_task_summary(confirmed_tasks)

            # v7.200: 检查意向驱动开关
            import os
            intent_driven = (
                self.generation_config.get("intent_driven_mode", True)
                and os.getenv("GAP_INTENT_DRIVEN_MODE", "true").lower() != "false"
            )
            intent_rerank = (
                self.generation_config.get("intent_rerank_enabled", True)
                and os.getenv("GAP_INTENT_RERANK_ENABLED", "true").lower() != "false"
            )

            # v7.200: 构建输出意向上下文
            output_intent_context = (
                self._build_output_intent_context(
                    active_projections, detected_identity_modes, output_framework_signals,
                    user_input=user_input,
                )
                if intent_driven
                else "（未启用意向驱动模式）"
            )

            # 填充用户 Prompt
            user_prompt = self.user_template.format(
                user_input=user_input,
                task_summary=task_summary or "（无已确认任务）",
                output_intent_context=output_intent_context,
                missing_dimensions=", ".join(missing_dimensions) if missing_dimensions else "无",
                covered_dimensions=", ".join(covered_dimensions) if covered_dimensions else "无",
                existing_info_summary=existing_info_summary or "（无已有信息）",
                completeness_score=int(completeness_score * 100),
                target_count=target_count,
            )

            logger.info("[LLMGapQuestionGenerator] 开始生成问题...")
            logger.debug(f"[LLMGapQuestionGenerator] 用户输入: {user_input[:100]}...")
            logger.debug(f"[LLMGapQuestionGenerator] 缺失维度: {missing_dimensions}")

            # 获取 LLM 实例
            if llm is None:
                from ..services.llm_factory import LLMFactory

                llm = LLMFactory.create_llm(
                    temperature=self.generation_config.get("temperature", 0.7),
                    max_tokens=self.generation_config.get("max_tokens", 2000),
                )

            #  v7.131: 使用重试机制调用 LLM
            messages = [SystemMessage(content=self.system_prompt), HumanMessage(content=user_prompt)]

            # 配置重试参数（从配置文件读取或使用默认值）
            retry_config = LLMRetryConfig(
                max_attempts=self.generation_config.get("max_retry_attempts", 3),
                min_wait=self.generation_config.get("retry_min_wait", 1.0),
                max_wait=self.generation_config.get("retry_max_wait", 10.0),
                timeout=self.generation_config.get("llm_timeout", 30.0),
            )

            response = await ainvoke_llm_with_retry(llm, messages, config=retry_config)
            response_text = response.content if hasattr(response, "content") else str(response)

            #  P1修复: 使用统一JSON解析器
            from ..utils.json_parser import parse_json_safe

            data = parse_json_safe(
                response_text,
                extract_from_markdown=True,
                fix_quotes=True,
                default={"questions": [], "generation_rationale": ""},
            )

            #  v7.130: 修复数据类型错误 - 处理LLM返回list的情况
            if isinstance(data, list):
                logger.warning("️ [LLMGapQuestionGenerator] LLM返回列表而非字典，自动转换")
                questions = data
                rationale = ""
            elif isinstance(data, dict):
                questions = data.get("questions", [])
                rationale = data.get("generation_rationale", "")
            else:
                logger.error(f" [LLMGapQuestionGenerator] 意外的数据类型: {type(data)}")
                questions = []
                rationale = ""

            #  v7.110: 验证和修复问题类型（复用 LLMQuestionGenerator 的逻辑）
            questions = self._validate_and_fix_questions(questions)

            # v7.200: 意向相关度后排序（软约束，不删题）
            if intent_rerank and active_projections:
                questions = self._rerank_questions_by_intent(questions, active_projections)
                logger.info(
                    f"[LLMGapQuestionGenerator] 意向重排完成，"
                    f"top3: {[q.get('id') for q in questions[:3]]}"
                )

            if not questions:
                logger.error("❌ [LLMGapQuestionGenerator] LLM返回空问题列表，触发降级")
                self.last_generation_metadata = {
                    "generation_source": "fallback_model_quality_failed",
                    "error_code": "LLM_EMPTY_RESULT",
                    "error_message": "LLM返回空问题列表",
                }
                return self._fallback_generate(missing_dimensions, confirmed_tasks)

            logger.info(f" [LLMGapQuestionGenerator] 成功生成 {len(questions)} 个问题")
            if rationale:
                logger.info(f"[LLMGapQuestionGenerator] 生成理由: {rationale}")

            return questions

        except Exception as e:
            logger.error(f" [LLMGapQuestionGenerator] 处理失败: {e}")
            error_code = self._classify_error_code(e)
            self.last_generation_metadata = {
                "generation_source": "fallback_auth_failed" if error_code == "LLM_AUTH_401" else "fallback_runtime_failed",
                "error_code": error_code,
                "error_message": str(e),
            }
            return self._fallback_generate(missing_dimensions, confirmed_tasks)

    def _fallback_generate(
        self, missing_dimensions: List[str], confirmed_tasks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        回退策略：使用 TaskCompletenessAnalyzer 生成硬编码问题

        Args:
            missing_dimensions: 缺失维度列表
            confirmed_tasks: 确认的任务列表

        Returns:
            硬编码问题列表
        """
        logger.warning("[LLMGapQuestionGenerator] 启用回退策略：使用硬编码问题")

        try:
            from ..services.task_completeness_analyzer import TaskCompletenessAnalyzer

            analyzer = TaskCompletenessAnalyzer()

            fallback_count = self.generation_config.get("fallback_min_questions", 5)
            questions = analyzer.generate_gap_questions(
                missing_dimensions=missing_dimensions,
                critical_gaps=[],
                confirmed_tasks=confirmed_tasks,
                existing_info_summary="",
                target_count=fallback_count,
            )

            logger.info(f" [LLMGapQuestionGenerator] 回退成功，生成 {len(questions)} 个硬编码问题")
            return questions

        except Exception as e:
            logger.error(f" [LLMGapQuestionGenerator] 回退策略失败: {e}")
            return []

    def _build_grouped_task_summary(self, confirmed_tasks: List[Dict[str, Any]]) -> str:
        """
        v7.200: 按 category 分组构建任务摘要。
        每组取代表性标题，最多 12 个分组，避免 [:5] 只覆盖同类任务。
        """
        if not confirmed_tasks:
            return "（无已确认任务）"

        groups: Dict[str, list] = {}
        for task in confirmed_tasks:
            cat = task.get("category", "其他")
            groups.setdefault(cat, []).append(task)

        lines = []
        for cat, tasks in list(groups.items())[:12]:
            rep = tasks[0]
            title = rep.get("title", "未命名")
            desc = (rep.get("description", "") or "")[:40]
            suffix = f"等{len(tasks)}项" if len(tasks) > 1 else ""
            lines.append(f"- [{cat}] {title}{suffix}: {desc}")

        return "\n".join(lines)

    def _build_output_intent_context(
        self,
        active_projections: Optional[List[str]],
        detected_identity_modes: Optional[List[Dict]],
        output_framework_signals: Optional[Dict],
        user_input: str = "",
    ) -> str:
        """
        v7.210: 构建输出意向上下文字符串，按项目类型选择合适描述，供注入 LLM prompt。
        修复：不再对所有项目类型使用同一套描述词（特别是乡村场景词汇不污染高端住宅项目）。
        """
        if not active_projections:
            return "（未检测到明确输出意向，使用通用维度分析）"

        project_type = self._detect_project_type(user_input)
        logger.info(f"[LLMGapQuestionGenerator] 检测到项目类型: {project_type}")

        lines = []
        for p in active_projections:
            # v7.211: 优先用 output_projections.yaml 动态数据，fallback 到硬编码 PROJECTION_DESCRIPTIONS
            type_map = self._dynamic_gap_dimensions.get(p) or self.PROJECTION_DESCRIPTIONS.get(p)
            if type_map:
                # 优先取项目类型对应描述，fallback 到 general
                desc = type_map.get(project_type) or type_map.get("general", "")
                if desc:
                    lines.append(f"- {desc}")
            else:
                lines.append(f"- {p}（自定义输出类型）")

        if detected_identity_modes:
            for mode in detected_identity_modes:
                label = mode.get("label") or mode.get("mode_name", "")
                spatial = mode.get("spatial_need", "")
                if label:
                    entry = f"- 身份模式「{label}」→ 空间需求：{spatial}" if spatial else f"- 身份模式「{label}」"
                    lines.append(entry)

        result = "\n".join(lines)
        logger.info(
            f"[LLMGapQuestionGenerator] 输出意向上下文构建完成（{len(active_projections)}个投射，项目类型:{project_type}）"
        )
        return result

    def _rerank_questions_by_intent(
        self, questions: List[Dict[str, Any]], active_projections: List[str]
    ) -> List[Dict[str, Any]]:
        """
        v7.200: 基于输出意向的软排序（不删题）。
        综合分 = 0.35*intent + 0.35*decision + 0.20*gap + 0.10*context
        保证：非相关题最多 2 题位于尾部（位置 > 5）。
        """
        DECISION_SCORE = {"high": 1.0, "medium": 0.7, "low": 0.3}
        proj_set = set(active_projections)

        def score(q: Dict) -> float:
            rel = set(q.get("projection_relevance") or [])
            intent = len(rel & proj_set) / max(len(proj_set), 1)
            decision = DECISION_SCORE.get(str(q.get("decision_impact", "")).lower(), 0.5)
            gap = 1.0 if q.get("is_required") else 0.4
            context = 0.8 if q.get("evidence_anchor") else 0.3
            return 0.35 * intent + 0.35 * decision + 0.20 * gap + 0.10 * context

        scored = sorted(((score(q), q) for q in questions), key=lambda x: -x[0])
        return [q for _, q in scored]

    def _validate_and_fix_questions(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        验证和修复问题格式（与 LLMQuestionGenerator 保持一致）

         v7.110: 添加类型标准化，修复 multi_choice 等错误类型

        Args:
            questions: 原始问题列表

        Returns:
            验证后的问题列表
        """
        validated = []
        type_count = {"single_choice": 0, "multiple_choice": 0, "open_ended": 0}

        for i, q in enumerate(questions):
            # 确保必要字段存在
            if not isinstance(q, dict):
                continue

            question_text = q.get("question", "")
            if not question_text:
                continue

            # 确保有唯一ID
            if not q.get("id"):
                q["id"] = f"gap_q_{i + 1}"

            # 验证和修正type字段
            q_type = q.get("type", "").lower()
            original_type = q_type  # 记录原始类型用于日志

            #  v7.110: 类型别名标准化映射（修复 multi_choice 等错误类型）
            type_aliases = {
                # multiple_choice 的各种错误拼写
                "multi_choice": "multiple_choice",
                "multi-choice": "multiple_choice",
                "multichoice": "multiple_choice",
                "checkbox": "multiple_choice",
                "checkboxes": "multiple_choice",
                "multi": "multiple_choice",
                # single_choice 的各种错误拼写
                "single": "single_choice",
                "single-choice": "single_choice",
                "singlechoice": "single_choice",
                "radio": "single_choice",
                "select": "single_choice",
                "dropdown": "single_choice",
                # open_ended 的各种错误拼写
                "open": "open_ended",
                "open-ended": "open_ended",
                "openended": "open_ended",
                "text": "open_ended",
                "textarea": "open_ended",
                "input": "open_ended",
                "free_text": "open_ended",
                "free-text": "open_ended",
            }

            # 应用类型别名映射
            if q_type in type_aliases:
                q_type = type_aliases[q_type]
                logger.warning(f" [Gap类型修复] 问题 {q.get('id', i+1)}: '{original_type}' → '{q_type}'")

            # 如果仍然不合法，从问题文本推断类型
            if q_type not in ["single_choice", "multiple_choice", "open_ended"]:
                # 从问题文本推断类型
                if "(单选)" in question_text or "单选" in question_text:
                    q_type = "single_choice"
                elif "(多选)" in question_text or "多选" in question_text:
                    q_type = "multiple_choice"
                elif "(开放题)" in question_text or "开放" in question_text:
                    q_type = "open_ended"
                else:
                    # 如果有options则为选择题，否则为开放题
                    if q.get("options"):
                        q_type = "single_choice"
                    else:
                        q_type = "open_ended"

                # 记录推断结果
                if original_type:
                    logger.warning(f" [Gap类型推断] 问题 {q.get('id', i+1)}: 未知类型 '{original_type}' → 推断为 '{q_type}'")

            q["type"] = q_type
            type_count[q_type] = type_count.get(q_type, 0) + 1

            # 验证选项（选择题必须有options）
            if q_type in ["single_choice", "multiple_choice"]:
                if not q.get("options") or not isinstance(q["options"], list):
                    q["options"] = ["选项A", "选项B", "选项C"]
                    logger.warning(f"️ Gap问题 {q['id']} 缺少选项，使用占位选项")

            # 验证开放题的placeholder
            if q_type == "open_ended":
                if not q.get("placeholder"):
                    q["placeholder"] = "请详细描述..."

            # 确保context存在
            if not q.get("context"):
                q["context"] = ""

            validated.append(q)

        logger.info(
            f" [Gap问卷验证] 问题类型分布: 单选={type_count['single_choice']}, "
            f"多选={type_count['multiple_choice']}, 开放={type_count['open_ended']}"
        )

        return validated

    def generate_sync(
        self,
        user_input: str,
        confirmed_tasks: List[Dict[str, Any]],
        missing_dimensions: List[str],
        covered_dimensions: List[str],
        existing_info_summary: str,
        completeness_score: float,
        llm: Optional[Any] = None,
        # v7.200: 输出意向参数（向后兼容）
        active_projections: Optional[List[str]] = None,
        detected_identity_modes: Optional[List[Dict]] = None,
        output_framework_signals: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """
        同步版本的 generate 方法（供非异步环境调用）

        使用 asyncio.run() 在独立事件循环中运行异步任务

        Args:
            参数同 generate()

        Returns:
            问题列表
        """
        import asyncio

        try:
            return asyncio.run(
                self.generate(
                    user_input=user_input,
                    confirmed_tasks=confirmed_tasks,
                    missing_dimensions=missing_dimensions,
                    covered_dimensions=covered_dimensions,
                    existing_info_summary=existing_info_summary,
                    completeness_score=completeness_score,
                    llm=llm,
                    active_projections=active_projections,
                    detected_identity_modes=detected_identity_modes,
                    output_framework_signals=output_framework_signals,
                )
            )
        except Exception as e:
            logger.error(f" [LLMGapQuestionGenerator] 同步调用失败: {e}")
            return self._fallback_generate(missing_dimensions, confirmed_tasks)
