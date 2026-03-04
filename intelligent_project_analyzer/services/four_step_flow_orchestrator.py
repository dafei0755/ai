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


# ============================================================================
# 配置加载
# ============================================================================


class PromptLoader:
    """Prompt配置加载器"""

    @staticmethod
    def load_prompt_config(prompt_file: str) -> Dict[str, Any]:
        """
        加载prompt配置文件

        Args:
            prompt_file: prompt文件名（如 "step1_deep_analysis.yaml"）

        Returns:
            配置字典
        """
        config_path = os.path.join(os.path.dirname(__file__), "..", "config", "prompts", prompt_file)

        try:
            with open(config_path, encoding="utf-8") as f:
                config = yaml.safe_load(f)
            logger.debug(f" 加载prompt配置: {prompt_file}")
            return config
        except Exception as e:
            logger.error(f" 加载prompt配置失败 {prompt_file}: {e}")
            raise


# ============================================================================
# 重复内容后处理清理
# ============================================================================


def clean_repetitive_content(content: str) -> str:
    """
    清理 LLM 输出中的重复内容（后处理）

    策略：保守处理，只清理明确的重复模式
    - 检测 "方案高参来帮您" 是否出现多次
    - 如果出现多次，截取到第二次出现之前的内容

    Args:
        content: LLM 生成的完整内容

    Returns:
        清理后的内容
    """
    # 优先：如果存在明确的结束标记，直接截断
    end_marker = "【输出到此结束】"
    end_idx = content.find(end_marker)
    if end_idx != -1:
        trimmed = content[: end_idx + len(end_marker)].strip()
        return trimmed

    # 关键段落标记，用于检测重复
    markers = [
        "方案高参来帮您",
        "【您将获得什么】",
        "**【您将获得什么】",
        "【我们如何理解您的需求】",
        "**【我们如何理解您的需求】**",
        "您面临的挑战：",
        "我们发现的深层需求：",
        "我们的分析维度：",
        "我们的设计重点：",
    ]

    def find_second_occurrence(text: str, marker: str) -> Tuple[int, int]:
        first = text.find(marker)
        if first == -1:
            return -1, -1
        second = text.find(marker, first + len(marker))
        return first, second

    candidates: List[Tuple[str, int, int]] = []
    for marker in markers:
        first_idx, second_idx = find_second_occurrence(content, marker)
        if first_idx != -1 and second_idx != -1:
            # 避免同一段内的误判：重复距离太近则忽略
            if second_idx - first_idx >= 100:
                candidates.append((marker, first_idx, second_idx))

    if not candidates:
        return content

    # 选择最早出现的“重复起点”
    marker, first_idx, second_idx = min(candidates, key=lambda x: x[2])

    logger.warning(f"️ 检测到重复内容: marker='{marker}' 第一次位置={first_idx}，第二次位置={second_idx}")
    logger.info(f"️ 截取内容长度: {len(content)} → {second_idx}")

    cleaned = content[:second_idx].strip()

    # 确保结尾是合理的（不是在句子中间截断）
    # 如果截断后没有以标点或换行结尾，往前找到最后一个完整段落
    if cleaned and not cleaned.endswith(("\n", "。", "！", "？", "）", "」", "】")):
        last_newline = cleaned.rfind("\n\n")
        if last_newline > len(cleaned) * 0.8:  # 只有在最后 20% 内找到换行才截断
            cleaned = cleaned[:last_newline].strip()

    return cleaned


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


# ============================================================================
# Step 2: 搜索任务分解执行器
# ============================================================================


class Step2SearchTaskDecompositionExecutor:
    """Step 2: 搜索任务分解执行器 (v2.0 - 支持搜索方向)"""

    def __init__(self, llm_factory: LLMFactory):
        self.llm_factory = llm_factory
        self.prompt_config = PromptLoader.load_prompt_config("step2_search_task_decomposition.yaml")

    async def execute(
        self,
        user_input: str,
        output_framework: OutputFramework,
        search_directions: Dict[str, List[SearchDirection]] | None = None,  # v2.0 新增
        stream: bool = True,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        执行Step 2搜索任务分解

        Args:
            user_input: 用户输入
            output_framework: Step 1的输出框架
            search_directions: Step 1.5的搜索方向 (block_id -> directions)
            stream: 是否流式输出

        Yields:
            SSE事件字典
        """
        logger.info(" [Step 2] 开始搜索任务分解...")

        try:
            # 1. 构建prompt
            task_prompt = self._build_task_decomposition_prompt(user_input, output_framework, search_directions)

            # 2. 调用LLM生成任务清单
            # v7.421: 提升参数以强化初始生成质量
            # - temperature 0.5 → 0.7: 提升创造性，生成更丰富的任务
            # - max_tokens 3000 → 5000: 确保充分输出（5个板块×8个任务需要更多token）
            llm = self.llm_factory.create_llm(temperature=0.7, max_tokens=5000)

            if stream:
                # 流式输出
                task_list_content = ""
                async for chunk in self._stream_llm_response(llm, task_prompt):
                    task_list_content += chunk
                    yield {
                        "event": "step2_task_list_chunk",
                        "data": {"chunk": chunk, "accumulated": task_list_content},
                    }

                # 3. 提取结构化数据
                yield {"event": "step2_extracting_structure", "data": {}}
                structured_data = await self._extract_structured_data(user_input, task_list_content)

                # 4. 解析为SearchTaskList
                result = self._parse_search_task_list(task_list_content, structured_data)

                #  v7.420: 验证并补充搜索任务
                yield {"event": "step2_validating_queries", "data": {"message": "正在验证搜索任务数量..."}}
                validated_queries = await self._validate_and_supplement_queries(
                    queries=result.search_queries,
                    output_framework=output_framework,
                    user_input=user_input,
                )

                # 更新结果
                result.search_queries = validated_queries

                yield {
                    "event": "step2_completed",
                    "data": {
                        "task_list_content": task_list_content,
                        "search_queries": self._serialize_search_queries(result.search_queries),
                        "execution_strategy": self._serialize_execution_strategy(result.execution_strategy),
                        "execution_advice": self._serialize_execution_advice(result.execution_advice),
                    },
                }

                logger.info(f" [Step 2] 搜索任务分解完成，共{len(result.search_queries)}个查询")

            else:
                # 非流式输出
                task_list_content = await self._generate_llm_response(llm, task_prompt)
                structured_data = await self._extract_structured_data(user_input, task_list_content)
                result = self._parse_search_task_list(task_list_content, structured_data)

                #  v7.420: 验证并补充搜索任务
                validated_queries = await self._validate_and_supplement_queries(
                    queries=result.search_queries,
                    output_framework=output_framework,
                    user_input=user_input,
                )

                # 更新结果
                result.search_queries = validated_queries

                yield {
                    "event": "step2_completed",
                    "data": {
                        "task_list_content": task_list_content,
                        "search_queries": self._serialize_search_queries(result.search_queries),
                        "execution_strategy": self._serialize_execution_strategy(result.execution_strategy),
                        "execution_advice": self._serialize_execution_advice(result.execution_advice),
                    },
                }

        except Exception as e:
            import traceback

            logger.error(f" [Step 2] 搜索任务分解失败: {e}")
            logger.error(f"完整异常信息:\n{traceback.format_exc()}")
            yield {"event": "step2_error", "data": {"error": str(e)}}

    def _build_task_decomposition_prompt(
        self,
        user_input: str,
        output_framework: OutputFramework,
        search_directions: Dict[str, List[SearchDirection]] | None = None,
        understanding: Understanding | None = None,  # v2.0 新增
    ) -> str:
        """构建任务分解prompt (v2.0 - 支持搜索方向和 L2/L3 分析结果)"""
        template = self.prompt_config.get("task_decomposition_prompt_template", "")

        # 序列化output_framework
        framework_str = self._format_output_framework(output_framework)

        # v2.0: 序列化search_directions
        directions_str = ""
        if search_directions:
            directions_str = self._format_search_directions(search_directions)

        # v2.0 新增：格式化 L2/L3/人性维度分析结果
        l2_motivations_summary = ""
        l3_tension_summary = ""
        human_dimensions_summary = ""

        if understanding:
            l2_motivations_summary = self._format_l2_motivations_for_step2(understanding)
            l3_tension_summary = self._format_l3_tension_for_step2(understanding)
            human_dimensions_summary = self._format_human_dimensions_for_step2(understanding)

        datetime_info = f"当前日期: {datetime.now().strftime('%Y年%m月%d日')}"

        prompt = template.format(
            datetime_info=datetime_info,
            user_input=user_input,
            output_framework=framework_str,
            search_directions=directions_str,
            l2_motivations_summary=l2_motivations_summary,  # v2.0 新增
            l3_tension_summary=l3_tension_summary,  # v2.0 新增
            human_dimensions_summary=human_dimensions_summary,  # v2.0 新增
        )
        return prompt

    def _format_l2_motivations_for_step2(self, understanding: Understanding) -> str:
        """格式化 L2 动机分析结果供 Step 2 使用（v2.0 新增）"""
        if not understanding or not understanding.l2_motivations:
            return "**L2 动机分析**: 未提供"

        lines = []
        lines.append("**L2 动机分析（用于智能维度选择）**:")
        lines.append("")

        # 按类型分组
        motivation_by_type = {}
        for m in understanding.l2_motivations:
            if m.type not in motivation_by_type:
                motivation_by_type[m.type] = []
            motivation_by_type[m.type].append(m)

        for mot_type, motivations in motivation_by_type.items():
            lines.append(f"**{mot_type}动机**:")
            for m in motivations:
                lines.append(f"  - {m.name}（得分{m.score}）: {m.scenario_expression}")
        lines.append("")

        # 维度选择建议
        lines.append("**基于动机的维度选择建议**:")
        if any(m.type == "精神型" for m in understanding.l2_motivations):
            lines.append("  - 精神型动机 → 【美学溯源】【时代对话】")
        if any(m.type == "情感型" for m in understanding.l2_motivations):
            lines.append("  - 情感型动机 → 【情感锚点】【生活仪式】")
        if any(m.type == "社会型" for m in understanding.l2_motivations):
            lines.append("  - 社会型动机 → 【空间叙事】")
        if any(m.type == "功能型" for m in understanding.l2_motivations):
            lines.append("  - 功能型动机 → 【材质肌理】")

        return "\n".join(lines)

    def _format_l3_tension_for_step2(self, understanding: Understanding) -> str:
        """格式化 L3 核心张力供 Step 2 使用（v2.0 新增）"""
        if not understanding or not understanding.l3_tension:
            return "**L3 核心张力**: 未提供"

        tension = understanding.l3_tension
        lines = []
        lines.append("**L3 核心张力（用于智能维度选择）**:")
        lines.append(f"  - 主导动机: {tension.primary_motivation}")
        lines.append(f"  - 次要动机: {tension.secondary_motivation}")
        lines.append(f"  - 张力公式: {tension.tension_formula}")
        lines.append(f"  - 解决策略: {tension.resolution_strategy}")
        lines.append("")

        # 维度选择建议
        lines.append("**基于张力的维度选择建议**:")
        if "vs" in tension.tension_formula:
            lines.append("  - 对立型张力（vs）→ 【时代对话】研究如何融合对立")
        if "+" in tension.tension_formula:
            lines.append("  - 融合型张力（+）→ 【在地融合】研究如何协同")

        # 隐性洞察
        if tension.hidden_insights:
            lines.append("")
            lines.append("**隐性需求洞察**:")
            for insight in tension.hidden_insights:
                lines.append(f"  - {insight}")

        return "\n".join(lines)

    def _format_human_dimensions_for_step2(self, understanding: Understanding) -> str:
        """格式化人性维度供 Step 2 使用（v2.0 新增）"""
        if not understanding or not understanding.human_dimensions:
            return "**人性维度**: 未启用"

        hd = understanding.human_dimensions
        if not hd.enabled:
            return "**人性维度**: 未启用"

        lines = []
        lines.append("**人性维度分析（用于智能维度选择）**:")
        lines.append("")

        if hd.emotional_landscape:
            lines.append(f"  - 情绪地图: {hd.emotional_landscape}")
        if hd.spiritual_aspirations:
            lines.append(f"  - 精神追求: {hd.spiritual_aspirations}")
        if hd.psychological_safety_needs:
            lines.append(f"  - 心理安全需求: {hd.psychological_safety_needs}")
        if hd.ritual_behaviors:
            lines.append(f"  - 仪式行为: {hd.ritual_behaviors}")
        if hd.memory_anchors:
            lines.append(f"  - 记忆锚点: {hd.memory_anchors}")

        lines.append("")
        lines.append("**基于人性维度的维度选择建议**:")
        if hd.memory_anchors:
            lines.append("  - memory_anchors 非空 → 【情感锚点】")
        if hd.ritual_behaviors:
            lines.append("  - ritual_behaviors 非空 → 【生活仪式】")
        if hd.emotional_landscape:
            lines.append("  - emotional_landscape 非空 → 【光影氛围】")

        return "\n".join(lines)

    def _format_search_directions(self, search_directions: Dict[str, List[SearchDirection]]) -> str:
        """格式化搜索方向为文本 (v2.0 新增)"""
        if not search_directions:
            return ""

        lines = []
        lines.append("## Step 1.5 搜索方向")
        lines.append("")

        for block_id, directions in search_directions.items():
            if not directions:
                continue

            lines.append(f"### 板块 {block_id}")
            for i, direction in enumerate(directions, 1):
                lines.append(f"\n**方向 {i}: {direction.core_theme}**")
                lines.append(f"- **搜索范围**: {direction.search_scope}")
                lines.append(f"- **预期信息类型**: {', '.join(direction.expected_info_types)}")
                lines.append(f"- **关键维度**: {', '.join(direction.key_dimensions)}")
                lines.append(f"- **预期查询数**: {direction.expected_query_count}个")
                lines.append(f"- **用户特征**: {', '.join(direction.user_characteristics)}")
            lines.append("")

        return "\n".join(lines)

    def _format_output_framework(self, framework: OutputFramework) -> str:
        """格式化输出框架为文本 (v2.0: 移除硬编码数量约束，改为智能提示)"""
        lines = []
        lines.append(f"**核心目标**: {framework.core_objective}")
        lines.append(f"**最终交付物类型**: {framework.deliverable_type}")
        lines.append("")
        lines.append("**输出结构**:")
        lines.append("")
        # v7.360: 先列出所有板块ID，方便LLM正确填写serves_blocks
        lines.append("**板块ID列表** (用于serves_blocks字段):")
        for block in framework.blocks:
            lines.append(f"  - {block.id}: {block.name} ({len(block.sub_items)}个子项)")
        lines.append("")

        # v2.0: 移除硬编码数量约束，改为智能提示
        block_count = len(framework.blocks)
        lines.append("=" * 60)
        lines.append("** 设计思维驱动的搜索任务生成**")
        lines.append(f"  - 板块数量: {block_count} 个")
        lines.append("  - 任务数量: 基于 L2 动机和 L3 张力智能确定")
        lines.append("  - 维度选择: 参考上方的 L2/L3/人性维度分析结果")
        lines.append("  - **核心原则**: 每个选定维度生成 1-2 个搜索任务")
        lines.append("=" * 60)
        lines.append("")

        # 详细板块信息
        for block in framework.blocks:
            lines.append(f"\n**板块 {block.id}: {block.name}** ({block.estimated_length})")
            lines.append("  根据 L2 动机和板块主题智能选择搜索维度")
            lines.append("  子项列表（参考，但搜索任务要更详细）：")
            for item in block.sub_items:
                lines.append(f"  - {item.id} {item.name}: {item.description}")

        return "\n".join(lines)

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

    async def _extract_structured_data(self, user_input: str, task_list_content: str) -> Dict[str, Any]:
        """提取结构化数据（JSON）"""
        json_prompt_template = self.prompt_config.get("json_extraction_prompt_template", "")

        datetime_info = f"当前日期: {datetime.now().strftime('%Y年%m月%d日')}"
        json_prompt = json_prompt_template.format(
            datetime_info=datetime_info,
            user_input=user_input,
            task_list_content=task_list_content,
        )

        llm = self.llm_factory.create_llm(temperature=0.3, max_tokens=4000)
        response = await self._generate_llm_response(llm, json_prompt)

        # 解析JSON（v7.333.3 增强健壮性）
        try:
            # 尝试提取 ```json ... ``` 代码块
            json_match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试提取 ``` ... ``` 代码块
                json_match = re.search(r"```\s*(.*?)\s*```", response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    # 尝试直接匹配 { ... } JSON 对象
                    json_match = re.search(r"\{[\s\S]*\}", response)
                    if json_match:
                        json_str = json_match.group(0)
                    else:
                        json_str = response

            # 清理常见问题
            json_str = json_str.strip()
            # 移除可能的 BOM 或其他不可见字符
            json_str = json_str.lstrip("\ufeff")

            structured_data = json.loads(json_str)
            logger.info(f" [Step 2] JSON 解析成功，提取到 {len(structured_data.get('search_queries', []))} 个查询")
            return structured_data
        except json.JSONDecodeError as e:
            logger.error(f" [Step 2] JSON解析失败: {e}")
            logger.debug(f"原始响应前200字符: {response[:200]}")

            # v7.333.4: 返回空结构而非抛出异常，让流程继续
            logger.warning("️ [Step 2] 使用空结构继续，后续将从 task_list_content 解析")
            return {
                "search_queries": [],
                "execution_strategy": {},
                "execution_advice": {},
            }
        except Exception as e:
            import traceback

            logger.error(f" [Step 2] JSON提取/解析时发生意外错误: {e}")
            logger.error(f"完整异常信息:\n{traceback.format_exc()}")
            # 返回空结构继续流程
            return {
                "search_queries": [],
                "execution_strategy": {},
                "execution_advice": {},
            }

    def _parse_search_task_list(self, task_list_content: str, structured_data: Dict[str, Any]) -> SearchTaskList:
        """解析为SearchTaskList对象"""
        # 解析search_queries
        queries = []
        for query_data in structured_data.get("search_queries", []):
            queries.append(
                SearchQuery(
                    id=query_data.get("id", ""),
                    query=query_data.get("query", ""),
                    serves_blocks=query_data.get("serves_blocks", []),
                    expected_output=query_data.get("expected_output", ""),
                    search_keywords=query_data.get("search_keywords", []),
                    success_criteria=query_data.get("success_criteria", ""),
                    priority=query_data.get("priority", 1),
                    dependencies=query_data.get("dependencies", []),
                    can_parallel_with=query_data.get("can_parallel_with", []),
                    status="pending",
                )
            )

        # 解析execution_strategy
        strategy_data = structured_data.get("execution_strategy", {})
        execution_strategy = ExecutionStrategy(
            priority_1_queries=strategy_data.get("priority_1_queries", []),
            priority_2_queries=strategy_data.get("priority_2_queries", []),
            priority_3_queries=strategy_data.get("priority_3_queries", []),
            parallel_groups=strategy_data.get("parallel_groups", []),
        )

        # 解析execution_advice
        advice_data = structured_data.get("execution_advice", {})
        execution_advice = ExecutionAdvice(
            overall_strategy=advice_data.get("overall_strategy", ""),
            key_success_factors=advice_data.get("key_success_factors", ""),
            risk_alerts=advice_data.get("risk_alerts", ""),
        )

        return SearchTaskList(
            search_queries=queries,
            execution_strategy=execution_strategy,
            execution_advice=execution_advice,
            metadata=structured_data.get("metadata", {}),
        )

    async def _validate_and_supplement_queries(
        self,
        queries: List[SearchQuery],
        output_framework: OutputFramework,
        user_input: str,
    ) -> List[SearchQuery]:
        """
        验证搜索任务数量并自动补充不足的任务（v7.420新增）

        核心逻辑：
        1. 统计每个板块的搜索任务数量
        2. 如果某个板块任务数少于3个，自动生成补充任务
        3. 确保所有板块都有充分的搜索覆盖

        Args:
            queries: 原始搜索查询列表
            output_framework: 输出框架
            user_input: 用户输入

        Returns:
            补充后的搜索查询列表
        """
        logger.info(" [Step 2 验证] 开始验证搜索任务数量...")

        # 1. 统计每个板块的搜索任务数量
        block_query_count = {}
        block_queries = {}

        for block in output_framework.blocks:
            block_query_count[block.id] = 0
            block_queries[block.id] = []

        for query in queries:
            for block_id in query.serves_blocks:
                if block_id in block_query_count:
                    block_query_count[block_id] += 1
                    block_queries[block_id].append(query)

        # 2. 检查并报告
        insufficient_blocks = []
        for block in output_framework.blocks:
            count = block_query_count.get(block.id, 0)
            logger.info(f"   板块 {block.id} ({block.name}): {count} 个搜索任务")

            if count < 3:
                insufficient_blocks.append(block)
                logger.warning(f"   ️ 板块 {block.id} 任务不足（{count}<3），需要补充")

        # 3. 如果有不足的板块，生成补充任务
        supplementary_queries = []
        if insufficient_blocks:
            logger.info(f" [Step 2 验证] 开始为 {len(insufficient_blocks)} 个板块生成补充任务...")

            for block in insufficient_blocks:
                current_count = block_query_count.get(block.id, 0)
                needed_count = 3 - current_count

                logger.info(f"   为板块 {block.id} 生成 {needed_count} 个补充任务...")

                # 生成补充任务
                block_supp_queries = await self._generate_supplementary_queries_for_block(
                    block=block,
                    existing_queries=block_queries.get(block.id, []),
                    needed_count=needed_count,
                    user_input=user_input,
                )

                supplementary_queries.extend(block_supp_queries)
                logger.info(f"    已生成 {len(block_supp_queries)} 个补充任务")

        # 4. 合并原始任务和补充任务
        all_queries = queries + supplementary_queries

        logger.info(" [Step 2 验证] 验证完成")
        logger.info(f"   原始任务: {len(queries)} 个")
        logger.info(f"   补充任务: {len(supplementary_queries)} 个")
        logger.info(f"   总计任务: {len(all_queries)} 个")

        return all_queries

    async def _generate_supplementary_queries_for_block(
        self,
        block: OutputBlock,
        existing_queries: List[SearchQuery],
        needed_count: int,
        user_input: str,
    ) -> List[SearchQuery]:
        """
        为单个板块生成补充搜索任务

        Args:
            block: 板块对象
            existing_queries: 该板块现有的搜索任务
            needed_count: 需要补充的任务数量
            user_input: 用户输入

        Returns:
            补充搜索任务列表
        """
        # 构建prompt
        existing_queries_text = (
            "\n".join([f"- {q.query}" for q in existing_queries]) if existing_queries else "（当前没有搜索任务）"
        )

        sub_items_text = "\n".join([f"- {item.id} {item.name}: {item.description}" for item in block.sub_items])

        prompt = f"""你是一位资深的信息检索专家。以下板块的搜索任务不足，需要补充。

## 板块信息

**板块ID**: {block.id}
**板块名称**: {block.name}
**板块长度**: {block.estimated_length}
**用户特征**: {', '.join(block.user_characteristics)}

**子项列表**:
{sub_items_text}

## 用户问题
"{user_input}"

## 现有搜索任务
{existing_queries_text}

## 任务

请为此板块生成 {needed_count} 个**深度挖掘**的补充搜索任务。

**要求**:
1. 不要重复现有任务的内容
2. 从不同维度扩展：理论基础、案例参考、技术细节、用户洞察、趋势动态、对比分析
3. 查询必须高度具体化，包含用户关键特征
4. 查询可以直接用于搜索引擎

**输出格式（JSON）**:

```json
{{
  "supplementary_queries": [
    {{
      "query": "具体查询内容（必须包含用户关键特征）",
      "expected_output": "预期输出说明",
      "search_keywords": ["关键词1", "关键词2", "关键词3"],
      "success_criteria": "成功标准",
      "dimension": "理论基础/案例参考/技术细节/用户洞察/趋势动态/对比分析"
    }}
  ]
}}
```

请只输出JSON，不要有其他内容。"""

        # 调用LLM（v7.421: 提升temperature到0.6以提升补充任务的多样性）
        llm = self.llm_factory.create_llm(temperature=0.6, max_tokens=2000)

        try:
            response = await llm.ainvoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)

            # 解析JSON
            json_match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match = re.search(r"\{[\s\S]*\}", content)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    json_str = content

            data = json.loads(json_str.strip())

            # 构建SearchQuery对象
            supplementary_queries = []
            existing_query_count = len(existing_queries)

            for i, query_data in enumerate(data.get("supplementary_queries", []), 1):
                query_id = f"query_{block.id.split('_')[-1]}_{existing_query_count + i}_supp"

                supplementary_queries.append(
                    SearchQuery(
                        id=query_id,
                        query=query_data.get("query", ""),
                        serves_blocks=[block.id],
                        expected_output=query_data.get("expected_output", ""),
                        search_keywords=query_data.get("search_keywords", []),
                        success_criteria=query_data.get("success_criteria", ""),
                        priority=2,  # 补充任务优先级为2
                        dependencies=[],
                        can_parallel_with=[],
                        status="pending",
                    )
                )

            return supplementary_queries

        except Exception as e:
            logger.error(f" 生成补充任务失败: {e}")
            # 降级策略：生成简单的补充任务
            return self._fallback_supplementary_queries(block, existing_queries, needed_count)

    def _fallback_supplementary_queries(
        self,
        block: OutputBlock,
        existing_queries: List[SearchQuery],
        needed_count: int,
    ) -> List[SearchQuery]:
        """
        降级策略：生成简单的补充任务

        当LLM生成失败时使用
        """
        logger.warning("️ 使用降级策略生成补充任务")

        supplementary_queries = []
        existing_query_count = len(existing_queries)

        # 预定义的补充任务模板（基于多维度）
        dimensions = [
            ("理论基础", f"{block.name}的设计原则和理论基础", ["设计原则", "理论", "方法论"]),
            ("案例参考", f"{block.name}的实际案例和成功经验", ["案例", "成功经验", "实践"]),
            ("技术细节", f"{block.name}的具体实现方法和技术细节", ["实现方法", "技术", "工艺"]),
            ("用户洞察", f"{block.name}的用户需求和痛点分析", ["用户需求", "痛点", "行为模式"]),
            ("趋势动态", f"{block.name}的行业趋势和创新方向", ["趋势", "创新", "展望"]),
        ]

        for i in range(min(needed_count, len(dimensions))):
            dim_name, query_template, keywords = dimensions[i]
            query_id = f"query_{block.id.split('_')[-1]}_{existing_query_count + i + 1}_supp"

            # 添加用户特征
            user_chars_str = " ".join(block.user_characteristics[:2]) if block.user_characteristics else ""
            if user_chars_str:
                query_text = f"{user_chars_str} {query_template}"
            else:
                query_text = query_template

            supplementary_queries.append(
                SearchQuery(
                    id=query_id,
                    query=query_text,
                    serves_blocks=[block.id],
                    expected_output=f"从{dim_name}角度补充{block.name}的相关信息",
                    search_keywords=keywords + block.user_characteristics[:1],
                    success_criteria=f"找到与{dim_name}相关的有价值信息",
                    priority=2,
                    dependencies=[],
                    can_parallel_with=[],
                    status="pending",
                )
            )

        return supplementary_queries

    def _serialize_search_queries(self, queries: List[SearchQuery]) -> List[Dict[str, Any]]:
        """序列化搜索查询列表"""
        return [
            {
                "id": q.id,
                "query": q.query,
                "serves_blocks": q.serves_blocks,
                "expected_output": q.expected_output,
                "search_keywords": q.search_keywords,
                "success_criteria": q.success_criteria,
                "priority": q.priority,
                "dependencies": q.dependencies,
                "can_parallel_with": q.can_parallel_with,
                "status": q.status,
            }
            for q in queries
        ]

    def _serialize_execution_strategy(self, strategy: ExecutionStrategy | None) -> Dict[str, Any] | None:
        """序列化执行策略"""
        if not strategy:
            return None
        return {
            "priority_1_queries": strategy.priority_1_queries,
            "priority_2_queries": strategy.priority_2_queries,
            "priority_3_queries": strategy.priority_3_queries,
            "parallel_groups": strategy.parallel_groups,
        }

    def _serialize_execution_advice(self, advice: ExecutionAdvice | None) -> Dict[str, Any] | None:
        """序列化执行建议"""
        if not advice:
            return None
        return {
            "overall_strategy": advice.overall_strategy,
            "key_success_factors": advice.key_success_factors,
            "risk_alerts": advice.risk_alerts,
        }


# ============================================================================
# Step 3: 智能搜索执行器
# ============================================================================


class Step3IntelligentSearchExecutor:
    """Step 3: 智能搜索执行器（含动态增补）"""

    def __init__(self, llm_factory: LLMFactory, search_service=None):
        self.llm_factory = llm_factory
        self.search_service = search_service or (get_ai_search_service() if SEARCH_SERVICE_AVAILABLE else None)
        self.prompt_config = PromptLoader.load_prompt_config("step3_search_result_analysis.yaml")

    async def execute(
        self,
        search_queries: List[SearchQuery],
        output_framework: OutputFramework,
        config: SearchExecutionConfig,
        stream: bool = True,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        执行Step 3智能搜索

        Args:
            search_queries: 搜索查询列表
            output_framework: 输出框架
            config: 搜索执行配置
            stream: 是否流式输出

        Yields:
            SSE事件字典
        """
        logger.info(f" [Step 3] 开始智能搜索执行，共{len(search_queries)}个查询...")

        if not self.search_service:
            logger.error(" 搜索服务不可用")
            yield {"event": "step3_error", "data": {"error": "搜索服务不可用"}}
            return

        try:
            all_queries = search_queries.copy()
            executed_queries = []
            supplementary_queries = []
            framework_additions = []
            search_results = {}

            query_count = 0
            total_queries = len(all_queries)

            # 按优先级执行查询
            while all_queries and query_count < config.max_total_queries_multiplier * total_queries:
                current_query = all_queries.pop(0)
                query_count += 1

                # 发送搜索开始事件
                yield {
                    "event": "step3_query_start",
                    "data": {
                        "query_id": current_query.id,
                        "query": current_query.query,
                        "progress": f"{query_count}/{total_queries}",
                    },
                }

                # 执行搜索
                results = await self._execute_single_query(current_query)
                search_results[current_query.id] = results
                executed_queries.append(current_query.id)

                # 发送搜索结果事件
                yield {
                    "event": "step3_query_completed",
                    "data": {
                        "query_id": current_query.id,
                        "result_count": len(results),
                        "results": self._serialize_search_results(results[:5]),  # 只发送前5条
                    },
                }

                # 分析搜索结果，生成补充查询
                if config.enable_dynamic_supplementary:
                    analysis = await self._analyze_search_results(
                        current_query, results, output_framework, executed_queries
                    )

                    if analysis.supplementary_queries:
                        # 过滤和添加补充查询
                        for supp_query in analysis.supplementary_queries:
                            if self._should_execute_supplementary(supp_query, config):
                                # 转换为SearchQuery
                                search_query = SearchQuery(
                                    id=supp_query.id,
                                    query=supp_query.query,
                                    serves_blocks=supp_query.serves_blocks,
                                    expected_output=supp_query.expected_output,
                                    search_keywords=supp_query.search_keywords,
                                    success_criteria=supp_query.success_criteria,
                                    priority=(1 if supp_query.priority == Priority.HIGH else 2),
                                    dependencies=[],
                                    can_parallel_with=[],
                                    status="pending",
                                )
                                all_queries.append(search_query)
                                supplementary_queries.append(supp_query)

                                # 发送补充查询事件
                                yield {
                                    "event": "step3_supplementary_added",
                                    "data": {
                                        "parent_query_id": current_query.id,
                                        "supplementary_query": {
                                            "id": supp_query.id,
                                            "query": supp_query.query,
                                            "reason": supp_query.reason,
                                            "priority": supp_query.priority.value,
                                        },
                                    },
                                }

                    # 收集框架增补建议
                    if config.enable_framework_additions and analysis.framework_additions:
                        framework_additions.extend(analysis.framework_additions)

                # 检查是否超时
                if query_count >= config.max_total_queries_multiplier * total_queries:
                    logger.warning("️ 达到最大查询数限制")
                    break

            # 发送搜索完成事件
            yield {
                "event": "step3_completed",
                "data": {
                    "total_queries": query_count,
                    "original_queries": total_queries,
                    "supplementary_queries": len(supplementary_queries),
                    "framework_additions": [
                        {
                            "block_name": fa.block_name,
                            "reason": fa.reason,
                            "importance": fa.importance.value,
                            "sub_items": fa.sub_items,
                        }
                        for fa in framework_additions
                    ],
                    "search_results": {
                        query_id: self._serialize_search_results(results)
                        for query_id, results in search_results.items()
                    },
                },
            }

            logger.info(f" [Step 3] 智能搜索完成，共执行{query_count}个查询")

        except Exception as e:
            logger.error(f" [Step 3] 智能搜索失败: {e}")
            yield {"event": "step3_error", "data": {"error": str(e)}}

    async def _execute_single_query(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """执行单个搜索查询"""
        try:
            # 使用搜索服务执行查询
            search_result = await self.search_service.search(query.query)

            # 转换为统一格式
            results = []
            if hasattr(search_result, "sources"):
                for source in search_result.sources[:20]:  # 最多返回20条
                    results.append(
                        {
                            "title": source.title,
                            "url": source.url,
                            "snippet": source.snippet,
                            "site_name": source.site_name,
                            "date_published": source.date_published,
                        }
                    )

            return results
        except Exception as e:
            logger.error(f" 搜索查询失败 {query.id}: {e}")
            return []

    async def _analyze_search_results(
        self,
        current_query: SearchQuery,
        results: List[Dict[str, Any]],
        output_framework: OutputFramework,
        executed_queries: List[str],
    ) -> SearchResultAnalysis:
        """分析搜索结果，生成补充查询"""
        try:
            # 构建分析prompt
            analysis_prompt = self._build_result_analysis_prompt(
                current_query, results, output_framework, executed_queries
            )

            # 调用LLM分析
            llm = self.llm_factory.create_llm(temperature=0.5, max_tokens=2000)
            response = await llm.ainvoke(analysis_prompt)
            analysis_content = response.content

            # 提取结构化数据
            structured_data = await self._extract_analysis_structured_data(analysis_content)

            # 解析为SearchResultAnalysis
            return self._parse_search_result_analysis(current_query.id, structured_data)

        except Exception as e:
            logger.error(f" 搜索结果分析失败: {e}")
            # 返回空分析
            return SearchResultAnalysis(
                current_query_id=current_query.id,
                quality_assessment=QualityAssessment(
                    score=50,
                    completeness="medium",
                    relevance="medium",
                    authority="medium",
                    timeliness="medium",
                    actionability="medium",
                ),
                should_execute=False,
            )

    def _build_result_analysis_prompt(
        self,
        current_query: SearchQuery,
        results: List[Dict[str, Any]],
        output_framework: OutputFramework,
        executed_queries: List[str],
    ) -> str:
        """构建搜索结果分析prompt"""
        template = self.prompt_config.get("result_analysis_prompt_template", "")

        # 格式化搜索结果
        results_str = "\n".join(
            [
                f"{i+1}. {r['title']}\n   URL: {r['url']}\n   摘要: {r['snippet'][:200]}..."
                for i, r in enumerate(results[:10])
            ]
        )

        # 格式化输出框架
        framework_str = self._format_output_framework(output_framework)

        # 格式化已执行查询
        executed_str = ", ".join(executed_queries)

        datetime_info = f"当前日期: {datetime.now().strftime('%Y年%m月%d日')}"

        prompt = template.format(
            datetime_info=datetime_info,
            current_query=current_query.query,
            result_count=len(results),
            search_results=results_str,
            output_framework=framework_str,
            executed_queries=executed_str,
        )
        return prompt

    def _format_output_framework(self, framework: OutputFramework) -> str:
        """格式化输出框架为文本"""
        lines = []
        for block in framework.blocks:
            lines.append(f"- {block.name}")
        return "\n".join(lines)

    async def _extract_analysis_structured_data(self, analysis_content: str) -> Dict[str, Any]:
        """提取分析的结构化数据"""
        json_prompt_template = self.prompt_config.get("json_extraction_prompt_template", "")

        datetime_info = f"当前日期: {datetime.now().strftime('%Y年%m月%d日')}"
        json_prompt = json_prompt_template.format(datetime_info=datetime_info, analysis_content=analysis_content)

        llm = self.llm_factory.create_llm(temperature=0.3, max_tokens=2000)
        response = await llm.ainvoke(json_prompt)

        # 解析JSON
        try:
            json_match = re.search(r"```json\s*(.*?)\s*```", response.content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response.content

            structured_data = json.loads(json_str)
            return structured_data
        except json.JSONDecodeError as e:
            logger.error(f" JSON解析失败: {e}")
            return {}

    def _parse_search_result_analysis(self, query_id: str, structured_data: Dict[str, Any]) -> SearchResultAnalysis:
        """解析为SearchResultAnalysis对象"""
        # 解析quality_assessment
        qa_data = structured_data.get("quality_assessment", {})
        quality_assessment = QualityAssessment(
            score=qa_data.get("score", 50),
            completeness=qa_data.get("completeness", "medium"),
            relevance=qa_data.get("relevance", "medium"),
            authority=qa_data.get("authority", "medium"),
            timeliness=qa_data.get("timeliness", "medium"),
            actionability=qa_data.get("actionability", "medium"),
            issues=qa_data.get("issues", []),
        )

        # 解析discoveries
        discoveries = []
        for disc_data in structured_data.get("discoveries", []):
            discoveries.append(
                Discovery(
                    type=TriggerType(disc_data.get("type", "insufficient_info")),
                    description=disc_data.get("description", ""),
                    importance=Priority(disc_data.get("importance", "medium")),
                )
            )

        # 解析supplementary_queries
        supp_queries = []
        for sq_data in structured_data.get("supplementary_queries", []):
            supp_queries.append(
                SupplementaryQuery(
                    id=sq_data.get("id", ""),
                    query=sq_data.get("query", ""),
                    reason=sq_data.get("reason", ""),
                    trigger_type=TriggerType(sq_data.get("trigger_type", "insufficient_info")),
                    priority=Priority(sq_data.get("priority", "medium")),
                    serves_blocks=sq_data.get("serves_blocks", []),
                    expected_output=sq_data.get("expected_output", ""),
                    search_keywords=sq_data.get("search_keywords", []),
                    success_criteria=sq_data.get("success_criteria", ""),
                    parent_query_id=query_id,
                )
            )

        # 解析framework_additions
        additions = []
        for fa_data in structured_data.get("framework_additions", []):
            additions.append(
                FrameworkAddition(
                    block_name=fa_data.get("block_name", ""),
                    reason=fa_data.get("reason", ""),
                    importance=Priority(fa_data.get("importance", "medium")),
                    sub_items=fa_data.get("sub_items", []),
                    source=fa_data.get("source", ""),
                )
            )

        # 解析execution_advice
        advice_data = structured_data.get("execution_advice", {})

        return SearchResultAnalysis(
            current_query_id=query_id,
            quality_assessment=quality_assessment,
            discoveries=discoveries,
            supplementary_queries=supp_queries,
            framework_additions=additions,
            should_execute=advice_data.get("should_execute", True),
            execution_order=advice_data.get("execution_order", []),
            expected_value=advice_data.get("expected_value", ""),
        )

    def _should_execute_supplementary(self, supp_query: SupplementaryQuery, config: SearchExecutionConfig) -> bool:
        """判断是否应该执行补充查询"""
        # 检查优先级
        if supp_query.priority.value not in config.auto_execute_priority:
            return False

        # TODO: 检查相似度（避免重复）

        return True

    def _serialize_search_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """序列化搜索结果"""
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("snippet", "")[:200],
                "site_name": r.get("site_name", ""),
            }
            for r in results
        ]


# ============================================================================
# Step 4: 总结生成执行器
# ============================================================================


class Step4SummaryGenerationExecutor:
    """Step 4: 总结生成执行器"""

    def __init__(self, llm_factory: LLMFactory):
        self.llm_factory = llm_factory
        self.prompt_config = PromptLoader.load_prompt_config("step4_summary_generation.yaml")

    async def execute(
        self,
        user_input: str,
        output_framework: OutputFramework,
        search_results: Dict[str, List[Dict[str, Any]]],
        framework_additions: List[FrameworkAddition],
        stream: bool = True,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        执行Step 4总结生成

        Args:
            user_input: 用户输入
            output_framework: 输出框架
            search_results: 搜索结果字典
            framework_additions: 框架增补建议
            stream: 是否流式输出

        Yields:
            SSE事件字典
        """
        logger.info(" [Step 4] 开始总结生成...")

        try:
            # 1. 构建prompt
            summary_prompt = self._build_summary_prompt(
                user_input, output_framework, search_results, framework_additions
            )

            # 2. 调用LLM生成总结
            llm = self.llm_factory.create_llm(temperature=0.7, max_tokens=6000)

            if stream:
                # 流式输出
                summary_content = ""
                async for chunk in self._stream_llm_response(llm, summary_prompt):
                    summary_content += chunk
                    yield {
                        "event": "step4_summary_chunk",
                        "data": {"chunk": chunk, "accumulated": summary_content},
                    }

                # 3. 提取结构化元数据
                yield {"event": "step4_extracting_metadata", "data": {}}
                metadata = await self._extract_summary_metadata(summary_content)

                yield {
                    "event": "step4_completed",
                    "data": {"summary_content": summary_content, "metadata": metadata},
                }

                logger.info(" [Step 4] 总结生成完成")

            else:
                # 非流式输出
                summary_content = await self._generate_llm_response(llm, summary_prompt)
                metadata = await self._extract_summary_metadata(summary_content)

                yield {
                    "event": "step4_completed",
                    "data": {"summary_content": summary_content, "metadata": metadata},
                }

        except Exception as e:
            logger.error(f" [Step 4] 总结生成失败: {e}")
            yield {"event": "step4_error", "data": {"error": str(e)}}

    def _build_summary_prompt(
        self,
        user_input: str,
        output_framework: OutputFramework,
        search_results: Dict[str, List[Dict[str, Any]]],
        framework_additions: List[FrameworkAddition],
    ) -> str:
        """构建总结生成prompt"""
        template = self.prompt_config.get("summary_generation_prompt_template", "")

        # 格式化输出框架
        framework_str = self._format_output_framework(output_framework)

        # 格式化搜索结果
        results_str = self._format_search_results(search_results)

        # 格式化框架增补
        additions_str = self._format_framework_additions(framework_additions)

        datetime_info = f"当前日期: {datetime.now().strftime('%Y年%m月%d日')}"

        prompt = template.format(
            datetime_info=datetime_info,
            user_input=user_input,
            output_framework=framework_str,
            result_count=sum(len(results) for results in search_results.values()),
            search_results=results_str,
            framework_additions=additions_str,
        )
        return prompt

    def _format_output_framework(self, framework: OutputFramework) -> str:
        """格式化输出框架"""
        lines = []
        lines.append(f"**核心目标**: {framework.core_objective}")
        lines.append(f"**交付物类型**: {framework.deliverable_type}")
        lines.append("\n**板块结构**:")
        for block in framework.blocks:
            lines.append(f"\n{block.name} ({block.estimated_length})")
            for item in block.sub_items:
                lines.append(f"  - {item.name}: {item.description}")
        return "\n".join(lines)

    def _format_search_results(self, search_results: Dict[str, List[Dict[str, Any]]]) -> str:
        """格式化搜索结果"""
        lines = []
        source_num = 1
        for _query_id, results in search_results.items():
            for result in results[:5]:  # 每个查询最多5条
                lines.append(
                    f"[{source_num}] {result.get('title', '')}\n"
                    f"    URL: {result.get('url', '')}\n"
                    f"    摘要: {result.get('snippet', '')[:300]}..."
                )
                source_num += 1
        return "\n\n".join(lines)

    def _format_framework_additions(self, additions: List[FrameworkAddition]) -> str:
        """格式化框架增补"""
        if not additions:
            return "无"

        lines = []
        for addition in additions:
            lines.append(f"**{addition.block_name}** ({addition.importance.value})")
            lines.append(f"原因: {addition.reason}")
            lines.append("建议子项:")
            for item in addition.sub_items:
                lines.append(f"  - {item}")
        return "\n\n".join(lines)

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

    async def _extract_summary_metadata(self, summary_content: str) -> Dict[str, Any]:
        """提取总结的元数据"""
        # TODO: 实现元数据提取
        return {
            "total_words": len(summary_content),
            "generation_time": datetime.now().isoformat(),
        }


# ============================================================================
# 主编排器
# ============================================================================


class FourStepFlowOrchestrator:
    """4步骤流程编排器 (v2.0 - 支持 Step 1.5 搜索方向生成)"""

    def __init__(self):
        self.llm_factory = LLMFactory()
        self.step1_executor = Step1DeepAnalysisExecutor(self.llm_factory)
        self.step2_executor = Step2SearchTaskDecompositionExecutor(self.llm_factory)
        self.step3_executor = Step3IntelligentSearchExecutor(self.llm_factory)
        self.step4_executor = Step4SummaryGenerationExecutor(self.llm_factory)

        # v2.0: 新增 Step 1.5 搜索方向生成器
        try:
            step1_5_config = PromptLoader.load_prompt_config("step1_5_direction_generation.yaml")
            self.search_direction_generator = SearchDirectionGenerator(self.llm_factory, step1_5_config)
            logger.info(" Step 1.5 搜索方向生成器初始化成功")
        except Exception as e:
            logger.warning(f"️ Step 1.5 搜索方向生成器初始化失败: {e}，将跳过 Step 1.5")
            self.search_direction_generator = None

    async def execute_flow(
        self, user_input: str, config: SearchExecutionConfig | None = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        执行完整的4步骤流程

        Args:
            user_input: 用户输入
            config: 搜索执行配置

        Yields:
            SSE事件字典
        """
        logger.info(" 开始执行4步骤搜索流程...")

        # 初始化状态
        state = FourStepFlowState(config=config or SearchExecutionConfig())

        try:
            # ================================================================
            # Step 1: 深度分析
            # ================================================================
            yield {"event": "flow_step_start", "data": {"step": 1, "name": "深度分析"}}

            step1_result = None
            async for event in self.step1_executor.execute(user_input, stream=True):
                yield event
                if event["event"] == "step1_completed":
                    step1_result = event["data"]
                    state.step1_completed = True

            if not step1_result:
                raise Exception("Step 1未能完成")

            # 等待用户确认/编辑输出框架
            yield {
                "event": "flow_waiting_user_confirmation",
                "data": {
                    "step": 1,
                    "message": "请查看深度分析结果，确认或编辑输出框架",
                    "editable_data": step1_result["output_framework"],
                },
            }

            # TODO: 实际实现中需要等待用户输入
            # 这里假设用户直接确认

            # ================================================================
            # Step 1.5: 搜索方向生成 (v2.0 新增)
            # ================================================================
            search_directions = {}
            if self.search_direction_generator:
                logger.info(" [Step 1.5] 开始搜索方向生成...")
                yield {
                    "event": "flow_step_start",
                    "data": {"step": 1.5, "name": "搜索方向生成"},
                }

                # 重建OutputFramework对象
                output_framework = self._rebuild_output_framework(step1_result["output_framework"])
                logger.info(f" [Step 1.5] 输出框架包含 {len(output_framework.blocks)} 个板块")

                # 重建Understanding对象
                understanding = self._rebuild_understanding(step1_result.get("understanding", {}))
                logger.debug(" [Step 1.5] Understanding 重建完成")

                # 为每个板块生成搜索方向
                for i, block in enumerate(output_framework.blocks):
                    logger.info(f" [Step 1.5] 处理板块 {i+1}/{len(output_framework.blocks)}: {block.name[:30]}...")
                    try:
                        directions = await self.search_direction_generator.generate_directions(
                            block=block, understanding=understanding, block_index=i
                        )
                        search_directions[block.id] = directions

                        # 发送进度事件
                        yield {
                            "event": "step1_5_direction_generated",
                            "data": {
                                "block_id": block.id,
                                "block_name": block.name,
                                "directions": [self._direction_to_dict(d) for d in directions],
                                "progress": f"{i+1}/{len(output_framework.blocks)}",
                            },
                        }
                        logger.info(f" [Step 1.5] 板块 {block.id} 生成 {len(directions)} 个搜索方向")
                        for j, d in enumerate(directions):
                            logger.debug(f"   方向 {j+1}: {d.core_theme[:40]}...")
                    except Exception as e:
                        logger.error(f" [Step 1.5] 板块 {block.id} 搜索方向生成失败: {e}", exc_info=True)
                        # 继续处理其他板块

                total_directions = sum(len(dirs) for dirs in search_directions.values())
                yield {
                    "event": "step1_5_completed",
                    "data": {
                        "search_directions": {
                            block_id: [self._direction_to_dict(d) for d in dirs]
                            for block_id, dirs in search_directions.items()
                        },
                        "total_directions": total_directions,
                    },
                }
                state.step1_5_completed = True
                logger.info(f" [Step 1.5] 搜索方向生成完成 | 板块数: {len(search_directions)} | 方向总数: {total_directions}")
            else:
                # 如果没有搜索方向生成器，重建OutputFramework对象
                output_framework = self._rebuild_output_framework(step1_result["output_framework"])
                logger.warning("️ [Step 1.5] 跳过搜索方向生成（生成器未初始化）")

            # ================================================================
            # Step 2: 搜索任务分解
            # ================================================================
            logger.info(" [Step 2] 开始搜索任务分解...")
            logger.info(f" [Step 2] 搜索方向数量: {len(search_directions) if search_directions else 0}")
            yield {
                "event": "flow_step_start",
                "data": {"step": 2, "name": "搜索任务分解"},
            }

            # v2.0: 传递搜索方向给 Step 2
            step2_result = None
            async for event in self.step2_executor.execute(
                user_input,
                output_framework,
                search_directions=search_directions if search_directions else None,
                stream=True,
            ):
                yield event
                if event["event"] == "step2_completed":
                    step2_result = event["data"]
                    state.step2_completed = True
                    query_count = len(step2_result.get("search_queries", []))
                    logger.info(f" [Step 2] 搜索任务分解完成 | 查询数量: {query_count}")

            if not step2_result:
                raise Exception("Step 2未能完成")

            # 等待用户确认/编辑搜索查询
            yield {
                "event": "flow_waiting_user_confirmation",
                "data": {
                    "step": 2,
                    "message": "请查看搜索任务清单，确认或编辑查询",
                    "editable_data": step2_result["search_queries"],
                },
            }

            # TODO: 实际实现中需要等待用户输入
            # 这里假设用户直接确认

            # ================================================================
            # Step 3: 智能搜索执行
            # ================================================================
            yield {
                "event": "flow_step_start",
                "data": {"step": 3, "name": "智能搜索执行"},
            }

            # 重建SearchQuery对象列表
            search_queries = self._rebuild_search_queries(step2_result["search_queries"])

            step3_result = None
            async for event in self.step3_executor.execute(search_queries, output_framework, state.config, stream=True):
                yield event
                if event["event"] == "step3_completed":
                    step3_result = event["data"]
                    state.step3_completed = True

            if not step3_result:
                raise Exception("Step 3未能完成")

            # 如果有框架增补建议，等待用户确认
            if step3_result.get("framework_additions"):
                yield {
                    "event": "flow_waiting_user_confirmation",
                    "data": {
                        "step": 3,
                        "message": "发现新的重要方向，是否增补输出框架？",
                        "editable_data": step3_result["framework_additions"],
                    },
                }

                # TODO: 实际实现中需要等待用户输入
                # 这里假设用户接受增补

            # ================================================================
            # Step 4: 总结生成
            # ================================================================
            yield {"event": "flow_step_start", "data": {"step": 4, "name": "总结生成"}}

            # 重建FrameworkAddition对象列表
            framework_additions = self._rebuild_framework_additions(step3_result.get("framework_additions", []))

            step4_result = None
            async for event in self.step4_executor.execute(
                user_input,
                output_framework,
                step3_result["search_results"],
                framework_additions,
                stream=True,
            ):
                yield event
                if event["event"] == "step4_completed":
                    step4_result = event["data"]
                    state.step4_completed = True

            if not step4_result:
                raise Exception("Step 4未能完成")

            # ================================================================
            # 流程完成
            # ================================================================
            yield {
                "event": "flow_completed",
                "data": {
                    "message": "4步骤流程完成",
                    "summary": step4_result["summary_content"],
                    "metadata": step4_result.get("metadata", {}),
                },
            }

            logger.info(" 4步骤流程完成")

        except Exception as e:
            logger.error(f" 4步骤流程执行失败: {e}")
            yield {"event": "flow_error", "data": {"error": str(e)}}

    def _rebuild_output_framework(self, framework_data: Dict[str, Any]) -> OutputFramework:
        """从序列化数据重建OutputFramework对象"""
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

        return OutputFramework(
            core_objective=framework_data.get("core_objective", ""),
            deliverable_type=framework_data.get("deliverable_type", ""),
            blocks=blocks,
            quality_standards=framework_data.get("quality_standards", []),
        )

    def _rebuild_search_queries(self, queries_data: List[Dict[str, Any]]) -> List[SearchQuery]:
        """从序列化数据重建SearchQuery对象列表"""
        queries = []
        for query_data in queries_data:
            queries.append(
                SearchQuery(
                    id=query_data.get("id", ""),
                    query=query_data.get("query", ""),
                    serves_blocks=query_data.get("serves_blocks", []),
                    expected_output=query_data.get("expected_output", ""),
                    search_keywords=query_data.get("search_keywords", []),
                    success_criteria=query_data.get("success_criteria", ""),
                    priority=query_data.get("priority", 1),
                    dependencies=query_data.get("dependencies", []),
                    can_parallel_with=query_data.get("can_parallel_with", []),
                    status=query_data.get("status", "pending"),
                )
            )
        return queries

    def _rebuild_framework_additions(self, additions_data: List[Dict[str, Any]]) -> List[FrameworkAddition]:
        """从序列化数据重建FrameworkAddition对象列表"""
        additions = []
        for addition_data in additions_data:
            additions.append(
                FrameworkAddition(
                    block_name=addition_data.get("block_name", ""),
                    reason=addition_data.get("reason", ""),
                    importance=Priority(addition_data.get("importance", "medium")),
                    sub_items=addition_data.get("sub_items", []),
                    source=addition_data.get("source", ""),
                )
            )
        return additions

    def _rebuild_understanding(self, understanding_data: Dict[str, Any]) -> Understanding:
        """从序列化数据重建Understanding对象 (v2.0 新增)"""
        # 重建 L1 问题解构
        l1_data = understanding_data.get("l1_deconstruction", {})
        l1 = L1ProblemDeconstruction(
            user_identity=l1_data.get("user_identity", ""),
            explicit_needs=l1_data.get("explicit_needs", ""),
            implicit_motivations=l1_data.get("implicit_motivations", ""),
            key_constraints=l1_data.get("key_constraints", ""),
            analysis_perspective=l1_data.get("analysis_perspective", ""),
        )

        # 重建 L2 动机列表
        l2_motivations = []
        for m_data in understanding_data.get("l2_motivations", []):
            l2_motivations.append(
                L2MotivationDimension(
                    name=m_data.get("name", ""),
                    type=m_data.get("type", "功能型"),
                    score=m_data.get("score", 3),
                    reason=m_data.get("reason", ""),
                    evidence=m_data.get("evidence", []),
                    scenario_expression=m_data.get("scenario_expression", ""),
                )
            )

        # 重建 L3 核心张力
        l3_data = understanding_data.get("l3_tension", {})
        l3 = L3CoreTension(
            primary_motivation=l3_data.get("primary_motivation", ""),
            secondary_motivation=l3_data.get("secondary_motivation", ""),
            tension_formula=l3_data.get("tension_formula", ""),
            resolution_strategy=l3_data.get("resolution_strategy", ""),
            hidden_insights=l3_data.get("hidden_insights", []),
        )

        # 重建 L4 JTBD
        l4_data = understanding_data.get("l4_jtbd", {})
        l4 = L4JTBDDefinition(
            user_role=l4_data.get("user_role", ""),
            information_type=l4_data.get("information_type", ""),
            task_1=l4_data.get("task_1", ""),
            task_2=l4_data.get("task_2", ""),
            full_statement=l4_data.get("full_statement", ""),
        )

        # 重建 L5 锐度测试
        l5_data = understanding_data.get("l5_sharpness", {})
        l5 = L5SharpnessTest(
            specificity_score=l5_data.get("specificity_score", 5),
            specificity_reason=l5_data.get("specificity_reason", ""),
            specificity_evidence=l5_data.get("specificity_evidence", ""),
            actionability_score=l5_data.get("actionability_score", 5),
            actionability_reason=l5_data.get("actionability_reason", ""),
            actionability_evidence=l5_data.get("actionability_evidence", ""),
            depth_score=l5_data.get("depth_score", 5),
            depth_reason=l5_data.get("depth_reason", ""),
            depth_evidence=l5_data.get("depth_evidence", ""),
            searchability_score=l5_data.get("searchability_score", 5),
            searchability_reason=l5_data.get("searchability_reason", ""),
            searchability_evidence=l5_data.get("searchability_evidence", ""),
        )

        return Understanding(
            l1_deconstruction=l1,
            l2_motivations=l2_motivations,
            l3_tension=l3,
            l4_jtbd=l4,
            l5_sharpness=l5,
            comprehensive_summary=understanding_data.get("comprehensive_summary", ""),
        )

    def _direction_to_dict(self, direction: SearchDirection) -> Dict[str, Any]:
        """将SearchDirection对象转换为字典 (v2.0 新增)"""
        return {
            "id": direction.id,
            "block_id": direction.block_id,
            "core_theme": direction.core_theme,
            "search_scope": direction.search_scope,
            "expected_info_types": direction.expected_info_types,
            "key_dimensions": direction.key_dimensions,
            "user_characteristics": direction.user_characteristics,
            "expected_query_count": direction.expected_query_count,
            "priority": direction.priority,
            "metadata": direction.metadata,
        }


# ============================================================================
# 导出接口
# ============================================================================


def get_four_step_flow_orchestrator() -> FourStepFlowOrchestrator:
    """获取4步骤流程编排器实例"""
    return FourStepFlowOrchestrator()
