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

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger


class LLMGapQuestionGenerator:
    """基于 LLM 生成任务信息补充问题"""

    def __init__(self):
        """初始化生成器，加载配置文件"""
        self.config = self._load_config()
        self.system_prompt = self.config.get("system_prompt", "")
        self.user_template = self.config.get("user_prompt_template", "")
        self.generation_config = self.config.get("generation_config", {})

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
                logger.info(f"✅ [LLMGapQuestionGenerator] 配置文件加载成功: {config_path}")
                return config
        except Exception as e:
            logger.error(f"❌ [LLMGapQuestionGenerator] 配置文件加载失败: {e}")
            return {}

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

        Returns:
            问题列表 [{"id": "", "question": "", "type": "", ...}]
        """
        try:
            # 计算目标问题数量
            target_count = self._calculate_target_count(missing_dimensions)

            # 构建任务摘要
            task_summary = "\n".join(
                [
                    f"- {task.get('title', '未命名任务')}: {task.get('description', '无描述')}"
                    for task in confirmed_tasks[:5]  # 最多显示5个任务
                ]
            )

            # 填充用户 Prompt
            user_prompt = self.user_template.format(
                user_input=user_input,
                task_summary=task_summary or "（无已确认任务）",
                missing_dimensions=", ".join(missing_dimensions) if missing_dimensions else "无",
                covered_dimensions=", ".join(covered_dimensions) if covered_dimensions else "无",
                existing_info_summary=existing_info_summary or "（无已有信息）",
                completeness_score=int(completeness_score * 100),
                target_count=target_count,
            )

            logger.info(f"[LLMGapQuestionGenerator] 开始生成问题...")
            logger.debug(f"[LLMGapQuestionGenerator] 用户输入: {user_input[:100]}...")
            logger.debug(f"[LLMGapQuestionGenerator] 缺失维度: {missing_dimensions}")

            # 获取 LLM 实例
            if llm is None:
                from ..services.llm_factory import LLMFactory

                llm = LLMFactory.create_llm(
                    temperature=self.generation_config.get("temperature", 0.7),
                    max_tokens=self.generation_config.get("max_tokens", 2000),
                )

            # 调用 LLM
            messages = [SystemMessage(content=self.system_prompt), HumanMessage(content=user_prompt)]

            response = await llm.ainvoke(messages)
            response_text = response.content if hasattr(response, "content") else str(response)

            # 🆕 P1修复: 使用统一JSON解析器
            from ..utils.json_parser import parse_json_safe

            data = parse_json_safe(
                response_text,
                extract_from_markdown=True,
                fix_quotes=True,
                default={"questions": [], "generation_rationale": ""},
            )

            questions = data.get("questions", [])
            rationale = data.get("generation_rationale", "")

            # 🆕 v7.110: 验证和修复问题类型（复用 LLMQuestionGenerator 的逻辑）
            questions = self._validate_and_fix_questions(questions)

            logger.info(f"✅ [LLMGapQuestionGenerator] 成功生成 {len(questions)} 个问题")
            if rationale:
                logger.info(f"[LLMGapQuestionGenerator] 生成理由: {rationale}")

            return questions

        except Exception as e:
            logger.error(f"❌ [LLMGapQuestionGenerator] 处理失败: {e}")
            return self._fallback_generate(missing_dimensions, confirmed_tasks)

        except Exception as e:
            logger.error(f"❌ [LLMGapQuestionGenerator] LLM 调用失败: {e}")
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

            logger.info(f"✅ [LLMGapQuestionGenerator] 回退成功，生成 {len(questions)} 个硬编码问题")
            return questions

        except Exception as e:
            logger.error(f"❌ [LLMGapQuestionGenerator] 回退策略失败: {e}")
            return []

    def _validate_and_fix_questions(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        验证和修复问题格式（与 LLMQuestionGenerator 保持一致）

        🆕 v7.110: 添加类型标准化，修复 multi_choice 等错误类型

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

            # 🆕 v7.110: 类型别名标准化映射（修复 multi_choice 等错误类型）
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
                logger.warning(f"🔧 [Gap类型修复] 问题 {q.get('id', i+1)}: '{original_type}' → '{q_type}'")

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
                    logger.warning(f"🔍 [Gap类型推断] 问题 {q.get('id', i+1)}: 未知类型 '{original_type}' → 推断为 '{q_type}'")

            q["type"] = q_type
            type_count[q_type] = type_count.get(q_type, 0) + 1

            # 验证选项（选择题必须有options）
            if q_type in ["single_choice", "multiple_choice"]:
                if not q.get("options") or not isinstance(q["options"], list):
                    q["options"] = ["选项A", "选项B", "选项C"]
                    logger.warning(f"⚠️ Gap问题 {q['id']} 缺少选项，使用占位选项")

            # 验证开放题的placeholder
            if q_type == "open_ended":
                if not q.get("placeholder"):
                    q["placeholder"] = "请详细描述..."

            # 确保context存在
            if not q.get("context"):
                q["context"] = ""

            validated.append(q)

        logger.info(
            f"📊 [Gap问卷验证] 问题类型分布: 单选={type_count['single_choice']}, "
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
                )
            )
        except Exception as e:
            logger.error(f"❌ [LLMGapQuestionGenerator] 同步调用失败: {e}")
            return self._fallback_generate(missing_dimensions, confirmed_tasks)
