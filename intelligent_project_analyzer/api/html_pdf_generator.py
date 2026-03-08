"""
HTML to PDF Generator using Playwright

使用浏览器引擎生成高质量 PDF，完美支持中文排版

v7.1.2 优化：
- 浏览器池单例模式，避免每次冷启动（性能提升 60-70%）
- 优化 wait_until 策略（domcontentloaded vs networkidle）
- 支持服务器生命周期管理
"""

import asyncio
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader
from loguru import logger
from playwright.async_api import Browser, Playwright, async_playwright

# ============================================================
#  v7.1.2: Playwright 浏览器池单例
# ============================================================


from ._browser_pool import PlaywrightBrowserPool, get_browser_pool
from ._pdf_text_mixin import PDFTextMixin
from ._pdf_parse_mixin import PDFParseMixin


class HTMLPDFGenerator(PDFTextMixin, PDFParseMixin):
    """基于 HTML + Playwright 的 PDF 生成器"""

    # 字段标签中英文映射
    FIELD_LABELS = {
        # 通用字段
        "name": "名称",
        "title": "标题",
        "description": "描述",
        "content": "内容",
        "summary": "总结",
        "conclusion": "结论",
        "recommendation": "建议",
        "recommendations": "建议",
        "analysis": "分析",
        "overview": "概述",
        "background": "背景",
        "objective": "目标",
        "objectives": "目标",
        "goal": "目标",
        "goals": "目标",
        "result": "结果",
        "results": "结果",
        "finding": "发现",
        "findings": "发现",
        "insight": "洞察",
        "insights": "洞察",
        "key_points": "要点",
        "keypoints": "要点",
        "highlights": "亮点",
        "notes": "备注",
        "comments": "评论",
        "feedback": "反馈",
        # 用户研究相关
        "persona": "用户画像",
        "personas": "用户画像",
        "user_persona": "用户画像",
        "pain_points": "痛点",
        "painpoints": "痛点",
        "pain points": "痛点",
        "needs": "需求",
        "user_needs": "用户需求",
        "behaviors": "行为",
        "user_behaviors": "用户行为",
        "motivations": "动机",
        "frustrations": "挫败点",
        "goals_and_needs": "目标与需求",
        "how_might_we": "我们如何能够",
        "hmw": "我们如何能够",
        "journey": "旅程",
        "user_journey": "用户旅程",
        "touchpoints": "触点",
        "scenarios": "场景",
        "use_cases": "用例",
        # 商业相关
        "market": "市场",
        "market_analysis": "市场分析",
        "competition": "竞争",
        "competitors": "竞争对手",
        "competitive_analysis": "竞争分析",
        "swot": "SWOT分析",
        "strengths": "优势",
        "weaknesses": "劣势",
        "opportunities": "机会",
        "threats": "威胁",
        "strategy": "策略",
        "strategies": "策略",
        "business_model": "商业模式",
        "value_proposition": "价值主张",
        "revenue": "收入",
        "cost": "成本",
        "pricing": "定价",
        "roi": "投资回报率",
        # 技术相关
        "architecture": "架构",
        "technology": "技术",
        "tech_stack": "技术栈",
        "implementation": "实现",
        "requirements": "需求",
        "specifications": "规格",
        "features": "功能",
        "feature": "功能",
        "modules": "模块",
        "components": "组件",
        "api": "接口",
        "database": "数据库",
        "security": "安全",
        "performance": "性能",
        "scalability": "可扩展性",
        # 项目管理
        "timeline": "时间线",
        "milestones": "里程碑",
        "deliverables": "交付物",
        "resources": "资源",
        "risks": "风险",
        "risk_assessment": "风险评估",
        "mitigation": "缓解措施",
        "dependencies": "依赖",
        "constraints": "约束",
        "assumptions": "假设",
        "budget": "预算",
        "schedule": "进度",
        "status": "状态",
        "progress": "进展",
        "priority": "优先级",
        # 设计相关
        "design": "设计",
        "wireframe": "线框图",
        "prototype": "原型",
        "mockup": "效果图",
        "layout": "布局",
        "color": "颜色",
        "typography": "字体",
        "branding": "品牌",
        "style": "风格",
        "theme": "主题",
        "ui": "用户界面",
        "ux": "用户体验",
        "interaction": "交互",
        "animation": "动画",
        "responsive": "响应式",
        "accessibility": "无障碍",
        # 红蓝对抗相关
        "pole_a": "立场A",
        "pole_b": "立场B",
        "pole_a_analysis": "立场A分析",
        "pole_b_analysis": "立场B分析",
        "pole_a_resolve": "立场A解决方案",
        "pole_b_resolve": "立场B解决方案",
        "debate": "辩论",
        "argument": "论点",
        "counter_argument": "反驳",
        "synthesis": "综合",
        "verdict": "裁决",
        "judge_verdict": "评委裁决",
        # 其他
        "introduction": "引言",
        "methodology": "方法论",
        "approach": "方法",
        "process": "流程",
        "workflow": "工作流",
        "steps": "步骤",
        "phase": "阶段",
        "phases": "阶段",
        "stage": "阶段",
        "stages": "阶段",
        "action_items": "行动项",
        "next_steps": "下一步",
        "appendix": "附录",
        "references": "参考",
        "glossary": "术语表",
        "faq": "常见问题",
        # 项目特定字段
        "project_vision_summary": "项目愿景摘要",
        "design_rationale": "设计理据",
        "decision_rationale": "决策理据",
        "spatial_concept": "空间概念",
        "customer_journey_design": "客户旅程设计",
        "critical_questions_responses": "关键问题回应",
        "chosen_design_stance": "设计立场选择",
        "expert_handoff_response": "专家交接回应",
        "healing_environment_kpis": "治愈环境KPI",
        "technical_requirements_for_v6": "V6技术要求",
        "challenge_flags": "挑战标记",
        "confidence": "置信度",
        # 业务与运营分析
        "business_goal_analysis": "商业目标分析",
        "operational_blueprint": "运营蓝图",
        "custom_analysis": "自定义分析",
        "missing_inputs_warning": "缺失输入警告",
        "missing_keys": "缺失字段",
        "impact": "影响",
        "business_model_analysis": "商业模式分析",
        "revenue_model": "盈利模式",
        "cost_structure": "成本结构",
        "value_chain": "价值链",
        # 空间与设计
        "space_planning_strategy": "空间规划策略",
        "functional_zoning": "功能分区",
        "traffic_flow": "动线设计",
        "spatial_hierarchy": "空间层次",
        "material_palette": "材料选板",
        "lighting_strategy": "照明策略",
        "acoustic_design": "声学设计",
        "environmental_control": "环境控制",
        # 用户体验
        "user_experience_design": "用户体验设计",
        "touchpoint_design": "触点设计",
        "service_blueprint": "服务蓝图",
        "emotional_journey": "情感旅程",
        "pain_point_solutions": "痛点解决方案",
        # 技术与实施
        "technical_specifications": "技术规格",
        "implementation_roadmap": "实施路线图",
        "quality_standards": "质量标准",
        "compliance_requirements": "合规要求",
        "sustainability_measures": "可持续措施",
        # 风险与挑战
        "risk_analysis": "风险分析",
        "challenge_response": "挑战应对",
        "mitigation_strategies": "缓解策略",
        "contingency_plans": "应急预案",
        # KPI与指标
        "key_performance_indicators": "关键绩效指标",
        "kpi": "关键绩效指标",
        "kpis": "关键绩效指标",
        "metric": "指标",
        "metrics": "指标",
        "target": "目标值",
        "targets": "目标值",
        "benchmark": "基准",
        "benchmarks": "基准",
        # 设计挑战
        "design_challenges": "设计挑战",
        "design_challenges_for_v2": "设计挑战（V2专用）",
        "challenge": "挑战",
        "challenges": "挑战",
        "constraint": "约束",
        "context": "背景",
        # 空间策略
        "spatial_strategy": "空间策略",
        "spatial_strategies": "空间策略",
        "space_strategy": "空间策略",
        # 品牌与视觉
        "brand_identity_integration": "品牌识别整合",
        "brand_identity": "品牌识别",
        "brand_integration": "品牌整合",
        "visual_merchandising": "视觉营销",
        "visualmerchandising": "视觉营销",
        "visual_identity": "视觉识别",
        # 实施指导
        "implementation_guidance": "实施指导",
        "guidance": "指导",
        "execution": "执行",
        "execution_plan": "执行计划",
        # 解释框架
        "interpretation_framework": "解释框架",
        "framework": "框架",
        # 初始场景
        "initial_key_scenario": "初始关键场景",
        "key_scenario": "关键场景",
        "scenario": "场景",
        # MEP与工程
        "mepoverall": "MEP总体",
        "mep_overall": "MEP总体",
        "mep_strategy": "MEP策略",
        "mep": "机电",
        "hvac": "暖通空调",
        "electrical": "电气",
        "plumbing": "给排水",
        "fire_protection": "消防",
        "system_solutions": "系统解决方案",
        "system": "系统",
        "systems": "系统",
        "recommended_solution": "推荐方案",
        "reasoning": "理由",
        "reason": "理由",
        # 工艺与材料
        "craftsmanship": "工艺",
        "craftsmanship_strategy": "工艺策略",
        "keymaterial": "关键材料",
        "key_material": "关键材料",
        "material": "材料",
        "materials": "材料",
        "application_area": "应用区域",
        "application": "应用",
        # 影响与架构
        "impact_on_architecture": "对架构的影响",
        "architecture_impact": "架构影响",
        "on": "",
        # 旅程与地图
        "journey_maps": "旅程地图",
        "journeymaps": "旅程地图",
        "maps": "地图",
        # 设计模式与复用
        "reusable": "可复用",
        "reusable_design_patterns": "可复用设计模式",
        "design_patterns": "设计模式",
        "designpatterns": "设计模式",
        "patterns": "模式",
        "pattern": "模式",
        # 团队指南
        "guidelines_for_team": "团队指南",
        "guidelinesforteam": "团队指南",
        "guidelines": "指南",
        "guideline": "指南",
        "team": "团队",
        # 成功因素
        "key_success_factors": "关键成功因素",
        "success_factors": "成功因素",
        "success": "成功",
        "factors": "因素",
        # 灵感与大师作品
        "missing_inspiration_warning": "缺失灵感警告",
        "inspiration": "灵感",
        "master_work_deconstruction": "大师作品解构",
        "master": "大师",
        "deconstruction": "解构",
        "nendo": "Nendo",
        "desc": "描述",
        "philosophy": "理念",
        "signature_methods": "标志性方法",
        "application_to_project": "项目应用",
        "applicationtoproject": "项目应用",
        # 品牌
        "brand": "品牌",
        "brands": "品牌",
        # 优势劣势
        "advantage": "优势",
        "advantages": "优势",
        "disadvantage": "劣势",
        "disadvantages": "劣势",
        # 常见英文标题
        "key_findings": "关键发现",
        "main_points": "主要要点",
        "action_plan": "行动计划",
        "implementation_plan": "实施计划",
        "space_planning": "空间规划",
        "material_selection": "材料选择",
        "lighting_design": "照明设计",
        "color_scheme": "配色方案",
        "furniture_layout": "家具布局",
        "cost_estimate": "成本估算",
        "timeline_estimate": "时间线估算",
        "type": "类型",
        "area": "区域",
        "spec": "规格",
        "specs": "规格",
        "specification": "规格",
        # ============ 任务导向模型字段 (task_oriented_models.py) ============
        # DeliverableOutput 交付物输出
        "deliverable_name": "交付物名称",
        "deliverable_outputs": "交付物输出",
        "completion_status": "完成状态",
        "completion_rate": "完成度",
        "quality_self_assessment": "质量自评",
        # TaskExecutionReport 任务执行报告
        "task_execution_report": "任务执行报告",
        "task_completion_summary": "任务完成总结",
        "additional_insights": "额外洞察",
        "execution_challenges": "执行挑战",
        # ProtocolExecutionReport 协议执行报告
        "protocol_execution": "协议执行报告",
        "protocol_status": "协议状态",
        "compliance_confirmation": "合规确认",
        "challenge_details": "挑战详情",
        "reinterpretation": "重新诠释",
        # ChallengeFlag 挑战标记
        "challenged_item": "被挑战内容",
        "challenge_reason": "挑战理由",
        "alternative_proposal": "替代方案",
        # ReinterpretationDetail 重新诠释详情
        "original_interpretation": "原始诠释",
        "new_interpretation": "新诠释",
        "reinterpretation_rationale": "诠释依据",
        "impact_on_approach": "方法论影响",
        # ExecutionMetadata 执行元数据
        "execution_metadata": "执行元数据",
        "execution_time_estimate": "执行时间估算",
        "execution_notes": "执行备注",
        "dependencies_satisfied": "依赖满足",
        # TaskInstruction 任务指令
        "success_criteria": "成功标准",
        "context_requirements": "上下文需求",
        # DeliverableSpec 交付物规格
        "format": "格式",
        # 协议状态枚举值
        "complied": "已遵照",
        "challenged": "已挑战",
        "reinterpreted": "已重新诠释",
        # 完成状态枚举值
        "completed": "已完成",
        "partial": "部分完成",
        "unable": "无法完成",
        # ============ V2-V6 FlexibleOutput 专家模型字段 ============
        # 通用字段
        "output_mode": "输出模式",
        "user_question_focus": "问题聚焦",
        "targeted_analysis": "针对性分析",
        "supplementary_insights": "补充洞察",
        # V6-1 结构与幕墙工程师
        "feasibility_assessment": "可行性评估",
        "structural_system_options": "结构体系选项",
        "facade_system_options": "幕墙体系选项",
        "key_technical_nodes": "关键技术节点",
        "risk_analysis_and_recommendations": "风险分析与建议",
        "option_name": "方案名称",
        "estimated_cost_level": "预估造价等级",
        "node_name": "节点名称",
        "proposed_solution": "建议方案",
        # V6-2 机电与智能化工程师
        "mep_overall_strategy": "机电整体策略",
        "smart_building_scenarios": "智能建筑场景",
        "coordination_and_clash_points": "协调与冲突点",
        "sustainability_and_energy_saving": "可持续与节能",
        "system_name": "系统名称",
        "scenario_name": "场景名称",
        "triggered_systems": "联动系统",
        # V6-3 室内工艺与材料专家
        "key_material_specifications": "关键材料规格",
        "critical_node_details": "关键节点详图",
        "quality_control_and_mockup": "质量控制与样板",
        "material_name": "材料名称",
        "key_specifications": "关键规格",
        # V6-4 成本与价值工程师
        "cost_estimation_summary": "成本估算摘要",
        "cost_breakdown_analysis": "成本构成分析",
        "value_engineering_options": "价值工程选项",
        "budget_control_strategy": "预算控制策略",
        "cost_overrun_risk_analysis": "成本超支风险分析",
        "category": "类别",
        "percentage": "百分比",
        "cost_drivers": "成本驱动因素",
        "original_scheme": "原方案",
        "proposed_option": "优化方案",
        "impact_analysis": "影响分析",
        # V5-1 居住场景与生活方式专家
        "family_profile_and_needs": "家庭成员画像与需求",
        "member": "成员",
        "daily_routine": "日常作息",
        "spatial_needs": "空间需求",
        "storage_needs": "收纳需求",
        # V5-2 商业零售运营专家
        # V5-3 企业办公策略专家
        "organizational_analysis": "组织分析",
        "collaboration_model": "协作模式",
        "workspace_strategy": "工作空间策略",
        # V5-4 酒店餐饮运营专家
        "service_process_analysis": "服务流程分析",
        "operational_efficiency": "运营效率",
        "guest_experience_blueprint": "宾客体验蓝图",
        # V5-5 文化教育场景专家
        "visitor_journey_analysis": "访客旅程分析",
        "educational_model": "教育模式",
        "public_service_strategy": "公共服务策略",
        # V5-6 医疗康养场景专家
        "healthcare_process_analysis": "医疗流程分析",
        "patient_experience_blueprint": "患者体验蓝图",
        "wellness_strategy": "康养策略",
        # V2系列 设计总监
        "visual_merchandising_strategy": "视觉营销策略",
        "architectural_concept": "建筑概念",
        "facade_and_envelope": "立面与围护",
        "landscape_integration": "景观整合",
        "indoor_outdoor_relationship": "室内外关系",
        "public_vision": "公共愿景",
        "spatial_accessibility": "空间可达性",
        "community_engagement": "社区参与",
        "cultural_expression": "文化表达",
        # V3系列 叙事与体验专家
        "narrative_framework": "叙事框架",
        # V4系列 设计研究专员
        "case_studies_deep_dive": "深度案例研究",
        "application_guidelines_for_team": "团队应用指南",
        "trend_analysis": "趋势分析",
        "future_scenarios": "未来场景",
        "opportunity_identification": "机会识别",
        "design_implications": "设计启示",
    }

    # 内容翻译映射
    CONTENT_TRANSLATIONS = {
        "How might we": "我们如何能够",
        "Pain Points": "痛点",
        "Pain points": "痛点",
        "Persona:": "用户画像:",
        "Persona：": "用户画像：",
        "User Persona": "用户画像",
        "Key Insights": "关键洞察",
        "Key insights": "关键洞察",
        "Recommendations": "建议",
        "Summary": "总结",
        "Conclusion": "结论",
        "Overview": "概述",
        "Background": "背景",
        "Analysis": "分析",
        "pole_a": "立场A",
        "pole_b": "立场B",
        "pole_a_resolve": "立场A解决方案",
        "pole_b_resolve": "立场B解决方案",
        "Pole A": "立场A",
        "Pole B": "立场B",
        # 品牌与视觉标题
        "Brand Identity Integration": "品牌识别整合",
        "Brand Identity": "品牌识别",
        "Visual Merchandising": "视觉营销",
        "Visual Identity": "视觉识别",
        # 实施相关
        "Implementation Guidance": "实施指导",
        "Implementation Plan": "实施计划",
        "Execution Plan": "执行计划",
        # 设计相关
        "Design Rationale": "设计理据",
        "Design Challenges": "设计挑战",
        "Spatial Strategy": "空间策略",
        "Space Planning": "空间规划",
        # 其他常见标题
        "Key Performance Indicators": "关键绩效指标",
        "Key Findings": "关键发现",
        "Key Success Factors": "关键成功因素",
        "Action Items": "行动项",
        "Next Steps": "下一步",
        "Risk Analysis": "风险分析",
        "Quality Standards": "质量标准",
        "Master Work Deconstruction Nendo": "大师作品解构 Nendo",
        "Missing Inspiration Warning": "缺失灵感警告",
        "Case Studies Deep Dive": "案例深度研究",
        "Case Studies": "案例研究",
        "Key Takeaways": "关键要点",
        # MEP与工程系统
        "System Solutions": "系统解决方案",
        "Recommended Solution": "推荐方案",
        "Reasoning": "理由",
        "Application Area": "应用区域",
        # 混合中英文格式修正 - 扩展列表
        "mepoverall策略": "MEP总体策略",
        "craftsmanship策略": "工艺策略",
        "keymaterial规格": "关键材料规格",
        "visualmerchandising策略": "视觉营销策略",
        "visualmerchandising": "视觉营销",
        "visual merchandising": "视觉营销",
        "实现guidance": "实施指导",
        "system名称": "系统名称",
        "material名称": "材料名称",
        "key规格": "关键规格",
        "影响on架构": "对架构的影响",
        "reusable设计patterns": "可复用设计模式",
        "应用guidelinesforteam": "团队应用指南",
        "应用指南for团队": "团队应用指南",
        "for团队": "团队",
        "旅程maps": "旅程地图",
        "pattern名称": "模式名称",
        "journey maps": "旅程地图",
        "journeymaps": "旅程地图",
        "design patterns": "设计模式",
        "designpatterns": "设计模式",
        "guidelines for team": "团队指南",
        "guidelinesforteam": "团队指南",
        "大师work解构Nendo": "大师作品解构 Nendo",
        "work": "作品",
        # 新增常见英文词汇
        "for": "",  # 单独的 for 通常可以省略
        "team": "团队",
        "guidance": "指导",
        "guidelines": "指南",
        "strategy": "策略",
        "strategies": "策略",
        "analysis": "分析",
        "design": "设计",
        "system": "系统",
        "material": "材料",
        "materials": "材料",
        "pattern": "模式",
        "patterns": "模式",
        "journey": "旅程",
        "map": "地图",
        "maps": "地图",
        "key": "关键",
        "implementation": "实施",
        "execution": "执行",
        "plan": "计划",
        "recommendation": "建议",
        "solution": "解决方案",
        "solutions": "解决方案",
    }

    def __init__(self, template_dir: str | None = None):
        """初始化生成器

        Args:
            template_dir: 模板目录路径，默认使用内置模板
        """
        if template_dir is None:
            template_dir = Path(__file__).parent / "templates"

        self.template_dir = Path(template_dir)
        self.env = Environment(loader=FileSystemLoader(str(self.template_dir)), autoescape=True)
        # 添加自定义过滤器
        self.env.filters["nl2br"] = self._nl2br
        self.env.filters["markdown"] = self._simple_markdown

    @staticmethod
    def render_html(
        self,
        experts: List[Dict[str, Any]],
        title: str = "专家分析报告",
        subtitle: str | None = None,
        session_id: str | None = None,
        template_name: str = "expert_report.html",
    ) -> str:
        """渲染 HTML 内容

        Args:
            experts: 专家数据列表
            title: 报告标题
            subtitle: 副标题
            session_id: 会话 ID
            template_name: 模板文件名

        Returns:
            渲染后的 HTML 字符串
        """
        # 解析专家数据
        parsed_experts = [self.parse_expert_content(exp) for exp in experts]

        # 渲染模板
        template = self.env.get_template(template_name)
        html = template.render(
            title=title,
            subtitle=subtitle,
            session_id=session_id,
            generated_time=datetime.now().strftime("%Y年%m月%d日 %H:%M"),
            experts=parsed_experts,
        )

        return html

    async def generate_pdf_async(
        self,
        experts: List[Dict[str, Any]],
        output_path: str | None = None,
        title: str = "专家分析报告",
        subtitle: str | None = None,
        session_id: str | None = None,
        **pdf_options,
    ) -> bytes:
        """异步生成 PDF

         P1修复: 添加Playwright可用性检查与降级策略

        Args:
            experts: 专家数据列表
            output_path: 输出文件路径（可选）
            title: 报告标题
            subtitle: 副标题
            session_id: 会话 ID
            **pdf_options: 传递给 Playwright PDF 方法的参数

        Returns:
            PDF 字节数据

        Raises:
            RuntimeError: Playwright不可用且无降级选项
        """
        import time

        start_time = time.time()

        # 渲染 HTML
        html = self.render_html(experts, title, subtitle, session_id)
        html_time = time.time()
        logger.debug(f" HTML 渲染耗时: {html_time - start_time:.2f}s")

        #  P1修复: 检查浏览器池健康状态
        browser_pool = get_browser_pool()

        try:
            browser = await asyncio.wait_for(browser_pool.get_browser(), timeout=15.0)

            #  P1修复: 二次验证浏览器连接
            if browser is None or not browser.is_connected():
                raise RuntimeError("浏览器未初始化或连接已断开")

        except (asyncio.TimeoutError, RuntimeError, Exception) as browser_error:
            logger.error(f" 获取Playwright浏览器失败: {browser_error}")
            logger.warning("️ 正在尝试降级策略：返回HTML内容")

            #  P1修复: 降级到HTML
            # 返回HTML字节（前端可检测Content-Type并显示提示）
            logger.info(" 使用HTML降级模式代替PDF")
            return html.encode("utf-8")

        browser_time = time.time()
        logger.debug(f" 获取浏览器耗时: {browser_time - html_time:.2f}s")

        # 创建新的 context 和 page（context 比 browser 轻量很多）
        context = await browser.new_context()
        page = await context.new_page()

        try:
            #  v7.1.2: 优化等待策略
            # 使用 domcontentloaded 而非 networkidle
            # 因为 HTML 使用内嵌样式，无需等待外部资源
            await page.set_content(html, wait_until="domcontentloaded")
            content_time = time.time()
            logger.debug(f" 设置内容耗时: {content_time - browser_time:.2f}s")

            # PDF 默认选项
            default_options = {
                "format": "A4",
                "print_background": True,
                "margin": {"top": "20mm", "bottom": "25mm", "left": "15mm", "right": "15mm"},
                "display_header_footer": True,
                "header_template": "<div></div>",
                "footer_template": """
                    <div style="width: 100%; font-size: 9pt; color: #666; text-align: center; padding: 10px;">
                        <span class="pageNumber"></span> / <span class="totalPages"></span>
                    </div>
                """,
            }
            default_options.update(pdf_options)

            # 生成 PDF
            if output_path:
                default_options["path"] = output_path

            pdf_bytes = await page.pdf(**default_options)
            pdf_time = time.time()
            logger.debug(f" PDF 生成耗时: {pdf_time - content_time:.2f}s")

        finally:
            #  只关闭 context，不关闭 browser（复用）
            await context.close()

        total_time = time.time() - start_time
        logger.info(f" PDF 生成完成，总耗时: {total_time:.2f}s")

        return pdf_bytes

    async def generate_pdf_async_legacy(
        self,
        experts: List[Dict[str, Any]],
        output_path: str | None = None,
        title: str = "专家分析报告",
        subtitle: str | None = None,
        session_id: str | None = None,
        **pdf_options,
    ) -> bytes:
        """
        [废弃] 异步生成 PDF（旧版本，每次启动新浏览器）

        保留此方法作为备用，如果浏览器池出问题可以回退
        """
        html = self.render_html(experts, title, subtitle, session_id)

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.set_content(html, wait_until="networkidle")

            default_options = {
                "format": "A4",
                "print_background": True,
                "margin": {"top": "20mm", "bottom": "25mm", "left": "15mm", "right": "15mm"},
            }
            default_options.update(pdf_options)

            if output_path:
                default_options["path"] = output_path

            pdf_bytes = await page.pdf(**default_options)
            await browser.close()

        return pdf_bytes

    def generate_pdf(
        self,
        experts: List[Dict[str, Any]],
        output_path: str | None = None,
        title: str = "专家分析报告",
        subtitle: str | None = None,
        session_id: str | None = None,
        **pdf_options,
    ) -> bytes:
        """同步生成 PDF

        Args:
            experts: 专家数据列表
            output_path: 输出文件路径（可选）
            title: 报告标题
            subtitle: 副标题
            session_id: 会话 ID
            **pdf_options: 传递给 Playwright PDF 方法的参数

        Returns:
            PDF 字节数据
        """
        # 检查是否在已有事件循环中
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None:
            # 在已有事件循环中，使用 nest_asyncio 或新线程
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    self.generate_pdf_async(experts, output_path, title, subtitle, session_id, **pdf_options),
                )
                return future.result()
        else:
            # 没有事件循环，直接运行
            return asyncio.run(
                self.generate_pdf_async(experts, output_path, title, subtitle, session_id, **pdf_options)
            )


# 便捷函数
def generate_expert_report_pdf(
    experts: List[Dict[str, Any]],
    title: str = "专家分析报告",
    subtitle: str | None = None,
    session_id: str | None = None,
    output_path: str | None = None,
) -> bytes:
    """生成专家报告 PDF 的便捷函数

    Args:
        experts: 专家数据列表，每个专家包含:
            - expert_name/name: 专家名称
            - role/expert_role: 专家角色（可选）
            - content/analysis: 分析内容（字符串/字典/列表）
        title: 报告标题
        subtitle: 副标题（可选）
        session_id: 会话 ID（可选）
        output_path: 输出路径（可选）

    Returns:
        PDF 字节数据
    """
    generator = HTMLPDFGenerator()
    return generator.generate_pdf(
        experts=experts, title=title, subtitle=subtitle, session_id=session_id, output_path=output_path
    )


if __name__ == "__main__":
    # 测试代码
    test_experts = [
        {
            "expert_name": "用户研究专家",
            "role": "负责用户需求分析和用户画像构建",
            "content": {
                "persona": "目标用户为25-35岁的都市白领，注重生活品质，追求便捷高效。",
                "pain_points": ["现有方案流程繁琐，用户体验差", "缺乏个性化推荐", "价格不透明"],
                "how_might_we": "我们如何能够简化用户操作流程，同时提供个性化的服务体验？",
                "recommendations": "1. 优化注册流程 2. 增加智能推荐 3. 实现价格透明化",
            },
        },
        {
            "expert_name": "技术架构专家",
            "role": "负责系统架构设计和技术选型",
            "content": {
                "architecture": "采用微服务架构，前后端分离，支持水平扩展。",
                "tech_stack": {
                    "frontend": "React + TypeScript",
                    "backend": "Python FastAPI",
                    "database": "PostgreSQL + Redis",
                    "deployment": "Docker + Kubernetes",
                },
                "performance": "系统支持 10000 QPS，平均响应时间 < 100ms。",
            },
        },
    ]

    # 生成测试 PDF
    pdf_bytes = generate_expert_report_pdf(
        experts=test_experts,
        title="项目分析报告",
        subtitle="智能项目分析系统",
        session_id="test-001",
        output_path="test_html_pdf.pdf",
    )

    print(f"PDF 生成成功，大小: {len(pdf_bytes)} bytes")
