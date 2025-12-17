"""
质量预检智能体 (LangGraph StateGraph)

🔥 v7.16: 将 QualityPreflightNode 升级为真正的 LangGraph Agent

核心功能:
1. 风险分析 (Analyze Risks)
2. 生成质量检查清单 (Generate Checklists)
3. 验证能力匹配度 (Validate Capability)

节点流转:
    analyze_risks → generate_checklists → validate_capability → END
"""

from typing import TypedDict, Dict, Any, List, Optional
from loguru import logger
from datetime import datetime
import asyncio
import time

from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt

# 导入共享工具函数
from ..utils.shared_agent_utils import PerformanceMonitor


# ============================================================================
# 状态定义
# ============================================================================

class QualityPreflightState(TypedDict):
    """质量预检智能体状态"""
    
    # 输入
    active_agents: List[str]        # 活跃的专家ID列表
    selected_roles: List[Dict]      # 选定的角色详情
    user_input: str                 # 用户原始输入
    requirements_summary: Dict      # 需求摘要
    
    # 中间状态
    risk_assessments: List[Dict]    # 风险评估结果
    quality_checklists: Dict[str, List]  # 各专家的质量检查清单
    capability_scores: Dict[str, float]  # 能力匹配度分数
    
    # 输出
    high_risk_warnings: List[Dict]  # 高风险警告
    preflight_completed: bool       # 预检是否完成
    preflight_report: Dict[str, Any]  # 预检报告
    
    # 配置
    _llm_model: Any                 # LLM模型
    
    # 处理日志
    processing_log: List[str]


# ============================================================================
# 节点函数
# ============================================================================

def analyze_risks_node(state: QualityPreflightState) -> Dict[str, Any]:
    """
    风险分析节点 - 评估每个任务的潜在风险
    """
    logger.info("⚠️ 执行风险分析节点")
    
    active_agents = state.get("active_agents", [])
    selected_roles = state.get("selected_roles", [])
    user_input = state.get("user_input", "")
    
    # 构建角色信息映射
    role_info_map = {}
    for role in selected_roles:
        if isinstance(role, dict):
            role_id = role.get("role_id", "")
            if role_id:
                role_info_map[role_id] = role
    
    risk_assessments = []
    
    for role_id in active_agents:
        role_info = role_info_map.get(role_id, {})
        dynamic_name = role_info.get("dynamic_role_name", role_info.get("role_name", role_id))
        task = role_info.get("task", "")
        
        # 评估风险因素
        risk_factors = []
        risk_score = 0
        
        # 规则1: 任务描述模糊
        if not task or len(task) < 20:
            risk_factors.append("任务描述不够详细")
            risk_score += 2
        
        # 规则2: 依赖关系复杂
        dependencies = role_info.get("depends_on", [])
        if len(dependencies) > 2:
            risk_factors.append(f"依赖{len(dependencies)}个其他专家")
            risk_score += 1
        
        # 规则3: 创意类任务（难以量化）
        if any(kw in dynamic_name.lower() for kw in ["创意", "叙事", "narrative", "设计"]):
            risk_factors.append("创意类任务，输出难以量化评估")
            risk_score += 1
        
        # 规则4: 用户输入模糊
        if len(user_input) < 50:
            risk_factors.append("用户输入信息有限")
            risk_score += 1
        
        # 确定风险级别
        risk_level = "low"
        if risk_score >= 4:
            risk_level = "high"
        elif risk_score >= 2:
            risk_level = "medium"
        
        risk_assessments.append({
            "role_id": role_id,
            "role_name": dynamic_name,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "risk_factors": risk_factors,
            "task_preview": task[:100] if task else "无任务描述"
        })
    
    # 按风险分数排序
    risk_assessments.sort(key=lambda x: x.get("risk_score", 0), reverse=True)
    
    high_risk_count = len([r for r in risk_assessments if r.get("risk_level") == "high"])
    log_entry = f"⚠️ 风险分析完成: {high_risk_count} 高风险, {len(risk_assessments)} 总计"
    logger.info(log_entry)
    
    return {
        "risk_assessments": risk_assessments,
        "processing_log": [log_entry]
    }


def generate_checklists_node(state: QualityPreflightState) -> Dict[str, Any]:
    """
    生成质量检查清单节点 - 为每个专家生成个性化清单
    """
    logger.info("📋 执行质量检查清单生成节点")
    
    risk_assessments = state.get("risk_assessments", [])
    
    quality_checklists = {}
    
    for assessment in risk_assessments:
        role_id = assessment.get("role_id", "")
        role_name = assessment.get("role_name", "")
        risk_level = assessment.get("risk_level", "low")
        risk_factors = assessment.get("risk_factors", [])
        
        # 基础检查项
        checklist = [
            "✅ 输出符合任务要求",
            "✅ 内容完整性检查",
            "✅ 与用户需求对齐"
        ]
        
        # 根据风险因素添加特定检查项
        if "任务描述不够详细" in risk_factors:
            checklist.append("⚠️ 确认任务理解正确")
            checklist.append("⚠️ 主动询问澄清问题")
        
        if "依赖" in str(risk_factors):
            checklist.append("⚠️ 确认依赖输入已获取")
            checklist.append("⚠️ 验证与上游专家一致性")
        
        if "创意类任务" in str(risk_factors):
            checklist.append("⚠️ 提供创意理念说明")
            checklist.append("⚠️ 包含可执行的具体建议")
        
        if "用户输入信息有限" in risk_factors:
            checklist.append("⚠️ 使用专业假设填补信息缺口")
            checklist.append("⚠️ 标注假设和不确定性")
        
        # 高风险专家额外检查
        if risk_level == "high":
            checklist.append("🔴 需要额外审核关注")
            checklist.append("🔴 建议分步骤交付")
        
        quality_checklists[role_id] = {
            "role_name": role_name,
            "checklist": checklist,
            "risk_level": risk_level
        }
    
    log_entry = f"📋 生成 {len(quality_checklists)} 个专家检查清单"
    logger.info(log_entry)
    
    return {
        "quality_checklists": quality_checklists,
        "processing_log": [log_entry]
    }


def validate_capability_node(state: QualityPreflightState) -> Dict[str, Any]:
    """
    验证能力匹配度节点 - 检查专家配置是否充足
    """
    logger.info("🎯 执行能力匹配度验证节点")
    
    risk_assessments = state.get("risk_assessments", [])
    quality_checklists = state.get("quality_checklists", {})
    
    capability_scores = {}
    high_risk_warnings = []
    
    for assessment in risk_assessments:
        role_id = assessment.get("role_id", "")
        role_name = assessment.get("role_name", "")
        risk_level = assessment.get("risk_level", "low")
        risk_factors = assessment.get("risk_factors", [])
        
        # 计算能力匹配度分数 (0-1)
        base_score = 1.0
        
        # 每个风险因素扣分
        deduction = len(risk_factors) * 0.1
        score = max(0.3, base_score - deduction)
        
        capability_scores[role_id] = score
        
        # 高风险警告
        if risk_level == "high":
            high_risk_warnings.append({
                "role_id": role_id,
                "role_name": role_name,
                "warning": f"{role_name} 存在高风险: {', '.join(risk_factors)}",
                "score": score,
                "checklist": quality_checklists.get(role_id, {}).get("checklist", [])
            })
    
    # 构建预检报告
    preflight_report = {
        "timestamp": datetime.now().isoformat(),
        "total_agents": len(risk_assessments),
        "high_risk_count": len(high_risk_warnings),
        "average_capability_score": sum(capability_scores.values()) / len(capability_scores) if capability_scores else 1.0,
        "risk_assessments": risk_assessments,
        "quality_checklists": quality_checklists,
        "high_risk_warnings": high_risk_warnings
    }
    
    preflight_completed = True
    
    log_entry = f"🎯 能力验证完成: 平均分 {preflight_report['average_capability_score']:.2f}, {len(high_risk_warnings)} 个高风险"
    logger.info(log_entry)
    
    return {
        "capability_scores": capability_scores,
        "high_risk_warnings": high_risk_warnings,
        "preflight_completed": preflight_completed,
        "preflight_report": preflight_report,
        "processing_log": [log_entry]
    }


# ============================================================================
# 状态图构建
# ============================================================================

def build_quality_preflight_graph() -> StateGraph:
    """
    构建质量预检状态图
    
    流程:
        START → analyze_risks → generate_checklists → validate_capability → END
    """
    workflow = StateGraph(QualityPreflightState)
    
    # 添加节点
    workflow.add_node("analyze_risks", analyze_risks_node)
    workflow.add_node("generate_checklists", generate_checklists_node)
    workflow.add_node("validate_capability", validate_capability_node)
    
    # 添加边
    workflow.add_edge(START, "analyze_risks")
    workflow.add_edge("analyze_risks", "generate_checklists")
    workflow.add_edge("generate_checklists", "validate_capability")
    workflow.add_edge("validate_capability", END)
    
    return workflow


# ============================================================================
# Agent 封装类
# ============================================================================

class QualityPreflightAgent:
    """
    质量预检智能体 - LangGraph 封装
    
    使用方式:
        agent = QualityPreflightAgent(llm_model)
        result = agent.execute(state)
    """
    
    def __init__(self, llm_model=None, config: Optional[Dict[str, Any]] = None):
        """初始化质量预检智能体"""
        self.llm_model = llm_model
        self.config = config or {}
        
        # 构建并编译状态图
        self._graph = build_quality_preflight_graph().compile()
        
        logger.info("🚀 QualityPreflightAgent (LangGraph) 已初始化")
    
    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行质量预检
        
        🔥 v7.16.1: 添加性能监控
        
        Args:
            state: 项目分析状态
            
        Returns:
            预检结果字典
        """
        start_time = time.time()
        logger.info("🎯 QualityPreflightAgent 开始执行")
        
        # 提取 strategic_analysis
        strategic_analysis = state.get("strategic_analysis", {})
        selected_roles = strategic_analysis.get("selected_roles", [])
        
        # 准备初始状态
        initial_state = {
            "active_agents": state.get("active_agents", []),
            "selected_roles": selected_roles,
            "user_input": state.get("user_input", ""),
            "requirements_summary": state.get("requirements_summary", {}),
            
            # 配置
            "_llm_model": self.llm_model,
            
            # 初始化中间状态
            "risk_assessments": [],
            "quality_checklists": {},
            "capability_scores": {},
            
            # 初始化输出
            "high_risk_warnings": [],
            "preflight_completed": False,
            "preflight_report": {},
            "processing_log": []
        }
        
        # 执行状态图
        try:
            final_state = self._graph.invoke(initial_state)
            
            result = {
                "preflight_completed": final_state.get("preflight_completed", False),
                "preflight_report": final_state.get("preflight_report", {}),
                "quality_checklists": final_state.get("quality_checklists", {}),
                "high_risk_warnings": final_state.get("high_risk_warnings", []),
                "processing_log": final_state.get("processing_log", [])
            }
            
            # 记录性能指标
            PerformanceMonitor.record("QualityPreflightAgent", time.time() - start_time, "v7.16")
            
            logger.info(f"✅ QualityPreflightAgent 完成: {len(result['high_risk_warnings'])} 个高风险警告")
            return result
            
        except Exception as e:
            # 记录失败时的性能指标
            PerformanceMonitor.record("QualityPreflightAgent", time.time() - start_time, "v7.16-error")
            
            logger.error(f"❌ QualityPreflightAgent 执行失败: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                "preflight_completed": False,
                "preflight_report": {},
                "quality_checklists": {},
                "high_risk_warnings": [],
                "processing_log": [f"❌ 执行失败: {e}"],
                "error": str(e)
            }
    
    async def execute_async(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """异步执行质量预检"""
        return self.execute(state)


# ============================================================================
# 向后兼容层
# ============================================================================

class QualityPreflightNodeCompat:
    """
    向后兼容原 QualityPreflightNode 接口
    """
    
    def __init__(self, llm_model):
        self._agent = QualityPreflightAgent(llm_model)
    
    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """兼容原调用方式"""
        result = self._agent.execute(state)
        
        # 转换为原有返回格式
        return {
            "preflight_completed": result.get("preflight_completed", False),
            "quality_checklists": result.get("quality_checklists", {}),
            "high_risk_warnings": result.get("high_risk_warnings", [])
        }
