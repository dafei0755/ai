# -*- coding: utf-8 -*-
"""
统一特性开关模块 — 消除各模块默认值分裂

所有特性开关从环境变量读取，默认值在此集中维护。
main_workflow.py 和 requirements_nodes.py 统一从这里导入，
避免同一进程内不同模块读到不同默认值。

启动时调用 log_feature_flags_snapshot() 输出完整快照。
"""
import os
from loguru import logger

# ─── v7.16 LangGraph Agent 升级版（默认关闭，旧版测试用）────────────────────────
USE_V716_AGENTS: bool = os.getenv("USE_V716_AGENTS", "false").lower() == "true"

# ─── v7.17 需求分析师 StateGraph Agent（默认开启）──────────────────────────────
#   main_workflow.py 原来默认 "false"，requirements_nodes.py 原来默认 "true"
#   统一改为 "true"，与回归测试期望（V-Default）保持一致
USE_V717_REQUIREMENTS_ANALYST: bool = os.getenv("USE_V717_REQUIREMENTS_ANALYST", "true").lower() == "true"

# ─── v7.18 问卷生成 StateGraph Agent（默认关闭）────────────────────────────────
USE_V718_QUESTIONNAIRE_AGENT: bool = os.getenv("USE_V718_QUESTIONNAIRE_AGENT", "false").lower() == "true"

# ─── v7.87 三步递进式问卷（默认开启）───────────────────────────────────────────
USE_PROGRESSIVE_QUESTIONNAIRE: bool = os.getenv("USE_PROGRESSIVE_QUESTIONNAIRE", "true").lower() == "true"

# ─── v7 前半链路语义回迁（默认开启）──────────────────────────────────────────────
# 保留当前 mixin/graph 架构，但让前半链路步骤顺序和节点交互语义回到
# langgraph-v7-0226-1000：任务梳理 → 信息补全 → 偏好雷达图 → 需求洞察。
USE_V7_FRONTCHAIN_SEMANTICS: bool = os.getenv("USE_V7_FRONTCHAIN_SEMANTICS", "true").lower() == "true"

# ─── 多轮迭代问卷（已停用，保留引用）────────────────────────────────────────────
USE_MULTI_ROUND_QUESTIONNAIRE: bool = os.getenv("USE_MULTI_ROUND_QUESTIONNAIRE", "false").lower() == "true"

# ─── Smart Nodes Self-Skip（半动态节点自跳步）────────────────────────────────────
# 启用后由 progressive 节点内部基于统一信号执行自跳步，不改主图拓扑。
ENABLE_SMART_NODE_SELF_SKIP: bool = os.getenv("ENABLE_SMART_NODE_SELF_SKIP", "false").lower() == "true"

# Shadow 模式：只产生日志与路由画像，不实际跳步。
ENABLE_SMART_NODE_SELF_SKIP_SHADOW: bool = (
    os.getenv("ENABLE_SMART_NODE_SELF_SKIP_SHADOW", "true").lower() == "true"
)


def log_feature_flags_snapshot() -> None:
    """启动时调用，打印完整特性开关快照以便诊断。"""
    logger.info(
        "[feature_flags] snapshot | "
        f"USE_V717_REQUIREMENTS_ANALYST={USE_V717_REQUIREMENTS_ANALYST} | "
        f"USE_PROGRESSIVE_QUESTIONNAIRE={USE_PROGRESSIVE_QUESTIONNAIRE} | "
        f"USE_V716_AGENTS={USE_V716_AGENTS} | "
        f"USE_V718_QUESTIONNAIRE_AGENT={USE_V718_QUESTIONNAIRE_AGENT} | "
        f"USE_V7_FRONTCHAIN_SEMANTICS={USE_V7_FRONTCHAIN_SEMANTICS} | "
        f"USE_MULTI_ROUND_QUESTIONNAIRE={USE_MULTI_ROUND_QUESTIONNAIRE} | "
        f"ENABLE_SMART_NODE_SELF_SKIP={ENABLE_SMART_NODE_SELF_SKIP} | "
        f"ENABLE_SMART_NODE_SELF_SKIP_SHADOW={ENABLE_SMART_NODE_SELF_SKIP_SHADOW}"
    )
