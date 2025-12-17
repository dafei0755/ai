"""
结果聚合智能体 (LangGraph StateGraph)

🔥 v7.16: 将 ResultAggregatorAgent 升级为真正的 LangGraph Agent

核心功能:
1. 提取专家报告 (Extract Reports)
2. 提取问卷/需求数据 (Extract Context Data)
3. LLM结构化输出 (Generate Structured Report)
4. 验证完整性 (Validate Report)

节点流转:
    extract_reports → extract_context → generate_report → validate_output → END
"""

from typing import TypedDict, Dict, Any, List, Optional
from loguru import logger
from datetime import datetime
import json
import time

from langgraph.graph import StateGraph, START, END

# 导入共享工具函数
from ..utils.shared_agent_utils import PerformanceMonitor, extract_expert_reports


# ============================================================================
# 状态定义
# ============================================================================

class ResultAggregatorState(TypedDict):
    """结果聚合智能体状态"""
    
    # 输入
    agent_results: Dict[str, Any]   # 所有专家的分析结果
    selected_roles: List[Dict]      # 选定的角色列表
    structured_requirements: Dict    # 结构化需求
    user_input: str                 # 用户原始输入
    questionnaire_data: Dict        # 问卷数据
    review_history: List[Dict]      # 审核历史
    
    # 中间状态
    expert_reports: Dict[str, str]  # 提取的专家报告
    context_data: Dict[str, Any]    # 上下文数据（问卷、需求等）
    llm_response: Dict[str, Any]    # LLM原始响应
    
    # 输出
    final_report: Dict[str, Any]    # 最终报告
    validation_result: Dict[str, Any]  # 验证结果
    is_valid: bool                  # 报告是否有效
    
    # 配置
    _llm_model: Any                 # LLM模型
    _config: Dict[str, Any]         # 配置参数
    
    # 处理日志
    processing_log: List[str]


# ============================================================================
# 节点函数
# ============================================================================

def extract_reports_node(state: ResultAggregatorState) -> Dict[str, Any]:
    """
    提取专家报告节点 - 从 agent_results 中提取各专家的输出
    """
    logger.info("📋 执行专家报告提取节点")
    
    agent_results = state.get("agent_results", {})
    selected_roles = state.get("selected_roles", [])
    
    # 构建 role_id -> 显示名称 映射
    role_display_names = {}
    for role in selected_roles:
        if isinstance(role, dict):
            role_id = role.get("role_id", "")
            dynamic_name = role.get("dynamic_role_name", role.get("role_name", ""))
            if role_id:
                # 提取层级编号（如 V4_xxx_4-1 → 4-1）
                parts = role_id.split("_")
                suffix = parts[-1] if len(parts) > 1 else role_id
                # 构建显示名称：编号 + 动态名称
                display_name = f"{suffix} {dynamic_name}" if dynamic_name else role_id
                role_display_names[role_id] = display_name
    
    # 提取专家报告
    expert_reports = {}
    skip_agents = {"requirements_analyst", "project_director", "RESULT_AGGREGATOR", "REPORT_GENERATOR"}
    
    for agent_id, result in agent_results.items():
        # 跳过非专家结果
        if agent_id in skip_agents:
            continue
        
        # 只处理 V2-V6 专家
        if not any(agent_id.startswith(f"V{i}") for i in range(2, 7)):
            continue
        
        if not isinstance(result, dict):
            continue
        
        # 获取显示名称
        display_name = role_display_names.get(agent_id, agent_id)
        
        # 提取内容
        content = _extract_agent_content(result)
        
        if content:
            expert_reports[display_name] = content
            logger.debug(f"  ✅ 提取 {display_name}: {len(content)} 字符")
    
    log_entry = f"📋 提取完成: {len(expert_reports)} 个专家报告"
    logger.info(log_entry)
    
    return {
        "expert_reports": expert_reports,
        "processing_log": [log_entry]
    }


def extract_context_node(state: ResultAggregatorState) -> Dict[str, Any]:
    """
    提取上下文数据节点 - 问卷回答、需求分析等
    """
    logger.info("📝 执行上下文数据提取节点")
    
    context_data = {}
    
    # 提取问卷数据
    questionnaire_data = state.get("questionnaire_data", {})
    if questionnaire_data:
        context_data["questionnaire_responses"] = questionnaire_data
        logger.debug(f"  ✅ 问卷数据: {len(questionnaire_data)} 项")
    
    # 提取需求分析
    structured_requirements = state.get("structured_requirements", {})
    if structured_requirements:
        context_data["requirements_analysis"] = structured_requirements
        logger.debug("  ✅ 需求分析已提取")
    
    # 提取审核历史
    review_history = state.get("review_history", [])
    if review_history:
        context_data["review_history"] = review_history
        logger.debug(f"  ✅ 审核历史: {len(review_history)} 轮")
    
    log_entry = f"📝 上下文提取完成: {len(context_data)} 类数据"
    logger.info(log_entry)
    
    return {
        "context_data": context_data,
        "processing_log": [log_entry]
    }


def generate_report_node(state: ResultAggregatorState) -> Dict[str, Any]:
    """
    生成报告节点 - 调用LLM生成结构化报告
    """
    logger.info("🤖 执行LLM报告生成节点")
    
    llm_model = state.get("_llm_model")
    expert_reports = state.get("expert_reports", {})
    context_data = state.get("context_data", {})
    user_input = state.get("user_input", "")
    
    if not llm_model:
        logger.warning("⚠️ 未提供LLM模型，使用模板报告")
        return _generate_template_report(expert_reports, context_data, user_input)
    
    # 构建报告生成提示
    prompt = _build_report_prompt(expert_reports, context_data, user_input)
    
    try:
        start_time = time.time()
        
        # 调用LLM生成报告
        from langchain_core.messages import HumanMessage, SystemMessage
        
        messages = [
            SystemMessage(content="""你是一个专业的项目报告整合专家。
请根据各专家的分析结果，生成一份结构化的项目分析报告。

输出格式要求：
1. executive_summary: 执行摘要
2. core_answer: 核心答案
3. insights: 关键洞察
4. recommendations: 建议列表

请使用JSON格式输出。"""),
            HumanMessage(content=prompt)
        ]
        
        response = llm_model.invoke(messages)
        elapsed_time = time.time() - start_time
        
        # 解析响应
        llm_response = _parse_llm_response(response.content)
        
        log_entry = f"🤖 LLM生成完成: {elapsed_time:.2f}秒"
        logger.info(log_entry)
        
        return {
            "llm_response": llm_response,
            "processing_log": [log_entry]
        }
        
    except Exception as e:
        logger.error(f"❌ LLM报告生成失败: {e}")
        return _generate_template_report(expert_reports, context_data, user_input)


def validate_output_node(state: ResultAggregatorState) -> Dict[str, Any]:
    """
    验证输出节点 - 检查报告完整性并合成最终报告
    """
    logger.info("✅ 执行报告验证节点")
    
    expert_reports = state.get("expert_reports", {})
    context_data = state.get("context_data", {})
    llm_response = state.get("llm_response", {})
    user_input = state.get("user_input", "")
    
    # 合成最终报告
    final_report = {
        "user_input": user_input,
        "expert_reports": expert_reports,
        "executive_summary": llm_response.get("executive_summary", {}),
        "core_answer": llm_response.get("core_answer", {}),
        "insights": llm_response.get("insights", {}),
        "recommendations": llm_response.get("recommendations", {}),
        "questionnaire_responses": context_data.get("questionnaire_responses", {}),
        "requirements_analysis": context_data.get("requirements_analysis", {}),
        "review_history": context_data.get("review_history", []),
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "expert_count": len(expert_reports),
            "generation_method": "langgraph_agent"
        }
    }
    
    # 验证必要字段
    validation_errors = []
    
    if not expert_reports:
        validation_errors.append("缺少专家报告")
    
    if not final_report.get("executive_summary"):
        validation_errors.append("缺少执行摘要")
    
    is_valid = len(validation_errors) == 0
    
    validation_result = {
        "is_valid": is_valid,
        "errors": validation_errors,
        "warnings": [],
        "expert_count": len(expert_reports),
        "has_questionnaire": bool(context_data.get("questionnaire_responses")),
        "has_requirements": bool(context_data.get("requirements_analysis"))
    }
    
    log_entry = f"✅ 验证完成: {'通过' if is_valid else f'失败({len(validation_errors)}个错误)'}"
    logger.info(log_entry)
    
    return {
        "final_report": final_report,
        "validation_result": validation_result,
        "is_valid": is_valid,
        "processing_log": [log_entry]
    }


# ============================================================================
# 辅助函数
# ============================================================================

def _extract_agent_content(result: Dict[str, Any]) -> str:
    """从专家结果中提取内容"""
    
    # 优先使用 structured_data
    structured_data = result.get("structured_data")
    if structured_data and isinstance(structured_data, dict):
        return json.dumps(structured_data, ensure_ascii=False, indent=2)
    
    # 其次使用 content
    content = result.get("content")
    if content:
        if isinstance(content, dict):
            return json.dumps(content, ensure_ascii=False, indent=2)
        return str(content)
    
    # 最后尝试 deliverable_outputs
    deliverables = result.get("deliverable_outputs", [])
    if deliverables:
        outputs = []
        for d in deliverables:
            if isinstance(d, dict):
                name = d.get("name", "未命名")
                content = d.get("content", "")
                outputs.append(f"### {name}\n{content}")
        return "\n\n".join(outputs)
    
    return ""


def _build_report_prompt(
    expert_reports: Dict[str, str],
    context_data: Dict[str, Any],
    user_input: str
) -> str:
    """构建报告生成提示"""
    
    prompt = f"""# 项目分析报告生成

## 用户需求
{user_input}

## 专家分析结果
"""
    
    for expert_name, content in expert_reports.items():
        # 截取前2000字符避免过长
        truncated = content[:2000] + "..." if len(content) > 2000 else content
        prompt += f"\n### {expert_name}\n{truncated}\n"
    
    # 添加需求分析
    requirements = context_data.get("requirements_analysis", {})
    if requirements:
        prompt += f"\n## 需求分析摘要\n{json.dumps(requirements, ensure_ascii=False, indent=2)[:1000]}\n"
    
    prompt += """
## 输出要求
请生成以下JSON格式的报告:
{
    "executive_summary": {
        "project_overview": "项目概述",
        "key_findings": ["关键发现1", "关键发现2"],
        "key_recommendations": ["核心建议1", "核心建议2"]
    },
    "core_answer": {
        "question": "用户的核心问题",
        "answer": "直接明了的答案"
    },
    "insights": {
        "key_insights": ["洞察1", "洞察2"],
        "cross_domain_connections": ["跨领域关联"]
    },
    "recommendations": {
        "recommendations": [
            {"content": "建议内容", "dimension": "critical", "reasoning": "原因"}
        ]
    }
}
"""
    
    return prompt


def _parse_llm_response(content: str) -> Dict[str, Any]:
    """解析LLM响应"""
    
    # 尝试提取JSON
    try:
        # 查找JSON代码块
        import re
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
        if json_match:
            return json.loads(json_match.group(1))
        
        # 直接尝试解析
        return json.loads(content)
        
    except json.JSONDecodeError:
        logger.warning("⚠️ LLM响应非JSON格式，使用文本摘要")
        return {
            "executive_summary": {
                "project_overview": content[:500],
                "key_findings": [],
                "key_recommendations": []
            },
            "core_answer": {
                "question": "待解析",
                "answer": content[:200]
            },
            "insights": {},
            "recommendations": {}
        }


def _generate_template_report(
    expert_reports: Dict[str, str],
    context_data: Dict[str, Any],
    user_input: str
) -> Dict[str, Any]:
    """生成模板报告（无LLM时的回退）"""
    
    log_entry = "⚠️ 使用模板报告生成（无LLM）"
    logger.warning(log_entry)
    
    return {
        "llm_response": {
            "executive_summary": {
                "project_overview": f"基于 {len(expert_reports)} 位专家的分析",
                "key_findings": [f"专家 {name} 已完成分析" for name in list(expert_reports.keys())[:3]],
                "key_recommendations": ["请查阅各专家详细报告"]
            },
            "core_answer": {
                "question": user_input[:100] if user_input else "未提供",
                "answer": "请查阅专家详细分析"
            },
            "insights": {},
            "recommendations": {}
        },
        "processing_log": [log_entry]
    }


# ============================================================================
# 状态图构建
# ============================================================================

def build_result_aggregator_graph() -> StateGraph:
    """
    构建结果聚合状态图
    
    流程:
        START → extract_reports → extract_context → generate_report → validate_output → END
    """
    workflow = StateGraph(ResultAggregatorState)
    
    # 添加节点
    workflow.add_node("extract_reports", extract_reports_node)
    workflow.add_node("extract_context", extract_context_node)
    workflow.add_node("generate_report", generate_report_node)
    workflow.add_node("validate_output", validate_output_node)
    
    # 添加边
    workflow.add_edge(START, "extract_reports")
    workflow.add_edge("extract_reports", "extract_context")
    workflow.add_edge("extract_context", "generate_report")
    workflow.add_edge("generate_report", "validate_output")
    workflow.add_edge("validate_output", END)
    
    return workflow


# ============================================================================
# Agent 封装类
# ============================================================================

class ResultAggregatorAgentV2:
    """
    结果聚合智能体 V2 - LangGraph 封装
    
    使用方式:
        agent = ResultAggregatorAgentV2(llm_model)
        result = agent.execute(state)
    """
    
    def __init__(self, llm_model=None, config: Optional[Dict[str, Any]] = None):
        """
        初始化结果聚合智能体
        
        Args:
            llm_model: LLM模型实例
            config: 配置参数
        """
        self.llm_model = llm_model
        self.config = config or {}
        
        # 构建并编译状态图
        self._graph = build_result_aggregator_graph().compile()
        
        logger.info("🚀 ResultAggregatorAgentV2 (LangGraph) 已初始化")
    
    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行结果聚合
        
        Args:
            state: 项目分析状态
            
        Returns:
            聚合结果字典
        """
        logger.info("🎯 ResultAggregatorAgentV2 开始执行")
        start_time = time.time()
        
        # 准备初始状态
        initial_state = {
            "agent_results": state.get("agent_results", {}),
            "selected_roles": state.get("strategic_analysis", {}).get("selected_roles", []),
            "structured_requirements": state.get("structured_requirements", {}),
            "user_input": state.get("user_input", ""),
            "questionnaire_data": self._extract_questionnaire_from_state(state),
            "review_history": state.get("review_history", []),
            
            # 配置
            "_llm_model": self.llm_model,
            "_config": self.config,
            
            # 初始化中间状态
            "expert_reports": {},
            "context_data": {},
            "llm_response": {},
            
            # 初始化输出
            "final_report": {},
            "validation_result": {},
            "is_valid": False,
            "processing_log": []
        }
        
        # 执行状态图
        try:
            final_state = self._graph.invoke(initial_state)
            
            # 提取结果
            final_report = final_state.get("final_report", {})
            
            logger.info(f"✅ ResultAggregatorAgentV2 完成: {len(final_report.get('expert_reports', {}))} 专家报告")
            
            # 记录性能指标
            PerformanceMonitor.record("ResultAggregatorAgentV2", time.time() - start_time, "v7.16")
            
            return {
                "structured_data": final_report,
                "validation": final_state.get("validation_result", {}),
                "processing_log": final_state.get("processing_log", [])
            }
            
        except Exception as e:
            # 记录失败时的性能指标
            PerformanceMonitor.record("ResultAggregatorAgentV2", time.time() - start_time, "v7.16-error")
            
            logger.error(f"❌ ResultAggregatorAgentV2 执行失败: {e}")
            import traceback
            traceback.print_exc()
            
            # 返回安全的默认值
            return {
                "structured_data": {
                    "user_input": state.get("user_input", ""),
                    "expert_reports": {},
                    "error": str(e)
                },
                "validation": {"is_valid": False, "errors": [str(e)]},
                "processing_log": [f"❌ 执行失败: {e}"]
            }
    
    def _extract_questionnaire_from_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """从状态中提取问卷数据"""
        calibration = state.get("calibration_questionnaire", {})
        responses = state.get("questionnaire_responses", {})
        summary = state.get("questionnaire_summary", {})
        
        if calibration or responses or summary:
            return {
                "calibration": calibration,
                "responses": responses,
                "summary": summary
            }
        return {}
    
    def to_dict(self) -> Dict[str, Any]:
        """兼容旧接口"""
        return {"agent_type": "ResultAggregatorAgentV2"}


# ============================================================================
# 向后兼容层 - 包装原有 ResultAggregatorAgent
# ============================================================================

class ResultAggregatorAgentCompat:
    """
    向后兼容层 - 可选择使用新版或旧版 Agent
    
    配置:
        USE_LANGGRAPH_AGGREGATOR=true  → 使用新版 LangGraph Agent
        USE_LANGGRAPH_AGGREGATOR=false → 使用原版 Agent
    """
    
    def __init__(self, llm_model=None, config: Optional[Dict[str, Any]] = None):
        import os
        self.use_langgraph = os.getenv("USE_LANGGRAPH_AGGREGATOR", "false").lower() == "true"
        
        if self.use_langgraph:
            self._agent = ResultAggregatorAgentV2(llm_model, config)
            logger.info("📊 使用 LangGraph 版本 ResultAggregatorAgent")
        else:
            # 导入原版
            from ..report.result_aggregator import ResultAggregatorAgent as OriginalAgent
            self._agent = OriginalAgent(llm_model=llm_model, config=config)
            logger.info("📊 使用原版 ResultAggregatorAgent")
    
    def execute(self, state, config=None, store=None):
        """统一执行接口"""
        if self.use_langgraph:
            result = self._agent.execute(state)
            # 转换为 AnalysisResult 格式
            from ..core.types import AnalysisResult
            return AnalysisResult(
                content=json.dumps(result.get("structured_data", {}), ensure_ascii=False),
                structured_data=result.get("structured_data", {}),
                confidence=1.0 if result.get("validation", {}).get("is_valid") else 0.5
            )
        else:
            return self._agent.execute(state, config, store)
