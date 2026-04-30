"""
动态项目总监智能体 - Dynamic Project Director Agent

基于角色配置系统的项目总监,负责分析需求并选择合适的专业角色。
Project Director based on role configuration system.
"""

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from langchain_core.exceptions import OutputParserException
from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger
from pydantic import BaseModel, Field, ValidationError, model_validator

from intelligent_project_analyzer.core.prompt_manager import PromptManager
from intelligent_project_analyzer.core.role_manager import RoleManager
from intelligent_project_analyzer.core.task_oriented_models import (
    DeliverableFormat,
    DeliverableSpec,
    DeliverableWorkPackage,
    Priority,
    TaskInstruction,
    generate_task_instruction_template,
)


def format_for_log(obj: Any) -> str:
    """
    格式化对象用于日志输出，避免 Unicode 转义

    Args:
        obj: 要格式化的对象

    Returns:
        格式化后的字符串，中文不会被转义
    """
    if isinstance(obj, (dict, list)):
        return json.dumps(obj, ensure_ascii=False, indent=2)
    elif isinstance(obj, BaseException):
        # 对于异常对象，提取可读的错误信息
        return json.dumps(str(obj), ensure_ascii=False)
    else:
        return str(obj)


class TaskDetail(BaseModel):
    """任务详情"""

    tasks: List[str] = Field(description="具体任务列表，每个任务应该详细、可执行", min_length=1)
    focus_areas: List[str] = Field(default_factory=list, description="重点关注领域")
    expected_output: str = Field(default="", description="期望输出描述")
    dependencies: List[str] = Field(default_factory=list, description="依赖的其他角色ID")


def build_dwps_from_role_selection(
    selection: "RoleSelection",
    confirmed_tasks: Optional[List[Dict[str, Any]]] = None,
    questionnaire_summary: Optional[Dict[str, Any]] = None,
) -> List[DeliverableWorkPackage]:
    """
    从 RoleSelection 后处理生成 DWP 列表。

    将每个角色的每个 deliverable 映射为一个 DWP，保留 source_task_ids 追溯链。
    如果 LLM 未填充 source_task_ids，则尝试基于关键词模糊匹配回填。

    v10.0: 注入 visual_type 和 keywords 字段，供 deliverable_id_generator 和概念图使用。

    Args:
        selection: LLM 返回的 RoleSelection 结果
        confirmed_tasks: 用户确认的核心任务列表（用于回填 source_task_ids）
        questionnaire_summary: 问卷摘要（用于提取关键词）

    Returns:
        DWP 列表
    """
    # v10.0: 角色类型 → 视觉身份映射
    _VISUAL_TYPE_MAP = {
        "V2": "photorealistic_rendering",
        "V3": "artistic_rendering",
        "V4": "artistic_rendering",
        "V5": "artistic_rendering",
        "V6": "technical_blueprint",
        "V7": "emotional_atmosphere",
    }

    # v10.0: 提取问卷关键词
    _questionnaire_keywords: List[str] = []
    if questionnaire_summary:
        answers = questionnaire_summary.get("answers", {})
        gap_answers = answers.get("gap_answers", {})
        for _k, v in gap_answers.items():
            if isinstance(v, str) and len(v) > 2:
                _questionnaire_keywords.append(v[:50])
        profile = questionnaire_summary.get("profile_label", "")
        if profile:
            _questionnaire_keywords.append(profile)

    dwps: List[DeliverableWorkPackage] = []
    dwp_counter = 1

    for role in selection.selected_roles:
        role_id = role.role_id
        ti = role.task_instruction

        # v10.0: 确定角色基础类型和视觉身份
        role_base_type = f"V{role_id.split('-')[0]}" if '-' in role_id else "V2"
        visual_type = _VISUAL_TYPE_MAP.get(role_base_type, "artistic_rendering")

        for deliverable in ti.deliverables:
            # 提取 source_task_ids（LLM 可能已填写）
            source_ids = getattr(deliverable, "source_task_ids", []) or []

            # 如果 LLM 未填写，尝试关键词回填
            if not source_ids and confirmed_tasks:
                source_ids = _fuzzy_match_task_ids(
                    deliverable_name=deliverable.name,
                    deliverable_desc=deliverable.description,
                    confirmed_tasks=confirmed_tasks,
                )

            dwp_id = f"DWP-{dwp_counter:03d}"
            dwp_counter += 1

            try:
                dwp = DeliverableWorkPackage(
                    dwp_id=dwp_id,
                    name=deliverable.name,
                    description=deliverable.description,
                    deliverable_type=_infer_deliverable_type(deliverable),
                    format=deliverable.format,
                    source_task_ids=source_ids if source_ids else ["UNLINKED"],
                    owner_role_id=role_id,
                    contributor_role_ids=[],
                    depends_on=[],
                    priority=deliverable.priority,
                    success_criteria=deliverable.success_criteria[:4]
                    if deliverable.success_criteria
                    else ["完成交付物"],
                    constraints=[],
                    require_search=getattr(deliverable, "require_search", False),
                    visual_type=visual_type,
                    keywords=_questionnaire_keywords[:10] if _questionnaire_keywords else [],
                )
                dwps.append(dwp)
            except Exception as e:
                logger.warning(f"⚠️ 构建 DWP-{dwp_counter - 1:03d} 失败: {e}")

    # 推断 DWP 间依赖（基于角色依赖关系）
    _infer_dwp_dependencies(dwps, selection)

    logger.info(f"✅ 从 RoleSelection 构建了 {len(dwps)} 个 DWP")
    return dwps


def _fuzzy_match_task_ids(
    deliverable_name: str,
    deliverable_desc: str,
    confirmed_tasks: List[Dict[str, Any]],
    threshold: float = 0.3,
) -> List[str]:
    """
    基于关键词重叠度模糊匹配 deliverable → task_id。

    v9.2 fix: 增强中文分词支持，原实现仅 split() 无法处理中文文本。
    使用字符级 n-gram + 空格分词双模式提升匹配率。
    """
    d_text = f"{deliverable_name} {deliverable_desc}".lower()
    d_words = set(d_text.split())
    # v9.2: 添加中文字符级 2-gram 以支持中文匹配
    d_chars = set()
    for ch_i in range(len(d_text) - 1):
        bigram = d_text[ch_i:ch_i+2].strip()
        if len(bigram) == 2 and bigram != "  ":
            d_chars.add(bigram)

    matched_ids = []
    for task in confirmed_tasks:
        task_id = task.get("task_id") or task.get("id", "")
        if not task_id:
            continue
        t_text = f"{task.get('title', '')} {task.get('description', '')}".lower()
        t_words = set(t_text.split())
        t_chars = set()
        for ch_i in range(len(t_text) - 1):
            bigram = t_text[ch_i:ch_i+2].strip()
            if len(bigram) == 2 and bigram != "  ":
                t_chars.add(bigram)

        if not t_words and not t_chars:
            continue

        # 计算两种重叠率取较高值
        word_overlap = len(d_words & t_words) / max(len(t_words), 1) if t_words else 0
        char_overlap = len(d_chars & t_chars) / max(len(t_chars), 1) if t_chars else 0
        overlap = max(word_overlap, char_overlap)

        if overlap >= threshold:
            matched_ids.append(task_id)

    return matched_ids


def _infer_deliverable_type(deliverable: DeliverableSpec) -> str:
    """从 deliverable 的 format 推断 deliverable_type"""
    fmt = deliverable.format
    if isinstance(fmt, DeliverableFormat):
        fmt_val = fmt.value
    else:
        fmt_val = str(fmt).lower()

    type_map = {
        "analysis": "analysis_report",
        "report": "analysis_report",
        "design": "design_plan",
        "plan": "design_plan",
        "strategy": "strategy_document",
        "recommendation": "recommendation_set",
        "comparison": "comparison_matrix",
        "case_study": "case_study_collection",
        "checklist": "checklist",
        "visualization": "visualization",
        "guideline": "guideline",
    }
    return type_map.get(fmt_val, "analysis_report")


def _infer_dwp_dependencies(
    dwps: List[DeliverableWorkPackage],
    selection: "RoleSelection",
) -> None:
    """
    根据角色间的 dependencies 关系推断 DWP 间依赖。

    逻辑：如果 role_A 依赖 role_B，则 role_A 的所有 DWP 依赖 role_B 的所有 DWP。
    """
    # 建立 role_id → [dwp_id] 映射
    role_to_dwps: Dict[str, List[str]] = {}
    for dwp in dwps:
        role_to_dwps.setdefault(dwp.owner_role_id, []).append(dwp.dwp_id)

    # 建立角色依赖映射
    for role in selection.selected_roles:
        dep_dwp_ids: List[str] = []
        for dep_role_id in role.dependencies:
            dep_dwp_ids.extend(role_to_dwps.get(dep_role_id, []))

        if dep_dwp_ids:
            for dwp in dwps:
                if dwp.owner_role_id == role.role_id:
                    dwp.depends_on = list(set(dwp.depends_on + dep_dwp_ids))


class RoleObject(BaseModel):
    """角色对象 - 包含角色的完整信息（更新为任务导向）"""

    role_id: str = Field(description="角色ID (如 '2-1')")
    role_name: str = Field(description="角色基础名称 (如 '居住空间设计总监')")
    dynamic_role_name: str = Field(
        description="动态角色名称 - 反映本次任务中的具体职责 (如 '三代同堂居住空间与生活模式总设计师')"
    )

    #  使用新的TaskInstruction替代分散的字段
    task_instruction: TaskInstruction = Field(
        description="统一的任务执行指令（合并了tasks、expected_output、focus_areas）"
    )

    dependencies: List[str] = Field(default_factory=list, description="这个动态角色的启动依赖")
    execution_priority: int = Field(default=1, description="执行优先级（1最高）")

    #  保持兼容性的属性（自动从task_instruction生成）
    @property
    def tasks(self) -> List[str]:
        """向后兼容：从task_instruction生成任务列表"""
        return [d.description for d in self.task_instruction.deliverables]

    @property
    def expected_output(self) -> str:
        """向后兼容：从task_instruction生成预期输出"""
        return self.task_instruction.objective

    @property
    def focus_areas(self) -> List[str]:
        """向后兼容：从task_instruction生成关注领域"""
        return [d.name for d in self.task_instruction.deliverables]


class RoleSelection(BaseModel):
    """角色选择结果"""

    selected_roles: List[RoleObject] = Field(
        description="选中的角色对象列表，每个对象包含完整的角色信息和任务分配", min_length=3, max_length=8
    )
    reasoning: str = Field(description="选择这些角色的详细理由,解释为什么这些角色最适合完成任务", min_length=50)

    # v9.0: 框架选择 — LLM 根据项目特征主动选择分析框架
    analysis_framework: Optional[str] = Field(
        default="ability_core",
        description="本项目推荐的分析框架ID，默认 ability_core。可选值参见 analysis_frameworks.yaml",
    )

    #  保留 task_distribution 字段以兼容旧代码，但自动从 selected_roles 生成
    @property
    def task_distribution(self) -> Dict[str, Union[TaskDetail, str]]:
        """从 selected_roles 自动生成 task_distribution 以兼容旧代码"""
        distribution: Dict[str, Union[TaskDetail, str]] = {}
        for role in self.selected_roles:
            # 构造完整的角色ID (如 "V2_设计总监_2-1")
            full_id = self._construct_full_role_id(role.role_id)
            distribution[full_id] = TaskDetail(
                tasks=role.tasks,
                focus_areas=role.focus_areas,
                expected_output=role.expected_output,
                dependencies=role.dependencies,
            )
        return distribution

    def _construct_full_role_id(self, role_id: str) -> str:
        """
        根据 role_id 构造完整的角色ID

        注意: 使用配置文件的实际键名（主角色名称/静态），而非LLM生成的动态名称
        - V3: "叙事与体验专家" (配置文件) vs "人物及叙事专家" (LLM生成)
        - V5: "场景与行业专家" (配置文件) vs "场景与用户生态专家" (LLM生成)

        v8.1: 支持合成角色ID格式 (如 "2-1+5-1")
        """
        # 如果已经是完整格式 (如 "V2_设计总监_2-1")，直接返回
        if role_id.count("_") >= 2:
            return role_id

        # v8.1: 检测合成角色ID (如 "2-1+5-1", "3-2+2-4+5-4")
        if "+" in role_id:
            return f"SYNTHESIZED_{role_id}"

        # 如果只是短ID (如 "2-1")，需要推断前缀
        # 根据第一个数字推断前缀
        if role_id.startswith("2-"):
            return f"V2_设计总监_{role_id}"
        elif role_id.startswith("3-"):
            return f"V3_叙事与体验专家_{role_id}"  # 配置文件键名
        elif role_id.startswith("4-"):
            return f"V4_设计研究员_{role_id}"
        elif role_id.startswith("5-"):
            return f"V5_场景与行业专家_{role_id}"  # 配置文件键名
        elif role_id.startswith("6-"):
            return f"V6_专业总工程师_{role_id}"
        elif role_id.startswith("7-"):
            return f"V7_社会关系与心理洞察专家_{role_id}"  # v2.0: 正式化名称
        elif role_id.startswith("8-"):
            return f"V8_政策与治理顾问_{role_id}"
        elif role_id.startswith("9-"):
            return f"V9_产业链分析师_{role_id}"
        else:
            # 未知格式，直接返回
            return role_id

    @model_validator(mode="after")
    def validate_v4_presence(self) -> "RoleSelection":
        """
        验证V4角色存在性（使用 Pydantic v2 的 model_validator）

        V4_设计研究员是其他角色的基础依赖，必须始终包含在selected_roles中。

        Raises:
            ValueError: 如果selected_roles中没有V4角色
        """
        # 从 RoleObject 中提取 role_id
        role_ids = [role.role_id for role in self.selected_roles]
        has_v4 = any(rid.startswith("4-") or rid.startswith("V4_") for rid in role_ids)

        if not has_v4:
            raise ValueError(
                " V4_设计研究员是必选角色，但在selected_roles中未找到。\n"
                "V4是其他角色（V2、V3、V5）的依赖基础，必须包含。\n"
                f"当前role_ids: {role_ids}\n"
                "请重新选择，确保包含至少一个role_id以'4-'开头的角色。"
            )

        # 验证通过，记录日志
        v4_roles = [
            role for role in self.selected_roles if role.role_id.startswith("4-") or role.role_id.startswith("V4_")
        ]
        logger.info(f" V4角色验证通过: {[r.role_id for r in v4_roles]}")

        return self

    @model_validator(mode="after")
    def validate_task_distribution_differentiation(self) -> "RoleSelection":
        """
         验证任务分配差异化（防止平均分配）+ v8.2 依赖环检测

        确保核心角色承担更多任务，避免所有角色平均分配相同数量的交付物。
        这是针对专题1发现的"任务分配平均化倾向"问题的修复。

        v8.2 Phase 4 新增:
        - 依赖环检测（DFS）: 检测角色间依赖是否存在环路
        - 分布监控日志: 输出 stdev + Gini 系数用于质量观测

        规则：
        - 如果所有角色的交付物数量标准差 < 0.5，认为是平均分配
        - 至少应该有1个角色的交付物数量显著高于平均值
        """
        import statistics

        # 统计每个角色的交付物数量
        deliverable_counts = [len(role.task_instruction.deliverables) for role in self.selected_roles]

        if len(deliverable_counts) < 2:
            # 只有1个角色时不验证
            return self

        # 计算标准差
        mean_count = statistics.mean(deliverable_counts)
        stdev_count = statistics.stdev(deliverable_counts) if len(deliverable_counts) > 1 else 0

        logger.info(f" 交付物数量分布: {deliverable_counts}, 平均值: {mean_count:.1f}, 标准差: {stdev_count:.2f}")

        # 如果标准差太小，说明分配过于平均
        if stdev_count < 0.8:  # 阈值可调整
            logger.warning(
                f"️ 任务分配过于平均化！标准差: {stdev_count:.2f} < 0.8\n"
                f"   交付物数量: {deliverable_counts}\n"
                f"   建议: 核心角色应承担4-6个交付物，支持角色1-2个"
            )
            # 注意: 这里使用warning而非raise，给LLM一些容错空间

        # 验证是否有"核心角色"（至少4个交付物）
        max_count = max(deliverable_counts)
        if max_count >= 4:
            core_roles = [role.role_id for role, count in zip(self.selected_roles, deliverable_counts) if count >= 4]
            logger.info(f" 检测到核心角色: {core_roles} (交付物数量≥4)")
        else:
            logger.warning("️ 所有角色的交付物数量都<4，可能缺少核心角色")

        return self


class DynamicProjectDirector:
    """
    动态项目总监 - 负责分析需求并选择合适的角色

    职责:
    1. 分析用户需求
    2. 从可用角色中选择3-8个最合适的角色
    3. 为每个角色分配具体任务
    4. 解释选择理由
    """

    def __init__(self, llm_model, role_manager: RoleManager):
        """
        初始化项目总监

        Args:
            llm_model: LLM模型实例
            role_manager: 角色管理器实例
        """
        self.llm = llm_model
        self.role_manager = role_manager

        # 初始化提示词管理器
        self.prompt_manager = PromptManager()

        # 【新增】初始化权重计算器
        from pathlib import Path

        from intelligent_project_analyzer.services.role_weight_calculator import RoleWeightCalculator

        # 优先使用新配置，回退到旧配置
        config_dir = Path(__file__).parent.parent / "config"
        new_config = config_dir / "role_selection_rules.yaml"
        old_config = config_dir / "role_selection_strategy.yaml"

        if new_config.exists():
            strategy_path = new_config
            logger.info("✅ 权重计算器使用新配置: role_selection_rules.yaml")
        elif old_config.exists():
            strategy_path = old_config
            logger.warning("⚠️ 权重计算器使用旧配置: role_selection_strategy.yaml")
        else:
            strategy_path = new_config
            logger.error("❌ 配置文件不存在，权重计算器将使用默认配置")

        self.weight_calculator = RoleWeightCalculator(str(strategy_path))
        logger.info(" 权重计算器已初始化")

    def select_roles_for_task(
        self,
        requirements: str,
        confirmed_core_tasks: Optional[List[Dict[str, Any]]] = None,
        primary_deliverables: Optional[List[Dict[str, Any]]] = None,
        max_retries: int = 3,
    ) -> RoleSelection:
        """
        根据需求选择合适的角色（带 project_scope 过滤）

        Args:
            requirements: 用户需求描述
            confirmed_core_tasks: 用户确认的核心任务列表（用于任务-交付物对齐验证）
            primary_deliverables: 主要交付物列表（用于交付物约束验证 v8.2）
            max_retries: 最大重试次数

        Note:
            不再需要外部传入task_complexity，由LLM根据需求自主判断项目复杂度和专家组合
        """
        # v8.2: 保存交付物列表供约束验证使用
        self._current_primary_deliverables = primary_deliverables
        # 1. 解析 project_scope 字段（支持 JSON 格式或 YAML 格式输入）
        project_scope = None
        # 尝试提取 project_scope
        match = re.search(r'"project_scope"\s*:\s*"([^"]+)"', requirements)
        if match:
            project_scope = match.group(1)
        else:
            # 尝试 YAML 格式
            match2 = re.search(r"project_scope\s*:\s*([a-zA-Z_]+)", requirements)
            if match2:
                project_scope = match2.group(1)
        # 默认 mixed
        if not project_scope:
            project_scope = "mixed"
        logger.info(f" 解析到 project_scope: {project_scope}")

        # 2. 计算角色权重（ 传递confirmed_core_tasks以提升精度）
        role_weights = self.weight_calculator.calculate_weights(requirements, confirmed_core_tasks=confirmed_core_tasks)
        logger.info(f" 角色权重计算完成: {role_weights}")

        # 3. 获取所有可用角色，并根据 applicable_scope 过滤
        available_roles = self.role_manager.get_available_roles()
        filtered_roles = []
        for role in available_roles:
            scope_list = role.get("applicable_scope")
            if scope_list:
                if project_scope in scope_list:
                    filtered_roles.append(role)
            else:
                # 没有 scope 限制的角色默认保留
                filtered_roles.append(role)

        # 如果过滤后没有角色，使用所有角色作为后备
        if not filtered_roles:
            logger.warning(
                f"️ 根据 scope '{project_scope}' 过滤后没有可用角色，将使用所有 {len(available_roles)} 个角色"
            )
            filtered_roles = available_roles

        # v9.3 fix: 在调用 LLM 前根据交付物硬约束过滤不可选角色，避免无效重试风暴
        hard_excluded_prefixes = self._collect_hard_excluded_role_prefixes(primary_deliverables)
        if hard_excluded_prefixes:
            before_count = len(filtered_roles)
            scoped_filtered_roles = [
                r for r in filtered_roles if not self._role_matches_excluded_prefixes(r, hard_excluded_prefixes)
            ]
            if scoped_filtered_roles:
                filtered_roles = scoped_filtered_roles
                logger.info(
                    f"[v9.3] 约束预过滤生效: 排除前缀={sorted(hard_excluded_prefixes)} | "
                    f"{before_count} -> {len(filtered_roles)}"
                )
            else:
                logger.warning(
                    f"[v9.3] 约束预过滤后角色为空，回退到 scope 过滤结果: excluded={sorted(hard_excluded_prefixes)}"
                )

        logger.info(f" 最终可用角色数: {len(filtered_roles)}")

        # 4. 构建角色信息字符串（包含权重）
        roles_info = self._format_roles_info_with_weights(filtered_roles, role_weights)

        # 5. 构建提示词（让LLM自主判断复杂度）
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt_with_weights(requirements, roles_info, role_weights)

        # 6. 调用LLM进行角色选择（带重试）
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]

        llm_with_structure = self.llm.with_structured_output(RoleSelection, method="json_mode")

        last_error = None
        for attempt in range(max_retries):
            try:
                logger.info(f" 尝试角色选择 (第 {attempt + 1}/{max_retries} 次)")
                raw_response = None
                try:
                    raw_response = llm_with_structure.invoke(messages)
                    logger.debug(f" LLM原始响应类型: {type(raw_response)}")
                except (ValidationError, OutputParserException) as structured_error:
                    logger.warning(
                        f"️ LangChain结构化输出失败 ({type(structured_error).__name__})\n   尝试从异常中恢复原始响应..."
                    )
                    raw_response = self._extract_raw_response_from_validation_error(structured_error)
                    if raw_response is None:
                        logger.error(" 无法提取LLM原始响应，将在 {max_retries-attempt} 次后降级")
                        raise structured_error

                response = self._validate_response_with_conversion(raw_response)

                if not response.task_distribution:
                    error_msg = " task_distribution 不能为空字典！必须为每个选择的角色分配任务。"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                task_dist_keys = set(response.task_distribution.keys())
                logger.info(f" [DEBUG] task_distribution keys: {task_dist_keys}")
                if len(task_dist_keys) != len(response.selected_roles):
                    error_msg = (
                        f" task_distribution ({len(task_dist_keys)}个) 与 "
                        f"selected_roles ({len(response.selected_roles)}个) 数量不一致"
                    )
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                if not isinstance(response.task_distribution, dict):
                    logger.warning(f"️ task_distribution is not a dict: {type(response.task_distribution)}")
                    response = self._fix_task_distribution(response)

                # v8.1: 合成角色质量在线验证
                self._validate_synthesized_roles(response)

                # v8.2: 交付物约束实时验证（参与重试循环）
                constraint_violations = self._validate_deliverable_constraints(response)
                if constraint_violations:
                    raise ValueError(f"交付物约束验证失败:\n{constraint_violations}\n请调整角色分配以满足约束要求。")

                logger.info(f" Role selection successful on attempt {attempt + 1}")
                logger.info(f" [DEBUG] task_distribution 类型: {type(response.task_distribution)}")
                logger.info(f" [DEBUG] task_distribution 包含 {len(response.task_distribution)} 个角色")
                for role_id, task_data in response.task_distribution.items():
                    logger.info(f" [DEBUG] 角色 {role_id}:")
                    logger.info(f"   - task_data 类型: {type(task_data)}")
                    if hasattr(task_data, "tasks"):
                        logger.info(f"   - TaskDetail 对象，包含 {len(task_data.tasks)} 个任务")
                        logger.info(f"   - 任务列表前2个: {format_for_log(task_data.tasks[:2])}")
                    elif isinstance(task_data, dict):
                        logger.info(f"   - 字典格式，keys: {format_for_log(list(task_data.keys()))}")
                    elif isinstance(task_data, str):
                        logger.info(f"   - 字符串格式，长度: {len(task_data)}")
                        logger.info(f"   - 内容预览: {task_data[:100]}...")
                    else:
                        logger.info(f"   - 未知格式: {type(task_data)}")
                return response
            except (ValidationError, ValueError, OutputParserException) as e:
                last_error = e
                error_type = type(e).__name__
                logger.warning(f"️ 第 {attempt + 1} 次尝试失败: [{error_type}] {format_for_log(e)}")
                if attempt < max_retries - 1:
                    logger.info(f" 准备重试... (第 {attempt + 2}/{max_retries} 次)")
                    continue
                else:
                    logger.error(
                        f" 所有 {max_retries} 次尝试均失败，降级到默认角色选择\n"
                        f"   最后错误: [{error_type}] {str(e)[:500]}\n"
                        f"    降级警告: 默认选择的任务质量可能低于LLM智能选择"
                    )
                    # 记录降级事件（可用于监控和优化）
                    self._log_fallback_event(requirements, last_error)
                    # v9.3 fix: 直接返回确定性降级结果，避免落入旧逻辑再次触发不必要重试
                    return self._get_default_role_selection(filtered_roles)
            except Exception as e:
                #  新增：捕获网络连接错误（如 SSL/代理问题）
                last_error = e
                error_type = type(e).__name__
                logger.error(f" Attempt {attempt + 1} failed with {error_type}: {e}")

                # 如果是网络连接错误，记录详细信息
                if "Connection" in error_type or "SSL" in str(e):
                    logger.error(" 检测到网络连接问题:")
                    logger.error(f"   - 错误类型: {error_type}")
                    logger.error(f"   - 错误详情: {str(e)[:200]}")
                    logger.error("   - 可能原因: SSL证书验证失败、代理配置问题、网络不稳定")
                    logger.error("   - 建议: 检查 .env 中的 OPENAI_API_BASE/OPENAI_PROXY 设置")

                if attempt < max_retries - 1:
                    import time

                    wait_time = 2**attempt  # 指数退避: 1s, 2s, 4s
                    logger.info(f" 等待 {wait_time}秒后重试... ({attempt + 2}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f" All {max_retries} attempts failed due to {error_type}")
                    # 抛出异常让上层处理
                    raise
        # ...existing code...
        """
        根据需求选择合适的角色（带重试机制）

        Args:
            requirements: 用户需求描述
            max_retries: 最大重试次数（默认3次）

        Returns:
            RoleSelection对象,包含选中的角色和理由
        """
        # 【新增】1. 计算角色权重
        role_weights = self.weight_calculator.calculate_weights(requirements)
        logger.info(f" 角色权重计算完成: {role_weights}")

        # 获取所有可用角色
        available_roles = self.role_manager.get_available_roles()

        # 构建角色信息字符串（包含权重）
        roles_info = self._format_roles_info_with_weights(available_roles, role_weights)

        # 构建提示词
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt_with_weights(requirements, roles_info, role_weights)

        # 调用LLM进行角色选择（带重试）
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]

        # 使用结构化输出 (使用 json_mode 方法以更好支持复杂嵌套类型)
        # 注意: json_mode 比 function_calling 更好地支持 Dict[str, Union[TaskDetail, str]] 这种复杂类型
        llm_with_structure = self.llm.with_structured_output(RoleSelection, method="json_mode")

        # 重试逻辑
        last_error = None
        for attempt in range(max_retries):
            try:
                logger.info(f" Attempting role selection (attempt {attempt + 1}/{max_retries})")
                raw_response = llm_with_structure.invoke(messages)

                #  调试日志：LLM 返回的原始响应
                logger.info(f" [DEBUG] LLM 返回的 raw_response 类型: {type(raw_response)}")

                #  手动验证响应（触发 Pydantic 的 @model_validator）
                # 这是关键步骤！with_structured_output 不会调用验证器，需要手动调用
                try:
                    response = RoleSelection.model_validate(raw_response)
                    logger.info(" Pydantic 验证通过")
                except Exception as validation_error:
                    logger.error(f" Pydantic 验证失败: {format_for_log(validation_error)}")
                    raise validation_error

                #  调试日志：验证后的响应
                logger.info(
                    f" [DEBUG] response.selected_roles: {format_for_log([r.dict() for r in response.selected_roles])}"
                )
                logger.info(f" [DEBUG] response.task_distribution 类型: {type(response.task_distribution)}")

                #  额外的手动验证（双重保险）
                if not response.task_distribution:
                    error_msg = " task_distribution 不能为空字典！必须为每个选择的角色分配任务。"
                    logger.error(error_msg)
                    raise ValueError(error_msg)

                #  检查是否所有选择的角色都有任务分配
                #  修复：response.task_distribution 的键已经是完整角色ID (通过 @property 自动生成)
                # 由于 task_distribution 是从 selected_roles 自动生成的，这个检查实际上总是通过
                # 保留这个检查仅用于防御性编程
                task_dist_keys = set(response.task_distribution.keys())
                logger.info(f" [DEBUG] task_distribution keys: {task_dist_keys}")

                if len(task_dist_keys) != len(response.selected_roles):
                    error_msg = (
                        f" task_distribution ({len(task_dist_keys)}个) 与 "
                        f"selected_roles ({len(response.selected_roles)}个) 数量不一致"
                    )
                    logger.error(error_msg)
                    raise ValueError(error_msg)

                # 验证 task_distribution 是否为字典
                if not isinstance(response.task_distribution, dict):
                    logger.warning(f"️ task_distribution is not a dict: {type(response.task_distribution)}")
                    # 尝试修复
                    response = self._fix_task_distribution(response)
                    # 尝试修复
                    response = self._fix_task_distribution(response)

                logger.info(f" Role selection successful on attempt {attempt + 1}")

                #  调试日志：输出 task_distribution 的详细信息
                logger.info(f" [DEBUG] task_distribution 类型: {type(response.task_distribution)}")
                logger.info(f" [DEBUG] task_distribution 包含 {len(response.task_distribution)} 个角色")

                for role_id, task_data in response.task_distribution.items():
                    logger.info(f" [DEBUG] 角色 {role_id}:")
                    logger.info(f"   - task_data 类型: {type(task_data)}")
                    if hasattr(task_data, "tasks"):
                        logger.info(f"   - TaskDetail 对象，包含 {len(task_data.tasks)} 个任务")
                        logger.info(f"   - 任务列表前2个: {format_for_log(task_data.tasks[:2])}")
                    elif isinstance(task_data, dict):
                        logger.info(f"   - 字典格式，keys: {format_for_log(list(task_data.keys()))}")
                    elif isinstance(task_data, str):
                        logger.info(f"   - 字符串格式，长度: {len(task_data)}")
                        logger.info(f"   - 内容预览: {task_data[:100]}...")
                    else:
                        logger.info(f"   - 未知格式: {type(task_data)}")

                return response

            except (ValidationError, ValueError) as e:
                last_error = e
                logger.warning(f"️ Attempt {attempt + 1} failed with validation error: {format_for_log(e)}")

                # 如果不是最后一次尝试，继续重试
                if attempt < max_retries - 1:
                    logger.info(f" Retrying... ({attempt + 2}/{max_retries})")
                    continue
                else:
                    # 最后一次尝试失败，使用默认模板
                    logger.error(f" All {max_retries} attempts failed, using default template")
                    return self._get_default_role_selection(available_roles)

            except Exception as e:
                last_error = e
                logger.error(f" Attempt {attempt + 1} failed with unexpected error: {e}")

                # 如果不是最后一次尝试，继续重试
                if attempt < max_retries - 1:
                    logger.info(f" Retrying... ({attempt + 2}/{max_retries})")
                    continue
                else:
                    # 最后一次尝试失败，使用默认模板
                    logger.error(f" All {max_retries} attempts failed, using default template")
                    return self._get_default_role_selection(available_roles)

        # 理论上不会到达这里，但为了安全起见
        logger.error(" Unexpected: reached end of retry loop, using default template")
        return self._get_default_role_selection(available_roles)

    def _fix_task_distribution(self, response: RoleSelection) -> RoleSelection:
        """
        尝试修复 task_distribution 字段，确保格式正确

        Args:
            response: 原始响应

        Returns:
            修复后的 RoleSelection
        """
        logger.info(" [DEBUG] 开始修复 task_distribution")
        logger.info(f" [DEBUG] 原始 task_distribution 类型: {type(response.task_distribution)}")

        #  检查 task_distribution 是否为空
        if not response.task_distribution:
            logger.error(" task_distribution 为空字典！LLM 没有为任何角色分配任务。")
            logger.error(" 这通常意味着 LLM 没有理解 Prompt 要求，或者生成的响应被截断。")
            logger.error(" 将使用默认角色选择和模板任务。")

            # 获取可用角色列表
            available_roles = self.role_manager.get_available_roles()
            return self._get_default_role_selection(available_roles)

        #  检查是否所有选择的角色都有任务分配
        missing_roles = [role for role in response.selected_roles if role not in response.task_distribution]
        if missing_roles:
            logger.error(f" 以下角色缺少任务分配: {missing_roles}")
            logger.error(f" selected_roles: {response.selected_roles}")
            logger.error(f" task_distribution keys: {list(response.task_distribution.keys())}")
            logger.error(" 将使用默认角色选择和模板任务。")

            # 获取可用角色列表
            available_roles = self.role_manager.get_available_roles()
            return self._get_default_role_selection(available_roles)

        try:
            # 检查每个角色的任务分配
            fixed_distribution = {}

            for role_id in response.selected_roles:
                role_task = response.task_distribution.get(role_id)

                logger.info(f" [DEBUG] 修复角色 {role_id}:")
                logger.info(f" [DEBUG]   - 原始类型: {type(role_task)}")

                # 情况1: 已经是 TaskDetail 对象
                if isinstance(role_task, TaskDetail):
                    fixed_distribution[role_id] = role_task
                    continue

                # 情况2: 是字典，尝试转换为 TaskDetail
                if isinstance(role_task, dict):
                    try:
                        logger.info(f" [DEBUG]   - 字典 keys: {list(role_task.keys())}")
                        fixed_distribution[role_id] = TaskDetail(**role_task)
                        logger.info(f" 成功将 {role_id} 的字典转换为 TaskDetail")
                        continue
                    except Exception as e:
                        logger.warning(f"️ 无法将 {role_id} 的字典转换为 TaskDetail: {e}")

                # 情况3: 是字符串，转换为 TaskDetail
                if isinstance(role_task, str):
                    logger.info(f" [DEBUG]   - 字符串长度: {len(role_task)}")
                    logger.info(f" 将 {role_id} 的字符串任务转换为 TaskDetail 格式")
                    fixed_distribution[role_id] = TaskDetail(
                        tasks=[role_task], focus_areas=[], expected_output="", dependencies=[]
                    )
                    continue

                # 情况4: 没有任务或格式不对，创建默认任务
                logger.warning(f"️ {role_id} 没有有效任务，创建默认任务")
                fixed_distribution[role_id] = TaskDetail(
                    tasks=["执行专业分析"], focus_areas=[], expected_output="", dependencies=[]
                )

            logger.info(" task_distribution 已由 selected_roles 推导，无需额外写回")
            return response

        except Exception as e:
            logger.error(f" Failed to fix task_distribution: {e}")
            return response

    def _validate_synthesized_roles(self, response: RoleSelection) -> None:
        """
        v8.1/v8.2: 在线验证合成角色质量 + 全局角色选择质量评分

        在角色选择完成后、专家执行前调用。
        v8.1: 验证所有合成角色的质量
        v8.2: 新增全局质量评分（任务-角色对齐 + 交付物覆盖）
        不合格的结果将被记录警告，但不会阻断流程（降级为warning）。

        Args:
            response: 角色选择结果
        """
        try:
            from intelligent_project_analyzer.services.synthesis_quality_validator import (
                validate_role_selection_synthesis,
                validate_overall_quality,
            )

            # 收集selected_roles数据
            roles_data = []
            for role in response.selected_roles:
                deliverable_count = len(role.task_instruction.deliverables) if role.task_instruction else 0
                role_data = {
                    "role_id": role.role_id,
                    "role_name": role.role_name,
                    "dynamic_role_name": role.dynamic_role_name,
                    "tasks": role.tasks,
                    "dependencies": role.dependencies,
                    "deliverable_count": deliverable_count,
                }
                roles_data.append(role_data)

            # v8.1: 合成角色质量验证
            validation_result = validate_role_selection_synthesis(roles_data)

            if validation_result["total_synthesized"] > 0:
                logger.info(
                    f"[v8.1] 合成角色验证: {validation_result['total_synthesized']}个合成角色, "
                    f"{'全部合格' if validation_result['all_valid'] else '存在不合格'}"
                )

                for report in validation_result["reports"]:
                    if not report.get("is_valid"):
                        logger.warning(
                            f"[v8.1] 合成角色质量警告: "
                            f"父角色={report.get('parent_roles')}, "
                            f"总分={report.get('total_score')}, "
                            f"错误={report.get('errors')}"
                        )

            # v8.2 Phase 2: 全局角色选择质量评分
            overall_result = validate_overall_quality(roles_data)
            if not overall_result["is_acceptable"]:
                logger.warning(
                    f"[v8.2] 全局角色选择质量偏低: "
                    f"总分={overall_result['overall_score']:.2f}, "
                    f"对齐={overall_result['alignment_score']:.2f}, "
                    f"覆盖={overall_result['coverage_score']:.2f}\n"
                    f"  警告: {overall_result['warnings']}"
                )

        except ImportError:
            logger.debug("[v8.1] 合成质量验证器未安装，跳过验证")
        except Exception as e:
            logger.warning(f"[v8.1] 合成质量验证异常: {e}")

    def _collect_hard_excluded_role_prefixes(
        self, primary_deliverables: Optional[List[Dict[str, Any]]]
    ) -> set[str]:
        """根据交付物约束收集 must_exclude 角色前缀（如 V6）。"""
        if not primary_deliverables:
            return set()

        try:
            from intelligent_project_analyzer.utils.constraint_loader import get_constraint_loader

            loader = get_constraint_loader()
            excluded: set[str] = set()
            for deliverable in primary_deliverables:
                d_type = deliverable.get("type", "custom")
                constraints = loader.get_constraints(d_type)
                for role_prefix in constraints.get("must_exclude", []) or []:
                    if isinstance(role_prefix, str) and role_prefix:
                        excluded.add(role_prefix.split("_")[0])
            return excluded
        except Exception as e:
            logger.warning(f"[v9.3] 收集硬排除角色失败（降级忽略）: {e}")
            return set()

    def _role_matches_excluded_prefixes(self, role: Dict[str, Any], excluded_prefixes: set[str]) -> bool:
        """判断某个候选角色是否命中硬排除前缀。"""
        if not excluded_prefixes:
            return False

        base_type = str(role.get("base_type", ""))
        full_id = str(role.get("full_id", ""))
        role_id = str(role.get("role_id", ""))

        for prefix in excluded_prefixes:
            if (
                base_type.startswith(prefix)
                or full_id.startswith(prefix)
                or role_id.startswith(prefix.replace("V", "") + "-")
                or role_id.startswith(prefix)
            ):
                return True
        return False

    def _format_deliverable_constraints(self, primary_deliverables: Optional[List[Dict[str, Any]]]) -> str:
        """将交付物约束格式化为可读文本，供 Prompt 注入。"""
        if not primary_deliverables:
            return ""

        try:
            from intelligent_project_analyzer.utils.constraint_loader import get_constraint_loader

            loader = get_constraint_loader()
            lines: List[str] = []
            for deliverable in primary_deliverables:
                d_type = deliverable.get("type", "custom")
                d_name = deliverable.get("description") or d_type
                constraints = loader.get_constraints(d_type)
                must_include = constraints.get("must_include", []) or []
                must_exclude = constraints.get("must_exclude", []) or []

                if must_include or must_exclude:
                    include_text = f"must_include={must_include}" if must_include else ""
                    exclude_text = f"must_exclude={must_exclude}" if must_exclude else ""
                    connector = " | " if include_text and exclude_text else ""
                    lines.append(f"- {d_name}: {include_text}{connector}{exclude_text}")

            return "\n".join(lines)
        except Exception as e:
            logger.warning(f"[v9.4] 生成交付物约束提示失败（降级忽略）: {e}")
            return ""

    def _validate_deliverable_constraints(self, response: RoleSelection) -> Optional[str]:
        """
        v8.2: 交付物约束实时验证

        使用 constraint_loader 检查 LLM 返回的角色分配是否违反
        deliverable_role_constraints.yaml 中定义的 must_include / must_exclude 规则。

        此方法参与重试循环：验证失败时返回违规描述字符串，
        由调用方抛出 ValueError 触发 LLM 重试，违规信息会作为错误上下文
        反馈给下一次 LLM 调用（通过 Pydantic ValidationError 消息）。

        Args:
            response: LLM 返回的角色选择结果

        Returns:
            None 表示验证通过；非空字符串表示违规描述
        """
        deliverables = getattr(self, "_current_primary_deliverables", None)
        if not deliverables:
            logger.debug("[v8.2] 无 primary_deliverables，跳过约束验证")
            return None

        try:
            from intelligent_project_analyzer.utils.constraint_loader import validate_allocation

            # 提取角色ID列表，转换为 constraint_loader 期望的 V前缀格式
            # RoleObject.role_id 为 "2-1" 格式，constraint_loader 期望 "V2" 前缀
            role_ids = []
            for role in response.selected_roles:
                rid = role.role_id
                # 合成角色 (如 "2-1+5-1") 拆分为父角色分别验证
                clean_id = rid.replace("SYNTHESIZED_", "")
                if "+" in clean_id:
                    for parent_id in clean_id.split("+"):
                        pid = parent_id.strip()
                        prefix = f"V{pid.split('-')[0]}"
                        if prefix not in [r.split("-")[0] if "-" in r else r for r in role_ids]:
                            role_ids.append(prefix)
                else:
                    prefix = f"V{clean_id.split('-')[0]}"
                    if prefix not in role_ids:
                        role_ids.append(prefix)

            is_valid, error_msg = validate_allocation(deliverables, role_ids)

            if not is_valid:
                logger.warning(f"[v8.2] 交付物约束验证失败: {error_msg}")
                return error_msg
            else:
                logger.info(f"[v8.2] 交付物约束验证通过 ({len(deliverables)}个交付物, {len(role_ids)}个角色)")
                return None

        except ImportError:
            logger.debug("[v8.2] constraint_loader 未安装，跳过约束验证")
            return None
        except Exception as e:
            # 约束验证异常不应阻断主流程
            logger.warning(f"[v8.2] 交付物约束验证异常（降级跳过）: {e}")
            return None

    def _log_fallback_event(self, requirements: str, error: Exception) -> None:
        """
         记录降级事件（用于监控和优化）

        当LLM选择失败，系统降级到默认选择时调用此方法。
        记录的信息可用于：
        1. 监控系统健康状况
        2. 分析prompt优化方向
        3. 识别常见失败模式

        Args:
            requirements: 触发降级的需求文本
            error: 导致降级的最后一个错误
        """
        import json
        import time
        from pathlib import Path

        try:
            # 准备日志目录
            log_dir = Path("logs/fallback_events")
            log_dir.mkdir(parents=True, exist_ok=True)

            # 构建事件记录
            event = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "error_type": type(error).__name__,
                "error_message": str(error)[:500],  # 限制长度
                "requirements_preview": requirements[:300],  # 预览前300字符
                "requirements_length": len(requirements),
            }

            # 追加到日志文件
            log_file = log_dir / f"fallback_{time.strftime('%Y%m%d')}.jsonl"
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")

            logger.info(f" 降级事件已记录到: {log_file}")

        except Exception as log_error:
            logger.warning(f"️ 记录降级事件失败: {log_error}")

    def _get_default_role_selection(self, available_roles: List[Dict]) -> RoleSelection:
        """
        获取默认的角色选择（当所有重试都失败时使用）- v2.0任务导向架构

        ️ 此方法仅在LLM多次重试失败后作为降级方案使用
        生成的TaskInstruction较为基础，建议优化LLM prompt以减少对此方法的依赖

        Args:
            available_roles: 可用角色列表

        Returns:
            默认的 RoleSelection（包含完整的RoleObject和TaskInstruction）
        """
        logger.info(" Creating default role selection with task-oriented architecture")

        # 如果传入的 available_roles 为空，尝试从 RoleManager 获取所有角色
        if not available_roles:
            logger.warning("️ 传入的 available_roles 为空，尝试获取所有可用角色")
            available_roles = self.role_manager.get_available_roles()

        # 选择每个类别的第一个角色（默认不包含V6，避免design_strategy等场景冲突）
        role_objects = []
        role_categories = ["V2_设计总监", "V3_叙事与体验专家", "V4_设计研究员"]

        hard_excluded_prefixes = self._collect_hard_excluded_role_prefixes(
            getattr(self, "_current_primary_deliverables", None)
        )

        selected_base_types = set()

        for role in available_roles:
            base_type = role.get("base_type", "")
            if hard_excluded_prefixes and self._role_matches_excluded_prefixes(role, hard_excluded_prefixes):
                continue
            if base_type in role_categories and base_type not in selected_base_types:
                # 构造RoleObject
                role_obj = self._create_default_role_object(role)
                role_objects.append(role_obj)
                selected_base_types.add(base_type)

                if len(role_objects) >= 4:
                    break

        # 如果没有找到足够的角色，从前4个可用角色生成
        if len(role_objects) < 3:
            logger.warning(f"️ 只找到{len(role_objects)}个默认角色，尝试补充至3个")
            for role in available_roles[:4]:
                if len(role_objects) >= 4:
                    break
                base_type = role.get("base_type", "")
                if hard_excluded_prefixes and self._role_matches_excluded_prefixes(role, hard_excluded_prefixes):
                    continue
                if base_type not in selected_base_types:
                    role_obj = self._create_default_role_object(role)
                    role_objects.append(role_obj)
                    selected_base_types.add(base_type)

        logger.info(f" Created default selection with {len(role_objects)} roles")

        return RoleSelection(
            selected_roles=role_objects,
            reasoning=(
                "由于LLM响应格式错误或缺少必需字段，系统自动使用默认角色选择策略。"
                "已选择核心角色（设计总监、叙事专家、设计研究员等）以确保项目分析的完整性和专业性。"
                "这些角色将协同工作，从多个维度对项目进行深入分析。"
                "️ 注意：由于使用默认策略，任务指令较为基础，建议人工审核并优化。"
            ),
        )

    def _create_default_role_object(self, role_config: Dict) -> RoleObject:
        """
        从角色配置创建默认的RoleObject（包含TaskInstruction）

        Args:
            role_config: 角色配置字典（来自role_manager）

        Returns:
            包含完整TaskInstruction的RoleObject
        """
        role_id = role_config.get("role_id", "unknown")
        #  v7.22: 兼容两种字段名 - role_manager 使用 "name"，LLM 输出使用 "role_name"
        role_name = role_config.get("role_name") or role_config.get("name", "未知角色")
        base_type = role_config.get("base_type", "")

        # Map base_type to role_type for template generation
        role_type_map = {"V2_设计总监": "V2_design_director", "V3_叙事与体验专家": "V3_narrative_expert"}
        mapped_role_type = role_type_map.get(base_type, "default")

        #  生成默认的TaskInstruction
        default_task_instruction = generate_task_instruction_template(mapped_role_type)

        #  v7.10: 为V3叙事专家标记创意模式
        if base_type == "V3_叙事与体验专家" or role_id.startswith("3-"):
            default_task_instruction.is_creative_narrative = True
            logger.info(f" 为叙事专家 {role_name} 启用创意叙事模式")

        # 尝试从策略管理器获取更详细的任务模板
        try:
            from intelligent_project_analyzer.core.strategy_manager import StrategyManager

            strategy_manager = StrategyManager()
            template_tasks = strategy_manager.get_task_template(base_type)

            if template_tasks and len(template_tasks) > 0:
                # 将模板任务转换为deliverables
                deliverables = []
                for i, task_desc in enumerate(template_tasks[:3]):  # 最多3个
                    deliverables.append(
                        DeliverableSpec(
                            name=f"{role_name}交付物{i + 1}",
                            description=task_desc if len(task_desc) > 20 else f"完成{task_desc}相关分析和方案",
                            format=DeliverableFormat.ANALYSIS,
                            priority=Priority.HIGH if i == 0 else Priority.MEDIUM,
                            success_criteria=["分析内容完整准确", "提供可执行建议"],
                        )
                    )

                if deliverables:
                    default_task_instruction.deliverables = deliverables
                    logger.info(f" 为 {role_name} 生成了 {len(deliverables)} 个交付物")
        except Exception as e:
            logger.warning(f"️ 无法从策略管理器获取任务模板: {e}，使用基础模板")

        return RoleObject(
            role_id=role_id,
            role_name=role_name,
            dynamic_role_name=f"{role_name}（默认配置）",
            task_instruction=default_task_instruction,
            dependencies=[],
            execution_priority=1,
        )

    def _convert_legacy_format_to_v2(self, raw_response: dict) -> Optional[dict]:
        """
        将LLM返回的老格式(tasks/expected_output)转换为v2格式(task_instruction)

        老格式示例:
        {
          "selected_roles": [{
            "role_id": "2-1",
            "role_name": "设计总监",
            "dynamic_role_name": "...",
            "tasks": ["任务1", "任务2"],
            "expected_output": "预期输出",
            "focus_areas": ["领域1", "领域2"],
            "dependencies": ["3-1"]
          }],
          "reasoning": "..."
        }

        新格式示例:
        {
          "selected_roles": [{
            "role_id": "2-1",
            "role_name": "设计总监",
            "dynamic_role_name": "...",
            "task_instruction": {
              "objective": "预期输出",
              "deliverables": [{"name": "任务1", "description": "任务1", ...}],
              "success_criteria": ["完成所有任务", "符合预期输出要求"]
            },
            "dependencies": ["3-1"]
          }],
          "reasoning": "..."
        }

        Args:
            raw_response: LLM返回的原始响应

        Returns:
            转换后的响应字典,如果转换失败则返回None
        """
        try:
            if not isinstance(raw_response, dict) or "selected_roles" not in raw_response:
                logger.error(" 原始响应格式不正确,缺少selected_roles")
                return None

            selected_roles = raw_response.get("selected_roles", [])
            if not selected_roles:
                logger.error(" selected_roles 为空")
                return None

            converted_roles = []
            for role_data in selected_roles:
                # 检查是否已经是v2格式
                if "task_instruction" in role_data:
                    converted_roles.append(role_data)
                    continue

                # 转换老格式到v2
                logger.info(f" 转换角色 {role_data.get('role_id')} 从老格式到v2")

                # 提取老格式字段
                tasks = role_data.get("tasks", [])
                expected_output = role_data.get("expected_output", "")
                focus_areas = role_data.get("focus_areas", [])

                # 构造TaskInstruction
                deliverables = []
                for i, task in enumerate(tasks[:5]):  # 最多5个
                    deliverables.append(
                        {
                            "name": focus_areas[i] if i < len(focus_areas) else f"交付物{i + 1}",
                            "description": task if len(task) > 20 else f"完成{task}相关分析和方案",
                            "format": "analysis",
                            "priority": "high" if i == 0 else "medium",
                            "success_criteria": ["内容完整准确", "提供可执行建议"],
                        }
                    )

                task_instruction = {
                    "objective": expected_output if expected_output else "完成角色分配的所有任务",
                    "deliverables": deliverables,
                    "success_criteria": ["完成所有指定任务", "输出符合预期格式和质量要求"],
                    "constraints": [],
                    "context_requirements": [],
                    #  v7.10: 为V3叙事专家标记创意模式
                    "is_creative_narrative": role_data.get("role_id", "").startswith("3-"),
                }

                # 构造v2格式的RoleObject
                converted_role = {
                    "role_id": role_data.get("role_id", ""),
                    "role_name": role_data.get("role_name", ""),
                    "dynamic_role_name": role_data.get("dynamic_role_name", ""),
                    "task_instruction": task_instruction,
                    "dependencies": role_data.get("dependencies", []),
                    "execution_priority": role_data.get("execution_priority", 1),
                }

                converted_roles.append(converted_role)
                logger.info(f" 角色 {converted_role['role_id']} 转换成功")

            # 构造最终响应
            converted_response = {
                "selected_roles": converted_roles,
                "reasoning": raw_response.get("reasoning", "角色选择完成"),
            }

            logger.info(f" 成功转换 {len(converted_roles)} 个角色到v2格式")
            return converted_response

        except Exception as e:
            logger.error(f" 格式转换失败: {e}")
            import traceback

            logger.error(traceback.format_exc())
            return None

    def _validate_response_with_conversion(self, raw_response: Any) -> RoleSelection:
        """验证LLM响应，如遇老格式则尝试自动转换。"""
        if isinstance(raw_response, RoleSelection):
            logger.info(" 已收到RoleSelection实例，无需再次验证")
            return raw_response

        # 字符串响应需要先解析成字典
        if isinstance(raw_response, str):
            try:
                raw_response = json.loads(raw_response)
            except json.JSONDecodeError as decode_error:
                logger.error(f" 无法解析LLM字符串响应为JSON: {decode_error}")
                raise decode_error

        # v9.4: 结构化校验前的轻量自动修复
        if isinstance(raw_response, dict):
            raw_response = self._auto_fix_common_issues(raw_response)

        #  第一步：尝试直接验证（期望v2格式）
        try:
            response = RoleSelection.model_validate(raw_response)
            logger.info(" Pydantic 验证通过（v2格式）")
            return response
        except ValidationError as validation_error:
            #  第二步：检测到验证失败，尝试从老格式转换
            logger.warning("️ Pydantic 验证失败，尝试从老格式转换")
            logger.debug(f"   原始错误: {format_for_log(validation_error)}")

            converted_response = self._convert_legacy_format_to_v2(raw_response)
            if converted_response:
                try:
                    response = RoleSelection.model_validate(converted_response)
                    logger.info(" 老格式转换成功，验证通过")
                    return response
                except ValidationError as convert_error:
                    logger.error(f" 转换后仍然验证失败: {format_for_log(convert_error)}")
                    raise validation_error  # 抛出原始错误，触发重试

            logger.error(" 无法转换老格式（检测失败或数据异常）")
            raise validation_error  # 抛出原始错误，触发重试

    def _auto_fix_common_issues(self, data: dict) -> dict:
        """自动修复LLM输出常见结构问题（不改变核心语义）。"""
        fixed = dict(data)

        selected_roles = fixed.get("selected_roles", [])
        if isinstance(selected_roles, list):
            for role in selected_roles:
                if not isinstance(role, dict):
                    continue
                ti = role.get("task_instruction")
                if not isinstance(ti, dict):
                    continue

                sc = ti.get("success_criteria")
                if not isinstance(sc, list):
                    ti["success_criteria"] = ["确保交付物质量达到专业标准", "结果可执行且可验证"]
                elif len(sc) < 2:
                    patched = list(sc)
                    while len(patched) < 2:
                        patched.append("确保交付物质量达到专业标准")
                    ti["success_criteria"] = patched

                if isinstance(ti.get("constraints"), bool):
                    ti["constraints"] = []

                role["task_instruction"] = ti

        reasoning = fixed.get("reasoning")
        if isinstance(reasoning, str) and len(reasoning) < 50:
            fixed["reasoning"] = (
                reasoning
                + "。基于项目需求、角色能力边界与交付约束进行了综合评估，"
                + "优先保证关键交付物覆盖与执行可行性。"
            )

        return fixed

    def _extract_raw_response_from_validation_error(self, error: Exception) -> Optional[dict]:
        """尝试从LangChain抛出的ValidationError或OutputParserException字符串中提取原始completion。"""

        # 1. 尝试从 OutputParserException 中提取 llm_output
        if hasattr(error, "llm_output") and error.llm_output:
            if isinstance(error.llm_output, dict):
                return error.llm_output
            if isinstance(error.llm_output, str):
                try:
                    return json.loads(error.llm_output)
                except json.JSONDecodeError:
                    pass

        # 2. 尝试从 error.args 中提取 completion (针对 ValidationError)
        if hasattr(error, "args"):
            for arg in error.args:
                if isinstance(arg, dict):
                    completion = arg.get("completion")
                    if completion:
                        if isinstance(completion, dict):
                            return completion
                        if isinstance(completion, str):
                            try:
                                return json.loads(completion)
                            except json.JSONDecodeError:
                                logger.error(" completion 字段非有效JSON字符串")

        # 3. 回退到解析报错文本 (Regex)
        error_text = str(error)
        # 匹配 "completion {...}. Got" 模式 (LangChain 标准错误格式)
        match = re.search(r"completion\s+(\{.*\})\.\s+Got", error_text, re.DOTALL)
        if match:
            json_text = match.group(1)
            try:
                return json.loads(json_text)
            except json.JSONDecodeError:
                logger.error(" 无法从ValidationError文本解析出有效JSON")

        # 尝试匹配 OutputParserException 的常见格式 (更宽泛的匹配)
        # 比如 "Failed to parse RoleSelection from completion {...}"
        # 注意：这里可能会匹配到不完整的JSON，所以放在最后尝试
        match = re.search(r"completion\s+(\{.*\})", error_text, re.DOTALL)
        if match:
            json_text = match.group(1)
            try:
                return json.loads(json_text)
            except json.JSONDecodeError:
                pass

        logger.error(" 异常中未找到completion片段")
        return None

    def _build_system_prompt(self) -> str:
        """
        构建系统提示词 - 从外部配置加载

        Returns:
            系统提示词

        Note:
            不再需要task_complexity参数，LLM会根据需求自主判断项目复杂度
        """
        # 优先使用v2版本（任务导向架构）
        prompt = self.prompt_manager.get_prompt("dynamic_project_director_v2")

        # 如果v2不存在，回退到v1
        if not prompt:
            logger.warning("️ 未找到v2版本提示词，回退到v1版本")
            prompt = self.prompt_manager.get_prompt("dynamic_project_director")

        # 如果配置不存在，抛出错误（不再使用硬编码 fallback）
        if not prompt:
            raise ValueError(
                " 未找到提示词配置: dynamic_project_director 或 dynamic_project_director_v2\n"
                "请确保配置文件存在: config/prompts/dynamic_project_director_v2.yaml\n"
                "系统无法使用硬编码提示词，请检查配置文件。"
            )

        return prompt

    def _build_user_prompt(self, requirements: str, roles_info: str) -> str:
        """
        构建用户提示词

        Args:
            requirements: 用户需求
            roles_info: 格式化的角色信息

        Returns:
            用户提示词字符串
        """
        prompt = f"""# 项目需求

{requirements}

# 可用角色

{roles_info}

# 任务

请根据上述项目需求,从可用角色中选择3-8个最合适的角色来完成这个项目。

要求:
1. 选择的角色必须能够覆盖项目的所有关键方面
2. 为每个角色分配具体、详细、可执行的任务（每个任务描述至少30-50个字符）
3. 任务描述要明确说明该角色需要完成什么、如何完成、达到什么目标
4. 解释你的选择理由
5. 说明这些角色如何协作完成项目

️ 重要格式要求：
你必须按照以下JSON格式返回结果：

{{
  "selected_roles": [
    {{
      "role_id": "2-1",
      "role_name": "居住空间设计总监",
      "dynamic_role_name": "针对本项目的具体称呼（如：三代同堂居住空间与生活模式总设计师）",
      "tasks": ["任务1描述（至少30字）", "任务2描述"],
      "focus_areas": ["关注点1", "关注点2"],
      "expected_output": "预期交付物描述",
      "dependencies": ["依赖的其他角色ID"]
    }},
    ...
  ],
  "reasoning": "选择理由（至少50个字符）"
}}

 关键注意事项：
1. selected_roles 必须是对象数组，不能是字符串数组！
2. 每个角色对象必须包含 role_id, role_name, dynamic_role_name, tasks 等所有字段
3. dynamic_role_name 是必填项，要根据本项目需求创造一个精准反映该角色职责的名称
4. 不要输出 task_distribution 字段（系统会自动生成）

请严格按照上述格式返回结果。
"""

    def _format_roles_info(self, roles: List[Dict]) -> str:
        """
        格式化角色信息

        Args:
            roles: 角色列表

        Returns:
            格式化的角色信息字符串
        """
        lines = []

        # 按base_type分组
        grouped_roles = {}
        for role in roles:
            base_type = role["base_type"]
            if base_type not in grouped_roles:
                grouped_roles[base_type] = []
            grouped_roles[base_type].append(role)

        # 格式化输出
        for base_type, role_list in grouped_roles.items():
            lines.append(f"\n## {base_type}")

            for role in role_list:
                lines.append(f"\n### {role['full_id']}")
                lines.append(f"**名称**: {role.get('name', 'N/A')}")
                lines.append(f"**描述**: {role.get('description', 'N/A')}")

                keywords = role.get("keywords", [])
                if keywords:
                    lines.append(f"**关键词**: {', '.join(keywords)}")

                lines.append("")

        return "\n".join(lines)

    def _format_roles_info_with_weights(self, roles: List[Dict], weights: Dict[str, float]) -> str:
        """
        格式化角色信息（包含权重）

        Args:
            roles: 角色列表
            weights: 权重字典（key为角色类别，如 "V4_设计研究员"）

        Returns:
            格式化的角色信息字符串（按权重排序）
        """
        lines = []

        # 按base_type分组
        grouped_roles = {}
        for role in roles:
            base_type = role["base_type"]
            if base_type not in grouped_roles:
                grouped_roles[base_type] = []
            grouped_roles[base_type].append(role)

        # 按权重排序（权重高的在前）
        sorted_base_types = sorted(grouped_roles.keys(), key=lambda bt: weights.get(bt, 0.0), reverse=True)

        # 格式化输出
        for base_type in sorted_base_types:
            weight = weights.get(base_type, 0.0)
            lines.append(f"\n## {base_type} （权重: {weight:.1f}）")

            role_list = grouped_roles[base_type]
            for role in role_list:
                lines.append(f"\n### {role['full_id']}")
                lines.append(f"**名称**: {role.get('name', 'N/A')}")
                lines.append(f"**描述**: {role.get('description', 'N/A')}")

                keywords = role.get("keywords", [])
                if keywords:
                    lines.append(f"**关键词**: {', '.join(keywords)}")

                lines.append("")

        return "\n".join(lines)

    def _build_user_prompt_with_weights(self, requirements: str, roles_info: str, weights: Dict[str, float]) -> str:
        """
        构建用户提示词（包含权重信息）

        Args:
            requirements: 用户需求
            roles_info: 格式化的角色信息（已包含权重）
            weights: 权重字典

        Returns:
            用户提示词字符串
        """
        # 生成权重说明
        weight_explanation = self._generate_weight_explanation(weights)

        return f"""# 项目需求

{requirements}

{weight_explanation}

# 可用角色（已按权重排序）

{roles_info}

# 任务

请根据上述项目需求和权重信息,从可用角色中选择3-8个最合适的角色来完成这个项目。

 **任务量分配要求（重要）**：
- **禁止平均分配**：不要给每个角色分配相同数量的任务！
- **核心角色**（权重≥2.5 或 V2设计总监）：分配 **4-6个交付物**
- **重要角色**（权重2.0-2.4）：分配 **2-3个交付物**
- **支持角色**（权重1.5-1.9）：分配 **1-2个交付物**
- **辅助角色**（权重<1.5）：分配 **1个交付物**
- **V2设计总监必须是任务量最多的角色（4-6个交付物）**

其他要求:
1. **参考权重信息**：权重越高说明该角色与需求的匹配度越高，应承担更多任务
2. 选择的角色必须能够覆盖项目的所有关键方面
3. **必须包含至少一个 V4_设计研究员 角色**，作为项目的基础研究支撑（这是强制要求）
4. 为每个角色的task_instruction.deliverables分配具体交付物（参考上述数量要求）
5. 任务描述要明确说明该角色需要完成什么、如何完成、达到什么目标
6. 解释你的选择理由（要结合权重信息说明为何某些角色承担更多任务）
7. 说明这些角色如何协作完成项目

️ 重要格式要求：
你必须按照以下JSON格式返回结果：

{{
  "analysis_framework": "ability_core",
  "selected_roles": [
    {{
      "role_id": "2-1",
      "role_name": "居住空间设计总监",
      "dynamic_role_name": "针对本项目的具体称呼（如：三代同堂居住空间与生活模式总设计师）",
      "task_instruction": {{
        "objective": "核心目标描述",
        "deliverables": [
          {{
            "name": "交付物名称",
            "description": "具体要求（50-150字）",
            "format": "analysis",
            "priority": "high",
            "success_criteria": ["标准1", "标准2"],
            "source_task_ids": ["CT-xxxxxxxx"]
          }}
        ],
        "success_criteria": ["整体成功标准1", "标准2"],
        "constraints": ["约束条件"],
        "context_requirements": ["上下文要求"],
        "source_task_ids": ["CT-xxxxxxxx"]
      }},
      "dependencies": ["依赖的其他角色ID"],
      "execution_priority": 1
    }},
    ...
  ],
  "reasoning": "选择理由（至少50个字符，要说明为何不同角色承担不同数量的任务）"
}}

📐 analysis_framework 选择指南：
- **ability_core**: 室内/建筑/空间设计（默认，覆盖~80%项目）— 12维度能力分析
- **multi_scale_integration**: 城市→建筑→室内跨尺度项目
- **budget_constrained_strategy**: 极限预算/翻新/改造项目
- **interdisciplinary_translation**: 涉及跨学科理论转译的项目
- **healthcare_healing**: 医疗/康复/治愈空间
- **design_methodology**: 非项目级的方法论研究
- **behavioral_design**: 行为引导/坪效/转化率导向
- **ephemeral_space**: 快闪/展览/临时空间
- **competitive_bidding**: 竞标/投标/比稿
- **construction_delivery**: 施工交付管理
- **humanitarian_design**: 人道主义/灾后/极端约束
如果不确定，默认 "ability_core"。

 关键注意事项：
1. selected_roles 必须是对象数组，不能是字符串数组！
2. 每个角色对象必须包含 task_instruction（使用新的TaskInstruction结构）
3. dynamic_role_name 是必填项，要根据本项目需求创造一个精准反映该角色职责的名称
4. 不要输出 task_distribution 字段（系统会自动生成）
5. **核心角色的deliverables数量必须明显多于支持角色**
6. **每个 deliverable 必须包含 source_task_ids**：引用「核心任务结构化索引」中的 task_id（如 "CT-a1b2c3d4"），标明该交付物对应哪个用户核心任务。
   如果需求文本中包含 task_id 索引，必须使用；如果没有则留空数组。
7. **每个 task_instruction 也必须包含 source_task_ids**：合并该角色所有 deliverable 的 source_task_ids。
8. **确保 100% 任务覆盖**：所有核心任务的 task_id 至少被一个 deliverable 的 source_task_ids 引用。

请严格按照上述格式和任务量要求返回结果。
"""

        # v9.4: 注入交付物约束信息（若存在）
        primary_deliverables = getattr(self, "_current_primary_deliverables", None)
        constraint_text = self._format_deliverable_constraints(primary_deliverables)
        if constraint_text:
            prompt += f"\n\n⚠️ 重要约束（必须满足）:\n{constraint_text}\n"

        return prompt

    def _generate_weight_explanation(self, weights: Dict[str, float]) -> str:
        """
        生成权重说明

        Args:
            weights: 权重字典

        Returns:
            权重说明文本
        """
        lines = ["# 权重信息与任务量分配指引", "", "基于需求文本中的关键词，系统计算出以下角色权重：", ""]

        # 按权重排序
        sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)

        for role, weight in sorted_weights:
            if weight > 0.1:  # 只显示有意义的权重
                # 根据权重推荐任务量
                if weight >= 2.5:
                    task_recommendation = "→ 建议分配 **4-6个交付物**（核心角色）"
                elif weight >= 2.0:
                    task_recommendation = "→ 建议分配 **2-3个交付物**（重要角色）"
                elif weight >= 1.5:
                    task_recommendation = "→ 建议分配 **1-2个交付物**（支持角色）"
                else:
                    task_recommendation = "→ 建议分配 **1个交付物**（辅助角色）"

                lines.append(f"- **{role}**: {weight:.1f} {task_recommendation}")

        lines.extend(
            [
                "",
                "**权重说明与任务量对应关系**：",
                "- 权重 ≥2.5：强烈推荐，与需求高度匹配 → **分配4-6个交付物**",
                "- 权重 2.0-2.4：适度推荐，有一定匹配度 → **分配2-3个交付物**",
                "- 权重 1.5-1.9：基础角色或中等匹配 → **分配1-2个交付物**",
                "- 权重 <1.5：弱匹配或非必需 → **分配1个交付物**",
                "",
                "️ **重要原则**：",
                "- V2设计总监无论权重多少，都必须分配**4-6个交付物**（作为核心整合角色）",
                "- 禁止平均分配：不同权重的角色承担的任务量应有明显差异",
                "- 权重仅供参考，最终选择需要你综合判断需求的隐含意图",
                "",
            ]
        )

        return "\n".join(lines)

    def explain_selection(self, selection: RoleSelection) -> str:
        """
        生成选择结果的详细说明

        Args:
            selection: 角色选择结果

        Returns:
            格式化的说明文本
        """
        lines = ["# 角色选择结果\n", f"## 选中的角色 ({len(selection.selected_roles)}个)\n"]

        for role_id in selection.selected_roles:
            try:
                base_type, rid = self.role_manager.parse_full_role_id(role_id)
                role_config = self.role_manager.get_role_config(base_type, rid)

                if role_config:
                    lines.append(f"### {role_id}")
                    lines.append(f"**名称**: {role_config.get('name', 'N/A')}")
                    lines.append(f"**任务**: {selection.task_distribution.get(role_id, 'N/A')}")
                    lines.append("")
            except Exception as e:
                lines.append(f"### {role_id}")
                lines.append(f"**错误**: 无法解析角色ID - {e}")
                lines.append("")

        lines.append("\n## 选择理由\n")
        lines.append(selection.reasoning)

        return "\n".join(lines)


# 使用示例
if __name__ == "__main__":
    import os

    from langchain_openai import ChatOpenAI

    # 初始化 - 使用 OpenAI Official API
    llm = ChatOpenAI(
        model="gpt-4.1",
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    role_manager = RoleManager()
    director = DynamicProjectDirector(llm, role_manager)

    # 测试需求
    test_requirements = """
    项目需求: 设计一个现代化的办公空间

    要求:
    1. 面积约1000平方米
    2. 需要容纳50人办公
    3. 包含会议室、休息区、开放办公区
    4. 注重自然采光和绿色环保
    5. 体现公司的创新文化
    """

    # 选择角色
    print("正在分析需求并选择角色...")
    selection = director.select_roles_for_task(test_requirements)

    # 显示结果
    print("\n" + director.explain_selection(selection))


# ============================================================================
# v3.5 Expert Collaboration: Challenge Detection & Feedback Loop
# ============================================================================


class ChallengeDetector:
    """
    v3.5挑战检测器 - 检测专家输出中的challenge_flags并处理

    职责:
    1. 检测专家输出中的challenge_flags
    2. 分类挑战类型（deeper_insight/uncertainty_clarification/competing_frames）
    3. 决策处理方式（accept/revisit/synthesize/escalate）
    4. 记录挑战日志
    """

    def __init__(self):
        self.challenge_log = []

    def detect_challenges(self, expert_outputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        检测所有专家输出中的挑战标记

        Args:
            expert_outputs: 专家输出字典，格式为 {expert_role_id: expert_output}

        Returns:
            检测结果字典，包含:
            - has_challenges: bool
            - challenges: List[Dict]
            - challenge_summary: str
        """
        challenges = []

        for expert_role, output in expert_outputs.items():
            # 检查是否有challenge_flags字段
            if isinstance(output, dict) and "challenge_flags" in output:
                challenge_flags = output.get("challenge_flags")

                # 确保challenge_flags不为空
                if challenge_flags and isinstance(challenge_flags, list):
                    for challenge in challenge_flags:
                        #  P0修复: 支持字符串类型的JSON解析
                        if isinstance(challenge, str):
                            try:
                                import json

                                # 尝试解析JSON
                                parsed_challenge = json.loads(challenge)
                                if isinstance(parsed_challenge, dict):
                                    challenge = parsed_challenge
                                    logger.debug(
                                        f" 成功解析字符串类型的challenge: {challenge.get('challenged_item', '')}"
                                    )
                                else:
                                    # 如果解析结果不是字典，抛出异常以触发fallback
                                    raise ValueError("Parsed JSON is not a dict")
                            except (json.JSONDecodeError, AttributeError, ValueError):
                                # Fallback: 将普通字符串视为挑战描述
                                logger.info(f"ℹ️ 将字符串视为简单挑战描述: {challenge[:50]}...")
                                challenge = {
                                    "challenged_item": "General Issue",
                                    "rationale": challenge,
                                    "reinterpretation": "N/A",
                                    "design_impact": "See rationale",
                                }

                        # 检查challenge是否为字典类型
                        if not isinstance(challenge, dict):
                            logger.warning(f"️ 跳过非字典类型的challenge: {type(challenge)}")
                            continue

                        # 添加专家角色信息
                        challenge_with_role = {
                            "expert_role": expert_role,
                            "challenged_item": challenge.get("challenged_item", ""),
                            "rationale": challenge.get("rationale", ""),
                            "reinterpretation": challenge.get("reinterpretation", ""),
                            "design_impact": challenge.get("design_impact", ""),
                        }
                        challenges.append(challenge_with_role)

                        # 记录到日志
                        self.challenge_log.append(
                            {
                                "timestamp": datetime.now().isoformat(),
                                "expert_role": expert_role,
                                "challenge": challenge_with_role,
                            }
                        )

                        logger.warning(f" 检测到挑战 from {expert_role}: {challenge.get('challenged_item')}")

        #  修复P1: 改进挑战检测逻辑,确保正确识别challenge_flags
        has_challenges = len(challenges) > 0

        result = {
            "has_challenges": has_challenges,
            "challenges": challenges,
            "challenge_summary": self._summarize_challenges(challenges) if has_challenges else "",
        }

        if has_challenges:
            logger.warning(f" [v3.5] 共检测到 {len(challenges)} 个挑战标记,触发反馈循环")
            for i, ch in enumerate(challenges, 1):
                logger.warning(f"    挑战{i}: {ch.get('expert_role')} 对 '{ch.get('challenged_item')}' 提出质疑")
        else:
            logger.info(" [v3.5] 未检测到挑战标记，专家接受需求分析师的洞察")

        return result

    def _summarize_challenges(self, challenges: List[Dict]) -> str:
        """生成挑战摘要"""
        summary_parts = []
        for i, challenge in enumerate(challenges, 1):
            summary_parts.append(
                f"{i}. **{challenge['expert_role']}** 挑战了 '{challenge['challenged_item']}':\n"
                f"   理由: {challenge['rationale'][:100]}...\n"
                f"   重新诠释: {challenge['reinterpretation'][:100]}..."
            )
        return "\n\n".join(summary_parts)

    def classify_challenge_type(self, challenge: Dict[str, Any]) -> str:
        """
        分类挑战类型

        Returns:
            challenge_type: "deeper_insight" | "uncertainty_clarification" | "competing_frames" | "other"
        """
        challenged_item = challenge.get("challenged_item", "").lower()
        rationale = challenge.get("rationale", "").lower()

        # 根据关键词判断类型
        if "更深" in rationale or "深刻" in rationale or "真正" in rationale:
            return "deeper_insight"
        elif "不确定" in challenged_item or "模糊" in challenged_item or "标记" in rationale:
            return "uncertainty_clarification"
        elif "框架" in challenged_item or "理解" in challenged_item or "诠释" in rationale:
            return "competing_frames"
        else:
            return "other"

    def decide_handling(self, challenge: Dict[str, Any], challenge_type: str) -> str:
        """
        决策挑战处理方式

        Args:
            challenge: 挑战详情
            challenge_type: 挑战类型

        Returns:
            handling_decision: "accept" | "revisit_ra" | "synthesize" | "escalate"
        """
        # 根据挑战类型决定处理方式
        if challenge_type == "deeper_insight":
            # 专家发现了更深的洞察 → 接受专家的重新诠释
            logger.info(" 决策: 接受专家的更深洞察")
            return "accept"

        elif challenge_type == "uncertainty_clarification":
            # 专家标记了不确定性需要澄清 → 回访需求分析师或用户
            logger.info(" 决策: 回访需求分析师或用户确认")
            return "revisit_ra"

        elif challenge_type == "competing_frames":
            # 存在竞争性框架 → 综合多个方案
            logger.info(" 决策: 综合多个诠释框架")
            return "synthesize"

        else:
            # 其他情况 → 交甲方裁决
            logger.info(" 决策: 交甲方裁决")
            return "escalate"

    def handle_challenges(self, detection_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理所有检测到的挑战

        Returns:
            handling_result: {
                "handling_decisions": List[Dict],  # 每个挑战的处理决策
                "requires_revisit": bool,          # 是否需要回访需求分析师
                "requires_synthesis": bool,        # 是否需要综合多方案
                "escalated_challenges": List[Dict] # 需要交甲方裁决的挑战
            }
        """
        if not detection_result["has_challenges"]:
            return {
                "handling_decisions": [],
                "requires_revisit": False,
                "requires_synthesis": False,
                "escalated_challenges": [],
            }

        handling_decisions = []
        requires_revisit = False
        requires_synthesis = False
        escalated_challenges = []

        for challenge in detection_result["challenges"]:
            # 分类
            challenge_type = self.classify_challenge_type(challenge)

            # 决策
            decision = self.decide_handling(challenge, challenge_type)

            handling_decisions.append({"challenge": challenge, "challenge_type": challenge_type, "decision": decision})

            # 更新标志
            if decision == "revisit_ra":
                requires_revisit = True
            elif decision == "synthesize":
                requires_synthesis = True
            elif decision == "escalate":
                escalated_challenges.append(challenge)

        result = {
            "handling_decisions": handling_decisions,
            "requires_revisit": requires_revisit,
            "requires_synthesis": requires_synthesis,
            "escalated_challenges": escalated_challenges,
        }

        logger.info(
            f" 挑战处理完成: 回访={requires_revisit}, 综合={requires_synthesis}, 升级={len(escalated_challenges)}"
        )

        return result

    def get_challenge_log(self) -> List[Dict]:
        """获取完整的挑战日志"""
        return self.challenge_log


def _apply_accepted_reinterpretation(state: Dict[str, Any], challenge: Dict[str, Any]) -> None:
    """
    应用被接受的专家重新诠释 - Accept决策的闭环逻辑

    将专家的新洞察更新到state中，使其对后续分析和报告生成可见

    Args:
        state: 工作流状态（会被原地修改）
        challenge: 包含专家重新诠释的挑战详情
    """
    #  P0修复: 防御性检查
    if not isinstance(challenge, dict):
        logger.error(f" _apply_accepted_reinterpretation 收到非字典类型challenge: {type(challenge)}")
        return

    expert_role = challenge.get("expert_role", "unknown")
    challenged_item = challenge.get("challenged_item", "")
    reinterpretation = challenge.get("reinterpretation", "")
    design_impact = challenge.get("design_impact", "")

    # 初始化expert_driven_insights字段
    if "expert_driven_insights" not in state:
        state["expert_driven_insights"] = {}

    # 记录采纳的新洞察
    state["expert_driven_insights"][challenged_item] = {
        "original_interpretation": "需求分析师的初始判断",
        "expert_reinterpretation": reinterpretation,
        "accepted_from": expert_role,
        "design_impact": design_impact,
        "timestamp": datetime.now().isoformat(),
        "status": "accepted",
    }

    # 通知机制：记录洞察更新，供其他专家参考
    if "insight_updates" not in state:
        state["insight_updates"] = []

    state["insight_updates"].append(
        {
            "item": challenged_item,
            "new_interpretation": reinterpretation,
            "source": expert_role,
            "reason": "专家提出更深洞察，已被项目总监接受",
        }
    )

    logger.info(f" [Accept闭环] 采纳{expert_role}对'{challenged_item}'的重新诠释")


def _synthesize_competing_frames(state: Dict[str, Any], challenges: List[Dict[str, Any]]) -> None:
    """
    综合多个竞争性框架 - Synthesize决策的闭环逻辑

    当多个专家对同一事项提出不同诠释时，综合成混合方案

    Args:
        state: 工作流状态（会被原地修改）
        challenges: 需要综合的挑战列表
    """
    if not challenges:
        return

    # 提取所有竞争性框架
    competing_interpretations = []
    for challenge in challenges:
        competing_interpretations.append(
            {
                "expert": challenge.get("expert_role", "unknown"),
                "challenged_item": challenge.get("challenged_item", ""),
                "interpretation": challenge.get("reinterpretation", ""),
                "rationale": challenge.get("rationale", ""),
                "design_impact": challenge.get("design_impact", ""),
            }
        )

    # 分组：按challenged_item分组
    from collections import defaultdict

    grouped = defaultdict(list)
    for interp in competing_interpretations:
        grouped[interp["challenged_item"]].append(interp)

    # 为每个有竞争的项生成综合方案
    if "framework_synthesis" not in state:
        state["framework_synthesis"] = {}

    for item, interpretations in grouped.items():
        if len(interpretations) > 1:
            # 多个框架需要综合
            synthesis_summary = f"检测到{len(interpretations)}个竞争性框架:\n"
            for i, interp in enumerate(interpretations, 1):
                synthesis_summary += f"{i}. {interp['expert']}: {interp['interpretation'][:100]}...\n"

            state["framework_synthesis"][item] = {
                "competing_frames": interpretations,
                "synthesis_summary": synthesis_summary,
                "recommendation": "建议在报告中并列展示多个方案，根据具体情境选择",
                "requires_deep_analysis": True,
            }

            logger.info(f" [Synthesize闭环] 综合{len(interpretations)}个关于'{item}'的竞争性框架")

    # 标记需要综合
    state["has_competing_frameworks"] = True
    state["synthesis_required"] = True


def detect_and_handle_challenges_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    工作流节点：挑战检测与处理 + 闭环执行

    在所有专家完成输出后调用，检测challenge_flags并决策处理方式

     v3.5.1 新增闭环机制:
    - Accept决策: 更新expert_driven_insights
    - Synthesize决策: 综合竞争性框架
    - Escalate决策: 标记需要甲方裁决

    Args:
        state: 工作流状态，包含所有专家的输出

    Returns:
        更新的状态，包含挑战检测和处理结果
    """
    logger.info(" 开始检测专家挑战...")

    # 初始化检测器
    detector = ChallengeDetector()

    # 收集所有专家输出
    expert_outputs = {}

    #  修复：从正确的字段读取专家输出
    # 专家输出存储在 state["agent_results"] 中
    agent_results = state.get("agent_results", {})

    logger.debug(f" 开始扫描 {len(agent_results)} 个专家输出...")

    for agent_id, agent_data in agent_results.items():
        # agent_data 是 AgentExecutionResult 对象转换的字典
        if isinstance(agent_data, dict):
            # 提取 structured_data 字段（专家的结构化输出）
            structured_data = agent_data.get("structured_data", {})
            if structured_data:
                expert_outputs[agent_id] = structured_data
                logger.debug(f"    提取 {agent_id} 的输出 (包含 {len(structured_data.keys())} 个字段)")
            elif agent_data.get("challenge_flags"):
                # 兼容旧格式：challenge_flags 直接附着在 agent_data 上
                expert_outputs[agent_id] = agent_data
                logger.debug(f"    从 {agent_id} 捕获直连的 challenge_flags")
            else:
                logger.debug(f"   ️ {agent_id} 的 structured_data 为空")

    #  兼容批次聚合结果中的 challenge_flags（tests 直接写在 batch_results 中）
    batch_results = state.get("batch_results", {})
    for batch_id, batch_data in batch_results.items():
        if not isinstance(batch_data, dict):
            continue
        for agent_id, agent_payload in batch_data.items():
            if not isinstance(agent_payload, dict):
                continue

            candidate = (
                agent_payload.get("structured_data")
                if isinstance(agent_payload.get("structured_data"), dict)
                else agent_payload
            )
            if isinstance(candidate, dict) and candidate.get("challenge_flags"):
                if agent_id not in expert_outputs:
                    expert_outputs[agent_id] = candidate
                    logger.debug(f"    从 batch {batch_id} 捕获 {agent_id} 的 challenge_flags")

    # 检测挑战
    detection_result = detector.detect_challenges(expert_outputs)

    # 处理挑战
    handling_result = detector.handle_challenges(detection_result)

    # 更新state（只返回新增/修改的字段，避免与上游节点的状态更新冲突）
    updated_state = {
        "challenge_detection": detection_result,
        "challenge_handling": handling_result,
        "has_active_challenges": detection_result["has_challenges"],
        "requires_feedback_loop": handling_result["requires_revisit"],
    }

    #  执行闭环逻辑
    handling_decisions = handling_result.get("handling_decisions", [])

    # 1️⃣ Accept闭环: 应用被接受的重新诠释
    accepted_challenges = [d["challenge"] for d in handling_decisions if d["decision"] == "accept"]
    for challenge in accepted_challenges:
        _apply_accepted_reinterpretation(state, challenge)

    if accepted_challenges:
        updated_state["accepted_reinterpretations_count"] = len(accepted_challenges)
        logger.info(f" [Accept闭环] 应用了{len(accepted_challenges)}个专家的重新诠释")

    # 2️⃣ Synthesize闭环: 综合竞争性框架
    if handling_result.get("requires_synthesis"):
        synthesis_challenges = [d["challenge"] for d in handling_decisions if d["decision"] == "synthesize"]
        _synthesize_competing_frames(state, synthesis_challenges)
        updated_state["synthesis_required"] = True
        logger.info(f" [Synthesize闭环] 综合了{len(synthesis_challenges)}个竞争性框架")

    # 3️⃣ Escalate闭环: 标记需要甲方裁决的挑战
    escalated = handling_result.get("escalated_challenges", [])
    if escalated:
        # 格式化为审核系统能理解的问题格式
        escalated_issues = []
        for challenge in escalated:
            escalated_issues.append(
                {
                    "issue_id": (
                        f"CHALLENGE_{challenge.get('expert_role', 'unknown')}_"
                        f"{datetime.now().strftime('%H%M%S')}"
                    ),
                    "type": "strategic_decision",
                    "severity": "high",
                    "description": f"{challenge.get('expert_role')}挑战了'{challenge.get('challenged_item')}'",
                    "expert_rationale": challenge.get("rationale", ""),
                    "reinterpretation": challenge.get("reinterpretation", ""),
                    "design_impact": challenge.get("design_impact", ""),
                    "requires_client_decision": True,
                }
            )

        updated_state["escalated_challenges"] = escalated_issues
        updated_state["requires_client_review"] = True
        logger.warning(f" [Escalate闭环] {len(escalated)}个挑战需要甲方裁决")

    # 如果需要回访，记录原因
    if handling_result["requires_revisit"]:
        logger.warning("️ 检测到需要回访需求分析师的挑战")
        updated_state["feedback_loop_reason"] = "Expert challenges require clarification"

    return updated_state
