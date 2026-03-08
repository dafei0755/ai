"""
动态项目总监智能体 - Dynamic Project Director Agent

基于角色配置系统的项目总监,负责分析需求并选择合适的专业角色。
Project Director based on role configuration system.
"""

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Union

from langchain_core.exceptions import OutputParserException
from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger
from pydantic import BaseModel, Field, ValidationError, model_validator

from intelligent_project_analyzer.core.prompt_manager import PromptManager
from intelligent_project_analyzer.core.role_manager import RoleManager
from intelligent_project_analyzer.core.task_oriented_models import (
    DeliverableFormat,
    DeliverableSpec,
    Priority,
    TaskInstruction,
    generate_task_instruction_template,
)


def format_for_log(obj: Any) -> str:
    """
    格式化对象用于日志输出，避免 Unicode 转义

    Args:
        obj: 要格式化的对象

    Returns:
        格式化后的字符串，中文不会被转义
    """
    if isinstance(obj, dict | list):
        return json.dumps(obj, ensure_ascii=False, indent=2)
    elif isinstance(obj, BaseException):
        # 对于异常对象，提取可读的错误信息
        return json.dumps(str(obj), ensure_ascii=False)
    else:
        return str(obj)


class TaskDetail(BaseModel):
    """任务详情"""

    tasks: List[str] = Field(description="具体任务列表，每个任务应该详细、可执行", min_length=1)
    focus_areas: List[str] = Field(default_factory=list, description="重点关注领域")
    expected_output: str = Field(default="", description="期望输出描述")
    dependencies: List[str] = Field(default_factory=list, description="依赖的其他角色ID")


class RoleObject(BaseModel):
    """角色对象 - 包含角色的完整信息（更新为任务导向）"""

    role_id: str = Field(description="角色ID (如 '2-1')")
    role_name: str = Field(description="角色基础名称 (如 '居住空间设计总监')")
    dynamic_role_name: str = Field(description="动态角色名称 - 反映本次任务中的具体职责 (如 '三代同堂居住空间与生活模式总设计师')")

    #  使用新的TaskInstruction替代分散的字段
    task_instruction: TaskInstruction = Field(description="统一的任务执行指令（合并了tasks、expected_output、focus_areas）")

    dependencies: List[str] = Field(default_factory=list, description="这个动态角色的启动依赖")
    execution_priority: int = Field(default=1, description="执行优先级（1最高）")

    #  保持兼容性的属性（自动从task_instruction生成）
    @property
    def tasks(self) -> List[str]:
        """向后兼容：从task_instruction生成任务列表"""
        return [d.description for d in self.task_instruction.deliverables]

    @property
    def expected_output(self) -> str:
        """向后兼容：从task_instruction生成预期输出"""
        return self.task_instruction.objective

    @property
    def focus_areas(self) -> List[str]:
        """向后兼容：从task_instruction生成关注领域"""
        return [d.name for d in self.task_instruction.deliverables]


class RoleSelection(BaseModel):
    """角色选择结果"""

    selected_roles: List[RoleObject] = Field(description="选中的角色对象列表，每个对象包含完整的角色信息和任务分配", min_length=3, max_length=8)
    reasoning: str = Field(description="选择这些角色的详细理由,解释为什么这些角色最适合完成任务", min_length=50)

    #  保留 task_distribution 字段以兼容旧代码，但自动从 selected_roles 生成
    @property
    def task_distribution(self) -> Dict[str, Union[TaskDetail, str]]:
        """从 selected_roles 自动生成 task_distribution 以兼容旧代码"""
        distribution = {}
        for role in self.selected_roles:
            # 构造完整的角色ID (如 "V2_设计总监_2-1")
            full_id = self._construct_full_role_id(role.role_id)
            distribution[full_id] = TaskDetail(
                tasks=role.tasks,
                focus_areas=role.focus_areas,
                expected_output=role.expected_output,
                dependencies=role.dependencies,
            )
        return distribution

    def _construct_full_role_id(self, role_id: str) -> str:
        """
        根据 role_id 构造完整的角色ID

        注意: 使用配置文件的实际键名（主角色名称/静态），而非LLM生成的动态名称
        - V3: "叙事与体验专家" (配置文件) vs "人物及叙事专家" (LLM生成)
        - V5: "场景与行业专家" (配置文件) vs "场景与用户生态专家" (LLM生成)
        """
        # 如果已经是完整格式 (如 "V2_设计总监_2-1")，直接返回
        if role_id.count("_") >= 2:
            return role_id

        # 如果只是短ID (如 "2-1")，需要推断前缀
        # 根据第一个数字推断前缀
        if role_id.startswith("2-"):
            return f"V2_设计总监_{role_id}"
        elif role_id.startswith("3-"):
            return f"V3_叙事与体验专家_{role_id}"  #  配置文件键名
        elif role_id.startswith("4-"):
            return f"V4_设计研究员_{role_id}"
        elif role_id.startswith("5-"):
            return f"V5_场景与行业专家_{role_id}"  #  配置文件键名
        elif role_id.startswith("6-"):
            return f"V6_专业总工程师_{role_id}"
        elif role_id.startswith("7-"):
            return f"V7_情感洞察专家_{role_id}"  #  V7情感洞察专家
        else:
            # 未知格式，直接返回
            return role_id

    @model_validator(mode="after")
    def validate_v4_presence(self) -> "RoleSelection":
        """
        验证V4角色存在性（使用 Pydantic v2 的 model_validator）

        V4_设计研究员是其他角色的基础依赖，必须始终包含在selected_roles中。

        Raises:
            ValueError: 如果selected_roles中没有V4角色
        """
        # 从 RoleObject 中提取 role_id
        role_ids = [role.role_id for role in self.selected_roles]
        has_v4 = any(rid.startswith("4-") or rid.startswith("V4_") for rid in role_ids)

        if not has_v4:
            raise ValueError(
                " V4_设计研究员是必选角色，但在selected_roles中未找到。\n"
                "V4是其他角色（V2、V3、V5）的依赖基础，必须包含。\n"
                f"当前role_ids: {role_ids}\n"
                "请重新选择，确保包含至少一个role_id以'4-'开头的角色。"
            )

        # 验证通过，记录日志
        v4_roles = [
            role for role in self.selected_roles if role.role_id.startswith("4-") or role.role_id.startswith("V4_")
        ]
        logger.info(f" V4角色验证通过: {[r.role_id for r in v4_roles]}")

        return self

    @model_validator(mode="after")
    def validate_task_distribution_differentiation(self) -> "RoleSelection":
        """
         验证任务分配差异化（防止平均分配）

        确保核心角色承担更多任务，避免所有角色平均分配相同数量的交付物。
        这是针对专题1发现的"任务分配平均化倾向"问题的修复。

        规则：
        - 如果所有角色的交付物数量标准差 < 0.5，认为是平均分配
        - 至少应该有1个角色的交付物数量显著高于平均值

        Raises:
            ValueError: 如果任务分配过于平均化
        """
        import statistics

        # 统计每个角色的交付物数量
        deliverable_counts = [len(role.task_instruction.deliverables) for role in self.selected_roles]

        if len(deliverable_counts) < 2:
            # 只有1个角色时不验证
            return self

        # 计算标准差
        mean_count = statistics.mean(deliverable_counts)
        stdev_count = statistics.stdev(deliverable_counts) if len(deliverable_counts) > 1 else 0

        logger.info(f" 交付物数量分布: {deliverable_counts}, 平均值: {mean_count:.1f}, 标准差: {stdev_count:.2f}")

        # 如果标准差太小，说明分配过于平均
        if stdev_count < 0.8:  # 阈值可调整
            logger.warning(
                f"️ 任务分配过于平均化！标准差: {stdev_count:.2f} < 0.8\n"
                f"   交付物数量: {deliverable_counts}\n"
                f"   建议: 核心角色应承担4-6个交付物，支持角色1-2个"
            )
            # 注意: 这里使用warning而非raise，给LLM一些容错空间
            # 如果需要严格控制，可改为 raise ValueError

        # 验证是否有"核心角色"（至少4个交付物）
        max_count = max(deliverable_counts)
        if max_count >= 4:
            core_roles = [role.role_id for role, count in zip(self.selected_roles, deliverable_counts, strict=False) if count >= 4]
            logger.info(f" 检测到核心角色: {core_roles} (交付物数量≥4)")
        else:
            logger.warning("️ 所有角色的交付物数量都<4，可能缺少核心角色")

        return self

    @model_validator(mode="after")
    def validate_task_deliverable_alignment(self) -> "RoleSelection":
        """
         验证任务-交付物对齐（确保用户确认的任务被覆盖）

        检查confirmed_core_tasks中的每个任务是否至少有一个专家的deliverable与之对应。
        这是针对问卷与任务分配关系研究发现的关键优化：用户确认的任务必须被执行。

        对齐算法：
        1. 提取任务标题的关键词（去除停用词）
        2. 遍历所有角色的交付物，检查deliverable的name/description是否包含任务关键词
        3. 如果任务的关键词匹配度 >= 50%，认为该任务被覆盖

        注意：此验证需要从外部context获取confirmed_core_tasks，暂时记录警告而非强制失败
        """
        # 尝试从model_config的context中获取confirmed_core_tasks
        # 注意：由于Pydantic模型的限制，这里需要特殊处理
        confirmed_tasks = getattr(self, "_confirmed_tasks", None)

        if not confirmed_tasks:
            # 没有confirmed_tasks数据，跳过验证
            logger.debug(" 未检测到confirmed_core_tasks，跳过任务-交付物对齐验证")
            return self

        logger.info(f" 开始验证 {len(confirmed_tasks)} 个确认任务的对齐情况...")

        # 收集所有交付物的关键词
        all_deliverables = []
        for role in self.selected_roles:
            for deliverable in role.task_instruction.deliverables:
                all_deliverables.append(
                    {
                        "role_id": role.role_id,
                        "name": deliverable.name,
                        "description": deliverable.description,
                        "text": f"{deliverable.name} {deliverable.description}".lower(),
                    }
                )

        # 检查每个确认任务是否被覆盖
        uncovered_tasks = []
        for task in confirmed_tasks:
            task_title = task.get("title", "")
            task_desc = task.get("description", "")
            task_keywords = self._extract_keywords(f"{task_title} {task_desc}")

            # 查找匹配的交付物
            matched = False
            best_match_score = 0
            best_match_deliverable = None

            for deliverable in all_deliverables:
                # 计算关键词匹配度
                match_count = sum(1 for kw in task_keywords if kw in deliverable["text"])
                match_score = match_count / len(task_keywords) if task_keywords else 0

                if match_score > best_match_score:
                    best_match_score = match_score
                    best_match_deliverable = deliverable

                if match_score >= 0.4:  # 40%匹配度阈值
                    matched = True
                    logger.info(
                        f"   任务 '{task_title}' 已对齐到 {deliverable['role_id']} "
                        f"的交付物 '{deliverable['name']}' (匹配度: {match_score:.0%})"
                    )
                    break

            if not matched:
                uncovered_tasks.append(
                    {
                        "task": task_title,
                        "best_match": best_match_deliverable["name"] if best_match_deliverable else "N/A",
                        "score": best_match_score,
                    }
                )
                logger.warning(
                    f"  ️ 任务 '{task_title}' 未被充分覆盖！"
                    f"最佳匹配: {best_match_deliverable['name'] if best_match_deliverable else 'N/A'} "
                    f"(匹配度仅: {best_match_score:.0%})"
                )

        # 汇总验证结果
        if uncovered_tasks:
            logger.warning(
                f"️ 任务-交付物对齐验证: {len(uncovered_tasks)}/{len(confirmed_tasks)} 个任务未被充分覆盖\n"
                f"   未覆盖任务: {[t['task'] for t in uncovered_tasks]}\n"
                f"   建议: LLM可能需要为这些任务分配专门的交付物"
            )
            # 注意：这里使用warning而非raise，避免阻断流程
            # 在实际场景中，可以根据业务需求决定是否强制失败
        else:
            logger.info(f" 任务-交付物对齐验证通过: 所有 {len(confirmed_tasks)} 个确认任务均已覆盖")

        return self

    def _extract_keywords(self, text: str) -> List[str]:
        """
        从文本中提取关键词（简化版，去除停用词）

        Args:
            text: 输入文本

        Returns:
            关键词列表
        """
        import re

        # 简单的停用词列表（中文）
        stopwords = {
            "的",
            "了",
            "和",
            "是",
            "在",
            "有",
            "与",
            "对",
            "为",
            "以",
            "及",
            "等",
            "中",
            "个",
            "将",
            "要",
            "可",
            "能",
            "如",
            "或",
            "于",
            "由",
            "从",
        }

        # 分词（简单按空格和标点分割）
        words = re.findall(r"[\w]+", text.lower())

        # 过滤停用词和短词
        keywords = [w for w in words if w not in stopwords and len(w) >= 2]

        return keywords


