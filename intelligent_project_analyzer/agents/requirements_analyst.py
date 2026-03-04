# HISTORICAL — superseded by RequirementsAnalystAgentV2 in requirements_analyst_agent.py
# 本文件中的 RequirementsAnalystAgent 是旧实现，已被工作流主路径弃用。
# 当前主工作流路径（requirements_nodes.py）只调用 RequirementsAnalystAgentV2。
# 保留原因：agents/__init__.py 懒加载兼容，避免外部导入立即崩溃。
# 计划删除时间：2026-04-04（兼容窗口结束）。
# 删除条件：确认无外部调用方依赖此类后执行 arch/delete-ra-v1-legacy。
"""
需求分析师智能体

负责理解和结构化用户需求，为后续分析提供基础
"""

import json
import time
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore
from loguru import logger

from ._analyst_parse_mixin import AnalystParseMixin
from ._analyst_phase_mixin import AnalystPhaseMixin
from ._analyst_fix_mixin import AnalystFixMixin
from ..core.prompt_manager import PromptManager
from ..core.state import AgentType, ProjectAnalysisState
from ..core.types import AnalysisResult

#  v7.270: Import new enhancement modules
from ..services.entity_extractor import EntityExtractor
from ..services.l2_perspective_activator import L2PerspectiveActivator
from ..services.motivation_engine import MotivationInferenceEngine
from ..services.requirements_validator import RequirementsValidator
from ..services.ucppt_search_engine import ProblemSolvingApproach
from ..utils.capability_detector import check_capability
from ..utils.jtbd_parser import transform_jtbd_to_natural_language
from .base import LLMAgent


class RequirementsAnalystAgent(AnalystParseMixin, AnalystPhaseMixin, AnalystFixMixin, LLMAgent):
    """需求分析师智能体"""
    
    def __init__(self, llm_model, config: Dict[str, Any] | None = None):
        super().__init__(
            agent_type=AgentType.REQUIREMENTS_ANALYST,
            name="需求分析师",
            description="理解和结构化用户项目需求，识别关键要素和约束条件",
            llm_model=llm_model,
            config=config
        )

        # 初始化提示词管理器
        self.prompt_manager = PromptManager()

        #  v7.270: Initialize enhancement modules
        self.entity_extractor = EntityExtractor(llm_model=llm_model)
        self.requirements_validator = RequirementsValidator()
        self.l2_activator = L2PerspectiveActivator()
        self.motivation_engine = MotivationInferenceEngine()
    
    def validate_input(self, state: ProjectAnalysisState) -> bool:
        """验证输入是否有效"""
        user_input = state.get("user_input", "").strip()
        return len(user_input) > 10  # 至少10个字符
    
    def get_system_prompt(self) -> str:
        """获取系统提示词 - 从外部配置加载 v3.4 (优化版本)"""
        #  v3.4优化: 优先加载精简版配置，提升3-5倍响应速度
        # 尝试加载精简版 (requirements_analyst_lite.yaml)
        prompt_config = self.prompt_manager.get_prompt("requirements_analyst_lite", return_full_config=True)
        
        # 如果精简版不存在，回退到完整版
        if not prompt_config:
            logger.info("[INFO] 精简版配置未找到，加载完整版 requirements_analyst.yaml")
            prompt_config = self.prompt_manager.get_prompt("requirements_analyst", return_full_config=True)

        # 如果配置不存在，抛出错误（不再使用硬编码 fallback）
        if not prompt_config:
            raise ValueError(
                " 未找到提示词配置: requirements_analyst 或 requirements_analyst_lite\n"
                "请确保配置文件存在: config/prompts/requirements_analyst_lite.yaml\n"
                "系统无法使用硬编码提示词，请检查配置文件。"
            )

        # 获取系统提示词
        system_prompt = prompt_config.get("system_prompt", "")

        if not system_prompt:
            raise ValueError(
                " 配置文件中缺少 system_prompt 字段\n"
                "请确保配置文件包含完整的 system_prompt 字段。"
            )
        
        #  v3.4优化日志
        prompt_length = len(system_prompt)
        estimated_tokens = prompt_length // 4
        logger.info(f"[v3.4 优化] 已加载提示词: {prompt_length} 字符, 约 {estimated_tokens} tokens")

        return system_prompt

    def get_task_description(self, state: ProjectAnalysisState) -> str:
        """获取具体任务描述 - v3.4版本（优先使用精简版配置）"""
        user_input = state.get("user_input", "")

        #  v3.4优化: 优先使用精简版配置
        # 使用 PromptManager 的新方法获取任务描述
        task_description = self.prompt_manager.get_task_description(
            agent_name="requirements_analyst_lite",
            user_input=user_input,
            include_datetime=True
        )
        
        # 如果精简版不存在，回退到完整版
        if not task_description:
            logger.info("[INFO] 精简版任务描述未找到，使用完整版")
            task_description = self.prompt_manager.get_task_description(
                agent_name="requirements_analyst",
                user_input=user_input,
                include_datetime=True
            )

        # 如果配置不存在，抛出错误
        if not task_description:
            raise ValueError(
                " 配置文件中缺少 task_description_template 字段\n"
                "请确保配置文件包含完整的 task_description_template 字段。"
            )

        return task_description
    
    def execute(
        self,
        state: ProjectAnalysisState,
        config: RunnableConfig,
        store: BaseStore | None = None,
        use_two_phase: bool = False  #  v7.17: 支持两阶段模式
    ) -> AnalysisResult:
        """执行需求分析
        
        Args:
            state: 项目分析状态
            config: 运行配置
            store: 可选的存储后端
            use_two_phase: 是否使用两阶段模式（v7.17新增）
                - False: 单次LLM调用（默认，向后兼容）
                - True: Phase1（快速定性）→ Phase2（深度分析）
        """
        #  v7.17: 如果启用两阶段模式，使用新的执行流程
        #  v7.502 P0优化: _execute_two_phase现在是async，需要使用asyncio.run运行
        #  v7.601: 修复 asyncio 嵌套风险
        if use_two_phase:
            import asyncio
            
            async def _run_two_phase():
                return await self._execute_two_phase(state, config, store)
            
            # 检查是否已有运行中的event loop
            try:
                loop = asyncio.get_running_loop()
                # 已有loop: 使用 nest_asyncio 或降级到线程执行
                try:
                    import nest_asyncio
                    nest_asyncio.apply()
                    return loop.run_until_complete(_run_two_phase())
                except ImportError:
                    # nest_asyncio 不可用时，在新线程中执行
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, _run_two_phase())
                        return future.result(timeout=120)
            except RuntimeError:
                # 没有运行中的loop，安全使用 asyncio.run
                return asyncio.run(_run_two_phase())
        # 原有的单次调用逻辑
        start_time = time.time()
        
        try:
            logger.info(f"Starting requirements analysis for session {state.get('session_id')}")
            
            # 验证输入
            if not self.validate_input(state):
                raise ValueError("Invalid input: user input is too short or empty")
            
            # 检索用户历史偏好（如果有store）
            user_context = ""
            if store and config.get("configurable", {}).get("user_id"):
                user_context = self._retrieve_user_preferences(store, config)
            
            # 准备消息
            messages = self.prepare_messages(state)
            
            # 添加用户偏好上下文
            if user_context:
                messages.append(HumanMessage(content=f"用户历史偏好：\n{user_context}"))
            
            # 调用LLM
            response = self.invoke_llm(messages)
            
            # 解析结构化结果
            structured_requirements = self._parse_requirements(response.content)

            #  v7.3: 问卷生成已分离到专门节点，此处不再处理问卷
            # 原因：只有充分分析才能指导问卷的生成
            # 新架构：需求分析（专注分析）→ calibration_questionnaire节点（动态生成问卷）

            # 向后兼容：如果LLM仍然返回了calibration_questionnaire字段（旧模型或缓存），保留但标记为待替换
            if "calibration_questionnaire" in structured_requirements:
                logger.info("ℹ️ 检测到LLM返回了calibration_questionnaire（旧行为），将保留但由专门节点重新生成")
                structured_requirements["calibration_questionnaire"]["source"] = "llm_legacy"
                structured_requirements["calibration_questionnaire"]["note"] = "此问卷将被专门节点重新生成"
            
            # 保存用户偏好（如果有新的偏好信息）
            if store and config.get("configurable", {}).get("user_id"):
                self._save_user_preferences(store, config, structured_requirements)
            
            # 创建分析结果
            result = self.create_analysis_result(
                content=response.content,
                structured_data=structured_requirements,
                confidence=self._calculate_confidence(structured_requirements),
                sources=["user_input", "llm_analysis"]
            )
            
            end_time = time.time()
            self._track_execution_time(start_time, end_time)
            
            logger.info("Requirements analysis completed successfully")
            return result
            
        except Exception as e:
            error = self.handle_error(e, "requirements analysis")
            raise error
    
    def _generate_problem_solving_approach(
        self,
        user_input: str,
        phase2_result: Dict[str, Any]
    ) -> ProblemSolvingApproach | None:
        """
        Generate problem-solving approach based on Phase 2 analysis

        Args:
            user_input: Original user input
            phase2_result: Phase 2 analysis result

        Returns:
            ProblemSolvingApproach instance or None if generation fails
        """
        try:
            # Extract key info from Phase 2
            analysis_layers = phase2_result.get("analysis_layers", {})
            l4_jtbd = analysis_layers.get("L4_project_task", "")
            l3_tension = analysis_layers.get("L3_core_tension", "")
            l5_sharpness = analysis_layers.get("L5_sharpness", {})
            l5_score = l5_sharpness.get("score", 0) if isinstance(l5_sharpness, dict) else 0

            # Build prompt
            prompt = f"""
基于深度分析结果，生成战术级解题思路（Problem-Solving Approach）。

**用户需求**: {user_input}

**分析摘要**:
- L4 JTBD: {l4_jtbd}
- L3 核心张力: {l3_tension}
- L5 锐度得分: {l5_score}

---

请生成解题思路，包含：

**1. 任务本质识别**
- task_type: research/design/decision/exploration/verification
- task_type_description: 详细描述任务类型
- complexity_level: simple/moderate/complex/highly_complex
- required_expertise: 所需专业知识领域（3-5个）

**2. 解题路径规划（5-8个详细步骤）**
每步包含：
- step_id: "S1", "S2", ...
- action: 具体行动（可执行级别）
- purpose: 目的
- expected_output: 预期输出

**3. 关键突破口（1-3个）**
每个包含：
- point: 突破点描述
- why_key: 为什么关键
- how_to_leverage: 如何利用

**4. 预期产出形态**
- format: report/list/comparison/recommendation/plan
- sections: 必须包含的章节（5-8个）
- key_elements: 关键交付物
- quality_criteria: 质量标准

**5. 备选路径（2-3个）**

**输出格式**（纯JSON）:
{{
  "task_type": "design",
  "task_type_description": "...",
  "complexity_level": "complex",
  "required_expertise": ["领域1", "领域2", "领域3"],
  "solution_steps": [
    {{
      "step_id": "S1",
      "action": "...",
      "purpose": "...",
      "expected_output": "..."
    }}
  ],
  "breakthrough_points": [
    {{
      "point": "...",
      "why_key": "...",
      "how_to_leverage": "..."
    }}
  ],
  "expected_deliverable": {{
    "format": "report",
    "sections": ["章节1", "章节2"],
    "key_elements": ["元素1", "元素2"],
    "quality_criteria": ["标准1", "标准2"]
  }},
  "alternative_approaches": ["方法1", "方法2"],
  "confidence_score": 0.85
}}
"""

            response = self.invoke_llm([{"role": "user", "content": prompt}])
            approach_data = self._parse_phase_response(response.content)

            # Create ProblemSolvingApproach instance
            problem_solving_approach = ProblemSolvingApproach(
                task_type=approach_data.get("task_type", "design"),
                task_type_description=approach_data.get("task_type_description", ""),
                complexity_level=approach_data.get("complexity_level", "complex"),
                required_expertise=approach_data.get("required_expertise", []),
                solution_steps=approach_data.get("solution_steps", []),
                breakthrough_points=approach_data.get("breakthrough_points", []),
                expected_deliverable=approach_data.get("expected_deliverable", {}),
                original_requirement=user_input,
                refined_requirement=l4_jtbd,
                confidence_score=approach_data.get("confidence_score", 0.8),
                alternative_approaches=approach_data.get("alternative_approaches", [])
            )

            return problem_solving_approach

        except Exception as e:
            logger.error(f" [v7.270] Failed to generate problem-solving approach: {e}")
            return None


# 注册智能体
from .base import AgentFactory

AgentFactory.register_agent(AgentType.REQUIREMENTS_ANALYST, RequirementsAnalystAgent)
