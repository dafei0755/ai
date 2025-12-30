"""
LLM语义安全检测器
用于处理边界复杂场景的深度语义分析
"""

import json
import re
from typing import Dict, Any, Optional
from loguru import logger


class LLMSafetyDetector:
    """LLM语义安全检测器"""

    # 安全检测提示词模板
    SAFETY_CHECK_PROMPT = """你是内容安全审核专家。请仔细检查以下文本是否包含不合规内容。

文本：
{text}

检查维度：
1. 政治敏感内容（政治立场、政治人物、政治事件等）
2. 色情低俗内容（性暗示、露骨描写、色情服务等）
3. 暴力血腥内容（暴力行为、血腥描写、自残自杀等）
4. 违法犯罪内容（毒品、诈骗、赌博、洗钱等）
5. 歧视仇恨内容（种族歧视、性别歧视、地域歧视等）
6. 虚假信息（明显的谣言、误导性陈述等）
7. 侵犯隐私（他人隐私信息、非公开个人数据等）

特别注意：
- 如果是设计行业的正常讨论（如"色彩设计"、"灯光效果"），应该判定为安全
- 如果是建筑相关的正常术语（如"结构稳定性"、"承重墙"），应该判定为安全
- 需要理解上下文语境，避免误判

请以JSON格式输出：
{{
    "is_safe": true/false,
    "confidence": 0.0-1.0,
    "violation": {{
        "category": "违规类别",
        "reason": "详细原因说明",
        "severity": "high/medium/low",
        "method": "llm_semantic_analysis"
    }}
}}

如果内容安全，返回：{{"is_safe": true, "confidence": 1.0}}"""

    # 边界场景提示词（更严格的检测）
    EDGE_CASE_PROMPT = """你是资深的内容安全审核专家。当前文本已通过基础检测，但可能存在隐性违规。请进行深度语义分析。

文本：
{text}

深度分析维度：
1. **隐性暗示**：是否通过隐喻、暗示等方式传达违规信息
2. **语境误导**：是否利用专业术语掩盖违规内容
3. **变形规避**：是否使用谐音、拆字等方式绕过检测
4. **引导诱导**：是否引导用户进行违规行为
5. **灰色地带**：是否处于合规与违规的边界

分析要求：
- 理解文本的深层含义和潜在意图
- 考虑不同文化和语境下的理解差异
- 判断是否有明显的违规倾向

请以JSON格式输出：
{{
    "is_safe": true/false,
    "confidence": 0.0-1.0,
    "risk_indicators": ["风险指标1", "风险指标2"],
    "violation": {{
        "category": "违规类别",
        "reason": "详细分析",
        "severity": "medium/low",
        "method": "llm_deep_semantic_analysis"
    }}
}}

如果内容安全，返回：{{"is_safe": true, "confidence": 1.0, "risk_indicators": []}}"""

    def __init__(self, llm_model=None, confidence_threshold: float = 0.7):
        """
        初始化LLM语义安全检测器

        Args:
            llm_model: LLM模型实例（LangChain格式）
            confidence_threshold: 置信度阈值，低于此值不采信检测结果
        """
        self.llm_model = llm_model
        self.confidence_threshold = confidence_threshold

    def check(self, text: str, mode: str = "normal") -> Dict[str, Any]:
        """
        检查文本安全性

        Args:
            text: 待检测文本
            mode: 检测模式
                - "normal": 常规检测
                - "edge_case": 边界场景深度检测

        Returns:
            {
                "is_safe": bool,
                "confidence": float,
                "violation": Dict | None,
                "risk_indicators": List[str] (仅edge_case模式)
            }
        """
        if not self.llm_model:
            logger.warning("⚠️ LLM模型未配置，跳过语义检测")
            return {"is_safe": True, "confidence": 0.0, "violation": None}

        try:
            # 选择提示词模板
            if mode == "edge_case":
                prompt = self.EDGE_CASE_PROMPT.format(text=text)
            else:
                prompt = self.SAFETY_CHECK_PROMPT.format(text=text)

            # 调用LLM
            response = self._invoke_llm(prompt)

            # 解析响应
            result = self._parse_response(response)

            # 验证置信度
            confidence = result.get("confidence", 0.0)
            if confidence < self.confidence_threshold:
                logger.info(f"LLM检测置信度过低 ({confidence:.2f} < {self.confidence_threshold})，忽略结果")
                return {"is_safe": True, "confidence": confidence, "violation": None}

            return result

        except Exception as e:
            logger.error(f"❌ LLM语义检测异常: {e}")
            # 出错时默认安全，避免误拦截
            return {"is_safe": True, "confidence": 0.0, "violation": None, "error": str(e)}

    def _invoke_llm(self, prompt: str) -> str:
        """调用LLM模型"""
        try:
            from langchain_core.messages import HumanMessage

            messages = [HumanMessage(content=prompt)]
            response = self.llm_model.invoke(messages)

            # 提取内容
            if hasattr(response, 'content'):
                return response.content
            return str(response)

        except Exception as e:
            logger.error(f"❌ LLM调用失败: {e}")
            raise

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """解析LLM响应"""
        try:
            # 提取JSON（支持markdown代码块包裹）
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 直接查找JSON对象
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group()
                else:
                    raise ValueError("响应中未找到JSON格式内容")

            # 解析JSON
            result = json.loads(json_str)

            # 验证必需字段
            if "is_safe" not in result:
                raise ValueError("响应缺少is_safe字段")

            # 标准化返回格式
            return {
                "is_safe": result.get("is_safe", True),
                "confidence": result.get("confidence", 1.0),
                "violation": result.get("violation"),
                "risk_indicators": result.get("risk_indicators", [])
            }

        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON解析失败: {e}")
            logger.debug(f"原始响应: {response}")
            raise ValueError(f"无效的JSON响应: {e}")

        except Exception as e:
            logger.error(f"❌ 响应解析异常: {e}")
            raise

    def batch_check(self, texts: list, mode: str = "normal") -> list:
        """
        批量检测文本

        Args:
            texts: 文本列表
            mode: 检测模式

        Returns:
            检测结果列表
        """
        results = []
        for text in texts:
            result = self.check(text, mode)
            results.append(result)
        return results
