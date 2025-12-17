"""
LLM驱动的问卷生成器

使用LLM基于用户输入和需求分析结果生成高度定制化的问卷，
解决正则/词库匹配方式无法理解用户意图的问题。

v7.5 新增：
- LLM驱动生成：利用LLM的深度理解能力生成针对性问题
- 相关性验证：生成后验证每个问题与用户需求的相关性
- 回退机制：LLM失败时使用FallbackQuestionGenerator

v7.18 新增：
- 添加 PerformanceMonitor 性能监控
- 共享函数迁移到 shared_agent_utils.py

作者：Design Beyond Team
日期：2025-12-11
"""

import json
import re
import time
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger

# 🆕 v7.18: 导入性能监控
from ...utils.shared_agent_utils import PerformanceMonitor


class LLMQuestionGenerator:
    """
    LLM驱动的问卷生成器

    使用LLM基于用户输入和需求分析结果生成定制化问卷，
    解决传统基于规则/词库的生成器无法理解用户深层需求的问题。
    """

    # 提示词版本号
    PROMPT_VERSION = "1.0"

    @classmethod
    def generate(
        cls,
        user_input: str,
        structured_data: Dict[str, Any],
        llm_model: Optional[Any] = None,
        timeout: int = 30
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        使用LLM生成定制化问卷

        Args:
            user_input: 用户原始输入
            structured_data: 需求分析师的结构化输出
            llm_model: LLM模型实例（可选，如果为None则创建默认实例）
            timeout: 超时时间（秒）

        Returns:
            Tuple[List[Dict], str]:
                - 问题列表
                - 生成来源标识（"llm_generated" | "fallback"）
        """
        logger.info("🤖 [LLMQuestionGenerator] 开始LLM驱动问卷生成")
        start_time = time.time()  # 🆕 v7.18: 性能监控开始

        try:
            # 1. 构建分析摘要
            analysis_summary = cls._build_analysis_summary(structured_data)
            logger.info(f"📊 [LLMQuestionGenerator] 分析摘要长度: {len(analysis_summary)}")

            # 🆕 v7.23: 提取用户关键词并注入到分析摘要
            user_keywords = cls._extract_user_keywords(user_input)
            if user_keywords:
                keywords_str = "、".join(user_keywords[:12])
                analysis_summary += f"\n\n## ⚠️ 用户关键词（问题必须引用）\n{keywords_str}"
                logger.info(f"🔑 [LLMQuestionGenerator] 注入用户关键词: {keywords_str[:50]}...")

            # 2. 获取或创建LLM实例
            if llm_model is None:
                from ...services.llm_factory import LLMFactory
                llm_model = LLMFactory.create_llm(temperature=0.7)
                logger.info("🔧 [LLMQuestionGenerator] 使用默认LLM实例")

            # 3. 加载提示词
            system_prompt, human_prompt = cls._load_prompts(user_input, analysis_summary)

            # 4. 调用LLM生成问卷
            logger.info("📤 [LLMQuestionGenerator] 调用LLM生成问卷...")
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": human_prompt}
            ]

            response = llm_model.invoke(messages)
            raw_content = response.content if hasattr(response, "content") else str(response)
            logger.info(f"📥 [LLMQuestionGenerator] LLM响应长度: {len(raw_content)}")

            # 5. 解析LLM输出
            questionnaire_data = cls._parse_llm_response(raw_content)
            questions = questionnaire_data.get("questions", [])

            if not questions:
                logger.warning("⚠️ [LLMQuestionGenerator] LLM返回空问卷，使用回退方案")
                # 🆕 v7.18: 记录失败性能
                PerformanceMonitor.record("LLMQuestionGenerator", time.time() - start_time, "v7.18-fallback")
                return cls._fallback_generate(structured_data, user_input), "fallback"

            # 6. 验证和修复问题格式
            validated_questions = cls._validate_and_fix_questions(questions)
            logger.info(f"✅ [LLMQuestionGenerator] 成功生成 {len(validated_questions)} 个问题")

            # 🆕 v7.6+v7.12: 验证问题与用户输入的相关性
            relevance_score, low_relevance_questions = cls._check_question_relevance(
                validated_questions, user_input
            )
            
            # 🆕 v7.18: 记录成功性能
            PerformanceMonitor.record("LLMQuestionGenerator", time.time() - start_time, "v7.18")
            
            if relevance_score < 0.3:
                # 🔧 v7.12: 相关性过低时尝试第二次生成，强化关键词要求
                logger.warning(f"⚠️ [LLMQuestionGenerator] 相关性过低 ({relevance_score:.2f})，尝试第二次生成")
                user_keywords = cls._extract_user_keywords(user_input)
                if user_keywords:
                    try:
                        regenerated_questions, _ = cls._regenerate_with_keywords(
                            user_input, analysis_summary, user_keywords, llm_model
                        )
                        if regenerated_questions:
                            new_score, _ = cls._check_question_relevance(regenerated_questions, user_input)
                            if new_score > relevance_score:
                                logger.info(f"✅ [LLMQuestionGenerator] 重新生成提升相关性: {relevance_score:.2f} → {new_score:.2f}")
                                validated_questions = regenerated_questions
                                relevance_score = new_score
                    except Exception as e:
                        logger.warning(f"⚠️ [LLMQuestionGenerator] 重新生成失败: {e}")
            elif relevance_score < 0.5:
                logger.warning(f"⚠️ [LLMQuestionGenerator] 问题相关性较低 ({relevance_score:.2f})，"
                              f"低相关问题: {low_relevance_questions}")

            # 7. 记录生成理由（用于调试）
            rationale = questionnaire_data.get("generation_rationale", "")
            if rationale:
                logger.info(f"💡 [LLMQuestionGenerator] 生成理由: {rationale[:200]}...")

            return validated_questions, "llm_generated"

        except Exception as e:
            logger.error(f"❌ [LLMQuestionGenerator] LLM生成失败: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

            # 使用回退方案
            return cls._fallback_generate(structured_data, user_input), "fallback"

    @classmethod
    def _build_analysis_summary(cls, structured_data: Dict[str, Any]) -> str:
        """
        构建需求分析摘要，用于提示词注入

        🔧 v7.6修复：
        - 扩展字段提取范围（新增 project_overview, core_objectives, narrative_characters 等）
        - 增加字段别名兼容（如 project_task/project_overview 互补）
        - 提取 constraints_opportunities 等重要决策信息

        Args:
            structured_data: 需求分析师的结构化输出

        Returns:
            格式化的分析摘要字符串
        """
        summary_parts = []

        # 🆕 v7.6: 项目概览（优先级最高，直接影响问卷针对性）
        project_overview = structured_data.get("project_overview", "")
        if project_overview:
            summary_parts.append(f"## 项目概览\n{project_overview}")

        # 项目任务（兼容旧字段名）
        project_task = structured_data.get("project_task", "") or structured_data.get("project_tasks", "")
        if isinstance(project_task, list):
            project_task = "；".join(project_task[:5])  # 最多5个任务
        if project_task and project_task != project_overview:  # 避免重复
            summary_parts.append(f"## 项目任务\n{project_task}")

        # 🆕 v7.6: 核心目标
        core_objectives = structured_data.get("core_objectives", [])
        if core_objectives:
            if isinstance(core_objectives, list):
                objectives_text = "\n".join([f"- {obj}" for obj in core_objectives[:5]])
            else:
                objectives_text = str(core_objectives)
            summary_parts.append(f"## 核心目标\n{objectives_text}")

        # 项目类型
        project_type = structured_data.get("project_type", "")
        if project_type:
            type_label = {
                "personal_residential": "个人住宅",
                "hybrid_residential_commercial": "混合型（住宅+商业）",
                "commercial_enterprise": "商业/企业项目",
                "cultural_educational": "文化/教育项目",
                "healthcare_wellness": "医疗/康养项目",
                "office_coworking": "办公/联合办公",
                "hospitality_tourism": "酒店/文旅项目",
                "sports_entertainment_arts": "体育/娱乐/艺术"
            }.get(project_type, project_type)
            summary_parts.append(f"## 项目类型\n{type_label}")

        # 设计挑战
        design_challenge = structured_data.get("design_challenge", "")
        if design_challenge:
            summary_parts.append(f"## 核心设计挑战\n{design_challenge}")

        # 核心张力
        core_tension = structured_data.get("core_tension", "")
        if core_tension:
            summary_parts.append(f"## 核心矛盾/张力\n{core_tension}")

        # 🆕 v7.6: 人物叙事（优先 narrative_characters，兼容 character_narrative）
        narrative_characters = structured_data.get("narrative_characters", "") or structured_data.get("character_narrative", "")
        if isinstance(narrative_characters, list):
            narrative_characters = "\n".join([f"- {char}" for char in narrative_characters[:3]])
        if narrative_characters:
            summary_parts.append(f"## 人物叙事/用户画像\n{narrative_characters}")

        # 🆕 v7.6: 物理环境（physical_contexts）
        physical_contexts = structured_data.get("physical_contexts", "")
        if isinstance(physical_contexts, list):
            physical_contexts = "；".join(physical_contexts[:3])
        if physical_contexts:
            summary_parts.append(f"## 物理环境\n{physical_contexts}")

        # 资源约束
        resource_constraints = structured_data.get("resource_constraints", "")
        if resource_constraints:
            summary_parts.append(f"## 资源约束\n{resource_constraints}")

        # 🆕 v7.6: 约束与机遇（constraints_opportunities）
        constraints_opportunities = structured_data.get("constraints_opportunities", "")
        if isinstance(constraints_opportunities, dict):
            co_parts = []
            if constraints_opportunities.get("constraints"):
                co_parts.append(f"约束: {constraints_opportunities['constraints']}")
            if constraints_opportunities.get("opportunities"):
                co_parts.append(f"机遇: {constraints_opportunities['opportunities']}")
            constraints_opportunities = "；".join(co_parts)
        if constraints_opportunities and constraints_opportunities != resource_constraints:
            summary_parts.append(f"## 约束与机遇\n{constraints_opportunities}")

        # 专家交接信息
        expert_handoff = structured_data.get("expert_handoff", {})
        if expert_handoff:
            handoff_summary = []
            if expert_handoff.get("design_challenge_spectrum"):
                spectrum = expert_handoff.get("design_challenge_spectrum", {})
                极端A = spectrum.get("极端A", {}).get("标签", "")
                极端B = spectrum.get("极端B", {}).get("标签", "")
                if 极端A and 极端B:
                    handoff_summary.append(f"设计光谱: {极端A} ←→ {极端B}")
            if expert_handoff.get("required_roles"):
                roles = expert_handoff.get("required_roles", [])
                if roles:
                    handoff_summary.append(f"建议专家: {', '.join(roles[:5])}")
            # 🆕 v7.6: 提取关键问题（critical_questions）
            critical_questions = expert_handoff.get("critical_questions_for_experts", {})
            if critical_questions:
                cq_list = []
                for role, questions in list(critical_questions.items())[:3]:
                    if questions:
                        # 🔧 确保 q_text 是字符串
                        if isinstance(questions, list):
                            q_text = questions[0] if questions else ""
                        elif isinstance(questions, dict):
                            # 如果是字典，尝试提取第一个值
                            q_text = next(iter(questions.values())) if questions else ""
                        else:
                            q_text = str(questions)
                        
                        # 确保 q_text 是字符串后再切片
                        if isinstance(q_text, str) and q_text:
                            cq_list.append(f"- {role}: {q_text[:50]}...")
                if cq_list:
                    handoff_summary.append(f"关键问题:\n" + "\n".join(cq_list))
            if handoff_summary:
                summary_parts.append(f"## 专家交接\n" + "\n".join(handoff_summary))

        # 🔥 v7.6: 如果摘要为空，返回更有用的提示而非"暂无"
        if not summary_parts:
            logger.warning("⚠️ [LLMQuestionGenerator] structured_data 字段全部为空，建议检查需求分析师输出")
            return "（需求分析数据不足，请基于用户原始输入生成问卷）"

        return "\n\n".join(summary_parts)

    @classmethod
    def _load_prompts(cls, user_input: str, analysis_summary: str) -> Tuple[str, str]:
        """
        加载并填充提示词模板

        Args:
            user_input: 用户原始输入
            analysis_summary: 分析摘要

        Returns:
            Tuple[str, str]: (system_prompt, human_prompt)
        """
        try:
            from ...core.prompt_manager import PromptManager
            prompt_manager = PromptManager()

            # 加载问卷生成器提示词 (返回完整配置字典)
            prompt_data = prompt_manager.get_prompt("questionnaire_generator", return_full_config=True)

            if prompt_data is None or not isinstance(prompt_data, dict):
                raise ValueError("questionnaire_generator prompt not found or invalid format")

            system_prompt = prompt_data.get("system_prompt", "")
            human_template = prompt_data.get("human_prompt_template", "")

            if not system_prompt:
                raise ValueError("system_prompt is empty")

            # 填充human_prompt模板
            human_prompt = human_template.format(
                user_input=user_input,
                analysis_summary=analysis_summary
            ) if human_template else f"""# 用户原始输入
{user_input}

# 需求分析结果
{analysis_summary}

请生成一份定制化问卷（7-10个问题），直接返回JSON格式。"""

            return system_prompt, human_prompt

        except Exception as e:
            logger.warning(f"⚠️ [LLMQuestionGenerator] 加载提示词失败: {e}")
            # 使用内置的基础提示词
            return cls._get_fallback_prompts(user_input, analysis_summary)

    @classmethod
    def _get_fallback_prompts(cls, user_input: str, analysis_summary: str) -> Tuple[str, str]:
        """
        获取内置的回退提示词

        Args:
            user_input: 用户原始输入
            analysis_summary: 分析摘要

        Returns:
            Tuple[str, str]: (system_prompt, human_prompt)
        """
        system_prompt = """你是一位资深的设计需求洞察专家。根据用户输入生成7-10个定制化问卷问题。

要求：
1. 问题必须紧密围绕用户的具体需求
2. 使用冲突选择题揭示用户的真实优先级
3. 避免通用模板问题

输出格式（纯JSON）：
{
  "introduction": "问卷引言",
  "questions": [
    {
      "id": "唯一ID",
      "question": "问题文本(单选)|(多选)|(开放题)",
      "context": "问题背景",
      "type": "single_choice|multiple_choice|open_ended",
      "options": ["选项A", "选项B"],  // 单选/多选必填
      "placeholder": "示例..."  // 开放题必填
    }
  ],
  "generation_rationale": "生成理由"
}"""

        human_prompt = f"""# 用户原始输入
{user_input}

# 需求分析结果
{analysis_summary}

请生成一份定制化问卷（7-10个问题），直接返回JSON格式。"""

        return system_prompt, human_prompt

    @classmethod
    def _parse_llm_response(cls, raw_content: str) -> Dict[str, Any]:
        """
        解析LLM响应，提取JSON格式的问卷数据

        Args:
            raw_content: LLM原始响应内容

        Returns:
            解析后的问卷数据字典
        """
        # 移除可能的markdown代码块标记
        content = raw_content.strip()

        # 尝试移除 ```json ... ``` 包装
        if content.startswith("```"):
            # 找到第一个换行符后的内容
            first_newline = content.find("\n")
            if first_newline != -1:
                content = content[first_newline + 1:]
            # 移除结尾的 ```
            if content.endswith("```"):
                content = content[:-3].strip()

        # 尝试直接解析JSON
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # 尝试提取JSON对象
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, content, re.DOTALL)

        for match in matches:
            try:
                parsed = json.loads(match)
                if "questions" in parsed:
                    return parsed
            except json.JSONDecodeError:
                continue

        # 最后尝试：查找包含questions的大JSON块
        start_idx = content.find('{"')
        if start_idx == -1:
            start_idx = content.find("{'")

        if start_idx != -1:
            # 尝试找到匹配的结束大括号
            brace_count = 0
            for i, char in enumerate(content[start_idx:]):
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        try:
                            return json.loads(content[start_idx:start_idx + i + 1])
                        except json.JSONDecodeError:
                            break

        logger.warning("⚠️ [LLMQuestionGenerator] 无法解析LLM响应为JSON")
        return {"questions": []}

    @classmethod
    def _validate_and_fix_questions(cls, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        验证和修复问题格式

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
                q["id"] = f"llm_q_{i + 1}"

            # 验证和修正type字段
            q_type = q.get("type", "").lower()
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
            q["type"] = q_type
            type_count[q_type] = type_count.get(q_type, 0) + 1

            # 验证选项（选择题必须有options）
            if q_type in ["single_choice", "multiple_choice"]:
                if not q.get("options") or not isinstance(q["options"], list):
                    # 尝试从问题文本中提取选项
                    q["options"] = ["选项A", "选项B", "选项C"]
                    logger.warning(f"⚠️ 问题 {q['id']} 缺少选项，使用占位选项")

            # 验证开放题的placeholder
            if q_type == "open_ended":
                if not q.get("placeholder"):
                    q["placeholder"] = "请详细描述..."

            # 确保context存在
            if not q.get("context"):
                q["context"] = ""

            validated.append(q)

        # 按题型排序：单选 → 多选 → 开放
        validated.sort(key=lambda x: {
            "single_choice": 0,
            "multiple_choice": 1,
            "open_ended": 2
        }.get(x.get("type", ""), 3))

        logger.info(f"📊 [LLMQuestionGenerator] 问题类型分布: 单选={type_count['single_choice']}, "
                    f"多选={type_count['multiple_choice']}, 开放={type_count['open_ended']}")

        return validated

    @classmethod
    def _fallback_generate(
        cls,
        structured_data: Dict[str, Any],
        user_input: str
    ) -> List[Dict[str, Any]]:
        """
        回退到规则生成器

        Args:
            structured_data: 结构化数据
            user_input: 用户输入

        Returns:
            问题列表
        """
        logger.info("🔄 [LLMQuestionGenerator] 使用FallbackQuestionGenerator回退")

        from .generators import FallbackQuestionGenerator
        from .context import KeywordExtractor

        extracted_info = KeywordExtractor.extract(user_input, structured_data)
        return FallbackQuestionGenerator.generate(
            structured_data,
            user_input=user_input,
            extracted_info=extracted_info
        )

    @classmethod
    def _check_question_relevance(
        cls,
        questions: List[Dict[str, Any]],
        user_input: str
    ) -> Tuple[float, List[str]]:
        """
        🆕 v7.6: 检查问题与用户输入的关键词重叠度

        通过简单的关键词匹配（不调用LLM），快速验证问题是否引用了用户原话。

        Args:
            questions: 问题列表
            user_input: 用户原始输入

        Returns:
            Tuple[float, List[str]]:
                - 平均相关性得分 (0-1)
                - 低相关性问题ID列表
        """
        if not questions or not user_input:
            return 1.0, []

        # 提取用户输入中的关键词（去除停用词）
        import re
        stopwords = {
            "的", "是", "在", "有", "我", "你", "他", "她", "它", "们",
            "这", "那", "和", "与", "或", "但", "而", "了", "着", "过",
            "吗", "呢", "吧", "啊", "呀", "哦", "嗯", "可以", "能够",
            "需要", "希望", "想要", "一个", "一些", "一种", "这个", "那个",
            "如何", "怎么", "什么", "哪些", "为什么", "请", "帮", "做",
            "进行", "实现", "完成", "考虑", "包括", "通过", "使用"
        }

        # 从用户输入提取关键词（2-10个字符的词）
        user_words = set()
        # 提取中文词语
        chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,10}', user_input)
        for word in chinese_words:
            if word not in stopwords:
                user_words.add(word)
        # 提取数字+单位
        numbers = re.findall(r'\d+[\u4e00-\u9fa5㎡]+', user_input)
        user_words.update(numbers)
        # 提取英文词
        english_words = re.findall(r'[a-zA-Z]{3,}', user_input)
        user_words.update(english_words)

        if not user_words:
            return 1.0, []  # 无法提取关键词，跳过检查

        logger.info(f"🔍 [RelevanceCheck] 用户关键词: {list(user_words)[:15]}...")

        # 检查每个问题是否包含用户关键词
        scores = []
        low_relevance = []

        for q in questions:
            question_text = q.get("question", "") + " ".join(q.get("options", []))
            # 计算关键词命中数
            hits = sum(1 for word in user_words if word in question_text)
            # 归一化得分
            score = min(1.0, hits / max(3, len(user_words) * 0.3))  # 命中3个词即满分
            scores.append(score)

            if score < 0.3:  # 低于30%相关性
                low_relevance.append(q.get("id", "unknown"))

        avg_score = sum(scores) / len(scores) if scores else 0
        logger.info(f"📊 [RelevanceCheck] 平均相关性: {avg_score:.2f}, 低相关问题: {len(low_relevance)}/{len(questions)}")

        return avg_score, low_relevance


class QuestionRelevanceValidator:
    """
    问题相关性验证器

    使用LLM评估每个问题与用户原始输入的相关性，
    过滤掉相关性低的问题。
    """

    @classmethod
    def validate(
        cls,
        questions: List[Dict[str, Any]],
        user_input: str,
        llm_model: Optional[Any] = None,
        threshold: float = 6.0
    ) -> List[Dict[str, Any]]:
        """
        验证问题相关性，过滤低相关性问题

        Args:
            questions: 问题列表
            user_input: 用户原始输入
            llm_model: LLM模型实例
            threshold: 相关性阈值（0-10），低于此值的问题将被过滤

        Returns:
            过滤后的问题列表
        """
        if not questions:
            return []

        # 如果问题数量较少，跳过验证
        if len(questions) <= 5:
            logger.info("📊 [RelevanceValidator] 问题数量≤5，跳过相关性验证")
            return questions

        try:
            if llm_model is None:
                from ...services.llm_factory import LLMFactory
                llm_model = LLMFactory.create_llm(temperature=0.3)

            # 构建验证提示词
            questions_text = "\n".join([
                f"{i+1}. [{q.get('id', f'q{i+1}')}] {q.get('question', '')}"
                for i, q in enumerate(questions)
            ])

            prompt = f"""请评估以下问卷问题与用户需求的相关性。

用户原始输入：
{user_input}

问卷问题：
{questions_text}

请为每个问题打分（0-10分），返回JSON格式：
{{"scores": {{"问题ID": 分数, ...}}}}

评分标准：
- 10分：问题直接针对用户提到的具体内容
- 7-9分：问题与用户需求相关，能够提供有价值的信息
- 4-6分：问题有一定关联，但较为通用
- 0-3分：问题与用户需求几乎无关

直接返回JSON，不要包含其他内容。"""

            response = llm_model.invoke([{"role": "user", "content": prompt}])
            raw_content = response.content if hasattr(response, "content") else str(response)

            # 解析评分结果
            scores = cls._parse_scores(raw_content)

            # 过滤低相关性问题
            filtered = []
            for q in questions:
                q_id = q.get("id", "")
                score = scores.get(q_id, 7.0)  # 默认7分（相关）

                if score >= threshold:
                    filtered.append(q)
                else:
                    logger.info(f"🚫 [RelevanceValidator] 过滤低相关性问题: {q_id} (得分: {score})")

            logger.info(f"📊 [RelevanceValidator] 保留 {len(filtered)}/{len(questions)} 个问题")
            return filtered

        except Exception as e:
            logger.warning(f"⚠️ [RelevanceValidator] 验证失败: {e}，保留所有问题")
            return questions

    @classmethod
    def _parse_scores(cls, raw_content: str) -> Dict[str, float]:
        """解析评分结果"""
        try:
            # 尝试直接解析JSON
            content = raw_content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content
                if content.endswith("```"):
                    content = content[:-3]

            data = json.loads(content)
            return {str(k): float(v) for k, v in data.get("scores", {}).items()}

        except (json.JSONDecodeError, ValueError, TypeError):
            logger.warning("⚠️ [RelevanceValidator] 无法解析评分结果")
            return {}


# ============================================================
# 🔧 v7.12: LLMQuestionGenerator 辅助方法（追加到类外部使用）
# ============================================================

# 为 LLMQuestionGenerator 添加辅助方法
def _extract_user_keywords_impl(user_input: str) -> List[str]:
    """
    🔧 v7.12: 从用户输入中提取关键词，用于强化问卷生成

    Args:
        user_input: 用户原始输入

    Returns:
        关键词列表（优先返回具体的名词、数字、专有名词）
    """
    if not user_input:
        return []
    
    keywords = []
    
    # 1. 提取数字+单位（如 200㎡、38岁、3房）
    import re
    num_patterns = re.findall(r'\d+[\u4e00-\u9fa5㎡a-zA-Z]+', user_input)
    keywords.extend(num_patterns)
    
    # 2. 提取引号内容（用户强调的内容）
    quoted = re.findall(r'[""「」『』【】]([^""「」『』【】]+)[""「」『』【】]', user_input)
    keywords.extend(quoted)
    
    # 3. 提取专有名词（连续中文，长度2-8）
    stopwords = {
        "的", "是", "在", "有", "我", "你", "他", "她", "它", "们",
        "这", "那", "和", "与", "或", "但", "而", "了", "着", "过",
        "需要", "希望", "想要", "一个", "一些", "这个", "那个",
        "如何", "怎么", "什么", "哪些", "为什么", "请", "帮",
        "进行", "实现", "完成", "考虑", "包括", "通过", "使用",
        "设计", "项目", "方案", "建议", "希望", "能够", "可以"
    }
    
    chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,8}', user_input)
    for word in chinese_words:
        if word not in stopwords and word not in keywords:
            keywords.append(word)
    
    # 4. 去重并限制数量
    unique_keywords = list(dict.fromkeys(keywords))  # 保持顺序去重
    return unique_keywords[:15]  # 最多15个关键词


def _regenerate_with_keywords_impl(
    user_input: str,
    analysis_summary: str,
    keywords: List[str],
    llm_model
) -> Tuple[List[Dict[str, Any]], str]:
    """
    🔧 v7.12: 使用强化关键词约束重新生成问卷

    Args:
        user_input: 用户原始输入
        analysis_summary: 分析摘要
        keywords: 用户关键词列表
        llm_model: LLM模型实例

    Returns:
        Tuple[问题列表, 来源标识]
    """
    keywords_str = "、".join(keywords[:10])
    
    reinforced_prompt = f"""请基于以下用户需求生成针对性问卷。

⚠️ 重要约束：每个问题必须至少包含以下关键词之一：
【{keywords_str}】

用户原始需求：
{user_input}

需求分析摘要：
{analysis_summary}

生成要求：
1. 每个问题必须引用用户原话中的具体内容（数字、地点、人物、特征）
2. 禁止生成"您对...有什么想法？"等泛化问题
3. 问题选项必须围绕用户提到的具体约束展开

返回JSON格式：
{{"questions": [
    {{"id": "q1", "question": "...", "options": ["选项A", "选项B", "选项C", "选项D"]}}
]}}"""

    messages = [
        {"role": "system", "content": "你是专业的用户需求调研专家，擅长生成高度针对性的问卷问题。"},
        {"role": "user", "content": reinforced_prompt}
    ]
    
    response = llm_model.invoke(messages)
    raw_content = response.content if hasattr(response, "content") else str(response)
    
    # 解析响应
    questionnaire_data = LLMQuestionGenerator._parse_llm_response(raw_content)
    questions = questionnaire_data.get("questions", [])
    
    if questions:
        validated = LLMQuestionGenerator._validate_and_fix_questions(questions)
        return validated, "llm_regenerated"
    
    return [], "regeneration_failed"


# 将方法绑定到 LLMQuestionGenerator 类
LLMQuestionGenerator._extract_user_keywords = classmethod(lambda cls, user_input: _extract_user_keywords_impl(user_input))
LLMQuestionGenerator._regenerate_with_keywords = classmethod(
    lambda cls, user_input, analysis_summary, keywords, llm_model: 
    _regenerate_with_keywords_impl(user_input, analysis_summary, keywords, llm_model)
)
