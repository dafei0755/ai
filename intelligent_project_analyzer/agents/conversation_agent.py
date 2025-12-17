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
    
    # 系统提示词模板 - 🔥 v7.14: 开放性增强
    SYSTEM_PROMPT = """你是一个专业的项目分析顾问助手，名叫「设计高参 AI」。

你的职责：
1. 帮助用户理解刚刚完成的项目分析报告
2. 回答关于报告内容的任何问题
3. 提供深入的解释和补充信息
4. 🔥 发挥专业知识，扩展回答视野
5. 保持专业、友好、耐心的语气

回答规范：
✅ 优先基于报告内容回答，引用具体章节和数据
✅ 可以结合专业知识扩展回答（用【扩展知识】标注）
✅ 可以提供行业案例和最佳实践（用【业界参考】标注）
✅ 使用结构化格式（标题、列表、要点）
✅ 鼓励用户继续追问和深挖
⚠️ 明确区分报告内容 vs 扩展知识（标注来源）
❌ 不要使用过于技术化的术语

当前分析报告上下文：
{context_summary}

对话历史：
{conversation_history}
"""
    
    # 🔥 v7.14: 问题类型专属提示词
    INTENT_PROMPTS = {
        # 闭环问题：严格基于报告
        "closed": """【闭环模式】用户询问的是报告中的具体内容，请严格基于报告回答：
- 直接引用报告中的数据和结论
- 指出具体章节位置
- 如报告未涉及，明确说明""",
        
        # 开放问题（基于报告扩展）：允许扩展但标注来源
        "open_with_context": """【扩展模式】用户希望获得更广泛的见解，在报告基础上扩展回答：
- 首先回应报告中的相关内容【📖 报告内容】
- 然后补充专业知识和行业经验【🌐 扩展知识】
- 可以提供类似案例参考【📚 业界参考】
- 确保用户能区分哪些是报告结论，哪些是扩展建议""",
        
        # 创意发散问题：充分发挥LLM能力
        "creative": """【创意模式】用户希望进行头脑风暴或探索性讨论：
- 自由发挥专业知识和创意思维
- 提供多种可能性和方向
- 鼓励「What-if」假设性探讨
- 结合行业趋势和前沿理念【💡 创意建议】
- 可以跨领域类比借鉴【🔗 跨界启发】""",
        
        # 通用问题
        "general": """请综合报告内容和专业知识回答，注意标注信息来源。"""
    }
    
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
        
        # 🔥 v7.14: 启用增强意图分类
        intent = self._classify_intent(question, conversation_history)
        logger.info(f"🎯 Detected intent: {intent}")
        
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
        
        # 4. 🔥 v7.14: 生成智能后续建议（传入intent）
        suggestions = self._generate_suggestions(
            question=question,
            answer=answer_data["answer"],
            context=context,
            intent=intent
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
    ) -> Literal["closed", "open_with_context", "creative", "general"]:
        """
        🔥 v7.14: 增强意图分类 - 区分问题类型以选择回答模式
        
        分类维度：
        - closed: 闭环问题，询问报告具体内容（数据、结论、章节）
        - open_with_context: 开放问题，希望在报告基础上扩展
        - creative: 创意问题，头脑风暴、假设性探讨
        - general: 通用问题，默认模式
        """
        question_lower = question.lower()
        
        # === 闭环问题关键词 ===
        closed_keywords = [
            # 报告定位类
            "报告中", "报告里", "分析结果", "专家说", "哪个专家",
            "第几章", "哪一章", "哪个部分", "在哪里提到",
            # 精确询问类
            "具体是什么", "原文是", "怎么说的", "结论是什么",
            "数据是多少", "比例是", "占比", "总结了什么"
        ]
        
        # === 开放扩展问题关键词 ===
        open_keywords = [
            # 扩展探索类
            "还有什么", "除此之外", "补充", "扩展", "更多",
            "类似案例", "类似的", "行业经验", "最佳实践", "业界",
            "有没有案例", "案例参考",
            # 深入探讨类
            "为什么", "怎么理解", "如何解读", "背后原因",
            "有什么建议", "你觉得", "你认为"
        ]
        
        # === 创意发散问题关键词 ===
        creative_keywords = [
            # 假设性问题
            "如果", "假设", "假如", "what if", "what-if",
            "万一", "要是", "设想",
            # 头脑风暴类
            "有没有可能", "能不能", "可以怎么", "还能怎样",
            "突破", "创新", "颠覆", "大胆一点", "大胆",
            "更大胆", "激进", "前卫",
            # 跨领域类
            "其他行业", "跨界", "借鉴", "类比", "参考其他"
        ]
        
        # 优先级：creative > open > closed > general
        for keyword in creative_keywords:
            if keyword in question_lower:
                logger.info(f"🎨 意图分类: creative (匹配关键词: {keyword})")
                return "creative"
        
        for keyword in open_keywords:
            if keyword in question_lower:
                logger.info(f"🌐 意图分类: open_with_context (匹配关键词: {keyword})")
                return "open_with_context"
        
        for keyword in closed_keywords:
            if keyword in question_lower:
                logger.info(f"📖 意图分类: closed (匹配关键词: {keyword})")
                return "closed"
        
        # 默认使用开放模式（充分发挥LLM能力）
        logger.info("💬 意图分类: general (默认模式)")
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

        # 🔥 v7.14: 根据意图选择提示词模式
        intent_prompt = self.INTENT_PROMPTS.get(intent, self.INTENT_PROMPTS["general"])
        
        # 构建提示词 - 开放性增强版
        system_message = f"""你是一个专业的项目分析顾问助手，名叫「设计高参 AI」。

你的职责：
1. 帮助用户理解刚刚完成的项目分析报告
2. 回答关于报告内容的任何问题
3. 提供深入的解释和补充信息
4. 🔥 充分发挥专业知识，提供高价值洞察
5. 保持专业、友好、耐心的语气

{intent_prompt}

回答规范：
✅ 使用结构化格式（标题、列表、要点）
✅ 明确标注信息来源（📖报告/🌐扩展/💡创意）
✅ 鼓励用户继续追问和深挖
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
        context: ConversationContext,
        intent: str = "general"
    ) -> List[str]:
        """
        🔥 v7.14: 智能后续建议生成 - 根据问题类型推荐不同方向
        
        策略：
        - 闭环问题 → 引导深挖报告细节
        - 开放问题 → 引导行业对标和扩展
        - 创意问题 → 引导What-if和跨界思考
        """
        # === 基础建议池 ===
        closed_suggestions = [
            "这部分报告的具体数据来源是什么？",
            "专家是基于什么理由得出这个结论的？",
            "报告中有没有提到相关的风险点？",
            "能展开说说这个方案的执行步骤吗？"
        ]
        
        open_suggestions = [
            "有没有类似的成功案例可以参考？",
            "业界目前的最佳实践是怎样的？",
            "这个方向未来3-5年的趋势是什么？",
            "还有哪些我可能忽略的关键点？"
        ]
        
        creative_suggestions = [
            "如果预算翻倍，方案会怎么变化？",
            "其他行业有什么可以借鉴的创新做法？",
            "有没有更大胆的替代方案？",
            "如果从零开始设计，你会怎么做？"
        ]
        
        general_suggestions = [
            "能详细展开这部分吗？",
            "你怎么看这个方案的可行性？",
            "还有什么需要我特别注意的？"
        ]
        
        # === 根据意图选择建议 ===
        if intent == "closed":
            # 闭环问题 → 引导向开放扩展
            return open_suggestions[:2] + creative_suggestions[:1]
        elif intent == "open_with_context":
            # 开放问题 → 引导深挖 + 创意
            return closed_suggestions[:1] + creative_suggestions[:2]
        elif intent == "creative":
            # 创意问题 → 继续发散 + 落地
            return creative_suggestions[:2] + closed_suggestions[:1]
        else:
            # 通用 → 混合建议
            return general_suggestions[:3]
