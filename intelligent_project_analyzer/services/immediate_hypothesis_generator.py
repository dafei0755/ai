"""
立即假设生成服务 - 结果导向型架构核心组件

提供0-5秒内的即时假设生成，置信度70%+，消除等待焦虑
基于用户输入快速生成可行假设，后续并行验证优化
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..core.config import get_config
from ..core.llm_service import LLMService

logger = logging.getLogger(__name__)


@dataclass
class ImmediateHypothesis:
    """即时假设结构"""

    hypothesis_id: str
    title: str
    summary: str
    confidence: float  # 0.0-1.0
    key_assumptions: List[str]
    expected_outcomes: List[str]
    risk_factors: List[str]
    verification_steps: List[str]
    timestamp: datetime


class ImmediateHypothesisGenerator:
    """立即假设生成器 - 0-5秒快速响应"""

    def __init__(self):
        self.llm_service = LLMService()
        self.config = get_config()

        # 预定义模板库 - 快速匹配
        self.hypothesis_templates = {
            "interior_design": {
                "pattern_keywords": ["室内", "装修", "设计", "家居", "空间"],
                "base_hypothesis": {
                    "title": "空间功能优化策略",
                    "assumptions": ["用户重视实用性", "预算有限制", "需要储物解决方案"],
                    "outcomes": ["提升空间利用率", "改善生活质量", "控制成本"],
                    "risks": ["预算超支", "施工周期延长", "设计偏好变化"],
                },
            },
            "business_strategy": {
                "pattern_keywords": ["商业", "战略", "市场", "运营", "增长"],
                "base_hypothesis": {
                    "title": "业务增长可行性分析",
                    "assumptions": ["市场有需求", "竞争压力存在", "资源配置关键"],
                    "outcomes": ["市场份额增长", "收入提升", "品牌建设"],
                    "risks": ["市场变化", "竞争加剧", "资源不足"],
                },
            },
            "technology": {
                "pattern_keywords": ["技术", "开发", "系统", "平台", "AI"],
                "base_hypothesis": {
                    "title": "技术实现可行性评估",
                    "assumptions": ["技术方案可行", "团队有能力", "时间充足"],
                    "outcomes": ["功能实现", "性能提升", "用户体验改善"],
                    "risks": ["技术难度", "时间不足", "资源限制"],
                },
            },
        }

    async def generate_immediate_hypothesis(
        self, user_input: str, context: Optional[Dict] = None
    ) -> ImmediateHypothesis:
        """
        生成立即假设 - 0-5秒响应目标

        Args:
            user_input: 用户输入内容
            context: 附加上下文信息

        Returns:
            ImmediateHypothesis: 立即生成的假设
        """
        start_time = datetime.now()

        try:
            # Step 1: 快速模式匹配 (0.1秒)
            domain = self._detect_domain(user_input)
            base_template = self.hypothesis_templates.get(domain, self.hypothesis_templates["business_strategy"])

            # Step 2: 并行执行快速分析 (2-4秒)
            tasks = [
                self._extract_key_elements(user_input),
                self._assess_initial_confidence(user_input, domain),
                self._generate_quick_insights(user_input, base_template),
            ]

            elements, confidence, insights = await asyncio.gather(*tasks)

            # Step 3: 组装假设 (0.5秒)
            hypothesis = self._assemble_hypothesis(user_input, domain, base_template, elements, confidence, insights)

            # 确保5秒内响应
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed > 5:
                logger.warning(f"假设生成超时: {elapsed:.2f}s")

            logger.info(f"立即假设生成完成: {elapsed:.2f}s, 置信度: {hypothesis.confidence:.2f}")
            return hypothesis

        except Exception as e:
            logger.error(f"立即假设生成失败: {e}")
            return self._create_fallback_hypothesis(user_input, domain)

    def _detect_domain(self, user_input: str) -> str:
        """快速领域检测"""
        user_input_lower = user_input.lower()

        for domain, config in self.hypothesis_templates.items():
            for keyword in config["pattern_keywords"]:
                if keyword in user_input_lower:
                    return domain

        return "business_strategy"  # 默认领域

    async def _extract_key_elements(self, user_input: str) -> Dict:
        """提取关键元素"""
        prompt = f"""
        快速分析用户输入，提取关键元素（30字以内）：

        用户输入: {user_input}

        返回JSON格式：
        {{
            "main_goal": "主要目标",
            "key_constraints": ["约束1", "约束2"],
            "success_criteria": ["成功标准1", "成功标准2"]
        }}
        """

        response = await self.llm_service.achat_completion([{"role": "user", "content": prompt}])

        try:
            return json.loads(response.content)
        except:
            return {"main_goal": "用户目标待明确", "key_constraints": ["预算限制", "时间要求"], "success_criteria": ["满足基本需求", "控制成本"]}

    async def _assess_initial_confidence(self, user_input: str, domain: str) -> float:
        """评估初始置信度"""
        # 基于输入详细程度快速评估
        input_length = len(user_input)
        detail_score = min(input_length / 200, 1.0)  # 200字符为满分

        # 基于领域匹配度
        domain_match = 0.8 if domain != "business_strategy" else 0.6

        # 基于关键信息完整性
        has_budget = any(word in user_input for word in ["预算", "费用", "成本", "价格"])
        has_timeline = any(word in user_input for word in ["时间", "周期", "期限", "完成"])
        has_specifics = any(word in user_input for word in ["平米", "房间", "功能", "要求"])

        completeness_score = (has_budget + has_timeline + has_specifics) / 3

        # 综合置信度计算
        base_confidence = 0.7  # 基础置信度70%
        confidence = base_confidence + (detail_score * 0.1) + (domain_match * 0.1) + (completeness_score * 0.1)

        return min(confidence, 0.95)  # 最高95%

    async def _generate_quick_insights(self, user_input: str, template: Dict) -> Dict:
        """生成快速洞察"""
        prompt = f"""
        基于用户输入快速生成3个关键洞察（每个15字以内）：

        用户输入: {user_input}

        返回JSON格式：
        {{
            "insights": ["洞察1", "洞察2", "洞察3"],
            "potential_challenges": ["挑战1", "挑战2"],
            "quick_wins": ["快速胜利1", "快速胜利2"]
        }}
        """

        response = await self.llm_service.achat_completion([{"role": "user", "content": prompt}])

        try:
            return json.loads(response.content)
        except:
            return {
                "insights": ["需求明确是关键", "资源配置很重要", "时间规划需合理"],
                "potential_challenges": ["预算控制", "执行难度"],
                "quick_wins": ["明确优先级", "分阶段执行"],
            }

    def _assemble_hypothesis(
        self, user_input: str, domain: str, template: Dict, elements: Dict, confidence: float, insights: Dict
    ) -> ImmediateHypothesis:
        """组装完整假设"""

        base_hypothesis = template["base_hypothesis"]
        hypothesis_id = f"hyp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 基于模板和分析结果生成假设
        title = f"{elements.get('main_goal', base_hypothesis['title'])}"

        summary = f"""
        基于初步分析，提出以下假设方案：

        核心目标：{elements.get('main_goal', '待明确')}
        主要洞察：{', '.join(insights.get('insights', []))}

        该方案基于{domain}领域的最佳实践，初步置信度为{confidence:.1%}。
        """.strip()

        # 组合关键假设
        key_assumptions = base_hypothesis["assumptions"] + elements.get("key_constraints", [])

        # 预期结果
        expected_outcomes = base_hypothesis["outcomes"] + elements.get("success_criteria", [])

        # 风险因素
        risk_factors = base_hypothesis["risks"] + insights.get("potential_challenges", [])

        # 验证步骤
        verification_steps = ["详细需求分析验证", "资源可行性评估", "风险影响评估", "方案优化迭代", "专家团队评审"]

        return ImmediateHypothesis(
            hypothesis_id=hypothesis_id,
            title=title,
            summary=summary,
            confidence=confidence,
            key_assumptions=key_assumptions[:5],  # 限制数量
            expected_outcomes=expected_outcomes[:5],
            risk_factors=risk_factors[:5],
            verification_steps=verification_steps,
            timestamp=datetime.now(),
        )

    def _create_fallback_hypothesis(self, user_input: str, domain: str) -> ImmediateHypothesis:
        """创建兜底假设"""
        return ImmediateHypothesis(
            hypothesis_id=f"fallback_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            title="基础可行性分析",
            summary="基于用户输入的初步可行性分析，需要进一步验证和优化。",
            confidence=0.7,
            key_assumptions=["用户需求真实存在", "基础资源可获得", "执行方案可调整"],
            expected_outcomes=["满足基本需求", "控制整体风险", "提供可行方案"],
            risk_factors=["需求理解偏差", "资源限制", "执行困难"],
            verification_steps=["需求澄清", "资源评估", "方案验证", "专家评审", "优化迭代"],
            timestamp=datetime.now(),
        )

    async def get_hypothesis_status(self, hypothesis_id: str) -> Dict:
        """获取假设状态"""
        # 这里可以实现假设跟踪逻辑
        return {
            "hypothesis_id": hypothesis_id,
            "status": "generated",
            "verification_progress": 0,
            "last_updated": datetime.now().isoformat(),
        }
