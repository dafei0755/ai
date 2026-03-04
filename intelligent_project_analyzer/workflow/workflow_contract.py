"""
工作流契约 — 单一事实源 (Single Source of Truth)

本模块是工作流所有公开契约的唯一权威来源：
  - 稳定外部阶段枚举（WorkflowStage）
  - 内部节点名 → 外部阶段映射
  - 节点名 → 进度百分比映射
  - WebSocket 事件类型枚举

修改规则：
  - 任何工作流节点名变更必须先更新本文件
  - workflow_runner.py / tests / 前端文档 必须从本文件导入，不得手写副本
  - 新节点上线时同步更新下方三个映射表

对应架构治理：F-02（进度映射与节点名不一致）、F-06（废弃节点残留）
创建时间：2026-03-04
"""
from enum import Enum
from typing import Dict, List, Optional


# ═══════════════════════════════════════════════════════════════════════════════
# 1. 稳定外部阶段枚举
#    对外暴露稳定名称，内部节点可自由演进而不影响前端和文档
# ═══════════════════════════════════════════════════════════════════════════════

class WorkflowStage(str, Enum):
    """工作流稳定外部阶段（对前端/监控/文档暴露的公开契约）"""
    INPUT_VALIDATION      = "input_validation"
    REQUIREMENTS_ANALYSIS = "requirements_analysis"
    QUESTIONNAIRE_FLOW    = "questionnaire_flow"
    PLANNING              = "planning"
    PREFLIGHT             = "preflight"
    EXECUTION_LOOP        = "execution_loop"
    CHALLENGE_RESOLUTION  = "challenge_resolution"
    REPORT_GENERATION     = "report_generation"
    DELIVERY              = "delivery"
    TERMINAL              = "terminal"  # 终止节点（拒绝/错误）


# ═══════════════════════════════════════════════════════════════════════════════
# 2. 内部节点名 → 外部阶段映射
#    来源：intelligent_project_analyzer/workflow/main_workflow.py
#    最后同步时间：2026-03-04
# ═══════════════════════════════════════════════════════════════════════════════

NODE_TO_STAGE: Dict[str, WorkflowStage] = {
    # 输入验证阶段
    "unified_input_validator_initial":   WorkflowStage.INPUT_VALIDATION,
    "unified_input_validator_secondary": WorkflowStage.INPUT_VALIDATION,
    "input_rejected":                    WorkflowStage.TERMINAL,

    # 需求分析阶段
    "requirements_analyst":              WorkflowStage.REQUIREMENTS_ANALYSIS,
    "output_intent_detection":           WorkflowStage.REQUIREMENTS_ANALYSIS,
    "feasibility_analyst":               WorkflowStage.REQUIREMENTS_ANALYSIS,

    # 问卷流阶段
    "progressive_step1_core_task":       WorkflowStage.QUESTIONNAIRE_FLOW,
    "progressive_step2_radar":           WorkflowStage.QUESTIONNAIRE_FLOW,
    "progressive_step3_gap_filling":     WorkflowStage.QUESTIONNAIRE_FLOW,
    "questionnaire_summary":             WorkflowStage.QUESTIONNAIRE_FLOW,

    # 规划阶段
    "project_director":                  WorkflowStage.PLANNING,
    "deliverable_id_generator":          WorkflowStage.PLANNING,
    "search_query_generator":            WorkflowStage.PLANNING,
    "role_task_unified_review":          WorkflowStage.PLANNING,
    "role_selection_quality_review":     WorkflowStage.PLANNING,    # DEPRECATED v7.280，合并到 role_task_unified_review，仍在图中注册，待移除

    # 预检阶段
    "quality_preflight":                 WorkflowStage.PREFLIGHT,

    # 执行循环阶段
    "batch_executor":                    WorkflowStage.EXECUTION_LOOP,
    "agent_executor":                    WorkflowStage.EXECUTION_LOOP,
    "batch_aggregator":                  WorkflowStage.EXECUTION_LOOP,
    "batch_router":                      WorkflowStage.EXECUTION_LOOP,
    "batch_strategy_review":             WorkflowStage.EXECUTION_LOOP,

    # 挑战处理阶段
    "detect_challenges":                 WorkflowStage.CHALLENGE_RESOLUTION,
    "manual_review":                     WorkflowStage.CHALLENGE_RESOLUTION,

    # 报告生成阶段
    "result_aggregator":                 WorkflowStage.REPORT_GENERATION,
    "report_guard":                      WorkflowStage.REPORT_GENERATION,
    "analysis_review":                   WorkflowStage.REPORT_GENERATION,  # DEPRECATED v2.2，仍在图中注册，待移除

    # 交付阶段
    "pdf_generator":                     WorkflowStage.DELIVERY,

    # 辅助节点（不在主链中展示进度）
    "user_question":                     WorkflowStage.EXECUTION_LOOP,
}


# ═══════════════════════════════════════════════════════════════════════════════
# 3. 节点名 → 进度百分比映射
#    替代 workflow_runner.py 中的手工维护副本
#    修复：移除废弃节点 analysis_review / progressive_step2_info_gather / progressive_step3_radar
#    修复：补入真实节点 output_intent_detection / deliverable_id_generator / search_query_generator
# ═══════════════════════════════════════════════════════════════════════════════

NODE_PROGRESS: Dict[str, float] = {
    # 输入验证阶段 (0-15%)
    "unified_input_validator_initial":   0.05,   # 5%  - 初始输入验证
    "unified_input_validator_secondary": 0.10,   # 10% - 二次验证

    # 需求分析阶段 (15-25%)
    "requirements_analyst":              0.15,   # 15% - 需求分析
    "output_intent_detection":           0.17,   # 17% - 输出意图识别
    "feasibility_analyst":               0.18,   # 18% - 可行性分析

    # 问卷流阶段 (20-35%)
    "progressive_step1_core_task":       0.20,   # 20% - Step 1: 核心任务
    "progressive_step2_radar":           0.25,   # 25% - Step 2: 雷达图  ← 修正（原 progressive_step2_info_gather）
    "progressive_step3_gap_filling":     0.30,   # 30% - Step 3: 信息补全  ← 修正（原 progressive_step3_radar）
    "questionnaire_summary":             0.35,   # 35% - 需求洞察

    # 规划阶段 (35-55%)
    "project_director":                  0.40,   # 40% - 项目总监
    "deliverable_id_generator":          0.42,   # 42% - 交付物ID生成
    "search_query_generator":            0.44,   # 44% - 搜索查询生成
    "role_task_unified_review":          0.45,   # 45% - 角色任务审核

    # 预检阶段 (50%)
    "quality_preflight":                 0.50,   # 50% - 质量预检

    # 执行循环阶段 (55-80%)
    "batch_executor":                    0.55,   # 55% - 批次调度
    "agent_executor":                    0.70,   # 70% - 专家执行
    "batch_aggregator":                  0.75,   # 75% - 批次聚合
    "batch_router":                      0.76,   # 76% - 批次路由
    "batch_strategy_review":             0.78,   # 78% - 策略审核

    # 挑战处理阶段 (80-85%)
    "detect_challenges":                 0.80,   # 80% - 挑战检测
    "manual_review":                     0.82,   # 82% - 人工审核

    # 报告生成阶段 (90-98%)
    "result_aggregator":                 0.90,   # 90% - 结果聚合
    "report_guard":                      0.95,   # 95% - 报告审核

    # 交付阶段 (98-100%)
    "pdf_generator":                     0.98,   # 98% - PDF 生成
}

# 所有在主图中注册的节点名集合（用于契约一致性测试）
# 包含无进度意义的终止节点和已废弃但仍注册的节点
ACTIVE_NODE_NAMES: List[str] = list(NODE_PROGRESS.keys()) + [
    "input_rejected",              # 终止节点，无进度意义
    "user_question",               # 问答节点，无进度意义
    "analysis_review",             # DEPRECATED v2.2，仍在图中注册 → 计划删除
    "role_selection_quality_review", # DEPRECATED v7.280，合并到 role_task_unified_review → 计划删除
]


# ═══════════════════════════════════════════════════════════════════════════════
# 4. WebSocket 事件类型枚举
#    来源：workflow_runner.py + ws_routes.py
# ═══════════════════════════════════════════════════════════════════════════════

class WSEventType(str, Enum):
    """工作流 WebSocket 消息事件类型（前端消费的公开契约）"""
    INITIAL_STATUS = "initial_status"    # 连接建立后的初始状态快照
    STATUS_UPDATE  = "status_update"     # 工作流进度更新
    NODE_UPDATE    = "node_update"       # 单节点执行详情
    INTERRUPT      = "interrupt"         # 工作流暂停，等待用户输入
    PING           = "ping"              # 心跳（服务端 → 客户端）
    PONG           = "pong"              # 心跳回复（客户端 → 服务端）


# ═══════════════════════════════════════════════════════════════════════════════
# 5. 辅助查询函数
# ═══════════════════════════════════════════════════════════════════════════════

def get_node_progress(node_name: str, fallback: Optional[float] = None) -> Optional[float]:
    """
    获取节点对应的进度值。
    若节点不在映射中且未提供 fallback，返回 None。
    """
    return NODE_PROGRESS.get(node_name, fallback)


def get_node_stage(node_name: str) -> Optional[WorkflowStage]:
    """获取节点对应的外部阶段枚举，未知节点返回 None。"""
    return NODE_TO_STAGE.get(node_name)


def is_deprecated_node(node_name: str) -> bool:
    """
    检查节点名是否是已废弃的历史节点名。
    用于运行期警告和测试断言。
    """
    _DEPRECATED_NODES = {
        "analysis_review",            # v2.2 废弃
        "progressive_step2_info_gather",  # 旧名称，已重命名为 progressive_step2_radar
        "progressive_step3_radar",    # 旧名称，已重命名为 progressive_step3_gap_filling
        "role_selection_quality_review",  # v7.280 废弃，合并到 role_task_unified_review
        "task_assignment_review",     # 废弃，合并到 role_task_unified_review
    }
    return node_name in _DEPRECATED_NODES
