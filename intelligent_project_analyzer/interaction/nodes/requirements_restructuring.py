"""
需求重构引擎 (Requirements Restructuring Engine)

职责：
将问卷数据 + AI洞察 + 用户原始输入重构为结构化的项目需求文档

核心理念：
不是机械回顾问卷答案，而是智能生成专业的需求文档，融合：
- 问卷数据（用户显性表达）
- L1-L5 AI洞察（深层理解）
- 原始输入（情感基调）

v7.135: 首次实现
v7.151: 升级为"需求洞察"模块
  - 新增 _llm_comprehensive_analysis: LLM深度分析生成项目本质、隐性需求、关键冲突
  - 优化 _extract_core_tension: LLM替换硬编码模板
  - 融合 L1-L5 洞察到主体: 用户表达 vs AI理解对比展示
  - 合并需求确认功能: 支持用户直接编辑
v3.0: 两阶段架构重构
  - Phase A: 规则化数据准备（收集整理原始数据）
  - Phase B: 单次LLM综合分析（生成全部输出字段）
  - Fallback: LLM失败时降级为规则提取
"""

from datetime import datetime
from typing import Any, Dict, List

from loguru import logger

# 使用LLMFactory创建LLM实例
from ._restructuring_synthesis_mixin import RestructuringSynthesisMixin
from ._restructuring_analysis_mixin import RestructuringAnalysisMixin
from ._restructuring_output_mixin import RestructuringOutputMixin
from ...services.llm_factory import LLMFactory


class RequirementsRestructuringEngine(RestructuringSynthesisMixin, RestructuringAnalysisMixin, RestructuringOutputMixin):
    """需求重构引擎 - 将问卷数据转化为结构化需求文档"""

    @staticmethod
    def restructure(
        questionnaire_data: "Dict[str, Any]",
        ai_analysis: "Dict[str, Any]",
        analysis_layers: "Dict[str, Any]",
        user_input: str,
        use_llm: bool = True,
        weight_interpretations: "Dict[str, Any] | None" = None,
    ) -> "Dict[str, Any]":
        """
        主重构流程 - v3.0 两阶段架构

        Phase A: 规则化数据准备（收集整理原始数据）
        Phase B: 单次LLM综合分析（生成全部输出字段）
        Fallback: LLM失败时降级为规则提取
        """
        logger.info("=" * 80)
        logger.info("🔧 [需求重构引擎 v3.0] 开始两阶段重构")
        logger.info("=" * 80)

        # Phase A: 收集整理原始数据
        context = RequirementsRestructuringEngine._prepare_synthesis_context(
            questionnaire_data, ai_analysis, analysis_layers, user_input
        )
        logger.info(
            f"✅ [Phase A] 数据准备完成: {len(context.get('core_tasks', []))}个任务, "
            f"{len(context.get('gap_filling_raw', {}))}个补充信息, "
            f"{len(context.get('dimensions', []))}个维度"
        )

        # Phase B: 单次LLM综合分析
        if use_llm:
            try:
                result = RequirementsRestructuringEngine._llm_synthesize_insight(context)
                if RequirementsRestructuringEngine._validate_synthesis_result(result):
                    doc = RequirementsRestructuringEngine._format_synthesis_output(result, context)
                    logger.info("✅ [Phase B] LLM综合分析完成")
                    logger.info(f"   - 项目本质: {doc.get('project_essence', '')[:50]}...")
                    logger.info(f"   - 项目目标: {doc.get('project_objectives', {}).get('primary_goal', '')[:50]}...")
                    logger.info(f"   - 设计重点: {len(doc.get('design_priorities', []))} 个维度")
                    logger.info(f"   - 约束条件: {len(doc.get('constraints', {}))} 项")
                    logger.info(f"   - 风险识别: {len(doc.get('identified_risks', []))} 项")
                    return doc
                else:
                    logger.warning("⚠️ [Phase B] LLM输出校验失败，降级为规则提取")
            except Exception as e:
                logger.warning(f"⚠️ [Phase B] LLM综合分析失败: {e}，降级为规则提取")

        # Fallback: 规则降级（复用现有逻辑）
        logger.info("🔄 [Fallback] 使用规则降级方案")
        return RequirementsRestructuringEngine._rule_based_fallback(
            questionnaire_data, ai_analysis, analysis_layers, user_input, weight_interpretations
        )

    # ==================== v3.0: Phase A - 数据准备 ====================

    DIMENSION_TASK_KEYWORDS: "Dict[str, List[str]]" = {
        "functionality": ["功能", "使用", "动线", "收纳", "布局", "分区", "空间"],
        "aesthetics": ["美学", "风格", "视觉", "色彩", "材质", "造型", "氛围"],
        "cost": ["预算", "成本", "造价", "资金", "费用"],
        "cost_control": ["预算", "成本", "造价", "资金", "费用"],
        "timeline": ["工期", "时间", "进度", "交付", "工程"],
        "sustainability": ["可持续", "环保", "节能", "绿色", "低碳"],
        "innovation": ["创新", "智能", "科技", "前沿", "数字"],
        "quality": ["品质", "质量", "精细", "工艺", "细节"],
        "cultural_authenticity": ["文化", "传统", "在地", "历史", "民族"],
        "spatial_atmosphere": ["氛围", "空间感", "光影", "情绪", "体验"],
        "emotional_resonance": ["情感", "共鸣", "归属", "记忆", "温度"],
    }

    @staticmethod
    def _fallback_deep_insights(
        user_input: str, questionnaire_data: Dict[str, Any], objectives: Dict[str, Any], constraints: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
         v7.152: 降级策略 - 基于规则生成基础洞察
        当LLM调用失败时，使用规则提取基础信息
        """
        logger.info(" [v7.152] 使用降级策略生成基础洞察")

        # 从用户输入中提取关键词
        primary_goal = objectives.get("primary_goal", "") if objectives else ""

        # 生成基础项目本质
        if primary_goal:
            project_essence = f"实现{primary_goal[:50]}，满足用户的核心需求期望"
        elif user_input:
            first_sentence = user_input.split("。")[0][:80]
            project_essence = f"基于用户表达'{first_sentence}'，打造符合期望的设计方案"
        else:
            project_essence = "待深入分析用户需求，明确项目核心价值"

        # 基础隐性需求（通用）
        implicit_requirements = [
            {"requirement": "空间的舒适度和宜居性", "evidence": "任何室内设计项目的基本诉求", "priority": "high"},
            {"requirement": "设计方案的可落地性", "evidence": "从预算和时间约束推断", "priority": "medium"},
        ]

        # 基础冲突检测
        key_conflicts = []
        if "budget" in constraints and primary_goal and len(primary_goal) > 30:
            key_conflicts.append(
                {
                    "conflict": "预算控制 vs 设计品质",
                    "sides": ["有限的预算约束", "对设计品质的追求"],
                    "recommended_approach": "通过优化材料选择和施工工艺，在预算范围内最大化设计效果",
                    "trade_off": "可能需要在部分非核心区域简化设计",
                }
            )

        if "timeline" in constraints:
            timeline_text = constraints["timeline"].get("duration", "").lower()
            if any(word in timeline_text for word in ["紧急", "加急", "1个月", "2周", "急"]):
                key_conflicts.append(
                    {
                        "conflict": "时间紧迫 vs 设计深度",
                        "sides": ["紧迫的交付时间", "深入思考的设计需求"],
                        "recommended_approach": "聚焦核心功能区域，分阶段实施非紧急设计元素",
                        "trade_off": "初期方案可能需要后续优化迭代",
                    }
                )

        return {
            "project_essence": project_essence,
            "implicit_requirements": implicit_requirements,
            "key_conflicts": key_conflicts,
        }
