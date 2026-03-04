"""
Dimension Selector - Dynamically select radar chart dimensions based on project type

v7.80: Core service for three-step progressive questionnaire system
v7.80.15 (P0.3): Integrate special scenario detector, auto-inject specialized dimensions
v7.137 (Phase 1): Intelligence optimization - synonym matching, task mapping, answer inference
v7.138 (Phase 2): LLM requirement understanding layer - use LLM to deeply understand user needs and recommend dimensions
v7.139 (Phase 3): Dimension correlation modeling - detect conflicts and generate adjustment suggestions
"""

import random
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import yaml
from loguru import logger

# v7.80.15 (P0.3): 场景 → 专用维度映射
SCENARIO_DIMENSION_MAPPING = {
    "extreme_environment": ["environmental_adaptation"],
    "medical_special_needs": ["accessibility_level"],
    "cultural_depth": ["cultural_authenticity"],
    "tech_geek": ["acoustic_performance", "automation_workflow"],
    "complex_relationships": ["conflict_mediation"],
    "poetic_philosophical": ["spiritual_atmosphere"],
    "extreme_budget": ["cost_efficiency"],
    "innovative_business": ["automation_workflow"],
}


class DimensionSelector:
    """
    Dimension Selector

    Select 9-12 most relevant dimensions from dimension library based on project type and user keywords.
    """

    _instance = None
    _dimensions_config: Dict[str, Any] | None = None
    _task_mapping_config: Dict[str, Any] | None = None  # v7.137: 任务映射配置
    _answer_rules_config: Dict[str, Any] | None = None  # v7.137: 答案推理配置
    _llm_recommender = None  # v7.138: LLM维度推荐器
    _correlation_detector = None  # v7.139: 维度关联检测器

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if DimensionSelector._dimensions_config is None:
            self._load_config()
        if DimensionSelector._task_mapping_config is None:
            self._load_task_mapping_config()
        if DimensionSelector._answer_rules_config is None:
            self._load_answer_rules_config()
        if DimensionSelector._llm_recommender is None:
            self._init_llm_recommender()
        if DimensionSelector._correlation_detector is None:
            self._init_correlation_detector()

    def _load_config(self) -> None:
        """加载维度配置文件"""
        config_path = Path(__file__).parent.parent / "config" / "prompts" / "radar_dimensions.yaml"

        if not config_path.exists():
            logger.error(f"[ERROR] 维度配置文件不存在: {config_path}")
            DimensionSelector._dimensions_config = {}
            return

        try:
            with open(config_path, encoding="utf-8") as f:
                DimensionSelector._dimensions_config = yaml.safe_load(f)
            logger.info(f"[OK] 维度配置加载成功: {len(self._dimensions_config.get('dimensions', {}))} 个维度")
        except Exception as e:
            logger.error(f"[ERROR] 维度配置加载失败: {e}")
            DimensionSelector._dimensions_config = {}

    def _load_task_mapping_config(self) -> None:
        """v7.137: 加载任务映射配置文件"""
        config_path = Path(__file__).parent.parent / "config" / "prompts" / "task_dimension_mapping.yaml"

        if not config_path.exists():
            logger.warning(f"[WARNING] 任务映射配置文件不存在: {config_path}，功能降级")
            DimensionSelector._task_mapping_config = {}
            return

        try:
            with open(config_path, encoding="utf-8") as f:
                DimensionSelector._task_mapping_config = yaml.safe_load(f)
            task_count = len(self._task_mapping_config.get("task_mappings", {}))
            logger.info(f"[OK] [v7.137] 任务映射配置加载成功: {task_count} 个任务类型")
        except Exception as e:
            logger.error(f"[ERROR] 任务映射配置加载失败: {e}")
            DimensionSelector._task_mapping_config = {}

    def _load_answer_rules_config(self) -> None:
        """v7.137: 加载答案推理规则配置文件"""
        config_path = Path(__file__).parent.parent / "config" / "prompts" / "answer_to_dimension_rules.yaml"

        if not config_path.exists():
            logger.warning(f"[WARNING] 答案推理规则配置文件不存在: {config_path}，功能降级")
            DimensionSelector._answer_rules_config = {}
            return

        try:
            with open(config_path, encoding="utf-8") as f:
                DimensionSelector._answer_rules_config = yaml.safe_load(f)
            rule_count = len(self._answer_rules_config.get("inference_rules", []))
            logger.info(f"[OK] [v7.137] 答案推理规则加载成功: {rule_count} 条规则")
        except Exception as e:
            logger.error(f"[ERROR] 答案推理规则加载失败: {e}")
            DimensionSelector._answer_rules_config = {}

    def _init_llm_recommender(self) -> None:
        """v7.138: 初始化LLM维度推荐器"""
        try:
            from .llm_dimension_recommender import LLMDimensionRecommender

            DimensionSelector._llm_recommender = LLMDimensionRecommender()
            if DimensionSelector._llm_recommender.is_enabled():
                logger.info("[OK] [v7.138] LLM维度推荐器初始化成功")
            else:
                logger.info("[INFO] [v7.138] LLM维度推荐器已禁用（通过环境变量）")
        except Exception as e:
            logger.warning(f"[WARNING] [v7.138] LLM维度推荐器初始化失败，功能降级: {e}")
            DimensionSelector._llm_recommender = None

    def _init_correlation_detector(self) -> None:
        """v7.139: 初始化维度关联检测器"""
        try:
            from .dimension_correlation_detector import DimensionCorrelationDetector

            DimensionSelector._correlation_detector = DimensionCorrelationDetector()
            if DimensionSelector._correlation_detector.is_enabled():
                logger.info("[OK] [v7.139] 维度关联检测器初始化成功")
            else:
                logger.info("[INFO] [v7.139] 维度关联检测器已禁用")
        except Exception as e:
            logger.warning(f"[WARNING] [v7.139] 维度关联检测器初始化失败，功能降级: {e}")
            DimensionSelector._correlation_detector = None

    @property
    def config(self) -> Dict[str, Any]:
        """获取配置"""
        return DimensionSelector._dimensions_config or {}

    def get_all_dimensions(self) -> Dict[str, Dict[str, Any]]:
        """获取所有维度定义"""
        return self.config.get("dimensions", {})

    def get_dimension_by_id(self, dimension_id: str) -> Dict[str, Any] | None:
        """根据ID获取单个维度"""
        return self.get_all_dimensions().get(dimension_id)

    def get_project_type_mapping(self, project_type: str) -> Dict[str, List[str]]:
        """获取项目类型对应的维度映射"""
        mappings = self.config.get("project_type_dimensions", {})
        return mappings.get(project_type, mappings.get("personal_residential", {}))

    def select_for_project(
        self,
        project_type: str,
        user_input: str = "",
        structured_data: Dict[str, Any] | None = None,
        min_dimensions: int = 9,
        max_dimensions: int = 12,
        special_scenes: List[str] | None = None,
        confirmed_tasks: List[Dict[str, Any]] | None = None,  # v7.137: Step1任务列表
        gap_filling_answers: Dict[str, str] | None = None,  # v7.137: Step2答案
    ) -> Dict[str, Any]:
        """
        为项目选择合适的维度

        算法（v7.152增强版）：
        0. v7.152: 自动检测项目类型（如果传入 "auto" 或空值）
        1. 从项目类型映射中获取 required 和 recommended 维度
        2. 根据用户输入的关键词匹配额外的 optional 维度（支持同义词）
        3. v7.138: 调用LLM深度理解需求，推荐维度（可选）
        4. v7.137: 基于confirmed_tasks进行任务映射增强
        5. 处理特殊场景，注入专用维度
        6. v7.137: 基于gap_filling_answers进行答案推理，调整默认值
        7. v7.139: 维度关联检测，识别冲突并生成调整建议
        8. 确保维度数量在 9-12 个之间

        Args:
            project_type: 项目类型（如 "personal_residential", "commercial_enterprise"）
                          传入 "auto" 或空字符串时自动检测
            user_input: 用户原始输入（用于关键词匹配）
            structured_data: 结构化数据（可选）
            min_dimensions: 最小维度数量
            max_dimensions: 最大维度数量
            special_scenes: 特殊场景标签列表（可选，用于注入专用维度）
            confirmed_tasks: Step1确认的核心任务列表（用于任务映射和LLM推荐）
            gap_filling_answers: Step2信息补全答案（用于答案推理和LLM推荐）

        Returns:
            字典，包含：
            - dimensions: 维度配置列表
            - conflicts: 冲突列表（v7.139新增）
            - adjustment_suggestions: 调整建议列表（v7.139新增）
            - detected_project_type: 自动检测的项目类型（v7.152新增，仅当自动检测时）
        """
        # v7.152: 自动检测项目类型
        detected_type_info = None
        if project_type == "auto" or not project_type:
            try:
                from .project_type_detector import ProjectTypeDetector

                detector = ProjectTypeDetector()
                detected_type_info = detector.detect_with_details(user_input, confirmed_tasks)
                project_type = detected_type_info["project_type"]
                logger.info(
                    f"[v7.152] 自动检测项目类型: {detected_type_info['project_type_name']} "
                    f"({project_type}), 置信度: {detected_type_info['confidence']:.0%}"
                )
            except Exception as e:
                logger.warning(f"[v7.152] 项目类型自动检测失败: {e}，使用默认类型")
                project_type = "personal_residential"

        logger.info(f"[INFO] 开始为项目选择维度: project_type={project_type}, special_scenes={special_scenes}")

        all_dimensions = self.get_all_dimensions()
        if not all_dimensions:
            logger.warning("[WARNING] 维度库为空，使用默认维度")
            return self._get_default_dimensions(max_dimensions)

        # 获取项目类型映射
        type_mapping = self.get_project_type_mapping(project_type)
        required = type_mapping.get("required", [])
        recommended = type_mapping.get("recommended", [])
        optional = type_mapping.get("optional", [])

        logger.info(
            f"[INFO] 项目类型 '{project_type}' 映射: required={len(required)}, recommended={len(recommended)}, optional={len(optional)}"
        )

        # 已选择的维度ID集合
        selected_ids: Set[str] = set()

        # Step 1: 添加所有 required 维度
        for dim_id in required:
            if dim_id in all_dimensions:
                selected_ids.add(dim_id)

        # Step 2: 添加 recommended 维度（直到达到目标数量）
        for dim_id in recommended:
            if len(selected_ids) >= max_dimensions:
                break
            if dim_id in all_dimensions and dim_id not in selected_ids:
                selected_ids.add(dim_id)

        # Step 3: 如果数量不够，根据关键词匹配 optional 维度（v7.137: 支持同义词）
        if len(selected_ids) < min_dimensions and user_input:
            keyword_matches = self._match_dimensions_by_keywords(user_input, optional, all_dimensions)
            for dim_id in keyword_matches:
                if len(selected_ids) >= max_dimensions:
                    break
                if dim_id not in selected_ids:
                    selected_ids.add(dim_id)
                    logger.info(f"[INFO] 关键词匹配添加维度: {dim_id}")

        # Step 3.5: v7.138 - LLM深度理解需求并推荐维度（可选）
        llm_result = None  # 保存LLM推荐结果，避免重复调用
        if self._llm_recommender and self._llm_recommender.is_enabled():
            logger.info("[INFO] [v7.138] 启动LLM维度推荐...")
            llm_result = self._llm_recommender.recommend_dimensions(
                project_type=project_type,
                user_input=user_input,
                all_dimensions=self._dimensions_config.get("dimensions", {}),  # 传递所有可用维度
                required_dimensions=list(required),  # 传递必选维度，确保LLM不会遗漏
                confirmed_tasks=confirmed_tasks or [],
                gap_filling_answers=gap_filling_answers or {},
                min_dimensions=min_dimensions,
                max_dimensions=max_dimensions,
            )

            if llm_result and llm_result.get("recommended_dimensions"):
                logger.info(
                    f"[OK] [v7.138] LLM推荐成功，置信度: {llm_result.get('confidence', 'N/A')}, 推理原因: {llm_result.get('reasoning', 'N/A')}"
                )

                # 合并LLM推荐的维度到selected_ids（去重）
                llm_dimensions = llm_result["recommended_dimensions"]
                added_count = 0
                for llm_dim in llm_dimensions:
                    dim_id = llm_dim.get("dimension_id")
                    if dim_id and dim_id in all_dimensions and dim_id not in selected_ids:
                        if len(selected_ids) < max_dimensions:
                            selected_ids.add(dim_id)
                            added_count += 1
                            logger.info(f"   [INFO] LLM推荐维度: {dim_id} (默认值: {llm_dim.get('default_value', 50)})")

                logger.info(f"[OK] [v7.138] LLM推荐层完成，新增 {added_count} 个维度")
            else:
                logger.warning("[WARNING] [v7.138] LLM推荐失败或返回空结果，继续使用规则引擎")
        else:
            logger.debug("[INFO] [v7.138] LLM维度推荐器未启用，跳过LLM推荐层")

        # Step 4: 如果仍然不够，从默认维度补充
        if len(selected_ids) < min_dimensions:
            default_dims = self.config.get("default_dimensions", [])
            for dim_id in default_dims:
                if len(selected_ids) >= min_dimensions:
                    break
                if dim_id in all_dimensions and dim_id not in selected_ids:
                    selected_ids.add(dim_id)

        # Step 5: 处理特殊场景，注入专用维度
        if special_scenes:
            logger.info(f"[INFO] [特殊场景处理] 检测到 {len(special_scenes)} 个特殊场景: {special_scenes}")
            injected_count = 0

            for scene in special_scenes:
                # 获取场景对应的专用维度
                specialized_dims = SCENARIO_DIMENSION_MAPPING.get(scene, [])
                if not specialized_dims:
                    logger.debug(f"   [INFO] 场景 '{scene}' 没有配置专用维度")
                    continue

                logger.info(f"   [INFO] 场景 '{scene}' 映射到专用维度: {specialized_dims}")

                # 注入专用维度
                for dim_id in specialized_dims:
                    if dim_id in all_dimensions and dim_id not in selected_ids:
                        selected_ids.add(dim_id)
                        injected_count += 1
                        logger.info(f"      [OK] 注入专用维度: {dim_id} (场景: {scene})")
                    elif dim_id in selected_ids:
                        logger.debug(f"      [INFO] 维度 '{dim_id}' 已存在，跳过")
                    else:
                        logger.warning(f"      [WARNING] 维度 '{dim_id}' 在配置中不存在，跳过")

            if injected_count > 0:
                logger.info(f"   [OK] [特殊场景处理完成] 共注入 {injected_count} 个专用维度")
            else:
                logger.info("   [INFO] [特殊场景处理完成] 未注入新维度（可能已存在或配置缺失）")
        else:
            logger.debug("[INFO] 未检测到特殊场景，跳过专用维度注入")

        # 构建最终的维度配置列表
        result = []
        # v7.138: 如果LLM返回了推荐结果，优先使用LLM的default_value
        llm_default_values = {}
        if llm_result and llm_result.get("recommended_dimensions"):
            for llm_dim in llm_result["recommended_dimensions"]:
                dim_id = llm_dim.get("dimension_id")
                default_value = llm_dim.get("default_value")
                if dim_id and default_value is not None:
                    llm_default_values[dim_id] = default_value

        for dim_id in selected_ids:
            dim_config = all_dimensions.get(dim_id)
            if dim_config:
                # v7.138: 优先使用LLM推荐的default_value
                default_value = llm_default_values.get(dim_id, dim_config.get("default_value", 50))
                # v7.150: 标记维度是否来自LLM推荐
                is_llm_recommended = dim_id in llm_default_values

                result.append(
                    {
                        "id": dim_id,  # 使用 dimension_id 作为 id（与 YAML 键一致）
                        "dimension_id": dim_id,  # 冗余字段，兼容前端
                        "name": dim_config.get("name", dim_id),
                        "left_label": dim_config.get("left_label", "低"),
                        "right_label": dim_config.get("right_label", "高"),
                        "description": dim_config.get("description", ""),
                        "default_value": default_value,  # v7.138: 优先使用LLM推荐的default_value
                        "category": dim_config.get("category", "other"),
                        "gap_threshold": dim_config.get("gap_threshold", 30),
                        "recommended_by_llm": is_llm_recommended,  # v7.150: 标记LLM推荐
                    }
                )

        # v7.137 Step 6: 任务映射增强
        if confirmed_tasks:
            result, injected_ids = self.enhance_dimensions_with_task_mapping(confirmed_tasks, result)

        # v7.137 Step 7: 答案推理
        if gap_filling_answers:
            result = self.apply_answer_to_dimension_rules(gap_filling_answers, result)

        # 按类别排序（美学 → 功能 → 科技 → 资源 → 体验）
        category_order = ["aesthetic", "functional", "technology", "resource", "experience", "other"]
        result.sort(key=lambda x: (category_order.index(x["category"]) if x["category"] in category_order else 99))

        # v7.139 Step 8: 维度关联检测
        conflicts = []
        adjustment_suggestions = []
        if self._correlation_detector and self._correlation_detector.is_enabled():
            logger.info("[INFO] [v7.139] 启动维度关联检测...")
            conflicts = self._correlation_detector.detect_conflicts(result)
            if conflicts:
                logger.info(f"   [WARNING] 检测到 {len(conflicts)} 个潜在冲突")
                adjustment_suggestions = self._correlation_detector.suggest_adjustments(conflicts, result)
                if adjustment_suggestions:
                    logger.info(f"   [INFO] 生成 {len(adjustment_suggestions)} 条调整建议")

        logger.info(f"[OK] 维度选择完成: {len(result)} 个维度")
        for dim in result:
            logger.debug(f"   - {dim['id']}: {dim['name']} ({dim['category']})")

        # v7.139: 在返回结果中添加关联检测信息
        # 注意：为保持向后兼容，老版本代码可能只使用dimensions字段
        result_dict = {
            "dimensions": result,
            "conflicts": conflicts,
            "adjustment_suggestions": adjustment_suggestions,
        }

        # v7.152: 添加自动检测的项目类型信息
        if detected_type_info:
            result_dict["detected_project_type"] = detected_type_info

        return result_dict

    def validate_dimensions(self, dimensions: List[Dict[str, Any]], mode: str | None = None) -> Dict[str, Any]:
        """
        v7.139: Validate dimension configuration and detect conflicts

        This is a standalone API for real-time validation of user-adjusted dimensions.

        Args:
            dimensions: List of dimension configurations (user-adjusted)
            mode: Detection mode (strict/balanced/lenient), defaults to config file setting

        Returns:
            Dictionary containing:
            - conflicts: List of conflicts
            - adjustment_suggestions: List of adjustment suggestions
            - is_valid: Whether validation passed (no critical conflicts)
        """
        if not self._correlation_detector or not self._correlation_detector.is_enabled():
            return {
                "conflicts": [],
                "adjustment_suggestions": [],
                "is_valid": True,
            }

        conflicts = self._correlation_detector.detect_conflicts(dimensions, mode=mode)
        adjustment_suggestions = []
        if conflicts:
            adjustment_suggestions = self._correlation_detector.suggest_adjustments(conflicts, dimensions)

        # 检查是否有critical冲突
        has_critical = any(c["severity"] == "critical" for c in conflicts)

        return {
            "conflicts": conflicts,
            "adjustment_suggestions": adjustment_suggestions,
            "is_valid": not has_critical,
        }

    def _match_dimensions_by_keywords(
        self, user_input: str, dimension_ids: List[str], all_dimensions: Dict[str, Dict[str, Any]]
    ) -> List[str]:
        """
        根据用户输入的关键词匹配维度

        v7.137: 增强版 - 支持同义词匹配和排除词过滤

        Returns:
            匹配度排序后的维度ID列表
        """
        user_input_lower = user_input.lower()
        scores: Dict[str, int] = {}

        for dim_id in dimension_ids:
            dim_config = all_dimensions.get(dim_id, {})
            keywords = dim_config.get("keywords", [])
            synonyms = dim_config.get("synonyms", [])  # v7.137: 同义词
            negative_keywords = dim_config.get("negative_keywords", [])  # v7.137: 排除词

            score = 0

            # Step 1: 核心关键词匹配 (权重 2)
            for keyword in keywords:
                if keyword.lower() in user_input_lower:
                    score += 2

            # Step 2: 同义词匹配 (权重 1)
            for synonym in synonyms:
                if synonym.lower() in user_input_lower:
                    score += 1

            # Step 3: 排除词过滤（如果匹配到排除词，降低分数）
            for neg_keyword in negative_keywords:
                if neg_keyword.lower() in user_input_lower:
                    score -= 1  # 降低优先级

            if score > 0:
                scores[dim_id] = score

        # 按匹配度降序排序
        sorted_dims = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        if sorted_dims:
            logger.info(f"[INFO] [v7.137] 关键词匹配结果（含同义词）: {len(sorted_dims)} 个维度")
            for dim_id in sorted_dims[:5]:  # 只显示前5个
                logger.debug(f"   - {dim_id}: score={scores[dim_id]}")

        return sorted_dims

    def _get_default_dimensions(self, count: int = 12) -> List[Dict[str, Any]]:
        """Get default dimensions (used when config loading fails)"""
        default_dims = [
            {
                "id": "cultural_axis",
                "name": "文化归属轴",
                "left_label": "东方",
                "right_label": "西方",
                "default_value": 50,
                "category": "aesthetic",
            },
            {
                "id": "temporal_axis",
                "name": "时序定位轴",
                "left_label": "古典",
                "right_label": "未来",
                "default_value": 50,
                "category": "aesthetic",
            },
            {
                "id": "function_intensity",
                "name": "功能强度轴",
                "left_label": "形式体验",
                "right_label": "极致实用",
                "default_value": 50,
                "category": "functional",
            },
            {
                "id": "decoration_density",
                "name": "装饰密度轴",
                "left_label": "极简",
                "right_label": "繁复",
                "default_value": 30,
                "category": "aesthetic",
            },
            {
                "id": "material_temperature",
                "name": "材料温度轴",
                "left_label": "冰冷工业",
                "right_label": "温暖自然",
                "default_value": 60,
                "category": "aesthetic",
            },
            {
                "id": "tech_visibility",
                "name": "科技渗透轴",
                "left_label": "隐藏科技",
                "right_label": "显性科技",
                "default_value": 40,
                "category": "technology",
            },
            {
                "id": "space_flexibility",
                "name": "空间灵活度轴",
                "left_label": "固定功能",
                "right_label": "多功能可变",
                "default_value": 50,
                "category": "functional",
            },
            {
                "id": "privacy_level",
                "name": "私密度轴",
                "left_label": "开放通透",
                "right_label": "私密隔离",
                "default_value": 50,
                "category": "functional",
            },
            {
                "id": "energy_level",
                "name": "能量层级轴",
                "left_label": "静谧放松",
                "right_label": "活力动感",
                "default_value": 40,
                "category": "experience",
            },
            {
                "id": "social_vs_private",
                "name": "社交属性轴",
                "left_label": "独处空间",
                "right_label": "社交中心",
                "default_value": 50,
                "category": "experience",
            },
            {
                "id": "budget_priority",
                "name": "预算优先度轴",
                "left_label": "严格控预算",
                "right_label": "品质优先",
                "default_value": 50,
                "category": "resource",
            },
            {
                "id": "natural_connection",
                "name": "自然连接轴",
                "left_label": "人工环境",
                "right_label": "自然融合",
                "default_value": 50,
                "category": "experience",
            },
        ]
        return default_dims[:count]

    def detect_and_inject_specialized_dimensions(
        self,
        user_input: str,
        confirmed_tasks: List[Dict[str, Any]],
        current_dimensions: List[Dict[str, Any]],
        special_scene_metadata: Dict[str, Any] | None = None,
    ) -> List[Dict[str, Any]]:
        """
        v7.80.15 (P0.3): 检测特殊场景并注入专用维度

        Args:
            user_input: 用户原始输入
            confirmed_tasks: 确认的核心任务列表
            current_dimensions: 当前已选择的维度列表
            special_scene_metadata: 特殊场景元数据（从 Step 1 传入，可选）

        Returns:
            注入专用维度后的维度列表（最多15个）
        """
        # 检测特殊场景
        detected_scenes = self._detect_special_scenarios(user_input, confirmed_tasks, special_scene_metadata)

        if not detected_scenes:
            logger.info("[INFO] 未检测到特殊场景，保持当前维度")
            return current_dimensions

        logger.info(f"[INFO] [特殊场景] 检测到 {len(detected_scenes)} 个场景: {list(detected_scenes.keys())}")

        # 获取所有维度配置
        all_dimensions = self.get_all_dimensions()
        current_dim_ids = {dim["id"] for dim in current_dimensions}

        # 需要注入的专用维度
        to_inject = []

        for scene_id, scene_info in detected_scenes.items():
            specialized_dim_ids = SCENARIO_DIMENSION_MAPPING.get(scene_id, [])
            for dim_id in specialized_dim_ids:
                if dim_id not in current_dim_ids and dim_id in all_dimensions:
                    dim_config = all_dimensions[dim_id]
                    to_inject.append(
                        {
                            "id": dim_config.get("id", dim_id),
                            "name": dim_config.get("name", dim_id),
                            "left_label": dim_config.get("left_label", "低"),
                            "right_label": dim_config.get("right_label", "高"),
                            "description": dim_config.get("description", ""),
                            "default_value": dim_config.get("default_value", 50),
                            "category": dim_config.get("category", "other"),
                            "gap_threshold": dim_config.get("gap_threshold", 30),
                            "generated": True,  # 标记为场景自动生成
                            "triggered_by_scene": scene_id,  # 记录触发场景
                        }
                    )
                    logger.info(f"   [OK] 注入专用维度: {dim_id} (场景: {scene_id})")

        # 合并维度（限制最多15个）
        result = current_dimensions + to_inject
        if len(result) > 15:
            logger.warning(f"[WARNING] 维度总数超过15个 ({len(result)})，保留前15个")
            result = result[:15]

        logger.info(f"[OK] [特殊场景] 注入完成: {len(current_dimensions)} → {len(result)} 个维度")
        return result

    def _detect_special_scenarios(
        self,
        user_input: str,
        confirmed_tasks: List[Dict[str, Any]],
        special_scene_metadata: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """
        检测特殊场景（复用 task_completeness_analyzer.py 的 SPECIAL_SCENARIO_DETECTORS）

        Returns:
            {
                "scene_id": {
                    "matched_keywords": ["keyword1", "keyword2"],
                    "trigger_message": "检测到XXX场景..."
                }
            }
        """
        # 优先使用 Step 1 传入的场景标签
        if special_scene_metadata and "scene_tags" in special_scene_metadata:
            logger.info(f"[INFO] 使用 Step 1 传入的场景标签: {special_scene_metadata['scene_tags']}")
            detected = {}
            for scene_tag in special_scene_metadata["scene_tags"]:
                detected[scene_tag] = {
                    "matched_keywords": special_scene_metadata.get("matched_keywords", {}).get(scene_tag, []),
                    "trigger_message": f"Step 1 识别的场景: {scene_tag}",
                }
            return detected

        # 否则，基于关键词实时检测
        from ..services.task_completeness_analyzer import SPECIAL_SCENARIO_DETECTORS

        detected_scenarios = {}
        combined_text = f"{user_input} {self._build_task_summary(confirmed_tasks)}".lower()

        for scenario_id, detector in SPECIAL_SCENARIO_DETECTORS.items():
            keywords = detector.get("keywords", [])
            matched_keywords = []

            # 检查关键词匹配
            for keyword in keywords:
                if keyword in combined_text:
                    matched_keywords.append(keyword)

            # 如果有匹配的关键词，记录该场景
            if matched_keywords:
                detected_scenarios[scenario_id] = {
                    "matched_keywords": matched_keywords[:3],  # 只保留前3个关键词
                    "trigger_message": detector.get("trigger_message", ""),
                }

        return detected_scenarios

    def _build_task_summary(self, tasks: List[Dict[str, Any]]) -> str:
        """构建任务摘要字符串（用于场景检测）"""
        if not tasks:
            return ""
        return " ".join([task.get("title", "") + " " + task.get("description", "") for task in tasks])

    def get_gap_question_template(self, dimension_id: str) -> Dict[str, Any] | None:
        """获取维度对应的Gap问题模板"""
        templates = self.config.get("gap_question_templates", {})
        return templates.get(dimension_id)

    def enhance_dimensions_with_task_mapping(
        self, confirmed_tasks: List[Dict[str, Any]], current_dimensions: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        v7.137: 基于确认的任务列表，增强维度选择

        Args:
            confirmed_tasks: Step1确认的核心任务列表
            current_dimensions: 当前已选择的维度列表

        Returns:
            (增强后的维度列表, 新增维度ID列表)
        """
        if not self._task_mapping_config or not confirmed_tasks:
            return current_dimensions, []

        logger.info(f"[INFO] [v7.137] 任务映射增强: {len(confirmed_tasks)} 个任务")

        task_mappings = self._task_mapping_config.get("task_mappings", {})
        all_dimensions = self.get_all_dimensions()
        current_dim_ids = {dim["id"] for dim in current_dimensions}

        # 收集需要注入的维度（按优先级排序）
        to_inject: List[Tuple[str, int, str]] = []  # (dimension_id, priority, reason)

        # 遍历确认的任务
        for task in confirmed_tasks:
            task_title = task.get("title", "").lower()
            task_desc = task.get("description", "").lower()
            task_text = f"{task_title} {task_desc}"

            # 匹配任务类型
            for task_type_id, task_config in task_mappings.items():
                keywords = task_config.get("keywords", [])
                matched = any(keyword.lower() in task_text for keyword in keywords)

                if matched:
                    logger.info(f"   [OK] 匹配任务类型: {task_config.get('name')} ({task_type_id})")

                    # 提取推荐维度
                    dimensions = task_config.get("dimensions", [])
                    for dim_info in dimensions:
                        dim_id = dim_info["dimension_id"]
                        priority = dim_info.get("priority", 5)
                        reason = dim_info.get("reason", "")

                        if dim_id not in current_dim_ids and dim_id in all_dimensions:
                            to_inject.append((dim_id, priority, reason))
                            logger.debug(f"      → 候选维度: {dim_id} (优先级{priority})")

        if not to_inject:
            logger.info("   [INFO] 未找到需要注入的新维度")
            return current_dimensions, []

        # v7.152: 按维度ID去重，保留最高优先级的记录
        unique_inject: Dict[str, Tuple[str, int, str]] = {}
        for dim_id, priority, reason in to_inject:
            if dim_id not in unique_inject or priority > unique_inject[dim_id][1]:
                unique_inject[dim_id] = (dim_id, priority, reason)

        # 按优先级排序
        to_inject_list = sorted(unique_inject.values(), key=lambda x: x[1], reverse=True)

        # 限制注入数量（最多5个）
        max_inject = self._task_mapping_config.get("matching_config", {}).get("max_injected_dimensions", 5)
        to_inject_list = to_inject_list[:max_inject]

        # 构建新维度配置
        injected_ids = []
        for dim_id, priority, reason in to_inject_list:
            dim_config = all_dimensions[dim_id]
            current_dimensions.append(
                {
                    "id": dim_id,
                    "dimension_id": dim_id,
                    "name": dim_config.get("name", dim_id),
                    "left_label": dim_config.get("left_label", "低"),
                    "right_label": dim_config.get("right_label", "高"),
                    "description": dim_config.get("description", ""),
                    "default_value": dim_config.get("default_value", 50),
                    "category": dim_config.get("category", "other"),
                    "gap_threshold": dim_config.get("gap_threshold", 30),
                    "injected_by_task": True,  # 标记为任务映射注入
                    "injection_reason": reason,
                }
            )
            injected_ids.append(dim_id)
            logger.info(f"   [OK] 注入维度: {dim_id} (优先级{priority}) - {reason}")

        logger.info(f"[OK] [v7.137] 任务映射完成: 注入 {len(injected_ids)} 个新维度")
        return current_dimensions, injected_ids

    def apply_answer_to_dimension_rules(
        self, gap_filling_answers: Dict[str, str], dimensions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        v7.137: 根据问卷答案，智能推理维度默认值

        Args:
            gap_filling_answers: Step2信息补全阶段的答案 {"question": "answer"}
            dimensions: 维度配置列表

        Returns:
            应用答案推理后的维度列表（default_value可能被修改）
        """
        if not self._answer_rules_config or not gap_filling_answers:
            return dimensions

        logger.info(f"[INFO] [v7.137] 答案推理: {len(gap_filling_answers)} 个答案")

        inference_rules = self._answer_rules_config.get("inference_rules", [])
        inference_config = self._answer_rules_config.get("inference_config", {})
        min_confidence = inference_config.get("min_confidence", 0.6)
        adjustment_range = inference_config.get("adjustment_range", 5)

        # 建立维度ID索引
        dim_map = {dim["id"]: dim for dim in dimensions}

        applied_count = 0

        # 遍历推理规则
        for rule in inference_rules:
            rule_id = rule.get("rule_id", "")
            question_keywords = rule.get("question_keywords", [])
            dimension_id = rule.get("dimension_id", "")
            answer_patterns = rule.get("answer_patterns", [])

            if dimension_id not in dim_map:
                continue  # 此维度不在当前选择的维度中

            # 查找匹配的问题答案
            matched_qa = None
            for question, answer in gap_filling_answers.items():
                question_lower = question.lower()
                if any(kw.lower() in question_lower for kw in question_keywords):
                    matched_qa = (question, answer)
                    break

            if not matched_qa:
                continue  # 没有匹配的问题

            question, answer = matched_qa
            answer_lower = answer.lower()

            # 匹配答案模式
            best_match = None
            best_confidence = 0.0

            for pattern_config in answer_patterns:
                pattern_words = pattern_config.get("pattern", [])
                value = pattern_config.get("value", 50)
                confidence = pattern_config.get("confidence", 0.5)
                reason = pattern_config.get("reason", "")

                # 检查答案中是否包含模式关键词
                match_count = sum(1 for word in pattern_words if word.lower() in answer_lower)
                match_ratio = match_count / len(pattern_words) if pattern_words else 0

                if match_ratio > 0.5 and confidence > best_confidence:
                    best_match = {"value": value, "confidence": confidence, "reason": reason}
                    best_confidence = confidence

            # 应用最佳匹配
            if best_match and best_confidence >= min_confidence:
                # 添加随机调整，避免过于机械
                adjusted_value = best_match["value"] + random.randint(-adjustment_range, adjustment_range)
                adjusted_value = max(0, min(100, adjusted_value))  # 限制在0-100

                original_value = dim_map[dimension_id].get("default_value", 50)
                dim_map[dimension_id]["default_value"] = adjusted_value
                dim_map[dimension_id]["inferred_from_answer"] = True  # 标记为答案推理
                dim_map[dimension_id]["inference_reason"] = best_match["reason"]

                applied_count += 1
                logger.info(
                    f"   [OK] {dimension_id}: {original_value} → {adjusted_value} (置信度{best_confidence:.1%}) - {best_match['reason']}"
                )

        logger.info(f"[OK] [v7.137] 答案推理完成: 应用 {applied_count} 条规则")
        return dimensions


class RadarGapAnalyzer:
    """
    雷达图短板分析器

    分析用户填写的雷达图数据，识别：
    1. 极端值维度（需要重点关注）
    2. 平衡值维度（用户态度模糊）
    3. 短板维度（需要追问的Gap）
    """

    def __init__(self, gap_threshold: int = 30):
        """
        Args:
            gap_threshold: Gap判断阈值，偏离中心小于此值视为需要追问
        """
        self.gap_threshold = gap_threshold

    def analyze(self, dimension_values: Dict[str, int], dimension_configs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析雷达图数据

        Args:
            dimension_values: 用户设置的维度值 {"dim_id": value}
            dimension_configs: 维度配置列表

        Returns:
            分析结果：
            {
                "extreme_dimensions": [...],  # 极端值维度（<25 或 >75）
                "balanced_dimensions": [...],  # 平衡值维度（45-55）
                "gap_dimensions": [...],  # 需要追问的短板维度
                "profile_label": "...",  # 风格标签
                "dimension_details": {...}  # 每个维度的详细分析
            }
        """
        extreme_dimensions = []
        balanced_dimensions = []
        gap_dimensions = []
        dimension_details = {}

        # 构建维度配置索引
        config_map = {d["id"]: d for d in dimension_configs}

        for dim_id, value in dimension_values.items():
            config = config_map.get(dim_id, {})
            threshold = config.get("gap_threshold", self.gap_threshold)

            detail = {
                "value": value,
                "name": config.get("name", dim_id),
                "left_label": config.get("left_label", "低"),
                "right_label": config.get("right_label", "高"),
                "tendency": self._get_tendency(value, config),
            }
            dimension_details[dim_id] = detail

            # 分类
            if value <= 25 or value >= 75:
                extreme_dimensions.append(dim_id)
            elif 45 <= value <= 55:
                balanced_dimensions.append(dim_id)

            # 判断是否为Gap（偏离中心距离小于阈值）
            distance_from_center = abs(value - 50)
            if distance_from_center < threshold:
                gap_dimensions.append(dim_id)

        # 生成风格标签
        profile_label = self._generate_profile_label(dimension_values, dimension_details)

        result = {
            "extreme_dimensions": extreme_dimensions,
            "balanced_dimensions": balanced_dimensions,
            "gap_dimensions": gap_dimensions,
            "profile_label": profile_label,
            "dimension_details": dimension_details,
        }

        logger.info(
            f"[INFO] 雷达图分析完成: 极端值={len(extreme_dimensions)}, 平衡值={len(balanced_dimensions)}, Gap={len(gap_dimensions)}"
        )
        logger.info(f"[INFO] 风格标签: {profile_label}")

        return result

    def _get_tendency(self, value: int, config: Dict[str, Any]) -> str:
        """获取维度倾向描述"""
        left_label = config.get("left_label", "低")
        right_label = config.get("right_label", "高")

        if value <= 20:
            return f"强烈倾向{left_label}"
        elif value <= 40:
            return f"偏向{left_label}"
        elif value <= 60:
            return "平衡/中立"
        elif value <= 80:
            return f"偏向{right_label}"
        else:
            return f"强烈倾向{right_label}"

    def _generate_profile_label(self, values: Dict[str, int], details: Dict[str, Dict[str, Any]]) -> str:
        """
        生成风格标签（基于规则，后续可升级为LLM生成）
        """
        labels = []

        # 文化倾向
        cultural = values.get("cultural_axis", 50)
        if cultural <= 30:
            labels.append("东方")
        elif cultural >= 70:
            labels.append("西方")

        # 时间倾向
        temporal = values.get("temporal_axis", 50)
        if temporal <= 30:
            labels.append("古典")
        elif temporal >= 70:
            labels.append("未来")
        else:
            labels.append("当代")

        # 装饰倾向
        decoration = values.get("decoration_density", 50)
        if decoration <= 30:
            labels.append("极简")
        elif decoration >= 70:
            labels.append("华丽")

        # 功能倾向
        function_val = values.get("function_intensity", 50)
        if function_val <= 30:
            labels.append("艺术")
        elif function_val >= 70:
            labels.append("实用")

        # 材料倾向
        material = values.get("material_temperature", 50)
        if material <= 30:
            labels.append("工业")
        elif material >= 70:
            labels.append("自然")

        if not labels:
            return "现代平衡风格"

        return "".join(labels[:3]) + "主义" if len(labels) >= 2 else labels[0] + "风格"


# 便捷函数
def select_dimensions_for_state(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    从State中提取信息并选择维度（便捷封装）

    v7.146: 兼容 v7.139 dict 返回格式（自动解包）
    """
    selector = DimensionSelector()

    # 提取项目类型
    project_type = state.get("project_type") or "personal_residential"

    # 提取用户输入
    user_input = state.get("user_input", "")

    # 提取结构化数据
    agent_results = state.get("agent_results", {})
    requirements_result = agent_results.get("requirements_analyst", {})
    structured_data = requirements_result.get("structured_data", {})

    result = selector.select_for_project(
        project_type=project_type, user_input=user_input, structured_data=structured_data
    )

    #  v7.146: v7.139 起 select_for_project 返回 dict（含 conflicts/adjustment_suggestions）
    # 为保持函数签名兼容性，自动解包为 list
    if isinstance(result, dict):
        logger.debug("[DEBUG] select_dimensions_for_state: 解包 v7.139 dict 返回格式")
        return result.get("dimensions", [])

    # 向后兼容：如果仍然返回 list，直接返回
    return result
