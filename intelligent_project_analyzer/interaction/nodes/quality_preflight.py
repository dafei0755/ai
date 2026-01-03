"""
质量预检节点 - 任务执行前的质量预防机制

在专家执行任务前进行风险预判和质量检查清单生成
"""

from typing import Any, Dict, List, Optional

from langgraph.types import interrupt
from loguru import logger

from ...core.state import ProjectAnalysisState
from ...services.llm_factory import LLMFactory


class QualityPreflightNode:
    """质量预检节点 - 前置预防第1层"""

    def __init__(self, llm_model):
        self.llm_model = llm_model
        self.llm_factory = LLMFactory()

    async def __call__(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        """
        执行质量预检（异步版本）

        🚀 P1优化：使用 asyncio.gather() 替代 ThreadPoolExecutor，减少线程切换开销

        预防措施:
        1. 风险预判：评估每个任务的潜在风险
        2. 质量检查清单：为每个专家生成个性化清单
        3. 能力匹配度验证：检查专家配置是否充足

        流程:
        - 分析用户需求和任务分配
        - 识别高风险任务（模糊、复杂、依赖性强）
        - 生成质量检查清单
        - 如果发现严重风险 → interrupt 让用户确认
        - 否则静默通过，将清单注入到执行环境
        """
        try:
            logger.info("🔍 开始质量预检（Pre-flight Check）")

            # 🔧 v7.122: 幂等性检查 - 避免重复执行
            if state.get("quality_preflight_completed"):
                logger.info("✅ 质量预检已完成，跳过重复执行")
                return {}

            # 🔥 立即返回进度更新（避免前端等待超时）
            # 这样前端会立即知道节点正在执行
            from datetime import datetime

            initial_update = {
                "current_stage": "质量预检中",
                "detail": "正在分析任务风险和生成质量检查清单...",
                "updated_at": datetime.now().isoformat(),
            }

            # 🔧 P1修复：使用正确的状态字段
            # active_agents 包含角色ID列表
            # strategic_analysis.selected_roles 包含完整角色信息
            active_agents = state.get("active_agents", [])
            strategic_analysis = state.get("strategic_analysis", None)

            # 🔥 防御性检查：如果 strategic_analysis 为 None，说明 ProjectDirector 失败了
            if strategic_analysis is None:
                logger.error("❌ strategic_analysis 为 None，ProjectDirector 可能失败了")
                logger.error("⚠️ 无法进行质量预检，跳过此节点")
                return {}

            selected_roles = strategic_analysis.get("selected_roles", [])

            user_input = state.get("user_input", "")
            requirements_summary = state.get("requirements_summary", {})

            # 如果没有活跃代理，尝试从 selected_roles 获取
            if not active_agents and selected_roles:
                active_agents = [role.get("role_id", "") for role in selected_roles if isinstance(role, dict)]

            if not active_agents:
                logger.warning("⚠️ 没有活跃代理，跳过质量预检")
                return {}

            logger.info(f"📋 检查 {len(active_agents)} 个活跃代理")

            # 构建角色ID到完整信息的映射
            role_info_map = {}
            for role in selected_roles:
                if isinstance(role, dict):
                    role_id = role.get("role_id", "")
                    if role_id:
                        role_info_map[role_id] = role

            # 为每个专家生成质量检查
            quality_checklists = {}
            high_risk_warnings = []

            logger.info(f"🔄 开始检查 {len(active_agents)} 个角色的任务风险...")

            # 🚀 P1优化：使用 asyncio.gather() 替代 ThreadPoolExecutor
            import asyncio

            # 准备所有角色的评估参数
            evaluation_tasks = []
            for i, role_id in enumerate(active_agents, 1):
                role_info = role_info_map.get(role_id, {})
                dynamic_name = role_info.get("dynamic_role_name", role_info.get("role_name", role_id))

                # 🔧 修复: 从 task_instruction.deliverables 提取任务
                # RoleObject.model_dump() 后，tasks 作为 @property 不会被序列化
                # 需要从 task_instruction.deliverables 中提取
                tasks = []
                task_instruction = role_info.get("task_instruction", {})
                if isinstance(task_instruction, dict):
                    deliverables = task_instruction.get("deliverables", [])
                    tasks = [
                        f"【{d.get('name', '')}】{d.get('description', '')}" for d in deliverables if isinstance(d, dict)
                    ]
                # 兼容旧格式: assigned_tasks
                if not tasks:
                    tasks = role_info.get("assigned_tasks", [])

                evaluation_tasks.append(
                    {
                        "index": i,
                        "role_id": role_id,
                        "dynamic_name": dynamic_name,
                        "tasks": tasks,
                        "user_input": user_input,
                        "requirements_summary": requirements_summary,
                    }
                )

                logger.info(f"📋 [{i}/{len(active_agents)}] 准备评估角色: {role_id} ({dynamic_name})")
                logger.debug(f"   - 任务数: {len(tasks)}")

            # 🚀 P1优化：并行执行风险评估（使用 asyncio.gather）
            logger.info(f"🚀 并行执行 {len(evaluation_tasks)} 个角色的风险评估（asyncio）...")

            async def evaluate_role_async(task_params):
                """单个角色的风险评估（异步）"""
                i = task_params["index"]
                role_id = task_params["role_id"]
                dynamic_name = task_params["dynamic_name"]

                logger.info(f"🤖 [{i}/{len(active_agents)}] 调用 LLM 分析风险: {dynamic_name}...")
                checklist = await self._generate_quality_checklist_async(
                    role_id=role_id,
                    dynamic_name=dynamic_name,
                    tasks=task_params["tasks"],
                    user_input=task_params["user_input"],
                    requirements_summary=task_params["requirements_summary"],
                )
                logger.info(f"✅ [{i}/{len(active_agents)}] 角色 {dynamic_name} 风险评估完成")
                logger.info(f"   - 风险等级: {checklist.get('risk_level', 'unknown')}")
                logger.info(f"   - 风险分数: {checklist.get('risk_score', 0)}/100")

                return role_id, dynamic_name, checklist

            # 🚀 使用 asyncio.gather 并行执行所有评估任务
            coroutines = [evaluate_role_async(task_params) for task_params in evaluation_tasks]
            results = await asyncio.gather(*coroutines)

            # 收集结果
            for role_id, dynamic_name, checklist in results:
                quality_checklists[role_id] = checklist

                # 检查风险等级
                if checklist.get("risk_level", "low") == "high":
                    risk_points = checklist.get("risk_points", [])
                    high_risk_warnings.append(
                        {
                            "role_id": role_id,
                            "role_name": dynamic_name,  # 前端接口要求 role_name
                            "task_summary": ", ".join(risk_points[:2]) if risk_points else "高风险任务",  # 取前2个风险点作为摘要
                            "risk_score": checklist.get("risk_score", 0),
                            "risk_level": checklist.get("risk_level", "high"),
                            "checklist": risk_points,  # 前端接口要求 checklist
                        }
                    )

            logger.info(f"✨ 并行评估完成，共评估 {len(quality_checklists)} 个角色")

            # 🔥 v7.13: 将结果暂存，高风险警告的 interrupt 移到 try 块外
            preflight_result = {
                "quality_checklists": quality_checklists,
                "preflight_completed": True,
                "quality_preflight_completed": True,  # 🔧 v7.122: 幂等性标志
                "high_risk_count": len(high_risk_warnings),
                "high_risk_warnings": high_risk_warnings,  # 暂存供后续使用
                "current_stage": "质量预检完成",
                "detail": f"已完成 {len(active_agents)} 个角色的风险评估",
            }

        except Exception as e:
            logger.error(f"❌ 质量预检失败: {e}")
            import traceback

            traceback.print_exc()
            return {"preflight_completed": False}

        # 🔥 v7.13: 将高风险警告的 interrupt 移到 try 块外，避免被 except 捕获
        # interrupt() 在 LangGraph 中会暂停工作流，不应被当作异常处理
        high_risk_warnings = preflight_result.get("high_risk_warnings", [])
        if high_risk_warnings:
            logger.warning(f"⚠️ 发现 {len(high_risk_warnings)} 个高风险任务，等待用户确认")
            self._show_risk_warnings(high_risk_warnings)
        else:
            logger.info("✅ 所有任务风险可控")

        # 返回结果（移除暂存的 high_risk_warnings）
        preflight_result.pop("high_risk_warnings", None)
        return preflight_result

    async def _generate_quality_checklist_async(
        self, role_id: str, dynamic_name: str, tasks: List[str], user_input: str, requirements_summary: Dict
    ) -> Dict[str, Any]:
        """
        为单个专家生成质量检查清单（异步版本）

        🚀 P1优化：使用异步LLM调用，减少线程切换开销

        返回:
        {
            "role_id": "V3_叙事与体验专家_3-1",
            "dynamic_name": "田园生活方式顾问",
            "risk_score": 65,  # 0-100
            "risk_level": "medium",  # low/medium/high
            "risk_points": ["用户画像缺乏数据支撑", "场景可能过于理想化"],
            "quality_checklist": [
                "提供至少3个真实用户案例或调研数据",
                "场景描述需要与需求明确映射",
                "避免主观臆断，标注信息来源"
            ],
            "capability_check": {
                "has_search_tool": false,
                "has_knowledge_base": true,
                "prompt_clarity": "medium"
            },
            "mitigation_suggestions": [
                "建议配置Tavily搜索工具以获取真实案例",
                "增强prompt中的'数据驱动'约束"
            ]
        }
        """
        try:
            # 构建分析prompt
            prompt = f"""你是一个质量控制专家，负责在任务执行前进行风险预判。

**角色信息**:
- 角色ID: {role_id}
- 动态名称: {dynamic_name}

**分配的任务**:
{chr(10).join(f"{i+1}. {task}" for i, task in enumerate(tasks))}

**用户需求**:
{user_input}

**需求摘要**:
{requirements_summary}

请分析这个专家任务的潜在风险，并生成质量检查清单。

输出JSON格式:
{{
    "risk_assessment": {{
        "requirement_clarity": 75,  // 需求清晰度 0-100，越高越清晰
        "task_complexity": 60,      // 任务复杂度 0-100，越高越复杂
        "data_dependency": 50,      // 数据依赖度 0-100，越高越依赖外部数据
        "overall_risk_score": 62    // 综合风险 0-100，越高风险越大
    }},
    "risk_points": [
        "具体的风险点1",
        "具体的风险点2"
    ],
    "quality_checklist": [
        "必须检查的质量项1",
        "必须检查的质量项2",
        "必须检查的质量项3"
    ],
    "capability_gaps": [
        "缺少的能力或工具"
    ],
    "mitigation_suggestions": [
        "降低风险的建议"
    ]
}}

注意:
1. 风险评分要客观，不要都打高分
2. 质量检查清单要具体可操作，不要泛泛而谈
3. 重点关注：需求模糊、数据缺失、主观臆断、工具不足
"""

            # 🚀 P1优化：使用异步LLM调用，增加重试机制
            import asyncio

            max_retries = 2
            last_error = None

            for attempt in range(max_retries + 1):
                try:
                    llm = self.llm_factory.create_llm(temperature=0.3)
                    response = await llm.ainvoke(prompt)
                    break  # 成功则跳出循环
                except Exception as e:
                    last_error = e
                    if attempt < max_retries:
                        wait_time = (attempt + 1) * 2  # 2秒, 4秒
                        logger.warning(f"⚠️ LLM调用失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}, {wait_time}秒后重试...")
                        await asyncio.sleep(wait_time)
                    else:
                        raise last_error

            # 解析响应
            import json
            import re

            content = response.content if hasattr(response, "content") else str(response)

            # 提取JSON
            json_match = re.search(r"\{[\s\S]*\}", content)
            if json_match:
                json_str = json_match.group()

                # 清理JSON：移除注释、修复常见格式问题
                # 1. 移除单行注释 //...
                json_str = re.sub(r"//.*?(?=\n|$)", "", json_str)
                # 2. 移除多行注释 /* ... */
                json_str = re.sub(r"/\*.*?\*/", "", json_str, flags=re.DOTALL)
                # 3. 修复缺少引号的键名（简单处理）
                json_str = re.sub(r"([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:", r'\1"\2":', json_str)

                try:
                    result = json.loads(json_str)
                except json.JSONDecodeError as e:
                    logger.warning(f"⚠️ JSON解析失败（尝试修复后仍失败）: {e}")
                    logger.debug(f"原始LLM输出: {content[:500]}...")
                    # 降级到默认值
                    result = None
            else:
                result = None

            # 统一处理默认值
            if result is None:
                # 默认值
                result = {
                    "risk_assessment": {
                        "requirement_clarity": 70,
                        "task_complexity": 50,
                        "data_dependency": 50,
                        "overall_risk_score": 57,
                    },
                    "risk_points": ["需要人工审核"],
                    "quality_checklist": ["确保输出完整", "提供数据支撑"],
                    "capability_gaps": [],
                    "mitigation_suggestions": [],
                }

            # 构建完整的质量检查清单
            risk_score = result["risk_assessment"]["overall_risk_score"]
            risk_level = "low" if risk_score < 50 else ("medium" if risk_score < 70 else "high")

            checklist = {
                "role_id": role_id,
                "dynamic_name": dynamic_name,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "risk_points": result.get("risk_points", []),
                "quality_checklist": result.get("quality_checklist", []),
                "capability_gaps": result.get("capability_gaps", []),
                "mitigation_suggestions": result.get("mitigation_suggestions", []),
                "risk_breakdown": result["risk_assessment"],
            }

            logger.info(f"  {dynamic_name}: 风险={risk_level}({risk_score}), 清单={len(checklist['quality_checklist'])}项")

            return checklist

        except Exception as e:
            logger.error(f"❌ 生成质量检查清单失败: {e}")
            # 返回默认的中等风险清单
            return {
                "role_id": role_id,
                "dynamic_name": dynamic_name,
                "risk_score": 50,
                "risk_level": "medium",
                "risk_points": ["分析失败，需要人工审核"],
                "quality_checklist": ["确保输出完整", "提供充分论证"],
                "capability_gaps": [],
                "mitigation_suggestions": [],
            }

    def _show_risk_warnings(self, high_risk_warnings: List[Dict]) -> None:
        """
        向用户展示高风险警告

        使用interrupt机制让用户了解风险并确认是否继续
        """
        warning_data = {
            "interaction_type": "quality_preflight_warning",
            "title": "⚠️ 质量预检发现高风险任务",
            "message": f"在任务执行前发现 {len(high_risk_warnings)} 个高风险任务，建议关注：",
            "warnings": high_risk_warnings,
            "options": [
                {"value": "continue", "label": "继续执行（已知悉风险）"},
                {"value": "adjust", "label": "调整任务分配"},
                {"value": "cancel", "label": "取消分析"},
            ],
        }

        logger.warning(f"⚠️ 向用户展示 {len(high_risk_warnings)} 个高风险警告")

        # 使用interrupt暂停工作流
        response = interrupt(warning_data)

        # 处理用户响应
        if response and response.get("choice") == "cancel":
            raise Exception("用户取消了分析流程")
        elif response and response.get("choice") == "adjust":
            logger.info("用户选择调整任务，需要返回任务分配阶段")
            # 这里可以设置状态标记，让workflow路由回task_assignment
        else:
            logger.info("用户确认继续执行")


# 创建节点实例的工厂函数
def create_quality_preflight_node(llm_model):
    """创建质量预检节点"""
    return QualityPreflightNode(llm_model)
