"""
统一能力边界检查服务

职责：
1. 对所有需求输入点进行能力边界检查
2. 提供统一的检查接口和结果格式
3. 支持检查规则的配置化管理
4. 生成可追溯的检查记录

Version: 1.0.0
Author: System
Created: 2026-01-02
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from ..utils.capability_detector import CapabilityDetector, CapabilityLevel

logger = logging.getLogger(__name__)


class CheckType(Enum):
    """检查类型"""

    FULL = "full"  # 完整检查(交付物+信息充足性)
    DELIVERABLE_ONLY = "deliverable"  # 仅交付物检查
    INFO_ONLY = "info"  # 仅信息充足性检查
    TASK_MODIFICATION = "task_mod"  # 任务修改检查
    QUESTIONNAIRE = "questionnaire"  # 问卷答案检查
    FOLLOWUP = "followup"  # 追问检查


@dataclass
class DeliverableCheck:
    """单个交付物的检查结果"""

    original_type: str
    within_capability: bool
    transformed_type: Optional[str] = None
    transformation_reason: Optional[str] = None
    detected_keywords: List[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class InfoSufficiencyCheck:
    """信息充足性检查结果"""

    is_sufficient: bool
    score: float
    present_elements: List[str] = field(default_factory=list)
    missing_elements: List[str] = field(default_factory=list)
    reason: str = ""


@dataclass
class BoundaryCheckResult:
    """统一的边界检查结果"""

    # 元数据
    check_id: str
    check_type: CheckType
    node_name: str
    timestamp: str

    # 能力状态
    within_capability: bool
    capability_score: float  # 0-1

    # 交付物检测
    deliverable_checks: List[DeliverableCheck] = field(default_factory=list)
    transformations_needed: List[Dict[str, Any]] = field(default_factory=list)
    capable_deliverables: List[Dict[str, Any]] = field(default_factory=list)

    # 信息充足性
    info_sufficiency: Optional[InfoSufficiencyCheck] = None

    # 警告和建议
    alert_level: Literal["info", "warning", "error"] = "info"
    alert_message: str = ""
    suggestions: List[str] = field(default_factory=list)

    # 上下文
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskModificationCheckResult:
    """任务修改检查结果"""

    check_id: str
    has_new_deliverables: bool
    new_deliverables: List[str] = field(default_factory=list)
    removed_deliverables: List[str] = field(default_factory=list)
    modified_deliverables: List[Dict[str, Any]] = field(default_factory=list)
    within_capability: bool = True
    capability_warnings: List[str] = field(default_factory=list)


@dataclass
class FollowupCheckResult:
    """追问检查结果"""

    check_id: str
    has_new_requirements: bool
    new_requirements: List[str] = field(default_factory=list)
    requires_reanalysis: bool = False
    within_capability: bool = True
    suggested_action: str = "continue"  # "continue" | "reanalyze" | "clarify"


class CapabilityBoundaryService:
    """统一能力边界检查服务"""

    # 配置缓存
    _config_cache: Optional[Dict[str, Any]] = None

    @classmethod
    def check_user_input(
        cls, user_input: str, context: Dict[str, Any], check_type: CheckType = CheckType.FULL
    ) -> BoundaryCheckResult:
        """
        检查用户输入的能力边界

        Args:
            user_input: 用户输入文本
            context: 上下文信息(节点名称、已有需求等)
            check_type: 检查类型

        Returns:
            BoundaryCheckResult: 统一的检查结果
        """
        check_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        node_name = context.get("node", "unknown")

        logger.info(f"🔍 [CapabilityBoundary] 开始检查: node={node_name}, type={check_type.value}")

        # 调用现有的 CapabilityDetector
        raw_result = CapabilityDetector.full_capability_check(user_input)

        # 转换为统一格式
        deliverable_capability = raw_result.get("deliverable_capability", {})
        info_sufficiency = raw_result.get("info_sufficiency", {})

        # 构建交付物检查结果
        deliverable_checks = []
        for item in raw_result.get("capable_deliverables", []):
            deliverable_checks.append(
                DeliverableCheck(
                    original_type=item.get("type", ""),
                    within_capability=True,
                    detected_keywords=item.get("keywords", []),
                    confidence=item.get("confidence", 0.0),
                )
            )

        for item in raw_result.get("transformations", []):
            deliverable_checks.append(
                DeliverableCheck(
                    original_type=item.get("original", ""),
                    within_capability=False,
                    transformed_type=item.get("transformed_to", ""),
                    transformation_reason=item.get("reason", ""),
                    detected_keywords=item.get("keywords", []),
                )
            )

        # 计算能力状态
        capability_score = deliverable_capability.get("capability_score", 1.0)
        within_capability = capability_score >= 0.6  # 阈值配置

        # 确定警告级别
        if capability_score >= 0.8:
            alert_level = "info"
            alert_message = "需求在能力范围内"
        elif capability_score >= 0.6:
            alert_level = "warning"
            alert_message = f"部分需求需要能力转化（匹配度: {capability_score:.0%}）"
        else:
            alert_level = "error"
            alert_message = f"多项需求超出能力范围（匹配度: {capability_score:.0%}），建议调整需求"

        # 构建建议
        suggestions = []
        if raw_result.get("transformations"):
            suggestions.append("系统已自动将超出能力的需求转化为可交付方案")
        if not info_sufficiency.get("is_sufficient", True):
            suggestions.append("建议补充关键信息以提高分析准确性")

        result = BoundaryCheckResult(
            check_id=check_id,
            check_type=check_type,
            node_name=node_name,
            timestamp=timestamp,
            within_capability=within_capability,
            capability_score=capability_score,
            deliverable_checks=deliverable_checks,
            transformations_needed=raw_result.get("transformations", []),
            capable_deliverables=raw_result.get("capable_deliverables", []),
            info_sufficiency=InfoSufficiencyCheck(
                is_sufficient=info_sufficiency.get("is_sufficient", True),
                score=info_sufficiency.get("score", 1.0),
                present_elements=info_sufficiency.get("present_elements", []),
                missing_elements=info_sufficiency.get("missing_elements", []),
                reason=info_sufficiency.get("reason", ""),
            ),
            alert_level=alert_level,
            alert_message=alert_message,
            suggestions=suggestions,
            context=context,
        )

        logger.info(f"✅ [CapabilityBoundary] 检查完成: within_capability={within_capability}, score={capability_score:.2f}")

        return result

    @classmethod
    def check_deliverable_list(cls, deliverables: List[Dict], context: Dict[str, Any]) -> BoundaryCheckResult:
        """
        检查交付物列表是否在能力范围内

        Args:
            deliverables: 交付物列表，每项包含 type, description 等
            context: 上下文信息

        Returns:
            BoundaryCheckResult
        """
        check_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        node_name = context.get("node", "unknown")

        logger.info(f"🔍 [CapabilityBoundary] 检查交付物列表: node={node_name}, count={len(deliverables)}")

        # 提取交付物类型和描述
        deliverable_texts = []
        for d in deliverables:
            d_type = d.get("type", "")
            d_desc = d.get("description", "")
            deliverable_texts.append(f"{d_type}: {d_desc}")

        combined_text = "\n".join(deliverable_texts)

        # 复用 check_user_input
        result = cls.check_user_input(user_input=combined_text, context=context, check_type=CheckType.DELIVERABLE_ONLY)

        result.check_id = check_id
        result.timestamp = timestamp

        return result

    @classmethod
    def check_task_modifications(
        cls, original_tasks: Dict[str, List[str]], modified_tasks: Dict[str, List[str]], context: Dict[str, Any]
    ) -> TaskModificationCheckResult:
        """
        检查任务修改是否引入超出能力的需求

        Args:
            original_tasks: 原始任务分配 {role_id: [task1, task2, ...]}
            modified_tasks: 修改后的任务分配
            context: 上下文信息

        Returns:
            TaskModificationCheckResult
        """
        check_id = str(uuid.uuid4())
        node_name = context.get("node", "unknown")

        logger.info(f"🔍 [CapabilityBoundary] 检查任务修改: node={node_name}")

        # 识别新增的任务
        new_tasks = []
        for role_id, tasks in modified_tasks.items():
            original = set(original_tasks.get(role_id, []))
            modified = set(tasks)
            new = modified - original
            new_tasks.extend(list(new))

        # 检查新增任务
        has_new_deliverables = len(new_tasks) > 0
        within_capability = True
        capability_warnings = []

        if new_tasks:
            new_tasks_text = "\n".join(new_tasks)
            check_result = cls.check_user_input(
                user_input=new_tasks_text, context=context, check_type=CheckType.TASK_MODIFICATION
            )

            within_capability = check_result.within_capability
            if not within_capability:
                capability_warnings.append(check_result.alert_message)
                for trans in check_result.transformations_needed:
                    capability_warnings.append(f"'{trans['original']}' 建议转化为 '{trans['transformed_to']}'")

        return TaskModificationCheckResult(
            check_id=check_id,
            has_new_deliverables=has_new_deliverables,
            new_deliverables=new_tasks,
            within_capability=within_capability,
            capability_warnings=capability_warnings,
        )

    @classmethod
    def check_questionnaire_answers(
        cls, answers: Dict[str, Any], questionnaire_type: str, context: Dict[str, Any]
    ) -> BoundaryCheckResult:
        """
        检查问卷答案是否包含超出能力的需求

        Args:
            answers: 问卷答案字典
            questionnaire_type: 问卷类型 (step1/step2/step3/calibration)
            context: 上下文信息

        Returns:
            BoundaryCheckResult
        """
        check_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        node_name = context.get("node", f"questionnaire_{questionnaire_type}")

        logger.info(f"🔍 [CapabilityBoundary] 检查问卷答案: type={questionnaire_type}")

        # 提取答案文本
        answer_texts = []
        for key, value in answers.items():
            if isinstance(value, str):
                answer_texts.append(value)
            elif isinstance(value, list):
                answer_texts.extend([str(v) for v in value])
            elif isinstance(value, dict):
                answer_texts.append(str(value))

        combined_text = "\n".join(answer_texts)

        # 检查
        result = cls.check_user_input(
            user_input=combined_text, context={"node": node_name, **context}, check_type=CheckType.QUESTIONNAIRE
        )

        result.check_id = check_id
        result.timestamp = timestamp

        return result

    @classmethod
    def check_followup_question(
        cls, question: str, original_requirements: Dict[str, Any], context: Dict[str, Any]
    ) -> FollowupCheckResult:
        """
        检查追问是否提出新的超出能力的需求

        Args:
            question: 用户追问内容
            original_requirements: 原始需求
            context: 上下文信息

        Returns:
            FollowupCheckResult
        """
        check_id = str(uuid.uuid4())
        node_name = context.get("node", "followup")

        logger.info(f"🔍 [CapabilityBoundary] 检查追问: node={node_name}")

        # 检查追问内容
        check_result = cls.check_user_input(
            user_input=question, context={"node": node_name, **context}, check_type=CheckType.FOLLOWUP
        )

        # 判断是否有新需求
        has_new_requirements = len(check_result.transformations_needed) > 0
        new_requirements = [t["original"] for t in check_result.transformations_needed]

        # 判断是否需要重新分析
        requires_reanalysis = check_result.capability_score < 0.5 and has_new_requirements

        # 建议的行动
        if requires_reanalysis:
            suggested_action = "reanalyze"
        elif not check_result.within_capability:
            suggested_action = "clarify"
        else:
            suggested_action = "continue"

        return FollowupCheckResult(
            check_id=check_id,
            has_new_requirements=has_new_requirements,
            new_requirements=new_requirements,
            requires_reanalysis=requires_reanalysis,
            within_capability=check_result.within_capability,
            suggested_action=suggested_action,
        )

    @classmethod
    def generate_boundary_alert(cls, check_result: BoundaryCheckResult) -> Dict[str, Any]:
        """
        生成能力边界警告信息

        Args:
            check_result: 检查结果

        Returns:
            {
                "has_alert": bool,
                "alert_level": "info|warning|error",
                "message": str,
                "transformations": List[Dict],
                "suggestions": List[str]
            }
        """
        has_alert = check_result.alert_level in ["warning", "error"]

        # 生成用户友好的转化说明
        transformation_messages = []
        for trans in check_result.transformations_needed:
            original = trans.get("original", "")
            transformed = trans.get("transformed_to", "")
            reason = trans.get("reason", "")
            transformation_messages.append(
                {
                    "original": original,
                    "transformed": transformed,
                    "reason": reason,
                    "display": f"'{original}' → '{transformed}' ({reason})",
                }
            )

        return {
            "has_alert": has_alert,
            "alert_level": check_result.alert_level,
            "message": check_result.alert_message,
            "capability_score": check_result.capability_score,
            "transformations": transformation_messages,
            "suggestions": check_result.suggestions,
            "check_id": check_result.check_id,
            "timestamp": check_result.timestamp,
        }

    @classmethod
    def apply_transformations(cls, user_input: str, check_result: BoundaryCheckResult) -> str:
        """
        自动应用能力转化

        将超出能力的需求转化为可交付替代方案

        Args:
            user_input: 原始输入
            check_result: 检查结果

        Returns:
            转化后的文本
        """
        if not check_result.transformations_needed:
            return user_input

        transformed_input = user_input

        # 应用转化（简单的文本替换）
        for trans in check_result.transformations_needed:
            original = trans.get("original", "")
            transformed = trans.get("transformed_to", "")

            # 查找并替换关键词
            for keyword in trans.get("keywords", []):
                if keyword in transformed_input:
                    # 添加转化说明
                    replacement = f"{transformed}（原需求'{keyword}'已转化）"
                    transformed_input = transformed_input.replace(keyword, replacement, 1)
                    logger.info(f"🔄 [CapabilityBoundary] 应用转化: {keyword} → {transformed}")

        return transformed_input

    @classmethod
    def should_trigger_user_interaction(
        cls, check_result: BoundaryCheckResult, node_config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        判断是否应该触发用户交互（显示警告对话框）

        Args:
            check_result: 检查结果
            node_config: 节点配置（从 capability_boundary_config.yaml 读取）

        Returns:
            是否触发用户交互
        """
        if node_config is None:
            node_config = {}

        # 获取节点的阈值配置
        interaction_threshold = node_config.get("interaction_threshold", 0.6)
        auto_transform = node_config.get("auto_transform", True)

        # 如果配置了自动转化且得分不是太低，不触发交互
        if auto_transform and check_result.capability_score >= interaction_threshold:
            return False

        # 如果有严重的能力不匹配，触发交互
        if check_result.alert_level == "error":
            return True

        # 如果有警告且分数低于阈值，触发交互
        if check_result.alert_level == "warning" and check_result.capability_score < interaction_threshold:
            return True

        return False
