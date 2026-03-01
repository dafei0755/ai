"""
视觉配置加载器 (Visual Config Loader)
v7.153 - 配置驱动的角色差异化视觉生成

从 role_visual_identity.yaml 加载角色视觉身份配置，
替代 image_generator.py 中的硬编码常量。
"""

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

import yaml
from loguru import logger

# 配置文件路径
CONFIG_DIR = Path(__file__).parent.parent / "config"
VISUAL_IDENTITY_FILE = CONFIG_DIR / "role_visual_identity.yaml"


@lru_cache(maxsize=1)
def _load_visual_identity_config() -> Dict[str, Any]:
    """
    加载视觉身份配置文件（带缓存）

    Returns:
        配置字典，失败时返回空字典
    """
    try:
        if not VISUAL_IDENTITY_FILE.exists():
            logger.warning(f"️ 视觉配置文件不存在: {VISUAL_IDENTITY_FILE}")
            return {}

        with open(VISUAL_IDENTITY_FILE, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        logger.info(f" 视觉配置加载成功: {len(config.get('roles', {}))} 个角色")
        return config or {}

    except Exception as e:
        logger.error(f" 加载视觉配置失败: {e}")
        return {}


def get_role_visual_identity(role_id: str) -> Dict[str, Any]:
    """
    获取指定角色的视觉身份配置

    Args:
        role_id: 角色ID，如 "V2", "V3", "2-1"（会自动转换）

    Returns:
        角色视觉配置字典，包含:
        - name: 角色名称
        - perspective: 专业视角
        - visual_type: 视觉类型
        - extraction_focus: 提取焦点列表
        - style_preferences: 风格偏好列表
        - avoid_patterns: 避免模式列表
        - required_keywords: 必保留关键词
    """
    config = _load_visual_identity_config()
    roles = config.get("roles", {})

    # 标准化角色ID: "2-1" -> "V2", "3-2" -> "V3"
    normalized_id = role_id
    if "-" in role_id:
        # 从 "2-1" 提取第一个数字 "2" -> "V2"
        first_digit = role_id.split("-")[0]
        normalized_id = f"V{first_digit}"
    elif not role_id.startswith("V"):
        normalized_id = f"V{role_id}"

    role_config = roles.get(normalized_id.upper(), {})

    if not role_config:
        logger.warning(f"️ 未找到角色配置: {role_id} (标准化为: {normalized_id})，使用默认V2配置")
        role_config = roles.get("V2", _get_default_role_config())

    return role_config


def get_role_visual_type_for_project(role_id: str, project_type: str) -> str:
    """
     v7.154: 根据项目类型获取角色的视觉类型

    对于V4设计研究员，设计类项目应生成案例对比图而非数据信息图

    Args:
        role_id: 角色ID，如 "V4", "4-1"
        project_type: 项目类型，如 "interior_design", "hybrid_residential_commercial"

    Returns:
        视觉类型字符串，如 "case_comparison", "data_infographic"
    """
    role_config = get_role_visual_identity(role_id)

    # 检查是否有项目类型感知的视觉类型配置
    visual_type_by_project = role_config.get("visual_type_by_project", {})

    if visual_type_by_project and project_type:
        # 尝试精确匹配项目类型
        if project_type in visual_type_by_project:
            selected_type = visual_type_by_project[project_type]
            logger.info(f" [v7.154] 角色 {role_id} 根据项目类型 '{project_type}' 选择视觉类型: {selected_type}")
            return selected_type

        # 尝试模糊匹配（设计类项目）
        design_keywords = ["design", "interior", "architectural", "residential", "commercial"]
        if any(kw in project_type.lower() for kw in design_keywords):
            if "design_project" in visual_type_by_project:
                selected_type = visual_type_by_project["design_project"]
                logger.info(f" [v7.154] 角色 {role_id} 检测到设计类项目，选择视觉类型: {selected_type}")
                return selected_type

        # 使用默认值
        if "default" in visual_type_by_project:
            return visual_type_by_project["default"]

    # 回退到角色默认视觉类型
    return role_config.get("visual_type", "photorealistic_rendering")


def get_visual_type_config(visual_type: str) -> Dict[str, Any]:
    """
    获取视觉类型的详细配置

    Args:
        visual_type: 视觉类型，如 "photorealistic_rendering"

    Returns:
        视觉类型配置字典，包含:
        - description: 中文描述
        - description_en: 英文描述
        - keywords_en: 英文关键词列表
        - keywords_cn: 中文关键词列表
        - negative_prompt: 负面提示词
        - quality_suffix: 质量后缀
    """
    config = _load_visual_identity_config()
    visual_types = config.get("visual_types", {})

    type_config = visual_types.get(visual_type, {})

    if not type_config:
        logger.warning(f"️ 未找到视觉类型配置: {visual_type}，使用默认配置")
        type_config = visual_types.get("photorealistic_rendering", _get_default_visual_type_config())

    return type_config


def get_deliverable_format_hint(deliverable_format: str) -> Dict[str, Any]:
    """
    获取交付物格式的视觉提示

    Args:
        deliverable_format: 交付物格式，如 "visualization", "narrative"

    Returns:
        格式提示字典，包含:
        - hint: 中文提示
        - hint_en: 英文提示
        - preferred_visual_type: 推荐的视觉类型
    """
    config = _load_visual_identity_config()
    format_hints = config.get("deliverable_format_hints", {})

    hint_config = format_hints.get(deliverable_format, {})

    if not hint_config:
        hint_config = format_hints.get(
            "analysis",
            {
                "hint": " 生成专业分析可视化",
                "hint_en": "professional analysis visualization",
                "preferred_visual_type": "photorealistic_rendering",
            },
        )

    return hint_config


def get_global_config() -> Dict[str, Any]:
    """
    获取全局配置

    Returns:
        全局配置字典
    """
    config = _load_visual_identity_config()
    return config.get(
        "global_config",
        {
            "visual_brief_max_length": 800,
            "final_prompt_min_length": 80,
            "style_anchor_max_words": 8,
            "fallback_style_preferences": ["professional design visualization"],
            "universal_negative_prompt": "low quality, blurry, watermark",
        },
    )


def get_all_role_ids() -> List[str]:
    """
    获取所有已配置的角色ID列表

    Returns:
        角色ID列表，如 ["V2", "V3", "V4", "V5", "V6", "V7"]
    """
    config = _load_visual_identity_config()
    return list(config.get("roles", {}).keys())


def clear_config_cache():
    """
    清除配置缓存（用于热更新）
    """
    _load_visual_identity_config.cache_clear()
    logger.info(" 视觉配置缓存已清除")


def _get_default_role_config() -> Dict[str, Any]:
    """默认角色配置（当配置文件不可用时）"""
    return {
        "name": "默认角色",
        "perspective": "综合设计协调者",
        "visual_type": "photorealistic_rendering",
        "unique_angle": "整体设计协调",
        "extraction_focus": ["空间整体效果", "材质与色彩", "光影氛围"],
        "style_preferences": ["professional design visualization", "high quality rendering"],
        "avoid_patterns": ["低质量渲染", "卡通风格"],
        "required_keywords": ["design", "space"],
    }


def _get_default_visual_type_config() -> Dict[str, Any]:
    """默认视觉类型配置"""
    return {
        "description": "专业设计可视化",
        "description_en": "Professional design visualization",
        "keywords_en": ["professional", "design", "visualization"],
        "keywords_cn": ["专业设计", "可视化"],
        "negative_prompt": "low quality, blurry",
        "quality_suffix": "high quality, professional",
    }


# ============================================================================
# 便捷函数：构建完整的角色视觉上下文
# ============================================================================


def build_role_visual_context(role_id: str, deliverable_format: str = "analysis") -> Dict[str, Any]:
    """
    构建角色的完整视觉上下文（合并角色配置+视觉类型配置+格式提示）

    Args:
        role_id: 角色ID
        deliverable_format: 交付物格式

    Returns:
        完整的视觉上下文字典
    """
    role_config = get_role_visual_identity(role_id)
    visual_type = role_config.get("visual_type", "photorealistic_rendering")
    visual_type_config = get_visual_type_config(visual_type)
    format_hint = get_deliverable_format_hint(deliverable_format)
    global_config = get_global_config()

    return {"role": role_config, "visual_type": visual_type_config, "format_hint": format_hint, "global": global_config}
