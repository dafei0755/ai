"""
🔥 v7.15: 追问智能体 - 基于 LangGraph 的独立 Agent

功能：
1. 意图识别节点：closed/open/creative/general
2. 上下文检索节点：从报告中提取相关内容
3. 回答生成节点：根据意图选择提示词模式
4. 建议生成节点：智能推荐后续问题
5. 支持工具扩展：预留搜索工具接口（暂未启用）

架构：
    ┌─────────────────┐
    │  classify_intent │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ retrieve_context │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ generate_answer  │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ generate_suggest │
    └────────┬────────┘
             │
             ▼
           [END]
"""

from typing import Dict, Any, List, Optional, Literal, TypedDict, Annotated
from datetime import datetime
from loguru import logger
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
import operator


# ============================================================
# 状态定义
# ============================================================

class FollowupAgentState(TypedDict):
    """追问 Agent 状态"""
    # 输入
    question: str                          # 用户问题
    report_context: Dict[str, Any]         # 报告上下文
    conversation_history: List[Dict]       # 对话历史
    
    # 中间状态
    intent: str                            # 识别的意图
    relevant_sections: List[Dict]          # 检索到的相关章节
    intent_prompt: str                     # 意图专属提示词
    
    # 输出
    answer: str                            # 生成的回答
    references: List[str]                  # 引用的章节
    suggestions: List[str]                 # 后续问题建议
    
    # 元数据
    processing_log: Annotated[List[str], operator.add]  # 处理日志（累加）


# ============================================================
# 意图分类器
# ============================================================

# 意图专属提示词
INTENT_PROMPTS = {
    "closed": """【闭环模式】用户询问的是报告中的具体内容，请严格基于报告回答：
- 直接引用报告中的数据和结论
- 指出具体章节位置
- 如报告未涉及，明确说明""",
    
    "open_with_context": """【扩展模式】用户希望获得更广泛的见解，在报告基础上扩展回答：
- 首先回应报告中的相关内容【📖 报告内容】
- 然后补充专业知识和行业经验【🌐 扩展知识】
- 可以提供类似案例参考【📚 业界参考】
- 确保用户能区分哪些是报告结论，哪些是扩展建议""",
    
    "creative": """【创意模式】用户希望进行头脑风暴或探索性讨论：
- 自由发挥专业知识和创意思维
- 提供多种可能性和方向
- 鼓励「What-if」假设性探讨
- 结合行业趋势和前沿理念【💡 创意建议】
- 可以跨领域类比借鉴【🔗 跨界启发】""",
    
    "general": """请综合报告内容和专业知识回答，注意标注信息来源。"""
}


def classify_intent_node(state: FollowupAgentState) -> Dict[str, Any]:
    """
    节点1: 意图分类
    
    分类维度：
    - closed: 闭环问题，询问报告具体内容
    - open_with_context: 开放问题，希望扩展
    - creative: 创意问题，头脑风暴
    - general: 通用问题
    """
    question = state["question"].lower()
    
    # === 闭环问题关键词 ===
    closed_keywords = [
        "报告中", "报告里", "分析结果", "专家说", "哪个专家",
        "第几章", "哪一章", "哪个部分", "在哪里提到",
        "具体是什么", "原文是", "怎么说的", "结论是什么",
        "数据是多少", "比例是", "占比", "总结了什么"
    ]
    
    # === 开放扩展问题关键词 ===
    open_keywords = [
        "还有什么", "除此之外", "补充", "扩展", "更多",
        "类似案例", "类似的", "行业经验", "最佳实践", "业界",
        "有没有案例", "案例参考",
        "为什么", "怎么理解", "如何解读", "背后原因",
        "有什么建议", "你觉得", "你认为"
    ]
    
    # === 创意发散问题关键词 ===
    creative_keywords = [
        "如果", "假设", "假如", "what if", "what-if",
        "万一", "要是", "设想",
        "有没有可能", "能不能", "可以怎么", "还能怎样",
        "突破", "创新", "颠覆", "大胆一点", "大胆",
        "更大胆", "激进", "前卫",
        "其他行业", "跨界", "借鉴", "类比", "参考其他"
    ]
    
    # 优先级：creative > open > closed > general
    intent = "general"
    matched_keyword = None
    
    for keyword in creative_keywords:
        if keyword in question:
            intent = "creative"
            matched_keyword = keyword
            break
    
    if intent == "general":
        for keyword in open_keywords:
            if keyword in question:
                intent = "open_with_context"
                matched_keyword = keyword
                break
    
    if intent == "general":
        for keyword in closed_keywords:
            if keyword in question:
                intent = "closed"
                matched_keyword = keyword
                break
    
    intent_prompt = INTENT_PROMPTS.get(intent, INTENT_PROMPTS["general"])
    
    log_msg = f"🎯 意图分类: {intent}" + (f" (关键词: {matched_keyword})" if matched_keyword else " (默认)")
    logger.info(log_msg)
    
    return {
        "intent": intent,
        "intent_prompt": intent_prompt,
        "processing_log": [log_msg]
    }


# ============================================================
# 上下文检索器
# ============================================================

def retrieve_context_node(state: FollowupAgentState) -> Dict[str, Any]:
    """
    节点2: 上下文检索
    
    从报告中提取相关章节
    """
    report_context = state.get("report_context", {})
    question = state.get("question", "")
    
    sections = []
    
    # 从 final_report 提取
    final_report = report_context.get("final_report", {})
    if isinstance(final_report, dict):
        for key, value in final_report.items():
            if isinstance(value, str):
                sections.append({"title": key, "content": value[:1000]})  # 截断
            elif isinstance(value, dict):
                sections.append({"title": key, "content": str(value)[:1000]})
    elif isinstance(final_report, str):
        sections.append({"title": "完整报告", "content": final_report[:2000]})
    
    # 从 agent_results 提取
    agent_results = report_context.get("agent_results", {})
    if isinstance(agent_results, dict):
        for agent_id, result in agent_results.items():
            if isinstance(result, dict):
                content = result.get("content", "") or str(result)
            else:
                content = str(result)
            sections.append({"title": f"专家分析: {agent_id}", "content": content[:800]})
    
    log_msg = f"📚 检索到 {len(sections)} 个相关章节"
    logger.info(log_msg)
    
    return {
        "relevant_sections": sections,
        "processing_log": [log_msg]
    }


# ============================================================
# 回答生成器
# ============================================================

def generate_answer_node(state: FollowupAgentState) -> Dict[str, Any]:
    """
    节点3: 回答生成
    
    使用 LLM 生成回答
    """
    from ..services.llm_factory import LLMFactory
    from ..services.followup_history_manager import FollowupHistoryManager
    
    question = state.get("question", "")
    intent = state.get("intent", "general")
    intent_prompt = state.get("intent_prompt", "")
    relevant_sections = state.get("relevant_sections", [])
    conversation_history = state.get("conversation_history", [])
    
    # 格式化上下文摘要
    context_parts = []
    for section in relevant_sections:
        content = section.get("content", "")
        truncated = content[:500] + "..." if len(content) > 500 else content
        context_parts.append(f"【{section.get('title', '未命名')}】\n{truncated}")
    
    context_summary = "\n\n".join(context_parts) if context_parts else "（暂无相关上下文）"
    
    # 🔥 使用智能上下文管理器
    temp_manager = FollowupHistoryManager(session_manager=None)
    context_result = temp_manager.build_context_for_llm(
        history=conversation_history,
        report_summary=context_summary,
        current_question=question,
        enable_memory_all=True
    )
    context_str = context_result["context_str"]
    
    # 构建系统提示词
    system_prompt = f"""你是一个专业的项目分析顾问助手，名叫「设计高参 AI」。

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
    llm = LLMFactory.create_llm()
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"""用户问题：{question}

请基于上述报告内容回答，并在回答末尾标注引用的章节（格式：📖 引用：第X章）。""")
    ]
    
    try:
        response = llm.invoke(messages)
        answer = response.content
        log_msg = f"✅ 回答生成成功 ({len(answer)} 字符)"
    except Exception as e:
        answer = f"抱歉，生成回答时遇到问题: {str(e)}"
        log_msg = f"❌ 回答生成失败: {e}"
    
    logger.info(log_msg)
    
    # 提取引用
    references = []
    for section in relevant_sections:
        title = section.get("title", "")
        if title and title in answer:
            references.append(title)
    
    return {
        "answer": answer,
        "references": list(set(references)),
        "processing_log": [log_msg]
    }


# ============================================================
# 建议生成器
# ============================================================

def generate_suggestions_node(state: FollowupAgentState) -> Dict[str, Any]:
    """
    节点4: 生成后续问题建议
    
    根据意图智能推荐
    """
    intent = state.get("intent", "general")
    
    # 基础建议池
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
    
    # 根据意图选择建议
    if intent == "closed":
        suggestions = open_suggestions[:2] + creative_suggestions[:1]
    elif intent == "open_with_context":
        suggestions = closed_suggestions[:1] + creative_suggestions[:2]
    elif intent == "creative":
        suggestions = creative_suggestions[:2] + closed_suggestions[:1]
    else:
        suggestions = general_suggestions[:3]
    
    log_msg = f"💡 生成 {len(suggestions)} 条后续建议"
    logger.info(log_msg)
    
    return {
        "suggestions": suggestions,
        "processing_log": [log_msg]
    }


# ============================================================
# 构建 Agent 图
# ============================================================

def build_followup_agent() -> StateGraph:
    """
    构建追问 Agent 状态图
    
    流程：classify_intent → retrieve_context → generate_answer → generate_suggestions → END
    """
    graph = StateGraph(FollowupAgentState)
    
    # 添加节点
    graph.add_node("classify_intent", classify_intent_node)
    graph.add_node("retrieve_context", retrieve_context_node)
    graph.add_node("generate_answer", generate_answer_node)
    graph.add_node("generate_suggestions", generate_suggestions_node)
    
    # 设置入口
    graph.set_entry_point("classify_intent")
    
    # 添加边（线性流程）
    graph.add_edge("classify_intent", "retrieve_context")
    graph.add_edge("retrieve_context", "generate_answer")
    graph.add_edge("generate_answer", "generate_suggestions")
    graph.add_edge("generate_suggestions", END)
    
    return graph.compile()


# ============================================================
# FollowupAgent 封装类
# ============================================================

class FollowupAgent:
    """
    🔥 v7.15: 追问智能体 - 基于 LangGraph
    
    替代原有的 ConversationAgent（服务类）
    升级为真正的独立 Agent
    """
    
    def __init__(self):
        """初始化追问智能体"""
        self.graph = build_followup_agent()
        logger.info("🚀 FollowupAgent (LangGraph) 已初始化")
    
    def answer_question(
        self,
        question: str,
        report_context: Dict[str, Any],
        conversation_history: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        回答用户问题
        
        Args:
            question: 用户问题
            report_context: 报告上下文 (final_report, agent_results, requirements)
            conversation_history: 对话历史
        
        Returns:
            {
                "answer": str,
                "intent": str,
                "references": List[str],
                "suggestions": List[str],
                "processing_log": List[str]
            }
        """
        # 构建初始状态
        initial_state: FollowupAgentState = {
            "question": question,
            "report_context": report_context or {},
            "conversation_history": conversation_history or [],
            "intent": "",
            "relevant_sections": [],
            "intent_prompt": "",
            "answer": "",
            "references": [],
            "suggestions": [],
            "processing_log": []
        }
        
        logger.info(f"🤖 FollowupAgent 处理问题: {question[:50]}...")
        
        # 运行图
        try:
            final_state = self.graph.invoke(initial_state)
            
            return {
                "answer": final_state.get("answer", ""),
                "intent": final_state.get("intent", "general"),
                "references": final_state.get("references", []),
                "suggestions": final_state.get("suggestions", []),
                "processing_log": final_state.get("processing_log", [])
            }
        except Exception as e:
            logger.error(f"❌ FollowupAgent 执行失败: {e}")
            return {
                "answer": f"抱歉，处理问题时遇到错误: {str(e)}",
                "intent": "error",
                "references": [],
                "suggestions": ["请尝试重新提问"],
                "processing_log": [f"❌ 执行失败: {e}"]
            }
    
    async def answer_question_async(
        self,
        question: str,
        report_context: Dict[str, Any],
        conversation_history: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """异步版本"""
        import asyncio
        return await asyncio.to_thread(
            self.answer_question,
            question=question,
            report_context=report_context,
            conversation_history=conversation_history
        )


# ============================================================
# 向后兼容：保留原 ConversationAgent 接口
# ============================================================

class ConversationAgentCompat:
    """
    向后兼容层：保持原 ConversationAgent 的调用接口
    内部使用 FollowupAgent (LangGraph)
    """
    
    def __init__(self):
        self.agent = FollowupAgent()
        logger.info("ConversationAgentCompat 已初始化（内部使用 FollowupAgent）")
    
    def answer_question(
        self,
        question: str,
        context,  # ConversationContext
        conversation_history = None
    ) -> Dict[str, Any]:
        """保持原接口"""
        # 转换 context 格式
        report_context = {
            "final_report": context.final_report if hasattr(context, 'final_report') else {},
            "agent_results": context.agent_results if hasattr(context, 'agent_results') else {},
            "requirements": context.requirements if hasattr(context, 'requirements') else {},
            "user_input": context.user_input if hasattr(context, 'user_input') else ""
        }
        
        # 转换 conversation_history 格式
        history_data = []
        if conversation_history:
            for turn in conversation_history:
                if hasattr(turn, 'dict'):
                    history_data.append(turn.dict())
                elif isinstance(turn, dict):
                    history_data.append(turn)
                else:
                    history_data.append({
                        "question": getattr(turn, 'question', ''),
                        "answer": getattr(turn, 'answer', ''),
                        "intent": getattr(turn, 'intent', 'general'),
                        "referenced_sections": getattr(turn, 'referenced_sections', []),
                        "timestamp": getattr(turn, 'timestamp', '')
                    })
        
        return self.agent.answer_question(
            question=question,
            report_context=report_context,
            conversation_history=history_data
        )
