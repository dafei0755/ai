"""
动态项目总监智能体 - Dynamic Project Director Agent

基于角色配置系统的项目总监,负责分析需求并选择合适的专业角色。
Project Director based on role configuration system.
"""

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Union

from langchain_core.exceptions import OutputParserException
from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger
from pydantic import BaseModel, Field, ValidationError, model_validator

from intelligent_project_analyzer.core.prompt_manager import PromptManager
from intelligent_project_analyzer.core.role_manager import RoleManager
from intelligent_project_analyzer.core.task_oriented_models import (
    DeliverableFormat,
    DeliverableSpec,
    Priority,
    TaskInstruction,
    generate_task_instruction_template,
)



from ._director_models import (
    format_for_log, TaskDetail, RoleObject, RoleSelection
)  # noqa: F401
from ._challenge_detector import (
    ChallengeDetector, detect_and_handle_challenges_node
)  # noqa: F401

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

        from intelligent_project_analyzer.services.role_weight_calculator import (
            RoleWeightCalculator,
        )

        strategy_path = Path(__file__).parent.parent / "config" / "role_selection_strategy.yaml"
        self.weight_calculator = RoleWeightCalculator(str(strategy_path))
        logger.info(" 权重计算器已初始化")

    def select_roles_for_task(
        self, requirements: str, confirmed_core_tasks: List[Dict[str, Any]] | None = None, max_retries: int = 3
    ) -> RoleSelection:
        """
        根据需求选择合适的角色（带 project_scope 过滤）

        Args:
            requirements: 用户需求描述
            confirmed_core_tasks: 用户确认的核心任务列表（用于任务-交付物对齐验证）
            max_retries: 最大重试次数

        Note:
            不再需要外部传入task_complexity，由LLM根据需求自主判断项目复杂度和专家组合
        """
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
            logger.warning(f"️ 根据 scope '{project_scope}' 过滤后没有可用角色，将使用所有 {len(available_roles)} 个角色")
            filtered_roles = available_roles

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
                    logger.warning(f"️ LangChain结构化输出失败 ({type(structured_error).__name__})\n" f"   尝试从异常中恢复原始响应...")
                    raw_response = self._extract_raw_response_from_validation_error(structured_error)
                    if raw_response is None:
                        logger.error(" 无法提取LLM原始响应，将在 {max_retries-attempt} 次后降级")
                        raise structured_error

                response = self._validate_response_with_conversion(raw_response)

                #  将confirmed_core_tasks注入到response对象以便验证器使用
                if confirmed_core_tasks:
                    response._confirmed_tasks = confirmed_core_tasks

                if not response.task_distribution:
                    error_msg = " task_distribution 不能为空字典！必须为每个选择的角色分配任务。"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                task_dist_keys = set(response.task_distribution.keys())
                logger.info(f" [DEBUG] task_distribution keys: {task_dist_keys}")
                if len(task_dist_keys) != len(response.selected_roles):
                    error_msg = f" task_distribution ({len(task_dist_keys)}个) 与 selected_roles ({len(response.selected_roles)}个) 数量不一致"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                if not isinstance(response.task_distribution, dict):
                    logger.warning(f"️ task_distribution is not a dict: {type(response.task_distribution)}")
                    response = self._fix_task_distribution(response)
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
                    error_msg = f" task_distribution ({len(task_dist_keys)}个) 与 selected_roles ({len(response.selected_roles)}个) 数量不一致"
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

            response.task_distribution = fixed_distribution
            logger.info(" 成功修复 task_distribution 格式")
            return response

        except Exception as e:
            logger.error(f" Failed to fix task_distribution: {e}")
            # 创建默认 TaskDetail 字典
            response.task_distribution = {
                role_id: TaskDetail(tasks=["执行专业分析"], focus_areas=[], expected_output="", dependencies=[])
                for role_id in response.selected_roles
            }
            return response

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

        # 选择每个类别的第一个角色（V2, V3, V4, V6）
        role_objects = []
        role_categories = ["V2_设计总监", "V3_叙事与体验专家", "V4_设计研究员", "V6_专业员工群"]

        selected_base_types = set()

        for role in available_roles:
            base_type = role.get("base_type", "")
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
                            name=f"{role_name}交付物{i+1}",
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

    def _convert_legacy_format_to_v2(self, raw_response: dict) -> dict | None:
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
                            "name": focus_areas[i] if i < len(focus_areas) else f"交付物{i+1}",
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

    def _extract_raw_response_from_validation_error(self, error: Exception) -> dict | None:
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
        return f"""# 项目需求

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
            "success_criteria": ["标准1", "标准2"]
          }}
        ],
        "success_criteria": ["整体成功标准1", "标准2"],
        "constraints": ["约束条件"],
        "context_requirements": ["上下文要求"]
      }},
      "dependencies": ["依赖的其他角色ID"],
      "execution_priority": 1
    }},
    ...
  ],
  "reasoning": "选择理由（至少50个字符，要说明为何不同角色承担不同数量的任务）"
}}

 关键注意事项：
1. selected_roles 必须是对象数组，不能是字符串数组！
2. 每个角色对象必须包含 task_instruction（使用新的TaskInstruction结构）
3. dynamic_role_name 是必填项，要根据本项目需求创造一个精准反映该角色职责的名称
4. 不要输出 task_distribution 字段（系统会自动生成）
5. **核心角色的deliverables数量必须明显多于支持角色**

请严格按照上述格式和任务量要求返回结果。
"""

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


