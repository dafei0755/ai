"""
批次调度器 - 基于依赖图的拓扑排序和批次分组

本模块实现了基于依赖关系的批次调度功能，支持动态计算专家执行顺序。

核心功能：
1. 依赖图构建 - 将客户定义的依赖关系映射到动态角色ID
2. 拓扑排序 - 使用Python内置graphlib.TopologicalSorter
3. 批次分组 - 将专家按依赖关系分组为可并行执行的批次
4. 验证依赖 - 检测循环依赖和缺失依赖

客户依赖关系（标准答案）：
- V4: []           # 无依赖，第1批
- V5: ["V4"]       # 依赖 V4，第2批
- V3: ["V4", "V5"] # 依赖 V4+V5，第3批
- V2: ["V3", "V4", "V5"] # 依赖全部，第4批
- V6: ["V2"]       # 依赖 V2，第5批

作者: LangGraph Design Team
最后更新: 2025-11-18
"""

from typing import Dict, List, Set, Tuple, Optional
from graphlib import TopologicalSorter
from loguru import logger
from collections import defaultdict

from ..core.types import format_role_display_name


class BatchScheduler:
    """批次调度器 - 管理专家执行顺序

    使用Python 3.9+内置的graphlib.TopologicalSorter实现依赖管理。

    Attributes:
        base_dependencies: 客户定义的标准依赖关系（基础类型）
    """

    def __init__(self):
        """初始化批次调度器"""
        # 客户文件定义的标准依赖关系（基础类型）
        # 注意：这里的依赖关系表示"前驱"（predecessors）
        # 即 V5: ["V4"] 表示V5依赖V4，V4必须先完成
        self.base_dependencies = {
            "V4": [],                    # 无依赖，第1批
            "V5": ["V4"],                # 依赖 V4，第2批
            "V3": ["V4", "V5"],          # 依赖 V4+V5，第3批
            "V2": ["V3", "V4", "V5"],    # 依赖全部，第4批
            "V6": ["V2"]                 # 依赖 V2，第5批
        }

        logger.info(f"BatchScheduler initialized with {len(self.base_dependencies)} base types")
        logger.debug(f"Base dependencies: {self.base_dependencies}")

    def build_dependency_graph(
        self,
        selected_roles: List[str]
    ) -> Dict[str, Set[str]]:
        """
        构建依赖图（基于动态角色 ID）

        将客户定义的基础类型依赖关系映射到具体的动态角色ID。
        例如：将 V3: ["V4", "V5"] 映射到
             "V3_人物及叙事专家_3-1": {"V4_设计研究员_4-1", "V5_场景专家_5-1"}

        Args:
            selected_roles: 动态选择的角色列表
                如: ["V3_人物及叙事专家_3-1", "V4_设计研究员_4-1"]

        Returns:
            依赖图字典，键是角色 ID，值是依赖的角色 ID 集合（Set）

        Raises:
            ValueError: 如果依赖的角色未在selected_roles中找到
        """
        dependency_graph = {}
        missing_dependencies = []

        for role_id in selected_roles:
            # 提取基础类型 (V3, V4, V5, V2, V6)
            base_type = self._extract_base_type(role_id)

            # 获取基础依赖
            base_deps = self.base_dependencies.get(base_type, [])

            # 映射到动态 ID（使用Set存储）
            dynamic_deps = set()
            for dep_base in base_deps:
                # 查找对应的动态 ID
                matching_roles = [
                    r for r in selected_roles
                    if r.startswith(f"{dep_base}_")
                ]

                if matching_roles:
                    # 添加所有匹配的角色（可能有多个子角色）
                    dynamic_deps.update(matching_roles)
                else:
                    # ✅ 依赖未选择，自动忽略（项目总监智能判断不需要）
                    logger.info(
                        f"✅ 角色 {format_role_display_name(role_id)} 的依赖 {dep_base} 未被选择，已自动忽略"
                    )

            dependency_graph[role_id] = dynamic_deps

        logger.info(f"构建依赖图完成: {len(dependency_graph)} 个角色")

        return dependency_graph

    def topological_sort_batches(
        self,
        dependency_graph: Dict[str, Set[str]]
    ) -> List[List[str]]:
        """
        拓扑排序 + 批次分组（使用Python内置graphlib）

        使用graphlib.TopologicalSorter进行拓扑排序，并按层级分组为批次。
        同一批次内的角色可以并行执行（它们之间没有依赖关系）。

        Args:
            dependency_graph: 依赖图（键是角色，值是依赖集合）

        Returns:
            批次列表，每个批次是可并行执行的角色列表
            例: [
                ["V4_设计研究员_4-1"],
                ["V5_场景专家_5-1"],
                ["V3_人物及叙事专家_3-1"],
                ["V2_设计总监_2-1"],
                ["V6_技术总监_6-1"]
            ]

        Raises:
            ValueError: 如果检测到循环依赖
        """
        logger.info("开始拓扑排序")

        # 创建TopologicalSorter
        # 注意：graphlib接受的是 {node: predecessors} 格式
        ts = TopologicalSorter(dependency_graph)

        # 尝试准备排序
        try:
            ts.prepare()
        except ValueError as e:
            # 检测到循环依赖
            logger.error(f"检测到循环依赖: {e}")
            raise ValueError(f"依赖图中存在循环依赖: {e}")

        batches = []
        batch_num = 0

        # 逐批获取可执行的节点
        while ts.is_active():
            batch = ts.get_ready()
            if batch:
                batch_list = sorted(list(batch))  # 排序以确保确定性
                batches.append(batch_list)
                batch_num += 1
                # 显示简洁格式的角色名
                display_batch = [format_role_display_name(r) for r in batch_list]
                logger.info(f"  批次 {batch_num}: {display_batch}")

                # 标记这些节点为完成
                for node in batch:
                    ts.done(node)

        logger.info(f"拓扑排序完成: {len(batches)} 个批次")

        return batches

    def schedule_batches(
        self,
        selected_roles: List[str]
    ) -> List[List[str]]:
        """
        完整的批次调度流程

        这是对外的主要接口，执行完整的批次调度流程：
        1. 构建依赖图
        2. 拓扑排序 + 分组
        3. 验证批次划分

        Args:
            selected_roles: 动态选择的角色列表

        Returns:
            批次列表

        Example:
            >>> scheduler = BatchScheduler()
            >>> roles = ["V4_设计研究员_4-1", "V3_叙事专家_3-1", "V2_总监_2-1"]
            >>> batches = scheduler.schedule_batches(roles)
            >>> # 返回: [["V4_..."], ["V3_..."], ["V2_..."]]
        """
        logger.info(f"开始批次调度: {len(selected_roles)} 个角色")
        logger.debug(f"Selected roles: {selected_roles}")

        # 1. 构建依赖图
        dependency_graph = self.build_dependency_graph(selected_roles)

        # 2. 拓扑排序 + 分组
        batches = self.topological_sort_batches(dependency_graph)

        # 3. 验证
        self._validate_batches(batches, dependency_graph)

        logger.info(f"✅ 批次调度完成: {len(batches)} 个批次")
        return batches

    def _extract_base_type(self, role_id: str) -> str:
        """
        提取基础类型

        从动态角色ID中提取基础类型标识（V2-V6）。

        Args:
            role_id: 完整角色ID，如 "V3_人物及叙事专家_3-1"

        Returns:
            基础类型，如 "V3"

        Example:
            >>> _extract_base_type("V3_人物及叙事专家_3-1")
            "V3"
            >>> _extract_base_type("V4_设计研究员_4-1")
            "V4"
        """
        if role_id.startswith("V") and "_" in role_id:
            return role_id.split("_")[0]
        logger.warning(f"无法提取基础类型: {role_id}")
        return role_id

    def _validate_batches(
        self,
        batches: List[List[str]],
        dependency_graph: Dict[str, Set[str]]
    ):
        """
        验证批次划分的正确性

        检查每个批次中的角色是否满足：
        1. 其所有依赖都在之前的批次中已执行
        2. 同一批次内的角色之间没有依赖关系

        Args:
            batches: 批次列表
            dependency_graph: 依赖图

        Raises:
            ValueError: 如果批次划分不正确
        """
        logger.info("验证批次划分...")
        executed = set()

        for batch_num, batch in enumerate(batches, start=1):
            logger.debug(f"验证批次 {batch_num}: {batch}")

            for role in batch:
                # 检查依赖是否已执行
                deps = dependency_graph.get(role, set())
                for dep in deps:
                    if dep not in executed:
                        error_msg = (
                            f"批次 {batch_num} 中的 {role} 依赖 {dep}，"
                            f"但 {dep} 尚未执行！"
                        )
                        logger.error(error_msg)
                        raise ValueError(f"批次划分错误: {error_msg}")

            # 检查批次内是否有相互依赖
            batch_set = set(batch)
            for role in batch:
                deps = dependency_graph.get(role, set())
                internal_deps = deps & batch_set
                if internal_deps:
                    error_msg = (
                        f"批次 {batch_num} 内部存在依赖: "
                        f"{role} 依赖同批次的 {internal_deps}"
                    )
                    logger.error(error_msg)
                    raise ValueError(f"批次划分错误: {error_msg}")

            # 标记当前批次为已执行
            executed.update(batch)

        logger.info("✅ 批次验证通过")

    def get_batch_number(
        self,
        role_id: str,
        batches: List[List[str]]
    ) -> Optional[int]:
        """
        获取角色所在的批次编号（从 1 开始）

        Args:
            role_id: 角色 ID
            batches: 批次列表

        Returns:
            批次编号（1-based），如果未找到返回 None

        Example:
            >>> batches = [["V4_..."], ["V5_..."], ["V3_..."]]
            >>> get_batch_number("V5_...", batches)
            2
        """
        for i, batch in enumerate(batches, start=1):
            if role_id in batch:
                return i
        logger.warning(f"角色 {role_id} 未在批次列表中找到")
        return None

    def get_dependencies(
        self,
        role_id: str,
        batches: List[List[str]]
    ) -> List[str]:
        """
        获取角色的所有依赖角色ID

        Args:
            role_id: 角色 ID
            batches: 批次列表

        Returns:
            依赖的角色ID列表

        Example:
            >>> get_dependencies("V3_...", batches)
            ["V4_...", "V5_..."]
        """
        base_type = self._extract_base_type(role_id)
        base_deps = self.base_dependencies.get(base_type, [])

        # 找到所有批次中匹配的依赖角色
        all_roles = [role for batch in batches for role in batch]
        deps = []
        for dep_base in base_deps:
            matching = [r for r in all_roles if r.startswith(f"{dep_base}_")]
            deps.extend(matching)

        return deps


# === 使用示例 ===

def example_usage():
    """批次调度器使用示例"""
    scheduler = BatchScheduler()

    # 模拟动态选择的角色
    active_agents = [
        "V4_设计研究员_4-1",
        "V5_场景与用户生态专家_5-1",
        "V3_人物及叙事专家_3-1",
        "V2_设计总监_2-1",
        "V6_技术总监_6-1"
    ]

    # 计算批次
    batches = scheduler.schedule_batches(active_agents)

    # 输出结果
    print("\n=== 批次调度结果 ===")
    for i, batch in enumerate(batches, start=1):
        print(f"批次 {i}: {batch}")

    # 查询特定角色的批次编号
    role = "V3_人物及叙事专家_3-1"
    batch_num = scheduler.get_batch_number(role, batches)
    print(f"\n{role} 在批次 {batch_num}")

    # 查询依赖关系
    deps = scheduler.get_dependencies(role, batches)
    print(f"{role} 依赖: {deps}")


if __name__ == "__main__":
    # 配置日志
    logger.info("Testing BatchScheduler")
    example_usage()
