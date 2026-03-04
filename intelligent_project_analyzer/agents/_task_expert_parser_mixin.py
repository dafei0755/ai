"""
ExpertOutputParserMixin

专家输出解析与质量校准相关方法，从 task_oriented_expert_factory.py 中拆分。
由 TaskOrientedExpertFactory 通过多重继承引入。
"""

import json
import re
from typing import Any, Dict, List

from loguru import logger

from ..core.task_oriented_models import TaskOrientedExpertOutput


class ExpertOutputParserMixin:
    """Mixin: 专家输出解析 + 质量校准"""

    def _detect_gibberish(self, text: str) -> bool:
        """
         v7.271: 检测文本是否包含乱码/幻觉内容

        检测规则:
        1. 无效URL模式 (test, placeholder, example)
        2. 连续无意义汉字 (无标点分隔的长串)
        3. 重复字符模式

        Args:
            text: 待检测的文本

        Returns:
            bool: True 表示检测到乱码
        """
        import re

        if not text:
            return False

        text_str = str(text)

        # 检测无效URL模式（不受长度限制）
        invalid_url_patterns = [
            r"http://[a-z]+/test\d+",  # 测试URL如 http://locear/test0010456
            r"(?:^|[^a-zA-Z])(?:example\.com|example2\.com|placeholder|locear)(?:[^a-zA-Z]|$)",  # 占位符域名
        ]
        for pattern in invalid_url_patterns:
            if re.search(pattern, text_str, re.IGNORECASE):
                return True

        # 以下检测仅对较长文本有效
        if len(text_str) < 50:
            return False

        # 检测连续无意义汉字（30+汉字无标点分隔）
        # 正常中文每10-15字会有标点
        chinese_without_punct = re.findall(r"[\u4e00-\u9fff]{30,}", text_str)
        for segment in chinese_without_punct:
            # 检查这段文字是否缺少标点
            if not re.search(r'[。，！？、；：""' "（）【】]", segment):
                return True

        # 检测重复字符模式（同一字符连续出现5次以上）
        if re.search(r"(.)\1{5,}", text_str):
            return True

        return False


    def _parse_and_validate_output(self, expert_output: str, role_object: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析并验证专家输出是否符合TaskOrientedExpertOutput结构
        如果验证失败，使用降级策略构造默认结构

         v7.11 增强: 更强的 JSON 预处理 + 多种修复策略
        """
        try:
            #  v7.11: 先进行全局预处理，移除所有markdown代码块标记
            cleaned_output = expert_output.strip()

            # 移除所有markdown代码块标记（包括```json, ```JSON, ``` 等变体）
            import re

            # 处理 ```json 或 ```JSON 开头
            if re.search(r"^```(?:json|JSON)?\s*", cleaned_output):
                cleaned_output = re.sub(r"^```(?:json|JSON)?\s*", "", cleaned_output)
            # 处理结尾的 ```
            cleaned_output = re.sub(r"\s*```$", "", cleaned_output)
            # 处理中间可能存在的代码块标记
            cleaned_output = re.sub(r"```(?:json|JSON)?\s*([\s\S]*?)\s*```", r"\1", cleaned_output)

            logger.debug(f" JSON预处理后长度: {len(cleaned_output)}")

            # 提取JSON内容
            if "{" in cleaned_output and "}" in cleaned_output:
                json_str = cleaned_output[cleaned_output.find("{") : cleaned_output.rfind("}") + 1]
            else:
                logger.warning("输出不包含有效JSON，尝试整体解析")
                json_str = cleaned_output.strip()

            #  尝试解析JSON（多种修复策略）
            parsed_output = self._try_parse_json_with_fixes(json_str)

            if parsed_output is None:
                raise json.JSONDecodeError("所有JSON修复策略都失败了", json_str, 0)

            # 验证结构（使用Pydantic模型验证）
            task_oriented_output = TaskOrientedExpertOutput(**parsed_output)

            logger.info(f" 成功验证 {role_object.get('role_name', 'Unknown')} 的TaskOrientedExpertOutput结构")
            return task_oriented_output.dict()

        except json.JSONDecodeError as e:
            logger.error(f" JSON解析失败: {str(e)}")
            logger.error(f"原始输出: {expert_output[:200]}...")
        except Exception as e:
            logger.error(f" 输出验证失败: {str(e)}")

        # 降级策略：构造符合最小规范的默认结构
        logger.warning(f"️ 使用降级策略为 {role_object.get('role_name', 'Unknown')} 构造默认输出")
        return self._create_fallback_output(expert_output, role_object)


    def _try_parse_json_with_fixes(self, json_str: str) -> Dict[str, Any] | None:
        """
        尝试多种策略修复并解析 JSON

        常见问题:
        1. 缺少逗号分隔符
        2. 多余的逗号
        3. 转义字符问题
        4. 截断的 JSON
        """
        import re

        # 策略1: 直接解析
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

        # 策略2: 移除控制字符并重试
        try:
            cleaned = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", json_str)
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # 策略3: 修复常见的逗号问题
        try:
            # 移除数组/对象末尾多余的逗号
            fixed = re.sub(r",\s*([}\]])", r"\1", json_str)
            # 添加缺失的逗号（对象属性之间）
            fixed = re.sub(r'"\s*\n\s*"', '",\n"', fixed)
            # 添加缺失的逗号（数组元素之间）
            fixed = re.sub(r"}\s*\n\s*{", "},\n{", fixed)
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass

        # 策略4: 尝试修复截断的 JSON
        try:
            # 计算未闭合的括号
            open_braces = json_str.count("{") - json_str.count("}")
            open_brackets = json_str.count("[") - json_str.count("]")

            if open_braces > 0 or open_brackets > 0:
                # 尝试补全括号
                fixed = json_str
                fixed += "}" * open_braces
                fixed += "]" * open_brackets
                return json.loads(fixed)
        except json.JSONDecodeError:
            pass

        # 策略5: 提取最外层的有效 JSON 对象
        try:
            # 找到第一个 { 到最后一个对应的 }
            depth = 0
            start = -1
            end = -1
            for i, c in enumerate(json_str):
                if c == "{":
                    if depth == 0:
                        start = i
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break

            if start >= 0 and end > start:
                return json.loads(json_str[start:end])
        except json.JSONDecodeError:
            pass

        logger.warning("️ 所有JSON修复策略都失败了")
        return None


    def _create_fallback_output(self, raw_output: str, role_object: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建降级输出结构（当Pydantic验证失败时）

         v7.6: 增强对嵌套 JSON 的处理，避免显示原始代码
        """
        role_name = role_object.get("dynamic_role_name", role_object.get("role_name", "Unknown Expert"))

        #  尝试提取实际内容而不是原始 JSON
        cleaned_content = self._extract_meaningful_content(raw_output)

        return {
            "task_execution_report": {
                "deliverable_outputs": [
                    {
                        "deliverable_name": "分析报告",
                        "content": cleaned_content,
                        "completion_status": "completed",
                        "completion_rate": 1.0,
                        "notes": "使用降级策略生成的输出",
                        "quality_self_assessment": 0.7,
                    }
                ],
                "task_completion_summary": f"{role_name}已完成分析任务",
                "additional_insights": None,
                "execution_challenges": ["LLM未按预期格式返回，使用降级策略"],
            },
            "protocol_execution": {
                "protocol_status": "complied",
                "compliance_confirmation": "接受需求分析师的洞察",
                "challenge_details": None,
                "reinterpretation": None,
            },
            "execution_metadata": {
                "confidence": 0.7,
                "completion_rate": 1.0,
                "execution_time_estimate": "未知",
                "execution_notes": "此输出使用降级策略生成，未经标准验证",
                "dependencies_satisfied": True,
            },
        }


    def _calibrate_quality_scores(
        self, structured_output: Dict[str, Any], recorder: Any | None = None
    ) -> Dict[str, Any]:
        """
         v7.154: 自评分校准 - 基于内容特征客观调整LLM自评分

        LLM自评分往往虚高（都在0.9+），此方法基于客观指标进行校准：
        1. 内容长度：过短的内容降低评分
        2. 搜索引用：缺少真实引用降低评分
        3. 具体案例：缺少具体案例降低评分
        4. 数据支撑：缺少数据支撑降低评分

         v7.154.1: 调整惩罚系数，使校准更温和
        - 原惩罚总和最高 0.33，导致 0.95 → 0.62
        - 新惩罚总和最高 0.20，使 0.95 → 0.75

        Args:
            structured_output: 专家的结构化输出
            recorder: 工具调用记录器（用于检查搜索引用）

        Returns:
            校准后的结构化输出
        """
        try:
            task_exec_report = structured_output.get("task_execution_report", {})
            deliverable_outputs = task_exec_report.get("deliverable_outputs", [])

            if not deliverable_outputs:
                return structured_output

            # 获取真实搜索引用数量
            real_search_refs_count = 0
            if recorder:
                search_refs = recorder.get_search_references()
                # 过滤掉占位符URL
                real_search_refs_count = len(
                    [
                        ref
                        for ref in search_refs
                        if ref.get("url")
                        and not any(
                            placeholder in ref.get("url", "").lower()
                            for placeholder in ["example.com", "example2.com", "placeholder"]
                        )
                    ]
                )

            for deliverable in deliverable_outputs:
                original_score = deliverable.get("quality_self_assessment", 0.9)
                content = deliverable.get("content", "")

                # 计算惩罚 ( v7.154.1: 调整惩罚系数)
                penalties = 0.0

                # 1. 内容长度惩罚 (降低惩罚)
                content_length = len(str(content)) if content else 0
                if content_length < 200:
                    penalties += 0.10  # 原 0.15
                    logger.debug(f"   内容过短惩罚: -0.10 (长度: {content_length})")
                elif content_length < 500:
                    penalties += 0.03  # 原 0.05
                    logger.debug(f"   内容较短惩罚: -0.03 (长度: {content_length})")

                # 2. 搜索引用惩罚 (降低惩罚)
                if real_search_refs_count == 0:
                    penalties += 0.05  # 原 0.1
                    logger.debug("   缺少搜索引用惩罚: -0.05")
                elif real_search_refs_count < 3:
                    penalties += 0.02  # 原 0.05
                    logger.debug(f"   搜索引用较少惩罚: -0.02 (数量: {real_search_refs_count})")

                # 3. 具体案例检测 (降低惩罚)
                content_str = str(content).lower() if content else ""
                case_keywords = ["案例", "例如", "比如", "实例", "case", "example"]
                has_cases = any(kw in content_str for kw in case_keywords)
                if not has_cases:
                    penalties += 0.03  # 原 0.05
                    logger.debug("   缺少具体案例惩罚: -0.03")

                # 4. 数据支撑检测 (降低惩罚)
                data_patterns = ["数据", "统计", "调研", "研究表明", "%", "比例", "增长"]
                has_data = any(pattern in content_str for pattern in data_patterns)
                if not has_data:
                    penalties += 0.02  # 原 0.03
                    logger.debug("   缺少数据支撑惩罚: -0.02")

                # 计算校准后的评分 ( v7.154.1: 提高最低分)
                calibrated_score = max(0.6, original_score - penalties)  # 原 0.5

                if penalties > 0:
                    deliverable_name = deliverable.get("deliverable_name", "未知")
                    logger.info(
                        f" [v7.154] 自评分校准: {deliverable_name} "
                        f"{original_score:.2f} → {calibrated_score:.2f} (惩罚: -{penalties:.2f})"
                    )
                    deliverable["quality_self_assessment"] = calibrated_score
                    deliverable["quality_calibration_note"] = f"原始评分{original_score:.2f}，校准后{calibrated_score:.2f}"

            return structured_output

        except Exception as e:
            logger.warning(f"️ [v7.154] 自评分校准失败: {e}")
            return structured_output


    def _extract_meaningful_content(self, raw_output: str) -> Any:
        """
        从原始输出中提取有意义的内容

        处理:
        1. Markdown 代码块包裹的 JSON
        2. 嵌套的 task_execution_report
        3. 直接返回解析后的结构化数据
        """
        if not raw_output:
            return "暂无输出"

        text = raw_output.strip()

        # 移除 markdown 代码块
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        # 尝试解析 JSON
        if text.startswith("{") or text.startswith("["):
            try:
                parsed = json.loads(text)

                # 如果是完整的 TaskOrientedExpertOutput 结构
                if isinstance(parsed, dict):
                    # 提取 deliverable_outputs 中的内容
                    ter = parsed.get("task_execution_report", {})
                    if ter:
                        deliverable_outputs = ter.get("deliverable_outputs", [])
                        if deliverable_outputs:
                            # 返回第一个交付物的内容
                            first = deliverable_outputs[0]
                            if isinstance(first, dict):
                                content = first.get("content")
                                if content:
                                    # 如果内容本身也是 JSON 字符串，递归处理
                                    if isinstance(content, str) and (
                                        content.strip().startswith("{") or content.strip().startswith("[")
                                    ):
                                        return self._extract_meaningful_content(content)
                                    return content

                    # 返回解析后的结构（让前端自行渲染）
                    return parsed

            except json.JSONDecodeError:
                pass

        # 返回清理后的文本
        return text

