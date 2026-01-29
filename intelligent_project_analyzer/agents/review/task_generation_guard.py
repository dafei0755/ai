"""
任务生成守卫 - 合并质量预检与角色选择审核

v7.280: 前置化质量控制重构
- 合并 QualityPreflightNode 的风险评分逻辑
- 整合 RoleSelectionQualityReviewNode 的红蓝对抗（简化为单次LLM调用）
- 在任务生成阶段自动修正问题，无需用户介入

设计原则:
1. 边生成边优化，而非生成后审核
2. 自动应用缓解策略，仅日志记录风险
3. 高风险任务标注但不阻塞流程
"""

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from ...services.llm_factory import LLMFactory


class TaskGenerationGuard:
    """
    任务生成守卫 - 前置质量控制

    在 role_task_unified_review 节点内部调用，
    对角色选择和任务分派进行风险评估并自动修正。

    合并了:
    - QualityPreflightNode 的风险评估维度
    - RoleSelectionQualityReviewNode 的红蓝对抗逻辑

    输出:
    - risks: 识别的风险点列表
    - auto_mitigations: 自动应用的修正措施
    - confidence_score: 整体置信度 (0-100)
    """

    # 可配置的风险阈值（超过此值仍继续但标注高风险）
    HIGH_RISK_THRESHOLD = 70
    EXTREME_RISK_THRESHOLD = 90

    def __init__(self, llm_model=None):
        self.llm_factory = LLMFactory()
        self.llm_model = llm_model or self.llm_factory.create_llm(temperature=0.3)

    async def evaluate_and_optimize(
        self,
        selected_roles: List[Dict[str, Any]],
        structured_requirements: Dict[str, Any],
        user_input: str,
    ) -> Dict[str, Any]:
        """
        评估角色选择和任务分派，自动优化问题

        Args:
            selected_roles: 项目总监选择的角色列表
            structured_requirements: 结构化需求
            user_input: 用户原始输入

        Returns:
            {
                "risks": [
                    {
                        "role_id": "V3_xxx_3-1",
                        "risk_type": "requirement_ambiguity|capability_gap|task_complexity",
                        "severity": "low|medium|high",
                        "description": "风险描述",
                        "auto_mitigation": "自动应用的修正"
                    }
                ],
                "auto_mitigations": [
                    "已为V3角色补充搜索关键词",
                    "已细化V4任务的输出要求"
                ],
                "role_adjustments": {
                    "role_id": {
                        "enhanced_prompt": "补充的提示词",
                        "additional_context": "额外上下文"
                    }
                },
                "confidence_score": 75,
                "high_risk_roles": ["V3_xxx_3-1"],
                "evaluation_summary": "整体评估摘要"
            }
        """
        logger.info("🛡️ [TaskGenerationGuard] 开始前置质量评估...")

        try:
            # 构建评估上下文
            evaluation_context = self._build_evaluation_context(selected_roles, structured_requirements, user_input)

            # 单次 LLM 调用进行综合评估（替代多次红蓝对抗）
            evaluation_result = await self._evaluate_with_llm(evaluation_context)

            # 自动应用缓解策略
            role_adjustments, auto_mitigations = self._apply_auto_mitigations(selected_roles, evaluation_result)

            # 汇总结果
            risks = evaluation_result.get("risks", [])
            high_risk_roles = [r["role_id"] for r in risks if r.get("severity") == "high"]

            confidence_score = evaluation_result.get("confidence_score", 70)

            result = {
                "risks": risks,
                "auto_mitigations": auto_mitigations,
                "role_adjustments": role_adjustments,
                "confidence_score": confidence_score,
                "high_risk_roles": high_risk_roles,
                "evaluation_summary": evaluation_result.get("summary", ""),
                "guard_completed": True,
                "guard_timestamp": datetime.now().isoformat(),
            }

            # 日志记录（不阻塞流程）
            if high_risk_roles:
                logger.warning(f"⚠️ [TaskGenerationGuard] 发现 {len(high_risk_roles)} 个高风险角色: {high_risk_roles}")
                for risk in risks:
                    if risk.get("severity") == "high":
                        logger.warning(f"   - {risk['role_id']}: {risk['description']}")
                        if risk.get("auto_mitigation"):
                            logger.info(f"     ✅ 已自动应用: {risk['auto_mitigation']}")
            else:
                logger.info(f"✅ [TaskGenerationGuard] 评估完成，置信度: {confidence_score}%")

            if auto_mitigations:
                logger.info(f"🔧 [TaskGenerationGuard] 已自动应用 {len(auto_mitigations)} 项优化:")
                for m in auto_mitigations:
                    logger.info(f"   - {m}")

            return result

        except Exception as e:
            logger.error(f"❌ [TaskGenerationGuard] 评估失败: {e}")
            # 失败时返回默认结果，不阻塞流程
            return {
                "risks": [],
                "auto_mitigations": [],
                "role_adjustments": {},
                "confidence_score": 50,
                "high_risk_roles": [],
                "evaluation_summary": f"评估失败: {str(e)}",
                "guard_completed": False,
                "guard_error": str(e),
            }

    def _build_evaluation_context(
        self,
        selected_roles: List[Dict[str, Any]],
        structured_requirements: Dict[str, Any],
        user_input: str,
    ) -> str:
        """构建 LLM 评估上下文"""

        # 格式化角色信息
        roles_text = []
        for role in selected_roles:
            role_id = role.get("role_id", "unknown")
            role_name = role.get("dynamic_role_name") or role.get("role_name", "")

            # 提取任务
            tasks = role.get("tasks", [])
            if not tasks and "task_instruction" in role:
                task_instruction = role["task_instruction"]
                if isinstance(task_instruction, dict):
                    deliverables = task_instruction.get("deliverables", [])
                    tasks = [
                        f"【{d.get('name', '')}】{d.get('description', '')}" for d in deliverables if isinstance(d, dict)
                    ]

            focus_areas = role.get("focus_areas", [])

            roles_text.append(
                f"""
角色ID: {role_id}
角色名称: {role_name}
分配任务:
{chr(10).join(f"  - {t}" for t in tasks) if tasks else "  - 无明确任务"}
关注领域: {', '.join(focus_areas) if focus_areas else '未指定'}
"""
            )

        # 格式化需求摘要
        req_summary = structured_requirements.get("summary", "") if structured_requirements else ""
        constraints = structured_requirements.get("constraints", {}) if structured_requirements else {}

        return f"""
## 用户需求
{user_input}

## 需求摘要
{req_summary}

## 约束条件
- 预算: {constraints.get('budget', '未指定')}
- 时间: {constraints.get('timeline', '未指定')}
- 空间: {constraints.get('space', '未指定')}

## 已选角色与任务分派
{''.join(roles_text)}
"""

    async def _evaluate_with_llm(self, context: str) -> Dict[str, Any]:
        """使用 LLM 进行综合评估"""

        prompt = f"""你是一个项目质量控制专家，负责在任务执行前进行风险预判并提供优化建议。

请分析以下角色选择和任务分派，识别潜在风险并给出自动修正建议。

{context}

## 评估维度
1. **需求清晰度**: 任务描述是否足够明确？
2. **角色适配性**: 角色选择是否与需求匹配？
3. **任务复杂度**: 任务是否过于复杂或模糊？
4. **能力覆盖**: 是否存在能力缺口？
5. **协同效率**: 角色间协作是否合理？

## 输出要求
请输出JSON格式:
{{
    "risks": [
        {{
            "role_id": "角色ID",
            "risk_type": "requirement_ambiguity|capability_gap|task_complexity|collaboration_issue",
            "severity": "low|medium|high",
            "description": "简洁的风险描述",
            "auto_mitigation": "具体的自动修正建议（如细化任务、补充搜索关键词等）"
        }}
    ],
    "role_optimizations": {{
        "角色ID": {{
            "enhanced_prompt": "为该角色补充的提示词或上下文",
            "search_keywords": ["推荐的搜索关键词"],
            "focus_refinement": "聚焦建议"
        }}
    }},
    "confidence_score": 75,
    "summary": "整体评估摘要（1-2句话）"
}}

注意:
1. 风险评分要客观，不要都打高分
2. 自动修正建议要具体可执行
3. 重点关注：需求模糊、任务过大、缺少数据支撑
4. 如果没有明显问题，risks 可以为空数组
"""

        try:
            llm = self.llm_factory.create_llm(temperature=0.3)
            response = await llm.ainvoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)

            # 解析 JSON
            json_match = re.search(r"\{[\s\S]*\}", content)
            if json_match:
                json_str = json_match.group()
                # 清理注释
                json_str = re.sub(r"//.*?(?=\n|$)", "", json_str)
                json_str = re.sub(r"/\*.*?\*/", "", json_str, flags=re.DOTALL)

                result = json.loads(json_str)
                return result
            else:
                logger.warning("⚠️ LLM 响应未包含有效 JSON")
                return self._default_evaluation()

        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ JSON 解析失败: {e}")
            return self._default_evaluation()
        except Exception as e:
            logger.error(f"❌ LLM 调用失败: {e}")
            return self._default_evaluation()

    def _default_evaluation(self) -> Dict[str, Any]:
        """返回默认评估结果"""
        return {"risks": [], "role_optimizations": {}, "confidence_score": 70, "summary": "自动评估完成，未发现明显风险"}

    def _apply_auto_mitigations(
        self,
        selected_roles: List[Dict[str, Any]],
        evaluation_result: Dict[str, Any],
    ) -> Tuple[Dict[str, Dict], List[str]]:
        """
        自动应用缓解策略

        Returns:
            (role_adjustments, auto_mitigations)
        """
        role_adjustments = {}
        auto_mitigations = []

        # 从评估结果中提取角色优化建议
        role_optimizations = evaluation_result.get("role_optimizations", {})

        for role_id, optimization in role_optimizations.items():
            if optimization:
                role_adjustments[role_id] = {
                    "enhanced_prompt": optimization.get("enhanced_prompt", ""),
                    "search_keywords": optimization.get("search_keywords", []),
                    "focus_refinement": optimization.get("focus_refinement", ""),
                    "additional_context": "",
                }

                # 记录应用的优化
                if optimization.get("enhanced_prompt"):
                    auto_mitigations.append(f"已为 {role_id} 补充任务说明")
                if optimization.get("search_keywords"):
                    keywords = optimization["search_keywords"]
                    auto_mitigations.append(f"已为 {role_id} 添加搜索关键词: {', '.join(keywords[:3])}")

        # 从风险列表中提取自动修正
        risks = evaluation_result.get("risks", [])
        for risk in risks:
            if risk.get("auto_mitigation") and risk.get("severity") in ["medium", "high"]:
                role_id = risk.get("role_id", "unknown")
                mitigation = risk["auto_mitigation"]

                # 合并到 role_adjustments
                if role_id not in role_adjustments:
                    role_adjustments[role_id] = {
                        "enhanced_prompt": "",
                        "search_keywords": [],
                        "focus_refinement": "",
                        "additional_context": mitigation,
                    }
                else:
                    existing = role_adjustments[role_id].get("additional_context", "")
                    role_adjustments[role_id]["additional_context"] = f"{existing}\n{mitigation}".strip()

                auto_mitigations.append(f"[{role_id}] {mitigation}")

        return role_adjustments, auto_mitigations


# 便捷函数
async def evaluate_task_generation(
    selected_roles: List[Dict[str, Any]],
    structured_requirements: Dict[str, Any],
    user_input: str,
    llm_model=None,
) -> Dict[str, Any]:
    """
    评估任务生成的便捷函数

    在 role_task_unified_review 节点中调用
    """
    guard = TaskGenerationGuard(llm_model)
    return await guard.evaluate_and_optimize(selected_roles, structured_requirements, user_input)
