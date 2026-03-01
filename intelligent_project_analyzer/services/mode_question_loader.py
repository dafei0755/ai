"""
Mode Question Loader Service (v7.800 P0+P2)

负责加载和处理 MODE_QUESTION_TEMPLATES.yaml 配置
根据检测到的设计模式(detected_modes)，动态注入模式特定问题

v7.800 新增:
- 集成混合模式冲突解决器
- 根据冲突解决策略调整问题和维度优先级
- 添加混合模式设计建议
"""

import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from loguru import logger

# 导入混合模式解决器
try:
    from ..mode_engine.hybrid_mode_resolver import HybridModeResolver, HybridModeDetectionResult, ResolutionResult

    HYBRID_RESOLVER_AVAILABLE = True
except ImportError:
    logger.warning("混合模式解决器导入失败，将使用基础模式处理")
    HYBRID_RESOLVER_AVAILABLE = False


class ModeQuestionLoader:
    """模式问题加载器（v7.800 P0+P2）"""

    _mode_questions_config: Optional[Dict] = None
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
    def _load_config(cls) -> Dict:
        """加载 MODE_QUESTION_TEMPLATES.yaml 配置"""
        if cls._mode_questions_config is not None:
            return cls._mode_questions_config

        config_path = Path(__file__).parent.parent / "config" / "MODE_QUESTION_TEMPLATES.yaml"

        try:
            if not config_path.exists():
                logger.warning(f"MODE_QUESTION_TEMPLATES.yaml 不存在: {config_path}")
                cls._mode_questions_config = {}
                return cls._mode_questions_config

            with open(config_path, "r", encoding="utf-8") as f:
                cls._mode_questions_config = yaml.safe_load(f) or {}

            logger.info(f"✅ 成功加载 MODE_QUESTION_TEMPLATES.yaml ({len(cls._mode_questions_config)} 个模式配置)")
            return cls._mode_questions_config

        except Exception as e:
            logger.error(f"❌ 加载 MODE_QUESTION_TEMPLATES.yaml 失败: {e}")
            cls._mode_questions_config = {}
            return cls._mode_questions_config

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
    def get_priority_dimensions_for_modes(
        cls, detected_modes: List[Dict[str, Any]], max_dimensions: int = 8
    ) -> Tuple[List[str], Optional["ResolutionResult"]]:
        """
        根据检测到的模式，返回优先维度列表

        v7.800: 新增混合模式冲突解决，返回值改为元组

        Args:
            detected_modes: Phase2 检测到的模式列表
                [{"mode": "M1_concept_driven", "confidence": 0.85}, ...]
            max_dimensions: 最多返回的维度数量

        Returns:
            (优先维度ID列表, 混合模式解决结果)
            例如: (["D12_文化叙事", "D03_空间秩序", ...], resolution_result)
        """
        config = cls._load_config()
        global_config = config.get("global_config", {})
        mode_confidence_threshold = global_config.get("mode_confidence_threshold", 0.3)
        mode_priority_order = global_config.get("mode_priority_order", [])

        # 🆕 P2: 检测混合模式
        detection_result, resolution_result = cls._detect_hybrid_mode(detected_modes)

        if detection_result and detection_result.is_hybrid and resolution_result:
            logger.info(f"🔄 [混合模式] {resolution_result.pattern_name}")
            logger.info(f"   策略: {resolution_result.resolution_strategy}")

        # 过滤符合阈值的模式
        valid_modes = [m for m in detected_modes if m.get("confidence", 0) > mode_confidence_threshold]

        if not valid_modes:
            logger.info("⚠️ 未检测到高置信度模式，使用默认功能效率型")
            default_mode = global_config.get("default_mode", "M2_function_efficiency")
            valid_modes = [{"mode": default_mode, "confidence": 1.0}]

        # 按优先级排序模式
        def get_mode_priority(mode_dict):
            mode_id = mode_dict.get("mode", "")
            try:
                return mode_priority_order.index(mode_id)
            except ValueError:
                return 999  # 未定义优先级的排在最后

        sorted_modes = sorted(valid_modes, key=get_mode_priority)

        # 收集优先维度（按模式优先级顺序）
        priority_dimensions = []
        dimension_set = set()

        for mode_dict in sorted_modes:
            mode_id = mode_dict["mode"]
            mode_config = config.get(mode_id, {})
            mode_dims = mode_config.get("priority_dimensions", [])

            for dim in mode_dims:
                if dim not in dimension_set and len(priority_dimensions) < max_dimensions:
                    priority_dimensions.append(dim)
                    dimension_set.add(dim)

            if len(priority_dimensions) >= max_dimensions:
                break

        log_prefix = "[混合模式优先维度]" if (detection_result and detection_result.is_hybrid) else "[Mode优先维度]"
        logger.info(f"🎯 {log_prefix} 根据 {len(sorted_modes)} 个模式生成 {len(priority_dimensions)} 个优先维度")
        for i, dim in enumerate(priority_dimensions):
            logger.info(f"   {i+1}. {dim}")

        return priority_dimensions, resolution_result

    @classmethod
    def get_step1_questions_for_modes(
        cls, detected_modes: List[Dict[str, Any]], max_questions: int = 5
    ) -> List[Dict[str, Any]]:
        """
        根据检测到的模式，返回 Step1 任务梳理阶段的引导问题

        Args:
            detected_modes: Phase2 检测到的模式列表
            max_questions: 最多返回的问题数量

        Returns:
            问题列表，每个问题包含: question, dimension_tag, purpose, example_answer, options
        """
        config = cls._load_config()
        global_config = config.get("global_config", {})
        mode_confidence_threshold = global_config.get("mode_confidence_threshold", 0.3)
        mode_priority_order = global_config.get("mode_priority_order", [])

        # 过滤符合阈值的模式
        valid_modes = [m for m in detected_modes if m.get("confidence", 0) > mode_confidence_threshold]

        if not valid_modes:
            default_mode = global_config.get("default_mode", "M2_function_efficiency")
            valid_modes = [{"mode": default_mode, "confidence": 1.0}]

        # 按优先级排序
        def get_mode_priority(mode_dict):
            mode_id = mode_dict.get("mode", "")
            try:
                return mode_priority_order.index(mode_id)
            except ValueError:
                return 999

        sorted_modes = sorted(valid_modes, key=get_mode_priority)

        # 收集问题
        questions = []
        question_ids = set()  # 避免重复问题

        for mode_dict in sorted_modes:
            mode_id = mode_dict["mode"]
            mode_config = config.get(mode_id, {})
            mode_name = mode_config.get("mode_name", mode_id)
            step1_questions = mode_config.get("step1_questions", [])

            for q in step1_questions:
                q_text = q.get("question", "")
                q_id = f"{mode_id}:{q_text[:30]}"  # 简单去重

                if q_id not in question_ids and len(questions) < max_questions:
                    # 添加模式来源标记
                    enriched_q = {**q, "source_mode": mode_id, "source_mode_name": mode_name}
                    questions.append(enriched_q)
                    question_ids.add(q_id)

            if len(questions) >= max_questions:
                break

        logger.info(f"🎯 [Step1 模式问题] 根据 {len(sorted_modes)} 个模式生成 {len(questions)} 个引导问题")
        for i, q in enumerate(questions):
            logger.info(f"   {i+1}. [{q['source_mode_name']}] {q['question'][:50]}...")

        return questions

    @classmethod
    def get_step2_dimension_prompts_for_modes(
        cls, detected_modes: List[Dict[str, Any]], selected_dimensions: List[str]
    ) -> Dict[str, List[str]]:
        """
        根据检测到的模式和选中的维度，返回 Step2 雷达图阶段的子维度追问

        Args:
            detected_modes: Phase2 检测到的模式列表
            selected_dimensions: Step2 用户选择的维度ID列表

        Returns:
            维度ID -> 追问列表的映射
            如 {"D12_文化叙事": ["这个项目的文化母题是否能避免符号堆砌？", ...], ...}
        """
        config = cls._load_config()
        global_config = config.get("global_config", {})
        mode_confidence_threshold = global_config.get("mode_confidence_threshold", 0.3)

        # 过滤符合阈值的模式
        valid_modes = [m for m in detected_modes if m.get("confidence", 0) > mode_confidence_threshold]

        if not valid_modes:
            return {}

        # 收集维度追问
        dimension_prompts = {}

        for dim_id in selected_dimensions:
            prompts_for_dim = []

            for mode_dict in valid_modes:
                mode_id = mode_dict["mode"]
                mode_config = config.get(mode_id, {})
                step2_prompts = mode_config.get("step2_dimension_prompts", {})

                if dim_id in step2_prompts:
                    mode_prompts = step2_prompts[dim_id]
                    prompts_for_dim.extend(mode_prompts)

            if prompts_for_dim:
                dimension_prompts[dim_id] = prompts_for_dim

        logger.info(f"🎯 [Step2 维度追问] 为 {len(dimension_prompts)} 个维度生成模式特定追问")
        for dim_id, prompts in dimension_prompts.items():
            logger.info(f"   {dim_id}: {len(prompts)} 个追问")

        return dimension_prompts

    @classmethod
    def get_step3_gap_filling_rules_for_modes(cls, detected_modes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        根据检测到的模式，返回 Step3 缺口追问阶段的验证规则

        Args:
            detected_modes: Phase2 检测到的模式列表

        Returns:
            验证规则列表，每个规则包含: condition, question, required, source_mode
        """
        config = cls._load_config()
        global_config = config.get("global_config", {})
        mode_confidence_threshold = global_config.get("mode_confidence_threshold", 0.3)

        # 过滤符合阈值的模式
        valid_modes = [m for m in detected_modes if m.get("confidence", 0) > mode_confidence_threshold]

        if not valid_modes:
            return []

        # 收集验证规则
        gap_filling_rules = []

        for mode_dict in valid_modes:
            mode_id = mode_dict["mode"]
            mode_config = config.get(mode_id, {})
            mode_name = mode_config.get("mode_name", mode_id)
            step3_rules = mode_config.get("step3_gap_filling_rules", [])

            for rule in step3_rules:
                enriched_rule = {**rule, "source_mode": mode_id, "source_mode_name": mode_name}
                gap_filling_rules.append(enriched_rule)

        # 按 required=true 优先排序
        gap_filling_rules.sort(key=lambda r: (not r.get("required", False), r.get("source_mode", "")))

        logger.info(f"🎯 [Step3 缺口规则] 根据 {len(valid_modes)} 个模式生成 {len(gap_filling_rules)} 条验证规则")
        required_count = sum(1 for r in gap_filling_rules if r.get("required", False))
        logger.info(f"   其中必需规则: {required_count} 条，可选规则: {len(gap_filling_rules) - required_count} 条")

        return gap_filling_rules

    @classmethod
    def get_mode_info(cls, mode_id: str) -> Dict[str, Any]:
        """获取指定模式的完整信息"""
        config = cls._load_config()
        return config.get(mode_id, {})

    @classmethod
    def get_all_mode_ids(cls) -> List[str]:
        """获取所有模式ID列表"""
        config = cls._load_config()
        config.get("global_config", {})
        return [k for k in config.keys() if k.startswith("M") and k != "global_config"]


# ==============================================================================
# 辅助函数
# ==============================================================================


def extract_detected_modes_from_state(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    从 ProjectAnalysisState 中提取 detected_modes

    Args:
        state: ProjectAnalysisState

    Returns:
        detected_modes 列表，如 [{"mode": "M1_concept_driven", "confidence": 0.85}, ...]
    """
    agent_results = state.get("agent_results", {})
    requirements_analyst_result = agent_results.get("requirements_analyst", {})
    structured_data = requirements_analyst_result.get("structured_data", {})

    # v7.900: Phase2 输出的 detected_modes
    detected_modes = structured_data.get("detected_modes", [])

    # v8.0 P0: 兼容 T1 写入的 detected_design_modes 键
    if not detected_modes:
        detected_modes = structured_data.get("detected_design_modes", [])

    # 兼容旧格式：{"design_modes": {...}}
    if not detected_modes:
        design_modes_dict = structured_data.get("design_modes", {})
        if design_modes_dict:
            detected_modes = [{"mode": mode_id, "confidence": conf} for mode_id, conf in design_modes_dict.items()]

    return detected_modes


def enrich_step1_payload_with_mode_questions(state: Dict[str, Any], base_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    在 Step1 payload 中注入模式特定问题

    Args:
        state: ProjectAnalysisState
        base_payload: 原始 Step1 interrupt payload

    Returns:
        增强后的 payload，包含 mode_guided_questions 字段
    """
    detected_modes = extract_detected_modes_from_state(state)

    if not detected_modes:
        logger.info("⚠️ [Step1] 未检测到模式，跳过模式问题注入")
        return base_payload

    mode_questions = ModeQuestionLoader.get_step1_questions_for_modes(detected_modes)

    enriched_payload = {
        **base_payload,
        "mode_guided_questions": mode_questions,
        "detected_modes_summary": [{"mode_id": m["mode"], "confidence": m["confidence"]} for m in detected_modes],
    }

    logger.info(f"✅ [Step1] 注入 {len(mode_questions)} 个模式引导问题")

    return enriched_payload
