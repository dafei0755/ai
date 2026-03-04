"""
4步骤搜索流程编排服务 (v1.0)

实现智能、开放、不硬编码的4步骤搜索流程：
- Step 1: 深度分析 - 动态生成输出框架
- Step 2: 搜索任务分解 - 将框架转化为具体查询
- Step 3: 智能搜索执行 - 动态增补查询
- Step 4: 总结生成 - 灵活的内容驱动输出

核心原则：
1. 智能、开放、不硬编码
2. 职责分离
3. 自适应搜索
4. 用户控制

Author: AI Assistant
Created: 2026-02-01
Version: 1.0
"""

import json
import os
import re
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Tuple

import yaml
from loguru import logger

# 导入数据结构
from intelligent_project_analyzer.core.four_step_flow_types import (
    DeepAnalysisResult,
    Discovery,
    ExecutionAdvice,
    ExecutionStrategy,
    FourStepFlowState,
    FrameworkAddition,
    HumanDimensions,
    L1ProblemDeconstruction,
    L2MotivationDimension,
    L3CoreTension,
    L4JTBDDefinition,
    L5SharpnessTest,
    OutputBlock,
    OutputBlockSubItem,
    OutputFramework,
    Priority,
    QualityAssessment,
    SearchDirection,  # Step 1.5 新增
    SearchExecutionConfig,
    SearchQuery,
    SearchResultAnalysis,
    SearchTaskList,
    SupplementaryQuery,
    TriggerType,
    Understanding,
    ValidationCheck,
    ValidationReport,
)

# 导入LLM工厂
from intelligent_project_analyzer.services.llm_factory import LLMFactory

# 导入搜索方向生成器 (Step 1.5)
from intelligent_project_analyzer.services.search_direction_generator import (
    SearchDirectionGenerator,
)

# 导入搜索服务
try:
    from intelligent_project_analyzer.services.bocha_ai_search import (
        get_ai_search_service,
    )

    SEARCH_SERVICE_AVAILABLE = True
except ImportError:
    SEARCH_SERVICE_AVAILABLE = False
    logger.warning("️ 搜索服务未可用")

from intelligent_project_analyzer.services._four_step_helpers import PromptLoader, clean_repetitive_content


# ============================================================================
# Step 1: 深度分析执行器
# ============================================================================


class Step1DeepAnalysisExecutor:
    """Step 1: 深度分析执行器 (v3.0 - Complete Redesign)

    Three-Stage Architecture:
    - Stage 1: Internal L1-L5 Analysis (JSON output)
    - Stage 2: User-Facing Dialogue (3 sections)
    - Stage 3: Validation & Extraction
    """

    def __init__(self, llm_factory: LLMFactory):
        self.llm_factory = llm_factory
        # 使用 v3 prompt
        self.prompt_config = PromptLoader.load_prompt_config("step1_deep_analysis_v3.yaml")
        self.max_retries = self.prompt_config.get("business_config", {}).get("max_retries", 2)
        logger.info(f" Step1 使用 Prompt 配置: step1_deep_analysis_v3.yaml (max_retries={self.max_retries})")

    async def execute(self, user_input: str, stream: bool = True) -> AsyncGenerator[Dict[str, Any], None]:
        """
        执行Step 1深度分析 (v3.0 - Three-Stage Architecture)

        Args:
            user_input: 用户输入
            stream: 是否流式输出

        Yields:
            SSE事件字典
        """
        logger.info(" [Step 1 v3] 开始深度分析...")

        try:
            # v7.332: 发送 Stage 1 开始事件，让用户知道系统在工作
            yield {
                "event": "step1_stage1_start",
                "data": {"message": "正在深度理解您的需求..."},
            }

            # Stage 1: Internal L1-L5 Analysis
            stage1_result = None
            for retry in range(self.max_retries + 1):
                try:
                    logger.info(f"[Stage 1] 尝试 {retry + 1}/{self.max_retries + 1}")
                    stage1_result = await self._execute_stage1(user_input)

                    # 验证 Stage 1 结果
                    validation_result = self._validate_stage1(stage1_result)
                    if validation_result["valid"]:
                        logger.info(" [Stage 1] 验证通过")
                        break
                    else:
                        logger.warning(f"️ [Stage 1] 验证失败: {validation_result['errors']}")
                        if retry < self.max_retries:
                            # 重试，带上错误反馈
                            continue
                        else:
                            # 最后一次尝试也失败，返回带警告的结果
                            yield {
                                "event": "step1_validation_warnings",
                                "data": {"warnings": validation_result["errors"]},
                            }
                except Exception as e:
                    logger.error(f" [Stage 1] 执行失败: {e}")
                    if retry < self.max_retries:
                        continue
                    else:
                        raise

            if not stage1_result:
                raise ValueError("Stage 1 执行失败")

            # Stage 2: User-Facing Output Generation
            # v7.520: 修复重试导致"输出→消失→再输出"的 bug
            # 策略：后端缓冲所有重试，只有验证通过（或最终尝试）后才流式发送给前端
            # 这样重试过程对用户完全不可见，避免内容闪烁
            stage2_result = None
            stage2_validation_warnings = None

            for retry in range(self.max_retries + 1):
                try:
                    logger.info(f"[Stage 2] 尝试 {retry + 1}/{self.max_retries + 1}")

                    if stream:
                        # 缓冲模式：先收集所有内容，验证通过后再流式发送
                        dialogue_content = ""
                        async for chunk in self._execute_stage2_stream(stage1_result):
                            dialogue_content += chunk
                        stage2_result = dialogue_content
                    else:
                        stage2_result = await self._execute_stage2(stage1_result)

                    # 验证 Stage 2 结果（v4.0: 传入 user_input 用于具体性检查）
                    validation_result = self._validate_stage2(stage2_result, user_input=user_input)
                    if validation_result["valid"]:
                        logger.info(" [Stage 2] 验证通过")
                        break
                    else:
                        logger.warning(f"️ [Stage 2] 验证失败 (尝试 {retry + 1}): {validation_result['errors']}")
                        if retry < self.max_retries:
                            # 还有重试机会，继续下一轮（用户无感知）
                            continue
                        else:
                            # 最后一次也失败，使用当前结果并记录警告
                            stage2_validation_warnings = validation_result["errors"]
                except Exception as e:
                    logger.error(f" [Stage 2] 执行失败 (尝试 {retry + 1}): {e}")
                    if retry < self.max_retries:
                        continue
                    else:
                        raise

            if not stage2_result:
                raise ValueError("Stage 2 执行失败")

            # v7.520: 验证通过（或最终尝试），现在流式发送给前端
            if stream:
                # 模拟流式输出：将缓冲的内容分块发送给前端
                chunk_size = 20  # 每次发送约20个字符，模拟自然的流式效果
                accumulated = ""
                for i in range(0, len(stage2_result), chunk_size):
                    chunk = stage2_result[i : i + chunk_size]
                    accumulated += chunk
                    yield {
                        "event": "step1_dialogue_chunk",
                        "data": {
                            "chunk": chunk,
                            "accumulated": accumulated,
                        },
                    }

            # 发送验证警告（如果有）
            if stage2_validation_warnings:
                yield {
                    "event": "step1_validation_warnings",
                    "data": {"warnings": stage2_validation_warnings},
                }

            # v7.306: 后处理清理重复内容
            original_length = len(stage2_result)
            stage2_result = clean_repetitive_content(stage2_result)
            if len(stage2_result) < original_length:
                logger.info(f"️ 清理重复内容: {original_length} → {len(stage2_result)} 字符")

            # Stage 3: Final Validation & Build Result
            yield {"event": "step1_extracting_structure", "data": {}}

            result = self._build_deep_analysis_result(stage1_result, stage2_result)
            validation_report = self._generate_validation_report(stage1_result, stage2_result)

            yield {
                "event": "step1_completed",
                "data": {
                    "dialogue_content": stage2_result,
                    "understanding": self._serialize_understanding(result.understanding),
                    "output_framework": self._serialize_output_framework(result.output_framework),
                    "search_direction_hints": result.search_direction_hints,
                    "validation_report": self._serialize_validation_report(validation_report),
                },
            }

            logger.info(" [Step 1 v3] 深度分析完成")

        except Exception as e:
            logger.error(f" [Step 1 v3] 深度分析失败: {e}")
            yield {"event": "step1_error", "data": {"error": str(e)}}

    async def _execute_stage1(self, user_input: str) -> Dict[str, Any]:
        """
        Stage 1: Internal L1-L5 Analysis

        Returns:
            JSON结构化数据
        """
        logger.info("[Stage 1] 开始内部L1-L5分析")

        # 构建 Stage 1 prompt
        stage1_prompt = self._build_stage1_prompt(user_input)

        # 调用LLM (JSON mode)
        llm = self.llm_factory.create_llm(temperature=0.3, max_tokens=3000)
        response = await self._generate_llm_response(llm, stage1_prompt)

        # 解析JSON
        try:
            # 提取JSON代码块
            json_match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response

            structured_data = json.loads(json_str)
            logger.info("[Stage 1] JSON解析成功")
            return structured_data
        except json.JSONDecodeError as e:
            logger.error(f" [Stage 1] JSON解析失败: {e}")
            logger.debug(f"原始响应: {response}")
            raise

    async def _execute_stage2(self, stage1_result: Dict[str, Any]) -> str:
        """
        Stage 2: User-Facing Output Generation (非流式)

        Returns:
            对话式内容
        """
        logger.info("[Stage 2] 开始生成用户友好输出")

        # 构建 Stage 2 prompt
        stage2_prompt = self._build_stage2_prompt(stage1_result)

        # 调用LLM
        # v7.510: 提升 max_tokens 从 4000 到 8000，支持 6-12 个板块的输出
        llm = self.llm_factory.create_llm(temperature=0.7, max_tokens=8000)
        dialogue_content = await self._generate_llm_response(llm, stage2_prompt)

        logger.info("[Stage 2] 对话内容生成完成")
        return dialogue_content

    async def _execute_stage2_stream(self, stage1_result: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """
        Stage 2: User-Facing Output Generation (流式)

        Yields:
            对话内容片段
        """
        logger.info("[Stage 2] 开始流式生成用户友好输出")

        # 构建 Stage 2 prompt
        stage2_prompt = self._build_stage2_prompt(stage1_result)

        # 流式调用LLM
        # v7.510: 提升 max_tokens 从 4000 到 8000，支持 6-12 个板块的输出
        llm = self.llm_factory.create_llm(temperature=0.7, max_tokens=8000)
        async for chunk in self._stream_llm_response(llm, stage2_prompt):
            yield chunk

    def _build_stage1_prompt(self, user_input: str) -> str:
        """构建 Stage 1 prompt"""
        system_prompt = self.prompt_config.get("stage1_system_prompt", "")
        user_prompt_template = self.prompt_config.get("stage1_user_prompt_template", "")

        # 添加当前日期时间信息
        datetime_info = f"当前日期: {datetime.now().strftime('%Y年%m月%d日')}"

        user_prompt = user_prompt_template.format(datetime_info=datetime_info, user_input=user_input)

        # 组合 system + user prompt
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        return full_prompt

    def _build_stage2_prompt(self, stage1_result: Dict[str, Any]) -> str:
        """构建 Stage 2 prompt"""
        system_prompt = self.prompt_config.get("stage2_system_prompt", "")
        user_prompt_template = self.prompt_config.get("stage2_user_prompt_template", "")

        # 添加当前日期时间信息
        datetime_info = f"当前日期: {datetime.now().strftime('%Y年%m月%d日')}"

        # 将 stage1_result 转为 JSON 字符串
        stage1_json = json.dumps(stage1_result, ensure_ascii=False, indent=2)

        user_prompt = user_prompt_template.format(datetime_info=datetime_info, stage1_analysis=stage1_json)

        # 组合 system + user prompt
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        return full_prompt

    def _validate_stage1(self, stage1_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证 Stage 1 输出 (v4.0 — 新增 research_dimensions 验证)

        Returns:
            {"valid": bool, "errors": List[str]}
        """
        errors = []
        validation_rules = self.prompt_config.get("validation_rules", {})

        # 1. 验证 L2 动机维度（v4.0: 全面扫描模式，输出所有score>=3的动机）
        l2_motivations = stage1_result.get("l2_motivations", [])
        standard_dimensions = validation_rules.get("l2_motivations", {}).get("standard_dimensions", [])

        for motivation in l2_motivations:
            name = motivation.get("name", "")
            if name not in standard_dimensions:
                errors.append(f"L2动机'{name}'不在12个标准维度中")

        # 2. 验证 L4 JTBD（v4.0: 移除 full_statement 长度要求）
        l4_jtbd = stage1_result.get("l4_jtbd", {})
        required_fields = [
            "user_role",
            "information_type",
            "task_1",
            "task_2",
        ]

        for field in required_fields:
            if not l4_jtbd.get(field):
                errors.append(f"L4 JTBD缺少字段: {field}")

        # 3. 验证 L5 锐度测试（v4.0: 移除 reason≥30字 要求）
        l5_sharpness = stage1_result.get("l5_sharpness", {})
        required_scores = ["specificity_score", "actionability_score", "depth_score", "searchability_score"]

        for score_field in required_scores:
            score = l5_sharpness.get(score_field, 0)
            if score != 0 and not 1 <= score <= 10:
                errors.append(f"L5 {score_field}不在1-10范围内: {score}")

        # 4. v4.0: 验证 research_dimensions（核心新增）
        research_dimensions = stage1_result.get("research_dimensions", [])
        rd_rules = validation_rules.get("research_dimensions", {})
        min_rd = rd_rules.get("min_count", 5)
        max_rd = rd_rules.get("max_count", 10)

        if len(research_dimensions) < min_rd:
            errors.append(f"研究维度数量不足: {len(research_dimensions)}个，至少需要{min_rd}个")
        elif len(research_dimensions) > max_rd:
            errors.append(f"研究维度数量过多: {len(research_dimensions)}个，最多{max_rd}个")

        for idx, dim in enumerate(research_dimensions):
            dim_name = dim.get("dimension_name", "")
            if not dim_name:
                errors.append(f"研究维度 #{idx+1} 缺少 dimension_name")
            if not dim.get("example_queries"):
                errors.append(f"研究维度 '{dim_name}' 缺少 example_queries")

        return {"valid": len(errors) == 0, "errors": errors}

    def _validate_stage2(self, dialogue_content: str, user_input: str = "") -> Dict[str, Any]:
        """
        验证 Stage 2 输出 (v4.0 — 新的"步骤 N"格式 + 去重/具体性/搜索可行性门控)

        Args:
            dialogue_content: Stage 2 生成的对话内容
            user_input: 用户原始输入（用于具体性检查）

        Returns:
            {"valid": bool, "errors": List[str]}
        """
        errors = []
        validation_rules = self.prompt_config.get("validation_rules", {})

        # 1. 检查必需部分（v4.0: "我们如何理解您的需求" + "深入研究计划"）
        required_sections = validation_rules.get(
            "output_format",
        ).get("required_sections", [])
        for section in required_sections:
            if section not in dialogue_content:
                errors.append(f"缺少必需部分: {section}")

        # 2. 检查禁止的内容
        forbidden_content = validation_rules.get("output_format", {}).get("forbidden_content", [])
        for forbidden in forbidden_content:
            if forbidden in dialogue_content:
                errors.append(f"包含禁止的术语: {forbidden}")

        # v4.0: 提取步骤名称（后续多个检查共用）
        step_names_raw = re.findall(r"步骤\s*\d+[：:\s]*(.+?)(?=步骤\s*\d+|---|$)", dialogue_content, re.DOTALL)
        step_names = [s.strip().split("\n")[0] for s in step_names_raw]

        # v4.0: 检查步骤数量（替代旧的 emoji 板块计数）
        step_count = len(step_names)
        min_step_count = validation_rules.get("step_count", {}).get("min_count", 5)
        if step_count < min_step_count:
            # 向后兼容：也检查旧的 emoji 格式
            old_block_pattern = r"\*\*[1-9]️⃣"
            old_block_count = len(re.findall(old_block_pattern, dialogue_content))
            if old_block_count >= min_step_count:
                step_count = old_block_count  # 旧格式也接受
            else:
                errors.append(f"步骤数量不足: {step_count}个，至少需要{min_step_count}个")

        # v4.0 Phase 3.1: 步骤去重检查（字符集相似度）
        if len(step_names) >= 2:
            for i, name1 in enumerate(step_names):
                for _j, name2 in enumerate(step_names[i + 1 :], start=i + 1):
                    similarity = self._calculate_step_similarity(name1, name2)
                    if similarity >= 0.7:
                        errors.append(f"步骤重叠(相似度{similarity:.0%}): " f"'{name1[:25]}...' vs '{name2[:25]}...'")

        # v4.0 Phase 3.2: 具体性检查（步骤名称须包含用户输入中的实体）
        if user_input and step_names:
            entities = self._extract_entities_from_input(user_input)
            if entities:
                for step_name in step_names:
                    has_entity = any(entity in step_name for entity in entities)
                    if not has_entity:
                        # 降级为 warning 而非 error — 不是所有步骤都必须包含用户实体
                        # 但如果超过一半的步骤都不包含，则报错
                        pass
                # 整体检查：至少一半步骤包含用户实体
                steps_with_entity = sum(1 for s in step_names if any(entity in s for entity in entities))
                if steps_with_entity < max(1, len(step_names) // 3):
                    errors.append(
                        f"步骤具体性不足: {steps_with_entity}/{len(step_names)}个步骤" f"包含用户相关实体({', '.join(entities[:5])})"
                    )

        # v4.0 Phase 3.3: 检查搜索可行性（代码层强制执行 forbidden_keywords）
        searchability_rules = validation_rules.get("searchability_check", {})
        forbidden_keywords = searchability_rules.get("forbidden_keywords", [])
        for step_name in step_names:
            for keyword in forbidden_keywords:
                if keyword in step_name:
                    errors.append(f"步骤'{step_name[:30]}...'包含实施类关键词'{keyword}'")

        return {"valid": len(errors) == 0, "errors": errors}

    @staticmethod
    def _calculate_step_similarity(name1: str, name2: str) -> float:
        """
        计算两个步骤名称的字符集相似度（Jaccard系数）

        Args:
            name1: 步骤名称1
            name2: 步骤名称2

        Returns:
            相似度 0.0-1.0
        """
        set1 = set(name1)
        set2 = set(name2)
        union = len(set1 | set2)
        if union == 0:
            return 0.0
        return len(set1 & set2) / union

    @staticmethod
    def _extract_entities_from_input(user_input: str) -> List[str]:
        """
        从用户输入中提取实体关键词（品牌名、地名、人名、数字等）

        简单实现：提取长度>=2的非停用词片段。
        不使用 LLM，纯字符串处理。

        Args:
            user_input: 用户原始输入

        Returns:
            实体关键词列表
        """
        # 停用词（常见虚词、连接词）
        stop_words = {
            "的",
            "了",
            "在",
            "是",
            "我",
            "有",
            "和",
            "就",
            "不",
            "人",
            "都",
            "一",
            "一个",
            "上",
            "也",
            "很",
            "到",
            "说",
            "要",
            "去",
            "你",
            "会",
            "着",
            "没有",
            "看",
            "好",
            "自己",
            "这",
            "他",
            "她",
            "它",
            "们",
            "那",
            "些",
            "什么",
            "怎么",
            "如何",
            "可以",
            "需要",
            "想",
            "做",
            "能",
            "让",
            "把",
            "被",
            "从",
            "对",
            "为",
            "以",
            "及",
            "或",
            "但",
            "而",
            "与",
            "等",
            "之",
            "所",
            "其",
            "这个",
            "那个",
            "关于",
            "进行",
            "通过",
            "使用",
            "帮",
            "帮我",
            "请",
            "想要",
            "主题",
            "设计",
            "方案",
            "概念",
            "思路",
            "风格",
            "分析",
            "研究",
        }

        entities = []

        # 1. 提取英文词/品牌名（连续英文字母，长度>=2）
        english_words = re.findall(r"[A-Za-z]{2,}", user_input)
        entities.extend(english_words)

        # 2. 提取数字+单位（如 350平米、35岁）
        number_units = re.findall(r"\d+[a-zA-Z\u4e00-\u9fff]{1,3}", user_input)
        entities.extend(number_units)

        # 3. 提取中文关键词片段
        # 简单分词：按标点和常见分隔符切分
        segments = re.split(r"[，。、；：！？\s,.:;!?\-—/\\()（）【】\[\]{}\"\']+", user_input)
        for seg in segments:
            seg = seg.strip()
            # 去除英文和数字部分后的纯中文片段
            chinese_parts = re.findall(r"[\u4e00-\u9fff]{2,6}", seg)
            for part in chinese_parts:
                if part not in stop_words:
                    entities.append(part)

        # 去重保序
        seen = set()
        unique_entities = []
        for e in entities:
            e_lower = e.lower()
            if e_lower not in seen:
                seen.add(e_lower)
                unique_entities.append(e)

        return unique_entities

    def _build_deep_analysis_result(self, stage1_result: Dict[str, Any], stage2_dialogue: str) -> DeepAnalysisResult:
        """
        构建 DeepAnalysisResult 对象 (v4.0 — 支持 research_dimensions)
        """
        # 解析 Understanding
        l1_data = stage1_result.get("l1_deconstruction", {})
        l1_deconstruction = L1ProblemDeconstruction(
            user_identity=l1_data.get("user_identity", ""),
            explicit_needs=l1_data.get("explicit_needs", ""),
            implicit_motivations=l1_data.get("implicit_motivations", ""),
            key_constraints=l1_data.get("key_constraints", ""),
            analysis_perspective=l1_data.get("analysis_perspective", ""),
        )

        l2_motivations = []
        for mot_data in stage1_result.get("l2_motivations", []):
            try:
                l2_motivations.append(
                    L2MotivationDimension(
                        name=mot_data.get("name", ""),
                        type=mot_data.get("type", ""),
                        score=mot_data.get("score", 0),
                        reason=mot_data.get("reason", ""),
                        evidence=mot_data.get("evidence", []),
                        scenario_expression=mot_data.get("scenario_expression", ""),
                    )
                )
            except ValueError as e:
                logger.warning(f"️ L2动机验证失败: {e}")

        l3_data = stage1_result.get("l3_tension", {})
        l3_tension = L3CoreTension(
            primary_motivation=l3_data.get("primary_motivation", ""),
            secondary_motivation=l3_data.get("secondary_motivation", ""),
            tension_formula=l3_data.get("tension_formula", ""),
            tension_description=l3_data.get("tension_description", ""),  # v4.0
            resolution_strategy=l3_data.get("resolution_strategy", ""),
            hidden_insights=l3_data.get("hidden_insights", []),
        )

        l4_data = stage1_result.get("l4_jtbd", {})
        l4_jtbd = L4JTBDDefinition(
            user_role=l4_data.get("user_role", ""),
            information_type=l4_data.get("information_type", ""),
            task_1=l4_data.get("task_1", ""),
            task_2=l4_data.get("task_2", ""),
            full_statement=l4_data.get("full_statement", ""),
        )

        l5_data = stage1_result.get("l5_sharpness", {})
        l5_sharpness = L5SharpnessTest(
            specificity_score=l5_data.get("specificity_score", 0),
            specificity_reason=l5_data.get("specificity_reason", ""),
            specificity_evidence=l5_data.get("specificity_evidence", ""),
            actionability_score=l5_data.get("actionability_score", 0),
            actionability_reason=l5_data.get("actionability_reason", ""),
            actionability_evidence=l5_data.get("actionability_evidence", ""),
            depth_score=l5_data.get("depth_score", 0),
            depth_reason=l5_data.get("depth_reason", ""),
            depth_evidence=l5_data.get("depth_evidence", ""),
            searchability_score=l5_data.get("searchability_score", 0),  # v4.0
            searchability_reason=l5_data.get("searchability_reason", ""),  # v4.0
            overall_quality=l5_data.get("overall_quality", "合格"),
        )

        # 人性维度
        human_dims_data = stage1_result.get("human_dimensions", {})
        human_dimensions = None
        if human_dims_data.get("enabled"):
            human_dimensions = HumanDimensions(
                enabled=True,
                emotional_landscape=human_dims_data.get("emotional_landscape"),
                spiritual_aspirations=human_dims_data.get("spiritual_aspirations"),
                psychological_safety_needs=human_dims_data.get("psychological_safety_needs"),
                ritual_behaviors=human_dims_data.get("ritual_behaviors"),
                memory_anchors=human_dims_data.get("memory_anchors"),
            )

        # v4.0: 提取 research_dimensions
        research_dimensions = stage1_result.get("research_dimensions", [])

        understanding = Understanding(
            l1_deconstruction=l1_deconstruction,
            l2_motivations=l2_motivations,
            l3_tension=l3_tension,
            l4_jtbd=l4_jtbd,
            l5_sharpness=l5_sharpness,
            human_dimensions=human_dimensions,
            comprehensive_summary=stage1_result.get("comprehensive_summary", ""),
            research_dimensions=research_dimensions,  # v4.0
        )

        # v4.0: 从对话内容中提取 OutputFramework，传入 research_dimensions 用于填充
        output_framework = self._extract_output_framework_from_dialogue(
            stage2_dialogue, research_dimensions=research_dimensions
        )

        # 搜索方向提示
        search_hints = self._extract_search_hints_from_dialogue(stage2_dialogue)

        # 生成验证报告
        validation_report = self._generate_validation_report(stage1_result, stage2_dialogue)

        return DeepAnalysisResult(
            understanding=understanding,
            output_framework=output_framework,
            search_direction_hints=search_hints,
            validation_report=validation_report,
            metadata={"version": "4.0", "timestamp": datetime.now().isoformat()},
        )

    def _extract_output_framework_from_dialogue(
        self, dialogue_content: str, research_dimensions: List[Dict[str, Any]] = None
    ) -> OutputFramework:
        """
        从对话内容中提取 OutputFramework (v4.0 — 支持"步骤 N"格式 + 旧格式兼容)

        v4.0 变更：
        - 优先匹配"步骤 N  研究XXX"格式
        - 向后兼容旧的 emoji 板块格式
        - 从 research_dimensions 填充 search_focus / indicative_queries / domain_knowledge_hints
        """
        if research_dimensions is None:
            research_dimensions = []

        blocks = []

        # v4.0: 优先匹配"步骤 N"格式
        step_pattern = r"步骤\s*(\d+)[：:\s]*(.+?)(?=步骤\s*\d+|---|$)"
        step_matches = list(re.finditer(step_pattern, dialogue_content, re.DOTALL))

        if step_matches:
            # v4.0 新格式：步骤 N
            for idx, match in enumerate(step_matches):
                step_num = int(match.group(1))
                step_content = match.group(2).strip()
                # 取第一行作为步骤名称（可能跨多行）
                step_lines = step_content.split("\n")
                step_name = step_lines[0].strip()

                # 从 research_dimensions 中按索引查找对应维度
                rd_data = research_dimensions[idx] if idx < len(research_dimensions) else {}

                user_characteristics = self._extract_user_characteristics(step_name)

                try:
                    blocks.append(
                        OutputBlock(
                            id=f"block_{step_num}",
                            name=step_name,
                            estimated_length="待定",
                            sub_items=[],  # v4.0: 步骤格式无子项
                            user_characteristics=user_characteristics,
                            search_focus=rd_data.get("why_searchable", ""),
                            indicative_queries=rd_data.get("example_queries", []),
                            domain_knowledge_hints=rd_data.get("domain_knowledge_hints", ""),
                        )
                    )
                except ValueError as e:
                    logger.warning(f"️ 步骤验证失败: {e}")
                    blocks.append(
                        OutputBlock(
                            id=f"block_{step_num}",
                            name=step_name if len(step_name) >= 4 else f"{step_name}（研究分析）",
                            estimated_length="待定",
                            sub_items=[],
                            user_characteristics=["用户"],
                            search_focus=rd_data.get("why_searchable", ""),
                            indicative_queries=rd_data.get("example_queries", []),
                            domain_knowledge_hints=rd_data.get("domain_knowledge_hints", ""),
                        )
                    )
        else:
            # 向后兼容：旧的 emoji 板块格式
            block_pattern = r"\*\*[1-9]️⃣\s*([^*]+?)\*\*(?:（约([^）]+)）)?|[1-9]️⃣\s*\*\*([^*]+?)\*\*(?:（约([^）]+)）)?"
            block_matches = re.finditer(block_pattern, dialogue_content)

            for idx, match in enumerate(block_matches, start=1):
                block_name = (match.group(1) or match.group(3) or "").strip()
                estimated_length = (match.group(2) or match.group(4) or "待定").strip()

                start_pos = match.end()
                next_block_pattern = r"\*\*[1-9]️⃣|[1-9]️⃣\s*\*\*"
                next_match = re.search(next_block_pattern, dialogue_content[start_pos:])

                if next_match:
                    end_pos = start_pos + next_match.start()
                else:
                    section_end = dialogue_content.find("---", start_pos)
                    end_pos = section_end if section_end != -1 else len(dialogue_content)

                block_content = dialogue_content[start_pos:end_pos]

                sub_items = []
                sub_item_pattern = r"(?:•\s*|[-–]\s*\d+\.\d+\s*)(.+?)(?=\n|$)"
                sub_item_matches = re.finditer(sub_item_pattern, block_content)

                for sub_idx, sub_match in enumerate(sub_item_matches, start=1):
                    sub_item_text = sub_match.group(1).strip()
                    sub_items.append(
                        OutputBlockSubItem(
                            id=f"{idx}.{sub_idx}",
                            name=sub_item_text,
                            description=sub_item_text,
                        )
                    )

                user_characteristics = self._extract_user_characteristics(block_name)
                rd_data = research_dimensions[idx - 1] if (idx - 1) < len(research_dimensions) else {}

                try:
                    blocks.append(
                        OutputBlock(
                            id=f"block_{idx}",
                            name=block_name,
                            estimated_length=estimated_length,
                            sub_items=sub_items,
                            user_characteristics=user_characteristics,
                            search_focus=rd_data.get("why_searchable", ""),
                            indicative_queries=rd_data.get("example_queries", []),
                            domain_knowledge_hints=rd_data.get("domain_knowledge_hints", ""),
                        )
                    )
                except ValueError as e:
                    logger.warning(f"️ 板块验证失败: {e}")
                    blocks.append(
                        OutputBlock(
                            id=f"block_{idx}",
                            name=f"{block_name}（用户特定需求分析）" if len(block_name) < 4 else block_name,
                            estimated_length=estimated_length,
                            sub_items=sub_items,
                            user_characteristics=["用户"],
                        )
                    )

        # v7.521: 兜底 - 正则提取失败时，从 research_dimensions 创建 blocks
        if not blocks and research_dimensions:
            logger.warning(f"️ 正则提取失败，使用 research_dimensions 作为后备 " f"({len(research_dimensions)} 个维度)")
            for idx, rd_data in enumerate(research_dimensions, start=1):
                dim_name = rd_data.get("dimension_name", f"研究维度 {idx}")
                user_characteristics = self._extract_user_characteristics(dim_name)
                try:
                    blocks.append(
                        OutputBlock(
                            id=f"block_{idx}",
                            name=dim_name,
                            estimated_length="待定",
                            sub_items=[],
                            user_characteristics=user_characteristics,
                            search_focus=rd_data.get("why_searchable", ""),
                            indicative_queries=rd_data.get("example_queries", []),
                            domain_knowledge_hints=rd_data.get("domain_knowledge_hints", ""),
                        )
                    )
                except ValueError as e:
                    logger.warning(f"️ 后备板块验证失败: {e}")
                    blocks.append(
                        OutputBlock(
                            id=f"block_{idx}",
                            name=dim_name if len(dim_name) >= 4 else f"{dim_name}（研究分析）",
                            estimated_length="待定",
                            sub_items=[],
                            user_characteristics=["用户"],
                        )
                    )

        if not blocks:
            logger.error(" 无法提取任何板块，创建默认板块")
            blocks.append(
                OutputBlock(
                    id="block_1",
                    name="综合研究分析（自动生成）",
                    estimated_length="待定",
                    sub_items=[],
                    user_characteristics=["用户"],
                )
            )

        # 提取核心目标和交付物类型
        core_objective = self._extract_core_objective(dialogue_content)
        deliverable_type = self._extract_deliverable_type(dialogue_content)
        quality_standards = self._extract_quality_standards(dialogue_content)

        return OutputFramework(
            core_objective=core_objective,
            deliverable_type=deliverable_type,
            blocks=blocks,
            quality_standards=quality_standards,
            validation_report=None,
        )

    def _extract_user_characteristics(self, block_name: str) -> List[str]:
        """从板块名称中提取用户特征关键词"""
        characteristics = []
        keywords = [
            "民宿业主",
            "开发者",
            "产品经理",
            "设计师",
            "创始人",
            "峨眉山",
            "七里坪",
            "React",
            "SaaS",
            "HAY",
            "38岁",
            "不婚",
            "女性",
            "高端",
            "中高端",
        ]

        for keyword in keywords:
            if keyword in block_name:
                characteristics.append(keyword)

        if not characteristics:
            characteristics.append("用户")

        return characteristics

    def _extract_core_objective(self, dialogue_content: str) -> str:
        """提取核心目标"""
        pattern = r"您的定制(.+?)包含："
        match = re.search(pattern, dialogue_content)
        if match:
            return f"提供{match.group(1).strip()}"
        return "提供定制化解决方案"

    def _extract_deliverable_type(self, dialogue_content: str) -> str:
        """提取交付物类型"""
        pattern = r"您的定制(.+?)包含："
        match = re.search(pattern, dialogue_content)
        if match:
            return match.group(1).strip()
        return "定制化方案"

    def _extract_quality_standards(self, dialogue_content: str) -> List[str]:
        """提取质量标准"""
        standards = []
        pattern = r"\s*(.+?)(?=\n|$)"
        matches = re.finditer(pattern, dialogue_content)

        for match in matches:
            standard = match.group(1).strip()
            if "个核心板块" not in standard and "包含" in standard:
                standards.append(standard)

        return standards[:5]

    def _extract_search_hints_from_dialogue(self, dialogue_content: str) -> str:
        """从对话内容中提取搜索方向提示"""
        pattern = r"【接下来的搜索计划】(.+?)(?=---|$)"
        match = re.search(pattern, dialogue_content, re.DOTALL)

        if match:
            search_section = match.group(1).strip()
            search_items = re.findall(r"\s*(.+?)(?=\n|$)", search_section)
            return "\n".join(search_items)

        return "根据用户需求进行相关搜索"

    def _generate_validation_report(self, stage1_result: Dict[str, Any], stage2_dialogue: str) -> ValidationReport:
        """生成完整的验证报告"""
        checks = []

        # Stage 1 验证
        stage1_validation = self._validate_stage1(stage1_result)
        if stage1_validation["valid"]:
            checks.append(
                ValidationCheck(
                    name="Stage 1: L1-L5分析",
                    status="passed",
                    message="所有L1-L5分析符合要求",
                )
            )
        else:
            for error in stage1_validation["errors"]:
                checks.append(ValidationCheck(name="Stage 1: L1-L5分析", status="failed", message=error))

        # Stage 2 验证
        stage2_validation = self._validate_stage2(stage2_dialogue)
        if stage2_validation["valid"]:
            checks.append(
                ValidationCheck(
                    name="Stage 2: 用户友好输出",
                    status="passed",
                    message="输出格式符合要求",
                )
            )
        else:
            for error in stage2_validation["errors"]:
                checks.append(ValidationCheck(name="Stage 2: 用户友好输出", status="failed", message=error))

        # 确定整体状态
        failed_checks = [c for c in checks if c.status == "failed"]
        warning_checks = [c for c in checks if c.status == "warning"]

        if failed_checks:
            overall_status = "failed"
        elif warning_checks:
            overall_status = "warning"
        else:
            overall_status = "passed"

        return ValidationReport(
            overall_status=overall_status,
            checks=checks,
            timestamp=datetime.now().isoformat(),
        )

    async def _stream_llm_response(self, llm, prompt: str) -> AsyncGenerator[str, None]:
        """流式调用LLM"""
        try:
            async for chunk in llm.astream(prompt):
                if hasattr(chunk, "content"):
                    yield chunk.content
        except Exception as e:
            logger.error(f" LLM流式调用失败: {e}")
            raise

    async def _generate_llm_response(self, llm, prompt: str) -> str:
        """非流式调用LLM"""
        try:
            response = await llm.ainvoke(prompt)
            return response.content
        except Exception as e:
            logger.error(f" LLM调用失败: {e}")
            raise

    async def _extract_structured_data(self, user_input: str, dialogue_content: str) -> Dict[str, Any]:
        """提取结构化数据（JSON）"""
        json_prompt_template = self.prompt_config.get("json_extraction_prompt_template", "")

        datetime_info = f"当前日期: {datetime.now().strftime('%Y年%m月%d日')}"
        json_prompt = json_prompt_template.format(
            datetime_info=datetime_info,
            user_input=user_input,
            dialogue_content=dialogue_content,
        )

        llm = self.llm_factory.create_llm(temperature=0.3, max_tokens=3000)
        response = await self._generate_llm_response(llm, json_prompt)

        # 解析JSON
        try:
            # 提取JSON代码块
            json_match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response

            structured_data = json.loads(json_str)
            return structured_data
        except json.JSONDecodeError as e:
            logger.error(f" JSON解析失败: {e}")
            logger.debug(f"原始响应: {response}")
            return {}

    def _parse_deep_analysis_result(self, dialogue_content: str, structured_data: Dict[str, Any]) -> DeepAnalysisResult:
        """解析为DeepAnalysisResult对象"""
        # 解析understanding
        understanding_data = structured_data.get("understanding", {})
        motivation_data = understanding_data.get("motivation_analysis", {})

        primary_motivations = [L2MotivationDimension(**m) for m in motivation_data.get("primary_motivations", [])]
        secondary_motivations = [L2MotivationDimension(**m) for m in motivation_data.get("secondary_motivations", [])]

        human_dims_data = understanding_data.get("human_dimensions", {})
        human_dimensions = None
        if human_dims_data.get("enabled"):
            human_dimensions = HumanDimensions(
                enabled=True,
                emotional_landscape=human_dims_data.get("emotional_landscape"),
                spiritual_aspirations=human_dims_data.get("spiritual_aspirations"),
                psychological_safety_needs=human_dims_data.get("psychological_safety_needs"),
                ritual_behaviors=human_dims_data.get("ritual_behaviors"),
                memory_anchors=human_dims_data.get("memory_anchors"),
            )

        # 解析 L5 锐度测试
        sharpness_data = understanding_data.get("sharpness_test", {})
        sharpness_test = None
        if sharpness_data:
            sharpness_test = L5SharpnessTest(
                specificity_score=sharpness_data.get("specificity_score", 0),
                specificity_reason=sharpness_data.get("specificity_reason", ""),
                actionability_score=sharpness_data.get("actionability_score", 0),
                actionability_reason=sharpness_data.get("actionability_reason", ""),
                depth_score=sharpness_data.get("depth_score", 0),
                depth_reason=sharpness_data.get("depth_reason", ""),
            )

        understanding = Understanding(
            problem_deconstruction=understanding_data.get("problem_deconstruction", ""),
            motivation_analysis={
                "primary_motivations": primary_motivations,
                "secondary_motivations": secondary_motivations,
            },
            core_tension=understanding_data.get("core_tension", ""),
            jtbd_definition=understanding_data.get("jtbd_definition", ""),
            sharpness_test=sharpness_test,
            human_dimensions=human_dimensions,
            comprehensive_understanding=understanding_data.get("comprehensive_understanding", ""),
        )

        # 解析output_framework
        framework_data = structured_data.get("output_framework", {})
        blocks = []
        for block_data in framework_data.get("blocks", []):
            sub_items = [OutputBlockSubItem(**item) for item in block_data.get("sub_items", [])]
            blocks.append(
                OutputBlock(
                    id=block_data.get("id", ""),
                    name=block_data.get("name", ""),
                    estimated_length=block_data.get("estimated_length", ""),
                    sub_items=sub_items,
                )
            )

        output_framework = OutputFramework(
            core_objective=framework_data.get("core_objective", ""),
            deliverable_type=framework_data.get("deliverable_type", ""),
            blocks=blocks,
            quality_standards=framework_data.get("quality_standards", []),
        )

        return DeepAnalysisResult(
            understanding=understanding,
            output_framework=output_framework,
            search_direction_hints=structured_data.get("search_direction_hints", ""),
            metadata=structured_data.get("metadata", {}),
        )

    def _serialize_understanding(self, understanding: Understanding) -> Dict[str, Any]:
        """序列化Understanding对象 (v3.0 - 适配新结构)"""
        return {
            "l1_deconstruction": {
                "user_identity": understanding.l1_deconstruction.user_identity,
                "explicit_needs": understanding.l1_deconstruction.explicit_needs,
                "implicit_motivations": understanding.l1_deconstruction.implicit_motivations,
                "key_constraints": understanding.l1_deconstruction.key_constraints,
            },
            "l2_motivations": [
                {
                    "name": m.name,
                    "type": m.type,
                    "score": m.score,
                    "reason": m.reason,
                    "evidence": m.evidence,
                }
                for m in understanding.l2_motivations
            ],
            "l3_tension": {
                "primary_motivation": understanding.l3_tension.primary_motivation,
                "secondary_motivation": understanding.l3_tension.secondary_motivation,
                "tension_formula": understanding.l3_tension.tension_formula,
                "resolution_strategy": understanding.l3_tension.resolution_strategy,
            },
            "l4_jtbd": {
                "user_role": understanding.l4_jtbd.user_role,
                "information_type": understanding.l4_jtbd.information_type,
                "task_1": understanding.l4_jtbd.task_1,
                "task_2": understanding.l4_jtbd.task_2,
                "full_statement": understanding.l4_jtbd.full_statement,
            },
            "l5_sharpness": {
                "specificity_score": understanding.l5_sharpness.specificity_score,
                "specificity_reason": understanding.l5_sharpness.specificity_reason,
                "specificity_evidence": understanding.l5_sharpness.specificity_evidence,
                "actionability_score": understanding.l5_sharpness.actionability_score,
                "actionability_reason": understanding.l5_sharpness.actionability_reason,
                "actionability_evidence": understanding.l5_sharpness.actionability_evidence,
                "depth_score": understanding.l5_sharpness.depth_score,
                "depth_reason": understanding.l5_sharpness.depth_reason,
                "depth_evidence": understanding.l5_sharpness.depth_evidence,
                "overall_quality": understanding.l5_sharpness.overall_quality,
            },
            "human_dimensions": (
                {
                    "enabled": understanding.human_dimensions.enabled,
                    "emotional_landscape": understanding.human_dimensions.emotional_landscape,
                    "spiritual_aspirations": understanding.human_dimensions.spiritual_aspirations,
                    "psychological_safety_needs": understanding.human_dimensions.psychological_safety_needs,
                    "ritual_behaviors": understanding.human_dimensions.ritual_behaviors,
                    "memory_anchors": understanding.human_dimensions.memory_anchors,
                }
                if understanding.human_dimensions
                else None
            ),
            "comprehensive_summary": understanding.comprehensive_summary,
        }

    def _serialize_output_framework(self, framework: OutputFramework) -> Dict[str, Any]:
        """序列化OutputFramework对象"""
        return {
            "core_objective": framework.core_objective,
            "deliverable_type": framework.deliverable_type,
            "blocks": [
                {
                    "id": block.id,
                    "name": block.name,
                    "estimated_length": block.estimated_length,
                    "sub_items": [
                        {
                            "id": item.id,
                            "name": item.name,
                            "description": item.description,
                        }
                        for item in block.sub_items
                    ],
                }
                for block in framework.blocks
            ],
            "quality_standards": framework.quality_standards,
        }

    def _serialize_validation_report(self, validation_report: ValidationReport) -> Dict[str, Any]:
        """序列化ValidationReport对象"""
        return {
            "overall_status": validation_report.overall_status,
            "checks": [
                {
                    "name": check.name,
                    "status": check.status,
                    "message": check.message,
                }
                for check in validation_report.checks
            ],
            "timestamp": validation_report.timestamp,
        }

    def _validate_output(self, dialogue_content: str, structured_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证 Step 1 输出质量 (v2.0 用户友好格式)

        Returns:
            验证结果字典，包含 warnings 列表
        """
        warnings = []

        # 1. 检查是否包含必需的2个部分 (v3.0 格式)
        # 注意："接下来的搜索计划" 是 Step 2 的内容，Step 1 不需要
        required_sections = ["我们如何理解您的需求", "您将获得什么"]

        for section in required_sections:
            if section not in dialogue_content:
                warnings.append(f"缺少必需部分: {section}")

        # 2. 检查是否包含不应该出现的内容（Step 2 的内容或旧版格式）
        forbidden_sections = [
            "【使命1：我的理解】",  # 旧版格式
            "【输出结果框架】",  # 旧版格式
            "【搜索方向提示】",  # 旧版格式
            "搜索执行框架",
            "维度1：",
            "维度2：",
            "并行搜索建议",
            "成功标准（5-8项）",
        ]

        for section in forbidden_sections:
            if section in dialogue_content:
                warnings.append(f"包含不应该出现的内容: {section} (这是旧版格式或 Step 2 的内容)")

        # 3. 检查 v2.0 格式的核心元素
        understanding = structured_data.get("understanding", {})

        # v2.0: 检查综合理解（替代 JTBD）
        comprehensive = understanding.get("comprehensive_understanding", "")
        if not comprehensive or len(comprehensive) < 50:
            warnings.append("综合理解缺失或过短（应至少50字）")

        # 4. v2.0: L5 锐度测试是内部分析，不强制要求在输出中
        # 但如果存在，应该有合理的分数
        sharpness = understanding.get("sharpness_test", None)
        if sharpness:
            if sharpness.get("specificity_score", 0) == 0:
                warnings.append("L5 锐度测试的专一性得分为0")
            if sharpness.get("actionability_score", 0) == 0:
                warnings.append("L5 锐度测试的可操作性得分为0")
            if sharpness.get("depth_score", 0) == 0:
                warnings.append("L5 锐度测试的深度得分为0")

        # 5. v2.0: 动机分析是内部分析，不强制检查标准维度
        # 但如果存在，应该有合理的类型分类
        motivation_analysis = understanding.get("motivation_analysis", {})
        all_motivations = motivation_analysis.get("primary_motivations", []) + motivation_analysis.get(
            "secondary_motivations", []
        )

        valid_types = ["功能型", "情感型", "社会型", "精神型"]
        for motivation in all_motivations:
            mot_type = motivation.get("type", "")
            if mot_type and mot_type not in valid_types:
                warnings.append(f"动机类型'{mot_type}'不在标准类型中（功能型/情感型/社会型/精神型）")

        # 6. v2.0: 检查板块名称是否足够具体（包含用户关键特征）
        framework = structured_data.get("output_framework", {})
        blocks = framework.get("blocks", [])

        generic_names = [
            "设计理念",
            "空间规划",
            "色彩方案",
            "材质选择",
            "功能分区",
            "基本概念",
            "基础分析",
        ]

        for block in blocks:
            block_name = block.get("name", "")
            # 检查是否包含泛化词汇且过短
            if any(generic in block_name for generic in generic_names):
                if len(block_name) < 15:
                    warnings.append(f"板块名称'{block_name}'过于泛化且过短（应至少15字且包含用户关键特征，如年龄/身份/品牌/地点）")
                    logger.warning(f"️ [验证] 板块名称过于泛化: {block_name}")
            # 检查长度
            if len(block_name) < 10:
                warnings.append(f"板块名称'{block_name}'过短（应至少10字，建议15字以上）")
                logger.warning(f"️ [验证] 板块名称过短: {block_name}")

            # v3.2: 检查板块是否包含多主题信号词
            multi_theme_signals = ["与", "和", "及", "以及"]
            for signal in multi_theme_signals:
                if signal in block_name:
                    parts = block_name.split(signal)
                    # 如果拆分后每部分都有实质内容（>5字），说明可能是多主题
                    if len(parts) >= 2 and all(len(p.strip()) > 5 for p in parts):
                        warnings.append(f"板块'{block_name}'可能包含多个主题（检测到'{signal}'连接词），建议拆分为独立板块")
                        logger.warning(f"️ [验证] 板块可能包含多主题: {block_name} (检测到'{signal}')")

        # 记录板块验证结果
        logger.info(f" [验证] 板块验证完成 | 板块数: {len(blocks)} | 警告数: {len([w for w in warnings if '板块' in w])}")

        # 7. v2.0: 检查搜索方向提示（从"接下来的搜索计划"提取）
        search_hints = structured_data.get("search_direction_hints", "")
        if not search_hints or len(search_hints) < 50:
            warnings.append("搜索方向提示缺失或过短（应至少50字）")

        # 8. v2.0: 检查是否包含具体数字（板块数、页数、案例数）
        if "个核心板块" not in dialogue_content and "个板块" not in dialogue_content:
            warnings.append("缺少板块数量说明（应包含'X个核心板块'）")

        if "约" not in dialogue_content and "页" not in dialogue_content:
            warnings.append("缺少页数估算（应包含'约X页'）")

        # 9. v2.0: 检查是否使用了emoji标记
        required_emojis = ["", "", "", "", ""]
        missing_emojis = [emoji for emoji in required_emojis if emoji not in dialogue_content]
        if missing_emojis:
            warnings.append(f"缺少视觉标记: {', '.join(missing_emojis)}")

        return {"valid": len(warnings) == 0, "warnings": warnings}


__all__ = ["Step1DeepAnalysisExecutor"]
