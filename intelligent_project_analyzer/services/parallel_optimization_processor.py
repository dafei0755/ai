"""
并行优化处理架构 - 实时验证与优化

5-30秒内并行处理假设验证、专家分析、优化建议
实时更新进度，透明化处理过程，提供持续反馈
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from ..core.config import get_config
from ..core.llm_service import LLMService
from ..core.search_service import SearchService
from .immediate_hypothesis_generator import ImmediateHypothesis

logger = logging.getLogger(__name__)


class OptimizationStage(Enum):
    """优化阶段枚举"""

    VERIFICATION = "verification"  # 验证阶段 (5-10秒)
    EXPERT_ANALYSIS = "expert_analysis"  # 专家分析 (10-20秒)
    OPTIMIZATION = "optimization"  # 优化建议 (20-30秒)
    INTEGRATION = "integration"  # 结果整合 (30秒)


@dataclass
class OptimizationProgress:
    """优化进度跟踪"""

    stage: OptimizationStage
    progress: float  # 0.0-1.0
    message: str
    timestamp: datetime
    details: Dict = field(default_factory=dict)


@dataclass
class VerificationResult:
    """验证结果"""

    verified_assumptions: List[Dict]
    challenged_assumptions: List[Dict]
    new_insights: List[str]
    confidence_adjustment: float  # -0.2 到 +0.2


@dataclass
class ExpertAnalysis:
    """专家分析结果"""

    expert_type: str
    analysis: str
    recommendations: List[str]
    risk_assessment: Dict
    confidence_score: float


@dataclass
class OptimizationSuggestion:
    """优化建议"""

    suggestion_type: str  # 'enhancement', 'risk_mitigation', 'alternative'
    title: str
    description: str
    impact_level: str  # 'high', 'medium', 'low'
    effort_required: str  # 'high', 'medium', 'low'
    priority: int  # 1-5


class ParallelOptimizationProcessor:
    """并行优化处理器"""

    def __init__(self):
        self.llm_service = LLMService()
        self.search_service = SearchService()
        self.config = get_config()
        self.progress_callbacks: List[Callable] = []

    def add_progress_callback(self, callback: Callable):
        """添加进度回调函数"""
        self.progress_callbacks.append(callback)

    async def _notify_progress(self, progress: OptimizationProgress):
        """通知进度更新"""
        for callback in self.progress_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(progress)
                else:
                    callback(progress)
            except Exception as e:
                logger.error(f"进度回调失败: {e}")

    async def optimize_hypothesis(
        self, hypothesis: ImmediateHypothesis, user_context: Dict, optimization_preferences: Optional[Dict] = None
    ) -> Dict:
        """
        并行优化假设 - 5-30秒处理目标

        Args:
            hypothesis: 初始假设
            user_context: 用户上下文
            optimization_preferences: 优化偏好设置

        Returns:
            优化结果字典
        """
        start_time = datetime.now()

        try:
            # 阶段1: 假设验证 (5-10秒)
            await self._notify_progress(
                OptimizationProgress(
                    stage=OptimizationStage.VERIFICATION, progress=0.1, message="开始验证初始假设...", timestamp=datetime.now()
                )
            )

            verification_result = await self._verify_hypothesis(hypothesis, user_context)

            await self._notify_progress(
                OptimizationProgress(
                    stage=OptimizationStage.VERIFICATION,
                    progress=0.3,
                    message="假设验证完成，启动专家分析...",
                    timestamp=datetime.now(),
                    details={"verified_count": len(verification_result.verified_assumptions)},
                )
            )

            # 阶段2: 并行专家分析 (10-20秒)
            expert_analyses = await self._parallel_expert_analysis(hypothesis, verification_result, user_context)

            await self._notify_progress(
                OptimizationProgress(
                    stage=OptimizationStage.EXPERT_ANALYSIS,
                    progress=0.6,
                    message="专家分析完成，生成优化建议...",
                    timestamp=datetime.now(),
                    details={"expert_count": len(expert_analyses)},
                )
            )

            # 阶段3: 优化建议生成 (20-30秒)
            optimization_suggestions = await self._generate_optimization_suggestions(
                hypothesis, verification_result, expert_analyses, user_context
            )

            await self._notify_progress(
                OptimizationProgress(
                    stage=OptimizationStage.OPTIMIZATION,
                    progress=0.9,
                    message="整合优化结果...",
                    timestamp=datetime.now(),
                    details={"suggestion_count": len(optimization_suggestions)},
                )
            )

            # 阶段4: 结果整合 (30秒)
            integrated_result = await self._integrate_results(
                hypothesis, verification_result, expert_analyses, optimization_suggestions
            )

            await self._notify_progress(
                OptimizationProgress(
                    stage=OptimizationStage.INTEGRATION,
                    progress=1.0,
                    message="优化完成！",
                    timestamp=datetime.now(),
                    details={"final_confidence": integrated_result["final_confidence"]},
                )
            )

            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"并行优化完成: {elapsed:.2f}s")

            return integrated_result

        except Exception as e:
            logger.error(f"并行优化失败: {e}")
            return await self._create_fallback_optimization(hypothesis)

    async def _verify_hypothesis(self, hypothesis: ImmediateHypothesis, user_context: Dict) -> VerificationResult:
        """验证假设的核心假设"""

        verification_tasks = []

        # 并行验证每个关键假设
        for assumption in hypothesis.key_assumptions:
            task = self._verify_single_assumption(assumption, user_context)
            verification_tasks.append(task)

        # 并行执行验证
        verification_results = await asyncio.gather(*verification_tasks, return_exceptions=True)

        verified_assumptions = []
        challenged_assumptions = []
        new_insights = []

        for i, result in enumerate(verification_results):
            if isinstance(result, Exception):
                logger.error(f"假设验证失败: {result}")
                continue

            if result["is_valid"]:
                verified_assumptions.append(
                    {
                        "assumption": hypothesis.key_assumptions[i],
                        "evidence": result["evidence"],
                        "confidence": result["confidence"],
                    }
                )
            else:
                challenged_assumptions.append(
                    {
                        "assumption": hypothesis.key_assumptions[i],
                        "challenge": result["challenge"],
                        "alternative": result.get("alternative", ""),
                    }
                )
                new_insights.extend(result.get("insights", []))

        # 计算置信度调整
        verification_rate = len(verified_assumptions) / len(hypothesis.key_assumptions)
        confidence_adjustment = (verification_rate - 0.5) * 0.2  # -0.2 to +0.2

        return VerificationResult(
            verified_assumptions=verified_assumptions,
            challenged_assumptions=challenged_assumptions,
            new_insights=new_insights,
            confidence_adjustment=confidence_adjustment,
        )

    async def _verify_single_assumption(self, assumption: str, context: Dict) -> Dict:
        """验证单个假设"""
        prompt = f"""
        基于用户上下文验证以下假设的合理性：

        假设: {assumption}
        用户上下文: {json.dumps(context, ensure_ascii=False, indent=2)}

        返回JSON格式：
        {{
            "is_valid": true/false,
            "confidence": 0.0-1.0,
            "evidence": "支持证据",
            "challenge": "质疑理由（如果不合理）",
            "alternative": "替代假设（如果有）",
            "insights": ["新洞察1", "新洞察2"]
        }}
        """

        response = await self.llm_service.achat_completion([{"role": "user", "content": prompt}])

        try:
            return json.loads(response.content)
        except:
            return {
                "is_valid": True,
                "confidence": 0.6,
                "evidence": "基于常见实践判断",
                "challenge": "",
                "alternative": "",
                "insights": [],
            }

    async def _parallel_expert_analysis(
        self, hypothesis: ImmediateHypothesis, verification: VerificationResult, context: Dict
    ) -> List[ExpertAnalysis]:
        """并行专家分析"""

        # 定义专家类型
        expert_types = [
            {"type": "feasibility_expert", "name": "可行性专家", "focus": "技术可行性、资源需求、实施难度"},
            {"type": "risk_expert", "name": "风险管理专家", "focus": "风险识别、影响评估、缓解策略"},
            {"type": "optimization_expert", "name": "优化专家", "focus": "效率提升、成本控制、性能优化"},
        ]

        # 并行执行专家分析
        analysis_tasks = [
            self._single_expert_analysis(expert, hypothesis, verification, context) for expert in expert_types
        ]

        analyses = await asyncio.gather(*analysis_tasks, return_exceptions=True)

        # 过滤异常结果
        valid_analyses = [analysis for analysis in analyses if not isinstance(analysis, Exception)]

        return valid_analyses

    async def _single_expert_analysis(
        self, expert_config: Dict, hypothesis: ImmediateHypothesis, verification: VerificationResult, context: Dict
    ) -> ExpertAnalysis:
        """单个专家分析"""

        prompt = f"""
        作为{expert_config['name']}，从{expert_config['focus']}的角度分析以下假设：

        假设标题: {hypothesis.title}
        假设摘要: {hypothesis.summary}
        验证结果: {len(verification.verified_assumptions)}个假设验证通过，{len(verification.challenged_assumptions)}个存疑

        请提供专业分析（200字以内）和建议。

        返回JSON格式：
        {{
            "analysis": "专业分析内容",
            "recommendations": ["建议1", "建议2", "建议3"],
            "risk_assessment": {{
                "high_risks": ["高风险项"],
                "medium_risks": ["中风险项"],
                "mitigation_strategies": ["缓解策略"]
            }},
            "confidence_score": 0.0-1.0
        }}
        """

        response = await self.llm_service.achat_completion([{"role": "user", "content": prompt}])

        try:
            result = json.loads(response.content)
            return ExpertAnalysis(
                expert_type=expert_config["type"],
                analysis=result["analysis"],
                recommendations=result["recommendations"],
                risk_assessment=result["risk_assessment"],
                confidence_score=result["confidence_score"],
            )
        except Exception as e:
            logger.error(f"专家分析解析失败: {e}")
            return ExpertAnalysis(
                expert_type=expert_config["type"],
                analysis="分析处理中遇到问题，建议进一步详细评估",
                recommendations=["详细需求分析", "多方案对比", "风险评估"],
                risk_assessment={"high_risks": [], "medium_risks": [], "mitigation_strategies": []},
                confidence_score=0.5,
            )

    async def _generate_optimization_suggestions(
        self,
        hypothesis: ImmediateHypothesis,
        verification: VerificationResult,
        expert_analyses: List[ExpertAnalysis],
        context: Dict,
    ) -> List[OptimizationSuggestion]:
        """生成优化建议"""

        # 收集所有专家建议
        all_recommendations = []
        for analysis in expert_analyses:
            all_recommendations.extend(analysis.recommendations)

        prompt = f"""
        基于专家分析结果，生成5个具体的优化建议：

        原始假设置信度: {hypothesis.confidence:.2f}
        验证调整: {verification.confidence_adjustment:+.2f}
        专家建议: {', '.join(all_recommendations)}

        返回JSON格式的建议数组：
        [
            {{
                "suggestion_type": "enhancement|risk_mitigation|alternative",
                "title": "建议标题",
                "description": "详细描述",
                "impact_level": "high|medium|low",
                "effort_required": "high|medium|low",
                "priority": 1-5
            }}
        ]
        """

        response = await self.llm_service.achat_completion([{"role": "user", "content": prompt}])

        try:
            suggestions_data = json.loads(response.content)
            suggestions = []

            for data in suggestions_data:
                suggestion = OptimizationSuggestion(
                    suggestion_type=data["suggestion_type"],
                    title=data["title"],
                    description=data["description"],
                    impact_level=data["impact_level"],
                    effort_required=data["effort_required"],
                    priority=data["priority"],
                )
                suggestions.append(suggestion)

            return suggestions

        except Exception as e:
            logger.error(f"优化建议生成失败: {e}")
            return self._create_fallback_suggestions()

    def _create_fallback_suggestions(self) -> List[OptimizationSuggestion]:
        """创建兜底优化建议"""
        return [
            OptimizationSuggestion(
                suggestion_type="enhancement",
                title="详细需求分析",
                description="进一步明确用户需求和期望",
                impact_level="high",
                effort_required="medium",
                priority=1,
            ),
            OptimizationSuggestion(
                suggestion_type="risk_mitigation",
                title="风险预案准备",
                description="制定主要风险的应对策略",
                impact_level="medium",
                effort_required="medium",
                priority=2,
            ),
        ]

    async def _integrate_results(
        self,
        hypothesis: ImmediateHypothesis,
        verification: VerificationResult,
        expert_analyses: List[ExpertAnalysis],
        optimization_suggestions: List[OptimizationSuggestion],
    ) -> Dict:
        """整合所有优化结果"""

        # 计算最终置信度
        base_confidence = hypothesis.confidence
        verification_adjustment = verification.confidence_adjustment
        expert_avg_confidence = (
            sum(a.confidence_score for a in expert_analyses) / len(expert_analyses) if expert_analyses else 0.5
        )

        final_confidence = (base_confidence + verification_adjustment + expert_avg_confidence) / 2
        final_confidence = max(0.1, min(0.95, final_confidence))  # 限制在10%-95%

        # 优先级排序建议
        sorted_suggestions = sorted(optimization_suggestions, key=lambda x: x.priority)

        return {
            "original_hypothesis": {
                "id": hypothesis.hypothesis_id,
                "title": hypothesis.title,
                "confidence": hypothesis.confidence,
            },
            "verification_summary": {
                "verified_count": len(verification.verified_assumptions),
                "challenged_count": len(verification.challenged_assumptions),
                "new_insights_count": len(verification.new_insights),
                "confidence_adjustment": verification.confidence_adjustment,
            },
            "expert_analysis_summary": {
                "expert_count": len(expert_analyses),
                "avg_confidence": expert_avg_confidence,
                "total_recommendations": sum(len(a.recommendations) for a in expert_analyses),
            },
            "optimization_summary": {
                "suggestion_count": len(optimization_suggestions),
                "high_priority_count": sum(1 for s in optimization_suggestions if s.priority <= 2),
            },
            "final_confidence": final_confidence,
            "confidence_improvement": final_confidence - hypothesis.confidence,
            "top_suggestions": [
                {"title": s.title, "type": s.suggestion_type, "impact": s.impact_level, "priority": s.priority}
                for s in sorted_suggestions[:3]
            ],
            "processing_timestamp": datetime.now().isoformat(),
            "next_steps": ["审查优化建议", "选择实施方案", "制定详细计划", "开始执行实施"],
        }

    async def _create_fallback_optimization(self, hypothesis: ImmediateHypothesis) -> Dict:
        """创建兜底优化结果"""
        return {
            "original_hypothesis": {
                "id": hypothesis.hypothesis_id,
                "title": hypothesis.title,
                "confidence": hypothesis.confidence,
            },
            "verification_summary": {"status": "fallback_mode", "message": "优化处理遇到问题，使用基础分析结果"},
            "final_confidence": max(0.6, hypothesis.confidence),
            "confidence_improvement": 0.0,
            "top_suggestions": [
                {"title": "详细需求确认", "type": "enhancement", "impact": "high", "priority": 1},
                {"title": "资源可行性评估", "type": "risk_mitigation", "impact": "medium", "priority": 2},
            ],
            "processing_timestamp": datetime.now().isoformat(),
            "next_steps": ["详细分析", "专家咨询", "方案细化"],
        }
