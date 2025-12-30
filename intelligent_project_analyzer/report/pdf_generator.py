"""
PDF报告生成器

使用ReportLab生成专业的PDF分析报告
"""

import os
import json
from typing import Dict, List, Optional, Any
import time
from datetime import datetime
from loguru import logger

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.platypus.flowables import HRFlowable
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.pdfbase.pdfmetrics import registerFontFamily
except ImportError:
    logger.warning("ReportLab library not installed. Please install with: pip install reportlab")
    SimpleDocTemplate = None

from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore

from ..agents.base import BaseAgent
from ..core.state import ProjectAnalysisState, AgentType, AnalysisStage
from ..core.types import AnalysisResult, ReportSection


class PDFGeneratorAgent(BaseAgent):
    """PDF报告生成器智能体"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(
            agent_type=AgentType.PDF_GENERATOR,
            name="PDF报告生成器",
            description="生成专业的PDF格式项目分析报告",
            config=config
        )

        if SimpleDocTemplate is None:
            raise ImportError("ReportLab library not installed. Please install with: pip install reportlab")

        # 注册中文字体
        self._register_chinese_fonts()

        # 初始化样式
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _register_chinese_fonts(self):
        """注册中文字体"""
        try:
            # 尝试注册Windows系统中文字体
            import platform
            system = platform.system()

            # 记录成功注册的字体名称
            registered_font = None

            if system == "Windows":
                # Windows系统字体路径 - 优先使用TTF文件而不是TTC
                font_paths = [
                    ('SimHei', 'C:/Windows/Fonts/simhei.ttf'),  # 黑体 (TTF)
                    ('SimSun', 'C:/Windows/Fonts/simsun.ttc'),  # 宋体 (TTC)
                ]
            elif system == "Darwin":  # macOS
                font_paths = [
                    ('PingFang', '/System/Library/Fonts/PingFang.ttc'),
                    ('STHeiti', '/System/Library/Fonts/STHeiti Light.ttc'),
                ]
            else:  # Linux
                font_paths = [
                    ('WenQuanYi', '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc'),
                ]

            # 尝试注册字体
            for font_name, font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont(font_name, font_path))
                        # 注册字体家族,将所有变体映射到同一个字体
                        # 这样可以避免 ReportLab 尝试查找不存在的 bold/italic 变体
                        pdfmetrics.registerFontFamily(
                            font_name,
                            normal=font_name,
                            bold=font_name,
                            italic=font_name,
                            boldItalic=font_name
                        )
                        logger.info(f"Successfully registered font and font family: {font_name}")
                        registered_font = font_name
                        # 注册成功后立即设置为默认字体并退出
                        self.default_font = font_name
                        break
                    except Exception as e:
                        logger.warning(f"Failed to register font {font_name}: {e}")
                        continue

            # 如果TTF字体都失败,尝试使用CID字体(Adobe内置)
            if not registered_font:
                try:
                    # 注册Adobe CID字体(不需要字体文件)
                    pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))  # 华文宋体
                    # CID字体也需要注册字体家族
                    pdfmetrics.registerFontFamily(
                        'STSong-Light',
                        normal='STSong-Light',
                        bold='STSong-Light',
                        italic='STSong-Light',
                        boldItalic='STSong-Light'
                    )
                    logger.info("Registered CID font and font family: STSong-Light")
                    # 设置默认字体为CID字体
                    self.default_font = 'STSong-Light'
                    registered_font = 'STSong-Light'
                except Exception as e:
                    logger.warning(f"Failed to register CID font: {e}")

            if not registered_font:
                logger.warning("No Chinese fonts registered, Chinese text may not display correctly")
                self.default_font = 'Helvetica'  # 回退到默认字体

        except Exception as e:
            logger.error(f"Error registering Chinese fonts: {e}")
            self.default_font = 'Helvetica'

    def validate_input(self, state: ProjectAnalysisState) -> bool:
        """验证输入是否有效"""
        return state.get("final_report") is not None

    def get_dependencies(self) -> List[AgentType]:
        """获取依赖的智能体"""
        return [AgentType.RESULT_AGGREGATOR]
    
    def _setup_custom_styles(self):
        """设置自定义样式"""
        # 获取默认字体
        font_name = getattr(self, 'default_font', 'Helvetica')

        # 定义样式列表
        custom_styles = [
            ('CustomTitle', {
                'parent': self.styles['Heading1'],
                'fontName': font_name,
                'fontSize': 24,
                'spaceAfter': 30,
                'alignment': TA_CENTER,
                'textColor': colors.darkblue
            }),
            ('SectionTitle', {
                'parent': self.styles['Heading2'],
                'fontName': font_name,
                'fontSize': 16,
                'spaceBefore': 20,
                'spaceAfter': 12,
                'textColor': colors.darkblue
            }),
            ('SubTitle', {
                'parent': self.styles['Heading3'],
                'fontName': font_name,
                'fontSize': 14,
                'spaceBefore': 15,
                'spaceAfter': 8,
                'textColor': colors.darkgreen
            }),
            ('CustomBodyText', {  # 改名避免冲突
                'parent': self.styles['Normal'],
                'fontName': font_name,
                'fontSize': 11,
                'spaceAfter': 8,
                'alignment': TA_JUSTIFY
            }),
            ('Highlight', {
                'parent': self.styles['Normal'],
                'fontName': font_name,
                'fontSize': 11,
                'textColor': colors.darkred,
                'spaceAfter': 8
            }),
            # 🆕 v7.64: 引用相关样式
            ('ReferenceText', {
                'parent': self.styles['Normal'],
                'fontName': font_name,
                'fontSize': 9,
                'textColor': colors.grey,
                'spaceAfter': 4,
                'leftIndent': 20
            }),
            ('ReferenceURL', {
                'parent': self.styles['Normal'],
                'fontName': font_name,
                'fontSize': 8,
                'textColor': colors.blue,
                'spaceAfter': 2,
                'leftIndent': 20
            }),
            ('ReferenceSnippet', {
                'parent': self.styles['Normal'],
                'fontName': font_name,
                'fontSize': 9,
                'textColor': colors.black,
                'spaceAfter': 8,
                'leftIndent': 30,
                'alignment': TA_JUSTIFY
            })
        ]

        # 添加样式，如果不存在的话
        for style_name, style_props in custom_styles:
            if style_name not in self.styles:
                self.styles.add(ParagraphStyle(name=style_name, **style_props))
    
    def execute(
        self,
        state: ProjectAnalysisState,
        config: RunnableConfig,
        store: Optional[BaseStore] = None
    ) -> AnalysisResult:
        """执行PDF生成"""
        start_time = time.time()
        
        try:
            logger.info(f"Starting PDF generation for session {state.get('session_id')}")
            
            # 验证输入
            if not self.validate_input(state):
                raise ValueError("Invalid input: final report not found")
            
            # 生成PDF
            pdf_path = self._generate_pdf_report(state)
            
            # 创建分析结果
            result = AnalysisResult(
                agent_type=self.agent_type,
                content=f"PDF报告已生成: {pdf_path}",
                structured_data={
                    "file_path": pdf_path,  # 修改为file_path以匹配测试期望
                    "file_size": os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0,
                    "generation_time": time.time() - start_time
                },
                confidence=1.0,
                sources=["final_report"]
            )
            
            logger.info(f"PDF generation completed: {pdf_path}")
            return result
            
        except Exception as e:
            error = self.handle_error(e, "PDF generation")
            raise error
    
    def _generate_pdf_report(self, state: ProjectAnalysisState) -> str:
        """生成PDF报告"""
        final_report = state.get("final_report", {})
        session_id = state.get("session_id", "unknown")
        
        # 确定输出路径
        output_dir = self.config.get("output_dir", "./reports")
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"project_analysis_{session_id}_{timestamp}.pdf"
        pdf_path = os.path.join(output_dir, pdf_filename)
        
        # 创建PDF文档
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        # 构建文档内容
        story = []
        
        # 添加标题页
        self._add_title_page(story, final_report, state)
        
        # 添加目录
        self._add_table_of_contents(story, final_report)
        
        # 添加执行摘要
        self._add_executive_summary(story, final_report)
        
        # 添加各个分析章节
        self._add_analysis_sections(story, final_report)
        
        # 添加综合分析
        self._add_comprehensive_analysis(story, final_report)
        
        # 添加结论和建议
        self._add_conclusions(story, final_report)

        # 🆕 v7.64: 添加搜索引用
        self._add_references(story, state)

        # 生成PDF
        doc.build(story)
        
        return pdf_path
    
    def _add_title_page(self, story: List, final_report: Dict[str, Any], state: ProjectAnalysisState):
        """添加标题页"""
        # 主标题
        title = "智能项目分析报告"
        story.append(Paragraph(title, self.styles['CustomTitle']))
        story.append(Spacer(1, 0.5*inch))
        
        # 项目信息
        executive_summary = final_report.get("executive_summary", {})
        project_overview = executive_summary.get("project_overview", "")
        
        if project_overview:
            story.append(Paragraph("项目概述", self.styles['SectionTitle']))
            story.append(Paragraph(project_overview, self.styles['CustomBodyText']))
            story.append(Spacer(1, 0.3*inch))
        
        # 报告信息
        metadata = final_report.get("metadata", {})
        report_info = [
            ["生成时间", metadata.get("generated_at", "")],
            ["会话ID", metadata.get("session_id", "")],
            ["分析智能体数量", str(metadata.get("total_agents", 0))],
            ["整体置信度", f"{metadata.get('overall_confidence', 0):.2f}"],
            ["预估页数", str(metadata.get("estimated_pages", 0))]
        ]
        
        table = Table(report_info, colWidths=[3*inch, 3*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), self.default_font),  # 使用中文字体
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
        story.append(PageBreak())
    
    def _add_table_of_contents(self, story: List, final_report: Dict[str, Any]):
        """添加目录"""
        story.append(Paragraph("目录", self.styles['CustomTitle']))
        story.append(Spacer(1, 0.3*inch))
        
        toc_items = [
            "1. 执行摘要",
            "2. 需求分析",
            "3. 设计研究",
            "4. 技术架构",
            "5. 用户体验设计",
            "6. 商业模式",
            "7. 实施规划",
            "8. 综合分析",
            "9. 结论和建议"
        ]
        
        for item in toc_items:
            story.append(Paragraph(item, self.styles['CustomBodyText']))
        
        story.append(PageBreak())
    
    def _add_executive_summary(self, story: List, final_report: Dict[str, Any]):
        """添加执行摘要"""
        story.append(Paragraph("1. 执行摘要", self.styles['CustomTitle']))
        
        executive_summary = final_report.get("executive_summary", {})
        
        # 关键发现
        key_findings = executive_summary.get("key_findings", [])
        if key_findings:
            story.append(Paragraph("关键发现", self.styles['SectionTitle']))
            for finding in key_findings:
                story.append(Paragraph(f"• {finding}", self.styles['CustomBodyText']))
            story.append(Spacer(1, 0.2*inch))
        
        # 核心建议
        key_recommendations = executive_summary.get("key_recommendations", [])
        if key_recommendations:
            story.append(Paragraph("核心建议", self.styles['SectionTitle']))
            for recommendation in key_recommendations:
                story.append(Paragraph(f"• {recommendation}", self.styles['Highlight']))
            story.append(Spacer(1, 0.2*inch))
        
        # 成功要素
        success_factors = executive_summary.get("success_factors", [])
        if success_factors:
            story.append(Paragraph("成功要素", self.styles['SectionTitle']))
            for factor in success_factors:
                story.append(Paragraph(f"• {factor}", self.styles['CustomBodyText']))
        
        story.append(PageBreak())
    
    def _add_analysis_sections(self, story: List, final_report: Dict[str, Any]):
        """添加分析章节"""
        sections = final_report.get("sections", [])  # 改为列表

        # 遍历sections列表
        for idx, section in enumerate(sections, start=2):
            section_id = section.get("section_id", "unknown")
            title = section.get("title", "未知章节")
            content = section.get("content", "")
            confidence = section.get("confidence", 0)

            story.append(Paragraph(f"{idx}. {title}", self.styles['CustomTitle']))

            # 置信度
            story.append(Paragraph(f"分析置信度: {confidence:.2f}", self.styles['Highlight']))
            story.append(Spacer(1, 0.2*inch))

            # 内容 (现在是字符串)
            self._add_section_content(story, content)

            story.append(PageBreak())
    
    def _add_section_content(self, story: List, content: str):
        """
        添加章节内容 - 智能解析JSON和文本

        🔥 Phase 1.4+: 增强PDF内容提取逻辑
        - 自动识别JSON格式并解析
        - 递归渲染结构化内容
        - 保持文本格式的可读性
        """
        if isinstance(content, str):
            # 🔥 尝试解析为JSON
            try:
                import json
                content_dict = json.loads(content)

                # 如果是JSON，递归渲染结构化内容
                if isinstance(content_dict, dict):
                    self._render_structured_content(story, content_dict)
                    return
                elif isinstance(content_dict, list):
                    # 如果是列表，逐项渲染
                    for item in content_dict:
                        if isinstance(item, dict):
                            self._render_structured_content(story, item)
                        else:
                            story.append(Paragraph(f"• {item}", self.styles['CustomBodyText']))
                    return
            except (json.JSONDecodeError, TypeError):
                # 不是JSON，按普通文本处理
                pass

            # 普通文本按行分割
            lines = content.split('\n')
            for line in lines:
                if line.strip():
                    # 跳过JSON格式标记行（如 {, }, [, ]）
                    if line.strip() in ['{', '}', '[', ']']:
                        continue
                    story.append(Paragraph(line, self.styles['CustomBodyText']))
                    story.append(Spacer(1, 0.1*inch))
        elif isinstance(content, dict):
            # 兼容旧格式(如果有)
            self._render_structured_content(story, content)

    def _render_structured_content(self, story: List, data: Dict[str, Any], level: int = 0):
        """
        🔥 Phase 1.4+: 递归渲染结构化内容

        将JSON结构转换为格式化的PDF内容，支持：
        - 嵌套字典（带缩进）
        - 列表（带项目符号）
        - 普通文本（键值对）
        """
        indent = "  " * level

        for key, value in data.items():
            # 跳过内部元数据字段
            if key in ['validation_warnings', 'raw_content', 'metadata']:
                continue

            # 格式化键名（将下划线替换为空格，首字母大写）
            display_key = key.replace('_', ' ').title()

            if isinstance(value, dict):
                # 🔥 子标题（字典）
                story.append(Paragraph(f"{indent}【{display_key}】", self.styles['SubTitle']))
                story.append(Spacer(1, 0.05*inch))
                self._render_structured_content(story, value, level + 1)
            elif isinstance(value, list):
                # 🔥 列表
                if not value:  # 空列表
                    continue
                story.append(Paragraph(f"{indent}【{display_key}】", self.styles['SubTitle']))
                story.append(Spacer(1, 0.05*inch))
                for item in value:
                    if isinstance(item, dict):
                        # 列表中的字典项，递归渲染
                        story.append(Spacer(1, 0.05*inch))
                        self._render_structured_content(story, item, level + 1)
                        story.append(Spacer(1, 0.05*inch))
                    else:
                        # 简单列表项
                        story.append(Paragraph(f"{indent}  • {item}", self.styles['CustomBodyText']))
            else:
                # 🔥 普通文本（键值对）
                if value:  # 只显示非空值
                    story.append(Paragraph(f"{indent}{display_key}: {value}", self.styles['CustomBodyText']))

            story.append(Spacer(1, 0.1*inch))
    
    def _add_comprehensive_analysis(self, story: List, final_report: Dict[str, Any]):
        """添加综合分析"""
        story.append(Paragraph("8. 综合分析", self.styles['CustomTitle']))
        
        comprehensive_analysis = final_report.get("comprehensive_analysis", {})
        
        for key, value in comprehensive_analysis.items():
            story.append(Paragraph(key.replace("_", " ").title(), self.styles['SectionTitle']))
            if isinstance(value, list):
                for item in value:
                    story.append(Paragraph(f"• {item}", self.styles['CustomBodyText']))
            else:
                story.append(Paragraph(str(value), self.styles['CustomBodyText']))
            story.append(Spacer(1, 0.2*inch))
        
        story.append(PageBreak())
    
    def _add_conclusions(self, story: List, final_report: Dict[str, Any]):
        """添加结论和建议"""
        story.append(Paragraph("9. 结论和建议", self.styles['CustomTitle']))

        conclusions = final_report.get("conclusions", {})

        # 总结
        summary = conclusions.get("summary", "")
        if summary:
            story.append(Paragraph("总结", self.styles['SectionTitle']))
            story.append(Paragraph(summary, self.styles['CustomBodyText']))
            story.append(Spacer(1, 0.2*inch))

        # 下一步行动
        next_steps = conclusions.get("next_steps", [])
        if next_steps:
            story.append(Paragraph("下一步行动", self.styles['SectionTitle']))
            for step in next_steps:
                story.append(Paragraph(f"• {step}", self.styles['Highlight']))
            story.append(Spacer(1, 0.2*inch))

        # 成功指标
        success_metrics = conclusions.get("success_metrics", [])
        if success_metrics:
            story.append(Paragraph("成功指标", self.styles['SectionTitle']))
            for metric in success_metrics:
                story.append(Paragraph(f"• {metric}", self.styles['CustomBodyText']))

    def _add_references(self, story: List, state: ProjectAnalysisState):
        """
        🆕 v7.64: 添加搜索引用章节

        从state.search_references中提取所有搜索引用，
        去重、按质量排序、分组显示

        Args:
            story: PDF内容列表
            state: 项目分析状态
        """
        # 提取搜索引用
        search_references = state.get("search_references", [])

        if not search_references:
            logger.debug("ℹ️ [v7.64] No search references to add to PDF")
            return

        # 添加新页面和标题
        story.append(PageBreak())
        story.append(Paragraph("10. 参考资料 (References)", self.styles['CustomTitle']))
        story.append(Spacer(1, 0.2*inch))

        # 去重
        unique_references = self._deduplicate_references(search_references)
        logger.info(f"📚 [v7.64] Adding {len(unique_references)} unique references to PDF")

        # 按source_tool分组
        references_by_tool = {
            "tavily": [],
            "arxiv": [],
            "ragflow": [],
            "bocha": []
        }

        for ref in unique_references:
            tool = ref.get("source_tool", "tavily")
            if tool in references_by_tool:
                references_by_tool[tool].append(ref)

        # 工具名称映射
        tool_labels = {
            "tavily": "🌐 国际搜索 (Tavily)",
            "arxiv": "📚 学术论文 (Arxiv)",
            "ragflow": "🗄️ 内部知识库 (RAGFlow)",
            "bocha": "🇨🇳 中文搜索 (博查)"
        }

        # 渲染每个工具的引用
        reference_counter = 1
        for tool_key, tool_label in tool_labels.items():
            refs = references_by_tool.get(tool_key, [])
            if not refs:
                continue

            # 按质量分数排序（降序）
            refs_sorted = sorted(
                refs,
                key=lambda x: x.get("quality_score", x.get("relevance_score", 0) * 100),
                reverse=True
            )

            # 添加工具标题
            story.append(Paragraph(tool_label, self.styles['SectionTitle']))
            story.append(Spacer(1, 0.1*inch))

            # 渲染每条引用
            for ref in refs_sorted:
                title = ref.get("title", "Untitled")
                url = ref.get("url", "")
                snippet = ref.get("snippet", "")
                quality_score = ref.get("quality_score")
                relevance_score = ref.get("relevance_score", 0)

                # [编号] 标题
                reference_text = f"[{reference_counter}] {title}"
                if quality_score is not None:
                    reference_text += f" (质量: {quality_score:.1f}/100)"
                elif relevance_score:
                    reference_text += f" (相关性: {relevance_score:.2f})"

                story.append(Paragraph(reference_text, self.styles['ReferenceText']))

                # URL
                if url:
                    story.append(Paragraph(f"🔗 {url}", self.styles['ReferenceURL']))

                # 摘要
                if snippet:
                    # 限制摘要长度
                    snippet_truncated = snippet[:250] + "..." if len(snippet) > 250 else snippet
                    story.append(Paragraph(snippet_truncated, self.styles['ReferenceSnippet']))

                story.append(Spacer(1, 0.15*inch))
                reference_counter += 1

        # 添加引用说明
        story.append(Spacer(1, 0.2*inch))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
        story.append(Spacer(1, 0.1*inch))

        note_text = (
            f"<i>注: 本报告共引用 {len(unique_references)} 条外部资料，来源包括国际搜索引擎、学术数据库、内部知识库等。"
            f"所有引用已根据相关性、可信度、时效性和完整性进行质量评分。</i>"
        )
        story.append(Paragraph(note_text, self.styles['CustomBodyText']))

    def _deduplicate_references(self, references: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        🆕 v7.64: 去重搜索引用（基于title + url）

        Args:
            references: 原始引用列表

        Returns:
            去重后的引用列表
        """
        seen = set()
        unique = []

        for ref in references:
            # 使用title和url作为去重键
            title = ref.get("title", "")
            url = ref.get("url", "")
            key = (title, url)

            if key not in seen:
                unique.append(ref)
                seen.add(key)

        logger.debug(f"📚 [v7.64] Deduplicated: {len(references)} → {len(unique)} references")
        return unique


# PDF生成器不需要注册到智能体工厂，因为它是工具类而非智能体
