"""
对话智能体 - 专业的后分析问答系统

功能：
1. 意图识别：追问/深挖/重新分析/新分析
2. 上下文检索：语义检索相关报告内容
3. 回答生成：基于上下文的专业回答
4. 引用溯源：标注回答来源章节
5. 多轮记忆：维护对话历史上下文
"""

from typing import Dict, Any, List, Optional, Literal
from datetime import datetime
from loguru import logger
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field


class ConversationContext(BaseModel):
    """对话上下文数据模型"""
    final_report: Dict[str, Any] = Field(default_factory=dict, description="最终分析报告")
    agent_results: Dict[str, Any] = Field(default_factory=dict, description="各专家分析结果")
    requirements: Dict[str, Any] = Field(default_factory=dict, description="需求分析结果")
    user_input: str = Field(default="", description="原始用户输入")


class ConversationTurn(BaseModel):
    """单轮对话记录"""
    question: str
    answer: str
    intent: str
    referenced_sections: List[str] = Field(default_factory=list)
    timestamp: str


class ConversationAgent:
    """
    对话智能体 - 专业的后分析问答系统
    
    核心能力：
    1. 意图识别：追问/深挖/重新分析/新分析
    2. 上下文检索：语义检索相关报告内容
    3. 回答生成：基于上下文的专业回答
    4. 引用溯源：标注回答来源章节
    5. 多轮记忆：维护对话历史上下文
    """
    
    # 系统提示词模板
    SYSTEM_PROMPT = """你是一个专业的项目分析顾问助手，名叫「设计知外 AI」。

你的职责：
1. 帮助用户理解刚刚完成的项目分析报告
2. 回答关于报告内容的任何问题
3. 提供深入的解释和补充信息
4. 保持专业、友好、耐心的语气

回答规范：
✅ 基于报告内容回答，引用具体章节和数据
✅ 如果问题超出报告范围，坦诚说明并提供建议
✅ 使用结构化格式（标题、列表、要点）
✅ 鼓励用户继续追问和深挖
❌ 不要编造报告中没有的内容
❌ 不要使用过于技术化的术语

当前分析报告上下文：
{context_summary}

对话历史：
{conversation_history}
"""
    
    def __init__(self):
        """初始化对话智能体"""
        from ..services.llm_factory import LLMFactory
        # from ..services.context_retriever import ContextRetriever
        # from ..services.intent_classifier import IntentClassifier
        
        self.llm = LLMFactory.create_llm()
        # self.context_retriever = ContextRetriever()
        # self.intent_classifier = IntentClassifier()
        
        logger.info("ConversationAgent initialized")
    
    def answer_question(
        self,
        question: str,
        context: ConversationContext,
        conversation_history: Optional[List[ConversationTurn]] = None
    ) -> Dict[str, Any]:
        """
        回答用户问题
        
        Args:
            question: 用户问题
            context: 分析上下文
            conversation_history: 对话历史
        
        Returns:
            {
                "answer": str,           # 回答文本
                "intent": str,           # 识别的意图
                "references": List[str], # 引用的报告章节
                "suggestions": List[str] # 后续问题建议
            }
        """
        logger.info(f"Processing question: {question[:100]}...")
        
        # 1. 意图识别 (简化版)
        intent = "general" # self._classify_intent(question, conversation_history)
        logger.info(f"Detected intent: {intent}")
        
        # 2. 上下文检索 (简化版：直接使用全部上下文)
        relevant_context = self._retrieve_relevant_context(
            question=question,
            context=context,
            intent=intent
        )
        
        # 3. 生成回答
        answer_data = self._generate_answer(
            question=question,
            relevant_context=relevant_context,
            conversation_history=conversation_history,
            intent=intent
        )
        
        # 4. 生成后续建议
        suggestions = self._generate_suggestions(
            question=question,
            answer=answer_data["answer"],
            context=context
        )
        
        return {
            "answer": answer_data["answer"],
            "intent": intent,
            "references": answer_data["references"],
            "suggestions": suggestions
        }
    
    def _classify_intent(
        self,
        question: str,
        history: Optional[List[ConversationTurn]]
    ) -> Literal["clarification", "deep_dive", "regenerate", "new_analysis", "general"]:
        """
        意图分类 (简化版)
        """
        return "general"
    
    def _retrieve_relevant_context(
        self,
        question: str,
        context: ConversationContext,
        intent: str
    ) -> Dict[str, Any]:
        """
        检索相关上下文 (简化版：直接返回完整报告摘要)
        """
        # 简单地将 final_report 转换为字符串作为上下文
        sections = []
        
        # 尝试从 final_report 提取
        if context.final_report:
            if isinstance(context.final_report, dict):
                for key, value in context.final_report.items():
                    if isinstance(value, str):
                        sections.append({"title": key, "content": value})
                    elif isinstance(value, dict):
                        sections.append({"title": key, "content": str(value)})
            elif isinstance(context.final_report, str):
                 sections.append({"title": "完整报告", "content": context.final_report})

        # 尝试从 agent_results 提取
        if context.agent_results:
            for agent_id, result in context.agent_results.items():
                content = result.get("content", "") or str(result)
                sections.append({"title": f"专家分析: {agent_id}", "content": content})

        return {
            "sections": sections,
            "metadata": {}
        }
    
    def _generate_answer(
        self,
        question: str,
        relevant_context: Dict[str, Any],
        conversation_history: Optional[List[ConversationTurn]],
        intent: str
    ) -> Dict[str, Any]:
        """
        生成回答

        🔥 v3.11 增强：使用智能上下文管理（支持"记忆全部"模式）
        """
        # 🔥 使用FollowupHistoryManager构建智能上下文
        from ..services.followup_history_manager import FollowupHistoryManager

        # 转换历史为字典格式
        history_data = []
        if conversation_history:
            history_data = [
                {
                    "turn_id": i + 1,
                    "question": turn.question,
                    "answer": turn.answer,
                    "intent": turn.intent,
                    "referenced_sections": turn.referenced_sections,
                    "timestamp": turn.timestamp
                }
                for i, turn in enumerate(conversation_history)
            ]

        # 格式化报告摘要
        context_summary = self._format_context_summary(relevant_context)

        # 🔥 使用智能上下文管理器（临时实例）
        temp_manager = FollowupHistoryManager(session_manager=None)  # 只用方法，不用Redis

        # 构建智能上下文
        context_result = temp_manager.build_context_for_llm(
            history=history_data,
            report_summary=context_summary,
            current_question=question,
            enable_memory_all=True  # 🔥 启用"记忆全部"模式
        )

        context_str = context_result["context_str"]
        metadata = context_result["metadata"]

        # 记录上下文统计
        logger.info(f"📊 上下文构建完成: {metadata}")
        if metadata.get("truncated"):
            logger.warning(f"⚠️ 上下文已截断: 总轮次={metadata['total_turns']}, 包含轮次={metadata['included_turns']}")

        # 构建提示词
        system_message = f"""你是一个专业的项目分析顾问助手，名叫「设计高参 AI」。

你的职责：
1. 帮助用户理解刚刚完成的项目分析报告
2. 回答关于报告内容的任何问题
3. 提供深入的解释和补充信息
4. 保持专业、友好、耐心的语气

回答规范：
✅ 基于报告内容回答，引用具体章节和数据
✅ 如果问题超出报告范围，坦诚说明并提供建议
✅ 使用结构化格式（标题、列表、要点）
✅ 鼓励用户继续追问和深挖
❌ 不要编造报告中没有的内容
❌ 不要使用过于技术化的术语

{context_str}
"""

        # 调用 LLM
        messages = [
            SystemMessage(content=system_message),
            HumanMessage(content=f"""用户问题：{question}

请基于上述报告内容回答，并在回答末尾标注引用的章节（格式：📖 引用：第X章）。""")
        ]

        response = self.llm.invoke(messages)
        answer = response.content

        # 提取引用章节
        references = self._extract_references(
            answer=answer,
            context_sections=relevant_context.get("sections", [])
        )

        return {
            "answer": answer,
            "references": references,
            "context_metadata": metadata  # 🔥 返回上下文元数据
        }
    
    def _format_context_summary(self, relevant_context: Dict[str, Any]) -> str:
        """格式化上下文摘要"""
        # retrieve() 返回 {"sections": [...], "metadata": {...}}
        sections = relevant_context.get("sections", [])
        
        summary_parts = []
        for section in sections:
            content = section.get('content', '')
            # 截断内容到合理长度
            truncated_content = content[:500] + "..." if len(content) > 500 else content
            summary_parts.append(f"""
【{section.get('title', '未命名章节')}】
{truncated_content}
""")
        
        return "\n".join(summary_parts) if summary_parts else "（暂无相关上下文）"
    
    def _extract_references(
        self,
        answer: str,
        context_sections: List[Dict[str, Any]]
    ) -> List[str]:
        """从回答中提取章节引用"""
        references = []
        for section in context_sections:
            section_title = section.get('title', '')
            section_id = section.get('id', '')
            if section_title and section_title in answer:
                references.append(section_id)
            elif section_id and section_id in answer:
                references.append(section_id)
        return list(set(references))  # 去重
    
    def _generate_suggestions(
        self,
        question: str,
        answer: str,
        context: ConversationContext
    ) -> List[str]:
        """生成后续问题建议"""
        # 简化版：返回固定建议
        suggestions = [
            "能详细展开这部分的实施步骤吗？",
            "有没有类似的行业案例参考？",
            "这个方案的成本大概是多少？",
            "可以补充更多的设计细节吗？"
        ]
        return suggestions[:3]
