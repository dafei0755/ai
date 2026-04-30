import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from loguru import logger

# =============================================================================
# Detector 输出 ID → Ontology 框架 ID 映射
# 当 detector 输出的类型 ID 在 ontology_frameworks 中没有直接匹配时，
# 通过此表找到最近邻框架。已有直接匹配的类型无需列入。
# =============================================================================
DETECTOR_TO_ONTOLOGY: Dict[str, str] = {
    # 多对一：3 个 detector 类型共享 1 个 ontology 框架
    "rural_construction": "rural_regeneration_urban_renewal",
    "urban_renewal_market": "rural_regeneration_urban_renewal",
    "urban_renewal_heritage": "rural_regeneration_urban_renewal",
    # 近邻归类：detector 类型归入最近邻的 ontology 框架
    "commercial_dining": "commercial_hospitality",
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
}


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
            # 优先直接匹配，否则通过 DETECTOR_TO_ONTOLOGY 映射
            resolved_type = project_type
            type_framework = frameworks.get(project_type, {})
            if not type_framework and project_type in DETECTOR_TO_ONTOLOGY:
                resolved_type = DETECTOR_TO_ONTOLOGY[project_type]
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
        # 如果直接查找未命中，尝试通过 DETECTOR_TO_ONTOLOGY 映射
        if not result and project_type in DETECTOR_TO_ONTOLOGY:
            resolved = DETECTOR_TO_ONTOLOGY[project_type]
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

