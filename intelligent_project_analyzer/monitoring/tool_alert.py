"""
工具调用告警系统 (v7.129)

检测工具使用异常并发送告警
"""

from enum import Enum
from typing import List, Optional

from loguru import logger


class AlertLevel(Enum):
    """告警级别"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ToolUsageAlert:
    """工具使用异常告警"""

    @staticmethod
    async def check_and_alert(session_id: str, role_id: str, tools_used: List[str]) -> None:
        """
        检查工具使用情况并告警

        Args:
            session_id: 会话ID
            role_id: 角色ID
            tools_used: 已使用的工具列表
        """

        # 规则1: V4/V6角色必须使用工具
        if _should_use_tools(role_id):
            if len(tools_used) == 0:
                await send_alert(
                    level=AlertLevel.ERROR,
                    session_id=session_id,
                    role_id=role_id,
                    message=f"角色 {role_id} 应使用工具但未调用任何工具",
                    action="检查LLM prompt是否正确 / 工具是否绑定",
                )
            elif len(tools_used) < 2:
                await send_alert(
                    level=AlertLevel.WARNING,
                    session_id=session_id,
                    role_id=role_id,
                    message=f"角色 {role_id} 仅调用了 {len(tools_used)} 个工具（建议≥2）",
                    action="检查工具调用策略",
                )

        # 规则2: V2仅能用milvus (v7.154: ragflow → milvus)
        elif role_id.startswith("V2") or role_id.startswith("2-"):
            external_tools = [t for t in tools_used if t not in ("milvus_kb_tool", "milvus_kb")]
            if external_tools:
                await send_alert(
                    level=AlertLevel.WARNING,
                    session_id=session_id,
                    role_id=role_id,
                    message=f"V2角色使用了外部工具: {external_tools}",
                    action="确认权限配置是否正确",
                )


async def send_alert(level: AlertLevel, session_id: str, role_id: str, message: str, action: str) -> None:
    """
    发送告警

    Args:
        level: 告警级别
        session_id: 会话ID
        role_id: 角色ID
        message: 告警消息
        action: 建议操作
    """
    # 格式化日志消息
    log_level = level.value.upper()
    formatted_msg = f"[TOOL_ALERT] [{role_id}] {message} | Session: {session_id[:16]}... | Action: {action}"

    # 根据级别记录日志
    if level == AlertLevel.CRITICAL or level == AlertLevel.ERROR:
        logger.error(formatted_msg)
    elif level == AlertLevel.WARNING:
        logger.warning(formatted_msg)
    else:
        logger.info(formatted_msg)

    # TODO: 集成外部告警（Slack/Email/钉钉）
    # 示例：
    # if level == AlertLevel.CRITICAL:
    #     await slack_notify(message, session_id, role_id)


def _should_use_tools(role_id: str) -> bool:
    """判断角色是否应该使用工具"""
    return role_id.startswith("V4") or role_id.startswith("V6") or role_id.startswith("4-") or role_id.startswith("6-")
