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
from typing import Any, Dict

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

    # 🆕 v7.121: 读取用户需求上下文
    user_input = state.get("user_input", "")
    structured_requirements = state.get("structured_requirements", {})

    # 🆕 v7.121: 读取问卷数据
    questionnaire_summary = state.get("questionnaire_summary", {})
    confirmed_core_tasks = state.get("confirmed_core_tasks", [])
    gap_answers = questionnaire_summary.get("answers", {}).get("gap_answers", {})
    profile_label = questionnaire_summary.get("profile_label", "")
    radar_values = questionnaire_summary.get("answers", {}).get("radar_values", {})

    logger.info(f"📊 [v7.121] 问卷数据读取:")
    logger.info(f"  核心任务数: {len(confirmed_core_tasks)}")
    logger.info(f"  Gap回答数: {len(gap_answers)}")
    logger.info(f"  风格标签: {profile_label}")
    logger.info(f"  雷达维度数: {len(radar_values)}")

    if not selected_roles:
        logger.warning("⚠️ [交付物ID生成] 未找到选定角色，跳过ID生成")
        return {"deliverable_metadata": {}, "deliverable_owner_map": {}, "detail": "未找到选定角色"}

    logger.info(f"📋 [交付物ID生成] 为 {len(selected_roles)} 个角色生成交付物ID")

    # 🆕 增强调试信息
    logger.debug(f"🔍 [调试] selected_roles 类型: {type(selected_roles)}")
    if selected_roles:
        logger.debug(f"🔍 [调试] 第一个元素类型: {type(selected_roles[0])}")
        logger.debug(f"🔍 [调试] 第一个元素内容: {selected_roles[0]}")

    # 2. 🆕 v7.121: 提取问卷关键词（替代硬编码模板）
    questionnaire_keywords = _extract_keywords_from_questionnaire(
        gap_answers=gap_answers, profile_label=profile_label, radar_values=radar_values
    )

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

        # 🆕 v7.121: 使用动态生成替代硬编码模板
        templates = _generate_role_specific_deliverables(
            role_id=role_id,
            role_base_type=role_base_type,
            user_input=user_input,
            structured_requirements=structured_requirements,
            questionnaire_keywords=questionnaire_keywords,
            confirmed_core_tasks=confirmed_core_tasks,
        )

        if not templates:
            logger.warning(f"⚠️ [交付物ID生成] 角色 {role_id} ({role_base_type}) 未能生成交付物")
            deliverable_owner_map[role_id] = []
            continue

        deliverable_owner_map[role_id] = []

        # 为该角色的每个交付物生成唯一ID
        for idx, template in enumerate(templates, start=1):
            deliverable_id = _generate_unique_id(role_id, idx)

            # 创建交付物元数据（现在包含问卷关键词）
            metadata = {
                "id": deliverable_id,
                "name": template.get("name", f"交付物{idx}"),
                "description": template.get("description", ""),
                "keywords": template.get("keywords", []),  # ✅ 现在包含项目特定关键词
                "constraints": template.get("constraints", {}),  # ✅ 包含问卷约束
                "owner_role": role_id,
                "created_at": datetime.now().isoformat(),
            }

            deliverable_metadata[deliverable_id] = metadata
            deliverable_owner_map[role_id].append(deliverable_id)

            logger.debug(f"  ✅ 生成交付物ID: {deliverable_id} - {metadata['name']}")

    total_deliverables = len(deliverable_metadata)
    logger.info(f"✅ [交付物ID生成] 完成！共生成 {total_deliverables} 个交付物ID")

    return {
        "deliverable_metadata": deliverable_metadata,
        "deliverable_owner_map": deliverable_owner_map,
        "detail": f"已生成 {total_deliverables} 个交付物ID",
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
    random_suffix = "".join(random.choices(string.ascii_lowercase, k=3))
    return f"{role_id}_{index}_{timestamp}_{random_suffix}"


def _extract_role_base_type(role_id: str) -> str:
    """
    从角色ID提取基础类型

    Args:
        role_id: 角色ID，如 "2-1", "3-2"

    Returns:
        基础类型，如 "V2", "V3"
    """
    if isinstance(role_id, str) and "-" in role_id:
        level = role_id.split("-")[0]
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
                    "style_preferences": "professional architectural rendering",
                },
            },
            {
                "name": "关键节点深化",
                "description": "重要设计节点的深化设计",
                "keywords": ["节点设计", "细部处理", "材料应用"],
                "constraints": {"must_include": ["节点详图", "材料清单"], "style_preferences": "detailed technical drawing"},
            },
        ],
        "V3": [
            {
                "name": "叙事与体验策略",
                "description": "空间叙事逻辑与用户体验路径",
                "keywords": ["叙事逻辑", "体验设计", "情感连接"],
                "constraints": {
                    "must_include": ["体验流线", "情感触点"],
                    "style_preferences": "conceptual narrative visualization",
                },
            }
        ],
        "V4": [
            {
                "name": "设计研究报告",
                "description": "前期调研与案例分析",
                "keywords": ["案例研究", "趋势分析", "用户研究"],
                "constraints": {"must_include": ["案例分析", "设计建议"], "style_preferences": "research infographic"},
            }
        ],
        "V5": [
            {
                "name": "场景设计方案",
                "description": "具体使用场景的设计策略",
                "keywords": ["场景设计", "功能配置", "氛围营造"],
                "constraints": {"must_include": ["场景描述", "功能清单"], "style_preferences": "scenario visualization"},
            }
        ],
        "V6": [
            {
                "name": "技术实施方案",
                "description": "工程技术可行性与实施建议",
                "keywords": ["技术可行性", "施工工艺", "成本控制"],
                "constraints": {"must_include": ["技术要点", "成本估算"], "style_preferences": "technical schematic"},
            }
        ],
    }


def _extract_keywords_from_questionnaire(
    gap_answers: Dict[str, Any], profile_label: str, radar_values: Dict[str, float]
) -> Dict[str, Any]:
    """
    🆕 v7.121: 从问卷数据中提取项目特定关键词

    Args:
        gap_answers: Step 3 的详细回答
        profile_label: Step 2 的风格标签（如"现代实用主义"）
        radar_values: Step 2 的雷达图评分

    Returns:
        分类的关键词字典
    """
    keywords = {
        "material_keywords": [],
        "color_palette": "",
        "emotional_keywords": [],
        "functional_keywords": [],
        "budget_keywords": [],
    }

    # 1. 从风格标签提取
    if profile_label:
        keywords["style_label"] = profile_label

        # 映射风格标签到视觉关键词
        style_mapping = {
            "现代实用主义": {"materials": ["简洁线条", "功能性家具", "智能收纳"], "colors": "neutral tones, functional aesthetics"},
            "温馨自然": {"materials": ["木质元素", "天然织物", "植物装饰"], "colors": "warm earth tones, natural wood"},
            "工业冷峻": {"materials": ["裸露混凝土", "金属管道", "黑色框架"], "colors": "industrial grey, black steel"},
            "轻奢优雅": {"materials": ["大理石", "黄铜饰面", "丝绒软包"], "colors": "luxury gold, marble white"},
        }

        if profile_label in style_mapping:
            keywords["material_keywords"].extend(style_mapping[profile_label]["materials"])
            keywords["color_palette"] = style_mapping[profile_label]["colors"]

    # 2. 从 gap_answers 提取具体需求
    import re

    for answer_key, answer_text in gap_answers.items():
        if not isinstance(answer_text, str):
            continue

        # 提取预算相关
        if "预算" in answer_text or "万" in answer_text or "元" in answer_text:
            budget_match = re.search(r"(\d+)万", answer_text)
            if budget_match:
                keywords["budget_keywords"].append(f"{budget_match.group(1)}万预算")

        # 提取材料关键词
        material_patterns = ["木", "石", "金属", "玻璃", "布艺", "皮革", "大理石", "混凝土", "砖", "瓷砖"]
        for mat in material_patterns:
            if mat in answer_text and mat not in keywords["material_keywords"]:
                keywords["material_keywords"].append(mat)

        # 提取功能需求
        function_patterns = ["收纳", "采光", "隐私", "安全", "儿童", "老人", "宠物", "通风", "降噪"]
        for func in function_patterns:
            if func in answer_text and func not in keywords["functional_keywords"]:
                keywords["functional_keywords"].append(func)

        # 提取情感关键词
        emotion_patterns = ["温馨", "宁静", "活力", "优雅", "舒适", "自然", "现代", "传统", "简约", "奢华"]
        for emo in emotion_patterns:
            if emo in answer_text and emo not in keywords["emotional_keywords"]:
                keywords["emotional_keywords"].append(emo)

    # 3. 从雷达图评分提取优先级
    if radar_values:
        # 找出评分最高的3个维度
        sorted_dims = sorted(radar_values.items(), key=lambda x: x[1], reverse=True)[:3]
        top_dimensions = [dim for dim, _ in sorted_dims]
        keywords["priority_dimensions"] = top_dimensions

    logger.info(f"🔍 [v7.121] 从问卷提取的关键词:")
    logger.info(f"  材料: {keywords['material_keywords'][:5]}")
    logger.info(f"  功能: {keywords['functional_keywords'][:5]}")
    logger.info(f"  预算: {keywords['budget_keywords']}")
    logger.info(f"  风格: {profile_label}")

    return keywords


def _generate_role_specific_deliverables(
    role_id: str,
    role_base_type: str,
    user_input: str,
    structured_requirements: Dict[str, Any],
    questionnaire_keywords: Dict[str, Any],
    confirmed_core_tasks: list,
) -> list:
    """
    🆕 v7.121: 为每个角色生成特定的交付物，注入项目上下文

    替代硬编码的 _get_deliverable_templates()

    Args:
        role_id: 角色ID，如 "2-1"
        role_base_type: 角色基础类型，如 "V2"
        user_input: 用户原始输入
        structured_requirements: 需求分析器的结构化数据
        questionnaire_keywords: 从问卷提取的关键词
        confirmed_core_tasks: Step 1 确认的核心任务列表

    Returns:
        交付物模板列表（注入了项目特定关键词和约束）
    """
    # 🔧 v7.122: 类型安全处理 - physical_context 和 design_challenge 可能是字符串或字典
    import json

    # 安全提取 physical_context
    physical_context = structured_requirements.get("physical_context", {})
    if isinstance(physical_context, str):
        try:
            physical_context = json.loads(physical_context)
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"⚠️ physical_context 是字符串且无法解析为 JSON，使用默认空字典")
            physical_context = {}

    # 安全提取 design_challenge
    design_challenge = structured_requirements.get("design_challenge", {})
    if isinstance(design_challenge, str):
        try:
            design_challenge = json.loads(design_challenge)
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"⚠️ design_challenge 是字符串且无法解析为 JSON，使用默认空字典")
            design_challenge = {}

    # 提取项目特征
    location = physical_context.get("location", "") if isinstance(physical_context, dict) else ""
    space_type = physical_context.get("space_type", "") if isinstance(physical_context, dict) else ""
    budget = design_challenge.get("budget", "") if isinstance(design_challenge, dict) else ""

    # 问卷关键词
    style_label = questionnaire_keywords.get("style_label", "")
    material_keywords = questionnaire_keywords.get("material_keywords", [])
    functional_keywords = questionnaire_keywords.get("functional_keywords", [])
    budget_keywords = questionnaire_keywords.get("budget_keywords", [])
    color_palette = questionnaire_keywords.get("color_palette", "")

    # 根据角色类型生成
    if role_base_type == "V2":  # 设计总监
        return [
            {
                "name": f"{space_type}整体设计方案" if space_type else "整体设计方案",
                "description": f"{location}项目的整体设计策略与空间规划" if location else "整体设计策略",
                "keywords": [
                    # 🔥 使用问卷关键词替代硬编码
                    f"{location}文化特色" if location else "地域文化",
                    f"{budget}预算优化" if budget else "预算控制",
                    style_label if style_label else "设计风格",
                    *functional_keywords[:2],  # 前2个功能关键词
                ],
                "constraints": {
                    "must_include": [
                        # 🔥 从问卷中提取的具体约束
                        *material_keywords[:3],  # 前3个材料关键词
                        *functional_keywords[:2],  # 前2个功能关键词
                        f"{space_type}的功能分区" if space_type else "功能分区",
                    ],
                    "budget_constraint": budget or (budget_keywords[0] if budget_keywords else ""),
                    "style_preferences": f"{style_label} aesthetic, {color_palette}"
                    if style_label
                    else "professional design",
                    "user_specific_needs": ", ".join(functional_keywords[:5]),  # 🔥 用户特定需求
                    # 🆕 v7.122: 保留完整的问卷情感关键词供概念图使用
                    "emotional_keywords": questionnaire_keywords.get("emotional_keywords", []),
                    "profile_label": style_label,  # 🔥 v7.122: 显式保存问卷风格标签
                },
            },
            {
                "name": "材质与色彩方案",
                "description": f"体现{location}文化的材质选型与配色" if location else "材质选型与配色",
                "keywords": material_keywords[:5] if material_keywords else ["天然材料", "本地特色"],
                "constraints": {
                    "must_include": [*material_keywords[:3], f"{budget}预算范围内的材料选择" if budget else "性价比材料"],
                    "color_palette": color_palette if color_palette else "natural, warm tones",
                    # 🆕 v7.122: 保留问卷关键词
                    "emotional_keywords": questionnaire_keywords.get("emotional_keywords", []),
                    "profile_label": style_label,
                },
            },
        ]

    elif role_base_type == "V3":  # 叙事专家
        return [
            {
                "name": f"{location}文化叙事方案" if location else "文化叙事方案",
                "description": f"空间中的{location}文化故事线与情感表达" if location else "空间叙事",
                "keywords": [
                    f"{location}历史记忆" if location else "历史记忆",
                    style_label if style_label else "叙事主题",
                    *questionnaire_keywords.get("emotional_keywords", [])[:3],
                ],
                "constraints": {
                    "must_include": [
                        f"{location}文化符号装饰" if location else "文化符号",
                        "情感化的空间场景",
                        *questionnaire_keywords.get("emotional_keywords", [])[:2],
                    ],
                    "narrative_theme": f"preserving {location} heritage while embracing modern life"
                    if location
                    else "cultural preservation",
                    "emotional_keywords": questionnaire_keywords.get("emotional_keywords", ["warmth", "comfort"]),
                    # 🆕 v7.122: 保留问卷风格标签
                    "profile_label": style_label,
                },
            }
        ]

    # 其他角色类型（V4, V5, V6）使用简化版本或回退到原有模板
    else:
        # 如果有问卷数据，生成简化的项目特定交付物
        if style_label or functional_keywords:
            return [
                {
                    "name": f"{role_base_type} 专家分析报告",
                    "description": f"基于{style_label}风格的专业分析" if style_label else "专业分析",
                    "keywords": [style_label if style_label else "专业分析", *functional_keywords[:3]],
                    "constraints": {
                        "must_include": material_keywords[:2] if material_keywords else [],
                        "project_context": f"{location}, {space_type}, {budget}"
                        if all([location, space_type, budget])
                        else "",
                    },
                }
            ]
        else:
            # 回退到原有模板
            return _get_deliverable_templates().get(role_base_type, [])
