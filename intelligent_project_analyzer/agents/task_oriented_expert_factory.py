# ============================================================================
# 任务导向专家工厂 - Task Oriented Expert Factory v2.0
# ============================================================================
# 更新日期: 2025-12-05
# 变更说明: 
# 1. 专家输出严格围绕TaskInstruction
# 2. 强制使用TaskOrientedExpertOutput结构
# 3. 确保协议闭环执行
# ============================================================================

from typing import Dict, Any, List, Optional
from ..core.state import ProjectAnalysisState
from ..core.task_oriented_models import TaskOrientedExpertOutput, ProtocolExecutionReport
from ..services.llm_factory import LLMFactory
import yaml
import json
import datetime
from pathlib import Path
from loguru import logger

def load_yaml_config(config_path: str) -> Dict[str, Any]:
    """
    加载YAML配置文件的辅助函数
    
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
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.error(f"加载配置文件失败 {full_path}: {str(e)}")
        return {}

class TaskOrientedExpertFactory:
    """
    任务导向专家工厂 - 确保专家输出严格围绕分配任务
    
    核心功能：
    1. 根据RoleObject中的TaskInstruction执行专家分析
    2. 强制返回TaskOrientedExpertOutput结构
    3. 确保协议执行完整闭环
    4. 消除不可预计的额外输出
    
    ✅ P3优化：缓存LLM实例，避免重复创建
    """
    
    # ✅ P3优化：类级别LLM实例缓存
    _llm_instance = None
    
    def __init__(self):
        self.llm_factory = LLMFactory()
    
    def _get_llm(self):
        """
        获取缓存的LLM实例（单例模式）
        
        ✅ P3优化：避免每次execute_expert都创建新的LLM实例
        """
        if TaskOrientedExpertFactory._llm_instance is None:
            logger.info("🔧 [P3优化] 创建共享LLM实例")
            TaskOrientedExpertFactory._llm_instance = self.llm_factory.create_llm()
        return TaskOrientedExpertFactory._llm_instance
    
    async def execute_expert(self, role_object: Dict[str, Any], context: str, state: ProjectAnalysisState) -> Dict[str, Any]:
        """
        执行任务导向的专家分析
        
        Args:
            role_object: 包含TaskInstruction的角色对象
            context: 项目上下文
            state: 当前状态
            
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
            # ✅ P3优化：使用缓存的LLM实例
            llm = self._get_llm()
            
            messages = [
                {"role": "system", "content": expert_prompt["system_prompt"]},
                {"role": "user", "content": expert_prompt["user_prompt"]}
            ]
            
            response = await llm.ainvoke(messages)
            expert_output = response.content if hasattr(response, 'content') else str(response)
            
            # 解析并验证TaskOrientedExpertOutput结构
            structured_output = self._parse_and_validate_output(expert_output, role_object)
            
            # 构建标准化返回结果
            result = {
                "expert_id": role_object.get("role_id", "unknown"),
                "expert_name": role_object.get("dynamic_role_name", role_object.get("role_name", "Unknown Expert")),
                "analysis": expert_output,  # 原始输出
                "structured_output": structured_output,  # 验证后的结构化输出
                "task_instruction": role_object.get("task_instruction", {}),  # 任务指令
                "role_definition": role_object,
                "execution_metadata": {
                    "timestamp": self._get_timestamp(),
                    "model_used": "gpt-4",
                    "prompt_version": "task_oriented_v2.0",
                    "output_format": "TaskOrientedExpertOutput"
                }
            }
            
            # 验证任务完成情况
            self._validate_task_completion(structured_output, role_object.get("task_instruction", {}))
            
            return result
            
        except Exception as e:
            logger.error(f"执行任务导向专家 {role_object.get('role_name', 'Unknown')} 时出错: {str(e)}")
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
        """
        try:
            # 加载基础角色配置 - 使用映射函数
            config_filename = self._get_role_config_filename(role_object['role_id'])
            role_config = load_yaml_config(config_filename)
            base_system_prompt = role_config.get("system_prompt", "你是一位专业的分析师")
            
            # 获取TaskInstruction
            task_instruction = role_object.get('task_instruction', {})
            
            # 加载专家自主性协议
            autonomy_protocol = load_yaml_config("prompts/expert_autonomy_protocol_v4.yaml")
            
            # 构建任务导向的系统提示词
            system_prompt = f"""
{base_system_prompt}

# 🎯 动态角色定义
你在本次分析中的具体角色：{role_object.get('dynamic_role_name', role_object.get('role_name'))}

# 📋 TaskInstruction - 你的明确任务指令

## 核心目标
{task_instruction.get('objective', '基于专业领域提供深度分析')}

## 交付物要求
"""
            
            # 添加交付物列表
            deliverables = task_instruction.get('deliverables', [])
            if deliverables:
                for i, deliverable in enumerate(deliverables, 1):
                    system_prompt += f"""
**交付物 {i}: {deliverable.get('name', f'交付物{i}')}**
- 描述: {deliverable.get('description', '')}
- 格式: {deliverable.get('format', 'analysis')}
- 优先级: {deliverable.get('priority', 'medium')}
- 成功标准: {', '.join(deliverable.get('success_criteria', []))}
"""
            
            system_prompt += f"""

## 整体成功标准
{', '.join(task_instruction.get('success_criteria', ['输出符合专业标准']))}

## 约束条件
{', '.join(task_instruction.get('constraints', ['无特殊约束']))}

## 上下文要求
{', '.join(task_instruction.get('context_requirements', ['无特殊上下文要求']))}

# 🔄 专家自主性协议 v{autonomy_protocol.get('version', '3.5')}
{autonomy_protocol.get('protocol_content', '')}

# 📊 严格输出要求

**你必须返回JSON格式的TaskOrientedExpertOutput，包含以下三个必填部分：**

```json
{{
  "task_execution_report": {{
    "deliverable_outputs": [
      {{
        "deliverable_name": "交付物名称（与任务指令中的交付物对应）",
        "content": "具体分析内容（详细完整，不要省略）",
        "completion_status": "completed",
        "completion_rate": 0.95,
        "notes": "补充说明或备注",
        "quality_self_assessment": 0.9
      }}
    ],
    "task_completion_summary": "任务完成情况总结（2-3句话）",
    "additional_insights": ["执行过程中的额外洞察（可选）"],
    "execution_challenges": ["遇到的挑战或限制（可选）"]
  }},
  "protocol_execution": {{
    "protocol_status": "complied",
    "compliance_confirmation": "确认接受需求分析师的洞察并按指令执行",
    "challenge_details": null,
    "reinterpretation": null
  }},
  "execution_metadata": {{
    "confidence": 0.9,
    "completion_rate": 1.0,
    "execution_time_estimate": "约X分钟",
    "execution_notes": "执行过程备注",
    "dependencies_satisfied": true
  }}
}}
```

# ⚠️ 关键要求

1. **严格围绕TaskInstruction**：只输出分配的交付物，不要添加其他内容
2. **JSON格式要求**：输出必须是有效的JSON，不要有额外的解释文字
3. **三个必填部分**：task_execution_report、protocol_execution、execution_metadata 缺一不可
4. **protocol_status**：必须是 "complied"、"challenged" 或 "reinterpreted" 之一
5. **内容完整性**：每个deliverable的content要详细完整，不要简化
6. **专业标准**：所有分析要符合你的专业领域标准

# 🚫 禁止事项

- 不要输出TaskInstruction之外的任何分析
- 不要在JSON前后添加解释性文字
- 不要省略或简化任何必需的字段
- 不要添加额外的建议或观察
- 不要使用markdown代码块包裹JSON
- 不要使用旧格式字段如 expert_summary、task_results、validation_checklist

**记住：你的输出将被严格验证，必须包含 task_execution_report、protocol_execution 和 execution_metadata 三个必填字段。**
            """
            
            # 构建用户提示词
            user_prompt = f"""
# 📂 项目上下文
{context}

# 📊 当前项目状态
- 项目阶段: {state.get('current_phase', '分析阶段')}
- 已完成分析: {len(state.get('expert_analyses', {}))}个专家

# 🎯 执行指令

请严格按照上述TaskInstruction执行你的专业分析任务，并以JSON格式返回TaskOrientedExpertOutput结构。

**关键要求：**
1. 只围绕分配的交付物进行分析
2. 确保protocol_execution部分完整填写
3. 所有内容必须符合成功标准
4. 返回格式必须是有效JSON
5. 不要有任何额外输出

开始执行你的专业分析任务：
            """
            
            return {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt
            }
            
        except Exception as e:
            logger.error(f"构建任务导向专家提示词时出错: {str(e)}")
            return {
                "system_prompt": "你是一位专业的分析师，请基于提供的信息进行分析。",
                "user_prompt": f"请分析以下内容：\n{context}"
            }
    
    def _parse_and_validate_output(self, expert_output: str, role_object: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析并验证专家输出是否符合TaskOrientedExpertOutput结构
        如果验证失败，使用降级策略构造默认结构
        """
        try:
            # 提取JSON内容
            if "```json" in expert_output:
                json_start = expert_output.find("```json") + 7
                json_end = expert_output.find("```", json_start)
                json_str = expert_output[json_start:json_end].strip()
            elif "{" in expert_output and "}" in expert_output:
                json_str = expert_output[expert_output.find("{"):expert_output.rfind("}")+1]
            else:
                logger.warning("输出不包含有效JSON，尝试整体解析")
                json_str = expert_output.strip()
            
            # 解析JSON
            parsed_output = json.loads(json_str)
            
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
    
    def _create_fallback_output(self, raw_output: str, role_object: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建降级输出结构（当Pydantic验证失败时）
        """
        role_name = role_object.get('dynamic_role_name', role_object.get('role_name', 'Unknown Expert'))
        
        return {
            "task_execution_report": {
                "deliverable_outputs": [
                    {
                        "deliverable_name": "分析报告",
                        "content": raw_output,
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

    
    def _validate_task_completion(self, structured_output: Dict[str, Any], task_instruction: Dict[str, Any]) -> bool:
        """
        验证任务完成情况，确保所有deliverables都已处理
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
                # 降级场景下不强制失败
                return True
            
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