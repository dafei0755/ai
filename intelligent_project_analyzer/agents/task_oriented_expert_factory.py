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
from ._task_expert_parser_mixin import ExpertOutputParserMixin
from ._task_expert_completion_mixin import ExpertCompletionMixin

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


class TaskOrientedExpertFactory(ExpertOutputParserMixin, ExpertCompletionMixin):
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
