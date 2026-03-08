"""
纯文本报告生成器 - 用于调试和查看完整数据结构
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore
from loguru import logger

from ..agents.base import BaseAgent
from ..core.state import AgentType, ProjectAnalysisState
from ..core.types import AnalysisResult


class TextGeneratorAgent(BaseAgent):
    """纯文本报告生成器智能体"""
    
    def __init__(self, config: Dict[str, Any] | None = None):
        super().__init__(
            agent_type=AgentType.PDF_GENERATOR,  # 复用相同类型
            name="纯文本报告生成器",
            description="生成纯文本格式的项目分析报告,用于调试",
            config=config
        )
    
    def validate_input(self, state: ProjectAnalysisState) -> bool:
        """验证输入状态"""
        return "final_report" in state and state["final_report"] is not None
    
    def execute(
        self,
        state: ProjectAnalysisState,
        config: RunnableConfig,
        store: BaseStore | None = None
    ) -> AnalysisResult:
        """执行纯文本报告生成"""
        try:
            logger.info(f"Starting text report generation for session {state.get('session_id')}")
            
            # 验证输入（如果没有 final_report，尝试使用审核结果生成简化报告）
            if not self.validate_input(state):
                logger.warning("️ final_report 不存在，尝试使用审核结果生成简化报告")
                text_path = self._generate_fallback_report(state)
            else:
                # 生成完整纯文本报告
                text_path = self._generate_text_report(state)
            
            # 创建分析结果
            result = AnalysisResult(
                agent_type=self.agent_type,
                content=f"纯文本报告已生成: {text_path}",
                structured_data={
                    "file_path": text_path,
                    "file_size": os.path.getsize(text_path) if os.path.exists(text_path) else 0
                },
                confidence=1.0,
                sources=["final_report"]
            )
            
            logger.info(f"Text report generation completed: {text_path}")
            return result
            
        except Exception as e:
            error = self.handle_error(e, "Text report generation")
            raise error
    
    def _generate_text_report(self, state: ProjectAnalysisState) -> str:
        """生成纯文本报告"""
        final_report = state.get("final_report", {})
        session_id = state.get("session_id", "unknown")
        strategic_analysis = state.get("strategic_analysis") or {}  #  修复：确保不为 None

        #  获取角色信息（包含动态名称）
        selected_roles = strategic_analysis.get("selected_roles", []) if isinstance(strategic_analysis, dict) else []
        role_map = {}  # {完整角色ID: 动态名称}
        
        for role in selected_roles:
            if isinstance(role, dict):
                role_id = role.get("role_id", "")
                dynamic_name = role.get("dynamic_role_name", "")
                # 构造完整ID
                if role_id and not role_id.count("_") >= 2:
                    # 短ID，需要构造完整ID
                    if role_id.startswith("2-"):
                        full_id = f"V2_设计总监_{role_id}"
                    elif role_id.startswith("3-"):
                        full_id = f"V3_叙事与体验专家_{role_id}"
                    elif role_id.startswith("4-"):
                        full_id = f"V4_设计研究员_{role_id}"
                    elif role_id.startswith("5-"):
                        full_id = f"V5_场景与行业专家_{role_id}"
                    elif role_id.startswith("6-"):
                        full_id = f"V6_专业总工程师_{role_id}"
                    else:
                        full_id = role_id
                else:
                    full_id = role_id
                
                role_map[full_id] = dynamic_name
        
        logger.info(f" 构建角色映射: {len(role_map)} 个动态角色")
        
        # 创建报告目录
        report_dir = "./reports"
        os.makedirs(report_dir, exist_ok=True)
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        text_path = os.path.join(report_dir, f"project_analysis_{session_id}_{timestamp}.txt")
        
        # 生成报告内容
        lines = []
        
        # 标题
        lines.append("=" * 80)
        lines.append("智能项目分析报告 (调试版本)")
        lines.append("=" * 80)
        lines.append("")
        
        # 元数据
        metadata = final_report.get("metadata", {})
        lines.append("## 元数据")
        lines.append(f"生成时间: {metadata.get('generated_at', 'N/A')}")
        lines.append(f"会话ID: {metadata.get('session_id', 'N/A')}")
        lines.append(f"智能体数量: {metadata.get('total_agents', 'N/A')}")
        lines.append(f"整体置信度: {metadata.get('overall_confidence', 'N/A')}")
        lines.append("")
        
        # 执行摘要
        lines.append("=" * 80)
        lines.append("1. 执行摘要")
        lines.append("=" * 80)
        
        #  修复v4.0: 如果没有 executive_summary 或内容为空，从其他字段合成
        executive_summary = final_report.get("executive_summary", {})
        if not executive_summary or executive_summary.get("project_overview") in [None, "N/A", ""]:
            # 从 core_answer、insights、recommendations 合成
            core_answer = final_report.get("core_answer", {})
            insights = final_report.get("insights", {})
            recommendations = final_report.get("recommendations", {})
            
            # 构建合成的执行摘要
            project_overview = (
                core_answer.get("answer") or 
                core_answer.get("question") or 
                insights.get("user_needs_interpretation") or
                "N/A"
            )
            key_findings = (
                insights.get("key_insights", [])[:5] 
                if isinstance(insights, dict) else []
            )
            key_recommendations = (
                recommendations.get("immediate_actions", [])[:3] 
                if isinstance(recommendations, dict) else []
            )
            success_factors = (
                insights.get("cross_domain_connections", []) 
                if isinstance(insights, dict) else []
            )
            
            executive_summary = {
                "project_overview": project_overview,
                "key_findings": key_findings,
                "key_recommendations": key_recommendations,
                "success_factors": success_factors
            }
            logger.info(" 从 core_answer/insights/recommendations 合成了 executive_summary")
        
        lines.append(f"\n项目概述:\n{executive_summary.get('project_overview', 'N/A')}\n")
        
        lines.append("关键发现:")
        for finding in executive_summary.get("key_findings", []):
            lines.append(f"  • {finding}")
        lines.append("")
        
        lines.append("关键建议:")
        for rec in executive_summary.get("key_recommendations", []):
            lines.append(f"  • {rec}")
        lines.append("")
        
        lines.append("成功要素:")
        for factor in executive_summary.get("success_factors", []):
            lines.append(f"  • {factor}")
        lines.append("")
        
        # 各个分析章节 -  按角色组织
        sections = final_report.get("sections", [])
        agent_results = state.get("agent_results", {})
        
        # 按角色ID分组章节
        role_sections = {}  # {完整角色ID: section}
        
        # 如果sections是列表格式
        if isinstance(sections, list):
            for section in sections:
                section_id = section.get("section_id", "")
                # 尝试从agent_results中找到对应的角色ID
                for agent_id, agent_result in agent_results.items():
                    if isinstance(agent_result, dict):
                        # 检查section_id是否匹配
                        if section_id in str(agent_result):
                            role_sections[agent_id] = section
                            break
        # 如果sections是字典格式（旧格式兼容）
        elif isinstance(sections, dict):
            for section_id, section_data in sections.items():
                for agent_id in agent_results.keys():
                    if section_id in agent_id or agent_id in section_id:
                        role_sections[agent_id] = section_data
                        break
        
        # 如果没有找到映射，直接按agent_results遍历
        if not role_sections:
            for agent_id in agent_results.keys():
                if agent_id not in ["requirements_analyst", "project_director"]:
                    role_sections[agent_id] = None
        
        lines.append("=" * 80)
        lines.append("2. 专家分析报告（按角色组织）")
        lines.append("=" * 80)
        lines.append("")
        
        # 遍历所有角色，按角色展示
        section_idx = 2
        for agent_id in sorted(role_sections.keys()):
            section_idx += 1
            
            # 获取动态名称
            dynamic_name = role_map.get(agent_id, "")
            static_name = agent_id
            
            # 标题格式：静态名称 (动态名称)
            if dynamic_name:
                title = f"{static_name} ({dynamic_name})"
            else:
                title = static_name
            
            lines.append("=" * 80)
            lines.append(f"{section_idx}. {title}")
            lines.append("=" * 80)
            
            # 获取该角色的分析结果
            agent_result = agent_results.get(agent_id, {})
            if isinstance(agent_result, dict):
                confidence = agent_result.get("confidence", 0)
                lines.append(f"置信度: {confidence:.2f}")
                lines.append("")
                
                # 获取内容
                content = agent_result.get("content", "")
                structured_data = agent_result.get("structured_data", {})
                
                if content:
                    lines.append("### 分析内容")
                    lines.append(content)
                    lines.append("")
                
                if structured_data:
                    lines.append("### 结构化数据")
                    lines.append(json.dumps(structured_data, ensure_ascii=False, indent=2))
                    lines.append("")
            else:
                lines.append("(无数据)")
                lines.append("")

        # 遍历sections列表（如果是新格式）
        if isinstance(sections, list):
            lines.append("=" * 80)
            lines.append(f"{section_idx + 1}. 补充章节（LLM生成）")
            lines.append("=" * 80)
            lines.append("")
            
            for idx, section in enumerate(sections, start=1):
                section_id = section.get("section_id", "unknown")
                title = section.get("title", "未知章节")
                content = section.get("content", "")
                confidence = section.get("confidence", 0)

                lines.append("-" * 40)
                lines.append(f"{idx}. {title} (ID: {section_id})")
                lines.append("-" * 40)
                lines.append(f"置信度: {confidence:.2f}")
                lines.append("")

                if content:
                    lines.append(content)
                    lines.append("")
                else:
                    lines.append("(无内容)")
                    lines.append("")
        
        # 综合分析
        lines.append("=" * 80)
        lines.append("8. 综合分析")
        lines.append("=" * 80)
        comprehensive_analysis = final_report.get("comprehensive_analysis", {})
        lines.append(json.dumps(comprehensive_analysis, ensure_ascii=False, indent=2))
        lines.append("")
        
        # 结论和建议
        lines.append("=" * 80)
        lines.append("9. 结论和建议")
        lines.append("=" * 80)
        conclusions = final_report.get("conclusions", {})
        lines.append(json.dumps(conclusions, ensure_ascii=False, indent=2))
        lines.append("")
        
        # 原始内容
        lines.append("=" * 80)
        lines.append("原始LLM响应")
        lines.append("=" * 80)
        raw_content = final_report.get("raw_content", "N/A")
        lines.append(raw_content)
        lines.append("")
        
        # 完整数据结构
        lines.append("=" * 80)
        lines.append("完整 final_report 数据结构")
        lines.append("=" * 80)
        lines.append(json.dumps(final_report, ensure_ascii=False, indent=2))
        
        # 写入文件
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        logger.info(f"Text report saved to: {text_path}")
        return text_path
    
    def _generate_fallback_report(self, state: ProjectAnalysisState) -> str:
        """
        生成后备简化报告（当 final_report 不存在时）
        使用审核结果和原始分析结果生成
        """
        session_id = state.get("session_id", "unknown")
        report_dir = Path("reports")
        report_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        text_path = str(report_dir / f"{session_id}_{timestamp}_fallback.txt")
        
        lines = []
        lines.append("=" * 80)
        lines.append("智能项目分析报告（简化版）")
        lines.append("=" * 80)
        lines.append(f"会话ID: {session_id}")
        lines.append(f"生成时间: {timestamp}")
        lines.append("")
        
        # ️ ST-1: review_result / improvement_suggestions 字段已在 v2.2 废弃
        # analysis_review 节点已删除，这两个字段永远不会被 state 赋值，块已移除。
        
        lines.append("=" * 80)
        lines.append("注：由于流程异常，本报告为简化版本")
        lines.append("=" * 80)
        
        # 写入文件
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        logger.info(f"Fallback report saved to: {text_path}")
        return text_path

