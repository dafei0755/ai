"""
硅基分身 (Designer Silicon Self / DSS) — 上下文注入工具

Phase 1: 将设计师画像摘要注入 S1 输入解构节点的上下文中。
分身数据只作为 prompt 补充上下文，不改变冻结对象结构。

约束：
- 只返回 str（prompt 片段），不返回可被 merge 到冻结对象的结构化数据
- 所有注入都是"建议性"的，不驱动节点流转
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def build_dss_context_snippet(designer_profile: Optional[Dict[str, Any]]) -> str:
    """
    从设计师画像构建 system prompt 注入片段。

    Args:
        designer_profile: 前端传来的 DesignerProfile 字典（可能为 None）

    Returns:
        可直接拼接到 system prompt 的文本片段。无画像时返回空字符串。
    """
    if not designer_profile:
        return ""

    parts: list[str] = []
    parts.append("【设计师画像上下文（硅基分身注入）】")

    name = designer_profile.get("displayName", "")
    if name:
        parts.append(f"设计师：{name}")

    years = designer_profile.get("yearsOfExperience")
    if years and years > 0:
        parts.append(f"从业年限：{years} 年")

    city = designer_profile.get("city", "")
    if city:
        parts.append(f"所在城市：{city}")

    company = designer_profile.get("companyType", "")
    team = designer_profile.get("teamSize", "")
    if company or team:
        parts.append(f"组织形态：{company} / {team}")

    # 业态能力矩阵摘要
    matrix = designer_profile.get("specialtyMatrix", [])
    if matrix:
        done_items = [
            s for s in matrix
            if s.get("confidenceLevel") == "done"
        ]
        if done_items:
            summary = "、".join(
                f"{s.get('archetype', '')}({s.get('geoType', '')})"
                for s in done_items[:5]
            )
            parts.append(f"真实做过的项目类型：{summary}")

    # 七视角倾向
    weights = designer_profile.get("perspectiveWeights")
    if weights and isinstance(weights, dict):
        dim_names = {
            "aesthetic": "美学",
            "functional": "功能",
            "operational": "运营",
            "cost": "成本",
            "risk": "风险",
            "cultural": "文化",
            "temporal": "时间",
        }
        sorted_dims = sorted(weights.items(), key=lambda x: x[1], reverse=True)
        strong = [dim_names.get(k, k) for k, v in sorted_dims[:2]]
        weak = [dim_names.get(k, k) for k, v in sorted_dims[-2:]]
        parts.append(f"视角偏好：偏重{'/'.join(strong)}，较少关注{'/'.join(weak)}")

    # 决策风格
    style = designer_profile.get("decisionStyle", {})
    approach = style.get("primaryApproach", "")
    if approach:
        parts.append(f"决策起手式：{approach}")

    parts.append("（以上仅作为上下文参考，不替代本次项目的具体判断）")

    snippet = "\n".join(parts)
    logger.info(f"[DSS] 画像注入片段生成完毕 ({len(snippet)} chars)")
    return snippet
