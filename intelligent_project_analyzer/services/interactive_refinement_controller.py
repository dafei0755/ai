"""
交互精化控制器 - 结果导向型架构的交互层

提供30秒后的用户驱动精化功能：
- 置信度透明化显示
- 交互式参数调整
- 实时结果预览
- 智能建议引导
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class RefinementAction(Enum):
    """精化动作类型"""

    ADJUST_PARAMETERS = "adjust_parameters"  # 调整参数
    ADD_CONSTRAINTS = "add_constraints"  # 添加约束
    MODIFY_PRIORITIES = "modify_priorities"  # 修改优先级
    EXPLORE_ALTERNATIVES = "explore_alternatives"  # 探索替代方案
    REQUEST_DETAILS = "request_details"  # 请求更多细节


@dataclass
class RefinementOption:
    """精化选项"""

    action: RefinementAction
    title: str
    description: str
    impact_preview: str
    confidence_change: float  # 预期置信度变化
    effort_level: int  # 1-5 (1=简单, 5=复杂)


@dataclass
class InteractiveControl:
    """交互控制项"""

    control_type: str  # 'slider', 'select', 'toggle', 'input'
    label: str
    current_value: Any
    options: List | None = None  # for select type
    min_value: float | None = None  # for slider
    max_value: float | None = None  # for slider
    step: float | None = None  # for slider
    description: str = ""


@dataclass
class RefinementResult:
    """精化结果"""

    refined_hypothesis: Dict
    confidence_improvement: float
    changes_summary: List[str]
    next_refinement_options: List[RefinementOption]
    processing_time: float


class InteractiveRefinementController:
    """交互式精化控制器"""

    def __init__(self):
        self.active_sessions: Dict[str, Dict] = {}
        self.refinement_history: Dict[str, List] = {}

        # 预定义控制模板
        self.control_templates = {
            "budget": {
                "type": "slider",
                "label": "预算范围",
                "min_value": 10000,
                "max_value": 1000000,
                "step": 5000,
                "description": "调整项目预算上限",
            },
            "timeline": {
                "type": "slider",
                "label": "时间要求（天）",
                "min_value": 7,
                "max_value": 365,
                "step": 7,
                "description": "项目完成时间限制",
            },
            "quality_level": {
                "type": "select",
                "label": "质量标准",
                "options": ["基础", "标准", "精品", "奢华"],
                "description": "期望的质量水准",
            },
            "risk_tolerance": {
                "type": "select",
                "label": "风险承受度",
                "options": ["保守", "稳健", "积极", "激进"],
                "description": "对项目风险的接受程度",
            },
            "innovation_level": {
                "type": "slider",
                "label": "创新程度",
                "min_value": 0,
                "max_value": 100,
                "step": 10,
                "description": "0=传统保守, 100=极具创新",
            },
        }

    async def initialize_refinement_session(
        self, session_id: str, optimization_result: Dict, user_context: Dict
    ) -> Dict:
        """
        初始化精化会话

        Args:
            session_id: 会话ID
            optimization_result: 优化结果
            user_context: 用户上下文

        Returns:
            精化界面配置
        """

        # 分析可精化的维度
        refinable_dimensions = self._analyze_refinable_dimensions(optimization_result, user_context)

        # 生成交互控制项
        interactive_controls = await self._generate_interactive_controls(refinable_dimensions, user_context)

        # 生成精化选项
        refinement_options = await self._generate_refinement_options(optimization_result, user_context)

        # 存储会话状态
        self.active_sessions[session_id] = {
            "optimization_result": optimization_result,
            "user_context": user_context,
            "refinable_dimensions": refinable_dimensions,
            "interactive_controls": interactive_controls,
            "current_refinement_options": refinement_options,
            "refinement_count": 0,
            "start_time": datetime.now(),
        }

        return {
            "session_id": session_id,
            "confidence_display": {
                "current_confidence": optimization_result.get("final_confidence", 0.7),
                "confidence_breakdown": self._create_confidence_breakdown(optimization_result),
                "improvement_potential": self._estimate_improvement_potential(refinement_options),
            },
            "interactive_controls": interactive_controls,
            "refinement_options": [self._option_to_dict(opt) for opt in refinement_options],
            "progress_indicator": {
                "stages_completed": ["假设生成", "并行验证", "专家分析", "优化建议"],
                "current_stage": "交互精化",
                "estimated_remaining_time": "按需调整",
            },
        }

    def _analyze_refinable_dimensions(self, optimization_result: Dict, user_context: Dict) -> List[str]:
        """分析可精化的维度"""

        dimensions = []

        # 基于用户输入分析
        user_input = user_context.get("original_input", "")

        if any(word in user_input for word in ["预算", "费用", "成本"]):
            dimensions.append("budget")

        if any(word in user_input for word in ["时间", "周期", "期限"]):
            dimensions.append("timeline")

        if any(word in user_input for word in ["质量", "档次", "标准"]):
            dimensions.append("quality_level")

        # 基于优化结果分析
        confidence = optimization_result.get("final_confidence", 0.7)
        if confidence < 0.8:
            dimensions.extend(["risk_tolerance", "innovation_level"])

        # 确保至少有基础维度
        if not dimensions:
            dimensions = ["quality_level", "risk_tolerance"]

        return dimensions

    async def _generate_interactive_controls(
        self, dimensions: List[str], user_context: Dict
    ) -> List[InteractiveControl]:
        """生成交互控制项"""

        controls = []

        for dimension in dimensions:
            template = self.control_templates.get(dimension)
            if not template:
                continue

            # 基于用户上下文设置默认值
            default_value = self._extract_default_value(dimension, user_context)

            control = InteractiveControl(
                control_type=template["type"],
                label=template["label"],
                current_value=default_value,
                options=template.get("options"),
                min_value=template.get("min_value"),
                max_value=template.get("max_value"),
                step=template.get("step"),
                description=template["description"],
            )

            controls.append(control)

        return controls

    def _extract_default_value(self, dimension: str, user_context: Dict) -> Any:
        """从用户上下文中提取默认值"""

        user_input = user_context.get("original_input", "").lower()

        if dimension == "budget":
            # 尝试从输入中提取预算数字
            import re

            budget_match = re.search(r"(\d+)\s*万", user_input)
            if budget_match:
                return int(budget_match.group(1)) * 10000
            return 100000  # 默认10万

        elif dimension == "timeline":
            if "急" in user_input or "快" in user_input:
                return 30
            elif "慢" in user_input or "充足" in user_input:
                return 180
            return 90  # 默认3个月

        elif dimension == "quality_level":
            if any(word in user_input for word in ["高端", "奢华", "精品"]):
                return "奢华"
            elif any(word in user_input for word in ["经济", "实用", "简单"]):
                return "基础"
            return "标准"

        elif dimension == "risk_tolerance":
            if any(word in user_input for word in ["保守", "稳妥", "安全"]):
                return "保守"
            elif any(word in user_input for word in ["创新", "大胆", "尝试"]):
                return "积极"
            return "稳健"

        elif dimension == "innovation_level":
            if any(word in user_input for word in ["传统", "经典", "常规"]):
                return 30
            elif any(word in user_input for word in ["创新", "前沿", "独特"]):
                return 80
            return 50

        return None

    async def _generate_refinement_options(
        self, optimization_result: Dict, user_context: Dict
    ) -> List[RefinementOption]:
        """生成精化选项"""

        options = []
        current_confidence = optimization_result.get("final_confidence", 0.7)

        # 基于置信度生成选项
        if current_confidence < 0.8:
            options.append(
                RefinementOption(
                    action=RefinementAction.REQUEST_DETAILS,
                    title="补充需求细节",
                    description="提供更多具体信息以提高分析精度",
                    impact_preview=f"预期提升置信度至 {min(0.9, current_confidence + 0.15):.1%}",
                    confidence_change=0.15,
                    effort_level=2,
                )
            )

        # 基于优化建议生成选项
        suggestions = optimization_result.get("top_suggestions", [])
        if suggestions:
            options.append(
                RefinementOption(
                    action=RefinementAction.ADJUST_PARAMETERS,
                    title="调整核心参数",
                    description="根据专家建议微调关键参数",
                    impact_preview="优化方案匹配度和可执行性",
                    confidence_change=0.08,
                    effort_level=3,
                )
            )

        # 通用精化选项
        options.extend(
            [
                RefinementOption(
                    action=RefinementAction.ADD_CONSTRAINTS,
                    title="增加约束条件",
                    description="添加新的限制条件以缩小方案范围",
                    impact_preview="提高方案针对性",
                    confidence_change=0.05,
                    effort_level=2,
                ),
                RefinementOption(
                    action=RefinementAction.EXPLORE_ALTERNATIVES,
                    title="探索替代方案",
                    description="生成不同的实现路径供比较",
                    impact_preview="发现更优选择可能性",
                    confidence_change=-0.02,  # 可能暂时降低置信度
                    effort_level=4,
                ),
                RefinementOption(
                    action=RefinementAction.MODIFY_PRIORITIES,
                    title="重新排序优先级",
                    description="调整各个目标的重要性权重",
                    impact_preview="优化资源分配策略",
                    confidence_change=0.03,
                    effort_level=1,
                ),
            ]
        )

        return options

    async def execute_refinement(self, session_id: str, action: RefinementAction, parameters: Dict) -> RefinementResult:
        """
        执行精化操作

        Args:
            session_id: 会话ID
            action: 精化动作
            parameters: 精化参数

        Returns:
            精化结果
        """

        start_time = datetime.now()

        if session_id not in self.active_sessions:
            raise ValueError(f"会话 {session_id} 不存在")

        session = self.active_sessions[session_id]

        try:
            # 执行具体精化操作
            if action == RefinementAction.ADJUST_PARAMETERS:
                result = await self._adjust_parameters(session, parameters)
            elif action == RefinementAction.ADD_CONSTRAINTS:
                result = await self._add_constraints(session, parameters)
            elif action == RefinementAction.MODIFY_PRIORITIES:
                result = await self._modify_priorities(session, parameters)
            elif action == RefinementAction.EXPLORE_ALTERNATIVES:
                result = await self._explore_alternatives(session, parameters)
            elif action == RefinementAction.REQUEST_DETAILS:
                result = await self._request_details(session, parameters)
            else:
                raise ValueError(f"不支持的精化动作: {action}")

            # 更新会话状态
            session["refinement_count"] += 1
            self._record_refinement_history(session_id, action, parameters, result)

            # 生成新的精化选项
            new_options = await self._generate_refinement_options(result["refined_hypothesis"], session["user_context"])
            session["current_refinement_options"] = new_options

            processing_time = (datetime.now() - start_time).total_seconds()

            return RefinementResult(
                refined_hypothesis=result["refined_hypothesis"],
                confidence_improvement=result["confidence_improvement"],
                changes_summary=result["changes_summary"],
                next_refinement_options=new_options,
                processing_time=processing_time,
            )

        except Exception as e:
            logger.error(f"精化执行失败: {e}")
            raise

    async def _adjust_parameters(self, session: Dict, parameters: Dict) -> Dict:
        """调整参数精化"""

        original_result = session["optimization_result"]
        adjusted_confidence = original_result.get("final_confidence", 0.7)

        changes = []

        # 处理各种参数调整
        for param_name, param_value in parameters.items():
            if param_name == "budget":
                # 预算调整影响
                if param_value > 200000:  # 20万以上
                    adjusted_confidence += 0.05
                    changes.append(f"预算提升至{param_value/10000:.0f}万，方案可行性增强")
                elif param_value < 50000:  # 5万以下
                    adjusted_confidence -= 0.1
                    changes.append(f"预算压缩至{param_value/10000:.0f}万，需要调整期望")

            elif param_name == "timeline":
                if param_value > 120:  # 4个月以上
                    adjusted_confidence += 0.03
                    changes.append(f"时间充裕({param_value}天)，执行质量可保证")
                elif param_value < 30:  # 1个月内
                    adjusted_confidence -= 0.08
                    changes.append(f"时间紧迫({param_value}天)，需要简化方案")

            elif param_name == "quality_level":
                quality_impact = {"基础": -0.02, "标准": 0, "精品": 0.05, "奢华": 0.08}
                impact = quality_impact.get(param_value, 0)
                adjusted_confidence += impact
                changes.append(f"质量标准调整为{param_value}")

        # 限制置信度范围
        adjusted_confidence = max(0.1, min(0.95, adjusted_confidence))
        original_confidence = original_result.get("final_confidence", 0.7)

        return {
            "refined_hypothesis": {
                **original_result,
                "final_confidence": adjusted_confidence,
                "parameter_adjustments": parameters,
                "refinement_timestamp": datetime.now().isoformat(),
            },
            "confidence_improvement": adjusted_confidence - original_confidence,
            "changes_summary": changes,
        }

    async def _add_constraints(self, session: Dict, parameters: Dict) -> Dict:
        """添加约束条件"""

        original_result = session["optimization_result"]
        constraints = parameters.get("constraints", [])

        # 约束通常会略微降低置信度但提高针对性
        constraint_impact = -0.02 * len(constraints)  # 每个约束-2%
        specificity_boost = 0.05  # 针对性提升+5%

        net_change = constraint_impact + specificity_boost
        adjusted_confidence = original_result.get("final_confidence", 0.7) + net_change
        adjusted_confidence = max(0.1, min(0.95, adjusted_confidence))

        changes = [f"新增约束: {constraint}" for constraint in constraints]
        changes.append("方案针对性和可执行性提升")

        return {
            "refined_hypothesis": {
                **original_result,
                "final_confidence": adjusted_confidence,
                "added_constraints": constraints,
                "refinement_timestamp": datetime.now().isoformat(),
            },
            "confidence_improvement": net_change,
            "changes_summary": changes,
        }

    async def _modify_priorities(self, session: Dict, parameters: Dict) -> Dict:
        """修改优先级"""

        original_result = session["optimization_result"]
        priority_changes = parameters.get("priority_changes", {})

        # 优先级调整通常小幅提升置信度
        confidence_improvement = 0.03
        adjusted_confidence = original_result.get("final_confidence", 0.7) + confidence_improvement
        adjusted_confidence = max(0.1, min(0.95, adjusted_confidence))

        changes = []
        for item, new_priority in priority_changes.items():
            changes.append(f"{item} 优先级调整为 {new_priority}")

        return {
            "refined_hypothesis": {
                **original_result,
                "final_confidence": adjusted_confidence,
                "priority_adjustments": priority_changes,
                "refinement_timestamp": datetime.now().isoformat(),
            },
            "confidence_improvement": confidence_improvement,
            "changes_summary": changes,
        }

    async def _explore_alternatives(self, session: Dict, parameters: Dict) -> Dict:
        """探索替代方案"""

        original_result = session["optimization_result"]

        # 探索替代方案可能暂时降低置信度，但提供更多选择
        confidence_change = -0.02
        adjusted_confidence = original_result.get("final_confidence", 0.7) + confidence_change

        alternatives = ["方案A: 渐进式实施，降低风险", "方案B: 集中投入，快速见效", "方案C: 混合策略，平衡收益与风险"]

        return {
            "refined_hypothesis": {
                **original_result,
                "final_confidence": adjusted_confidence,
                "alternative_approaches": alternatives,
                "refinement_timestamp": datetime.now().isoformat(),
            },
            "confidence_improvement": confidence_change,
            "changes_summary": ["生成3个替代实施方案", "增加选择灵活性"],
        }

    async def _request_details(self, session: Dict, parameters: Dict) -> Dict:
        """请求更多细节"""

        original_result = session["optimization_result"]
        requested_details = parameters.get("detail_areas", [])

        # 获取更多细节通常显著提升置信度
        confidence_improvement = 0.12
        adjusted_confidence = original_result.get("final_confidence", 0.7) + confidence_improvement
        adjusted_confidence = max(0.1, min(0.95, adjusted_confidence))

        changes = []
        for area in requested_details:
            changes.append(f"补充 {area} 相关详细信息")
        changes.append("分析精度和可信度显著提升")

        return {
            "refined_hypothesis": {
                **original_result,
                "final_confidence": adjusted_confidence,
                "detailed_areas": requested_details,
                "refinement_timestamp": datetime.now().isoformat(),
            },
            "confidence_improvement": confidence_improvement,
            "changes_summary": changes,
        }

    def _create_confidence_breakdown(self, optimization_result: Dict) -> Dict:
        """创建置信度分解显示"""

        final_confidence = optimization_result.get("final_confidence", 0.7)

        return {
            "初始假设": optimization_result.get("original_hypothesis", {}).get("confidence", 0.7),
            "验证调整": optimization_result.get("verification_summary", {}).get("confidence_adjustment", 0),
            "专家分析": optimization_result.get("expert_analysis_summary", {}).get("avg_confidence", 0.7),
            "最终置信度": final_confidence,
            "置信度等级": self._get_confidence_level(final_confidence),
        }

    def _get_confidence_level(self, confidence: float) -> str:
        """获取置信度等级描述"""
        if confidence >= 0.9:
            return "极高 "
        elif confidence >= 0.8:
            return "高 "
        elif confidence >= 0.7:
            return "中等 "
        elif confidence >= 0.6:
            return "偏低 ️"
        else:
            return "低 "

    def _estimate_improvement_potential(self, options: List[RefinementOption]) -> Dict:
        """估算改进潜力"""

        if not options:
            return {"max_improvement": 0, "recommended_actions": 0}

        max_improvement = max(opt.confidence_change for opt in options)
        recommended_actions = len([opt for opt in options if opt.confidence_change > 0.05])

        return {
            "max_improvement": max_improvement,
            "recommended_actions": recommended_actions,
            "potential_final_confidence": min(0.95, 0.7 + max_improvement),
        }

    def _option_to_dict(self, option: RefinementOption) -> Dict:
        """转换精化选项为字典"""
        return {
            "action": option.action.value,
            "title": option.title,
            "description": option.description,
            "impact_preview": option.impact_preview,
            "confidence_change": option.confidence_change,
            "effort_level": option.effort_level,
        }

    def _record_refinement_history(self, session_id: str, action: RefinementAction, parameters: Dict, result: Dict):
        """记录精化历史"""

        if session_id not in self.refinement_history:
            self.refinement_history[session_id] = []

        self.refinement_history[session_id].append(
            {
                "timestamp": datetime.now().isoformat(),
                "action": action.value,
                "parameters": parameters,
                "confidence_change": result["confidence_improvement"],
                "changes_count": len(result["changes_summary"]),
            }
        )

    def get_session_status(self, session_id: str) -> Dict:
        """获取会话状态"""

        if session_id not in self.active_sessions:
            return {"error": "会话不存在"}

        session = self.active_sessions[session_id]
        history = self.refinement_history.get(session_id, [])

        return {
            "session_id": session_id,
            "refinement_count": session["refinement_count"],
            "start_time": session["start_time"].isoformat(),
            "current_confidence": session["optimization_result"].get("final_confidence", 0.7),
            "available_options": len(session["current_refinement_options"]),
            "history_count": len(history),
        }
