"""
用户意图解析器

基于LLM或关键词分析用户输入的意图
"""

import json
import re
from typing import Dict, Any, Optional
from loguru import logger
from langchain_core.messages import HumanMessage

try:
    from intelligent_project_analyzer.core.prompt_manager import PromptManager
    PROMPT_MANAGER_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ PromptManager 不可用，将使用硬编码配置")
    PROMPT_MANAGER_AVAILABLE = False


class UserIntentParser:
    """用户意图解析器 - 支持对话式交互"""
    
    def __init__(self, llm_model=None):
        """
        初始化意图解析器

        Args:
            llm_model: LLM模型实例（可选，如果提供则使用LLM解析）
        """
        self.llm = llm_model

        # 加载配置（优先从 YAML，降级到硬编码）
        self.config = self._load_config()

        # 关键词映射（从配置加载）
        self.intent_keywords = self.config.get("keywords", self._get_default_keywords())

        # LLM 提示词模板（从配置加载）
        self.llm_prompt_template = self.config.get("llm_prompt", self._get_default_prompt())

        # 意图类型定义（从配置加载）
        self.intent_types = self.config.get("intent_types", self._get_default_intent_types())

        # 否定词列表（从配置加载）
        self.negation_words = self.config.get("negation_words", self._get_default_negation_words())
    
    def parse(
        self,
        user_input: Any,
        context: str = "",
        stage: str = ""
    ) -> Dict[str, Any]:
        """
        解析用户输入的意图
        
        Args:
            user_input: 用户输入（字符串或字典）
            context: 上下文信息
            stage: 当前阶段（calibration/confirmation/review等）
            
        Returns:
            {
                "intent": "approve|add|modify|skip|revise|reject",
                "content": "提取的关键内容",
                "original_input": "原始输入",
                "confidence": 0.9,
                "method": "llm|keyword|dict"
            }
        """
        # 1. 如果已经是字典格式（API或按钮），直接返回
        if isinstance(user_input, dict):
            return self._handle_dict_input(user_input)
        
        # 2. 转换为字符串
        user_text = str(user_input).strip()
        
        # 3. 如果是简单的单词，快速匹配
        if len(user_text) < 20 and not any(char in user_text for char in "，。、！？"):
            result = self._quick_match(user_text)
            if result:
                return result
        
        # 4. 如果有LLM，使用LLM解析
        if self.llm:
            try:
                return self._llm_parse(user_text, context, stage)
            except Exception as e:
                logger.warning(f"LLM解析失败，降级到关键词匹配: {e}")
        
        # 5. 降级到关键词匹配
        return self._keyword_parse(user_text)
    
    def _handle_dict_input(self, user_dict: Dict) -> Dict:
        """处理字典格式的输入（兼容原有API）"""
        return {
            "intent": user_dict.get("action", "approve"),
            "content": user_dict.get("additional_info") or user_dict.get("modifications") or user_dict.get("feedback", ""),
            "original_input": user_dict,
            "confidence": 1.0,
            "method": "dict",
            "answers": user_dict.get("answers"),
            "modifications": user_dict.get("modifications"),
            "additional_info": user_dict.get("additional_info")
        }
    
    def _quick_match(self, user_text: str) -> Optional[Dict]:
        """快速匹配简单输入"""
        text_lower = user_text.lower()
        
        for intent, keywords in self.intent_keywords.items():
            for keyword in keywords:
                if text_lower == keyword.lower():
                    logger.info(f"🎯 快速匹配: '{user_text}' → {intent}")
                    return {
                        "intent": intent,
                        "content": "",
                        "original_input": user_text,
                        "confidence": 1.0,
                        "method": "quick_match"
                    }
        
        return None
    
    def _llm_parse(self, user_text: str, context: str, stage: str) -> Dict:
        """使用LLM解析用户意图"""
        logger.info(f"🤖 使用LLM解析用户意图: {user_text[:50]}...")

        # 使用配置中的提示词模板
        prompt = self.llm_prompt_template.format(
            stage=stage,
            context=context,
            user_text=user_text
        )
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            content = response.content.strip()
            
            # 提取JSON（去除markdown代码块标记）
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            result = json.loads(content)
            
            logger.info(f"🤖 LLM解析结果: intent={result['intent']}, reasoning={result.get('reasoning', '')[:50]}")
            
            return {
                "intent": result["intent"],
                "content": result.get("content", ""),
                "original_input": user_text,
                "confidence": 0.9,
                "method": "llm",
                "reasoning": result.get("reasoning", "")
            }
            
        except Exception as e:
            logger.error(f"LLM解析JSON失败: {e}")
            # 降级到关键词
            return self._keyword_parse(user_text)
    
    def _keyword_parse(self, user_text: str) -> Dict:
        """基于关键词解析用户意图"""
        logger.info(f"🔍 使用关键词匹配: {user_text[:50]}...")
        
        text_lower = user_text.lower()
        
        # 计算每个意图的匹配分数
        scores = {}
        for intent, keywords in self.intent_keywords.items():
            score = sum(1 for kw in keywords if kw.lower() in text_lower)
            if score > 0:
                scores[intent] = score
        
        # 特殊处理：如果同时包含批准和补充/修改
        if "approve" in scores and ("add" in scores or "modify" in scores):
            # "确认，但我还需要..." → 优先识别为add/modify
            if scores.get("add", 0) > 0:
                intent = "add"
            elif scores.get("modify", 0) > 0:
                intent = "modify"
            else:
                intent = "approve"
        elif scores:
            # 选择得分最高的意图
            intent = max(scores, key=scores.get)
        else:
            # 没有匹配，默认处理
            if len(user_text) > 10:
                intent = "add"  # 长文本当作补充
            else:
                intent = "approve"  # 短文本当作批准
        
        logger.info(f"🔍 关键词匹配结果: {intent} (scores: {scores})")
        
        return {
            "intent": intent,
            "content": user_text if intent in ["add", "modify"] else "",
            "original_input": user_text,
            "confidence": 0.7,
            "method": "keyword"
        }

    def _load_config(self) -> Dict[str, Any]:
        """
        加载配置（优先从 YAML，失败则降级到硬编码）

        Returns:
            配置字典
        """
        if not PROMPT_MANAGER_AVAILABLE:
            logger.info("📋 使用硬编码配置（PromptManager 不可用）")
            return self._get_default_config()

        try:
            prompt_manager = PromptManager()

            # PromptManager 直接通过 prompts 属性访问配置
            if "intent_parser" in prompt_manager.prompts:
                config = prompt_manager.prompts["intent_parser"]
                logger.info("✅ 成功从 YAML 加载 intent_parser 配置")
                return config
            else:
                logger.warning("⚠️ YAML 配置未找到，使用硬编码配置")
                return self._get_default_config()

        except Exception as e:
            logger.warning(f"⚠️ 加载 YAML 配置失败: {e}，使用硬编码配置")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """
        获取默认硬编码配置（作为降级方案）

        Returns:
            默认配置字典
        """
        return {
            "keywords": self._get_default_keywords(),
            "llm_prompt": self._get_default_prompt(),
            "intent_types": self._get_default_intent_types(),
            "negation_words": self._get_default_negation_words()
        }

    def _get_default_keywords(self) -> Dict[str, list]:
        """获取默认关键词映射"""
        return {
            "approve": ["批准", "确认", "同意", "继续", "好的", "可以", "没问题", "approve", "confirm", "ok", "yes"],
            "add": ["补充", "增加", "还需要", "另外", "还有", "add", "also", "additionally"],
            "modify": ["修改", "改成", "应该是", "不是", "错了", "更正", "modify", "change", "correct", "should be"],
            "skip": ["跳过", "忽略", "不需要", "skip"],
            "revise": ["重新", "再来", "重做", "revise", "redo"],
            "reject": ["拒绝", "不行", "不对", "reject", "no"]
        }

    def _get_default_prompt(self) -> str:
        """获取默认 LLM 提示词模板"""
        return """你是一个用户意图分析专家。请分析用户的输入意图。

当前阶段: {stage}
上下文: {context}

用户输入:
{user_text}

可能的意图类型:
1. approve - 批准/确认/同意/继续（无修改）
2. add - 补充额外信息或需求
3. modify - 修改已有信息（纠正错误）
4. skip - 跳过当前步骤
5. revise - 拒绝并要求重新分析
6. reject - 拒绝

分析规则:
- 如果用户说"批准"、"确认"、"好的"、"继续" → approve
- 如果用户说"我还需要..."、"另外..."、"补充..." → add
- 如果用户说"应该是..."、"改成..."、"不是..." → modify
- 如果用户说"跳过"、"不需要" → skip
- 如果用户说"重新"、"再来一遍" → revise
- 如果用户说"不行"、"拒绝" → reject

请返回JSON格式（只返回JSON，不要其他文字）:
{{
    "intent": "意图类型（approve/add/modify/skip/revise/reject）",
    "content": "提取的关键内容（如果是approve/skip则为空）",
    "reasoning": "判断理由（简短说明）"
}}
"""

    def _get_default_intent_types(self) -> list:
        """获取默认意图类型定义"""
        return [
            {
                "name": "approve",
                "display_name": "批准/确认",
                "description": "用户批准当前结果，无修改",
                "requires_content": False
            },
            {
                "name": "add",
                "display_name": "补充信息",
                "description": "用户补充额外信息或需求",
                "requires_content": True
            },
            {
                "name": "modify",
                "display_name": "修改内容",
                "description": "用户修改已有信息",
                "requires_content": True
            },
            {
                "name": "skip",
                "display_name": "跳过",
                "description": "用户跳过当前步骤",
                "requires_content": False
            },
            {
                "name": "revise",
                "display_name": "重新分析",
                "description": "用户要求重新分析",
                "requires_content": False
            },
            {
                "name": "reject",
                "display_name": "拒绝",
                "description": "用户拒绝当前结果",
                "requires_content": False
            }
        ]

    def _get_default_negation_words(self) -> list:
        """获取默认否定词列表"""
        return ["不", "不是", "没有", "别", "no", "not", "don't", "doesn't"]


# 辅助函数
def parse_user_intent(
    user_input: Any,
    llm_model=None,
    context: str = "",
    stage: str = ""
) -> Dict[str, Any]:
    """
    便捷函数：解析用户意图
    
    Args:
        user_input: 用户输入
        llm_model: LLM模型（可选）
        context: 上下文
        stage: 当前阶段
        
    Returns:
        意图解析结果
    """
    parser = UserIntentParser(llm_model)
    return parser.parse(user_input, context, stage)

