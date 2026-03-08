"""
MT-1 (2026-03-01): PDF 生成工具模块

从 api/server.py 提取的 PDF 生成代码。
纯工具函数，无路由依赖，可独立测试。
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Dict

from fpdf import FPDF
from loguru import logger

from intelligent_project_analyzer.api.html_pdf_generator import (
    HTMLPDFGenerator,
)
from intelligent_project_analyzer.api.html_pdf_generator import (
    generate_expert_report_pdf as generate_html_pdf,
)


class PDFGenerator(FPDF):
    """支持中文的 PDF 生成器"""

    def __init__(self):
        super().__init__()
        self.chinese_font_loaded = False
        # 设置页面边距（左、上、右）- 先设置边距
        self.set_margins(left=25, top=25, right=25)
        self.set_auto_page_break(auto=True, margin=30)
        # 尝试加载中文字体
        self._load_chinese_font()

    def _load_chinese_font(self):
        """加载中文字体"""
        # 尝试多个常见的中文字体路径
        font_paths = [
            "C:/Windows/Fonts/msyh.ttc",  # 微软雅黑
            "C:/Windows/Fonts/simsun.ttc",  # 宋体
            "C:/Windows/Fonts/simhei.ttf",  # 黑体
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",  # Linux
            "/System/Library/Fonts/PingFang.ttc",  # macOS
        ]

        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    self.add_font("Chinese", "", font_path, uni=True)
                    self.add_font("Chinese", "B", font_path, uni=True)
                    self.chinese_font_loaded = True
                    logger.info(f" 成功加载中文字体: {font_path}")
                    return
                except Exception as e:
                    logger.warning(f"️ 加载字体失败 {font_path}: {e}")
                    continue

        logger.warning("️ 未找到中文字体，使用内置字体")

    def _set_font_safe(self, style: str = "", size: int = 10):
        """安全设置字体"""
        if self.chinese_font_loaded:
            self.set_font("Chinese", style, size)
        else:
            self.set_font("Arial", style, size)

    def header(self):
        """页眉（留空）"""
        pass

    def footer(self):
        """页脚（已移除）"""
        pass

    def add_cover_page(self, title: str = "项目分析报告"):
        """添加封面页

         v7.26 整改:
        - 中英文靠近（不要空行）
        - 生成时间前加"极致概念"
        - 不要生成时间和冒号
        - 不要版本
        """
        self.add_page()

        # 封面标题 - 居中显示在页面中部偏上
        self.set_y(80)
        self._set_font_safe("B", 28)
        self.set_text_color(26, 26, 26)
        self.cell(0, 20, title, ln=True, align="C")

        # 副标题 -  v7.26: 中英文靠近（ln(10) → ln(3)）
        self.ln(3)
        self._set_font_safe("", 14)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, "Intelligent Project Analyzer", ln=True, align="C")

        #  v7.26: "极致概念" + 日期（无冒号，无版本）
        self.ln(40)
        self._set_font_safe("", 11)
        self.set_text_color(128, 128, 128)
        self.cell(0, 8, f"极致概念 {datetime.now().strftime('%Y-%m-%d')}", ln=True, align="C")

    def add_table_of_contents(self, chapters: list):
        """添加目录页

        Args:
            chapters: 章节列表，每项为 {"title": str, "page": int}
        """
        self.add_page()

        # 目录标题
        self._set_font_safe("B", 18)
        self.set_text_color(26, 26, 26)
        self.cell(0, 15, "目 录", ln=True, align="C")
        self.ln(15)

        # 目录项
        self._set_font_safe("", 12)
        self.set_text_color(51, 51, 51)

        for i, chapter in enumerate(chapters, 1):
            title = chapter.get("title", "")
            page = chapter.get("page", "")

            # 章节编号和标题
            chapter_text = f"第{i}章  {title}"

            # 计算点线填充
            self.set_x(self.l_margin)
            title_width = self.get_string_width(chapter_text)
            page_width = self.get_string_width(str(page))
            available_width = self.w - self.l_margin - self.r_margin - title_width - page_width - 10
            dots = "." * int(available_width / self.get_string_width("."))

            # 输出目录行
            self.cell(title_width + 5, 10, chapter_text, ln=False)
            self.set_text_color(180, 180, 180)
            self.cell(available_width, 10, dots, ln=False)
            self.set_text_color(51, 51, 51)
            self.cell(page_width + 5, 10, str(page), ln=True, align="R")
            self.ln(2)

    def chapter_title(self, title: str, level: int = 1):
        """添加标题 - 智能处理换行"""
        if not title:
            return
        sizes = {1: 16, 2: 13, 3: 11, 4: 10}
        size = sizes.get(level, 10)
        self._set_font_safe("B", size)
        self.set_text_color(26, 26, 26)
        self.ln(4 if level > 1 else 0)
        # 重置 X 到左边距
        self.set_x(self.l_margin)
        # 使用 wrapmode=WrapMode.CHAR 避免英文单词被拆分换行
        from fpdf.enums import WrapMode

        self.multi_cell(w=0, h=7, text=str(title), wrapmode=WrapMode.CHAR)
        self.set_x(self.l_margin)  # multi_cell 后重置
        self.ln(2)

    def body_text(self, text: str):
        """添加正文 - 智能处理换行和Markdown格式

         v7.26.3: 支持Markdown格式解析
        - ### 标题 → 小节标题
        - **加粗** → 去除星号显示
        - - 列表项 → bullet列表
        """
        if not text:
            return

        # 清理文本，确保字符串格式
        clean_text = str(text).strip()
        if not clean_text:
            return


        from fpdf.enums import WrapMode

        #  v7.26.3: 按行处理，识别Markdown格式
        lines = clean_text.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 1. 处理 Markdown 标题 (### 或 ## 或 #)
            header_match = re.match(r"^(#{1,4})\s+(.+)$", line)
            if header_match:
                level = len(header_match.group(1)) + 2  # # -> level 3, ## -> level 4
                title_text = header_match.group(2).strip()
                # 清理标题中的Markdown格式
                title_text = re.sub(r"\*\*(.+?)\*\*", r"\1", title_text)
                title_text = re.sub(r"\*(.+?)\*", r"\1", title_text)
                self.chapter_title(title_text, min(level, 4))
                continue

            # 2. 处理 Markdown 无序列表 (- 或 *)
            list_match = re.match(r"^[-*]\s+(.+)$", line)
            if list_match:
                item_text = list_match.group(1).strip()
                # 清理列表项中的Markdown格式
                item_text = re.sub(r"\*\*(.+?)\*\*", r"\1", item_text)
                item_text = re.sub(r"\*(.+?)\*", r"\1", item_text)
                self.list_item(item_text)
                continue

            # 3. 普通文本：清理Markdown格式后输出
            # 去除 **加粗** 和 *斜体* 标记
            clean_line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
            clean_line = re.sub(r"\*(.+?)\*", r"\1", clean_line)

            # 设置字体和颜色
            self._set_font_safe("", 10)
            self.set_text_color(51, 51, 51)
            self.set_x(self.l_margin)

            # 检查是否包含编号列表
            if any(f"{i}." in clean_line or f"{i}、" in clean_line for i in range(1, 10)):
                formatted_text = _format_numbered_list(clean_line)
                sub_lines = formatted_text.split("\n")
                for sub_line in sub_lines:
                    sub_line = sub_line.strip()
                    if sub_line:
                        self.multi_cell(w=0, h=5, text=sub_line, wrapmode=WrapMode.CHAR)
                        self.set_x(self.l_margin)
            else:
                self.multi_cell(w=0, h=5, text=clean_line, wrapmode=WrapMode.CHAR)
                self.set_x(self.l_margin)

        self.ln(2)

    def list_item(self, text: str, numbered: bool = False, index: int = 0):
        """添加列表项 - 智能处理换行"""
        if not text:
            return
        self._set_font_safe("", 10)
        self.set_text_color(51, 51, 51)
        prefix = f"{index + 1}. " if numbered else "• "
        clean_text = str(text).strip()
        if clean_text:
            self.set_x(self.l_margin)  # 重置 X 到左边距
            # 使用 wrapmode=WrapMode.CHAR 避免英文单词被拆分换行
            from fpdf.enums import WrapMode

            self.multi_cell(w=0, h=5, text=prefix + clean_text, wrapmode=WrapMode.CHAR)
            self.set_x(self.l_margin)  # multi_cell 后重置

    def add_divider(self):
        """添加分隔线"""
        self.ln(3)
        self.set_draw_color(229, 231, 235)
        # 使用页面宽度计算
        page_width = self.w - self.l_margin - self.r_margin
        self.line(self.l_margin, self.get_y(), self.l_margin + page_width, self.get_y())
        self.ln(4)

    def highlighted_box(self, text: str):
        """添加高亮框（用户输入）"""
        if not text:
            return

        clean_text = str(text).strip()
        if not clean_text:
            return

        self.set_fill_color(248, 249, 250)
        self.set_draw_color(59, 130, 246)
        self._set_font_safe("", 10)
        self.set_text_color(51, 51, 51)

        # 计算可用宽度
        available_width = self.w - self.l_margin - self.r_margin
        box_width = available_width - 10  # 留一点边距

        # 先绘制左侧蓝色边线
        x = self.l_margin + 5
        y = self.get_y()

        # 存储当前位置
        start_y = y

        # 绘制背景和文本 - 使用字符级换行
        self.set_x(x + 5)
        from fpdf.enums import WrapMode

        self.multi_cell(w=box_width - 10, h=5, text=clean_text, fill=True, wrapmode=WrapMode.CHAR)

        # 绘制左侧蓝色边线
        end_y = self.get_y()
        self.set_line_width(0.8)
        self.set_draw_color(59, 130, 246)
        self.line(x, start_y, x, end_y)

        # 重置 X 位置
        self.set_x(self.l_margin)
        self.ln(4)


def generate_report_pdf(report_data: dict, user_input: str = "") -> bytes:
    """
     v7.24 合并优化：生成完整报告 PDF（含专家报告）

    PDF 结构对齐前端显示，包含 6 个核心章节：
    1. 用户原始需求
    2. 校准问卷回顾（过滤"未回答"）
    3. 需求洞察
    4. 核心答案（支持 v7.0 多交付物格式）
    5. 专家报告附录（ v7.24: 合并原独立下载）
    6. 执行元数据
    """
    pdf = PDFGenerator()

    # ========== 封面页 ==========
    pdf.add_cover_page("项目分析报告")

    # ========== 目录页（简化版，无页码） ==========
    #  v7.26: 添加"报告（极致概念）"条目
    chapters = [
        {"title": "报告（极致概念）", "page": ""},
        {"title": "用户原始需求", "page": ""},
        {"title": "校准问卷回顾", "page": ""},
        {"title": "需求洞察", "page": ""},
        {"title": "核心答案", "page": ""},
        {"title": "专家报告附录", "page": ""},
        {"title": "执行元数据", "page": ""},
    ]
    pdf.add_table_of_contents(chapters)

    # ========== 第一章：报告（极致概念） ==========
    #  v7.26: 新增章节 - 报告概述
    pdf.add_page()  # 目录后的第一章需要新页
    pdf.chapter_title("第一章  报告（极致概念）", 1)
    pdf.body_text("本报告由极致概念智能分析系统生成，基于多智能体协作框架，为您的项目需求提供全方位的专业分析与建议。")
    pdf.ln(5)

    # 报告概述信息
    expert_reports = report_data.get("expert_reports", {})
    expert_count = len(expert_reports) if isinstance(expert_reports, dict) else 0
    if expert_count > 0:
        pdf.chapter_title("分析概述", 2)
        pdf.body_text(f"• 参与专家数量：{expert_count} 位")
        pdf.body_text(f"• 生成日期：{datetime.now().strftime('%Y-%m-%d')}")

    pdf.add_divider()

    # ========== 第二章：用户原始需求 ==========
    #  v7.26: 空两行连续输出，不要每个章节分页
    pdf.ln(15)
    pdf.chapter_title("第二章  用户原始需求", 1)
    if user_input:
        pdf.highlighted_box(user_input)
    else:
        pdf.body_text("（无用户输入）")
    pdf.add_divider()

    # ========== 第三章：校准问卷回顾 ==========
    #  v7.26: 空两行连续输出
    pdf.ln(15)
    pdf.chapter_title("第三章  校准问卷回顾", 1)

    questionnaire = report_data.get("questionnaire_responses", {})
    if questionnaire and isinstance(questionnaire, dict):
        responses = questionnaire.get("responses", [])
        #  过滤：只显示有效回答（排除"未回答"和空答案）
        valid_responses = [
            r for r in responses if isinstance(r, dict) and r.get("answer") and r.get("answer") not in ["未回答", ""]
        ]

        if valid_responses:
            pdf.body_text(f"共收集 {len(valid_responses)} 条有效回答：")
            pdf.ln(3)

            for idx, resp in enumerate(valid_responses, 1):
                question = resp.get("question", "")
                answer = resp.get("answer", "")
                context = resp.get("context", "")

                # 问题标题
                pdf.chapter_title(f"Q{idx}. {question}", 3)

                # 回答内容
                pdf._set_font_safe("", 10)
                pdf.set_text_color(51, 51, 51)
                pdf.body_text(f"回答：{answer}")

                # 问题背景（如果有）
                if context:
                    pdf._set_font_safe("", 9)
                    pdf.set_text_color(128, 128, 128)
                    pdf.body_text(f"背景：{context}")

                pdf.ln(2)

            # 分析洞察（如果有）
            analysis_insights = questionnaire.get("analysis_insights", "")
            if analysis_insights:
                pdf.add_divider()
                pdf.chapter_title("需求分析", 3)
                pdf.body_text(analysis_insights)
        else:
            pdf.body_text("用户跳过了校准问卷，或所有问题均未回答。")
    else:
        pdf.body_text("用户跳过了校准问卷。")

    pdf.add_divider()

    # ========== 第四章：需求洞察 ==========
    #  v7.26: 空两行连续输出
    pdf.ln(15)
    pdf.chapter_title("第四章  需求洞察", 1)

    insights = report_data.get("insights", {})

    #  v7.26.2: 兜底逻辑 - 如果 insights 为空，从 requirements_analysis 提取
    if not insights or not isinstance(insights, dict):
        requirements_analysis = report_data.get("requirements_analysis", {})
        if requirements_analysis and isinstance(requirements_analysis, dict):
            logger.info(" [PDF] insights 为空，从 requirements_analysis 提取兜底数据")
            insights = {
                "key_insights": [
                    requirements_analysis.get("project_overview", ""),
                    requirements_analysis.get("project_task", ""),
                ],
                "cross_domain_connections": requirements_analysis.get("core_objectives", []),
                "user_needs_interpretation": requirements_analysis.get("character_narrative", ""),
            }
            # 过滤空值
            insights["key_insights"] = [i for i in insights["key_insights"] if i]
            if not insights["key_insights"]:
                insights = {}

    if insights and isinstance(insights, dict):
        # 核心洞察
        key_insights = insights.get("key_insights", [])
        if key_insights:
            pdf.chapter_title("核心洞察", 2)
            for idx, insight in enumerate(key_insights, 1):
                pdf.list_item(f"{insight}", numbered=True, index=idx - 1)
            pdf.ln(3)

        # 跨领域关联
        cross_domain = insights.get("cross_domain_connections", [])
        if cross_domain:
            pdf.chapter_title("跨领域关联", 2)
            for item in cross_domain:
                pdf.list_item(item)
            pdf.ln(3)

        # 用户需求深层解读
        interpretation = insights.get("user_needs_interpretation", "")
        if interpretation:
            pdf.chapter_title("用户需求深层解读", 2)
            pdf.body_text(interpretation)
    else:
        pdf.body_text("（暂无需求洞察数据）")

    pdf.add_divider()

    # ========== 第五章：核心答案 ==========
    #  v7.26: 空两行连续输出
    pdf.ln(15)
    pdf.chapter_title("第五章  核心答案", 1)

    core_answer = report_data.get("core_answer", {})

    #  v7.26.2: 兜底逻辑 - 如果 core_answer 为空，从 expert_reports 提取交付物信息
    if not core_answer or not isinstance(core_answer, dict):
        logger.info(" [PDF] core_answer 为空，从 expert_reports 提取兜底数据")
        # 从专家报告中提取交付物名称
        deliverable_names = []
        expert_reports_raw = report_data.get("expert_reports", {})
        if isinstance(expert_reports_raw, dict):
            for _expert_name, content in expert_reports_raw.items():
                if isinstance(content, str):
                    try:
                        content_dict = json.loads(content) if content.strip().startswith("{") else {}
                        ter = content_dict.get("task_execution_report", content_dict)
                        if isinstance(ter, dict):
                            outputs = ter.get("deliverable_outputs", [])
                            for output in outputs:
                                if isinstance(output, dict):
                                    name = output.get("deliverable_name", output.get("name", ""))
                                    if name and name not in deliverable_names:
                                        deliverable_names.append(name)
                    except (json.JSONDecodeError, AttributeError):
                        pass

        if deliverable_names:
            requirements = report_data.get("requirements_analysis", {})
            core_answer = {
                "question": user_input[:100] + "..." if len(user_input) > 100 else user_input,
                "answer": requirements.get("project_overview", "请查看各专家的详细分析报告"),
                "deliverables": deliverable_names[:5],
                "timeline": "请参考工程师专家的实施规划",
                "budget_range": "请参考工程师专家的成本估算",
            }

    if core_answer and isinstance(core_answer, dict):
        # 检测是否是 v7.0 多交付物格式
        deliverable_answers = core_answer.get("deliverable_answers", [])

        if deliverable_answers:
            #  v7.0 多交付物格式
            pdf.body_text(f"本项目包含 {len(deliverable_answers)} 个核心交付物：")
            pdf.ln(5)

            for da in deliverable_answers:
                if not isinstance(da, dict):
                    continue

                deliverable_id = da.get("deliverable_id", "")
                deliverable_name = da.get("deliverable_name", "")
                owner_role = da.get("owner_role", "")
                answer_summary = da.get("answer_summary", "")
                owner_answer = da.get("owner_answer", "")
                supporters = da.get("supporters", [])
                quality_score = da.get("quality_score")

                # 交付物标题
                pdf.chapter_title(f"【{deliverable_id}】{deliverable_name}", 2)

                # 责任者信息
                pdf._set_font_safe("", 10)
                pdf.set_text_color(100, 100, 100)
                role_display = _get_role_display_name(owner_role)
                pdf.body_text(f"责任专家: {role_display}")

                if quality_score:
                    pdf.body_text(f"完成度: {int(quality_score)}%")

                # 答案摘要
                if answer_summary:
                    pdf.chapter_title("答案摘要", 3)
                    pdf.body_text(answer_summary)

                # 完整输出
                if owner_answer:
                    pdf.chapter_title("责任者输出", 3)
                    pdf.body_text(owner_answer)

                # 支撑专家
                if supporters:
                    pdf.chapter_title("支撑专家", 3)
                    supporter_names = [_get_role_display_name(s) for s in supporters]
                    pdf.body_text("、".join(supporter_names))

                pdf.ln(5)
        else:
            # 旧格式（单一答案）
            question = core_answer.get("question", "")
            answer = core_answer.get("answer", "")
            deliverables = core_answer.get("deliverables", [])
            timeline = core_answer.get("timeline", "")
            budget_range = core_answer.get("budget_range", "")

            if question:
                pdf.chapter_title("核心问题", 2)
                pdf.body_text(question)

            if answer:
                pdf.chapter_title("综合答案", 2)
                pdf.body_text(answer)

            if deliverables:
                pdf.chapter_title("交付物清单", 2)
                for idx, d in enumerate(deliverables, 1):
                    pdf.list_item(d, numbered=True, index=idx - 1)
                pdf.ln(3)

            if timeline:
                pdf.chapter_title("时间规划", 2)
                pdf.body_text(timeline)

            if budget_range:
                pdf.chapter_title("预算范围", 2)
                pdf.body_text(budget_range)
    else:
        pdf.body_text("（暂无核心答案数据）")

    pdf.add_divider()

    # ========== 第六章：专家报告附录  v7.24 ==========
    expert_reports = report_data.get("expert_reports", {})
    if expert_reports and isinstance(expert_reports, dict) and len(expert_reports) > 0:
        #  v7.26: 空两行连续输出，不要分页
        pdf.ln(15)
        pdf.chapter_title("第六章  专家报告附录", 1)
        pdf.body_text(f"本章包含 {len(expert_reports)} 位专家的详细分析报告。")
        pdf.ln(5)

        # 专家目录
        pdf.chapter_title("专家列表", 2)
        for i, expert_name in enumerate(expert_reports.keys(), 1):
            pdf.list_item(f"{i}. {expert_name}", numbered=False)
        pdf.ln(5)

        # 逐个专家报告 -  v7.26: 不分页，空行分隔
        for expert_name, content in expert_reports.items():
            pdf.ln(10)
            pdf.chapter_title(expert_name, 2)
            format_expert_content_for_pdf(pdf, content)

    pdf.add_divider()

    # ========== 第七章：执行元数据 ==========
    #  v7.26: 空两行连续输出，不要分页
    pdf.ln(15)
    pdf.chapter_title("第七章  执行元数据", 1)

    # 从 report_data 中收集元数据
    inquiry_architecture = report_data.get("inquiry_architecture", "")
    expert_reports = report_data.get("expert_reports", {})
    expert_count = len(expert_reports) if isinstance(expert_reports, dict) else 0

    # 专家数量
    pdf.chapter_title("专家数量", 2)
    pdf.body_text(f"{expert_count} 位专家参与分析")

    # 探询架构
    if inquiry_architecture:
        pdf.chapter_title("探询架构", 2)
        pdf.body_text(inquiry_architecture)

    # 生成时间
    pdf.chapter_title("报告生成时间", 2)
    pdf.body_text(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    return bytes(pdf.output())


def _get_role_display_name(role_id: str) -> str:
    """提取角色显示名称"""
    role_map = {
        "V2_设计总监": "设计总监",
        "V3_叙事与体验专家": "叙事与体验专家",
        "V3_人物及叙事专家": "人物及叙事专家",
        "V4_设计研究专员": "设计研究专员",
        "V4_设计研究员": "设计研究员",
        "V5_场景策划师": "场景策划师",
        "V5_场景与用户生态专家": "场景与用户生态专家",
        "V6_专业总工程师": "专业总工程师",
        "V6_工程师": "工程师",
    }

    for prefix, name in role_map.items():
        if role_id.startswith(prefix):
            return name
    return role_id


# 字段中文标签映射（与前端保持一致）
FIELD_LABELS = {
    # 通用字段
    "executive_summary": "执行摘要",
    "project_overview": "项目概述",
    "key_findings": "关键发现",
    "key_recommendations": "核心建议",
    "success_factors": "成功要素",
    "core_analysis": "核心分析",
    "professional_opinion": "专业意见",
    "design_recommendations": "设计建议",
    "implementation_guidance": "实施指导",
    "analysis": "分析",
    "recommendations": "建议",
    "conclusion": "结论",
    "summary": "总结",
    "overview": "概述",
    "details": "详情",
    "description": "描述",
    "assessment": "评估",
    "evaluation": "评价",
    "findings": "发现",
    "insights": "洞察",
    "observations": "观察",
    "considerations": "考虑因素",
    "factors": "因素",
    "challenges": "挑战",
    "opportunities": "机遇",
    "risks": "风险",
    "benefits": "优势",
    "limitations": "局限",
    "requirements": "需求",
    "objectives": "目标",
    "goals": "目标",
    "strategy": "策略",
    "approach": "方法",
    "methodology": "方法论",
    "framework": "框架",
    "principles": "原则",
    "guidelines": "指导方针",
    "standards": "标准",
    "criteria": "标准",
    "metrics": "指标",
    "indicators": "指标",
    "performance": "性能",
    "quality": "质量",
    "efficiency": "效率",
    "effectiveness": "有效性",
    "impact": "影响",
    "outcome": "结果",
    "output": "产出",
    "input": "输入",
    "process": "流程",
    "procedure": "程序",
    "steps": "步骤",
    "phases": "阶段",
    "stages": "阶段",
    "timeline": "时间线",
    "schedule": "计划",
    "budget": "预算",
    "cost": "成本",
    "resources": "资源",
    "materials": "材料",
    "equipment": "设备",
    "tools": "工具",
    "technologies": "技术",
    "methods": "方法",
    "techniques": "技术",
    "solutions": "解决方案",
    "alternatives": "替代方案",
    "options": "选项",
    "choices": "选择",
    "preferences": "偏好",
    "priorities": "优先级",
    "concerns": "关注点",
    "issues": "问题",
    "problems": "问题",
    "actions": "行动",
    "tasks": "任务",
    "activities": "活动",
    "deliverables": "交付物",
    "milestones": "里程碑",
    "achievements": "成就",
    "results": "结果",
    "confidence": "置信度",
    "custom_analysis": "定制分析",
    "expert_handoff_response": "专家交接响应",
    "critical_questions_responses": "关键问题响应",
    "missing_inputs_warning": "缺失输入警告",
    # 设计相关字段
    "project_vision_summary": "项目愿景概述",
    "decision_rationale": "决策依据",
    "spatial_concept": "空间概念",
    "customer_journey_design": "客户旅程设计",
    "visual_merchandising_strategy": "视觉营销策略",
    "brand_identity_integration": "品牌识别整合",
    "space_planning": "空间规划",
    "material_selection": "材料选择",
    "lighting_design": "照明设计",
    "color_scheme": "配色方案",
    "furniture_layout": "家具布局",
    "user_experience": "用户体验",
    "functional_requirements": "功能需求",
    "aesthetic_considerations": "美学考量",
    "sustainability": "可持续性",
    "accessibility": "无障碍设计",
    "safety": "安全性",
    "maintenance": "维护",
    "durability": "耐久性",
    # 案例研究相关
    "case_studies_deep_dive": "深度案例研究",
    "competitive_analysis": "竞品分析",
    "reusable_design_patterns": "可复用设计模式",
    "key_success_factors": "关键成功因素",
    "application_guidelines_for_team": "团队应用指南",
    "key_takeaways": "关键要点",
    "name": "名称",
    "brand": "品牌",
    "strengths": "优势",
    "weaknesses": "劣势",
    "pattern_name": "模式名称",
    "pattern name": "模式名称",
    # 运营相关
    "business_goal_analysis": "商业目标分析",
    "operational_blueprint": "运营蓝图",
    "key_performance_indicators": "关键绩效指标",
    "design_challenges_for_v2": "给设计总监的挑战",
    "journey_maps": "旅程地图",
    "healing_environment_kpis": "疗愈环境KPI",
    "technical_requirements_for_v6": "给技术专家的需求",
    "metric": "指标",
    "target": "目标值",
    "spatial_strategy": "空间策略",
    # 用户研究相关
    "pain_points": "痛点",
    "Pain Points": "痛点",
    "persona": "用户画像",
    "Persona": "用户画像",
    "user_needs": "用户需求",
    "user_goals": "用户目标",
    "user_journey": "用户旅程",
    "touchpoints": "触点",
    "empathy_map": "共情地图",
    # 技术相关
    "mep_overall_strategy": "机电整体策略",
    "system_solutions": "系统解决方案",
    "smart_building_scenarios": "智能建筑场景",
    "coordination_and_clash_points": "协调与冲突点",
    "sustainability_and_energy_saving": "可持续与节能",
    # 材料与工艺
    "craftsmanship_strategy": "工艺策略",
    "key_material_specifications": "关键材料规格",
    "critical_node_details": "关键节点详图",
    "quality_control_and_mockup": "质量控制与样板",
    "risk_analysis": "风险分析",
    "design_rationale": "设计依据",
    # 挑战相关
    "challenge": "挑战",
    "context": "背景",
    "constraints": "约束条件",
    "challenge_flags": "挑战标记",
    # 签名方法/应用相关
    "signature_methods": "标志性方法",
    "application_to_project": "项目应用",
    "initial_key_scenario": "初始关键场景",
    # 设计立场相关
    "pole_a_resolve": "立场A解决方案",
    "pole_b_resolve": "立场B解决方案",
    "chosen_design_stance": "选定的设计立场",
    # 大师案例研究相关
    "master_work_deconstruction_nendo": "大师作品解构：Nendo",
    "master_work_deconstruction": "大师作品解构",
    "master": "大师",
    "philosophy": "设计哲学",
    "missing_inspiration_warning": "缺失灵感警告",
    "desc": "说明",
    # 其他常见字段
    "q1": "问题1",
    "q2": "问题2",
    "q3": "问题3",
    # ============ 任务导向模型字段 (task_oriented_models.py) ============
    # DeliverableOutput 交付物输出
    "deliverable_name": "交付物名称",
    "deliverable_outputs": "交付物输出",
    "content": "内容",
    "completion_status": "完成状态",
    "completion_rate": "完成度",
    "notes": "备注",
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
    "objective": "核心目标",
    "success_criteria": "成功标准",
    "context_requirements": "上下文需求",
    # DeliverableSpec 交付物规格
    "format": "格式",
    "priority": "优先级",
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
    "advantages": "优势",
    "disadvantages": "劣势",
    "estimated_cost_level": "预估造价等级",
    "node_name": "节点名称",
    "proposed_solution": "建议方案",
    # V6-2 机电与智能化工程师
    "system_name": "系统名称",
    "recommended_solution": "推荐方案",
    "reasoning": "理由",
    "impact_on_architecture": "对建筑的影响",
    "scenario_name": "场景名称",
    "triggered_systems": "联动系统",
    # V6-3 室内工艺与材料专家
    "material_name": "材料名称",
    "application_area": "应用区域",
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
    "emotional_journey": "情感旅程",
    "touchpoint_design": "触点设计",
    # V4系列 设计研究专员
    "trend_analysis": "趋势分析",
    "future_scenarios": "未来场景",
    "opportunity_identification": "机会识别",
    "design_implications": "设计启示",
}


def format_expert_content_for_pdf(pdf: PDFGenerator, content: str, depth: int = 0):
    """
    格式化专家报告内容并写入 PDF

    支持解析 JSON 结构化数据，递归处理嵌套对象和数组
    """
    import json

    if not content:
        pdf.body_text("（无内容）")
        return

    # 尝试解析 JSON
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            _format_dict_to_pdf(pdf, parsed, depth)
        elif isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict):
                    _format_dict_to_pdf(pdf, item, depth)
                else:
                    pdf.list_item(str(item))
        else:
            pdf.body_text(str(parsed))
    except (json.JSONDecodeError, TypeError):
        # 不是 JSON，直接输出原始文本
        pdf.body_text(content)


def _get_field_label(key: str) -> str:
    """获取字段的中文标签"""

    lower_key = key.lower().strip()

    # 精确匹配（包括带空格的key）
    if lower_key in FIELD_LABELS:
        return FIELD_LABELS[lower_key]

    # 尝试替换空格为下划线后匹配
    normalized_key = lower_key.replace(" ", "_").replace("-", "_")
    if normalized_key in FIELD_LABELS:
        return FIELD_LABELS[normalized_key]

    # 处理特殊格式：如 "Q1 空间要强化..." 这种问题+内容混合格式
    # 只翻译 Q1/Q2/Q3 部分
    import re as regex

    q_match = regex.match(r"^(q\d+)\s*(.*)$", lower_key, regex.IGNORECASE)
    if q_match:
        q_num = q_match.group(1).upper()
        rest = q_match.group(2).strip()
        q_label = {"Q1": "问题1", "Q2": "问题2", "Q3": "问题3", "Q4": "问题4", "Q5": "问题5"}.get(q_num, q_num)
        if rest:
            return f"{q_label} {rest}"
        return q_label

    # 常见英文词汇到中文的映射
    common_words = {
        # 功能词
        "for": "",
        "the": "",
        "of": "",
        "and": "与",
        "to": "到",
        "in": "在",
        "on": "上",
        "a": "",
        "an": "",
        "is": "",
        "are": "",
        "be": "",
        # 角色
        "v2": "设计总监",
        "v3": "专家",
        "v4": "研究员",
        "v5": "创新专家",
        "v6": "技术专家",
        # 常见术语
        "kpi": "KPI",
        "kpis": "KPI指标",
        "deep": "深度",
        "dive": "研究",
        "how": "如何",
        "might": "可能",
        "we": "我们",
        "pattern": "模式",
        "name": "名称",
        "signature": "标志性",
        "methods": "方法",
        "application": "应用",
        "project": "项目",
        "initial": "初始",
        "key": "关键",
        "scenario": "场景",
        "pole": "立场",
        "resolve": "解决方案",
        "chosen": "选定的",
        "design": "设计",
        "stance": "立场",
        "q1": "问题1",
        "q2": "问题2",
        "q3": "问题3",
        "brand": "品牌",
        "identity": "识别",
        "integration": "整合",
        "space": "空间",
        "spatial": "空间",
        "concept": "概念",
        "customer": "客户",
        "journey": "旅程",
        "visual": "视觉",
        "merchandising": "营销",
        "strategy": "策略",
        "summary": "概述",
        "vision": "愿景",
        "rationale": "依据",
        "decision": "决策",
        "guidance": "指导",
        "implementation": "实施",
        "custom": "定制",
        "analysis": "分析",
        "confidence": "置信度",
        "expert": "专家",
        "handoff": "交接",
        "response": "响应",
        "critical": "关键",
        "questions": "问题",
        "responses": "响应",
        "missing": "缺失",
        "inputs": "输入",
        "warning": "警告",
        "challenges": "挑战",
        "flags": "标记",
        # 大师/案例相关
        "master": "大师",
        "work": "作品",
        "deconstruction": "解构",
        "nendo": "Nendo",
        "philosophy": "设计哲学",
        "inspiration": "灵感",
        "desc": "说明",
    }

    # 尝试部分匹配（将 snake_case 分解后翻译）
    parts = normalized_key.split("_")
    translated_parts = []
    has_untranslated = False

    for part in parts:
        if not part:
            continue
        if part in FIELD_LABELS:
            translated_parts.append(FIELD_LABELS[part])
        elif part in common_words:
            if common_words[part]:
                translated_parts.append(common_words[part])
        elif part.isdigit():
            translated_parts.append(part)
        else:
            has_untranslated = True
            translated_parts.append(part)

    # 如果有未翻译的部分，返回格式化的原始标签
    if has_untranslated:
        label = key.replace("_", " ").replace("-", " ")
        label = regex.sub(r"([a-z])([A-Z])", r"\1 \2", label)
        return label.title()

    return "".join(translated_parts) if translated_parts else key


# 需要跳过的重复/内部字段
#  v7.9.2: 扩展黑名单,过滤元数据字段(与前端ExpertReportAccordion.tsx保持一致)
#  v7.26.1: 移除 content 字段，交给递归函数特殊处理（允许嵌套对象的 content）
SKIP_FIELDS = {
    # 原有字段 -  v7.26.1: 移除 'content'，交给递归函数处理
    "raw_content",
    "raw_response",
    "original_content",
    #  v7.9.2: 任务导向输出元数据(避免显示技术字段)
    "task_execution_report",  # 已被提取,不再需要显示
    "protocol_execution",
    "protocol执行",
    "protocol_status",
    "protocol状态",
    "execution_metadata",
    "executionmetadata",
    "compliance_confirmation",
    "complianceconfirmation",
    # 技术字段
    "confidence",
    "置信度",
    "completion_status",
    "completion记录",
    "completion_ratio",
    "completion_rate",
    "quality_self_assessment",
    "dependencies_satisfied",
    "notes",  # 通常是技术备注
    #  v7.10.1: 过滤无意义的图片占位符字段
    "image",
    "images",
    "图片",
    "illustration",
    "illustrations",
    "image_1_url",
    "image_2_url",
    "image_3_url",
    "image_4_url",
    "image_5_url",
    "image_6_url",
    "image_url",
    "image_urls",
    "图片链接",
}

#  v7.26.1: 顶层专用黑名单（只在 depth=0 时跳过）
TOP_LEVEL_SKIP_FIELDS = {
    "content",  # 顶层 content 可能与 structured_data 重复
}

# ============ 内容翻译函数（处理 LLM 输出中的英文短语） ============
CONTENT_TRANSLATIONS = {
    # 设计思维框架短语
    "How might we": "我们如何能够",
    "How Might We": "我们如何能够",
    "HMW": "如何",
    # Pain Points 各种变体
    "Pain Points": "痛点",
    "Pain points": "痛点",
    "pain points": "痛点",
    "Pain Point": "痛点",
    "pain point": "痛点",
    # Persona 各种变体（保留冒号后的空格）
    "Persona: ": "用户画像: ",
    "Persona:": "用户画像:",
    "persona: ": "用户画像: ",
    "persona:": "用户画像:",
    # 值翻译（LLM 可能输出的英文值）
    "pole_a_resolve": "立场A解决方案",
    "pole_b_resolve": "立场B解决方案",
    "pole_a": "立场A",
    "pole_b": "立场B",
    "Pole A": "立场A",
    "Pole B": "立场B",
    # 旅程地图相关
    "Journey Map": "旅程地图",
    "journey map": "旅程地图",
    "User Journey": "用户旅程",
    "Customer Journey": "客户旅程",
    "Touchpoint": "触点",
    "touchpoint": "触点",
    # 常见设计术语
    "Key Takeaways": "关键要点",
    "Key takeaways": "关键要点",
    "Best Practices": "最佳实践",
    "best practices": "最佳实践",
    "Case Study": "案例研究",
    "case study": "案例研究",
    "Deep Dive": "深度研究",
    "deep dive": "深度研究",
    "Next Steps": "下一步",
    "next steps": "下一步",
    "Action Items": "行动项",
    "action items": "行动项",
    "Trade-offs": "权衡",
    "trade-offs": "权衡",
    "Pros and Cons": "优缺点",
    "pros and cons": "优缺点",
}


def _translate_content(text: str) -> str:
    """翻译内容中的英文短语为中文"""
    if not text or not isinstance(text, str):
        return text

    result = text
    for eng, chn in CONTENT_TRANSLATIONS.items():
        result = result.replace(eng, chn)

    return result


def _clean_markdown_inline(text: str) -> str:
    """v7.26.3: 清理行内Markdown格式（用于短文本）

    去除 **加粗** 和 *斜体* 标记，保留文本内容
    """
    if not text or not isinstance(text, str):
        return text


    # 去除 **加粗**
    result = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    # 去除 *斜体*
    result = re.sub(r"\*(.+?)\*", r"\1", result)
    return result


def _format_numbered_list(text: str) -> str:
    """将连续的编号列表拆分成独立行

    例如: "1. xxx 2. yyy 3. zzz" -> "1. xxx\n2. yyy\n3. zzz"
    """
    if not text or not isinstance(text, str):
        return text


    # 匹配 "数字. " 或 "数字、" 或 "数字）" 前面有内容的情况
    # 在编号前插入换行（但不是开头的编号）
    result = re.sub(r"([。；，、\.\)）])\s*(\d+[\.\、\)）]\s*)", r"\1\n\2", text)

    return result


def _format_dict_to_pdf(pdf: PDFGenerator, data: dict, depth: int = 0):
    """递归格式化字典数据到 PDF

    增强版：
    - depth=0 (顶级) 时添加分隔线
    - 改进列表和嵌套结构的间距
    -  v7.26.1: 顶层跳过 content，嵌套层允许
    """
    is_top_level = depth == 0
    item_count = 0

    for key, value in data.items():
        # 跳过重复内容字段
        if key.lower() in SKIP_FIELDS:
            continue

        #  v7.26.1: 顶层时额外跳过 content（可能与 structured_data 重复）
        if is_top_level and key.lower() in TOP_LEVEL_SKIP_FIELDS:
            continue

        label = _get_field_label(key)

        if value is None or (isinstance(value, str) and not value.strip()):
            continue

        # 顶级字段之间添加分隔线（除了第一个）
        if is_top_level and item_count > 0:
            pdf.add_divider()
        item_count += 1

        if isinstance(value, list):
            if not value:
                continue
            # 列表标题
            level = min(depth + 2, 4) if is_top_level else min(depth + 3, 4)
            pdf.chapter_title(label, level)

            for idx, item in enumerate(value):
                if isinstance(item, dict):
                    # 交付物列表项之间添加小间距
                    if idx > 0:
                        pdf.ln(3)
                    _format_dict_to_pdf(pdf, item, depth + 1)
                else:
                    #  v7.26.3: 清理列表项中的Markdown格式
                    item_str = _translate_content(str(item).strip())
                    item_str = _clean_markdown_inline(item_str)
                    if item_str:
                        pdf.list_item(item_str)
            pdf.ln(3)

        elif isinstance(value, dict):
            if not value:
                continue
            level = min(depth + 2, 4) if is_top_level else min(depth + 3, 4)
            pdf.chapter_title(label, level)
            _format_dict_to_pdf(pdf, value, depth + 1)

        else:
            #  v7.26.3: 先翻译，再清理Markdown格式
            value_str = _translate_content(str(value).strip())
            value_str = _clean_markdown_inline(value_str)
            if not value_str:
                continue

            # 计算标签和值的实际显示宽度
            pdf._set_font_safe("B", 10)
            label_text = f"{label}: "
            label_width = pdf.get_string_width(label_text) + 2

            pdf._set_font_safe("", 10)
            value_width = pdf.get_string_width(value_str)

            # 页面可用宽度
            page_width = pdf.w - pdf.l_margin - pdf.r_margin

            # 决定显示方式：
            # 1. 如果标签+值能在一行显示 → 同行
            # 2. 如果值本身超过页面宽度的80% → 作为段落（标签单独一行作为标题）
            # 3. 否则 → 标签: 换行显示值

            if label_width + value_width <= page_width - 5:
                # 情况1: 能在一行显示
                pdf.set_text_color(51, 51, 51)
                pdf.set_x(pdf.l_margin)
                pdf._set_font_safe("B", 10)
                pdf.cell(label_width, 6, label_text, ln=False)
                pdf._set_font_safe("", 10)
                pdf.set_text_color(0, 0, 0)
                pdf.cell(0, 6, value_str, ln=True)
                pdf.set_x(pdf.l_margin)
                pdf.ln(2)
            elif value_width > page_width * 0.8:
                # 情况2: 长文本，作为段落显示
                level = min(depth + 2, 4) if is_top_level else min(depth + 3, 4)
                pdf.chapter_title(label, level)
                pdf.body_text(value_str)
            else:
                # 情况3: 中等长度，标签后换行显示值
                pdf.set_text_color(51, 51, 51)
                pdf.set_x(pdf.l_margin)
                pdf._set_font_safe("B", 10)
                pdf.cell(0, 6, label_text, ln=True)
                pdf._set_font_safe("", 10)
                pdf.set_text_color(0, 0, 0)
                pdf.set_x(pdf.l_margin)
                from fpdf.enums import WrapMode

                pdf.multi_cell(w=0, h=5, text=value_str, wrapmode=WrapMode.CHAR)
                pdf.set_x(pdf.l_margin)
                pdf.ln(2)


async def generate_all_experts_pdf_async(expert_reports: Dict[str, str], user_input: str = "") -> bytes:
    """异步生成所有专家报告的合并 PDF（使用 HTML + Playwright 方案）

    v7.1.2 性能优化：使用异步版本，充分利用浏览器池
    """
    import json

    # 转换专家数据格式
    experts = []
    for expert_name, expert_content in expert_reports.items():
        # 解析内容
        content = expert_content
        if isinstance(expert_content, str):
            try:
                content = json.loads(expert_content)
            except json.JSONDecodeError:
                content = {"分析内容": expert_content}

        experts.append({"expert_name": expert_name, "content": content})

    # 使用异步 HTML PDF 生成器
    generator = HTMLPDFGenerator()
    pdf_bytes = await generator.generate_pdf_async(
        experts=experts,
        title="专家报告合集",
        subtitle=user_input[:100] + "..." if len(user_input) > 100 else user_input if user_input else None,
        session_id=None,
    )

    return pdf_bytes


def generate_all_experts_pdf(expert_reports: Dict[str, str], user_input: str = "") -> bytes:
    """生成所有专家报告的合并 PDF（使用 HTML + Playwright 方案）

    注意：此为同步版本，在 FastAPI 异步上下文中推荐使用 generate_all_experts_pdf_async
    """
    import json

    # 转换专家数据格式
    experts = []
    for expert_name, expert_content in expert_reports.items():
        # 解析内容
        content = expert_content
        if isinstance(expert_content, str):
            try:
                content = json.loads(expert_content)
            except json.JSONDecodeError:
                content = {"分析内容": expert_content}

        experts.append({"expert_name": expert_name, "content": content})

    # 使用新的 HTML PDF 生成器
    pdf_bytes = generate_html_pdf(
        experts=experts,
        title="专家报告合集",
        subtitle=user_input[:100] + "..." if len(user_input) > 100 else user_input if user_input else None,
        session_id=None,
    )

    return pdf_bytes


def generate_all_experts_pdf_fast(expert_reports: Dict[str, str], user_input: str = "") -> bytes:
    """
     v7.1.3: 快速生成所有专家报告 PDF (使用 FPDF)

    替代 Playwright 方案，提供极速生成体验。
    """
    pdf = PDFGenerator()

    # 封面
    pdf.add_cover_page("专家报告汇总")

    # 目录
    pdf.add_page()
    pdf._set_font_safe("B", 18)
    pdf.set_text_color(26, 26, 26)
    pdf.cell(0, 15, "专家列表", ln=True, align="C")
    pdf.ln(10)
    pdf._set_font_safe("", 12)
    pdf.set_text_color(51, 51, 51)

    # 收集专家列表用于目录
    expert_names = list(expert_reports.keys())
    for i, name in enumerate(expert_names, 1):
        pdf.cell(0, 10, f"{i}. {name}", ln=True)

    # 用户输入
    if user_input:
        pdf.add_page()
        pdf.chapter_title("用户原始需求", level=1)
        pdf.body_text(user_input)

    # 专家内容
    for expert_name, content in expert_reports.items():
        pdf.add_page()
        pdf.chapter_title(expert_name, level=1)
        format_expert_content_for_pdf(pdf, content)

    return bytes(pdf.output())
