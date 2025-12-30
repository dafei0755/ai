"""
问卷生成智能体 (LangGraph StateGraph)

🔥 v7.16: 将 LLMQuestionGenerator 升级为真正的 LangGraph Agent

核心功能:
1. 上下文提取 (Extract Context) - 从需求分析中提取关键信息
2. 问题生成 (Generate Questions) - LLM驱动生成定制化问题
3. 相关性验证 (Validate Relevance) - 验证问题与用户输入的相关性

节点流转:
    extract_context → generate_questions → validate_relevance → END
    
    如果验证失败:
    extract_context → generate_questions → validate_relevance → regenerate_questions → END
"""

from typing import TypedDict, Dict, Any, List, Optional, Tuple
from loguru import logger
from datetime import datetime
import json
import re
import time

from langgraph.graph import StateGraph, START, END

# 导入共享工具函数
from ..utils.shared_agent_utils import PerformanceMonitor, extract_questionnaire_context


# ============================================================================
# 状态定义
# ============================================================================

class QuestionnaireState(TypedDict):
    """问卷生成智能体状态"""
    
    # 输入
    user_input: str                   # 用户原始输入
    structured_data: Dict[str, Any]   # 需求分析师的结构化输出
    
    # 中间状态
    analysis_summary: str             # 构建的分析摘要
    user_keywords: List[str]          # 从用户输入提取的关键词
    raw_llm_response: str             # LLM原始响应
    
    # 输出
    questions: List[Dict[str, Any]]   # 生成的问题列表
    relevance_score: float            # 相关性分数 (0-1)
    low_relevance_questions: List[str]  # 低相关性问题
    generation_source: str            # 生成来源 ("llm_generated" | "fallback" | "regenerated")
    generation_rationale: str         # 生成理由
    
    # 配置
    _llm_model: Any                   # LLM模型
    _max_regenerations: int           # 最大重新生成次数
    _regeneration_count: int          # 当前重新生成次数
    
    # 处理日志
    processing_log: List[str]


# ============================================================================
# 节点函数
# ============================================================================

def extract_context_node(state: QuestionnaireState) -> Dict[str, Any]:
    """
    上下文提取节点 - 从需求分析中提取关键信息
    """
    logger.info("📊 执行上下文提取节点")
    
    structured_data = state.get("structured_data", {})
    user_input = state.get("user_input", "")
    
    # 构建分析摘要
    summary_parts = []
    
    # 项目概览
    project_overview = structured_data.get("project_overview", "")
    if project_overview:
        summary_parts.append(f"## 项目概览\n{project_overview}")
    
    # 项目任务
    project_task = structured_data.get("project_task", "") or structured_data.get("project_tasks", "")
    if isinstance(project_task, list):
        project_task = "；".join(project_task[:5])
    if project_task and project_task != project_overview:
        summary_parts.append(f"## 项目任务\n{project_task}")
    
    # 核心目标
    core_objectives = structured_data.get("core_objectives", [])
    if core_objectives:
        if isinstance(core_objectives, list):
            objectives_text = "\n".join([f"- {obj}" for obj in core_objectives[:5]])
        else:
            objectives_text = str(core_objectives)
        summary_parts.append(f"## 核心目标\n{objectives_text}")
    
    # 项目类型
    project_type = structured_data.get("project_type", "")
    if project_type:
        type_label = {
            "personal_residential": "个人住宅",
            "hybrid_residential_commercial": "混合型（住宅+商业）",
            "commercial_enterprise": "商业/企业项目",
            "cultural_educational": "文化/教育项目",
            "healthcare_wellness": "医疗/康养项目",
            "office_coworking": "办公/联合办公",
            "hospitality_tourism": "酒店/文旅项目",
            "sports_entertainment_arts": "体育/娱乐/艺术"
        }.get(project_type, project_type)
        summary_parts.append(f"## 项目类型\n{type_label}")
    
    # 设计挑战
    design_challenge = structured_data.get("design_challenge", "")
    if design_challenge:
        summary_parts.append(f"## 核心设计挑战\n{design_challenge}")
    
    # 核心张力
    core_tension = structured_data.get("core_tension", "")
    if core_tension:
        summary_parts.append(f"## 核心矛盾/张力\n{core_tension}")
    
    # 人物叙事
    narrative_characters = structured_data.get("narrative_characters", "") or structured_data.get("character_narrative", "")
    if isinstance(narrative_characters, list):
        narrative_characters = "\n".join([f"- {char}" for char in narrative_characters[:3]])
    if narrative_characters:
        summary_parts.append(f"## 人物叙事/用户画像\n{narrative_characters}")
    
    # 物理环境
    physical_contexts = structured_data.get("physical_contexts", "")
    if isinstance(physical_contexts, list):
        physical_contexts = "；".join(physical_contexts[:3])
    if physical_contexts:
        summary_parts.append(f"## 物理环境\n{physical_contexts}")
    
    # 资源约束
    resource_constraints = structured_data.get("resource_constraints", "")
    if resource_constraints:
        summary_parts.append(f"## 资源约束\n{resource_constraints}")
    
    analysis_summary = "\n\n".join(summary_parts) if summary_parts else "（未提取到足够的需求信息）"
    
    # 提取用户关键词（用于相关性验证）
    user_keywords = _extract_keywords(user_input)
    
    log_entry = f"📊 上下文提取完成: 摘要长度 {len(analysis_summary)}, 提取 {len(user_keywords)} 个关键词"
    logger.info(log_entry)
    
    return {
        "analysis_summary": analysis_summary,
        "user_keywords": user_keywords,
        "processing_log": [log_entry]
    }


def generate_questions_node(state: QuestionnaireState) -> Dict[str, Any]:
    """
    问题生成节点 - 使用LLM生成定制化问题
    """
    logger.info("🤖 执行问题生成节点")
    
    user_input = state.get("user_input", "")
    analysis_summary = state.get("analysis_summary", "")
    llm_model = state.get("_llm_model")
    user_keywords = state.get("user_keywords", [])
    regeneration_count = state.get("_regeneration_count", 0)
    
    # 如果是重新生成，使用更强的约束
    is_regeneration = regeneration_count > 0
    
    if llm_model is None:
        logger.warning("⚠️ LLM模型未提供，使用回退方案")
        return _fallback_generate(user_input, state.get("structured_data", {}))
    
    try:
        # 构建提示词
        system_prompt = _build_system_prompt(is_regeneration, user_keywords)
        human_prompt = _build_human_prompt(user_input, analysis_summary, is_regeneration, user_keywords)
        
        # 调用LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": human_prompt}
        ]
        
        response = llm_model.invoke(messages)
        raw_content = response.content if hasattr(response, "content") else str(response)
        
        # 解析LLM响应
        questionnaire_data = _parse_llm_response(raw_content)
        questions = questionnaire_data.get("questions", [])
        
        if not questions:
            logger.warning("⚠️ LLM返回空问卷，使用回退方案")
            return _fallback_generate(user_input, state.get("structured_data", {}))
        
        # 验证和修复问题格式
        validated_questions = _validate_questions(questions)
        
        log_entry = f"🤖 问题生成完成: {len(validated_questions)} 个问题 (重新生成: {is_regeneration})"
        logger.info(log_entry)
        
        return {
            "questions": validated_questions,
            "raw_llm_response": raw_content,
            "generation_rationale": questionnaire_data.get("generation_rationale", ""),
            "generation_source": "regenerated" if is_regeneration else "llm_generated",
            "processing_log": [log_entry]
        }
        
    except Exception as e:
        logger.error(f"❌ LLM生成失败: {e}")
        return _fallback_generate(user_input, state.get("structured_data", {}))


def validate_relevance_node(state: QuestionnaireState) -> Dict[str, Any]:
    """
    相关性验证节点 - 验证问题与用户输入的相关性
    """
    logger.info("🎯 执行相关性验证节点")
    
    questions = state.get("questions", [])
    user_input = state.get("user_input", "").lower()
    user_keywords = state.get("user_keywords", [])
    
    if not questions:
        return {
            "relevance_score": 0.0,
            "low_relevance_questions": [],
            "processing_log": ["⚠️ 无问题可验证"]
        }
    
    relevant_count = 0
    low_relevance_questions = []
    
    for q in questions:
        question_text = q.get("question", "").lower()
        
        # 检查问题是否包含用户关键词
        is_relevant = False
        for keyword in user_keywords:
            if keyword.lower() in question_text or keyword.lower() in user_input:
                is_relevant = True
                break
        
        # 也检查问题与用户输入的直接关联
        if not is_relevant:
            # 检查是否有内容上的相关性（通过公共词汇）
            question_words = set(question_text.split())
            input_words = set(user_input.split())
            common_words = question_words & input_words
            # 排除停用词
            stop_words = {"的", "是", "在", "和", "有", "为", "与", "了", "能", "吗", "呢", "吧", "什么", "如何", "怎么", "您"}
            meaningful_common = common_words - stop_words
            if len(meaningful_common) >= 1:
                is_relevant = True
        
        if is_relevant:
            relevant_count += 1
        else:
            low_relevance_questions.append(q.get("question", "")[:50])
    
    relevance_score = relevant_count / len(questions) if questions else 0.0
    
    log_entry = f"🎯 相关性验证完成: 分数 {relevance_score:.2f}, {len(low_relevance_questions)} 个低相关问题"
    logger.info(log_entry)
    
    return {
        "relevance_score": relevance_score,
        "low_relevance_questions": low_relevance_questions,
        "processing_log": [log_entry]
    }


def should_regenerate(state: QuestionnaireState) -> str:
    """
    条件路由：决定是否需要重新生成
    """
    relevance_score = state.get("relevance_score", 0.0)
    regeneration_count = state.get("_regeneration_count", 0)
    max_regenerations = state.get("_max_regenerations", 1)
    
    # 如果相关性太低且还有重试机会
    if relevance_score < 0.3 and regeneration_count < max_regenerations:
        logger.info(f"🔄 相关性过低 ({relevance_score:.2f})，触发重新生成")
        return "regenerate"
    
    return "complete"


def increment_regeneration_node(state: QuestionnaireState) -> Dict[str, Any]:
    """
    增加重新生成计数
    """
    current_count = state.get("_regeneration_count", 0)
    return {
        "_regeneration_count": current_count + 1,
        "processing_log": [f"🔄 触发第 {current_count + 1} 次重新生成"]
    }


# ============================================================================
# 辅助函数
# ============================================================================

def _extract_keywords(text: str) -> List[str]:
    """从文本中提取关键词"""
    # 简单的关键词提取：提取引号内的内容和数字相关的词
    keywords = []
    
    # 提取引号内容
    quoted = re.findall(r'[""「『]([^""」』]+)[""」』]', text)
    keywords.extend(quoted)
    
    # 提取数字+单位
    numbers = re.findall(r'\d+(?:\.\d+)?(?:㎡|平米|万|米|层|间|人|年|%)', text)
    keywords.extend(numbers)
    
    # 提取关键名词（通过常见模式）
    patterns = [
        r'(\w{2,4}(?:住宅|公寓|别墅|商铺|办公|酒店|学校|医院|餐厅|咖啡厅))',
        r'((?:客厅|卧室|厨房|卫生间|阳台|书房|餐厅|玄关)\w{0,4})',
        r'(三代同堂|二胎|独居|老人|孩子|宠物)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        keywords.extend(matches)
    
    return list(set(keywords))


def _build_system_prompt(is_regeneration: bool, user_keywords: List[str]) -> str:
    """构建系统提示词"""
    base_prompt = """你是一个专业的项目需求问卷生成专家。

你的任务是根据用户的项目描述和需求分析结果，生成一份高度针对性的澄清问卷。

## 问卷生成原则

1. **高度针对性**：每个问题必须直接关联用户描述中的具体内容
2. **引用用户原话**：尽量在问题中引用用户使用的关键词、数字、场景描述
3. **探索矛盾冲突**：关注需求中可能存在的矛盾或权衡取舍
4. **避免泛化模板**：禁止使用"您喜欢什么风格？"这类通用问题

## 输出格式

返回JSON格式：
```json
{
    "questions": [
        {
            "id": "q1",
            "question": "问题内容（必须包含用户描述中的关键词）",
            "purpose": "问这个问题的目的",
            "options": ["选项A", "选项B", "选项C"],
            "allow_custom": true
        }
    ],
    "generation_rationale": "生成理由说明"
}
```"""

    if is_regeneration:
        keywords_str = "、".join(user_keywords[:10]) if user_keywords else "用户输入中的关键词"
        base_prompt += f"""

## ⚠️ 重新生成注意事项

上一次生成的问题相关性不足。这次必须：

1. **必须引用关键词**：{keywords_str}
2. **每个问题必须包含**至少一个用户原话中的关键词或数字
3. **禁止使用通用模板问题**

⚠️ 如果问题不包含用户输入的关键词，将被判定为无效问题！"""

    return base_prompt


def _build_human_prompt(user_input: str, analysis_summary: str, is_regeneration: bool, user_keywords: List[str]) -> str:
    """构建用户提示词"""
    prompt = f"""## 用户原始输入

{user_input}

## 需求分析摘要

{analysis_summary}

## 任务

请根据以上信息，生成5-8个高度针对性的澄清问题。

要求：
1. 每个问题必须与用户描述直接相关
2. 问题中应引用用户使用的具体词汇、数字或场景
3. 探索用户可能面临的选择和权衡
4. 避免过于宽泛的通用问题"""

    if is_regeneration and user_keywords:
        prompt += f"""

⚠️ 必须在问题中引用的关键词：
{', '.join(user_keywords[:10])}

请确保每个问题至少包含上述关键词之一！"""

    return prompt


def _parse_llm_response(raw_content: str) -> Dict[str, Any]:
    """解析LLM响应"""
    try:
        # 尝试提取JSON块
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', raw_content)
        if json_match:
            raw_content = json_match.group(1)
        
        # 清理可能的前后缀
        raw_content = raw_content.strip()
        if raw_content.startswith("```"):
            raw_content = raw_content[3:]
        if raw_content.endswith("```"):
            raw_content = raw_content[:-3]
        
        return json.loads(raw_content)
    except json.JSONDecodeError as e:
        logger.warning(f"⚠️ JSON解析失败: {e}")
        return {"questions": []}


def _validate_questions(questions: List[Dict]) -> List[Dict]:
    """验证和修复问题格式"""
    validated = []
    
    for i, q in enumerate(questions):
        if isinstance(q, dict) and q.get("question"):
            validated_q = {
                "id": q.get("id", f"q{i+1}"),
                "question": q.get("question", ""),
                "purpose": q.get("purpose", ""),
                "options": q.get("options", []),
                "allow_custom": q.get("allow_custom", True)
            }
            validated.append(validated_q)
    
    return validated


def _fallback_generate(user_input: str, structured_data: Dict[str, Any]) -> Dict[str, Any]:
    """回退生成方案"""
    logger.info("📋 使用回退问卷生成方案")
    
    # 基于项目类型生成基础问题
    project_type = structured_data.get("project_type", "personal_residential")
    
    questions = [
        {
            "id": "q1",
            "question": "您对这个项目最看重的核心目标是什么？",
            "purpose": "明确优先级",
            "options": ["功能性", "美观性", "成本控制", "时间效率"],
            "allow_custom": True
        },
        {
            "id": "q2",
            "question": "在资源有限的情况下，您更倾向于优先保障哪个方面？",
            "purpose": "权衡取舍",
            "options": ["空间尺寸", "材料品质", "设计创意", "施工周期"],
            "allow_custom": True
        },
        {
            "id": "q3",
            "question": "您对项目的预期使用年限是多久？",
            "purpose": "了解长期规划",
            "options": ["短期（1-3年）", "中期（3-10年）", "长期（10年以上）", "永久使用"],
            "allow_custom": True
        }
    ]
    
    return {
        "questions": questions,
        "relevance_score": 0.5,
        "generation_source": "fallback",
        "generation_rationale": "LLM生成失败，使用回退方案",
        "processing_log": ["📋 使用回退问卷生成方案"]
    }


# ============================================================================
# 状态图构建
# ============================================================================

def build_questionnaire_graph() -> StateGraph:
    """
    构建问卷生成状态图
    
    流程:
        START → extract_context → generate_questions → validate_relevance → [条件判断]
            - 如果相关性足够: → END
            - 如果相关性不足: → increment_regeneration → generate_questions → ...
    """
    workflow = StateGraph(QuestionnaireState)
    
    # 添加节点
    workflow.add_node("extract_context", extract_context_node)
    workflow.add_node("generate_questions", generate_questions_node)
    workflow.add_node("validate_relevance", validate_relevance_node)
    workflow.add_node("increment_regeneration", increment_regeneration_node)
    
    # 添加边
    workflow.add_edge(START, "extract_context")
    workflow.add_edge("extract_context", "generate_questions")
    workflow.add_edge("generate_questions", "validate_relevance")
    
    # 条件边：决定是否重新生成
    workflow.add_conditional_edges(
        "validate_relevance",
        should_regenerate,
        {
            "regenerate": "increment_regeneration",
            "complete": END
        }
    )
    
    workflow.add_edge("increment_regeneration", "generate_questions")
    
    return workflow


# ============================================================================
# Agent 封装类
# ============================================================================

class QuestionnaireAgent:
    """
    问卷生成智能体 - LangGraph 封装
    
    使用方式:
        agent = QuestionnaireAgent(llm_model)
        result = agent.generate(user_input, structured_data)
    """
    
    def __init__(self, llm_model=None, config: Optional[Dict[str, Any]] = None):
        """初始化问卷生成智能体"""
        self.llm_model = llm_model
        self.config = config or {}
        self.max_regenerations = self.config.get("max_regenerations", 1)
        
        # 构建并编译状态图
        self._graph = build_questionnaire_graph().compile()
        
        logger.info("🚀 QuestionnaireAgent (LangGraph) 已初始化")
    
    def generate(
        self, 
        user_input: str, 
        structured_data: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        生成问卷
        
        Args:
            user_input: 用户原始输入
            structured_data: 需求分析师的结构化输出
            
        Returns:
            Tuple[List[Dict], str]:
                - 问题列表
                - 生成来源标识
        """
        logger.info("🎯 QuestionnaireAgent 开始执行")
        start_time = time.time()
        
        # 准备初始状态
        initial_state = {
            "user_input": user_input,
            "structured_data": structured_data,
            
            # 配置
            "_llm_model": self.llm_model,
            "_max_regenerations": self.max_regenerations,
            "_regeneration_count": 0,
            
            # 初始化中间状态
            "analysis_summary": "",
            "user_keywords": [],
            "raw_llm_response": "",
            
            # 初始化输出
            "questions": [],
            "relevance_score": 0.0,
            "low_relevance_questions": [],
            "generation_source": "",
            "generation_rationale": "",
            "processing_log": []
        }
        
        # 执行状态图
        try:
            final_state = self._graph.invoke(initial_state)
            
            questions = final_state.get("questions", [])
            source = final_state.get("generation_source", "unknown")
            
            logger.info(f"✅ QuestionnaireAgent 完成: {len(questions)} 个问题, 来源: {source}")
            
            # 记录性能指标
            PerformanceMonitor.record("QuestionnaireAgent", time.time() - start_time, "v7.16")
            
            return questions, source
            
        except Exception as e:
            # 记录失败时的性能指标
            PerformanceMonitor.record("QuestionnaireAgent", time.time() - start_time, "v7.16-error")
            
            logger.error(f"❌ QuestionnaireAgent 执行失败: {e}")
            import traceback
            traceback.print_exc()
            
            # 使用回退方案
            fallback_result = _fallback_generate(user_input, structured_data)
            return fallback_result.get("questions", []), "fallback"
    
    def get_full_result(
        self, 
        user_input: str, 
        structured_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        获取完整结果（包含所有中间状态）
        
        Returns:
            完整的状态字典
        """
        initial_state = {
            "user_input": user_input,
            "structured_data": structured_data,
            "_llm_model": self.llm_model,
            "_max_regenerations": self.max_regenerations,
            "_regeneration_count": 0,
            "analysis_summary": "",
            "user_keywords": [],
            "raw_llm_response": "",
            "questions": [],
            "relevance_score": 0.0,
            "low_relevance_questions": [],
            "generation_source": "",
            "generation_rationale": "",
            "processing_log": []
        }
        
        try:
            return self._graph.invoke(initial_state)
        except Exception as e:
            logger.error(f"❌ QuestionnaireAgent 执行失败: {e}")
            return {
                "questions": [],
                "relevance_score": 0.0,
                "generation_source": "error",
                "error": str(e)
            }


# ============================================================================
# 向后兼容层
# ============================================================================

class LLMQuestionGeneratorCompat:
    """
    向后兼容原 LLMQuestionGenerator 接口
    """
    
    @classmethod
    def generate(
        cls,
        user_input: str,
        structured_data: Dict[str, Any],
        llm_model: Optional[Any] = None,
        timeout: int = 30
    ) -> Tuple[List[Dict[str, Any]], str]:
        """兼容原 LLMQuestionGenerator.generate 接口"""
        agent = QuestionnaireAgent(llm_model)
        return agent.generate(user_input, structured_data)
