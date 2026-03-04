# ============================================================================
# 任务导向专家工厂 - Task Oriented Expert Factory v2.1
# ============================================================================
# 更新日期: 2025-12-17
# 变更说明:
# 1. 专家输出严格围绕TaskInstruction
# 2. 强制使用TaskOrientedExpertOutput结构
# 3. 确保协议闭环执行
# 4.  v7.18: 使用 JSON Schema 强制约束（降低解析失败率 15%→3%）
# 5.  v7.19: 按角色类型动态调参（V3高创意/V6高精确）+ 输出质量引导
# ============================================================================

import datetime
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

import yaml
from loguru import logger
from pydantic import ValidationError

from ..core.state import ProjectAnalysisState
from ..core.task_oriented_models import TaskOrientedExpertOutput
from ..services.llm_factory import LLMFactory

#  v7.64: 导入工具调用记录器
try:
    from .tool_callback import ToolCallRecorder, add_references_to_state
except ImportError:
    logger.warning("️ ToolCallRecorder not available (v7.64 feature)")
    ToolCallRecorder = None
    add_references_to_state = None

#  v7.18: 全局缓存自主性协议（所有专家共享，只加载一次）
_autonomy_protocol_cache = None


def get_autonomy_protocol() -> Dict[str, Any]:
    """
    获取缓存的自主性协议（全局单例）

     升级1优化：所有专家共享同一份协议，避免重复加载

    Returns:
        自主性协议字典
    """
    global _autonomy_protocol_cache
    if _autonomy_protocol_cache is None:
        logger.info(" [升级1] 首次加载自主性协议，将缓存于内存")
        _autonomy_protocol_cache = load_yaml_config_cached("prompts/expert_autonomy_protocol_v4.yaml")
    return _autonomy_protocol_cache


@lru_cache(maxsize=20)
def load_yaml_config_cached(config_path: str) -> Dict[str, Any]:
    """
    加载YAML配置文件的辅助函数（带LRU缓存）

     升级1优化：使用LRU缓存避免重复加载，maxsize=20 足够缓存所有角色配置

    Args:
        config_path: 配置文件相对路径（相对于config目录）

    Returns:
        Dict: 配置字典
    """
    # 获取配置目录的绝对路径
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent
    config_dir = project_root / "config"

    full_path = config_dir / config_path

    if not full_path.exists():
        logger.warning(f"配置文件不存在: {full_path}")
        return {}

    try:
        with open(full_path, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
            logger.debug(f" [升级1] 已缓存配置文件: {config_path}")
            return config
    except Exception as e:
        logger.error(f"加载配置文件失败 {full_path}: {str(e)}")
        return {}


def load_yaml_config(config_path: str) -> Dict[str, Any]:
    """
    加载YAML配置文件（向后兼容接口）

     升级1优化：内部调用缓存版本

    Args:
        config_path: 配置文件相对路径（相对于config目录）

    Returns:
        Dict: 配置字典
    """
    return load_yaml_config_cached(config_path)


class TaskOrientedExpertFactory:
    """
    任务导向专家工厂 - 确保专家输出严格围绕分配任务

    核心功能：
    1. 根据RoleObject中的TaskInstruction执行专家分析
    2. 强制返回TaskOrientedExpertOutput结构
    3. 确保协议执行完整闭环
    4. 消除不可预计的额外输出

     P3优化：缓存LLM实例，避免重复创建
     v7.19优化：按角色类型动态调参
    """

    #  P3优化：类级别LLM实例缓存（按角色类型分别缓存）
    _llm_instances: Dict[str, Any] = {}

    #  v7.19: 角色类型专属参数配置
    # - V2 设计总监：中等创意度，需要平衡创意与务实
    # - V3 叙事专家：高创意度，擅长故事和情感表达
    # - V4 设计研究员：中等精确度，需要数据支撑
    # - V5 场景专家：中等创意度，行业洞察
    # - V6 首席工程师：高精确度，技术方案必须严谨
    ROLE_LLM_PARAMS: Dict[str, Dict[str, Any]] = {
        "V2": {"temperature": 0.6, "description": "设计总监-平衡创意与务实"},
        "V3": {"temperature": 0.75, "description": "叙事专家-高创意度"},
        "V4": {"temperature": 0.5, "description": "设计研究员-数据驱动"},
        "V5": {"temperature": 0.6, "description": "场景专家-行业洞察"},
        "V6": {"temperature": 0.4, "description": "首席工程师-高精确度"},
        "default": {"temperature": 0.6, "description": "默认-稳定输出"},
    }

    def __init__(self):
        self.llm_factory = LLMFactory()

    def _get_llm(self, role_type: str = "default", deliverable_count: int = 0):
        """
        获取角色专属的LLM实例（按角色类型缓存）

         v7.19优化：不同角色使用不同的 temperature
        - V3 叙事专家：temperature=0.75（高创意）
        - V6 工程师：temperature=0.4（高精确）
        - 其他角色：temperature=0.5-0.6（平衡）

         v7.52优化：动态Token分配机制
        - 根据角色级别和交付物数量计算max_tokens
        - 避免专家输出被截断

        Args:
            role_type: 角色类型（V2/V3/V4/V5/V6）
            deliverable_count: 交付物数量（用于动态调整token）

        Returns:
            配置了对应参数的 LLM 实例
        """
        # 获取角色专属参数
        params = self.ROLE_LLM_PARAMS.get(role_type, self.ROLE_LLM_PARAMS["default"])

        #  v7.52: 计算动态max_tokens
        max_tokens = self._get_max_tokens_for_expert(role_type, deliverable_count)

        cache_key = f"{role_type}_{params['temperature']}_{max_tokens}"

        if cache_key not in TaskOrientedExpertFactory._llm_instances:
            logger.info(
                f" [v7.19] 为 {role_type} 创建专属LLM (temperature={params['temperature']}, max_tokens={max_tokens}, {params['description']})"
            )
            TaskOrientedExpertFactory._llm_instances[cache_key] = self.llm_factory.create_llm(
                temperature=params["temperature"], max_tokens=max_tokens
            )
        return TaskOrientedExpertFactory._llm_instances[cache_key]

    def _get_max_tokens_for_expert(self, role_type: str, deliverable_count: int) -> int:
        """
         v7.52: 根据角色级别和交付物数量动态计算max_tokens

        Args:
            role_type: 角色类型（V2/V3/V4/V5/V6）
            deliverable_count: 交付物数量

        Returns:
            动态计算的max_tokens值
        """
        # 基础token配额（按角色等级）
        base_tokens = {
            "V2": 12000,  # 设计总监 - 综合性强，输出较多
            "V3": 10000,  # 叙事专家 - 内容详细
            "V4": 8000,  # 研究员 - 数据分析
            "V5": 8000,  # 场景专家 - 行业洞察
            "V6": 8000,  # 工程师 - 技术方案
        }

        # 每个交付物额外增加1500 tokens
        tokens_per_deliverable = 1500

        # 计算总token
        total_tokens = base_tokens.get(role_type, 8000) + (deliverable_count * tokens_per_deliverable)

        # 硬上限32000 (考虑成本和响应时间)
        # 下限 8000 (保证基本输出质量)
        total_tokens = max(8000, min(32000, total_tokens))

        logger.debug(
            f" [v7.52] {role_type} token分配: 基础{base_tokens.get(role_type, 8000)} + {deliverable_count}交付物×{tokens_per_deliverable} = {total_tokens}"
        )

        return total_tokens

    def _detect_gibberish(self, text: str) -> bool:
        """
         v7.271: 检测文本是否包含乱码/幻觉内容

        检测规则:
        1. 无效URL模式 (test, placeholder, example)
        2. 连续无意义汉字 (无标点分隔的长串)
        3. 重复字符模式

        Args:
            text: 待检测的文本

        Returns:
            bool: True 表示检测到乱码
        """
        import re

        if not text:
            return False

        text_str = str(text)

        # 检测无效URL模式（不受长度限制）
        invalid_url_patterns = [
            r"http://[a-z]+/test\d+",  # 测试URL如 http://locear/test0010456
            r"(?:^|[^a-zA-Z])(?:example\.com|example2\.com|placeholder|locear)(?:[^a-zA-Z]|$)",  # 占位符域名
        ]
        for pattern in invalid_url_patterns:
            if re.search(pattern, text_str, re.IGNORECASE):
                return True

        # 以下检测仅对较长文本有效
        if len(text_str) < 50:
            return False

        # 检测连续无意义汉字（30+汉字无标点分隔）
        # 正常中文每10-15字会有标点
        chinese_without_punct = re.findall(r"[\u4e00-\u9fff]{30,}", text_str)
        for segment in chinese_without_punct:
            # 检查这段文字是否缺少标点
            if not re.search(r'[。，！？、；：""' "（）【】]", segment):
                return True

        # 检测重复字符模式（同一字符连续出现5次以上）
        if re.search(r"(.)\1{5,}", text_str):
            return True

        return False

    async def execute_expert(
        self,
        role_object: Dict[str, Any],
        context: str,
        state: ProjectAnalysisState,
        tools: List[Any] | None = None,  #  v7.63.1: 添加工具支持
    ) -> Dict[str, Any]:
        """
         v7.154: 两阶段执行 - 分离搜索和报告生成

        执行任务导向的专家分析，分为两个阶段：
        1. 搜索阶段：使用 bind_tools 执行搜索工具调用
        2. 报告阶段：使用 with_structured_output 生成结构化报告

        Args:
            role_object: 包含TaskInstruction的角色对象
            context: 项目上下文
            state: 当前状态
            tools: 可用的工具列表（可选） - v7.63.1新增

        Returns:
            标准化的专家执行结果
        """
        try:
            role_id = role_object.get("role_id", "unknown")
            role_type = self._extract_base_type(role_id)

            #  v7.52优化：计算交付物数量以动态分配token
            task_instruction = role_object.get("task_instruction", {})
            deliverable_count = len(task_instruction.get("deliverables", []))

            # ========== 阶段1: 搜索阶段 ==========
            search_results = []
            search_recorder = None

            if tools and ToolCallRecorder:
                logger.info(f" [v7.154] {role_id} 开始搜索阶段...")

                # 验证工具可用性
                tool_names = [getattr(tool, "name", str(tool)) for tool in tools]
                logger.info(f" {role_id} 获得工具: {tool_names}")

                # 检查预期工具是否缺失
                role_tool_mapping = {
                    "V2": [],  # 设计总监：无工具
                    "V3": ["bocha", "tavily", "milvus"],
                    "V4": ["bocha", "tavily", "arxiv", "milvus"],
                    "V5": ["bocha", "tavily", "milvus"],
                    "V6": ["bocha", "tavily", "arxiv", "milvus"],
                    "V7": ["bocha", "tavily", "arxiv", "milvus"],  #  v7.156: 情感洞察专家
                }

                expected_tools = role_tool_mapping.get(role_type, [])
                if expected_tools:
                    actual_tool_keys = []
                    for name in tool_names:
                        if "bocha" in name.lower():
                            actual_tool_keys.append("bocha")
                        elif "tavily" in name.lower():
                            actual_tool_keys.append("tavily")
                        elif "arxiv" in name.lower():
                            actual_tool_keys.append("arxiv")
                        elif "milvus" in name.lower() or "ragflow" in name.lower():
                            actual_tool_keys.append("milvus")

                    missing_tools = [t for t in expected_tools if t not in actual_tool_keys]
                    if missing_tools:
                        logger.warning(f"️ {role_id} 缺少工具: {missing_tools}（配置问题或创建失败）")

                # 执行搜索阶段
                search_results, search_recorder = await self._execute_search_phase(
                    role_object=role_object,
                    context=context,
                    state=state,
                    tools=tools,
                )
                logger.info(f" [v7.154] {role_id} 搜索阶段完成，获得 {len(search_results)} 条结果")
            else:
                if not tools:
                    logger.warning(f"️ [v7.154] {role_id} 没有可用工具，跳过搜索阶段")
                    # 检查是否应该有工具但实际没有
                    role_tool_mapping = {
                        "V2": [],
                        "V3": ["bocha", "tavily", "milvus"],
                        "V4": ["bocha", "tavily", "arxiv", "milvus"],
                        "V5": ["bocha", "tavily", "milvus"],
                        "V6": ["bocha", "tavily", "arxiv", "milvus"],
                        "V7": ["bocha", "tavily", "arxiv", "milvus"],  #  v7.156: 情感洞察专家
                    }
                    expected_tools = role_tool_mapping.get(role_type, [])
                    if expected_tools:
                        logger.error(f" {role_id} 应该有工具 {expected_tools} 但实际为空（严重配置问题）")

            # ========== 阶段2: 报告生成阶段 ==========
            logger.info(f" [v7.154] {role_id} 开始报告生成阶段...")

            # 将搜索结果注入到上下文中
            enhanced_context = self._inject_search_results(context, search_results)

            # 构建任务导向的专家提示词
            expert_prompt = self._build_task_oriented_expert_prompt(
                role_object=role_object, context=enhanced_context, state=state
            )

            # 获取 LLM（不绑定工具，只用于结构化输出）
            llm = self._get_llm(role_type, deliverable_count)

            #  v7.18: 强制JSON Schema输出（降低解析失败率 15% → 3%）
            llm_with_structure = llm.with_structured_output(
                TaskOrientedExpertOutput,
                method="json_schema",  # 使用严格JSON Schema而非json_mode
                strict=True,  # 强制LLM遵守schema，无法偏离
            )

            messages = [
                {"role": "system", "content": expert_prompt["system_prompt"]},
                {"role": "user", "content": expert_prompt["user_prompt"]},
            ]

            #  v7.18: response直接是TaskOrientedExpertOutput实例，无需解析
            response = await llm_with_structure.ainvoke(messages)

            # 使用搜索阶段的 recorder 进行后续处理
            recorder = search_recorder

            # 将Pydantic模型转换为字典（保持向后兼容）
            #  Phase 0优化: 排除None和默认值以减少token消耗
            structured_output = (
                response.dict(exclude_none=True, exclude_defaults=True)
                if hasattr(response, "dict")
                else response.model_dump(exclude_none=True, exclude_defaults=True)
            )

            # 构建标准化返回结果
            result = {
                "expert_id": role_object.get("role_id", "unknown"),
                "expert_name": role_object.get("dynamic_role_name", role_object.get("role_name", "Unknown Expert")),
                "analysis": self._extract_full_deliverable_content(structured_output),  #  v7.128: 使用完整内容
                "summary": structured_output.get("task_execution_report", {}).get(
                    "task_completion_summary", ""
                ),  #  v7.128: 保留摘要用于其他用途
                "structured_output": structured_output,  # 已验证的结构化输出
                "task_instruction": role_object.get("task_instruction", {}),  # 任务指令
                "role_definition": role_object,
                "execution_metadata": {
                    "timestamp": self._get_timestamp(),
                    "model_used": "gpt-4",
                    "prompt_version": "task_oriented_v2.0",
                    "output_format": "TaskOrientedExpertOutput",
                    "json_schema_enforced": True,  #  v7.18: 标记使用了强制JSON Schema
                },
            }

            #  v7.9.3: 验证任务完成情况，如果有缺失则自动补全
            validation_passed = self._validate_task_completion(
                structured_output, role_object.get("task_instruction", {})
            )

            #  v7.9.3: 如果验证未通过且有缺失交付物，尝试自动补全
            if not validation_passed and structured_output.get("validation_result", {}).get("needs_completion"):
                logger.info(" 检测到缺失交付物，开始自动补全...")
                structured_output = await self._complete_missing_deliverables(
                    structured_output=structured_output, role_object=role_object, context=context, state=state
                )
                # 更新result中的structured_output
                result["structured_output"] = structured_output
                logger.info(" 交付物补全完成")

            #  v7.154: 自评分校准 - 基于内容特征客观调整LLM自评分
            structured_output = self._calibrate_quality_scores(structured_output, recorder)
            result["structured_output"] = structured_output

            #  v7.129: 工具使用情况统计
            if recorder:
                tool_calls = recorder.get_tool_calls()
                role_id = role_object.get("role_id", "unknown")

                logger.info(f" [v7.129] {role_id} 工具使用统计:")
                logger.info(f"   总调用次数: {len(tool_calls)}")

                if tool_calls:
                    # 按工具类型分类
                    tool_counts = {}
                    for call in tool_calls:
                        tool_name = call.get("tool_name", "unknown")
                        tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1

                    for tool_name, count in tool_counts.items():
                        logger.info(f"   - {tool_name}: {count} 次")

                    # 统计成功/失败
                    success_count = sum(1 for call in tool_calls if call.get("status") == "completed")
                    failed_count = sum(1 for call in tool_calls if call.get("status") == "failed")
                    logger.info(f"   成功: {success_count}, 失败: {failed_count}")
                else:
                    logger.warning("   ️ 未调用任何工具")

            #  v7.64: 从工具调用记录器提取搜索引用并添加到state
            if recorder and add_references_to_state:
                search_references = recorder.get_search_references()
                if search_references:
                    logger.info(f" [v7.64] 提取了 {len(search_references)} 条搜索引用")
                    # 添加到state（会自动去重）
                    add_references_to_state(state, recorder)

                    #  可选：将引用添加到交付物输出（供PDF生成使用）
                    task_exec_report = structured_output.get("task_execution_report", {})
                    deliverable_outputs = task_exec_report.get("deliverable_outputs", [])

                    #  v7.154: 用真实搜索引用覆盖LLM生成的虚假引用
                    # 为每个交付物关联相关的搜索引用
                    for deliverable in deliverable_outputs:
                        deliverable_name = deliverable.get("deliverable_name", "")

                        #  v7.154: 检测并移除LLM生成的虚假引用
                        existing_refs = deliverable.get("search_references", [])
                        if existing_refs:
                            fake_refs = [
                                ref
                                for ref in existing_refs
                                if ref.get("url")
                                and any(
                                    placeholder in ref.get("url", "").lower()
                                    for placeholder in ["example.com", "example2.com", "placeholder", "test.com"]
                                )
                            ]
                            if fake_refs:
                                logger.warning(f"  ️ [v7.154] 检测到 {len(fake_refs)} 条LLM生成的虚假引用，将被覆盖")

                        # 筛选与此交付物相关的引用（基于deliverable_id前缀匹配）
                        related_refs = [
                            ref for ref in search_references if deliverable_name in ref.get("deliverable_id", "")
                        ]

                        #  v7.154: 如果没有精确匹配，使用所有真实引用
                        if not related_refs and search_references:
                            related_refs = search_references
                            logger.info(f"  ℹ️ [v7.154] 无精确匹配，使用全部 {len(related_refs)} 条真实引用")

                        if related_refs:
                            # 强制覆盖，确保使用真实引用
                            deliverable["search_references"] = related_refs
                            logger.info(f"   [v7.154] 为交付物 '{deliverable_name}' 关联了 {len(related_refs)} 条真实引用")

            #  v7.108: 为该专家的交付物生成概念图
            try:
                logger.info(f" [概念图流程] 开始检查角色 {role_object.get('role_id', 'unknown')} 的概念图需求...")

                deliverable_owner_map = state.get("deliverable_owner_map", {})
                deliverable_metadata = state.get("deliverable_metadata", {})
                role_id = role_object.get("role_id", "unknown")
                deliverable_ids = deliverable_owner_map.get(role_id, [])

                logger.debug(f"   交付物归属映射: {len(deliverable_owner_map)} 个角色")
                logger.debug(f"   交付物元数据: {len(deliverable_metadata)} 个交付物")
                logger.info(f"   当前角色 {role_id} 拥有 {len(deliverable_ids)} 个交付物")

                if deliverable_ids and deliverable_metadata:
                    #  v7.110: 检查用户设置，确定是否生成概念图
                    concept_image_config = role_object.get("concept_image_config", {})
                    deliverable_settings = concept_image_config.get("deliverables", [])

                    logger.info(f"  ️  用户概念图配置: {len(deliverable_settings)} 个交付物设置")

                    # 构建交付物名称到配置的映射
                    deliverable_name_to_enable = {}
                    for d_setting in deliverable_settings:
                        deliverable_name_to_enable[d_setting.get("name", "")] = d_setting.get(
                            "enable_concept_image", True
                        )

                    if deliverable_settings:
                        logger.debug(f"   启用概念图的交付物: {[k for k, v in deliverable_name_to_enable.items() if v]}")

                    logger.info(f" [概念图生成] 开始为角色 {role_id} 生成概念图...")

                    # 导入图片生成服务
                    from ..services.image_generator import ImageGeneratorService

                    # 初始化图片生成器
                    logger.debug("   初始化 ImageGeneratorService...")
                    image_generator = ImageGeneratorService()

                    #  v7.128: 准备专家分析内容（完整版本，不再截断至500字）
                    session_id = state.get("session_id", "unknown")
                    project_type = state.get("project_type", "interior")

                    #  v7.122: 提取问卷数据用于概念图生成
                    questionnaire_summary = state.get("questionnaire_summary", {})
                    questionnaire_data = None
                    if questionnaire_summary:
                        questionnaire_data = {
                            "profile_label": questionnaire_summary.get("profile_label", ""),
                            "answers": questionnaire_summary.get("answers", {}),
                        }
                        logger.info("   [v7.122] 准备注入问卷数据到概念图生成")

                    #  v7.155: 提取视觉参考用于概念图生成
                    visual_references = state.get("uploaded_visual_references", None)
                    visual_style_anchor = state.get("visual_style_anchor", None)
                    if visual_references:
                        logger.info(f"  ️ [v7.155] 准备注入 {len(visual_references)} 个视觉参考到概念图生成")
                    if visual_style_anchor:
                        logger.info(f"   [v7.155] 全局风格锚点: {visual_style_anchor[:50]}...")

                    logger.info(f"   会话ID: {session_id}")
                    logger.info(f"  ️  项目类型: {project_type}")

                    # 为每个交付物生成概念图
                    concept_images = []
                    for idx, deliverable_id in enumerate(deliverable_ids, 1):
                        logger.info(f"   [{idx}/{len(deliverable_ids)}] 处理交付物 {deliverable_id}...")

                        metadata = deliverable_metadata.get(deliverable_id)
                        if not metadata:
                            logger.warning("    ️  交付物元数据缺失，跳过")
                            continue

                        #  v7.110: 检查该交付物是否启用概念图
                        deliverable_name = metadata.get("deliverable_name", "")
                        should_generate = deliverable_name_to_enable.get(deliverable_name, True)

                        logger.info(f"     交付物名称: {deliverable_name}")
                        logger.info(f"     是否启用概念图: {should_generate}")

                        if not should_generate:
                            logger.info("    ️  用户禁用，跳过生成")
                            continue

                        try:
                            logger.info("    ️  开始生成概念图...")

                            #  v7.128: 使用精准匹配的交付物专家分析内容
                            deliverable_specific_content = self._extract_deliverable_specific_content(
                                structured_output=result.get("structured_output", {}), deliverable_metadata=metadata
                            )

                            #  v7.122: 传递问卷数据到概念图生成器
                            #  v7.127: 返回值改为 List[ImageMetadata]
                            #  v7.128: 传递完整专家分析内容（最多3000字）
                            #  v7.155: 传递视觉参考和全局风格锚点
                            image_metadata_list = await image_generator.generate_deliverable_image(
                                deliverable_metadata=metadata,
                                expert_analysis=deliverable_specific_content,  #  v7.128: 完整内容
                                session_id=session_id,
                                project_type=project_type,
                                aspect_ratio="16:9",
                                questionnaire_data=questionnaire_data,  #  v7.122: 注入问卷数据
                                visual_references=visual_references,  #  v7.155: 注入视觉参考
                                global_style_anchor=visual_style_anchor,  #  v7.155: 注入全局风格锚点
                            )

                            #  v7.127: 遍历添加所有生成的图片
                            #  Phase 0优化: 排除None和默认值
                            for img_metadata in image_metadata_list:
                                concept_images.append(img_metadata.model_dump(exclude_none=True, exclude_defaults=True))

                            logger.info(f"     成功生成 {len(image_metadata_list)} 张概念图")
                            for idx, img in enumerate(image_metadata_list, 1):
                                logger.info(f"      [{idx}] 文件名: {img.filename}")
                                logger.info(f"      [{idx}] URL: {img.url if hasattr(img, 'url') else 'N/A'}")

                        except Exception as img_error:
                            logger.error(f"     概念图生成失败: {img_error}")
                            logger.exception(img_error)
                            # 不阻塞workflow，继续执行
                            continue

                    # 将概念图添加到专家结果中
                    if concept_images:
                        result["concept_images"] = concept_images
                        logger.info(f" [概念图流程] 成功为角色 {role_id} 生成 {len(concept_images)} 张概念图")
                        logger.info(
                            f"   成功率: {len(concept_images)}/{len(deliverable_ids)} ({len(concept_images)*100//len(deliverable_ids)}%)"
                        )
                    else:
                        logger.warning(f"️  [概念图流程] 角色 {role_id} 未生成任何概念图")
                        logger.info("  可能原因: 所有交付物被用户禁用或元数据缺失")
                else:
                    if not deliverable_ids:
                        logger.debug(f" [概念图流程] 角色 {role_id} 无交付物归属，跳过图片生成")
                    elif not deliverable_metadata:
                        logger.warning("️  [概念图流程] 缺少交付物元数据，无法生成图片")

            except Exception as e:
                logger.error(f" [概念图流程] 发生异常: {e}")
                logger.exception(e)
                logger.warning("  流程继续，专家分析结果仍然有效")
                # 不阻塞workflow，专家分析仍然有效

            return result

        except ValidationError as ve:
            #  v7.18: JSON Schema 强制约束下极少出现，但保留防御性处理
            logger.error(f" Pydantic验证失败 {role_object.get('role_name', 'Unknown')}: {str(ve)}")
            logger.error("️ 这不应该发生在 JSON Schema 强制模式下，请检查 schema 定义")
            #  v7.120: 验证失败也标记为失败状态
            return {
                "expert_id": role_object.get("role_id", "unknown"),
                "expert_name": role_object.get("dynamic_role_name", role_object.get("role_name", "Unknown Expert")),
                "analysis": f"验证失败: {str(ve)}",
                "structured_output": None,
                "task_instruction": role_object.get("task_instruction", {}),
                "role_definition": role_object,
                "error": True,
                "status": "failed",  #  明确标记为失败状态
                "confidence": 0.0,  #  失败时置信度为0
                "execution_metadata": {
                    "timestamp": self._get_timestamp(),
                    "model_used": "gpt-4",
                    "prompt_version": "task_oriented_v2.0",
                    "error_type": "ValidationError",
                    "error_message": str(ve),
                    "failure_type": "validation_error",  #  失败类型
                },
            }
        except Exception as e:
            #  v7.60.3: 检测是否为输出长度超限错误
            error_msg = str(e)
            if "length limit was reached" in error_msg or "completion_tokens" in error_msg:
                logger.error(f" 专家 {role_object.get('role_name', 'Unknown')} 输出超长被截断")
                logger.error(f"   错误详情: {error_msg}")
                logger.error("    建议: 调整提示词要求更简洁的输出，或增加输出长度限制警告")
            else:
                logger.error(f"执行任务导向专家 {role_object.get('role_name', 'Unknown')} 时出错: {error_msg}")

            #  v7.120: 添加明确的失败状态标记
            return {
                "expert_id": role_object.get("role_id", "unknown"),
                "expert_name": role_object.get("dynamic_role_name", role_object.get("role_name", "Unknown Expert")),
                "analysis": f"执行失败: {str(e)}",
                "structured_output": None,
                "task_instruction": role_object.get("task_instruction", {}),
                "role_definition": role_object,
                "error": True,
                "status": "failed",  #  明确标记为失败状态
                "confidence": 0.0,  #  失败时置信度为0
                "execution_metadata": {
                    "timestamp": self._get_timestamp(),
                    "model_used": "gpt-4",
                    "prompt_version": "task_oriented_v2.0",
                    "error_message": str(e),
                    "failure_type": "exception",  #  失败类型
                },
            }

    async def _execute_search_phase(
        self,
        role_object: Dict[str, Any],
        context: str,
        state: ProjectAnalysisState,
        tools: List[Any],
    ) -> tuple:
        """
         v7.175: 搜索阶段 - 使用5轮渐进式搜索编排器
         v7.180: 支持需求分析上下文注入，增强搜索精准度

        替代原有的 LLM 自主决定模式，使用 SearchOrchestrator 执行结构化的5轮搜索：
        1. 基础概念探索 - 获取定义和框架
        2. 维度深化 - 深入各影响维度
        3. 学术深度 - 搜索论文和方法论
        4. 实践案例 - 搜索项目案例
        5. 数据支撑 - 搜索统计数据

        v7.180 增强：
        - 从state提取需求分析结果（JTBD、核心矛盾、人性维度）
        - 使用JTBDQueryBuilder构建增强查询
        - 使用InsightAwareQualityControl评估结果

        Args:
            role_object: 角色对象
            context: 项目上下文
            state: 当前状态
            tools: 可用的工具列表

        Returns:
            tuple: (search_results, recorder)
                - search_results: 搜索引用列表
                - recorder: ToolCallRecorder 实例（用于后续统计）
        """
        import os

        role_id = role_object.get("role_id", "unknown")
        role_type = self._extract_base_type(role_id)

        #  v7.175: 检查是否启用5轮渐进式搜索
        use_progressive_search = os.getenv("USE_PROGRESSIVE_SEARCH", "true").lower() == "true"

        # 创建工具调用记录器
        recorder = ToolCallRecorder(role_id=role_id, deliverable_id=f"{role_id}_search")
        logger.info(f" [v7.180] {role_id} 创建搜索阶段 ToolCallRecorder")

        if use_progressive_search:
            #  v7.175/v7.180: 使用5轮渐进式搜索编排器（支持需求分析上下文）
            try:
                from ..services.search_orchestrator import get_search_orchestrator

                orchestrator = get_search_orchestrator()
                task_instruction = role_object.get("task_instruction", {})
                deliverables = task_instruction.get("deliverables", [])

                # 构建搜索查询
                project_type = state.get("project_type", "设计")
                original_requirements = state.get("original_requirements", "")

                # 为每个交付物执行5轮渐进式搜索
                all_search_results = []
                for deliverable in deliverables:
                    deliverable_name = deliverable.get("name", "")
                    deliverable_desc = deliverable.get("description", "")
                    query = f"{original_requirements} {deliverable_name} {deliverable_desc}"

                    context_dict = {
                        "project_type": project_type,
                        "role_id": role_id,
                        "deliverable_name": deliverable_name,
                    }

                    logger.info(f" [v7.180] {role_id} 开始5轮渐进式搜索: {deliverable_name}")
                    logger.info(f"    Query: {query[:100]}...")

                    #  v7.180: 执行5轮编排搜索（传入state以提取需求分析上下文）
                    result = orchestrator.orchestrate(
                        query, context_dict, max_rounds=5, state=state  #  v7.180: 传入state
                    )

                    # 提取搜索结果
                    sources = result.get("all_sources", [])
                    rounds_completed = result.get("rounds_completed", 0)
                    execution_time = result.get("execution_time", 0)
                    enhanced_query_count = result.get("enhanced_queries", [])

                    logger.info(f"    完成 {rounds_completed} 轮搜索, 获取 {len(sources)} 条结果, 耗时 {execution_time:.2f}s")
                    if enhanced_query_count:
                        logger.info(f"    使用了 {len(enhanced_query_count)} 个增强查询（来自需求分析）")

                    # 转换为搜索引用格式
                    for source in sources:
                        ref = {
                            "title": source.get("title", ""),
                            "url": source.get("url", source.get("link", "")),
                            "snippet": source.get("content", source.get("snippet", "")),
                            "source": source.get("source", "web"),
                            "round": source.get("round", "unknown"),
                            "deliverable": deliverable_name,
                            #  v7.180: 添加人性维度评估结果
                            "human_score": source.get("human_score"),
                            "matched_dimensions": source.get("matched_dimensions", []),
                        }
                        all_search_results.append(ref)

                        # 记录到 recorder
                        recorder._add_search_result(
                            tool_name=source.get("tool", "orchestrator"), query=query[:50], result=ref
                        )

                logger.info(f" [v7.180] {role_id} 渐进式搜索完成: 共 {len(all_search_results)} 条引用")

                # 添加到 state
                if all_search_results and add_references_to_state:
                    add_references_to_state(state, recorder)
                    logger.info(f" [v7.180] 已将 {len(all_search_results)} 条搜索引用添加到 state")

                return all_search_results, recorder

            except Exception as e:
                logger.warning(f"️ [v7.180] 渐进式搜索失败，回退到LLM自主搜索: {e}")
                # 回退到原有方式

        # 原有的 LLM 自主搜索模式 (fallback)
        # 获取基础 LLM（不使用 structured_output）
        llm = self._get_llm(role_type)

        # 绑定工具和回调
        tool_names = [getattr(tool, "name", str(tool)) for tool in tools]
        logger.info(f" [v7.175] {role_id} 绑定 {len(tools)} 个工具: {tool_names}")

        llm_with_tools = llm.bind_tools(tools, callbacks=[recorder])
        logger.info(f" [v7.175] {role_id} 工具绑定成功 + ToolCallRecorder已启用")
        logger.info(f"    工具调用将记录到: {recorder.log_file}")

        # 构建搜索专用 prompt
        search_prompt = self._build_search_prompt(role_object, context, state)

        messages = [
            {"role": "system", "content": search_prompt["system_prompt"]},
            {"role": "user", "content": search_prompt["user_prompt"]},
        ]

        # 执行搜索（允许 LLM 自主决定调用哪些工具）
        try:
            logger.info(f" [v7.175] {role_id} 开始执行LLM自主搜索...")
            await llm_with_tools.ainvoke(messages)
            logger.info(f" [v7.175] {role_id} 搜索执行完成")
        except Exception as e:
            logger.error(f" [v7.175] {role_id} 搜索执行失败: {e}")
            # 搜索失败不阻塞流程，返回空结果
            return [], recorder

        # 提取搜索结果
        search_references = recorder.get_search_references()

        # 记录工具使用统计
        tool_calls = recorder.get_tool_calls()
        logger.info(f" [v7.175] {role_id} 搜索阶段统计:")
        logger.info(f"   总调用次数: {len(tool_calls)}")

        if tool_calls:
            # 按工具类型分类
            tool_counts = {}
            for call in tool_calls:
                tool_name = call.get("tool_name", "unknown")
                tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1

            for tool_name, count in tool_counts.items():
                logger.info(f"   - {tool_name}: {count} 次")

            # 统计成功/失败
            success_count = sum(1 for call in tool_calls if call.get("status") == "completed")
            failed_count = sum(1 for call in tool_calls if call.get("status") == "failed")
            logger.info(f"   成功: {success_count}, 失败: {failed_count}")
        else:
            logger.warning("   ️ 搜索阶段未调用任何工具")

        # 添加到 state
        if search_references and add_references_to_state:
            add_references_to_state(state, recorder)
            logger.info(f" [v7.175] 已将 {len(search_references)} 条搜索引用添加到 state")

        logger.info(f" [v7.175] {role_id} 搜索阶段: {len(tool_calls)} 次工具调用, {len(search_references)} 条引用")

        return search_references, recorder

    def _build_search_prompt(
        self,
        role_object: Dict[str, Any],
        context: str,
        state: ProjectAnalysisState,
    ) -> Dict[str, str]:
        """
         v7.154: 构建搜索阶段专用 prompt

        这个 prompt 专注于引导 LLM 调用搜索工具，而不是生成报告。
        通过明确的指令和示例，确保 LLM 理解需要调用工具。

        Args:
            role_object: 角色对象
            context: 项目上下文
            state: 当前状态

        Returns:
            Dict: 包含 system_prompt 和 user_prompt
        """
        task_instruction = role_object.get("task_instruction", {})
        deliverables = task_instruction.get("deliverables", [])
        role_name = role_object.get("dynamic_role_name", role_object.get("role_name", "专家"))

        # 提取需要搜索的交付物
        deliverable_names = [d.get("name", "") for d in deliverables]

        system_prompt = f"""你是一位专业的研究助手，正在为 {role_name} 收集外部资料。

#  你的任务
为以下交付物搜索相关资料：
{chr(10).join([f'- {name}' for name in deliverable_names])}

#  搜索工具说明
你有以下搜索工具可用，**必须调用它们**：

1. **bocha_search** - 中文搜索引擎
   - 适用于：中文内容、国内案例、中文行业报告
   - 优先用于中文项目

2. **tavily_search** - 国际搜索引擎
   - 适用于：英文内容、全球案例、国际趋势
   - 适合获取国际视角

3. **arxiv_search** - 学术论文搜索
   - 适用于：学术理论、研究方法、技术论文
   - 适合需要学术支撑的内容

4. **milvus_kb_search** - 内部知识库搜索
   - 适用于：历史项目、内部案例、专有知识

#  搜索策略
1. **每个交付物至少搜索 2-3 次**
2. **使用不同的关键词组合**
3. **中文项目优先使用 bocha_search**
4. **学术内容使用 arxiv_search**

#  搜索内容建议
- 最新案例和趋势（2024-2025年）
- 行业最佳实践
- 相关理论和方法论
- 竞品分析和市场数据

# ️ 重要提醒
- **你必须调用搜索工具**，不要仅凭内部知识回答
- 每次搜索后简要说明搜索目的
- 完成所有搜索后，回复 "搜索完成"
- 不要生成报告，只需要调用搜索工具收集资料

# 示例
如果交付物是"用户画像分析"，你应该：
1. 调用 bocha_search("用户画像 设计方法 2024")
2. 调用 tavily_search("user persona design methodology")
3. 调用 bocha_search("目标用户 需求分析 案例")
"""

        user_input = state.get("user_input", "")
        project_type = state.get("project_type", "设计项目")

        user_prompt = f"""# 项目背景
{context[:2000]}

# 用户需求
{user_input}

# 项目类型
{project_type}

# 需要搜索的交付物
{chr(10).join([f'- {name}' for name in deliverable_names])}

请开始搜索相关资料。记住：
1. **必须调用搜索工具**
2. 不要直接生成内容
3. 每个交付物至少搜索 2-3 次
4. 完成后回复 "搜索完成"
"""

        return {"system_prompt": system_prompt, "user_prompt": user_prompt}

    def _inject_search_results(
        self,
        context: str,
        search_results: List[Dict[str, Any]],
    ) -> str:
        """
         v7.154: 将搜索结果注入到上下文中
         v7.271: 添加乱码/无效结果预过滤

        将搜索阶段收集的资料格式化后注入到报告生成阶段的上下文中，
        确保专家在生成报告时能够引用这些外部资料。

        Args:
            context: 原始上下文
            search_results: 搜索引用列表

        Returns:
            str: 增强后的上下文
        """
        if not search_results:
            logger.debug("[v7.154] 无搜索结果需要注入")
            return context

        #  v7.271: 过滤无效搜索结果
        valid_results = []
        filtered_count = 0
        for ref in search_results:
            url = ref.get("url", "")
            snippet = ref.get("snippet", "")
            title = ref.get("title", "")

            # 跳过无效URL
            invalid_url_patterns = ["test", "example", "placeholder", "locear", "localhost"]
            if url and any(invalid in url.lower() for invalid in invalid_url_patterns):
                logger.warning(f"️ [v7.271] 过滤无效URL搜索结果: {url[:50]}")
                filtered_count += 1
                continue

            # 跳过乱码内容
            if self._detect_gibberish(snippet) or self._detect_gibberish(title):
                logger.warning(f"️ [v7.271] 过滤乱码搜索结果: {title[:30] if title else 'N/A'}")
                filtered_count += 1
                continue

            valid_results.append(ref)

        if filtered_count > 0:
            logger.info(
                f" [v7.271] 搜索结果过滤: 原始 {len(search_results)} 条, 过滤 {filtered_count} 条, 有效 {len(valid_results)} 条"
            )

        if not valid_results:
            logger.warning("[v7.271] 所有搜索结果均被过滤，跳过注入")
            return context

        # 格式化搜索结果
        formatted_results = []
        for idx, ref in enumerate(valid_results[:15], 1):  # 最多15条
            title = ref.get("title", "N/A")
            source = ref.get("source_tool", "N/A")
            snippet = ref.get("snippet", "N/A")[:400]  # 限制摘要长度
            url = ref.get("url", "N/A")
            query = ref.get("query", "")

            formatted_results.append(
                f"""
### 参考资料 {idx}
- **标题**: {title}
- **来源**: {source}
- **搜索词**: {query}
- **摘要**: {snippet}
- **URL**: {url}
"""
            )

        search_section = f"""
#  搜索结果（共 {len(search_results)} 条）

以下是为本次分析收集的外部资料，请在分析中引用这些内容：

{''.join(formatted_results)}

---
**注意**: 请在你的分析中适当引用上述资料，确保内容有据可依。
"""

        logger.info(f"[v7.154] 已将 {len(search_results)} 条搜索结果注入到上下文中")
        return f"{context}\n\n{search_section}"

    async def execute_expert_with_retry(
        self,
        role_object: Dict[str, Any],
        context: str,
        state: ProjectAnalysisState,
        tools: List[Any] | None = None,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """
         v7.129 Week2 P2: 带重试机制的专家执行包装函数

        如果V4/V6角色未使用工具，将增强prompt并重试，确保搜索工具被正确调用。

        Args:
            role_object: 包含TaskInstruction的角色对象
            context: 项目上下文
            state: 当前状态
            tools: 可用的工具列表（可选）
            max_retries: 最大重试次数（默认3次）

        Returns:
            标准化的专家执行结果
        """
        role_id = role_object.get("role_id", "unknown")
        role_type = self._extract_base_type(role_id)

        # 检查是否为需要搜索工具的角色
        search_required_roles = ["V4", "V6"]
        requires_search = role_type in search_required_roles

        logger.info(f" [v7.129 Retry] {role_id} 开始执行（最多{max_retries}次重试）")
        logger.info(f"   需要搜索工具: {'是' if requires_search else '否'}")

        attempt = 0
        last_result = None

        while attempt < max_retries:
            attempt += 1
            logger.info(f" [v7.129 Retry] {role_id} 第 {attempt}/{max_retries} 次尝试")

            # 如果是重试，增强prompt以强调工具使用
            if attempt > 1 and requires_search:
                logger.info(f" [v7.129 Retry] {role_id} 增强prompt（第{attempt}次尝试）")
                # 在task_instruction中添加强制工具使用提示
                task_instruction = role_object.get("task_instruction", {})

                #  渐进式增强策略
                if attempt == 2:
                    # 第2次：温和提醒
                    task_instruction["execution_notes"] = (
                        task_instruction.get("execution_notes", "")
                        + "\n\n️ IMPORTANT: 请务必使用搜索工具（tavily_search, arxiv_search等）进行研究，"
                        + "不要仅凭内部知识生成内容。至少调用3个不同的工具。"
                    )
                elif attempt == 3:
                    # 第3次：强烈要求
                    task_instruction["execution_notes"] = (
                        task_instruction.get("execution_notes", "")
                        + "\n\n CRITICAL: 前两次尝试未使用搜索工具，这是不可接受的！"
                        + "你必须调用至少5次搜索工具（tavily_search, arxiv_search, bocha_search）。"
                        + "每个deliverable都需要有外部搜索支持。立即开始使用工具！"
                    )

                role_object["task_instruction"] = task_instruction

            # 执行专家分析
            try:
                result = await self.execute_expert(role_object=role_object, context=context, state=state, tools=tools)

                last_result = result

                # 检查工具使用情况（通过structured_output中的protocol_execution）
                if requires_search and tools:
                    structured_output = result.get("structured_output", {})
                    protocol_exec = structured_output.get("protocol_execution", {})
                    tools_used = protocol_exec.get("tools_used", [])

                    if len(tools_used) == 0:
                        logger.warning(f"️ [v7.129 Retry] {role_id} 第{attempt}次尝试未使用任何工具")

                        if attempt < max_retries:
                            logger.info(f" [v7.129 Retry] {role_id} 准备重试...")
                            continue  # 继续下一次尝试
                        else:
                            logger.error(f" [v7.129 Retry] {role_id} 已达最大重试次数，但仍未使用工具")

                            #  v7.129 Week2 P2: 触发搜索降级策略
                            logger.warning(f" [v7.129 Fallback] {role_id} 触发搜索降级策略")
                            try:
                                fallback_refs = await self._execute_fallback_search(
                                    role_object=role_object, context=context, state=state, tools=tools
                                )

                                if fallback_refs:
                                    logger.info(f" [v7.129 Fallback] {role_id} 降级搜索获得 {len(fallback_refs)} 条引用")

                                    # 将降级搜索结果添加到state
                                    if add_references_to_state and state:
                                        existing_refs = state.get("search_references", [])
                                        state["search_references"] = existing_refs + fallback_refs
                                        logger.info(" [v7.129 Fallback] 已将降级搜索结果添加到state")

                                    # 添加降级标记到警告
                                    result["warnings"] = result.get("warnings", [])
                                    result["warnings"].append(
                                        {
                                            "type": "fallback_search_executed",
                                            "message": "LLM未主动调用工具，系统自动执行了降级搜索",
                                            "fallback_references_count": len(fallback_refs),
                                        }
                                    )
                                else:
                                    logger.warning(f"️ [v7.129 Fallback] {role_id} 降级搜索未获得结果")
                            except Exception as fallback_error:
                                logger.error(f" [v7.129 Fallback] {role_id} 降级搜索失败: {fallback_error}")

                            # 添加工具缺失警告标记到结果
                            result["warnings"] = result.get("warnings", [])
                            result["warnings"].append(
                                {
                                    "type": "missing_tool_usage",
                                    "message": f"角色{role_id}应使用搜索工具但未执行，已尝试{max_retries}次",
                                    "impact": "结果可能缺乏外部验证和最新信息",
                                }
                            )
                            # 降低confidence
                            result["confidence"] = min(0.6, result.get("confidence", 1.0))
                    else:
                        logger.info(f" [v7.129 Retry] {role_id} 第{attempt}次尝试成功使用了工具: {tools_used}")
                        # 成功使用工具，退出重试循环
                        break
                else:
                    # 不需要搜索工具的角色，或未提供工具，直接成功
                    logger.info(f" [v7.129 Retry] {role_id} 执行成功（无需工具检查）")
                    break

            except Exception as e:
                logger.error(f" [v7.129 Retry] {role_id} 第{attempt}次尝试失败: {e}")
                if attempt >= max_retries:
                    logger.error(f" [v7.129 Retry] {role_id} 已达最大重试次数，返回失败结果")
                    # 返回最后一次的结果或错误结果
                    if last_result:
                        return last_result
                    else:
                        raise
                else:
                    logger.info(f" [v7.129 Retry] {role_id} 准备重试...")
                    continue

        logger.info(f" [v7.129 Retry] {role_id} 执行完成（共{attempt}次尝试）")
        return last_result

    def _get_role_config_filename(self, role_id: str) -> str:
        """
        从role_id提取配置文件名

        role_id格式支持:
        - 完整格式: V2_设计总监_2-0, V3_叙事与体验专家_3-3, V5_场景与行业专家_5-2
        - 短格式: 2-0, 3-3, 5-2
        配置文件: v2_design_director.yaml, v3_narrative_expert.yaml, v5_scenario_expert.yaml
        """
        # 同时支持完整格式 (V2_xxx) 和短格式 (2-x)
        if role_id.startswith("V2") or role_id.startswith("2-"):
            return "roles/v2_design_director.yaml"
        elif role_id.startswith("V3") or role_id.startswith("3-"):
            return "roles/v3_narrative_expert.yaml"
        elif role_id.startswith("V4") or role_id.startswith("4-"):
            return "roles/v4_design_researcher.yaml"
        elif role_id.startswith("V5") or role_id.startswith("5-"):
            return "roles/v5_scenario_expert.yaml"
        elif role_id.startswith("V6") or role_id.startswith("6-"):
            return "roles/v6_chief_engineer.yaml"
        else:
            logger.warning(f"未识别的role_id格式: {role_id}")
            return f"roles/{role_id}.yaml"  # 回退到原始逻辑

    def _build_task_oriented_expert_prompt(
        self, role_object: Dict[str, Any], context: str, state: ProjectAnalysisState
    ) -> Dict[str, str]:
        """
        构建任务导向的专家提示词，确保输出严格围绕TaskInstruction

         v7.18 升级1: 使用 Prompt 模板系统，减少 80% 的拼接开销
         v7.122: 注入预生成的搜索查询，确保数据流一致性
        """
        try:
            # 加载基础角色配置 - 使用缓存的映射函数
            config_filename = self._get_role_config_filename(role_object["role_id"])
            role_config = load_yaml_config(config_filename)
            base_system_prompt = role_config.get("system_prompt", "你是一位专业的分析师")

            # 获取TaskInstruction
            task_instruction = role_object.get("task_instruction", {})

            #  v7.10: 检测创意叙事模式
            is_creative_narrative = task_instruction.get("is_creative_narrative", False)

            #  v7.18 升级1: 使用缓存的自主性协议（所有专家共享，避免重复加载）
            autonomy_protocol = get_autonomy_protocol()

            # 提取角色类型（用于模板缓存）
            role_type = self._extract_base_type(role_object["role_id"])

            #  v7.122: 提取预生成的搜索查询（如果存在）
            search_queries_hint = self._build_search_queries_hint(role_object, state)

            #  v7.18 升级1: 使用 Prompt 模板系统（预构建静态部分）
            from ..core.prompt_templates import get_expert_template

            template = get_expert_template(role_type, base_system_prompt, autonomy_protocol)

            #  v7.10: 创意叙事模式的特殊说明
            creative_mode_note = ""
            if is_creative_narrative:
                creative_mode_note = """
#  创意叙事模式 (Creative Narrative Mode)

️ **特别说明**: 你正在创意叙事模式下工作，以下约束放宽：
- `completion_rate` 和 `quality_self_assessment` **可选填**（如不适用可省略或设为默认值）
- `execution_time_estimate` **可选填**（创意过程难以精确量化时间）
- 允许更自由的叙事结构和表达方式
- 输出重点在于**叙事质量和情感共鸣**，而非量化指标

 **建议**: 如果叙事内容本身就包含完整性和质量的体现，可以简化或省略这些量化字段。
"""

            #  v7.18 升级1: 使用模板渲染（只构建20%的动态内容）
            #  v7.122: 添加搜索查询提示
            return template.render(
                dynamic_role_name=role_object.get("dynamic_role_name", role_object.get("role_name")),
                task_instruction=task_instruction,
                context=context,
                state=state,
                creative_mode_note=creative_mode_note,
                search_queries_hint=search_queries_hint,
            )

        except Exception as e:
            logger.error(f"构建任务导向专家提示词时出错: {str(e)}")
            return {"system_prompt": "你是一位专业的分析师，请基于提供的信息进行分析。", "user_prompt": f"请分析以下内容：\n{context}"}

    def _extract_base_type(self, role_id: str) -> str:
        """
        提取角色的基础类型（用于模板缓存）

        Args:
            role_id: 角色 ID（如 "3-1", "V3_叙事专家_3-1"）

        Returns:
            基础类型（如 "V3"）
        """
        if role_id.startswith("V") and "_" in role_id:
            return role_id.split("_")[0]
        elif role_id.startswith("2-"):
            return "V2"
        elif role_id.startswith("3-"):
            return "V3"
        elif role_id.startswith("4-"):
            return "V4"
        elif role_id.startswith("5-"):
            return "V5"
        elif role_id.startswith("6-"):
            return "V6"
        else:
            logger.warning(f"无法提取基础类型: {role_id}")
            return role_id

    def _build_search_queries_hint(self, role_object: Dict[str, Any], state: ProjectAnalysisState) -> str:
        """
        构建搜索查询提示，引导专家使用预生成的查询

         v7.122: 确保预生成的搜索查询（已整合用户问题+问卷）被专家优先使用

        Args:
            role_object: 角色对象
            state: 当前状态

        Returns:
            搜索查询提示文本
        """
        role_id = role_object.get("role_id", "unknown")
        deliverable_owner_map = state.get("deliverable_owner_map", {})
        deliverable_metadata = state.get("deliverable_metadata", {})

        deliverable_ids = deliverable_owner_map.get(role_id, [])

        if not deliverable_ids or not deliverable_metadata:
            return ""

        # 收集所有交付物的预生成查询
        all_queries = []
        deliverable_names = []

        for deliverable_id in deliverable_ids:
            metadata = deliverable_metadata.get(deliverable_id, {})
            if not metadata:
                continue

            deliverable_name = metadata.get("name", "未命名交付物")
            search_queries = metadata.get("search_queries", [])

            if search_queries:
                deliverable_names.append(deliverable_name)
                all_queries.extend(search_queries)

        if not all_queries:
            return ""

        # 构建提示文本
        hint = f"""
#  推荐搜索查询（Recommended Search Queries）

系统已基于用户问题和问卷数据为你的交付物预生成了优化的搜索查询。
这些查询已整合了用户的风格偏好、情感需求和项目特征。

**你的交付物**: {', '.join(deliverable_names)}

**推荐查询** (请优先使用或基于它们优化):
{chr(10).join(f'  {i+1}. "{q}"' for i, q in enumerate(all_queries))}

 **使用建议**:
- 优先使用这些查询获取项目相关信息
- 可以基于这些查询进行微调或组合
- 如需补充其他查询，请确保与项目上下文一致
"""

        logger.info(f" [v7.122] 为角色 {role_id} 注入了 {len(all_queries)} 个预生成搜索查询")
        return hint

    def _parse_and_validate_output(self, expert_output: str, role_object: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析并验证专家输出是否符合TaskOrientedExpertOutput结构
        如果验证失败，使用降级策略构造默认结构

         v7.11 增强: 更强的 JSON 预处理 + 多种修复策略
        """
        try:
            #  v7.11: 先进行全局预处理，移除所有markdown代码块标记
            cleaned_output = expert_output.strip()

            # 移除所有markdown代码块标记（包括```json, ```JSON, ``` 等变体）
            import re

            # 处理 ```json 或 ```JSON 开头
            if re.search(r"^```(?:json|JSON)?\s*", cleaned_output):
                cleaned_output = re.sub(r"^```(?:json|JSON)?\s*", "", cleaned_output)
            # 处理结尾的 ```
            cleaned_output = re.sub(r"\s*```$", "", cleaned_output)
            # 处理中间可能存在的代码块标记
            cleaned_output = re.sub(r"```(?:json|JSON)?\s*([\s\S]*?)\s*```", r"\1", cleaned_output)

            logger.debug(f" JSON预处理后长度: {len(cleaned_output)}")

            # 提取JSON内容
            if "{" in cleaned_output and "}" in cleaned_output:
                json_str = cleaned_output[cleaned_output.find("{") : cleaned_output.rfind("}") + 1]
            else:
                logger.warning("输出不包含有效JSON，尝试整体解析")
                json_str = cleaned_output.strip()

            #  尝试解析JSON（多种修复策略）
            parsed_output = self._try_parse_json_with_fixes(json_str)

            if parsed_output is None:
                raise json.JSONDecodeError("所有JSON修复策略都失败了", json_str, 0)

            # 验证结构（使用Pydantic模型验证）
            task_oriented_output = TaskOrientedExpertOutput(**parsed_output)

            logger.info(f" 成功验证 {role_object.get('role_name', 'Unknown')} 的TaskOrientedExpertOutput结构")
            return task_oriented_output.dict()

        except json.JSONDecodeError as e:
            logger.error(f" JSON解析失败: {str(e)}")
            logger.error(f"原始输出: {expert_output[:200]}...")
        except Exception as e:
            logger.error(f" 输出验证失败: {str(e)}")

        # 降级策略：构造符合最小规范的默认结构
        logger.warning(f"️ 使用降级策略为 {role_object.get('role_name', 'Unknown')} 构造默认输出")
        return self._create_fallback_output(expert_output, role_object)

    def _try_parse_json_with_fixes(self, json_str: str) -> Dict[str, Any] | None:
        """
        尝试多种策略修复并解析 JSON

        常见问题:
        1. 缺少逗号分隔符
        2. 多余的逗号
        3. 转义字符问题
        4. 截断的 JSON
        """
        import re

        # 策略1: 直接解析
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

        # 策略2: 移除控制字符并重试
        try:
            cleaned = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", json_str)
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # 策略3: 修复常见的逗号问题
        try:
            # 移除数组/对象末尾多余的逗号
            fixed = re.sub(r",\s*([}\]])", r"\1", json_str)
            # 添加缺失的逗号（对象属性之间）
            fixed = re.sub(r'"\s*\n\s*"', '",\n"', fixed)
            # 添加缺失的逗号（数组元素之间）
            fixed = re.sub(r"}\s*\n\s*{", "},\n{", fixed)
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass

        # 策略4: 尝试修复截断的 JSON
        try:
            # 计算未闭合的括号
            open_braces = json_str.count("{") - json_str.count("}")
            open_brackets = json_str.count("[") - json_str.count("]")

            if open_braces > 0 or open_brackets > 0:
                # 尝试补全括号
                fixed = json_str
                fixed += "}" * open_braces
                fixed += "]" * open_brackets
                return json.loads(fixed)
        except json.JSONDecodeError:
            pass

        # 策略5: 提取最外层的有效 JSON 对象
        try:
            # 找到第一个 { 到最后一个对应的 }
            depth = 0
            start = -1
            end = -1
            for i, c in enumerate(json_str):
                if c == "{":
                    if depth == 0:
                        start = i
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break

            if start >= 0 and end > start:
                return json.loads(json_str[start:end])
        except json.JSONDecodeError:
            pass

        logger.warning("️ 所有JSON修复策略都失败了")
        return None

    def _create_fallback_output(self, raw_output: str, role_object: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建降级输出结构（当Pydantic验证失败时）

         v7.6: 增强对嵌套 JSON 的处理，避免显示原始代码
        """
        role_name = role_object.get("dynamic_role_name", role_object.get("role_name", "Unknown Expert"))

        #  尝试提取实际内容而不是原始 JSON
        cleaned_content = self._extract_meaningful_content(raw_output)

        return {
            "task_execution_report": {
                "deliverable_outputs": [
                    {
                        "deliverable_name": "分析报告",
                        "content": cleaned_content,
                        "completion_status": "completed",
                        "completion_rate": 1.0,
                        "notes": "使用降级策略生成的输出",
                        "quality_self_assessment": 0.7,
                    }
                ],
                "task_completion_summary": f"{role_name}已完成分析任务",
                "additional_insights": None,
                "execution_challenges": ["LLM未按预期格式返回，使用降级策略"],
            },
            "protocol_execution": {
                "protocol_status": "complied",
                "compliance_confirmation": "接受需求分析师的洞察",
                "challenge_details": None,
                "reinterpretation": None,
            },
            "execution_metadata": {
                "confidence": 0.7,
                "completion_rate": 1.0,
                "execution_time_estimate": "未知",
                "execution_notes": "此输出使用降级策略生成，未经标准验证",
                "dependencies_satisfied": True,
            },
        }

    def _calibrate_quality_scores(
        self, structured_output: Dict[str, Any], recorder: Any | None = None
    ) -> Dict[str, Any]:
        """
         v7.154: 自评分校准 - 基于内容特征客观调整LLM自评分

        LLM自评分往往虚高（都在0.9+），此方法基于客观指标进行校准：
        1. 内容长度：过短的内容降低评分
        2. 搜索引用：缺少真实引用降低评分
        3. 具体案例：缺少具体案例降低评分
        4. 数据支撑：缺少数据支撑降低评分

         v7.154.1: 调整惩罚系数，使校准更温和
        - 原惩罚总和最高 0.33，导致 0.95 → 0.62
        - 新惩罚总和最高 0.20，使 0.95 → 0.75

        Args:
            structured_output: 专家的结构化输出
            recorder: 工具调用记录器（用于检查搜索引用）

        Returns:
            校准后的结构化输出
        """
        try:
            task_exec_report = structured_output.get("task_execution_report", {})
            deliverable_outputs = task_exec_report.get("deliverable_outputs", [])

            if not deliverable_outputs:
                return structured_output

            # 获取真实搜索引用数量
            real_search_refs_count = 0
            if recorder:
                search_refs = recorder.get_search_references()
                # 过滤掉占位符URL
                real_search_refs_count = len(
                    [
                        ref
                        for ref in search_refs
                        if ref.get("url")
                        and not any(
                            placeholder in ref.get("url", "").lower()
                            for placeholder in ["example.com", "example2.com", "placeholder"]
                        )
                    ]
                )

            for deliverable in deliverable_outputs:
                original_score = deliverable.get("quality_self_assessment", 0.9)
                content = deliverable.get("content", "")

                # 计算惩罚 ( v7.154.1: 调整惩罚系数)
                penalties = 0.0

                # 1. 内容长度惩罚 (降低惩罚)
                content_length = len(str(content)) if content else 0
                if content_length < 200:
                    penalties += 0.10  # 原 0.15
                    logger.debug(f"   内容过短惩罚: -0.10 (长度: {content_length})")
                elif content_length < 500:
                    penalties += 0.03  # 原 0.05
                    logger.debug(f"   内容较短惩罚: -0.03 (长度: {content_length})")

                # 2. 搜索引用惩罚 (降低惩罚)
                if real_search_refs_count == 0:
                    penalties += 0.05  # 原 0.1
                    logger.debug("   缺少搜索引用惩罚: -0.05")
                elif real_search_refs_count < 3:
                    penalties += 0.02  # 原 0.05
                    logger.debug(f"   搜索引用较少惩罚: -0.02 (数量: {real_search_refs_count})")

                # 3. 具体案例检测 (降低惩罚)
                content_str = str(content).lower() if content else ""
                case_keywords = ["案例", "例如", "比如", "实例", "case", "example"]
                has_cases = any(kw in content_str for kw in case_keywords)
                if not has_cases:
                    penalties += 0.03  # 原 0.05
                    logger.debug("   缺少具体案例惩罚: -0.03")

                # 4. 数据支撑检测 (降低惩罚)
                data_patterns = ["数据", "统计", "调研", "研究表明", "%", "比例", "增长"]
                has_data = any(pattern in content_str for pattern in data_patterns)
                if not has_data:
                    penalties += 0.02  # 原 0.03
                    logger.debug("   缺少数据支撑惩罚: -0.02")

                # 计算校准后的评分 ( v7.154.1: 提高最低分)
                calibrated_score = max(0.6, original_score - penalties)  # 原 0.5

                if penalties > 0:
                    deliverable_name = deliverable.get("deliverable_name", "未知")
                    logger.info(
                        f" [v7.154] 自评分校准: {deliverable_name} "
                        f"{original_score:.2f} → {calibrated_score:.2f} (惩罚: -{penalties:.2f})"
                    )
                    deliverable["quality_self_assessment"] = calibrated_score
                    deliverable["quality_calibration_note"] = f"原始评分{original_score:.2f}，校准后{calibrated_score:.2f}"

            return structured_output

        except Exception as e:
            logger.warning(f"️ [v7.154] 自评分校准失败: {e}")
            return structured_output

    def _extract_meaningful_content(self, raw_output: str) -> Any:
        """
        从原始输出中提取有意义的内容

        处理:
        1. Markdown 代码块包裹的 JSON
        2. 嵌套的 task_execution_report
        3. 直接返回解析后的结构化数据
        """
        if not raw_output:
            return "暂无输出"

        text = raw_output.strip()

        # 移除 markdown 代码块
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        # 尝试解析 JSON
        if text.startswith("{") or text.startswith("["):
            try:
                parsed = json.loads(text)

                # 如果是完整的 TaskOrientedExpertOutput 结构
                if isinstance(parsed, dict):
                    # 提取 deliverable_outputs 中的内容
                    ter = parsed.get("task_execution_report", {})
                    if ter:
                        deliverable_outputs = ter.get("deliverable_outputs", [])
                        if deliverable_outputs:
                            # 返回第一个交付物的内容
                            first = deliverable_outputs[0]
                            if isinstance(first, dict):
                                content = first.get("content")
                                if content:
                                    # 如果内容本身也是 JSON 字符串，递归处理
                                    if isinstance(content, str) and (
                                        content.strip().startswith("{") or content.strip().startswith("[")
                                    ):
                                        return self._extract_meaningful_content(content)
                                    return content

                    # 返回解析后的结构（让前端自行渲染）
                    return parsed

            except json.JSONDecodeError:
                pass

        # 返回清理后的文本
        return text

    def _validate_task_completion(self, structured_output: Dict[str, Any], task_instruction: Dict[str, Any]) -> bool:
        """
        验证任务完成情况，确保所有deliverables都已处理

         v7.9.3: 增强验证 - 检测到缺失交付物时标记需要补全，而非直接通过

        Returns:
            bool: True表示验证通过，False表示需要补全
        """
        if not structured_output:
            logger.warning("️ 无结构化输出，无法验证任务完成情况")
            return False

        try:
            # 获取任务指令中的预期交付物
            expected_deliverables = task_instruction.get("deliverables", [])

            # 获取实际的交付物输出（修复字段路径）
            task_exec_report = structured_output.get("task_execution_report", {})
            actual_results = task_exec_report.get("deliverable_outputs", [])

            # 如果没有预期交付物，则直接通过（降级场景）
            if not expected_deliverables:
                logger.info(" 无预期交付物要求，验证通过")
                return True

            expected_names = {d.get("name", f"交付物{i}") for i, d in enumerate(expected_deliverables, 1)}
            actual_names = {r.get("deliverable_name", "") for r in actual_results}

            missing_deliverables = expected_names - actual_names
            if missing_deliverables:
                logger.warning(f"️ 缺失交付物: {missing_deliverables}")
                #  v7.9.3: 不再直接返回True，而是标记需要补全
                if "validation_result" not in structured_output:
                    structured_output["validation_result"] = {}
                structured_output["validation_result"]["missing_deliverables"] = list(missing_deliverables)
                structured_output["validation_result"]["needs_completion"] = True
                structured_output["validation_result"]["expected_deliverables"] = expected_deliverables
                logger.info(f" 标记需要补全的交付物: {missing_deliverables}")
                return False  #  返回False表示验证未通过，需要补全

            # 验证协议执行状态（修复字段名）
            protocol_execution = structured_output.get("protocol_execution", {})
            if not protocol_execution.get("protocol_status"):
                logger.warning("️ 协议执行状态缺失")
                # 降级场景下不强制失败
                return True

            logger.info(" 任务完成验证通过")
            return True

        except Exception as e:
            logger.error(f" 验证任务完成时出错: {str(e)}")
            # 发生错误时也返回True，避免阻塞流程
            return True

    async def _complete_missing_deliverables(
        self, structured_output: Dict[str, Any], role_object: Dict[str, Any], context: str, state: ProjectAnalysisState
    ) -> Dict[str, Any]:
        """
         v7.11: 自动补全缺失的交付物（性能优化版）

        当检测到专家输出缺少部分交付物时，自动调用LLM补充缺失部分

        性能优化:
        - 限制每次补全最多3个交付物
        - 添加超时控制（30秒）
        - 如果缺失过多，优先补全核心交付物

        Args:
            structured_output: 当前的结构化输出（包含validation_result）
            role_object: 角色对象
            context: 项目上下文
            state: 当前状态

        Returns:
            Dict: 补全后的结构化输出
        """
        import asyncio

        try:
            validation_result = structured_output.get("validation_result", {})
            missing_deliverables = validation_result.get("missing_deliverables", [])
            expected_deliverables = validation_result.get("expected_deliverables", [])

            if not missing_deliverables:
                logger.warning("️ 没有缺失的交付物，无需补全")
                return structured_output

            #  v7.11: 性能优化 - 限制每次补全的数量
            MAX_COMPLETION_COUNT = 3
            if len(missing_deliverables) > MAX_COMPLETION_COUNT:
                logger.warning(f"️ 缺失交付物过多({len(missing_deliverables)}个)，只补全前{MAX_COMPLETION_COUNT}个")
                missing_deliverables = missing_deliverables[:MAX_COMPLETION_COUNT]

            logger.info(f" 开始补全缺失的交付物: {missing_deliverables}")

            # 构建补全提示词
            completion_prompt = self._build_completion_prompt(
                role_object=role_object,
                context=context,
                state=state,
                missing_deliverables=missing_deliverables,
                expected_deliverables=expected_deliverables,
                existing_output=structured_output,
            )

            #  v7.11: 添加超时控制（30秒）
            #  v7.52: 使用 JSON 模式强制 JSON 输出
            llm = self._get_llm()

            # 尝试使用 with_structured_output (JSON模式)
            try:
                llm_json_mode = llm.with_structured_output(method="json_mode")
                logger.info(" [v7.52] 使用 JSON 模式强制输出")
            except Exception as e:
                logger.debug(f"️ JSON模式不可用，使用普通模式: {e}")
                llm_json_mode = llm

            messages = [
                {"role": "system", "content": completion_prompt["system_prompt"]},
                {"role": "user", "content": completion_prompt["user_prompt"]},
            ]

            try:
                response = await asyncio.wait_for(llm_json_mode.ainvoke(messages), timeout=30.0)  # 30秒超时
                completion_output = response.content if hasattr(response, "content") else str(response)
            except asyncio.TimeoutError:
                logger.warning("️ 交付物补全超时（30秒），使用原始输出")
                return structured_output

            # 解析补充的交付物
            completed_deliverables = self._parse_completion_output(completion_output, missing_deliverables)

            #  v7.52: 批量失败时尝试逐个生成
            if not completed_deliverables and len(missing_deliverables) > 1:
                logger.warning(f"️ 批量补全失败，尝试逐个生成 {len(missing_deliverables)} 个交付物")
                completed_deliverables = await self._complete_deliverables_one_by_one(
                    role_object, context, state, missing_deliverables
                )

            #  v7.23: 更准确的日志信息
            if not completed_deliverables:
                logger.warning(f"️ 交付物补全完全失败：尝试补全 {len(missing_deliverables)} 个，实际解析出 0 个")
                #  v7.52: 生成占位符，避免完全失败
                completed_deliverables = self._generate_placeholder_deliverables(missing_deliverables)
                logger.info(f" [v7.52] 已生成 {len(completed_deliverables)} 个占位交付物")

            # 合并到原始输出
            task_exec_report = structured_output.get("task_execution_report", {})
            deliverable_outputs = task_exec_report.get("deliverable_outputs", [])

            # 添加补充的交付物
            for deliverable in completed_deliverables:
                deliverable_outputs.append(deliverable)
                logger.info(f" 已补全交付物: {deliverable.get('deliverable_name')}")

            # 更新结构化输出
            task_exec_report["deliverable_outputs"] = deliverable_outputs
            structured_output["task_execution_report"] = task_exec_report

            # 清除validation_result标记
            if "validation_result" in structured_output:
                del structured_output["validation_result"]

            logger.info(f" 成功补全 {len(completed_deliverables)}/{len(missing_deliverables)} 个交付物")
            return structured_output

        except Exception as e:
            logger.error(f" 补全缺失交付物时出错: {str(e)}")
            # 发生错误时返回原始输出，不阻塞流程
            logger.warning("️ 补全失败，使用原始输出")
            return structured_output

    def _build_completion_prompt(
        self,
        role_object: Dict[str, Any],
        context: str,
        state: ProjectAnalysisState,
        missing_deliverables: List[str],
        expected_deliverables: List[Dict[str, Any]],
        existing_output: Dict[str, Any],
    ) -> Dict[str, str]:
        """
         v7.9.3: 构建补全提示词，只要求LLM输出缺失的交付物

        Args:
            role_object: 角色对象
            context: 项目上下文
            state: 当前状态
            missing_deliverables: 缺失的交付物名称列表
            expected_deliverables: 预期的所有交付物定义
            existing_output: 已有的输出（用于上下文）

        Returns:
            Dict: 包含system_prompt和user_prompt的字典
        """
        # 筛选出缺失的交付物定义
        missing_defs = [d for d in expected_deliverables if d.get("name") in missing_deliverables]

        # 获取已完成的交付物（作为参考）
        existing_deliverables = existing_output.get("task_execution_report", {}).get("deliverable_outputs", [])
        existing_names = [d.get("deliverable_name") for d in existing_deliverables]

        system_prompt = f"""
你是 {role_object.get('dynamic_role_name', role_object.get('role_name'))}。

#  补全任务

你之前已经完成了部分交付物：{', '.join(existing_names)}

但还有以下交付物**尚未完成**，需要你现在补充：

"""
        for i, deliverable in enumerate(missing_defs, 1):
            system_prompt += f"""
**缺失交付物 {i}: {deliverable.get('name')}**
- 描述: {deliverable.get('description', '')}
- 格式: {deliverable.get('format', 'analysis')}
- 成功标准: {', '.join(deliverable.get('success_criteria', []))}
"""

        system_prompt += """

#  输出要求

**请只输出缺失的交付物**，格式如下：

```json
{
  "deliverable_outputs": [
    {
      "deliverable_name": "缺失交付物的名称（必须与上面列出的名称完全一致）",
      "content": "详细的分析内容（完整、专业、符合成功标准）",
      "completion_status": "completed",
      "completion_rate": 0.95,
      "notes": "补充说明",
      "quality_self_assessment": 0.9
    }
  ]
}
```

# ️ 关键要求

1. **只输出缺失的交付物**，不要重复已完成的交付物
2. **deliverable_name必须与任务指令中的名称完全一致**
3. **content要详细完整**，不要简化或省略
4. **返回有效的JSON格式**，不要有额外文字
5. **不要使用markdown代码块包裹JSON**

开始补充缺失的交付物：
"""

        user_prompt = f"""
#  项目上下文
{context}

#  当前项目状态
- 项目阶段: {state.get('current_phase', '分析阶段')}
- 已完成分析: {len(state.get('expert_analyses', {}))}个专家

#  你的任务

请基于上述项目上下文，补充以下缺失的交付物：
{', '.join(missing_deliverables)}

**记住**：只输出缺失的交付物，格式为JSON，不要有任何额外文字。
"""

        return {"system_prompt": system_prompt, "user_prompt": user_prompt}

    def _parse_completion_output(self, completion_output: str, missing_deliverables: List[str]) -> List[Dict[str, Any]]:
        """
         v7.9.3: 解析补全输出，提取交付物列表
         v7.23: 增强 JSON 解析容错性，支持多种格式

        Args:
            completion_output: LLM返回的补全内容
            missing_deliverables: 预期的缺失交付物名称列表

        Returns:
            List[Dict]: 解析后的交付物列表
        """
        import re

        try:
            json_str = None

            # 策略1: 提取 ```json ... ``` 代码块
            if "```json" in completion_output:
                json_start = completion_output.find("```json") + 7
                json_end = completion_output.find("```", json_start)
                if json_end > json_start:
                    json_str = completion_output[json_start:json_end].strip()

            # 策略2: 提取 ``` ... ``` 代码块（无语言标识）
            if not json_str and "```" in completion_output:
                matches = re.findall(r"```\s*([\s\S]*?)\s*```", completion_output)
                for match in matches:
                    if "{" in match and "}" in match:
                        json_str = match.strip()
                        break

            # 策略3: 提取最外层 {...} 或 [...]
            if not json_str:
                # 优先尝试提取对象
                obj_match = re.search(r"\{[\s\S]*\}", completion_output)
                if obj_match:
                    json_str = obj_match.group()
                else:
                    # 尝试提取数组
                    arr_match = re.search(r"\[[\s\S]*\]", completion_output)
                    if arr_match:
                        json_str = arr_match.group()

            if not json_str:
                logger.warning("️ 补全输出不包含有效JSON结构")
                return []

            #  v7.23: 清理常见的 JSON 格式问题
            # 移除 JavaScript 风格的注释
            json_str = re.sub(r"//.*?(?=\n|$)", "", json_str)
            json_str = re.sub(r"/\*.*?\*/", "", json_str, flags=re.DOTALL)
            # 移除尾随逗号
            json_str = re.sub(r",(\s*[}\]])", r"\1", json_str)

            # 解析JSON
            parsed = json.loads(json_str)

            # 提取deliverable_outputs（支持多种字段名）
            if isinstance(parsed, dict):
                deliverables = (
                    parsed.get("deliverable_outputs") or parsed.get("deliverables") or parsed.get("outputs") or []
                )
                if deliverables:
                    logger.info(f" 成功解析 {len(deliverables)} 个补全交付物")
                    return deliverables
                else:
                    logger.warning("️ 解析的JSON中没有deliverable_outputs字段")
                    return []
            elif isinstance(parsed, list):
                # 如果直接返回数组
                if parsed:
                    logger.info(f" 成功解析 {len(parsed)} 个补全交付物（数组格式）")
                    return parsed
                return []
            else:
                logger.warning(f"️ 解析结果类型不符合预期: {type(parsed)}")
                return []

        except json.JSONDecodeError as e:
            logger.error(f" 解析补全输出JSON失败: {str(e)}")
            logger.debug(f"原始输出片段: {completion_output[:300]}...")

            #  v7.23: 尝试从原始输出构造默认交付物
            fallback_deliverables = []
            for name in missing_deliverables[:2]:  # 最多构造2个
                fallback_deliverables.append(
                    {
                        "deliverable_name": name,
                        "content": f"[解析失败，需要人工补充] 原始输出: {completion_output[:200]}...",
                        "completion_status": "partial",
                        "completion_rate": 0.3,
                        "notes": "LLM输出格式异常，已使用降级策略",
                    }
                )
            if fallback_deliverables:
                logger.warning(f"️ 使用降级策略，构造 {len(fallback_deliverables)} 个占位交付物")
            return fallback_deliverables

        except Exception as e:
            logger.error(f" 处理补全输出时出错: {str(e)}")
            return []

    async def _complete_deliverables_one_by_one(
        self, role_object: Dict[str, Any], context: str, state: ProjectAnalysisState, missing_deliverables: List[str]
    ) -> List[Dict[str, Any]]:
        """
         v7.52: 逐个生成缺失交付物（降级策略）

        当批量生成失败时，尝试逐个生成每个交付物，
        提高成功率。

        Args:
            role_object: 角色对象
            context: 项目上下文
            state: 当前状态
            missing_deliverables: 缺失的交付物名称列表

        Returns:
            List[Dict]: 生成的交付物列表
        """
        import asyncio

        completed = []
        llm = self._get_llm()

        for deliverable_name in missing_deliverables:
            try:
                logger.info(f" 逐个生成: {deliverable_name}")

                # 构建单个交付物的提示词
                single_prompt = f"""你是 {role_object.get('name', '专家')}。

请生成以下交付物：
**{deliverable_name}**

#  项目上下文
{context[:1000]}...

#  要求
1. 输出JSON格式，包含以下字段：
   - deliverable_name: "{deliverable_name}"
   - content: 详细内容
   - key_insights: 关键洞察（列表）
   - completion_rate: 完成度（0-1）

2. 直接返回JSON，不要有额外文字

输出示例：
{{
  "deliverable_name": "{deliverable_name}",
  "content": "...",
  "key_insights": ["洞察1", "洞察2"],
  "completion_rate": 1.0
}}
"""

                # 调用LLM（10秒超时）
                response = await asyncio.wait_for(
                    llm.ainvoke([{"role": "user", "content": single_prompt}]), timeout=10.0
                )
                output = response.content if hasattr(response, "content") else str(response)

                # 解析单个交付物
                single_result = self._parse_single_deliverable_output(output, deliverable_name)
                if single_result:
                    completed.append(single_result)
                    logger.info(f" 成功生成: {deliverable_name}")
                else:
                    logger.warning(f"️ 解析失败: {deliverable_name}")

            except asyncio.TimeoutError:
                logger.warning(f"️ 生成超时: {deliverable_name}")
            except Exception as e:
                logger.error(f" 生成失败 {deliverable_name}: {e}")

            # 限制最多尝试3个
            if len(completed) >= 3:
                logger.info(" 已成功生成3个交付物，停止逐个生成")
                break

        return completed

    def _parse_single_deliverable_output(self, output: str, expected_name: str) -> Dict[str, Any] | None:
        """
         v7.52: 解析单个交付物的LLM输出

        Args:
            output: LLM原始输出
            expected_name: 期望的交付物名称

        Returns:
            Dict | None: 解析成功返回交付物字典，失败返回None
        """
        import json
        import re

        try:
            # 提取JSON
            json_str = None
            if "```json" in output:
                json_start = output.find("```json") + 7
                json_end = output.find("```", json_start)
                if json_end > json_start:
                    json_str = output[json_start:json_end].strip()
            elif "```" in output:
                matches = re.findall(r"```\s*([\s\S]*?)\s*```", output)
                for match in matches:
                    if "{" in match:
                        json_str = match.strip()
                        break

            if not json_str:
                obj_match = re.search(r"\{[\s\S]*\}", output)
                if obj_match:
                    json_str = obj_match.group()

            if not json_str:
                return None

            # 解析JSON
            parsed = json.loads(json_str)

            # 验证必需字段
            if not parsed.get("deliverable_name"):
                parsed["deliverable_name"] = expected_name

            if not parsed.get("content"):
                return None

            # 补充可选字段
            if "completion_rate" not in parsed:
                parsed["completion_rate"] = 0.8
            if "key_insights" not in parsed:
                parsed["key_insights"] = []

            return parsed

        except Exception as e:
            logger.debug(f"️ 单个交付物解析失败: {e}")
            return None

    def _generate_placeholder_deliverables(self, missing_names: List[str]) -> List[Dict[str, Any]]:
        """
         v7.52: 生成占位交付物（最终降级策略）

        当所有生成策略都失败时，生成占位内容，
        避免流程完全失败。

        Args:
            missing_names: 缺失的交付物名称列表

        Returns:
            List[Dict]: 占位交付物列表
        """
        placeholders = []
        for name in missing_names[:3]:  # 最多3个
            placeholders.append(
                {
                    "deliverable_name": name,
                    "content": f"[待补充] {name}\n\n由于LLM生成失败，此交付物需要人工补充。建议审查项目需求后手动完成。",
                    "completion_status": "pending",
                    "completion_rate": 0.0,
                    "key_insights": [],
                    "notes": " v7.52: 自动生成的占位内容，需要人工补充",
                }
            )
        return placeholders

    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _extract_full_deliverable_content(self, structured_output: Dict[str, Any]) -> str:
        """
         v7.128: 提取所有交付物的完整内容（用于概念图生成）

        Args:
            structured_output: 专家结构化输出

        Returns:
            拼接后的完整内容（包含设计理念、空间布局、材料选型等所有细节）
            格式：## 交付物名称1\n\n详细内容...\n\n## 交付物名称2\n\n详细内容...
        """
        task_exec_report = structured_output.get("task_execution_report", {})
        deliverable_outputs = task_exec_report.get("deliverable_outputs", [])

        full_content = []
        for deliverable in deliverable_outputs:
            name = deliverable.get("deliverable_name", "")
            content = deliverable.get("content", "")
            if content:
                full_content.append(f"## {name}\n\n{content}")

        result = "\n\n".join(full_content) if full_content else ""
        logger.debug(f"[v7.128] 提取完整内容长度: {len(result)} 字符")
        return result

    def _extract_deliverable_specific_content(
        self, structured_output: Dict[str, Any], deliverable_metadata: dict
    ) -> str:
        """
         v7.128: 提取特定交付物的完整分析内容

        Args:
            structured_output: 专家结构化输出
            deliverable_metadata: 交付物元数据（包含name）

        Returns:
            该交付物的完整分析内容（最多3000字）
        """
        deliverable_name = deliverable_metadata.get("name", "")

        task_exec_report = structured_output.get("task_execution_report", {})
        deliverable_outputs = task_exec_report.get("deliverable_outputs", [])

        # 精准匹配交付物名称
        for deliverable in deliverable_outputs:
            if deliverable.get("deliverable_name") == deliverable_name:
                content = deliverable.get("content", "")
                limited_content = content[:3000]  # 限制3000字
                logger.info(f"[v7.128] 为交付物 '{deliverable_name}' 提取专家分析: {len(limited_content)} 字符")
                return limited_content

        # 降级：返回所有内容的拼接
        all_content = "\n\n".join(d.get("content", "") for d in deliverable_outputs)
        limited_content = all_content[:3000]
        logger.warning(f"[v7.128] 未找到交付物 '{deliverable_name}' 的精准匹配，返回所有内容: {len(limited_content)} 字符")
        return limited_content

    async def _execute_fallback_search(
        self,
        role_object: Dict[str, Any],
        context: str,
        state: ProjectAnalysisState,
        tools: List[Any] | None = None,
    ) -> List[Dict[str, Any]]:
        """
         v7.129 Week2 P2: 执行降级搜索

        当LLM未主动调用工具时，系统自动执行搜索作为后备方案，
        确保至少有基本的搜索引用。优先级: Serper > Tavily > Bocha (v7.130+)

        Args:
            role_object: 角色对象
            context: 项目上下文
            state: 当前状态
            tools: 可用的工具列表

        Returns:
            搜索引用列表
        """
        role_id = role_object.get("role_id", "unknown")
        logger.info(f" [v7.129 Fallback] {role_id} 开始执行降级搜索")

        search_references = []

        try:
            # 1. 从tools中找到搜索工具（优先博查 → Tavily → Milvus）
            bocha_tool = None
            tavily_tool = None
            serper_tool = None

            if tools:
                for tool in tools:
                    tool_name = getattr(tool, "name", "")
                    if "bocha" in tool_name.lower():
                        bocha_tool = tool
                    elif "tavily" in tool_name.lower():
                        tavily_tool = tool
                    elif "serper" in tool_name.lower():
                        serper_tool = tool

            # 2. 如果tools中没有，从ToolFactory创建（博查优先）
            if not bocha_tool and not tavily_tool and not serper_tool:
                logger.info(f" [v7.129 Fallback] {role_id} 从ToolFactory创建搜索工具")
                from ..services.tool_factory import ToolFactory

                try:
                    bocha_tool = ToolFactory.create_bocha_tool()
                    logger.info(" [v7.129 Fallback] 博查工具创建成功（优先）")
                except Exception as e:
                    logger.warning(f"️ [v7.129 Fallback] 博查工具创建失败: {e}")
                    try:
                        tavily_tool = ToolFactory.create_tavily_tool()
                        logger.info(" [v7.129 Fallback] Tavily工具创建成功（降级）")
                    except Exception as e2:
                        logger.warning(f"️ [v7.129 Fallback] Tavily工具也创建失败: {e2}")
                        try:
                            serper_tool = ToolFactory.create_serper_tool()
                            logger.info(" [v7.129 Fallback] Serper工具创建成功（二次降级）")
                        except Exception as e3:
                            logger.error(f" [v7.129 Fallback] 所有搜索工具创建失败: {e3}")

            # 3. 提取搜索查询关键词
            task_instruction = role_object.get("task_instruction", {})
            deliverables = task_instruction.get("deliverables", [])

            # 构建基本搜索查询
            user_input = state.get("user_input", "")
            base_query = user_input[:100] if user_input else context[:100]

            # 生成搜索查询列表（最多3个）
            search_queries = []

            # Query 1: 基于用户输入
            if user_input:
                search_queries.append(base_query + " 设计案例 2025")

            # Query 2: 基于第一个deliverable
            if deliverables and len(deliverables) > 0:
                first_deliverable = deliverables[0].get("name", "")
                if first_deliverable:
                    search_queries.append(f"{first_deliverable} 最佳实践")

            # Query 3: 基于角色名称
            role_name = role_object.get("dynamic_role_name", role_object.get("role_name", ""))
            if role_name:
                search_queries.append(f"{role_name} 专业分析方法")

            # 确保至少有1个查询
            if not search_queries:
                search_queries.append(base_query)

            # 限制最多3个查询
            search_queries = search_queries[:3]

            logger.info(f" [v7.129 Fallback] {role_id} 执行 {len(search_queries)} 个搜索查询")

            # 4. 执行搜索
            for idx, query in enumerate(search_queries, 1):
                try:
                    logger.info(f"   [{idx}/{len(search_queries)}] 查询: {query[:50]}...")

                    #  智能语言感知路由：根据查询语言选择最佳工具
                    # 策略：中文查询 → 博查（中文专用）→ Tavily（全球覆盖）→ Serper
                    #      英文查询 → Tavily（全球覆盖）→ 博查 → Serper

                    def is_chinese_query(text: str) -> bool:
                        """判断是否为中文查询（包含中文字符）"""
                        return any("\u4e00" <= char <= "\u9fff" for char in text)

                    is_chinese = is_chinese_query(query)

                    #  v7.131: 语言感知路由 - 中文查询优先使用博查
                    if is_chinese:
                        # 中文查询: Bocha → Tavily → Serper
                        tool_to_use = bocha_tool if bocha_tool else (tavily_tool if tavily_tool else serper_tool)
                        if bocha_tool:
                            logger.info(f" [Fallback] 中文查询 '{query[:30]}...'，使用博查（中文专用）")
                        elif tavily_tool:
                            logger.warning("️ [Fallback] 博查不可用，降级至Tavily")
                        elif serper_tool:
                            logger.warning("️ [Fallback] 博查和Tavily不可用，降级至Serper")
                    else:
                        # 英文查询: Tavily → Bocha → Serper
                        tool_to_use = tavily_tool if tavily_tool else (bocha_tool if bocha_tool else serper_tool)
                        if tavily_tool:
                            logger.info(" [Fallback] 英文查询，使用Tavily（全球覆盖）")
                        elif bocha_tool:
                            logger.warning("️ [Fallback] Tavily不可用，降级至博查")
                        elif serper_tool:
                            logger.warning("️ [Fallback] Tavily和博查不可用，降级至Serper")

                    if not tool_to_use:
                        logger.error(" [v7.129 Fallback] 无可用搜索工具")
                        break

                    # 调用工具
                    search_result = await tool_to_use.ainvoke({"query": query})

                    # 解析结果
                    if isinstance(search_result, dict):
                        results_list = search_result.get("results", [])
                    elif isinstance(search_result, list):
                        results_list = search_result
                    else:
                        # 尝试解析字符串结果
                        import json

                        try:
                            parsed = json.loads(str(search_result))
                            results_list = parsed.get("results", []) if isinstance(parsed, dict) else []
                        except:
                            logger.warning(f"️ [v7.129 Fallback] 无法解析搜索结果: {type(search_result)}")
                            results_list = []

                    # 转换为search_references格式
                    for result in results_list[:5]:  # 每个查询最多5条结果
                        ref = {
                            "title": result.get("title", ""),
                            "url": result.get("url", ""),
                            "snippet": result.get("snippet", result.get("content", ""))[:500],
                            "source": f"fallback_{tool_to_use.name}"
                            if hasattr(tool_to_use, "name")
                            else "fallback_search",
                            "query": query,
                            "role_id": role_id,
                            "deliverable_id": f"{role_id}_fallback",
                            "timestamp": self._get_timestamp(),
                        }
                        search_references.append(ref)

                    logger.info(f"    查询{idx}获得 {len(results_list)} 条结果")

                except Exception as search_error:
                    logger.error(f"    查询{idx}失败: {search_error}")
                    continue

            logger.info(f" [v7.129 Fallback] {role_id} 降级搜索完成，共获得 {len(search_references)} 条引用")

        except Exception as e:
            logger.error(f" [v7.129 Fallback] {role_id} 降级搜索异常: {e}")
            import traceback

            traceback.print_exc()

        return search_references


# 兼容性接口：为现有代码提供平滑过渡
class SpecializedAgentFactory:
    """
    兼容性包装器 - 逐步迁移到TaskOrientedExpertFactory
    """

    def __init__(self):
        self._task_oriented_factory = TaskOrientedExpertFactory()
        self._legacy_mode = True  # 可以通过配置切换

    async def execute_expert(
        self, role_object: Dict[str, Any], context: str, state: ProjectAnalysisState
    ) -> Dict[str, Any]:
        """
        执行专家分析 - 自动选择任务导向或传统模式
        """
        # 检查是否有TaskInstruction，决定使用哪种模式
        if "task_instruction" in role_object and not self._legacy_mode:
            logger.info(f" 使用任务导向模式执行专家: {role_object.get('role_name')}")
            return await self._task_oriented_factory.execute_expert(role_object, context, state)
        else:
            # 降级到传统模式（保持原有逻辑）
            logger.info(f" 使用传统模式执行专家: {role_object.get('role_name')}")
            return await self._execute_legacy_expert(role_object, context, state)

    async def _execute_legacy_expert(
        self, role_object: Dict[str, Any], context: str, state: ProjectAnalysisState
    ) -> Dict[str, Any]:
        """
        传统专家执行模式（向后兼容）
        """
        try:
            # 这里可以保留原有的执行逻辑
            # 或者调用原始的specialized_agent_factory
            logger.warning("Legacy expert execution not fully implemented - using basic fallback")

            return {
                "expert_id": role_object.get("role_id", "unknown"),
                "expert_name": role_object.get("dynamic_role_name", role_object.get("role_name", "Unknown Expert")),
                "analysis": "Legacy mode placeholder analysis",
                "structured_output": None,
                "role_definition": role_object,
                "execution_metadata": {
                    "timestamp": self._task_oriented_factory._get_timestamp(),
                    "model_used": "gpt-4",
                    "prompt_version": "legacy",
                    "mode": "fallback",
                },
            }

        except Exception as e:
            logger.error(f"传统专家执行失败: {str(e)}")
            return {
                "expert_id": role_object.get("role_id", "unknown"),
                "expert_name": role_object.get("role_name", "Unknown Expert"),
                "analysis": f"执行失败: {str(e)}",
                "error": True,
            }
