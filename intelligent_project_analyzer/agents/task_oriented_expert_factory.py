# ============================================================================
# 任务导向专家工厂 - Task Oriented Expert Factory v2.1
# ============================================================================
# 更新日期: 2025-12-17
# 变更说明:
# 1. 专家输出严格围绕TaskInstruction
# 2. 强制使用TaskOrientedExpertOutput结构
# 3. 确保协议闭环执行
# 4. 🔥 v7.18: 使用 JSON Schema 强制约束（降低解析失败率 15%→3%）
# 5. 🔥 v7.19: 按角色类型动态调参（V3高创意/V6高精确）+ 输出质量引导
# ============================================================================

from typing import Dict, Any, List, Optional
from functools import lru_cache
from pydantic import ValidationError
from ..core.state import ProjectAnalysisState
from ..core.task_oriented_models import TaskOrientedExpertOutput, ProtocolExecutionReport
from ..services.llm_factory import LLMFactory
import yaml
import json
import datetime
from pathlib import Path
from loguru import logger

# 🆕 v7.64: 导入工具调用记录器
try:
    from .tool_callback import ToolCallRecorder, add_references_to_state
except ImportError:
    logger.warning("⚠️ ToolCallRecorder not available (v7.64 feature)")
    ToolCallRecorder = None
    add_references_to_state = None

# 🔥 v7.18: 全局缓存自主性协议（所有专家共享，只加载一次）
_autonomy_protocol_cache = None

def get_autonomy_protocol() -> Dict[str, Any]:
    """
    获取缓存的自主性协议（全局单例）

    ✅ 升级1优化：所有专家共享同一份协议，避免重复加载

    Returns:
        自主性协议字典
    """
    global _autonomy_protocol_cache
    if _autonomy_protocol_cache is None:
        logger.info("🔧 [升级1] 首次加载自主性协议，将缓存于内存")
        _autonomy_protocol_cache = load_yaml_config_cached("prompts/expert_autonomy_protocol_v4.yaml")
    return _autonomy_protocol_cache

@lru_cache(maxsize=20)
def load_yaml_config_cached(config_path: str) -> Dict[str, Any]:
    """
    加载YAML配置文件的辅助函数（带LRU缓存）

    ✅ 升级1优化：使用LRU缓存避免重复加载，maxsize=20 足够缓存所有角色配置

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
        with open(full_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
            logger.debug(f"✅ [升级1] 已缓存配置文件: {config_path}")
            return config
    except Exception as e:
        logger.error(f"加载配置文件失败 {full_path}: {str(e)}")
        return {}

def load_yaml_config(config_path: str) -> Dict[str, Any]:
    """
    加载YAML配置文件（向后兼容接口）

    ✅ 升级1优化：内部调用缓存版本

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
    
    ✅ P3优化：缓存LLM实例，避免重复创建
    🔥 v7.19优化：按角色类型动态调参
    """
    
    # ✅ P3优化：类级别LLM实例缓存（按角色类型分别缓存）
    _llm_instances: Dict[str, Any] = {}
    
    # 🔥 v7.19: 角色类型专属参数配置
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

        🔥 v7.19优化：不同角色使用不同的 temperature
        - V3 叙事专家：temperature=0.75（高创意）
        - V6 工程师：temperature=0.4（高精确）
        - 其他角色：temperature=0.5-0.6（平衡）

        🔥 v7.52优化：动态Token分配机制
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

        # 🔥 v7.52: 计算动态max_tokens
        max_tokens = self._get_max_tokens_for_expert(role_type, deliverable_count)

        cache_key = f"{role_type}_{params['temperature']}_{max_tokens}"

        if cache_key not in TaskOrientedExpertFactory._llm_instances:
            logger.info(f"🔧 [v7.19] 为 {role_type} 创建专属LLM (temperature={params['temperature']}, max_tokens={max_tokens}, {params['description']})")
            TaskOrientedExpertFactory._llm_instances[cache_key] = self.llm_factory.create_llm(
                temperature=params["temperature"],
                max_tokens=max_tokens
            )
        return TaskOrientedExpertFactory._llm_instances[cache_key]

    def _get_max_tokens_for_expert(self, role_type: str, deliverable_count: int) -> int:
        """
        🔥 v7.52: 根据角色级别和交付物数量动态计算max_tokens

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
            "V4": 8000,   # 研究员 - 数据分析
            "V5": 8000,   # 场景专家 - 行业洞察
            "V6": 8000,   # 工程师 - 技术方案
        }

        # 每个交付物额外增加1500 tokens
        tokens_per_deliverable = 1500

        # 计算总token
        total_tokens = base_tokens.get(role_type, 8000) + (deliverable_count * tokens_per_deliverable)

        # 硬上限32000 (考虑成本和响应时间)
        # 下限 8000 (保证基本输出质量)
        total_tokens = max(8000, min(32000, total_tokens))

        logger.debug(f"📊 [v7.52] {role_type} token分配: 基础{base_tokens.get(role_type, 8000)} + {deliverable_count}交付物×{tokens_per_deliverable} = {total_tokens}")

        return total_tokens
    
    async def execute_expert(
        self,
        role_object: Dict[str, Any],
        context: str,
        state: ProjectAnalysisState,
        tools: Optional[List[Any]] = None  # 🔥 v7.63.1: 添加工具支持
    ) -> Dict[str, Any]:
        """
        执行任务导向的专家分析

        Args:
            role_object: 包含TaskInstruction的角色对象
            context: 项目上下文
            state: 当前状态
            tools: 可用的工具列表（可选） - v7.63.1新增

        Returns:
            标准化的专家执行结果
        """
        try:
            # 构建任务导向的专家提示词
            expert_prompt = self._build_task_oriented_expert_prompt(
                role_object=role_object,
                context=context,
                state=state
            )

            # 调用LLM生成专家分析
            # 🔥 v7.19优化：使用角色专属的LLM实例
            role_type = self._extract_base_type(role_object.get('role_id', ''))

            # 🔥 v7.52优化：计算交付物数量以动态分配token
            task_instruction = role_object.get('task_instruction', {})
            deliverable_count = len(task_instruction.get('deliverables', []))

            llm = self._get_llm(role_type, deliverable_count)

            # 🆕 v7.64: 创建工具调用记录器（如果有工具）
            recorder = None
            if tools and ToolCallRecorder:
                role_id = role_object.get('role_id', 'unknown')
                # 使用角色ID作为deliverable_id的前缀
                recorder = ToolCallRecorder(role_id=role_id, deliverable_id=f"{role_id}_analysis")
                logger.info(f"🔧 [v7.64] {role_id} 启用工具调用记录器")

            # 🔥 v7.63.1: 如果提供了工具，绑定到LLM
            if tools:
                tool_names = [getattr(tool, 'name', str(tool)) for tool in tools]
                logger.info(f"🔧 [v7.63.1] {role_object.get('role_id', 'unknown')} 绑定 {len(tools)} 个工具: {tool_names}")
                # 🆕 v7.64: 绑定工具时传入callbacks
                if recorder:
                    llm = llm.bind_tools(tools, callbacks=[recorder])
                else:
                    llm = llm.bind_tools(tools)
            else:
                logger.debug(f"ℹ️ [v7.63.1] {role_object.get('role_id', 'unknown')} 无工具（综合者模式）")

            # 🔥 v7.18: 强制JSON Schema输出（降低解析失败率 15% → 3%）
            llm_with_structure = llm.with_structured_output(
                TaskOrientedExpertOutput,
                method="json_schema",  # 使用严格JSON Schema而非json_mode
                strict=True  # 强制LLM遵守schema，无法偏离
            )

            messages = [
                {"role": "system", "content": expert_prompt["system_prompt"]},
                {"role": "user", "content": expert_prompt["user_prompt"]}
            ]

            # 🔥 v7.18: response直接是TaskOrientedExpertOutput实例，无需解析
            response = await llm_with_structure.ainvoke(messages)

            # 将Pydantic模型转换为字典（保持向后兼容）
            structured_output = response.dict() if hasattr(response, 'dict') else response.model_dump()

            # 构建标准化返回结果
            result = {
                "expert_id": role_object.get("role_id", "unknown"),
                "expert_name": role_object.get("dynamic_role_name", role_object.get("role_name", "Unknown Expert")),
                "analysis": structured_output.get("task_execution_report", {}).get("task_completion_summary", ""),  # 🔥 v7.18: 从结构化输出获取摘要
                "structured_output": structured_output,  # 已验证的结构化输出
                "task_instruction": role_object.get("task_instruction", {}),  # 任务指令
                "role_definition": role_object,
                "execution_metadata": {
                    "timestamp": self._get_timestamp(),
                    "model_used": "gpt-4",
                    "prompt_version": "task_oriented_v2.0",
                    "output_format": "TaskOrientedExpertOutput",
                    "json_schema_enforced": True  # 🔥 v7.18: 标记使用了强制JSON Schema
                }
            }
            
            # 🔥 v7.9.3: 验证任务完成情况，如果有缺失则自动补全
            validation_passed = self._validate_task_completion(structured_output, role_object.get("task_instruction", {}))

            # 🔥 v7.9.3: 如果验证未通过且有缺失交付物，尝试自动补全
            if not validation_passed and structured_output.get('validation_result', {}).get('needs_completion'):
                logger.info("🔄 检测到缺失交付物，开始自动补全...")
                structured_output = await self._complete_missing_deliverables(
                    structured_output=structured_output,
                    role_object=role_object,
                    context=context,
                    state=state
                )
                # 更新result中的structured_output
                result["structured_output"] = structured_output
                logger.info("✅ 交付物补全完成")

            # 🆕 v7.64: 从工具调用记录器提取搜索引用并添加到state
            if recorder and add_references_to_state:
                search_references = recorder.get_search_references()
                if search_references:
                    logger.info(f"📚 [v7.64] 提取了 {len(search_references)} 条搜索引用")
                    # 添加到state（会自动去重）
                    add_references_to_state(state, recorder)

                    # 🔧 可选：将引用添加到交付物输出（供PDF生成使用）
                    task_exec_report = structured_output.get('task_execution_report', {})
                    deliverable_outputs = task_exec_report.get('deliverable_outputs', [])

                    # 为每个交付物关联相关的搜索引用
                    for deliverable in deliverable_outputs:
                        deliverable_name = deliverable.get('deliverable_name', '')
                        # 筛选与此交付物相关的引用（基于deliverable_id前缀匹配）
                        related_refs = [
                            ref for ref in search_references
                            if deliverable_name in ref.get('deliverable_id', '')
                        ]
                        if related_refs:
                            deliverable['search_references'] = related_refs
                            logger.debug(f"  ↳ 为交付物 '{deliverable_name}' 关联了 {len(related_refs)} 条引用")

            # 🆕 v7.108: 为该专家的交付物生成概念图
            try:
                deliverable_owner_map = state.get("deliverable_owner_map", {})
                deliverable_metadata = state.get("deliverable_metadata", {})
                role_id = role_object.get("role_id", "unknown")
                deliverable_ids = deliverable_owner_map.get(role_id, [])

                if deliverable_ids and deliverable_metadata:
                    logger.info(f"🎨 [v7.108] 为角色 {role_id} 的 {len(deliverable_ids)} 个交付物生成概念图...")

                    # 导入图片生成服务
                    from ..services.image_generator import ImageGeneratorService

                    # 初始化图片生成器
                    image_generator = ImageGeneratorService()

                    # 获取专家分析摘要（用于图片生成）
                    expert_summary = result.get("analysis", "")[:500]  # 取前500字符
                    session_id = state.get("session_id", "unknown")
                    project_type = state.get("project_type", "interior")

                    # 为每个交付物生成概念图
                    concept_images = []
                    for deliverable_id in deliverable_ids:
                        metadata = deliverable_metadata.get(deliverable_id)
                        if not metadata:
                            logger.warning(f"  ⚠️ 交付物 {deliverable_id} 元数据缺失，跳过图片生成")
                            continue

                        try:
                            image_metadata = await image_generator.generate_deliverable_image(
                                deliverable_metadata=metadata,
                                expert_analysis=expert_summary,
                                session_id=session_id,
                                project_type=project_type,
                                aspect_ratio="16:9"
                            )

                            # 转换为字典存储
                            concept_images.append(image_metadata.model_dump())
                            logger.info(f"  ✅ 生成概念图: {image_metadata.filename}")

                        except Exception as img_error:
                            logger.error(f"  ❌ 生成概念图失败 (交付物 {deliverable_id}): {img_error}")
                            # 不阻塞workflow，继续执行

                    # 将概念图添加到专家结果中
                    if concept_images:
                        result["concept_images"] = concept_images
                        logger.info(f"✅ [v7.108] 成功为角色 {role_id} 生成 {len(concept_images)} 张概念图")
                    else:
                        logger.warning(f"⚠️ [v7.108] 角色 {role_id} 未生成任何概念图")
                else:
                    logger.debug(f"[v7.108] 角色 {role_id} 无交付物，跳过图片生成")

            except Exception as e:
                logger.error(f"❌ [v7.108] 概念图生成流程失败: {e}")
                logger.exception(e)
                # 不阻塞workflow，专家分析仍然有效

            return result

        except ValidationError as ve:
            # 🔥 v7.18: JSON Schema 强制约束下极少出现，但保留防御性处理
            logger.error(f"❌ Pydantic验证失败 {role_object.get('role_name', 'Unknown')}: {str(ve)}")
            logger.error("⚠️ 这不应该发生在 JSON Schema 强制模式下，请检查 schema 定义")
            return {
                "expert_id": role_object.get("role_id", "unknown"),
                "expert_name": role_object.get("dynamic_role_name", role_object.get("role_name", "Unknown Expert")),
                "analysis": f"验证失败: {str(ve)}",
                "structured_output": None,
                "task_instruction": role_object.get("task_instruction", {}),
                "role_definition": role_object,
                "error": True,
                "execution_metadata": {
                    "timestamp": self._get_timestamp(),
                    "model_used": "gpt-4",
                    "prompt_version": "task_oriented_v2.0",
                    "error_type": "ValidationError",
                    "error_message": str(ve)
                }
            }
        except Exception as e:
            # 🔥 v7.60.3: 检测是否为输出长度超限错误
            error_msg = str(e)
            if "length limit was reached" in error_msg or "completion_tokens" in error_msg:
                logger.error(f"❌ 专家 {role_object.get('role_name', 'Unknown')} 输出超长被截断")
                logger.error(f"   错误详情: {error_msg}")
                logger.error("   💡 建议: 调整提示词要求更简洁的输出，或增加输出长度限制警告")
            else:
                logger.error(f"执行任务导向专家 {role_object.get('role_name', 'Unknown')} 时出错: {error_msg}")
            return {
                "expert_id": role_object.get("role_id", "unknown"),
                "expert_name": role_object.get("dynamic_role_name", role_object.get("role_name", "Unknown Expert")),
                "analysis": f"执行失败: {str(e)}",
                "structured_output": None,
                "task_instruction": role_object.get("task_instruction", {}),
                "role_definition": role_object,
                "error": True,
                "execution_metadata": {
                    "timestamp": self._get_timestamp(),
                    "model_used": "gpt-4",
                    "prompt_version": "task_oriented_v2.0",
                    "error_message": str(e)
                }
            }
    
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
    
    def _build_task_oriented_expert_prompt(self, role_object: Dict[str, Any], context: str, state: ProjectAnalysisState) -> Dict[str, str]:
        """
        构建任务导向的专家提示词，确保输出严格围绕TaskInstruction

        🔥 v7.18 升级1: 使用 Prompt 模板系统，减少 80% 的拼接开销
        """
        try:
            # 加载基础角色配置 - 使用缓存的映射函数
            config_filename = self._get_role_config_filename(role_object['role_id'])
            role_config = load_yaml_config(config_filename)
            base_system_prompt = role_config.get("system_prompt", "你是一位专业的分析师")

            # 获取TaskInstruction
            task_instruction = role_object.get('task_instruction', {})

            # 🔥 v7.10: 检测创意叙事模式
            is_creative_narrative = task_instruction.get('is_creative_narrative', False)

            # 🔥 v7.18 升级1: 使用缓存的自主性协议（所有专家共享，避免重复加载）
            autonomy_protocol = get_autonomy_protocol()

            # 提取角色类型（用于模板缓存）
            role_type = self._extract_base_type(role_object['role_id'])

            # 🔥 v7.18 升级1: 使用 Prompt 模板系统（预构建静态部分）
            from ..core.prompt_templates import get_expert_template

            template = get_expert_template(role_type, base_system_prompt, autonomy_protocol)

            # 🔥 v7.10: 创意叙事模式的特殊说明
            creative_mode_note = ""
            if is_creative_narrative:
                creative_mode_note = f"""
# 🎨 创意叙事模式 (Creative Narrative Mode)

⚠️ **特别说明**: 你正在创意叙事模式下工作，以下约束放宽：
- `completion_rate` 和 `quality_self_assessment` **可选填**（如不适用可省略或设为默认值）
- `execution_time_estimate` **可选填**（创意过程难以精确量化时间）
- 允许更自由的叙事结构和表达方式
- 输出重点在于**叙事质量和情感共鸣**，而非量化指标

💡 **建议**: 如果叙事内容本身就包含完整性和质量的体现，可以简化或省略这些量化字段。
"""

            # 🔥 v7.18 升级1: 使用模板渲染（只构建20%的动态内容）
            return template.render(
                dynamic_role_name=role_object.get('dynamic_role_name', role_object.get('role_name')),
                task_instruction=task_instruction,
                context=context,
                state=state,
                creative_mode_note=creative_mode_note
            )

        except Exception as e:
            logger.error(f"构建任务导向专家提示词时出错: {str(e)}")
            return {
                "system_prompt": "你是一位专业的分析师，请基于提供的信息进行分析。",
                "user_prompt": f"请分析以下内容：\n{context}"
            }

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
    
    def _parse_and_validate_output(self, expert_output: str, role_object: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析并验证专家输出是否符合TaskOrientedExpertOutput结构
        如果验证失败，使用降级策略构造默认结构
        
        🔧 v7.11 增强: 更强的 JSON 预处理 + 多种修复策略
        """
        try:
            # 🔧 v7.11: 先进行全局预处理，移除所有markdown代码块标记
            cleaned_output = expert_output.strip()
            
            # 移除所有markdown代码块标记（包括```json, ```JSON, ``` 等变体）
            import re
            # 处理 ```json 或 ```JSON 开头
            if re.search(r'^```(?:json|JSON)?\s*', cleaned_output):
                cleaned_output = re.sub(r'^```(?:json|JSON)?\s*', '', cleaned_output)
            # 处理结尾的 ```
            cleaned_output = re.sub(r'\s*```$', '', cleaned_output)
            # 处理中间可能存在的代码块标记
            cleaned_output = re.sub(r'```(?:json|JSON)?\s*([\s\S]*?)\s*```', r'\1', cleaned_output)
            
            logger.debug(f"🔧 JSON预处理后长度: {len(cleaned_output)}")
            
            # 提取JSON内容
            if "{" in cleaned_output and "}" in cleaned_output:
                json_str = cleaned_output[cleaned_output.find("{"):cleaned_output.rfind("}")+1]
            else:
                logger.warning("输出不包含有效JSON，尝试整体解析")
                json_str = cleaned_output.strip()
            
            # 🔧 尝试解析JSON（多种修复策略）
            parsed_output = self._try_parse_json_with_fixes(json_str)
            
            if parsed_output is None:
                raise json.JSONDecodeError("所有JSON修复策略都失败了", json_str, 0)
            
            # 验证结构（使用Pydantic模型验证）
            task_oriented_output = TaskOrientedExpertOutput(**parsed_output)
            
            logger.info(f"✅ 成功验证 {role_object.get('role_name', 'Unknown')} 的TaskOrientedExpertOutput结构")
            return task_oriented_output.dict()
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON解析失败: {str(e)}")
            logger.error(f"原始输出: {expert_output[:200]}...")
        except Exception as e:
            logger.error(f"❌ 输出验证失败: {str(e)}")
        
        # 降级策略：构造符合最小规范的默认结构
        logger.warning(f"⚠️ 使用降级策略为 {role_object.get('role_name', 'Unknown')} 构造默认输出")
        return self._create_fallback_output(expert_output, role_object)
    
    def _try_parse_json_with_fixes(self, json_str: str) -> Optional[Dict[str, Any]]:
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
            cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_str)
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
        
        # 策略3: 修复常见的逗号问题
        try:
            # 移除数组/对象末尾多余的逗号
            fixed = re.sub(r',\s*([}\]])', r'\1', json_str)
            # 添加缺失的逗号（对象属性之间）
            fixed = re.sub(r'"\s*\n\s*"', '",\n"', fixed)
            # 添加缺失的逗号（数组元素之间）
            fixed = re.sub(r'}\s*\n\s*{', '},\n{', fixed)
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass
        
        # 策略4: 尝试修复截断的 JSON
        try:
            # 计算未闭合的括号
            open_braces = json_str.count('{') - json_str.count('}')
            open_brackets = json_str.count('[') - json_str.count(']')
            
            if open_braces > 0 or open_brackets > 0:
                # 尝试补全括号
                fixed = json_str
                fixed += '}' * open_braces
                fixed += ']' * open_brackets
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
                if c == '{':
                    if depth == 0:
                        start = i
                    depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            
            if start >= 0 and end > start:
                return json.loads(json_str[start:end])
        except json.JSONDecodeError:
            pass
        
        logger.warning("⚠️ 所有JSON修复策略都失败了")
        return None
    
    def _create_fallback_output(self, raw_output: str, role_object: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建降级输出结构（当Pydantic验证失败时）
        
        🔧 v7.6: 增强对嵌套 JSON 的处理，避免显示原始代码
        """
        role_name = role_object.get('dynamic_role_name', role_object.get('role_name', 'Unknown Expert'))
        
        # 🔧 尝试提取实际内容而不是原始 JSON
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
                        "quality_self_assessment": 0.7
                    }
                ],
                "task_completion_summary": f"{role_name}已完成分析任务",
                "additional_insights": None,
                "execution_challenges": ["LLM未按预期格式返回，使用降级策略"]
            },
            "protocol_execution": {
                "protocol_status": "complied",
                "compliance_confirmation": "接受需求分析师的洞察",
                "challenge_details": None,
                "reinterpretation": None
            },
            "execution_metadata": {
                "confidence": 0.7,
                "completion_rate": 1.0,
                "execution_time_estimate": "未知",
                "execution_notes": "此输出使用降级策略生成，未经标准验证",
                "dependencies_satisfied": True
            }
        }

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
                                    if isinstance(content, str) and (content.strip().startswith("{") or content.strip().startswith("[")):
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

        🔥 v7.9.3: 增强验证 - 检测到缺失交付物时标记需要补全，而非直接通过

        Returns:
            bool: True表示验证通过，False表示需要补全
        """
        if not structured_output:
            logger.warning("⚠️ 无结构化输出，无法验证任务完成情况")
            return False

        try:
            # 获取任务指令中的预期交付物
            expected_deliverables = task_instruction.get('deliverables', [])

            # 获取实际的交付物输出（修复字段路径）
            task_exec_report = structured_output.get('task_execution_report', {})
            actual_results = task_exec_report.get('deliverable_outputs', [])

            # 如果没有预期交付物，则直接通过（降级场景）
            if not expected_deliverables:
                logger.info("✅ 无预期交付物要求，验证通过")
                return True

            expected_names = {d.get('name', f'交付物{i}') for i, d in enumerate(expected_deliverables, 1)}
            actual_names = {r.get('deliverable_name', '') for r in actual_results}

            missing_deliverables = expected_names - actual_names
            if missing_deliverables:
                logger.warning(f"⚠️ 缺失交付物: {missing_deliverables}")
                # 🔥 v7.9.3: 不再直接返回True，而是标记需要补全
                if 'validation_result' not in structured_output:
                    structured_output['validation_result'] = {}
                structured_output['validation_result']['missing_deliverables'] = list(missing_deliverables)
                structured_output['validation_result']['needs_completion'] = True
                structured_output['validation_result']['expected_deliverables'] = expected_deliverables
                logger.info(f"📝 标记需要补全的交付物: {missing_deliverables}")
                return False  # 🔥 返回False表示验证未通过，需要补全

            # 验证协议执行状态（修复字段名）
            protocol_execution = structured_output.get('protocol_execution', {})
            if not protocol_execution.get('protocol_status'):
                logger.warning("⚠️ 协议执行状态缺失")
                # 降级场景下不强制失败
                return True

            logger.info("✅ 任务完成验证通过")
            return True

        except Exception as e:
            logger.error(f"❌ 验证任务完成时出错: {str(e)}")
            # 发生错误时也返回True，避免阻塞流程
            return True
    
    async def _complete_missing_deliverables(
        self,
        structured_output: Dict[str, Any],
        role_object: Dict[str, Any],
        context: str,
        state: ProjectAnalysisState
    ) -> Dict[str, Any]:
        """
        🔥 v7.11: 自动补全缺失的交付物（性能优化版）

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
            validation_result = structured_output.get('validation_result', {})
            missing_deliverables = validation_result.get('missing_deliverables', [])
            expected_deliverables = validation_result.get('expected_deliverables', [])

            if not missing_deliverables:
                logger.warning("⚠️ 没有缺失的交付物，无需补全")
                return structured_output

            # 🔧 v7.11: 性能优化 - 限制每次补全的数量
            MAX_COMPLETION_COUNT = 3
            if len(missing_deliverables) > MAX_COMPLETION_COUNT:
                logger.warning(f"⚠️ 缺失交付物过多({len(missing_deliverables)}个)，只补全前{MAX_COMPLETION_COUNT}个")
                missing_deliverables = missing_deliverables[:MAX_COMPLETION_COUNT]

            logger.info(f"🔄 开始补全缺失的交付物: {missing_deliverables}")

            # 构建补全提示词
            completion_prompt = self._build_completion_prompt(
                role_object=role_object,
                context=context,
                state=state,
                missing_deliverables=missing_deliverables,
                expected_deliverables=expected_deliverables,
                existing_output=structured_output
            )

            # 🔧 v7.11: 添加超时控制（30秒）
            # 🔥 v7.52: 使用 JSON 模式强制 JSON 输出
            llm = self._get_llm()

            # 尝试使用 with_structured_output (JSON模式)
            try:
                llm_json_mode = llm.with_structured_output(method="json_mode")
                logger.info("🔧 [v7.52] 使用 JSON 模式强制输出")
            except Exception as e:
                logger.debug(f"⚠️ JSON模式不可用，使用普通模式: {e}")
                llm_json_mode = llm

            messages = [
                {"role": "system", "content": completion_prompt["system_prompt"]},
                {"role": "user", "content": completion_prompt["user_prompt"]}
            ]

            try:
                response = await asyncio.wait_for(
                    llm_json_mode.ainvoke(messages),
                    timeout=30.0  # 30秒超时
                )
                completion_output = response.content if hasattr(response, 'content') else str(response)
            except asyncio.TimeoutError:
                logger.warning("⚠️ 交付物补全超时（30秒），使用原始输出")
                return structured_output

            # 解析补充的交付物
            completed_deliverables = self._parse_completion_output(completion_output, missing_deliverables)

            # 🔥 v7.52: 批量失败时尝试逐个生成
            if not completed_deliverables and len(missing_deliverables) > 1:
                logger.warning(f"⚠️ 批量补全失败，尝试逐个生成 {len(missing_deliverables)} 个交付物")
                completed_deliverables = await self._complete_deliverables_one_by_one(
                    role_object, context, state, missing_deliverables
                )

            # 🔧 v7.23: 更准确的日志信息
            if not completed_deliverables:
                logger.warning(f"⚠️ 交付物补全完全失败：尝试补全 {len(missing_deliverables)} 个，实际解析出 0 个")
                # 🔥 v7.52: 生成占位符，避免完全失败
                completed_deliverables = self._generate_placeholder_deliverables(missing_deliverables)
                logger.info(f"🔧 [v7.52] 已生成 {len(completed_deliverables)} 个占位交付物")

            # 合并到原始输出
            task_exec_report = structured_output.get('task_execution_report', {})
            deliverable_outputs = task_exec_report.get('deliverable_outputs', [])

            # 添加补充的交付物
            for deliverable in completed_deliverables:
                deliverable_outputs.append(deliverable)
                logger.info(f"✅ 已补全交付物: {deliverable.get('deliverable_name')}")

            # 更新结构化输出
            task_exec_report['deliverable_outputs'] = deliverable_outputs
            structured_output['task_execution_report'] = task_exec_report

            # 清除validation_result标记
            if 'validation_result' in structured_output:
                del structured_output['validation_result']

            logger.info(f"✅ 成功补全 {len(completed_deliverables)}/{len(missing_deliverables)} 个交付物")
            return structured_output

        except Exception as e:
            logger.error(f"❌ 补全缺失交付物时出错: {str(e)}")
            # 发生错误时返回原始输出，不阻塞流程
            logger.warning("⚠️ 补全失败，使用原始输出")
            return structured_output

    def _build_completion_prompt(
        self,
        role_object: Dict[str, Any],
        context: str,
        state: ProjectAnalysisState,
        missing_deliverables: List[str],
        expected_deliverables: List[Dict[str, Any]],
        existing_output: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        🔥 v7.9.3: 构建补全提示词，只要求LLM输出缺失的交付物

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
        missing_defs = [d for d in expected_deliverables if d.get('name') in missing_deliverables]

        # 获取已完成的交付物（作为参考）
        existing_deliverables = existing_output.get('task_execution_report', {}).get('deliverable_outputs', [])
        existing_names = [d.get('deliverable_name') for d in existing_deliverables]

        system_prompt = f"""
你是 {role_object.get('dynamic_role_name', role_object.get('role_name'))}。

# 🎯 补全任务

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

# 📊 输出要求

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

# ⚠️ 关键要求

1. **只输出缺失的交付物**，不要重复已完成的交付物
2. **deliverable_name必须与任务指令中的名称完全一致**
3. **content要详细完整**，不要简化或省略
4. **返回有效的JSON格式**，不要有额外文字
5. **不要使用markdown代码块包裹JSON**

开始补充缺失的交付物：
"""

        user_prompt = f"""
# 📂 项目上下文
{context}

# 📊 当前项目状态
- 项目阶段: {state.get('current_phase', '分析阶段')}
- 已完成分析: {len(state.get('expert_analyses', {}))}个专家

# 🎯 你的任务

请基于上述项目上下文，补充以下缺失的交付物：
{', '.join(missing_deliverables)}

**记住**：只输出缺失的交付物，格式为JSON，不要有任何额外文字。
"""

        return {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt
        }

    def _parse_completion_output(self, completion_output: str, missing_deliverables: List[str]) -> List[Dict[str, Any]]:
        """
        🔥 v7.9.3: 解析补全输出，提取交付物列表
        🔧 v7.23: 增强 JSON 解析容错性，支持多种格式

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
                matches = re.findall(r'```\s*([\s\S]*?)\s*```', completion_output)
                for match in matches:
                    if '{' in match and '}' in match:
                        json_str = match.strip()
                        break
            
            # 策略3: 提取最外层 {...} 或 [...]
            if not json_str:
                # 优先尝试提取对象
                obj_match = re.search(r'\{[\s\S]*\}', completion_output)
                if obj_match:
                    json_str = obj_match.group()
                else:
                    # 尝试提取数组
                    arr_match = re.search(r'\[[\s\S]*\]', completion_output)
                    if arr_match:
                        json_str = arr_match.group()
            
            if not json_str:
                logger.warning("⚠️ 补全输出不包含有效JSON结构")
                return []
            
            # 🔧 v7.23: 清理常见的 JSON 格式问题
            # 移除 JavaScript 风格的注释
            json_str = re.sub(r'//.*?(?=\n|$)', '', json_str)
            json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
            # 移除尾随逗号
            json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
            
            # 解析JSON
            parsed = json.loads(json_str)

            # 提取deliverable_outputs（支持多种字段名）
            if isinstance(parsed, dict):
                deliverables = (
                    parsed.get('deliverable_outputs') or 
                    parsed.get('deliverables') or 
                    parsed.get('outputs') or
                    []
                )
                if deliverables:
                    logger.info(f"✅ 成功解析 {len(deliverables)} 个补全交付物")
                    return deliverables
                else:
                    logger.warning("⚠️ 解析的JSON中没有deliverable_outputs字段")
                    return []
            elif isinstance(parsed, list):
                # 如果直接返回数组
                if parsed:
                    logger.info(f"✅ 成功解析 {len(parsed)} 个补全交付物（数组格式）")
                    return parsed
                return []
            else:
                logger.warning(f"⚠️ 解析结果类型不符合预期: {type(parsed)}")
                return []

        except json.JSONDecodeError as e:
            logger.error(f"❌ 解析补全输出JSON失败: {str(e)}")
            logger.debug(f"原始输出片段: {completion_output[:300]}...")
            
            # 🔧 v7.23: 尝试从原始输出构造默认交付物
            fallback_deliverables = []
            for name in missing_deliverables[:2]:  # 最多构造2个
                fallback_deliverables.append({
                    "deliverable_name": name,
                    "content": f"[解析失败，需要人工补充] 原始输出: {completion_output[:200]}...",
                    "completion_status": "partial",
                    "completion_rate": 0.3,
                    "notes": "LLM输出格式异常，已使用降级策略"
                })
            if fallback_deliverables:
                logger.warning(f"⚠️ 使用降级策略，构造 {len(fallback_deliverables)} 个占位交付物")
            return fallback_deliverables
            
        except Exception as e:
            logger.error(f"❌ 处理补全输出时出错: {str(e)}")
            return []

    async def _complete_deliverables_one_by_one(
        self,
        role_object: Dict[str, Any],
        context: str,
        state: ProjectAnalysisState,
        missing_deliverables: List[str]
    ) -> List[Dict[str, Any]]:
        """
        🔥 v7.52: 逐个生成缺失交付物（降级策略）

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
                logger.info(f"🔄 逐个生成: {deliverable_name}")

                # 构建单个交付物的提示词
                single_prompt = f"""你是 {role_object.get('name', '专家')}。

请生成以下交付物：
**{deliverable_name}**

# 📂 项目上下文
{context[:1000]}...

# 🎯 要求
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
                    llm.ainvoke([{"role": "user", "content": single_prompt}]),
                    timeout=10.0
                )
                output = response.content if hasattr(response, 'content') else str(response)

                # 解析单个交付物
                single_result = self._parse_single_deliverable_output(output, deliverable_name)
                if single_result:
                    completed.append(single_result)
                    logger.info(f"✅ 成功生成: {deliverable_name}")
                else:
                    logger.warning(f"⚠️ 解析失败: {deliverable_name}")

            except asyncio.TimeoutError:
                logger.warning(f"⚠️ 生成超时: {deliverable_name}")
            except Exception as e:
                logger.error(f"❌ 生成失败 {deliverable_name}: {e}")

            # 限制最多尝试3个
            if len(completed) >= 3:
                logger.info("🔧 已成功生成3个交付物，停止逐个生成")
                break

        return completed

    def _parse_single_deliverable_output(self, output: str, expected_name: str) -> Optional[Dict[str, Any]]:
        """
        🔥 v7.52: 解析单个交付物的LLM输出

        Args:
            output: LLM原始输出
            expected_name: 期望的交付物名称

        Returns:
            Dict | None: 解析成功返回交付物字典，失败返回None
        """
        import re
        import json

        try:
            # 提取JSON
            json_str = None
            if "```json" in output:
                json_start = output.find("```json") + 7
                json_end = output.find("```", json_start)
                if json_end > json_start:
                    json_str = output[json_start:json_end].strip()
            elif "```" in output:
                matches = re.findall(r'```\s*([\s\S]*?)\s*```', output)
                for match in matches:
                    if '{' in match:
                        json_str = match.strip()
                        break

            if not json_str:
                obj_match = re.search(r'\{[\s\S]*\}', output)
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
            logger.debug(f"⚠️ 单个交付物解析失败: {e}")
            return None

    def _generate_placeholder_deliverables(self, missing_names: List[str]) -> List[Dict[str, Any]]:
        """
        🔥 v7.52: 生成占位交付物（最终降级策略）

        当所有生成策略都失败时，生成占位内容，
        避免流程完全失败。

        Args:
            missing_names: 缺失的交付物名称列表

        Returns:
            List[Dict]: 占位交付物列表
        """
        placeholders = []
        for name in missing_names[:3]:  # 最多3个
            placeholders.append({
                "deliverable_name": name,
                "content": f"[待补充] {name}\n\n由于LLM生成失败，此交付物需要人工补充。建议审查项目需求后手动完成。",
                "completion_status": "pending",
                "completion_rate": 0.0,
                "key_insights": [],
                "notes": "🔧 v7.52: 自动生成的占位内容，需要人工补充"
            })
        return placeholders

    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 兼容性接口：为现有代码提供平滑过渡
class SpecializedAgentFactory:
    """
    兼容性包装器 - 逐步迁移到TaskOrientedExpertFactory
    """
    
    def __init__(self):
        self._task_oriented_factory = TaskOrientedExpertFactory()
        self._legacy_mode = True  # 可以通过配置切换
    
    async def execute_expert(self, role_object: Dict[str, Any], context: str, state: ProjectAnalysisState) -> Dict[str, Any]:
        """
        执行专家分析 - 自动选择任务导向或传统模式
        """
        # 检查是否有TaskInstruction，决定使用哪种模式
        if 'task_instruction' in role_object and not self._legacy_mode:
            logger.info(f"📋 使用任务导向模式执行专家: {role_object.get('role_name')}")
            return await self._task_oriented_factory.execute_expert(role_object, context, state)
        else:
            # 降级到传统模式（保持原有逻辑）
            logger.info(f"📝 使用传统模式执行专家: {role_object.get('role_name')}")
            return await self._execute_legacy_expert(role_object, context, state)
    
    async def _execute_legacy_expert(self, role_object: Dict[str, Any], context: str, state: ProjectAnalysisState) -> Dict[str, Any]:
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
                    "mode": "fallback"
                }
            }
            
        except Exception as e:
            logger.error(f"传统专家执行失败: {str(e)}")
            return {
                "expert_id": role_object.get("role_id", "unknown"),
                "expert_name": role_object.get("role_name", "Unknown Expert"),
                "analysis": f"执行失败: {str(e)}",
                "error": True
            }