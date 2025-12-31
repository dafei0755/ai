"""
交付物ID生成节点

在workflow早期阶段（project_director之后、batch_router之前）生成交付物ID，
以便在专家执行阶段可以使用这些ID进行概念图生成。

Author: Claude Code
Created: 2025-12-29
Version: v1.0
"""

import random
import string
from datetime import datetime
from typing import Dict, Any
from loguru import logger


def deliverable_id_generator_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    为所有选定角色生成唯一的交付物ID

    输入state字段:
    - strategic_analysis["selected_roles"]: List[str] - 角色ID列表，如 ["2-1", "3-1", "4-1"]
    - session_id: str - 会话ID

    输出state字段:
    - deliverable_metadata: Dict[str, Dict] - 交付物元数据
      格式: {
          "deliverable_id": {
              "id": "2-1_1_143022_abc",
              "name": "空间功能分区方案",
              "description": "...",
              "keywords": ["现代", "简约"],
              "constraints": {...},
              "owner_role": "2-1",
              "created_at": "2025-12-29T14:30:22"
          }
      }
    - deliverable_owner_map: Dict[str, List[str]] - 角色到交付物ID的映射
      格式: {
          "2-1": ["2-1_1_143022_abc", "2-1_2_143023_def"],
          "3-1": ["3-1_1_143024_ghi"]
      }
    """

    logger.info("📋 [交付物ID生成] 开始生成交付物ID...")

    # 1. 从state中提取必要信息
    strategic_analysis = state.get("strategic_analysis", {})
    selected_roles = strategic_analysis.get("selected_roles", [])
    session_id = state.get("session_id", "unknown")

    if not selected_roles:
        logger.warning("⚠️ [交付物ID生成] 未找到选定角色，跳过ID生成")
        return {
            "deliverable_metadata": {},
            "deliverable_owner_map": {},
            "detail": "未找到选定角色"
        }

    logger.info(f"📋 [交付物ID生成] 为 {len(selected_roles)} 个角色生成交付物ID")

    # 🆕 增强调试信息
    logger.debug(f"🔍 [调试] selected_roles 类型: {type(selected_roles)}")
    if selected_roles:
        logger.debug(f"🔍 [调试] 第一个元素类型: {type(selected_roles[0])}")
        logger.debug(f"🔍 [调试] 第一个元素内容: {selected_roles[0]}")

    # 2. 加载交付物配置（简化版本，实际应从config/deliverable_role_constraints.yaml加载）
    # 这里使用简化的硬编码配置作为示例
    role_deliverable_templates = _get_deliverable_templates()

    # 3. 为每个角色生成交付物ID
    deliverable_metadata = {}
    deliverable_owner_map = {}

    for role_info in selected_roles:  # ✅ 重命名变量更清晰
        # 🆕 兼容两种格式：dict（新格式）或 str（旧格式）
        if isinstance(role_info, dict):
            role_id = role_info.get("role_id")
            if not role_id:
                logger.warning(f"⚠️ [交付物ID生成] 跳过无效角色（缺少role_id）: {role_info}")
                continue
        else:
            # 向后兼容字符串格式
            role_id = role_info

        role_base_type = _extract_role_base_type(role_id)  # "2-1" -> "V2"

        # 获取该角色类型的交付物模板
        templates = role_deliverable_templates.get(role_base_type, [])

        if not templates:
            logger.warning(f"⚠️ [交付物ID生成] 角色 {role_id} ({role_base_type}) 未找到交付物模板")
            deliverable_owner_map[role_id] = []  # ✅ role_id 现在是字符串
            continue

        deliverable_owner_map[role_id] = []  # ✅ role_id 现在是字符串

        # 为该角色的每个交付物生成唯一ID
        for idx, template in enumerate(templates, start=1):
            deliverable_id = _generate_unique_id(role_id, idx)

            # 创建交付物元数据
            metadata = {
                "id": deliverable_id,
                "name": template.get("name", f"交付物{idx}"),
                "description": template.get("description", ""),
                "keywords": template.get("keywords", []),
                "constraints": template.get("constraints", {}),
                "owner_role": role_id,
                "created_at": datetime.now().isoformat()
            }

            deliverable_metadata[deliverable_id] = metadata
            deliverable_owner_map[role_id].append(deliverable_id)

            logger.debug(f"  ✅ 生成交付物ID: {deliverable_id} - {metadata['name']}")

    total_deliverables = len(deliverable_metadata)
    logger.info(f"✅ [交付物ID生成] 完成！共生成 {total_deliverables} 个交付物ID")

    return {
        "deliverable_metadata": deliverable_metadata,
        "deliverable_owner_map": deliverable_owner_map,
        "detail": f"已生成 {total_deliverables} 个交付物ID"
    }


def _generate_unique_id(role_id: str, index: int) -> str:
    """
    生成唯一的交付物ID

    格式: {role_id}_{index}_{timestamp}_{random}
    示例: 2-1_1_143022_abc

    Args:
        role_id: 角色ID，如 "2-1"
        index: 交付物索引（从1开始）

    Returns:
        唯一的交付物ID
    """
    timestamp = datetime.now().strftime("%H%M%S")
    random_suffix = ''.join(random.choices(string.ascii_lowercase, k=3))
    return f"{role_id}_{index}_{timestamp}_{random_suffix}"


def _extract_role_base_type(role_id: str) -> str:
    """
    从角色ID提取基础类型

    Args:
        role_id: 角色ID，如 "2-1", "3-2"

    Returns:
        基础类型，如 "V2", "V3"
    """
    if isinstance(role_id, str) and '-' in role_id:
        level = role_id.split('-')[0]
        return f"V{level}"
    return "V2"  # 默认V2


def _get_deliverable_templates() -> Dict[str, list]:
    """
    获取各角色类型的交付物模板配置

    Returns:
        角色类型到交付物模板列表的映射
    """
    # 简化版本的交付物模板
    # 实际应从 config/deliverable_role_constraints.yaml 加载
    return {
        "V2": [
            {
                "name": "整体设计方案",
                "description": "项目整体设计策略与概念",
                "keywords": ["设计方向", "风格定位", "空间规划"],
                "constraints": {
                    "must_include": ["设计理念", "空间布局", "材质选型"],
                    "style_preferences": "professional architectural rendering"
                }
            },
            {
                "name": "关键节点深化",
                "description": "重要设计节点的深化设计",
                "keywords": ["节点设计", "细部处理", "材料应用"],
                "constraints": {
                    "must_include": ["节点详图", "材料清单"],
                    "style_preferences": "detailed technical drawing"
                }
            }
        ],
        "V3": [
            {
                "name": "叙事与体验策略",
                "description": "空间叙事逻辑与用户体验路径",
                "keywords": ["叙事逻辑", "体验设计", "情感连接"],
                "constraints": {
                    "must_include": ["体验流线", "情感触点"],
                    "style_preferences": "conceptual narrative visualization"
                }
            }
        ],
        "V4": [
            {
                "name": "设计研究报告",
                "description": "前期调研与案例分析",
                "keywords": ["案例研究", "趋势分析", "用户研究"],
                "constraints": {
                    "must_include": ["案例分析", "设计建议"],
                    "style_preferences": "research infographic"
                }
            }
        ],
        "V5": [
            {
                "name": "场景设计方案",
                "description": "具体使用场景的设计策略",
                "keywords": ["场景设计", "功能配置", "氛围营造"],
                "constraints": {
                    "must_include": ["场景描述", "功能清单"],
                    "style_preferences": "scenario visualization"
                }
            }
        ],
        "V6": [
            {
                "name": "技术实施方案",
                "description": "工程技术可行性与实施建议",
                "keywords": ["技术可行性", "施工工艺", "成本控制"],
                "constraints": {
                    "must_include": ["技术要点", "成本估算"],
                    "style_preferences": "technical schematic"
                }
            }
        ]
    }
