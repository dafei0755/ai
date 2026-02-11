"""
分析模式配置管理器
提供统一的接口获取和验证不同分析模式的配置

版本历史：
- v7.110: 初始版本，支持从 config/analysis_mode.yaml 读取配置
"""

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger(__name__)


class AnalysisModeConfigError(Exception):
    """分析模式配置相关错误"""

    pass


@lru_cache(maxsize=1)
def load_mode_config() -> Dict[str, Any]:
    """
    加载分析模式配置文件（带缓存）

    Returns:
        Dict[str, Any]: 完整的配置字典

    Raises:
        AnalysisModeConfigError: 配置文件不存在或格式错误
    """
    # 查找配置文件路径
    config_paths = [
        Path(__file__).parent.parent.parent / "config" / "analysis_mode.yaml",  # 标准路径
        Path("config/analysis_mode.yaml"),  # 相对路径
    ]

    config_path = None
    for path in config_paths:
        if path.exists():
            config_path = path
            break

    if not config_path:
        raise AnalysisModeConfigError(f"未找到分析模式配置文件 analysis_mode.yaml，已搜索路径: {config_paths}")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # 验证配置结构
        if not isinstance(config, dict) or "modes" not in config:
            raise AnalysisModeConfigError(f"配置文件格式错误: 必须包含 'modes' 字段")

        logger.info(f" 成功加载分析模式配置: {config_path}")
        return config

    except yaml.YAMLError as e:
        raise AnalysisModeConfigError(f"配置文件解析失败: {e}")
    except Exception as e:
        raise AnalysisModeConfigError(f"加载配置文件时发生错误: {e}")


def get_concept_image_config(analysis_mode: str, fallback_to_default: bool = True) -> Dict[str, Any]:
    """
    获取指定分析模式的概念图配置

    Args:
        analysis_mode: 分析模式 ("normal" 或 "deep_thinking")
        fallback_to_default: 当模式不存在时是否降级到默认模式

    Returns:
        Dict[str, Any]: 概念图配置字典
        {
            "count": int,        # 默认生成数量
            "editable": bool,    # 是否可编辑
            "max_count": int,    # 最大数量
            "min_count": int     # 最小数量
        }

    Raises:
        AnalysisModeConfigError: 模式不存在且 fallback_to_default=False 时

    Example:
        >>> config = get_concept_image_config("deep_thinking")
        >>> config["count"]
        3
        >>> config["editable"]
        True
    """
    try:
        full_config = load_mode_config()
        modes = full_config.get("modes", {})

        # 检查模式是否存在
        if analysis_mode not in modes:
            if fallback_to_default:
                default_mode = full_config.get("default_mode", "normal")
                logger.warning(f"️ 未知分析模式 '{analysis_mode}'，降级为默认模式 '{default_mode}'")
                analysis_mode = default_mode
            else:
                available_modes = list(modes.keys())
                raise AnalysisModeConfigError(f"不支持的分析模式: {analysis_mode}。可用模式: {available_modes}")

        # 提取概念图配置
        mode_config = modes[analysis_mode]
        concept_config = mode_config.get("concept_image", {})

        # 验证必需字段
        required_fields = ["count", "editable", "max_count"]
        for field in required_fields:
            if field not in concept_config:
                raise AnalysisModeConfigError(f"模式 '{analysis_mode}' 的配置缺少必需字段: {field}")

        # 添加模式名称和描述（可选）
        result = concept_config.copy()
        result["mode_name"] = mode_config.get("name", analysis_mode)
        result["mode_description"] = mode_config.get("description", "")

        logger.debug(
            f" [模式配置] {analysis_mode} → 概念图: "
            f"count={result['count']}, editable={result['editable']}, "
            f"max={result['max_count']}"
        )

        return result

    except AnalysisModeConfigError:
        raise
    except Exception as e:
        logger.error(f" 获取概念图配置时发生错误: {e}")
        # 返回安全的默认值
        return {
            "count": 1,
            "editable": False,
            "max_count": 1,
            "min_count": 1,
            "mode_name": "fallback",
            "mode_description": "错误降级模式",
        }


def validate_concept_image_count(count: int, analysis_mode: str) -> int:
    """
    验证并修正概念图数量是否在允许范围内

    Args:
        count: 用户请求的概念图数量
        analysis_mode: 分析模式

    Returns:
        int: 验证后的数量（可能已修正）

    Example:
        >>> validate_concept_image_count(15, "deep_thinking")
        10  # 自动限制为 max_count
    """
    config = get_concept_image_config(analysis_mode)

    min_count = config.get("min_count", 1)
    max_count = config.get("max_count", 10)

    if count < min_count:
        logger.warning(f"️ 概念图数量 {count} 小于最小值 {min_count}，已调整为 {min_count}")
        return min_count

    if count > max_count:
        logger.warning(f"️ 概念图数量 {count} 超过最大值 {max_count}，已调整为 {max_count}")
        return max_count

    return count


def get_all_modes() -> Dict[str, Dict[str, Any]]:
    """
    获取所有可用的分析模式及其配置

    Returns:
        Dict[str, Dict[str, Any]]: 模式名称到配置的映射

    Example:
        >>> modes = get_all_modes()
        >>> list(modes.keys())
        ['normal', 'deep_thinking']
    """
    try:
        full_config = load_mode_config()
        return full_config.get("modes", {})
    except Exception as e:
        logger.error(f" 获取所有模式时发生错误: {e}")
        return {}


def is_mode_editable(analysis_mode: str) -> bool:
    """
    检查指定模式的概念图数量是否可编辑

    Args:
        analysis_mode: 分析模式

    Returns:
        bool: True 表示可编辑，False 表示固定数量
    """
    config = get_concept_image_config(analysis_mode)
    return config.get("editable", False)


def get_file_upload_config(analysis_mode: str, fallback_to_default: bool = True) -> Dict[str, Any]:
    """
    获取指定分析模式的文件上传配置

     v7.350: 新增函数，支持按模式限制文件上传功能

    Args:
        analysis_mode: 分析模式 ("normal" 或 "deep_thinking")
        fallback_to_default: 当模式不存在时是否降级到默认模式

    Returns:
        Dict[str, Any]: 文件上传配置字典
        {
            "enabled": bool,           # 是否启用文件上传
            "max_files": int,          # 最大文件数量
            "allowed_types": List[str] # 允许的文件类型
        }

    Example:
        >>> config = get_file_upload_config("normal")
        >>> config["enabled"]
        False
        >>> config = get_file_upload_config("deep_thinking")
        >>> config["enabled"]
        True
    """
    try:
        full_config = load_mode_config()
        modes = full_config.get("modes", {})

        # 检查模式是否存在
        if analysis_mode not in modes:
            if fallback_to_default:
                default_mode = full_config.get("default_mode", "normal")
                logger.warning(f"️ 未知分析模式 '{analysis_mode}'，降级为默认模式 '{default_mode}'")
                analysis_mode = default_mode
            else:
                available_modes = list(modes.keys())
                raise AnalysisModeConfigError(f"不支持的分析模式: {analysis_mode}。可用模式: {available_modes}")

        # 提取文件上传配置
        mode_config = modes[analysis_mode]
        file_upload_config = mode_config.get("file_upload", {})

        # 如果配置不存在，使用安全的默认值
        if not file_upload_config:
            logger.warning(f"️ 模式 '{analysis_mode}' 缺少 file_upload 配置，使用默认值")
            file_upload_config = {"enabled": False, "max_files": 0, "allowed_types": []}

        result = {
            "enabled": file_upload_config.get("enabled", False),
            "max_files": file_upload_config.get("max_files", 0),
            "allowed_types": file_upload_config.get("allowed_types", []),
        }

        logger.debug(
            f" [文件上传配置] {analysis_mode} → "
            f"enabled={result['enabled']}, max_files={result['max_files']}, "
            f"types={len(result['allowed_types'])}"
        )

        return result

    except AnalysisModeConfigError:
        raise
    except Exception as e:
        logger.error(f" 获取文件上传配置时发生错误: {e}")
        # 返回安全的默认值（禁用上传）
        return {"enabled": False, "max_files": 0, "allowed_types": []}


def is_file_upload_enabled(analysis_mode: str) -> bool:
    """
    检查指定模式是否启用文件上传功能

     v7.350: 新增函数

    Args:
        analysis_mode: 分析模式

    Returns:
        bool: True 表示启用文件上传，False 表示禁用

    Example:
        >>> is_file_upload_enabled("normal")
        False
        >>> is_file_upload_enabled("deep_thinking")
        True
    """
    config = get_file_upload_config(analysis_mode)
    return config.get("enabled", False)


# 预加载配置以捕获配置错误
try:
    _config = load_mode_config()
    logger.info(
        f" 分析模式配置已加载: " f"{len(_config.get('modes', {}))} 个模式, " f"默认模式: {_config.get('default_mode', 'unknown')}"
    )
except AnalysisModeConfigError as e:
    logger.error(f" 配置加载失败: {e}")
