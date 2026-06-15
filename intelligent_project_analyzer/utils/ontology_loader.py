import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from loguru import logger

# =============================================================================
# Detector 输出 ID → Ontology 框架 ID 映射
# 当 detector 输出的类型 ID 在 ontology_frameworks 中没有直接匹配时，
# 通过此表找到最近邻框架。已有直接匹配的类型无需列入。
#
# v1.8 改造 (双跑期):
#   事实源已迁移到 config/registries/classification_master_index.yaml
#     ::axis_mappings.project_type_to_framework
#   _resolve_detector_to_ontology() 优先读 master_index, fallback 到本常量
#   本常量保留以防 yaml 缺失 / 解析失败 (零运行时风险)
# =============================================================================
DETECTOR_TO_ONTOLOGY: Dict[str, str] = {
    # 多对一：3 个 detector 类型共享 1 个 ontology 框架
    "rural_construction": "rural_regeneration_urban_renewal",
    "urban_renewal_market": "rural_regeneration_urban_renewal",
    "urban_renewal_heritage": "rural_regeneration_urban_renewal",
    # 近邻归类：detector 类型归入最近邻的 ontology 框架
    "commercial_dining": "commercial_dining",            # 餐饮→独立框架（直接匹配）
    "performing_arts": "public_cultural",
    "community_public": "public_cultural",
    "brand_experience": "commercial_retail",
    "real_estate_showcase": "personal_residential",
    "residential_collective": "hybrid_residential_commercial",
    # special_function 不映射——仅使用 meta_framework 兆底
    # v8.0 新增 8 个类型的近邻归并
    "leisure_entertainment": "commercial_hospitality",      # 休闲娱乐→酒店/民宿框架最近
    "wedding_banquet": "commercial_hospitality",            # 婚庆宴会→宴请属酒店/宴会域
    "children_family": "educational_facility",              # 亲子早教→教育建筑框架
    "residential_renovation": "personal_residential",       # 存量改造→个人住宅框架
    "beauty_personal_care": "commercial_retail",            # 美容美发→商业零售框架
    "automotive_showroom": "commercial_retail",             # 汽车展厅→商业零售/品牌框架
    "digital_media_studio": "commercial_office",            # 直播基地→办公框架
    "popup_temporary": "commercial_retail",                 # 快闪临时→零售/品牌框架
    # special_function: 无明确项目类型时，以 commercial_enterprise 作为通用兜底
    # （meta_framework 已作为 Layer1 全局注入，此映射补充 Layer2 业务视角）
    "special_function": "commercial_enterprise",
}


# =============================================================================
# v1.8 master_index 加载器 (双跑期: 优先 yaml, 失败回退内联常量)
# =============================================================================
_MASTER_INDEX_PATH = (
    Path(__file__).resolve().parent.parent
    / "config" / "registries" / "classification_master_index.yaml"
)

_master_index_cache: Optional[Dict[str, Any]] = None


def _load_master_index() -> Dict[str, Any]:
    """加载 classification_master_index.yaml (带进程级缓存)"""
    global _master_index_cache
    if _master_index_cache is not None:
        return _master_index_cache
    if not _MASTER_INDEX_PATH.exists():
        logger.debug(f"[OntologyLoader] master_index 不存在, 使用内联 DETECTOR_TO_ONTOLOGY")
        _master_index_cache = {}
        return _master_index_cache
    try:
        with open(_MASTER_INDEX_PATH, "r", encoding="utf-8") as f:
            _master_index_cache = yaml.safe_load(f) or {}
        logger.info(f"[OntologyLoader] master_index 已加载: {len(_master_index_cache.get('classification_axes', {}))} 个轴")
    except Exception as exc:
        logger.warning(f"[OntologyLoader] master_index 解析失败, 回退内联常量: {exc}")
        _master_index_cache = {}
    return _master_index_cache


def reload_master_index() -> None:
    """清空 master_index 缓存 (admin / 测试用)"""
    global _master_index_cache
    _master_index_cache = None


def _resolve_detector_to_ontology(detector_type_id: str) -> Optional[str]:
    """
    detector type_id → ontology framework id 的统一解析入口。

    优先级:
      1. master_index.axis_mappings.project_type_to_framework
      2. 内联常量 DETECTOR_TO_ONTOLOGY (fallback)

    Returns:
        ontology framework id, 或 None 表示无映射
    """
    mi = _load_master_index()
    yaml_map = (
        ((mi.get("axis_mappings") or {}).get("project_type_to_framework") or {}).get("mappings")
        or {}
    )
    if detector_type_id in yaml_map:
        return yaml_map[detector_type_id]
    # fallback 到内联常量
    return DETECTOR_TO_ONTOLOGY.get(detector_type_id)


class OntologyLoader:
    """
    分层本体论加载器（v2.0 - 支持三层注入架构）
    
    三层架构：
    1. 基础层（Base Layer）：meta_framework - 所有专家共享的通用维度
    2. 项目类型层（Project Type Layer）：按项目类型的领域框架
    3. 专家强化层（Expert Enhancement Layer）：针对特定专家的额外维度（可选）
    
    使用方式：
        loader = OntologyLoader("path/to/ontology.yaml")
        
        # 传统方式（向后兼容）
        ontology = loader.get_ontology_by_type("personal_residential")
        
        # 分层注入（新方式）
        ontology = loader.get_layered_ontology(
            project_type="personal_residential",
            expert_role="spatial_planner"
        )
    """
    def __init__(self, ontology_path: str):
        self.ontology_path = Path(ontology_path)
        self.ontology_data = self._load_ontology()

    def _load_ontology(self) -> Dict[str, Any]:
        """加载完整的本体论配置文件"""
        if not self.ontology_path.exists():
            raise FileNotFoundError(f"Ontology file not found: {self.ontology_path}")
        with open(self.ontology_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}

    def get_ontology_by_type(self, project_type: str) -> Dict[str, Any]:
        """
        【传统方法 - 向后兼容】
        根据项目类型返回对应本体论片段
        """
        frameworks = self.ontology_data.get('ontology_frameworks', {})
        return frameworks.get(project_type, {})

    def get_meta_framework(self) -> Dict[str, Any]:
        """
        【传统方法 - 向后兼容】
        返回元框架（通用维度）
        """
        frameworks = self.ontology_data.get('ontology_frameworks', {})
        return frameworks.get('meta_framework', {})

    def get_layered_ontology(
        self, 
        project_type: str, 
        expert_role: Optional[str] = None,
        include_base: bool = True
    ) -> Dict[str, Any]:
        """
        【分层注入 - 核心方法】
        按照三层架构加载并合并本体论框架
        
        Args:
            project_type: 项目类型（如 "personal_residential"）
            expert_role: 专家角色标识（如 "spatial_planner"），可选
            include_base: 是否包含基础层（meta_framework），默认True
            
        Returns:
            合并后的本体论字典，包含所有适用的维度
            
        示例：
            # 空间规划师分析个人住宅项目
            ontology = loader.get_layered_ontology(
                project_type="personal_residential",
                expert_role="spatial_planner"
            )
            # 将得到：meta_framework + personal_residential + spatial_planner额外维度
        """
        merged_ontology = {}
        layers_applied = []
        
        frameworks = self.ontology_data.get('ontology_frameworks', {})
        expert_extensions = self.ontology_data.get('expert_extensions', {})
        
        # 第1层：基础层（meta_framework）
        if include_base:
            base_framework = frameworks.get('meta_framework', {})
            if base_framework:
                self._merge_framework(merged_ontology, base_framework)
                layers_applied.append("meta_framework")
                logger.debug(" 注入基础层: meta_framework")
        
        # 第2层：项目类型层——支持 detector ID 自动映射到 ontology 框架
        if project_type and project_type != 'meta_framework':
            # 优先直接匹配，否则通过 _resolve_detector_to_ontology() (master_index 优先) 映射
            resolved_type = project_type
            type_framework = frameworks.get(project_type, {})
            if not type_framework:
                mapped = _resolve_detector_to_ontology(project_type)
                if mapped:
                    resolved_type = mapped
                    type_framework = frameworks.get(resolved_type, {})
                    logger.info(f" Detector映射: {project_type} → {resolved_type}")
            
            if type_framework:
                self._merge_framework(merged_ontology, type_framework)
                layers_applied.append(f"project_type:{resolved_type}")
                logger.debug(f" 注入项目类型层: {resolved_type}")
            else:
                logger.warning(f"️ 项目类型 '{project_type}' 无对应框架，仅使用 meta_framework")
        
        # 第3层：专家强化层（可选）
        if expert_role:
            expert_extension = expert_extensions.get(expert_role, {})
            if expert_extension:
                self._merge_expert_extension(merged_ontology, expert_extension)
                layers_applied.append(f"expert:{expert_role}")
                logger.debug(f" 注入专家强化层: {expert_role}")
            else:
                logger.debug(f"ℹ️ 专家 '{expert_role}' 无额外强化维度")
        
        logger.info(f" 分层注入完成: {' + '.join(layers_applied)}")
        return merged_ontology

    def _merge_framework(self, target: Dict[str, Any], source: Dict[str, Any]):
        """
        合并框架到目标字典（深度合并，保留层级结构）
        
        框架结构示例：
        {
            "category_name": [
                {"name": "...", "description": "...", "ask_yourself": "...", "examples": "..."},
                ...
            ]
        }
        """
        for category, dimensions in source.items():
            if category not in target:
                target[category] = []
            if isinstance(dimensions, list):
                target[category].extend(dimensions)
            else:
                logger.warning(f"️ 框架 '{category}' 格式异常，跳过")

    def _merge_expert_extension(self, target: Dict[str, Any], extension: Dict[str, Any]):
        """
        合并专家强化层到目标字典
        
        扩展结构示例：
        {
            "additional_dimensions": [
                {"name": "...", "description": "...", "ask_yourself": "...", "examples": "..."},
                ...
            ]
        }
        """
        additional_dims = extension.get('additional_dimensions', [])
        if additional_dims:
            # 创建一个专门的"专家强化"分类
            if 'expert_enhancement' not in target:
                target['expert_enhancement'] = []
            target['expert_enhancement'].extend(additional_dims)

    def format_as_prompt(self, ontology: Dict[str, Any], expert_name: str = "专家", project_type: Optional[str] = None) -> str:
        """
        将本体论字典格式化为系统提示文本
        
        Args:
            ontology: 本体论字典（通常由 get_layered_ontology 返回）
            expert_name: 专家角色名称，用于个性化提示语
            project_type: 项目类型标识（可选），用于注入激活图谱指导
            
        Returns:
            格式化的Markdown文本，可直接注入系统提示
        """
        if not ontology:
            return ""
        
        lines = [
            f"##  {expert_name}专属分析维度",
            "",
        ]
        
        # 注入激活图谱指导（如果有）
        if project_type:
            profile = self.get_activation_profile(project_type)
            if profile:
                guidance = profile.get('guidance', '')
                elevated = profile.get('elevated_topics', [])
                typical_depth = profile.get('typical_depth', '')
                tensions = profile.get('key_tensions', [])
                
                lines.append("### 本体论分析重心")
                if elevated:
                    lines.append(f"**重点议题**: {', '.join(elevated)}")
                if typical_depth:
                    lines.append(f"**典型深度**: {typical_depth}")
                lines.append("")
                if guidance:
                    lines.append(guidance)
                    lines.append("")
                if tensions:
                    lines.append("**核心设计张力（必须回应）:**")
                    for t in tensions:
                        lines.append(f"- {t}")
                    lines.append("")
                lines.append("---")
                lines.append("")
        
        lines.extend([
            "以下维度框架将指导你的深度分析。每个维度包含：",
            "- **核心问题**：你需要回答的关键问题",
            "- **参考示例**：常见的情况类型",
            "",
            "---",
            ""
        ])
        
        for category, dimensions in ontology.items():
            # 分类标题
            category_display = category.replace('_', ' ').title()
            lines.append(f"###  {category_display}")
            lines.append("")
            
            if not isinstance(dimensions, list):
                continue
            
            for dim in dimensions:
                name = dim.get('name', '未命名维度')
                desc = dim.get('description', '')
                question = dim.get('ask_yourself', '')
                examples = dim.get('examples', '')
                issue_id = dim.get('issue_id', '')
                
                header = f"#### {name}"
                if issue_id:
                    header = f"#### [{issue_id}] {name}"
                lines.append(header)
                if desc:
                    lines.append(f"{desc}")
                    lines.append("")
                if question:
                    lines.append(f"** 核心问题**: {question}")
                    lines.append("")
                if examples:
                    lines.append(f"** 参考示例**: {examples}")
                    lines.append("")
                lines.append("---")
                lines.append("")
        
        return "\n".join(lines)

    def get_available_expert_roles(self) -> List[str]:
        """
        获取所有可用的专家角色列表（有额外强化维度的专家）
        
        Returns:
            专家角色ID列表
        """
        expert_extensions = self.ontology_data.get('expert_extensions', {})
        return list(expert_extensions.keys())

    def get_available_project_types(self) -> List[str]:
        """
        获取所有可用的项目类型列表
        
        Returns:
            项目类型ID列表（不包含meta_framework）
        """
        frameworks = self.ontology_data.get('ontology_frameworks', {})
        return [k for k in frameworks.keys() if k != 'meta_framework']

    def get_cognitive_scaffolding(self) -> Dict[str, Any]:
        """
        获取认知脚手架框架（L0-L4层级定义）
        
        Returns:
            认知层级字典，包含 description 和 levels
        """
        return self.ontology_data.get('cognitive_scaffolding', {})

    def get_activation_profile(self, project_type: str) -> Dict[str, Any]:
        """
        获取特定业态的激活图谱（支持 detector ID 自动映射）
        
        Args:
            project_type: 项目类型标识（如 "personal_residential" 或 detector 输出的 ID）
            
        Returns:
            激活图谱字典，包含 elevated_topics, typical_depth, guidance, key_tensions
        """
        profiles = self.ontology_data.get('activation_profiles', {})
        result = profiles.get(project_type, {})
        # 如果直接查找未命中，通过 _resolve_detector_to_ontology() (master_index 优先) 映射
        if not result:
            resolved = _resolve_detector_to_ontology(project_type)
            if resolved:
                result = profiles.get(resolved, {})
        return result

    def get_available_activation_profiles(self) -> List[str]:
        """
        获取所有已定义激活图谱的项目类型列表

        Returns:
            项目类型ID列表
        """
        profiles = self.ontology_data.get('activation_profiles', {})
        return [k for k in profiles.keys() if k != 'description']

    # =========================================================================
    # v1.8 Layer 4: activation_pack injector
    # (本体激活的第 4 层, 在 meta_framework / project_type / expert 之上)
    # =========================================================================
    def inject_activation_pack(
        self,
        merged_ontology: Dict[str, Any],
        subdomain_id: Optional[str] = None,
        spatial_layer_ids: Optional[List[str]] = None,
        active_ontology_dimension_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Layer 4: 按 subdomain / spatial_layer / dimension_ids 增量注入激活包内容。

        本方法是 v1.8 §11.3 Layer 4 的实现:
          1. 按 subdomain_id 加载对象 / 属性 / 关系 / 约束 (activation pack yaml)
          2. 按 spatial_layer_ids 过滤空间层对象
          3. 按 active_ontology_dimension_ids 关联 E 维度

        设计原则:
          - 不破坏已合并的 ontology dict (1-3 层结果)
          - 激活包 yaml 缺失时静默跳过, 不抛异常
          - 输出额外字段挂在 merged_ontology 顶层的 _activation_pack key 下,
            既能被 format_as_prompt 间接消费, 也方便下游单独读取

        Args:
            merged_ontology: get_layered_ontology() 的返回值 (1-3 层结果)
            subdomain_id: 子域 ID (如 tea_drink_store)
            spatial_layer_ids: 空间层 ID 数组 (如 [interior_layer])
            active_ontology_dimension_ids: 激活的 E 维度 (如 [E2_body_movement])

        Returns:
            扩展后的 ontology dict (含 _activation_pack 字段)
        """
        if not subdomain_id and not spatial_layer_ids and not active_ontology_dimension_ids:
            return merged_ontology  # 无任何 Layer 4 输入, 直接返回

        pack_info: Dict[str, Any] = {
            "subdomain_id": subdomain_id,
            "spatial_layer_ids": spatial_layer_ids or [],
            "active_ontology_dimension_ids": active_ontology_dimension_ids or [],
        }

        # 1. 按 subdomain_id 加载激活包 yaml
        if subdomain_id:
            pack_yaml = self._load_activation_pack_yaml(subdomain_id)
            if pack_yaml:
                pack_info["activation_pack"] = pack_yaml
                logger.info(f"[Layer4] 加载激活包: {subdomain_id}")
            else:
                pack_info["activation_pack"] = None
                logger.debug(f"[Layer4] 激活包未找到或未建立: {subdomain_id}")

        # 2. 按 spatial_layer_ids 关联本体维度 (从 master_index.spatial_layer_to_dimensions)
        if spatial_layer_ids:
            mi = _load_master_index()
            sl_map = (
                ((mi.get("axis_mappings") or {})
                 .get("spatial_layer_to_dimensions") or {})
                .get("mappings") or {}
            )
            inferred_dims: List[str] = []
            priority_dims: List[str] = []
            for layer_id in spatial_layer_ids:
                layer_info = sl_map.get(layer_id, {})
                inferred_dims.extend(layer_info.get("active_dimensions", []))
                priority_dims.extend(layer_info.get("priority_dimensions", []))
            pack_info["inferred_dimensions_from_layers"] = list(dict.fromkeys(inferred_dims))
            pack_info["priority_dimensions_from_layers"] = list(dict.fromkeys(priority_dims))

        # 3. 解析 E 维度 (从 ontology_dimension_registry.yaml)
        if active_ontology_dimension_ids:
            resolved_dims = self._resolve_ontology_dimensions(active_ontology_dimension_ids)
            pack_info["resolved_dimensions"] = resolved_dims

        merged_ontology["_activation_pack"] = pack_info
        return merged_ontology

    def _load_activation_pack_yaml(self, subdomain_id: str) -> Optional[Dict[str, Any]]:
        """加载 activation_packs/<subdomain_id>_pack.yaml (容错)"""
        # 激活包按 v1.8 约定存放路径
        candidates = [
            self.ontology_path.parent / "activation_packs" / f"{subdomain_id}_pack.yaml",
            self.ontology_path.parent / "activation_packs" / f"{subdomain_id}.yaml",
        ]
        for path in candidates:
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        return yaml.safe_load(f) or {}
                except Exception as exc:
                    logger.warning(f"[Layer4] 激活包加载失败 {path}: {exc}")
                    return None
        return None

    def _resolve_ontology_dimensions(self, dimension_ids: List[str]) -> Dict[str, Any]:
        """
        从 ontology_dimension_registry.yaml 解析 E 维度完整定义。
        若 registry 不存在, 回退到 ontology.yaml::meta_framework.ontological_foundations。
        """
        # 优先 registry
        reg_path = self.ontology_path.parent / "ontology_dimension_registry.yaml"
        if reg_path.exists():
            try:
                with open(reg_path, "r", encoding="utf-8") as f:
                    reg = yaml.safe_load(f) or {}
                all_dims = reg.get("ontology_dimensions", {})
                return {did: all_dims[did] for did in dimension_ids if did in all_dims}
            except Exception as exc:
                logger.warning(f"[Layer4] dimension_registry 加载失败: {exc}")

        # fallback: ontology.yaml 内嵌
        meta = self.ontology_data.get("ontology_frameworks", {}).get("meta_framework", {})
        legacy = meta.get("ontological_foundations", [])
        result: Dict[str, Any] = {}
        for dim_entry in legacy:
            issue_id = dim_entry.get("issue_id", "")
            # 旧 issue_id 是 E1/E2 形式; 需匹配新 id (E1_xxx) 前缀
            for did in dimension_ids:
                if did.startswith(issue_id + "_") or did == issue_id:
                    result[did] = dim_entry
                    break
        return result

    def get_layered_ontology_v18(
        self,
        project_type: Optional[str] = None,
        subdomain_id: Optional[str] = None,
        spatial_layer_ids: Optional[List[str]] = None,
        active_ontology_dimension_ids: Optional[List[str]] = None,
        expert_role: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        v1.8 一站式入口: 1-3 层 + Layer 4 一次完成。

        Args:
            project_type: 项目类型 ID (Layer 2)
            subdomain_id: 子域 ID (Layer 4)
            spatial_layer_ids: 空间层 (Layer 4)
            active_ontology_dimension_ids: 激活维度 (Layer 4)
            expert_role: 专家角色 (Layer 3)

        Returns:
            完整 ontology dict, 含 _activation_pack 字段
        """
        # 1-3 层走旧方法 (向后兼容, 零回归风险)
        merged = self.get_layered_ontology(
            project_type=project_type or "meta_framework",
            expert_role=expert_role,
            include_base=True,
        )
        # Layer 4 增量注入
        return self.inject_activation_pack(
            merged,
            subdomain_id=subdomain_id,
            spatial_layer_ids=spatial_layer_ids,
            active_ontology_dimension_ids=active_ontology_dimension_ids,
        )

