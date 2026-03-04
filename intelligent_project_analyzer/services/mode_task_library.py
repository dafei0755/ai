"""
Mode Task Library Service (v7.800 P0+P2)

负责加载和处理 MODE_TASK_LIBRARY.yaml 配置
根据检测到的设计模式(detected_modes)，注入必需任务到任务分配中
确保核心任务100%覆盖，不会因JTBD表述不清而遭漏

v7.800 新增:
- 集成混合模式冲突解决器
- 根据冲突解决策略调整任务优先级
- 添加混合模式专家推荐
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from loguru import logger

# 导入混合模式解决器
try:
    from ..mode_engine.hybrid_mode_resolver import (
        HybridModeDetectionResult,
        HybridModeResolver,
        ResolutionResult,
    )

    HYBRID_RESOLVER_AVAILABLE = True
except ImportError:
    logger.warning("混合模式解决器导入失败，将使用基础模式处理")
    HYBRID_RESOLVER_AVAILABLE = False


class ModeTaskLibrary:
    """模式任务库加载器（v7.800 P0+P2）"""

    _mode_tasks_config: Dict | None = None
    _hybrid_resolver: Optional["HybridModeResolver"] = None

    @classmethod
    def _get_hybrid_resolver(cls) -> Optional["HybridModeResolver"]:
        """获取混合模式解决器实例（单例）"""
        if not HYBRID_RESOLVER_AVAILABLE:
            return None

        if cls._hybrid_resolver is None:
            try:
                cls._hybrid_resolver = HybridModeResolver()
                logger.info("✅ 混合模式解决器初始化成功")
            except Exception as e:
                logger.error(f"❌ 混合模式解决器初始化失败: {e}")
                cls._hybrid_resolver = None

        return cls._hybrid_resolver

    @classmethod
    def _detect_hybrid_mode(
        cls, detected_modes: List[Dict[str, Any]]
    ) -> Tuple[Optional["HybridModeDetectionResult"], Optional["ResolutionResult"]]:
        """
        检测并解决混合模式冲突

        Returns:
            (检测结果, 解决结果) 或 (None, None)
        """
        resolver = cls._get_hybrid_resolver()
        if not resolver:
            return None, None

        try:
            # 转换为 mode_id -> confidence 格式
            mode_confidences = {}
            for m in detected_modes:
                mode_full_id = m.get("mode", "")
                confidence = m.get("confidence", 0)

                # 提取模式编号 (M1_concept_driven -> M1)
                mode_id = mode_full_id.split("_")[0] if "_" in mode_full_id else mode_full_id
                mode_confidences[mode_id] = confidence

            # 检测混合模式
            detection_result = resolver.detect_hybrid_mode(mode_confidences)

            # 解决冲突
            resolution_result = None
            if detection_result.is_hybrid:
                resolution_result = resolver.resolve_conflict(detection_result)

            return detection_result, resolution_result

        except Exception as e:
            logger.error(f"混合模式检测失败: {e}")
            return None, None

    @classmethod
    def _load_config(cls) -> Dict:
        """加载 MODE_TASK_LIBRARY.yaml 配置"""
        if cls._mode_tasks_config is not None:
            return cls._mode_tasks_config

        config_path = Path(__file__).parent.parent / "config" / "MODE_TASK_LIBRARY.yaml"

        try:
            if not config_path.exists():
                logger.warning(f"MODE_TASK_LIBRARY.yaml 不存在: {config_path}")
                cls._mode_tasks_config = {}
                return cls._mode_tasks_config

            with open(config_path, encoding="utf-8") as f:
                cls._mode_tasks_config = yaml.safe_load(f) or {}

            logger.info(f"✅ 成功加载 MODE_TASK_LIBRARY.yaml ({len(cls._mode_tasks_config)} 个模式配置)")
            return cls._mode_tasks_config

        except Exception as e:
            logger.error(f"❌ 加载 MODE_TASK_LIBRARY.yaml 失败: {e}")
            cls._mode_tasks_config = {}
            return cls._mode_tasks_config

    @classmethod
    def get_mandatory_tasks_for_modes(
        cls, detected_modes: List[Dict[str, Any]], include_p1: bool = True, include_p2: bool = False
    ) -> Tuple[List[Dict[str, Any]], Optional["ResolutionResult"]]:
        """
        根据检测到的模式，返回必需任务列表

        v7.800: 新增混合模式冲突解决，返回值改为元组

        Args:
            detected_modes: Phase2 检测到的模式列表
                [{"mode": "M1_concept_driven", "confidence": 0.85}, ...]
            include_p1: 是否包含P1推荐任务
            include_p2: 是否包含P2可选任务

        Returns:
            (任务列表, 混合模式解决结果)
            每个任务包含: task_id, task_name, priority, target_expert,
                          description, deliverables, quality_target (或 validation_criteria 兼容旧格式)
        """
        config = cls._load_config()
        global_config = config.get("global_config", {})
        mode_confidence_threshold = global_config.get("mode_confidence_threshold", 0.3)

        # 🆕 P2: 检测混合模式
        detection_result, resolution_result = cls._detect_hybrid_mode(detected_modes)

        if detection_result and detection_result.is_hybrid and resolution_result:
            logger.info(f"🔄 [混合模式任务] {resolution_result.pattern_name}")
            logger.info(f"   策略: {resolution_result.resolution_strategy}")

        # 过滤符合阈值的模式
        valid_modes = [m for m in detected_modes if m.get("confidence", 0) > mode_confidence_threshold]

        if not valid_modes:
            logger.info("⚠️ 未检测到高置信度模式，跳过任务注入")
            return [], None

        # 收集任务
        mandatory_tasks = []
        task_ids = set()  # 避免重复任务

        for mode_dict in valid_modes:
            mode_id = mode_dict["mode"]
            mode_config = config.get(mode_id, {})
            mode_name = mode_config.get("mode_name", mode_id)
            core_tasks = mode_config.get("core_tasks", [])

            for task in core_tasks:
                task_id = task.get("task_id", "")
                priority = task.get("priority", "P2")

                # 根据优先级筛选
                if priority == "P0":
                    should_include = True
                elif priority == "P1":
                    should_include = include_p1
                elif priority == "P2":
                    should_include = include_p2
                else:
                    should_include = False

                if should_include and task_id not in task_ids:
                    # 添加模式来源标记
                    enriched_task = {
                        **task,
                        "source_mode": mode_id,
                        "source_mode_name": mode_name,
                        "mode_confidence": mode_dict.get("confidence", 0),
                    }
                    mandatory_tasks.append(enriched_task)
                    task_ids.add(task_id)

        # 按优先级排序 (P0 > P1 > P2)
        priority_order = {"P0": 0, "P1": 1, "P2": 2}
        mandatory_tasks.sort(key=lambda t: (priority_order.get(t.get("priority", "P2"), 999), t.get("source_mode", "")))

        log_prefix = "[混合模式任务库]" if (detection_result and detection_result.is_hybrid) else "[任务库]"
        logger.info(f"🎯 {log_prefix} 根据 {len(valid_modes)} 个模式生成 {len(mandatory_tasks)} 个必需任务")
        p0_count = sum(1 for t in mandatory_tasks if t.get("priority") == "P0")
        p1_count = sum(1 for t in mandatory_tasks if t.get("priority") == "P1")
        p2_count = sum(1 for t in mandatory_tasks if t.get("priority") == "P2")
        logger.info(f"   P0必做: {p0_count}, P1推荐: {p1_count}, P2可选: {p2_count}")

        return mandatory_tasks, resolution_result

    @classmethod
    def get_task_by_id(cls, task_id: str) -> Dict[str, Any] | None:
        """根据 task_id 获取任务详情"""
        config = cls._load_config()

        for mode_id in config.keys():
            if not mode_id.startswith("M"):
                continue

            mode_config = config.get(mode_id, {})
            core_tasks = mode_config.get("core_tasks", [])

            for task in core_tasks:
                if task.get("task_id") == task_id:
                    return {**task, "source_mode": mode_id}

        return None

    @classmethod
    def get_expert_for_task(cls, task_id: str) -> str | None:
        """获取任务对应的目标专家"""
        task = cls.get_task_by_id(task_id)
        if task:
            return task.get("target_expert")
        return None

    @classmethod
    def get_primary_experts_for_modes(cls, detected_modes: List[Dict[str, Any]]) -> List[str]:
        """
        根据检测到的模式，返回主力专家列表

        Args:
            detected_modes: Phase2 检测到的模式列表

        Returns:
            专家ID列表，如 ["V3", "V2", "V6-1", ...]
        """
        config = cls._load_config()
        global_config = config.get("global_config", {})
        mode_confidence_threshold = global_config.get("mode_confidence_threshold", 0.3)
        mode_to_expert_mapping = config.get("mode_to_expert_mapping", {})

        # 过滤符合阈值的模式
        valid_modes = [m for m in detected_modes if m.get("confidence", 0) > mode_confidence_threshold]

        if not valid_modes:
            return []

        # 收集主力专家
        primary_experts = []
        expert_set = set()

        for mode_dict in valid_modes:
            mode_id = mode_dict["mode"]
            expert_mapping = mode_to_expert_mapping.get(mode_id, {})

            # 主力专家
            for expert_id in expert_mapping.get("primary_experts", []):
                if expert_id not in expert_set:
                    primary_experts.append(expert_id)
                    expert_set.add(expert_id)

        logger.info(f"🎯 [专家推荐] 根据 {len(valid_modes)} 个模式推荐 {len(primary_experts)} 个主力专家")
        logger.info(f"   专家列表: {', '.join(primary_experts)}")

        return primary_experts

    @classmethod
    def get_supporting_experts_for_modes(cls, detected_modes: List[Dict[str, Any]]) -> List[str]:
        """获取辅助专家列表"""
        config = cls._load_config()
        global_config = config.get("global_config", {})
        mode_confidence_threshold = global_config.get("mode_confidence_threshold", 0.3)
        mode_to_expert_mapping = config.get("mode_to_expert_mapping", {})

        valid_modes = [m for m in detected_modes if m.get("confidence", 0) > mode_confidence_threshold]

        if not valid_modes:
            return []

        supporting_experts = []
        expert_set = set()

        for mode_dict in valid_modes:
            mode_id = mode_dict["mode"]
            expert_mapping = mode_to_expert_mapping.get(mode_id, {})

            for expert_id in expert_mapping.get("supporting_experts", []):
                if expert_id not in expert_set:
                    supporting_experts.append(expert_id)
                    expert_set.add(expert_id)

        return supporting_experts

    @classmethod
    def validate_task_coverage(
        cls, detected_modes: List[Dict[str, Any]], allocated_tasks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        验证任务覆盖率：检查P0必做任务是否全部分配

        Args:
            detected_modes: 检测到的模式列表
            allocated_tasks: 已分配的任务列表（来自 project_director）

        Returns:
            验证结果: {
                "status": "passed" | "warning" | "failed",
                "missing_p0_tasks": [...],
                "coverage_rate": 0.85,
                "summary": "..."
            }
        """
        cls._load_config()

        # 获取所有P0必做任务
        p0_tasks = cls.get_mandatory_tasks_for_modes(detected_modes, include_p1=False, include_p2=False)
        p0_task_ids = {task["task_id"] for task in p0_tasks}

        if not p0_task_ids:
            return {"status": "passed", "missing_p0_tasks": [], "coverage_rate": 1.0, "summary": "未检测到P0必做任务"}

        # 检查已分配任务中包含哪些P0任务
        allocated_task_ids = set()
        for task_dict in allocated_tasks:
            # 尝试从任务描述中提取 task_id（如果有标记）
            task_description = str(task_dict.get("description", ""))

            # 简单匹配：如果任务描述包含 "M1_T01"、"M2_T02" 等
            for p0_id in p0_task_ids:
                if p0_id in task_description:
                    allocated_task_ids.add(p0_id)

        # 计算缺失任务
        missing_p0_ids = p0_task_ids - allocated_task_ids
        coverage_rate = (len(allocated_task_ids) / len(p0_task_ids)) if p0_task_ids else 1.0

        if not missing_p0_ids:
            status = "passed"
            summary = f"✅ 所有 {len(p0_task_ids)} 个P0必做任务已覆盖"
        elif len(missing_p0_ids) <= 2:
            status = "warning"
            summary = f"⚠️ 覆盖率 {coverage_rate:.1%}，缺少 {len(missing_p0_ids)} 个P0任务"
        else:
            status = "failed"
            summary = f"❌ 覆盖率 {coverage_rate:.1%}，严重缺少 {len(missing_p0_ids)} 个P0任务"

        # 获取缺失任务详情
        missing_task_details = []
        for task_id in missing_p0_ids:
            task = cls.get_task_by_id(task_id)
            if task:
                missing_task_details.append(
                    {
                        "task_id": task_id,
                        "task_name": task.get("task_name"),
                        "target_expert": task.get("target_expert"),
                        "source_mode": task.get("source_mode"),
                    }
                )

        result = {
            "status": status,
            "missing_p0_tasks": missing_task_details,
            "coverage_rate": coverage_rate,
            "total_p0_tasks": len(p0_task_ids),
            "allocated_p0_tasks": len(allocated_task_ids),
            "summary": summary,
        }

        logger.info(f"🔍 [任务覆盖率验证] {summary}")
        if missing_task_details:
            logger.warning(f"   缺失任务: {', '.join([t['task_id'] for t in missing_task_details])}")

        return result


# ==============================================================================
# 辅助函数
# ==============================================================================


def inject_mandatory_tasks_to_jtbd(
    detected_modes: List[Dict[str, Any]], original_jtbd: List[str]
) -> Tuple[List[str], Optional["ResolutionResult"]]:
    """
    将模式必需任务注入到 JTBD 列表中

    v7.800: 返回值改为元组，包含混合模式解决结果

    Args:
        detected_modes: 检测到的模式列表
        original_jtbd: Phase2 输出的原始 JTBD 列表

    Returns:
        (增强后的 JTBD 列表, 混合模式解决结果)
    """
    mandatory_tasks, resolution_result = ModeTaskLibrary.get_mandatory_tasks_for_modes(
        detected_modes, include_p1=True, include_p2=False  # 包含P1推荐任务  # 不包含P2可选任务
    )

    if not mandatory_tasks:
        return original_jtbd, None

    # 将任务转换为 JTBD 格式
    injected_jtbd = []
    for task in mandatory_tasks:
        task_name = task.get("task_name", "")
        description = task.get("description", "")
        target_expert = task.get("target_expert", "")
        priority = task.get("priority", "P1")
        task_id = task.get("task_id", "")

        # 构建 JTBD 语句
        jtbd = (
            f"[{priority}:{task_id}] 当设计{task.get('source_mode_name', '项目')}时，"
            f"我需要{task_name}（目标专家:{target_expert}），以便{description[:50]}..."
        )

        injected_jtbd.append(jtbd)

    # 合并原始JTBD和注入JTBD
    enhanced_jtbd = original_jtbd + injected_jtbd

    logger.info(f"✅ [JTBD增强] 注入 {len(injected_jtbd)} 个模式必需任务")
    logger.info(f"   原始JTBD: {len(original_jtbd)} 条 → 增强后: {len(enhanced_jtbd)} 条")

    return enhanced_jtbd, resolution_result


def enrich_task_distribution_with_mode_tasks(
    detected_modes: List[Dict[str, Any]], task_distribution: Dict[str, Any]
) -> Dict[str, Any]:
    """
    在任务分配结果中标记模式必需任务的覆盖情况

    Args:
        detected_modes: 检测到的模式列表
        task_distribution: project_director 的任务分配结果

    Returns:
        增强后的 task_distribution，包含 mode_task_coverage 字段
    """
    coverage_result = ModeTaskLibrary.validate_task_coverage(detected_modes, list(task_distribution.values()))

    enriched_distribution = {**task_distribution, "_mode_task_coverage": coverage_result}

    return enriched_distribution


def extract_task_validation(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    提取任务验证标准（兼容新旧格式）

    v8.0: 支持新的 quality_target 格式，同时保持对旧 validation_criteria 格式的兼容

    Args:
        task: 任务字典

    Returns:
        标准化的验证标准字典:
        {
            "format": "quality_target" | "validation_criteria" | "none",
            "data": {...}  # 具体数据结构取决于格式
        }

    Examples:
        # 新格式 (quality_target)
        >>> task = {
        ...     "quality_target": {
        ...         "dimension": "空间叙事性",
        ...         "target_level": "L3",
        ...         "reference": "13_Evaluation_Matrix",
        ...         "criteria_mapping": {...}
        ...     }
        ... }
        >>> result = extract_task_validation(task)
        >>> result["format"]
        'quality_target'

        # 旧格式 (validation_criteria)
        >>> task = {
        ...     "validation_criteria": [
        ...         "必须包含空间叙事分析",
        ...         "需要提供场景设计方案"
        ...     ]
        ... }
        >>> result = extract_task_validation(task)
        >>> result["format"]
        'validation_criteria'
    """
    # 优先使用新格式 quality_target
    if "quality_target" in task:
        quality_target = task["quality_target"]
        return {
            "format": "quality_target",
            "data": {
                "dimension": quality_target.get("dimension", ""),
                "target_level": quality_target.get("target_level", ""),
                "reference": quality_target.get("reference", "13_Evaluation_Matrix"),
                "criteria_mapping": quality_target.get("criteria_mapping", {}),
            },
        }

    # 回退到旧格式 validation_criteria
    elif "validation_criteria" in task:
        return {"format": "validation_criteria", "data": task["validation_criteria"]}

    # 无验证标准
    else:
        return {"format": "none", "data": None}


def get_task_quality_dimension(task: Dict[str, Any]) -> str | None:
    """
    获取任务对应的质量维度（仅适用于 quality_target 格式）

    Args:
        task: 任务字典

    Returns:
        质量维度名称，如果不存在则返回 None

    Example:
        >>> task = {"quality_target": {"dimension": "空间叙事性"}}
        >>> get_task_quality_dimension(task)
        '空间叙事性'
    """
    validation = extract_task_validation(task)
    if validation["format"] == "quality_target":
        return validation["data"].get("dimension")
    return None


def get_task_target_level(task: Dict[str, Any]) -> str | None:
    """
    获取任务的目标质量等级（仅适用于 quality_target 格式）

    Args:
        task: 任务字典

    Returns:
        目标等级，如 "L3", "L4"，如果不存在则返回 None

    Example:
        >>> task = {"quality_target": {"target_level": "L3"}}
        >>> get_task_target_level(task)
        'L3'
    """
    validation = extract_task_validation(task)
    if validation["format"] == "quality_target":
        return validation["data"].get("target_level")
    return None
