"""
PDF生成器 解析/格式化 Mixin
由 scripts/refactor/_split_mt15_html_pdf.py 自动生成 (MT-15)
"""
from __future__ import annotations

from typing import Any, Dict, List


class PDFParseMixin:
    """Mixin — PDF生成器 解析/格式化 Mixin"""
    def _try_parse_dict_string(self, text: str) -> Dict | None:
        """尝试将字符串解析为字典

        支持 Python 字典格式: {'key': 'value', ...}
        和 JSON 格式: {"key": "value", ...}
        """
        if not text or not isinstance(text, str):
            return None

        text = text.strip()

        # 检查是否像字典格式
        if not (text.startswith("{") and text.endswith("}")):
            # 也检查是否像 'q1_xxx': 这种键值对格式
            if not re.search(r"'[a-zA-Z_][a-zA-Z0-9_]*'\s*:", text):
                return None

        try:
            # 尝试用 ast.literal_eval 解析 Python 字典
            import ast

            result = ast.literal_eval(text)
            if isinstance(result, dict):
                return result
        except Exception:
            pass

        try:
            # 尝试用 JSON 解析
            import json

            result = json.loads(text)
            if isinstance(result, dict):
                return result
        except Exception:
            pass

        return None

    def _clean_json_artifacts(self, text: str) -> str:
        """清理文本中残留的JSON/字典符号

         v7.1 增强：处理 deliverable_outputs 等复杂结构
        """
        if not text:
            return text

        text = text.strip()

        #  首先处理字面换行符（\n 作为字符串）
        text = text.replace("\\n\\n", "\n\n")
        text = text.replace("\\n", "\n")

        # 移除空数组标记 [''] 或 [""] 或 []
        text = re.sub(r"\[''\]", "", text)
        text = re.sub(r'\[""\]', "", text)
        text = re.sub(r"\[\]", "", text)
        text = re.sub(r"\[\s*\]", "", text)

        #  处理 'key': 'value', 'key2': 'value2' 格式（字典展开为可读格式）
        # 先检测是否为字典字符串格式
        if re.match(r"^\s*['\"][a-zA-Z_\u4e00-\u9fff]", text):
            # 将字典键值对转为可读格式
            # 'deliverable_name': 'xxx', 'content': 'yyy' →
            # **交付物名称**: xxx\n**内容**: yyy
            def format_dict_pair(match):
                key = match.group(1)
                value = match.group(2)
                # 翻译键名
                translated_key = self.translate_label(key)
                # 清理值中的引号
                value = value.strip("'\"")
                return f"\n**{translated_key}**：{value}"

            # 匹配 'key': 'value' 或 "key": "value" 模式
            text = re.sub(r"['\"]([a-zA-Z_][a-zA-Z0-9_]*)['\"]:\s*['\"]([^'\"]+)['\"]", format_dict_pair, text)
            # 移除残留的逗号分隔符
            text = re.sub(r",\s*(?=\n\*\*)", "", text)

        # 移除开头和结尾的大括号
        while text.startswith("{") and text.endswith("}"):
            text = text[1:-1].strip()

        # 移除开头和结尾的方括号
        while text.startswith("[") and text.endswith("]"):
            text = text[1:-1].strip()

        # 移除开头的方括号（如果内容以 [ 开头但不以 ] 结尾）
        if text.startswith("["):
            text = text[1:].strip()
        if text.endswith("]"):
            text = text[:-1].strip()

        # 移除字段名格式的引号: 'key': 或 "key":
        text = re.sub(r"['\"]([a-zA-Z_][a-zA-Z0-9_]*)['\"]:\s*", r"\1: ", text)

        # 移除值周围的单引号（但保留中文内容）
        # 匹配 ': 'xxx' 或 ', 'xxx' 格式
        text = re.sub(r":\s*'([^']+)'", r": \1", text)
        text = re.sub(r",\s*'([^']+)'", r", \1", text)

        # 移除残留的单独引号
        text = re.sub(r"(?<![a-zA-Z\u4e00-\u9fff])'(?![a-zA-Z\u4e00-\u9fff])", "", text)

        # 移除残留的大括号
        text = text.replace("{", "").replace("}", "")

        # 处理 Q&A 格式: "问题？: 答案" -> "问题？<br>答案"
        # 匹配中文问号或英文问号后跟冒号的模式
        text = re.sub(r"([？?])\s*[:：]\s*", r"\1<br>", text)

        # 将逗号分隔的项目转为换行（如果是列表项）
        # 检测 ', ' 后跟字母或中文的模式
        if ", " in text and not re.search(r"\d+[)）]", text):
            # 不是编号列表，可能是逗号分隔的项目
            pass  # 暂不处理，避免误伤正常句子

        return text.strip()

    def _clean_and_format_value(self, value: Any, is_nested: bool = False) -> str:
        """清理和格式化值，用于显示

        Args:
            value: 要格式化的值
            is_nested: 是否是嵌套的子项（用于控制 bullet 层级）
        """
        if value is None:
            return ""

        if isinstance(value, list | tuple):
            # 过滤空值
            valid_items = [item for item in value if item is not None and item != "" and item != []]
            if not valid_items:
                return ""
            # 只有一个项目时不加序号
            if len(valid_items) == 1:
                return self._clean_and_format_value(valid_items[0], is_nested)
            # 多个项目，使用序号列表
            items = [self._clean_and_format_value(item, is_nested=True) for item in valid_items]
            formatted_items = []
            for i, item in enumerate(items, 1):
                if item:
                    # 子列表使用缩进样式
                    formatted_items.append(f"&nbsp;&nbsp;&nbsp;&nbsp;{i}. {item}")
            return "<br>".join(formatted_items)

        if isinstance(value, dict):
            # 跳过 confidence 字段
            filtered_dict = {k: v for k, v in value.items() if k.lower() not in ("confidence", "置信度", "conf")}
            if not filtered_dict:
                return ""
            # 字典展开为键值对，加粗标签前不加序号
            parts = []
            for k, v in filtered_dict.items():
                label = self.translate_label(k)
                val = self._clean_and_format_value(v, is_nested=True)
                if val:
                    # 如果值包含多行（有换行），在标签后也换行
                    if "<br>" in val:
                        parts.append(f"<strong>{label}</strong>:<br>{val}")
                    else:
                        parts.append(f"<strong>{label}</strong>: {val}")
            return "<br><br>".join(parts)  #  用双换行分隔不同字段

        text = str(value)
        #  先处理字面换行符
        text = self._normalize_newlines(text)
        # 清理 JSON 符号
        text = self._clean_json_artifacts(text)
        # 翻译英文
        text = self._translate_all_english(text)
        # 统一列表格式（作为子列表处理）
        text = self._unify_list_format(text, is_sublist=True)
        #  最后将换行符转为 <br>
        text = text.replace("\n\n", "<br><br>")
        text = text.replace("\n", "<br>")

        return text

    def _format_object_list(self, obj_list: List[Dict]) -> str:
        """格式化对象列表为HTML内容

        用于案例研究、竞争分析等结构化数据
        加粗标签前不加序号
        """
        if not obj_list:
            return ""

        parts = []
        for obj in obj_list:
            obj_parts = []
            for k, v in obj.items():
                # 跳过 confidence 字段
                if k.lower() in ("confidence", "置信度", "conf"):
                    continue
                if v is None or v == "":
                    continue

                label = self.translate_label(k)

                # 处理值
                if isinstance(v, list):
                    # 列表值，格式化为带缩进的序号列表
                    list_items = []
                    for i, item in enumerate(v, 1):
                        cleaned = self._clean_json_artifacts(str(item))
                        cleaned = self._translate_all_english(cleaned)
                        if cleaned:
                            # 子列表添加缩进
                            list_items.append(f"&nbsp;&nbsp;&nbsp;&nbsp;{i}. {cleaned}")
                    val = "<br>".join(list_items)
                elif isinstance(v, dict):
                    val = self._clean_and_format_value(v)
                else:
                    val = self._clean_json_artifacts(str(v))
                    val = self._translate_all_english(val)
                    # 子列表处理
                    val = self._unify_list_format(val, is_sublist=True)

                if val:
                    # 如果值包含多行，在标签后换行
                    if "<br>" in val:
                        obj_parts.append(f"<strong>{label}</strong>:<br>{val}")
                    else:
                        obj_parts.append(f"<strong>{label}</strong>: {val}")

            if obj_parts:
                parts.append("<br>".join(obj_parts))

        # 用双换行分隔不同对象
        return "<br><br>".join(parts)

    def _format_numbered_text(self, text: str) -> str:
        """格式化编号文本，在编号前添加换行

        处理规则:
        - 如果只有一个编号项（如 0) 或 1)），移除编号前缀
        - 如果有多个编号项，在每个编号前添加换行
        """
        if not text:
            return text

        # 先统计编号数量
        number_matches = list(re.finditer(r"(\d+)[)）\.、]\s*", text))

        if len(number_matches) == 0:
            return text

        if len(number_matches) == 1:
            # 只有一个编号，移除编号前缀
            result = re.sub(r"^(\d+)[)）\.、]\s*", "", text.strip())
            return result

        # 多个编号，在编号前添加换行（除了第一个）
        result = re.sub(r"(?<!\A)(?<![<\n])(\s*)(\d+)[)）\.、]\s*", r"<br>\2) ", text)

        # 确保第一个编号格式正确
        result = re.sub(r"^(\d+)[)）\.、]\s*", r"\1) ", result)

        return result

    def format_numbered_list(self, text: str) -> List[str]:
        """解析编号列表，返回各项内容"""
        if not text:
            return []

        # 检测是否包含编号列表模式
        pattern = r"(\d+)[\.\、\)）]\s*"

        # 尝试分割
        parts = re.split(pattern, text)

        if len(parts) <= 1:
            # 不是编号列表，返回原文
            return [text]

        items = []
        # parts 格式: ['前缀', '1', '内容1', '2', '内容2', ...]
        i = 1
        while i < len(parts) - 1:
            parts[i]
            content = parts[i + 1].strip() if i + 1 < len(parts) else ""
            if content:
                items.append(content)
            i += 2

        return items if items else [text]

    def _parse_deliverable_outputs(self, title: str, value: Any) -> Dict[str, Any] | None:
        """ v7.1: 专门处理交付物输出字段

        交付物输出是 v7.0 任务导向架构的核心输出格式，包含：
        - deliverable_name: 交付物名称
        - content: 交付物内容（可能包含大量 \n 换行）
        - completion_status: 完成状态
        - quality_self_assessment: 质量自评

        Args:
            title: 已翻译的标题
            value: 字段值（可能是字符串、字典或列表）
        """
        if not value:
            return None

        # 如果是字符串，尝试解析
        if isinstance(value, str):
            # 先处理换行符
            value = self._normalize_newlines(value)

            # 尝试解析为字典/列表
            try:
                import ast

                parsed = ast.literal_eval(value)
                value = parsed
            except Exception:
                try:
                    import json

                    parsed = json.loads(value)
                    value = parsed
                except Exception:
                    # 无法解析，按普通文本处理
                    return {"title": title, "type": "text", "content": self._simple_markdown(value)}

        # 处理列表格式（多个交付物）
        if isinstance(value, list):
            formatted_parts = []
            for idx, item in enumerate(value, 1):
                if isinstance(item, dict):
                    formatted_parts.append(self._format_single_deliverable(item, idx))
                else:
                    # 字符串项
                    text = self._normalize_newlines(str(item))
                    formatted_parts.append(self._simple_markdown(text))

            return {"title": title, "type": "text", "content": "<br><br>".join(formatted_parts)}

        # 处理单个字典格式
        if isinstance(value, dict):
            return {"title": title, "type": "text", "content": self._format_single_deliverable(value)}

        return None

    def _format_single_deliverable(self, deliverable: Dict[str, Any], index: int = None) -> str:
        """格式化单个交付物

        Args:
            deliverable: 交付物字典
            index: 序号（可选）
        """
        parts = []

        # 交付物名称（作为标题）
        name = deliverable.get("deliverable_name", deliverable.get("name", ""))
        if name:
            if index:
                parts.append(f"<strong>{index}. {name}</strong>")
            else:
                parts.append(f"<strong>{name}</strong>")

        # 完成状态
        status = deliverable.get("completion_status", "")
        if status:
            status_label = self.translate_label(status)
            parts.append(f"<em>状态: {status_label}</em>")

        # 内容（最重要，需要仔细处理换行）
        content = deliverable.get("content", "")
        if content:
            # 处理换行符
            content = self._normalize_newlines(str(content))
            # 清理 JSON 符号
            content = self._clean_json_artifacts(content)
            # 翻译
            content = self._translate_all_english(content)
            # 转换换行为 HTML
            content = content.replace("\n\n", "<br><br>")
            content = content.replace("\n", "<br>")
            parts.append(content)

        # 质量自评
        quality = deliverable.get("quality_self_assessment", "")
        if quality:
            parts.append(f"<br><em>质量自评: {quality}</em>")

        return "<br>".join(parts)

    def parse_expert_content(self, expert_data: Dict[str, Any]) -> Dict[str, Any]:
        """解析专家数据，转换为模板所需格式

        Args:
            expert_data: 专家原始数据

        Returns:
            格式化后的专家数据，包含 sections 列表
        """
        expert_name = expert_data.get("expert_name", expert_data.get("name", "专家"))
        expert_role = expert_data.get("role", expert_data.get("expert_role", ""))
        content = expert_data.get("content", expert_data.get("analysis", {}))

        sections = []

        if isinstance(content, str):
            # 纯文本内容
            translated = self.translate_content(content)
            sections.append({"title": "分析内容", "type": "text", "content": self._simple_markdown(translated)})
        elif isinstance(content, dict):
            # 字典内容，按字段处理
            for key, value in content.items():
                section = self._parse_field(key, value)
                if section:
                    sections.append(section)
        elif isinstance(content, list):
            # 列表内容
            sections.append(
                {"title": "分析要点", "type": "list", "list_items": [self.translate_content(str(item)) for item in content]}
            )

        return {"name": expert_name, "role": expert_role, "sections": sections}

    def _parse_field(self, key: str, value: Any) -> Dict[str, Any] | None:
        """解析单个字段

        Args:
            key: 字段名
            value: 字段值

        Returns:
            解析后的 section 数据
        """
        if value is None or value == "" or value == []:
            return None

        # 跳过置信度字段
        key_lower = key.lower()
        if key_lower in ("confidence", "置信度", "conf"):
            return None

        title = self.translate_label(key)

        #  v7.1: 特殊处理 deliverable_outputs（交付物输出）
        if key_lower in ("deliverable_outputs", "deliverable_answers"):
            return self._parse_deliverable_outputs(title, value)

        if isinstance(value, str):
            # 尝试解析字符串中的字典格式
            parsed_dict = self._try_parse_dict_string(value)
            if parsed_dict:
                # 成功解析为字典，递归处理
                # 如果只有一个键且是 q1_xxx 格式，直接展开为问答格式
                if len(parsed_dict) == 1:
                    single_key = list(parsed_dict.keys())[0]
                    single_value = parsed_dict[single_key]
                    # 对于单个 q_xxx 格式的问题，提取纯问题内容
                    q_match = re.match(r"^[qQ](\d+)[_\s]*(.*)$", single_key)
                    if q_match:
                        q_content = q_match.group(2)
                        if q_content:
                            # 将下划线替换为空格
                            q_content = q_content.replace("_", " ").strip()
                            q_label = q_content
                        else:
                            q_label = self.translate_label(single_key)
                    else:
                        q_label = self.translate_label(single_key)
                    q_value = self._clean_and_format_value(single_value)
                    # 格式化为问答
                    return {
                        "title": title,
                        "type": "qa",
                        "question": q_label.replace(": ", "").rstrip(":"),
                        "answer": q_value,
                    }

                fields = []
                for k, v in parsed_dict.items():
                    # 跳过 confidence 字段
                    if k.lower() in ("confidence", "置信度", "conf"):
                        continue
                    label = self.translate_label(k)
                    if isinstance(v, dict):
                        # 嵌套字典，继续展开，也要跳过 confidence
                        nested_fields = []
                        for nk, nv in v.items():
                            if nk.lower() in ("confidence", "置信度", "conf"):
                                continue
                            nested_fields.append(
                                {"label": self.translate_label(nk), "value": self._clean_and_format_value(nv)}
                            )
                        if nested_fields:
                            fields.append({"label": label, "value": "", "nested": nested_fields})
                    else:
                        fields.append({"label": label, "value": self._clean_and_format_value(v)})
                if fields:
                    return {"title": title, "type": "fields", "fields": fields}

            translated = self.translate_content(value)
            # 清理可能残留的JSON符号
            translated = self._clean_json_artifacts(translated)

            # 检测是否为编号列表
            if re.search(r"\d+[\.、\)）]\s*\S", translated):
                items = self.format_numbered_list(translated)
                if len(items) > 1:
                    return {"title": title, "type": "numbered_list", "list_items": items}

            # 普通文本
            return {"title": title, "type": "text", "content": self._simple_markdown(translated)}

        elif isinstance(value, list):
            if all(isinstance(item, str) for item in value):
                # 字符串列表 - 使用序号列表
                cleaned_items = [self._clean_json_artifacts(self.translate_content(item)) for item in value if item]
                return {"title": title, "type": "numbered_list", "list_items": cleaned_items}
            elif all(isinstance(item, dict) for item in value):
                # 对象列表，格式化为结构化内容（加粗标签，不加序号）
                if len(value) > 0:
                    # 将对象列表转为格式化的字段显示
                    formatted_content = self._format_object_list(value)
                    return {"title": title, "type": "text", "content": formatted_content}
            else:
                # 混合列表
                cleaned_items = [
                    self._clean_json_artifacts(self.translate_content(str(item))) for item in value if item
                ]
                return {"title": title, "type": "numbered_list", "list_items": cleaned_items}

        elif isinstance(value, dict):
            # 嵌套字典，展开为字段组
            fields = []
            for k, v in value.items():
                # 跳过 confidence 字段
                if k.lower() in ("confidence", "置信度", "conf"):
                    continue
                if v is not None and v != "":
                    fields.append(
                        {
                            "label": self.translate_label(k),
                            "value": self._simple_markdown(self.translate_content(str(v))),
                        }
                    )
            if fields:
                return {"title": title, "type": "fields", "fields": fields}

        else:
            # 其他类型
            return {"title": title, "type": "text", "content": str(value)}

        return None

