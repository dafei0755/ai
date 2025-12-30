"""
维度选择器 - 根据项目类型动态选择雷达图维度

v7.80: 三步递进式问卷系统核心服务
v7.80.15 (P0.3): 集成特殊场景检测器，自动注入专用维度
"""

import os
from typing import Dict, Any, List, Optional, Set
from pathlib import Path
from loguru import logger

import yaml


# 🆕 v7.80.15 (P0.3): 场景 → 专用维度映射
SCENARIO_DIMENSION_MAPPING = {
    "extreme_environment": ["environmental_adaptation"],
    "medical_special_needs": ["accessibility_level"],
    "cultural_depth": ["cultural_authenticity"],
    "tech_geek": ["acoustic_performance", "automation_workflow"],
    "complex_relationships": ["conflict_mediation"],
    "poetic_philosophical": ["spiritual_atmosphere"],
    "extreme_budget": ["cost_efficiency"],
    "innovative_business": ["automation_workflow"]
}


class DimensionSelector:
    """
    维度选择器

    根据项目类型和用户输入的关键词，从维度库中选择9-12个最相关的维度。
    """

    _instance = None
    _dimensions_config: Optional[Dict[str, Any]] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if DimensionSelector._dimensions_config is None:
            self._load_config()

    def _load_config(self) -> None:
        """加载维度配置文件"""
        config_path = Path(__file__).parent.parent / "config" / "prompts" / "radar_dimensions.yaml"

        if not config_path.exists():
            logger.error(f"❌ 维度配置文件不存在: {config_path}")
            DimensionSelector._dimensions_config = {}
            return

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                DimensionSelector._dimensions_config = yaml.safe_load(f)
            logger.info(f"✅ 维度配置加载成功: {len(self._dimensions_config.get('dimensions', {}))} 个维度")
        except Exception as e:
            logger.error(f"❌ 维度配置加载失败: {e}")
            DimensionSelector._dimensions_config = {}

    @property
    def config(self) -> Dict[str, Any]:
        """获取配置"""
        return DimensionSelector._dimensions_config or {}

    def get_all_dimensions(self) -> Dict[str, Dict[str, Any]]:
        """获取所有维度定义"""
        return self.config.get("dimensions", {})

    def get_dimension_by_id(self, dimension_id: str) -> Optional[Dict[str, Any]]:
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
        structured_data: Optional[Dict[str, Any]] = None,
        min_dimensions: int = 9,
        max_dimensions: int = 12
    ) -> List[Dict[str, Any]]:
        """
        为项目选择合适的维度

        算法：
        1. 从项目类型映射中获取 required 和 recommended 维度
        2. 根据用户输入的关键词匹配额外的 optional 维度
        3. 确保维度数量在 9-12 个之间

        Args:
            project_type: 项目类型（如 "personal_residential", "commercial_enterprise"）
            user_input: 用户原始输入（用于关键词匹配）
            structured_data: 结构化数据（可选）
            min_dimensions: 最小维度数量
            max_dimensions: 最大维度数量

        Returns:
            维度配置列表
        """
        logger.info(f"🎯 开始为项目选择维度: project_type={project_type}")

        all_dimensions = self.get_all_dimensions()
        if not all_dimensions:
            logger.warning("⚠️ 维度库为空，使用默认维度")
            return self._get_default_dimensions(max_dimensions)

        # 获取项目类型映射
        type_mapping = self.get_project_type_mapping(project_type)
        required = type_mapping.get("required", [])
        recommended = type_mapping.get("recommended", [])
        optional = type_mapping.get("optional", [])

        logger.info(f"📊 项目类型 '{project_type}' 映射: required={len(required)}, recommended={len(recommended)}, optional={len(optional)}")

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

        # Step 3: 如果数量不够，根据关键词匹配 optional 维度
        if len(selected_ids) < min_dimensions and user_input:
            keyword_matches = self._match_dimensions_by_keywords(user_input, optional, all_dimensions)
            for dim_id in keyword_matches:
                if len(selected_ids) >= max_dimensions:
                    break
                if dim_id not in selected_ids:
                    selected_ids.add(dim_id)
                    logger.info(f"🔍 关键词匹配添加维度: {dim_id}")

        # Step 4: 如果仍然不够，从默认维度补充
        if len(selected_ids) < min_dimensions:
            default_dims = self.config.get("default_dimensions", [])
            for dim_id in default_dims:
                if len(selected_ids) >= min_dimensions:
                    break
                if dim_id in all_dimensions and dim_id not in selected_ids:
                    selected_ids.add(dim_id)

        # 构建最终的维度配置列表
        result = []
        for dim_id in selected_ids:
            dim_config = all_dimensions.get(dim_id)
            if dim_config:
                result.append({
                    "id": dim_id,  # 使用 dimension_id 作为 id（与 YAML 键一致）
                    "dimension_id": dim_id,  # 冗余字段，兼容前端
                    "name": dim_config.get("name", dim_id),
                    "left_label": dim_config.get("left_label", "低"),
                    "right_label": dim_config.get("right_label", "高"),
                    "description": dim_config.get("description", ""),
                    "default_value": dim_config.get("default_value", 50),
                    "category": dim_config.get("category", "other"),
                    "gap_threshold": dim_config.get("gap_threshold", 30)
                })

        # 按类别排序（美学 → 功能 → 科技 → 资源 → 体验）
        category_order = ["aesthetic", "functional", "technology", "resource", "experience", "other"]
        result.sort(key=lambda x: (category_order.index(x["category"]) if x["category"] in category_order else 99))

        logger.info(f"✅ 维度选择完成: {len(result)} 个维度")
        for dim in result:
            logger.debug(f"   - {dim['id']}: {dim['name']} ({dim['category']})")

        return result

    def _match_dimensions_by_keywords(
        self,
        user_input: str,
        dimension_ids: List[str],
        all_dimensions: Dict[str, Dict[str, Any]]
    ) -> List[str]:
        """
        根据用户输入的关键词匹配维度

        Returns:
            匹配度排序后的维度ID列表
        """
        user_input_lower = user_input.lower()
        scores: Dict[str, int] = {}

        for dim_id in dimension_ids:
            dim_config = all_dimensions.get(dim_id, {})
            keywords = dim_config.get("keywords", [])

            score = 0
            for keyword in keywords:
                if keyword.lower() in user_input_lower:
                    score += 1

            if score > 0:
                scores[dim_id] = score

        # 按匹配度降序排序
        sorted_dims = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        return sorted_dims

    def _get_default_dimensions(self, count: int = 12) -> List[Dict[str, Any]]:
        """获取默认维度（当配置加载失败时使用）"""
        default_dims = [
            {"id": "cultural_axis", "name": "文化归属轴", "left_label": "东方", "right_label": "西方", "default_value": 50, "category": "aesthetic"},
            {"id": "temporal_axis", "name": "时序定位轴", "left_label": "古典", "right_label": "未来", "default_value": 50, "category": "aesthetic"},
            {"id": "function_intensity", "name": "功能强度轴", "left_label": "形式体验", "right_label": "极致实用", "default_value": 50, "category": "functional"},
            {"id": "decoration_density", "name": "装饰密度轴", "left_label": "极简", "right_label": "繁复", "default_value": 30, "category": "aesthetic"},
            {"id": "material_temperature", "name": "材料温度轴", "left_label": "冰冷工业", "right_label": "温暖自然", "default_value": 60, "category": "aesthetic"},
            {"id": "tech_visibility", "name": "科技渗透轴", "left_label": "隐藏科技", "right_label": "显性科技", "default_value": 40, "category": "technology"},
            {"id": "space_flexibility", "name": "空间灵活度轴", "left_label": "固定功能", "right_label": "多功能可变", "default_value": 50, "category": "functional"},
            {"id": "privacy_level", "name": "私密度轴", "left_label": "开放通透", "right_label": "私密隔离", "default_value": 50, "category": "functional"},
            {"id": "energy_level", "name": "能量层级轴", "left_label": "静谧放松", "right_label": "活力动感", "default_value": 40, "category": "experience"},
            {"id": "social_vs_private", "name": "社交属性轴", "left_label": "独处空间", "right_label": "社交中心", "default_value": 50, "category": "experience"},
            {"id": "budget_priority", "name": "预算优先度轴", "left_label": "严格控预算", "right_label": "品质优先", "default_value": 50, "category": "resource"},
            {"id": "natural_connection", "name": "自然连接轴", "left_label": "人工环境", "right_label": "自然融合", "default_value": 50, "category": "experience"},
        ]
        return default_dims[:count]

    def detect_and_inject_specialized_dimensions(
        self,
        user_input: str,
        confirmed_tasks: List[Dict[str, Any]],
        current_dimensions: List[Dict[str, Any]],
        special_scene_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        🆕 v7.80.15 (P0.3): 检测特殊场景并注入专用维度

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
            logger.info("ℹ️ 未检测到特殊场景，保持当前维度")
            return current_dimensions

        logger.info(f"🎯 [特殊场景] 检测到 {len(detected_scenes)} 个场景: {list(detected_scenes.keys())}")

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
                    to_inject.append({
                        "id": dim_config.get("id", dim_id),
                        "name": dim_config.get("name", dim_id),
                        "left_label": dim_config.get("left_label", "低"),
                        "right_label": dim_config.get("right_label", "高"),
                        "description": dim_config.get("description", ""),
                        "default_value": dim_config.get("default_value", 50),
                        "category": dim_config.get("category", "other"),
                        "gap_threshold": dim_config.get("gap_threshold", 30),
                        "generated": True,  # 🆕 标记为场景自动生成
                        "triggered_by_scene": scene_id  # 🆕 记录触发场景
                    })
                    logger.info(f"   ✅ 注入专用维度: {dim_id} (场景: {scene_id})")

        # 合并维度（限制最多15个）
        result = current_dimensions + to_inject
        if len(result) > 15:
            logger.warning(f"⚠️ 维度总数超过15个 ({len(result)})，保留前15个")
            result = result[:15]

        logger.info(f"✅ [特殊场景] 注入完成: {len(current_dimensions)} → {len(result)} 个维度")
        return result

    def _detect_special_scenarios(
        self,
        user_input: str,
        confirmed_tasks: List[Dict[str, Any]],
        special_scene_metadata: Optional[Dict[str, Any]] = None
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
            logger.info(f"📋 使用 Step 1 传入的场景标签: {special_scene_metadata['scene_tags']}")
            detected = {}
            for scene_tag in special_scene_metadata["scene_tags"]:
                detected[scene_tag] = {
                    "matched_keywords": special_scene_metadata.get("matched_keywords", {}).get(scene_tag, []),
                    "trigger_message": f"Step 1 识别的场景: {scene_tag}"
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
                    "trigger_message": detector.get("trigger_message", "")
                }

        return detected_scenarios

    def _build_task_summary(self, tasks: List[Dict[str, Any]]) -> str:
        """构建任务摘要字符串（用于场景检测）"""
        if not tasks:
            return ""
        return " ".join([task.get("title", "") + " " + task.get("description", "") for task in tasks])

    def get_gap_question_template(self, dimension_id: str) -> Optional[Dict[str, Any]]:
        """获取维度对应的Gap问题模板"""
        templates = self.config.get("gap_question_templates", {})
        return templates.get(dimension_id)


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

    def analyze(
        self,
        dimension_values: Dict[str, int],
        dimension_configs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
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
                "tendency": self._get_tendency(value, config)
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
            "dimension_details": dimension_details
        }

        logger.info(f"📊 雷达图分析完成: 极端值={len(extreme_dimensions)}, 平衡值={len(balanced_dimensions)}, Gap={len(gap_dimensions)}")
        logger.info(f"🏷️ 风格标签: {profile_label}")

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

    def _generate_profile_label(
        self,
        values: Dict[str, int],
        details: Dict[str, Dict[str, Any]]
    ) -> str:
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

    return selector.select_for_project(
        project_type=project_type,
        user_input=user_input,
        structured_data=structured_data
    )
