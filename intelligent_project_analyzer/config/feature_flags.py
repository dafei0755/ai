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

# ─── 深度搜索功能开关（暂停开放，设为 false；恢复时改为 true 或设置环境变量）────────────
DEEP_SEARCH_ENABLED: bool = os.getenv("DEEP_SEARCH_ENABLED", "false").lower() == "true"

# ─── v7.18 问卷生成 StateGraph Agent（默认关闭，可能未来启用）────────────────────
USE_V718_QUESTIONNAIRE_AGENT: bool = os.getenv("USE_V718_QUESTIONNAIRE_AGENT", "false").lower() == "true"

# ─── Smart Nodes Self-Skip（半动态节点自跳步）────────────────────────────────────
# 启用后由 progressive 节点内部基于统一信号执行自跳步，不改主图拓扑。
ENABLE_SMART_NODE_SELF_SKIP: bool = os.getenv("ENABLE_SMART_NODE_SELF_SKIP", "false").lower() == "true"

# Shadow 模式：只产生日志与路由画像，不实际跳步。
ENABLE_SMART_NODE_SELF_SKIP_SHADOW: bool = os.getenv("ENABLE_SMART_NODE_SELF_SKIP_SHADOW", "true").lower() == "true"


# v8.1.1 已删除向后兼容 flag：USE_V716_AGENTS / USE_V717_REQUIREMENTS_ANALYST /
# USE_PROGRESSIVE_QUESTIONNAIRE / USE_V7_FRONTCHAIN_SEMANTICS / USE_MULTI_ROUND_QUESTIONNAIRE
# 所有分支均已内联为固定路径，注释遗留引用可忽略。


def log_feature_flags_snapshot() -> None:
    """启动时调用，打印完整特性开关快照以便诊断。"""
    logger.info(
        "[feature_flags] snapshot | "
        f"DEEP_SEARCH_ENABLED={DEEP_SEARCH_ENABLED} | "
        f"USE_V718_QUESTIONNAIRE_AGENT={USE_V718_QUESTIONNAIRE_AGENT} | "
        f"ENABLE_SMART_NODE_SELF_SKIP={ENABLE_SMART_NODE_SELF_SKIP} | "
        f"ENABLE_SMART_NODE_SELF_SKIP_SHADOW={ENABLE_SMART_NODE_SELF_SKIP_SHADOW}"
    )
