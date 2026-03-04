"""
Send 对象创建工厂（重构版）

统一创建批次执行的 Send 对象，支持动态批次调度

重构说明（2025-11-18）：
- 从固定2批次改为支持动态N批次
- 集成BatchScheduler实现基于依赖的拓扑排序
- 统一批次Send对象创建逻辑
- 保留旧接口以保持向后兼容

作者: LangGraph Design Team
"""

from typing import Any, Dict, List

from langgraph.types import Send
from loguru import logger

from ...core.state import AnalysisStage


class SendFactory:
    """Send 对象创建工厂 - 统一处理批次执行"""

    @staticmethod
    def create_batch_sends(
        state: Dict[str, Any],
        batch_number: int,
        node_name: str = "agent_executor",
        batches: List[List[str]] | None = None
    ) -> List[Send]:
        """
        创建指定批次的 Send 对象列表（通用方法）

        使用场景：
        1. 从 state["execution_batches"] 读取批次列表（如果 batches 参数为 None）
        2. 或直接使用传入的 batches 参数（优先级更高）
        3. 为指定批次创建 Send 对象
        4. 支持动态数量的批次（1-N 批）

        Args:
            state: 工作流状态
            batch_number: 批次编号（从 1 开始）
            node_name: 目标节点名称（默认 "agent_executor"）
            batches: 可选的批次列表（优先使用此参数，如果提供）

        Returns:
            Send 对象列表

        Example:
            >>> # 方式1: 从 state 读取批次
            >>> state["execution_batches"] = [
            ...     ["V4_设计研究员_4-1"],
            ...     ["V5_场景专家_5-1"],
            ...     ["V3_叙事专家_3-1"]
            ... ]
            >>> sends = SendFactory.create_batch_sends(state, batch_number=1)
            >>> # 返回: [Send("agent_executor", {...role_id="V4_..."})]

            >>> # 方式2: 直接传递批次（推荐用于时序敏感场景）
            >>> batches = scheduler.schedule_batches(active_agents)
            >>> sends = SendFactory.create_batch_sends(
            ...     state, batch_number=1, batches=batches
            ... )
        """
        # 1. 获取批次列表（优先使用参数，其次从 state 读取）
        if batches is None:
            batches = state.get("execution_batches", [])
            if not batches:
                logger.error(" state 中未找到 execution_batches，且未提供 batches 参数")
                logger.warning("请先调用 BatchScheduler.schedule_batches() 计算批次")
                logger.debug(f"可用的 state 键: {list(state.keys())}")
                return []
            logger.debug(f" 从 state 读取批次列表: {len(batches)} 个批次")
        else:
            logger.debug(f" 使用传入的 batches 参数: {len(batches)} 个批次")

        # 2. 验证批次编号
        if batch_number < 1 or batch_number > len(batches):
            logger.error(f" 批次编号 {batch_number} 超出范围 [1, {len(batches)}]")
            logger.debug(f"批次列表: {batches}")
            return []

        # 3. 获取当前批次的角色
        current_batch_roles = batches[batch_number - 1]
        logger.info(f" 创建批次 {batch_number}/{len(batches)} 的 Send 对象")
        logger.info(f"   角色列表: {current_batch_roles}")
        logger.info(f"   目标节点: {node_name}")

        # 4. 创建 Send 对象
        send_list = []
        for i, role_id in enumerate(current_batch_roles, start=1):
            agent_state = dict(state)
            agent_state["role_id"] = role_id
            agent_state["current_batch"] = batch_number
            agent_state["total_batches"] = len(batches)
            agent_state["current_stage"] = AnalysisStage.PARALLEL_ANALYSIS.value

            send_list.append(Send(node_name, agent_state))
            logger.debug(f"   [{i}/{len(current_batch_roles)}]  创建 Send({node_name}, role_id={role_id})")

        logger.info(f" 成功创建 {len(send_list)} 个 Send 对象")
        return send_list

    @staticmethod
    def create_batch_sends_from_roles(
        state: Dict[str, Any],
        role_ids: List[str],
        batch_number: int,
        node_name: str = "agent_executor"
    ) -> List[Send]:
        """
        从指定的角色ID列表创建Send对象（不依赖 execution_batches）

        使用场景：
        1. 重新执行特定专家（审核系统要求）
        2. 临时执行未在批次列表中的角色
        3. 自定义执行顺序

        Args:
            state: 工作流状态
            role_ids: 要执行的角色ID列表
            batch_number: 批次编号（用于标记，不影响执行）
            node_name: 目标节点名称

        Returns:
            Send 对象列表

        Example:
            >>> # 重新执行特定专家
            >>> agents_to_rerun = ["V3_叙事专家_3-1", "V5_场景专家_5-1"]
            >>> sends = SendFactory.create_batch_sends_from_roles(
            ...     state, agents_to_rerun, batch_number=0
            ... )
        """
        logger.info(f"从角色列表创建 Send 对象: {role_ids}")

        send_list = []
        for role_id in role_ids:
            agent_state = dict(state)
            agent_state["role_id"] = role_id
            agent_state["current_batch"] = batch_number
            agent_state["is_rerun"] = True  # 标记为重新执行

            send_list.append(Send(node_name, agent_state))

        logger.info(f"创建了 {len(send_list)} 个重执行 Send 对象")
        return send_list

    @staticmethod
    def create_first_batch_sends(state: Dict[str, Any]) -> List[Send]:
        """
        创建第一批 Send 对象（V3/V4/V5）

        保留接口（向后兼容）：
        - 旧代码：使用硬编码前缀过滤 (V3_, V4_, V5_)
        - 新代码：应使用 create_batch_sends(state, batch_number=1)

        ️ 废弃警告: 此方法将在未来版本中移除
        请使用 create_batch_sends() 代替
        """
        logger.warning(
            "create_first_batch_sends() 已废弃，请使用 create_batch_sends(state, 1)"
        )

        # 检查是否已经计算了批次
        if state.get("execution_batches"):
            # 使用新方法
            #  修复 (2025-11-19): 使用正确的节点名 agent_executor
            return SendFactory.create_batch_sends(state, batch_number=1, node_name="agent_executor")

        # 降级到旧逻辑（硬编码前缀过滤）
        logger.warning("未找到 execution_batches，降级到硬编码前缀过滤")
        active_agents = state.get("active_agents", [])
        target_roles = [
            role_id for role_id in active_agents
            if role_id.startswith("V3_") or
               role_id.startswith("V4_") or
               role_id.startswith("V5_")
        ]

        send_list = []
        for role_id in target_roles:
            agent_state = dict(state)
            agent_state["role_id"] = role_id
            agent_state["current_stage"] = AnalysisStage.PARALLEL_ANALYSIS.value
            agent_state["execution_batch"] = "first"
            send_list.append(Send("batch_executor", agent_state))

        return send_list

    @staticmethod
    def create_second_batch_sends(state: Dict[str, Any]) -> List[Send]:
        """
        创建第二批 Send 对象（V2/V6）

        保留接口（向后兼容）：
        - 旧代码：使用硬编码前缀过滤 (V2_, V6_)
        - 新代码：应使用 create_batch_sends(state, batch_number=2)

        ️ 废弃警告: 此方法将在未来版本中移除
        请使用 create_batch_sends() 代替
        """
        logger.warning(
            "create_second_batch_sends() 已废弃，请使用 create_batch_sends(state, batch_number)"
        )

        # 检查是否已经计算了批次
        if state.get("execution_batches"):
            # 查找 V2/V6 所在的批次编号
            batches = state.get("execution_batches", [])
            for i, batch in enumerate(batches, start=1):
                # 检查批次中是否有 V2 或 V6
                has_v2_v6 = any(
                    role.startswith("V2_") or role.startswith("V6_")
                    for role in batch
                )
                if has_v2_v6:
                    logger.info(f"找到 V2/V6 在批次 {i}")
                    #  修复 (2025-11-19): 使用正确的节点名 agent_executor
                    return SendFactory.create_batch_sends(state, batch_number=i, node_name="agent_executor")

        # 降级到旧逻辑（硬编码前缀过滤）
        logger.warning("未找到 execution_batches 或 V2/V6 批次，降级到硬编码前缀过滤")
        active_agents = state.get("active_agents", [])
        target_roles = [
            role_id for role_id in active_agents
            if role_id.startswith("V2_") or role_id.startswith("V6_")
        ]

        send_list = []
        for role_id in target_roles:
            agent_state = dict(state)
            agent_state["role_id"] = role_id
            agent_state["current_stage"] = AnalysisStage.PARALLEL_ANALYSIS.value
            agent_state["execution_batch"] = "second"
            send_list.append(Send("batch_executor", agent_state))

        return send_list


# === 辅助函数 ===

def get_batch_for_role(state: Dict[str, Any], role_id: str) -> int | None:
    """
    获取指定角色所在的批次编号

    Args:
        state: 工作流状态
        role_id: 角色ID（如 "V3_人物及叙事专家_3-1"）

    Returns:
        批次编号（1-based），如果未找到返回 None

    Example:
        >>> batches = [["V4_..."], ["V5_..."], ["V3_..."]]
        >>> state = {"execution_batches": batches}
        >>> batch_num = get_batch_for_role(state, "V3_...")
        >>> # 返回: 3
    """
    batches = state.get("execution_batches", [])
    for i, batch in enumerate(batches, start=1):
        if role_id in batch:
            return i
    logger.warning(f"角色 {role_id} 未在批次列表中找到")
    return None


def get_current_batch_roles(state: Dict[str, Any]) -> List[str]:
    """
    获取当前批次的所有角色ID

    Args:
        state: 工作流状态

    Returns:
        当前批次的角色ID列表

    Example:
        >>> state = {
        ...     "current_batch": 2,
        ...     "execution_batches": [["V4_..."], ["V5_..."], ["V3_..."]]
        ... }
        >>> roles = get_current_batch_roles(state)
        >>> # 返回: ["V5_..."]
    """
    current_batch = state.get("current_batch", 0)
    batches = state.get("execution_batches", [])

    if not batches or current_batch < 1 or current_batch > len(batches):
        logger.warning(f"无法获取批次 {current_batch} 的角色列表")
        return []

    return batches[current_batch - 1]


def is_batch_completed(state: Dict[str, Any], batch_number: int) -> bool:
    """
    检查指定批次是否已完成

    Args:
        state: 工作流状态
        batch_number: 批次编号（从 1 开始）

    Returns:
        True 如果批次已完成，否则 False

    Example:
        >>> state = {
        ...     "completed_batches": [1, 2],
        ...     "current_batch": 3
        ... }
        >>> is_batch_completed(state, 1)
        True
        >>> is_batch_completed(state, 3)
        False
    """
    completed_batches = state.get("completed_batches", [])
    return batch_number in completed_batches
