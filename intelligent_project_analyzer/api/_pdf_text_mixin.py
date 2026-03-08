"""
PDF生成器 文本处理/翻译 Mixin
由 scripts/refactor/_split_mt15_html_pdf.py 自动生成 (MT-15)
"""
from __future__ import annotations

from typing import Any, Dict, List


class PDFTextMixin:
    """Mixin — PDF生成器 文本处理/翻译 Mixin"""
    def _nl2br(text: str) -> str:
        """将换行符转为 <br> 标签"""
        if not text:
            return ""
        return text.replace("\n", "<br>\n")

    def _normalize_newlines(self, text: str) -> str:
        """统一处理所有换行符格式

        处理以下情况：
        1. 字面字符串 \\n（反斜杠+n）→ 实际换行
        2. 连续空格+\\n → 换行
        3. \\n\\n → 段落分隔
        """
        if not text:
            return text

        # 处理字面 \n（JSON 中的转义换行）
        text = text.replace("\\n\\n", "\n\n")  # 段落先处理
        text = text.replace("\\n", "\n")  # 单换行

        # 处理 \r\n
        text = text.replace("\r\n", "\n")

        return text

    def _simple_markdown(self, text: str) -> str:
        """简单的 Markdown 转 HTML，包含格式清理"""
        if not text:
            return ""

        # 第零步：统一换行符格式（处理字面 \n）
        text = self._normalize_newlines(text)

        # 第一步：清理 JSON 符号
        text = self._clean_json_artifacts(text)

        # 第二步：翻译英文内容
        text = self._translate_all_english(text)

        # 第三步：统一列表格式
        text = self._unify_list_format(text)

        # 转义 HTML（在清理之后）
        text = text.replace("&", "&amp;")

        # 标题
        text = re.sub(r"^### (.+)$", r"<h3>\1</h3>", text, flags=re.MULTILINE)
        text = re.sub(r"^## (.+)$", r"<h2>\1</h2>", text, flags=re.MULTILINE)
        text = re.sub(r"^# (.+)$", r"<h1>\1</h1>", text, flags=re.MULTILINE)

        # 粗体和斜体
        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)

        # 代码块
        text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)

        # 段落分隔（双换行变成段落间距）
        text = re.sub(r"\n\n+", "<br><br>\n", text)

        # 单换行
        text = text.replace("\n", "<br>\n")

        return text

    def _translate_all_english(self, text: str) -> str:
        """从根源上翻译所有英文内容

        策略：
        1. 先替换已知的固定短语
        2. 处理英文+中文混合格式
        3. 处理纯英文单词（通过词典）
        """
        if not text:
            return text

        result = text

        # 1. 替换已知的固定短语（按长度降序，避免短串干扰长串）
        sorted_translations = sorted(self.CONTENT_TRANSLATIONS.items(), key=lambda x: len(x[0]), reverse=True)
        for eng, chn in sorted_translations:
            result = result.replace(eng, chn)

        # 2. 处理英文+中文混合格式 (如 visualmerchandising策略)
        def replace_mixed(match):
            eng_part = match.group(1).lower()
            chn_part = match.group(2)
            # 先查完整组合
            full_key = eng_part + chn_part
            if full_key in self.CONTENT_TRANSLATIONS:
                return self.CONTENT_TRANSLATIONS[full_key]
            # 查英文部分
            if eng_part in self.FIELD_LABELS:
                return self.FIELD_LABELS[eng_part] + chn_part
            # 在 CONTENT_TRANSLATIONS 中模糊匹配
            for eng, chn in self.CONTENT_TRANSLATIONS.items():
                if eng.lower().replace(" ", "").replace("_", "") == eng_part:
                    return chn + chn_part
            return match.group(0)

        result = re.sub(r"([a-zA-Z]{3,})([\u4e00-\u9fff]+)", replace_mixed, result)

        # 3. 处理独立的纯英文单词/短语（3个字母以上）
        def replace_pure_english(match):
            word = match.group(0)
            word_lower = word.lower().replace(" ", "_")
            # 在 FIELD_LABELS 中查找
            if word_lower in self.FIELD_LABELS:
                return self.FIELD_LABELS[word_lower]
            # 在 CONTENT_TRANSLATIONS 中查找
            for eng, chn in self.CONTENT_TRANSLATIONS.items():
                if eng.lower() == word.lower():
                    return chn
            return word

        # 匹配连续的英文单词（可能带空格）
        result = re.sub(r"\b[A-Za-z][a-z]{2,}(?:\s+[A-Za-z][a-z]+)*\b", replace_pure_english, result)

        return result

    def _unify_list_format(self, text: str, is_sublist: bool = False) -> str:
        """统一所有列表格式

        Args:
            text: 要处理的文本
            is_sublist: 是否为子列表（子列表添加缩进）

        一级列表（加粗标签前）：1. **标签**: 内容
        二级列表（子列表）：    1. 内容（带缩进）
        """
        if not text:
            return text

        # 缩进前缀
        indent = "&nbsp;&nbsp;&nbsp;&nbsp;" if is_sublist else ""

        # === 第一步：将所有编号格式统一为临时标记 ===
        # 处理圆圈数字 ①②③
        circled_numbers = "①②③④⑤⑥⑦⑧⑨⑩"
        for i, cn in enumerate(circled_numbers, 1):
            text = text.replace(cn, f"__LIST_ITEM_{i}__")

        # 处理 1) 2) 格式
        text = re.sub(r"(\d+)\)\s*", r"__LIST_ITEM_\1__", text)

        # 处理 1） 2） 格式（全角括号）
        text = re.sub(r"(\d+)）\s*", r"__LIST_ITEM_\1__", text)

        # 处理 1、 2、 格式
        text = re.sub(r"(\d+)、\s*", r"__LIST_ITEM_\1__", text)

        # 处理 1. 2. 格式（保留，但统一化）- 但不处理加粗标签前的编号
        # 检测 "数字. **" 模式，这是一级编号，保留原样
        text = re.sub(r"(\d+)\.\s+(?!\*\*)", r"__LIST_ITEM_\1__", text)

        # === 第二步：将临时标记转换为统一格式 ===
        def format_list_item(match):
            num = match.group(1)
            return f"<br>{indent}{num}. "

        text = re.sub(r"__LIST_ITEM_(\d+)__", format_list_item, text)

        # === 第三步：清理格式 ===
        # 移除开头的换行
        text = re.sub(r"^(<br>\s*)+", "", text)
        # 合并连续换行
        text = re.sub(r"(<br>\s*)+", "<br>", text)

        return text

    def translate_label(self, key: str) -> str:
        """翻译字段标签

        支持处理以下格式:
        - 普通字段: design_rationale -> 设计理据
        - 带编号字段: q1_高效流转体验 -> 问题1: 高效流转体验
        - 下划线连接: project_vision_summary -> 项目愿景摘要
        - 混合中英文: mepoverall策略 -> MEP总体策略
        """
        if not key:
            return key

        # 首先检查 CONTENT_TRANSLATIONS 中是否有直接匹配（处理混合中英文）
        if key in self.CONTENT_TRANSLATIONS:
            return self.CONTENT_TRANSLATIONS[key]

        key_lower = key.lower().replace(" ", "_").replace("-", "_")

        # 检查是否在映射表中（完全匹配）
        if key_lower in self.FIELD_LABELS:
            return self.FIELD_LABELS[key_lower]

        # 检查 CONTENT_TRANSLATIONS 中是否有匹配（不区分大小写）
        for eng, chn in self.CONTENT_TRANSLATIONS.items():
            if eng.lower().replace(" ", "").replace("_", "") == key_lower.replace("_", ""):
                return chn

        # 处理混合中英文格式：将英文部分翻译
        # 例如: mepoverall策略 -> MEP总体策略
        # 也处理: visualmerchandising策略 -> 视觉营销策略
        if not key.isascii():
            # 提取英文部分和中文部分
            eng_part_match = re.match(r"^([a-zA-Z_]+)([\u4e00-\u9fff]+)$", key)
            if eng_part_match:
                eng_part = eng_part_match.group(1).lower()
                chn_part = eng_part_match.group(2)
                # 先检查完整的混合格式是否有翻译
                full_key = eng_part + chn_part
                if full_key in self.CONTENT_TRANSLATIONS:
                    return self.CONTENT_TRANSLATIONS[full_key]
                # 再检查英文部分
                if eng_part in self.FIELD_LABELS:
                    return self.FIELD_LABELS[eng_part] + chn_part
                # 尝试在 CONTENT_TRANSLATIONS 中查找
                for eng_key, chn_val in self.CONTENT_TRANSLATIONS.items():
                    if eng_key.lower().replace(" ", "").replace("_", "") == eng_part:
                        return chn_val + chn_part

        # 处理 q1_xxx, q2_xxx, q10_xxx 等格式 (问卷问题)
        q_match = re.match(r"^[qQ](\d+)[_\s]*(.*)$", key)
        if q_match:
            q_num = q_match.group(1)
            q_content = q_match.group(2)
            if q_content:
                # 将下划线替换为空格，但保留中文
                q_content = q_content.replace("_", " ").strip()
                # 如果内容是全英文下划线格式，尝试翻译
                content_key = q_content.lower().replace(" ", "_")
                if content_key in self.FIELD_LABELS:
                    q_content = self.FIELD_LABELS[content_key]
                return f"问题{q_num}: {q_content}"
            return f"问题{q_num}"

        # 尝试分词翻译：将 business_goal_analysis 拆分为各个单词
        parts = key_lower.split("_")
        translated_parts = []
        for part in parts:
            if part in self.FIELD_LABELS:
                translated_parts.append(self.FIELD_LABELS[part])
            else:
                translated_parts.append(part)

        # 如果有任何部分被翻译了，组合返回
        if any(p != parts[i] for i, p in enumerate(translated_parts)):
            return "".join(translated_parts)

        # 尝试将下划线转为空格，使标签更可读
        readable = key.replace("_", " ").strip()

        # 如果是全英文，首字母大写
        if readable and readable.isascii():
            return readable.title()

        return readable if readable else key

    def translate_content(self, text: str) -> str:
        """翻译内容中的英文短语和字段名

        处理以下情况:
        1. 固定短语翻译 (CONTENT_TRANSLATIONS)
        2. JSON 格式中的字段名: "field_name": -> "中文名":
        3. 字典显示格式中的字段名: 'field_name': -> '中文名':
        4. 独立出现的下划线字段名
        5. | xxx: 格式的标题行 -> 翻译并换行
        6. 纯英文标题自动翻译
        """
        if not text:
            return text

        result = text

        # 0. 处理 | xxx: 格式的标题（如 | Key Takeaways:）
        def replace_pipe_heading(match):
            heading = match.group(1).strip()
            # 查找翻译
            translated = heading
            for eng, chn in self.CONTENT_TRANSLATIONS.items():
                if eng.lower() == heading.lower() or eng.lower() == heading.rstrip(":").lower():
                    translated = chn
                    break
            # 如果没找到翻译，尝试用 translate_label
            if translated == heading:
                translated = self.translate_label(heading.rstrip(":"))
            return f"<br><strong>{translated.rstrip(':')}</strong>：<br>"

        result = re.sub(r"\|\s*([A-Za-z][A-Za-z\s]+:?)\s*", replace_pipe_heading, result)

        # 1. 替换固定短语
        for eng, chn in self.CONTENT_TRANSLATIONS.items():
            result = result.replace(eng, chn)

        # 2. 处理纯英文标题（如 visualmerchandising策略）
        # 匹配英文+中文的混合格式
        def replace_mixed_label(match):
            eng_part = match.group(1).lower()
            chn_part = match.group(2)
            # 在 FIELD_LABELS 中查找
            if eng_part in self.FIELD_LABELS:
                return self.FIELD_LABELS[eng_part] + chn_part
            # 在 CONTENT_TRANSLATIONS 中查找
            for eng, chn in self.CONTENT_TRANSLATIONS.items():
                if eng.lower().replace(" ", "").replace("_", "") == eng_part:
                    return chn + chn_part
            return match.group(0)

        result = re.sub(r"([a-zA-Z]+)([\u4e00-\u9fff]+)", replace_mixed_label, result)

        # 2. 替换 JSON/字典格式中的字段名: "field_name": 或 'field_name':
        def replace_field_in_quotes(match):
            quote = match.group(1)  # " 或 '
            field = match.group(2)  # 字段名
            translated = self.translate_label(field)
            # 如果翻译后仍是英文（首字母大写格式），保持原样
            if translated == field.replace("_", " ").title():
                return match.group(0)
            return f"{quote}{translated}{quote}:"

        # 匹配 "xxx_xxx": 或 'xxx_xxx': 格式
        result = re.sub(r'(["\'])([a-z][a-z0-9_]*)\1\s*:', replace_field_in_quotes, result)

        # 3. 替换独立出现的下划线字段名（作为标题）
        def replace_standalone_field(match):
            field = match.group(1)
            translated = self.translate_label(field)
            if translated == field.replace("_", " ").title():
                return match.group(0)
            return translated

        # 匹配行首或空格后的 xxx_xxx 格式（通常是字段名作为标题）
        result = re.sub(
            r"(?:^|(?<=\s))([a-z][a-z0-9]*(?:_[a-z0-9]+)+)(?=\s*[:：]|\s*$)",
            replace_standalone_field,
            result,
            flags=re.MULTILINE,
        )

        return result

