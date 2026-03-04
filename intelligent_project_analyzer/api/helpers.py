# -*- coding: utf-8 -*-
"""
MT-1 (2026-03-01): API 报告数据清洗辅助函数

从 api/server.py 提取的纯工具函数，无服务器状态依赖。
"""
from __future__ import annotations

import json
import re
import uuid
from collections import OrderedDict, defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from .models import ReportSectionResponse


def _is_blank_section(section: ReportSectionResponse) -> bool:
    """判断章节内容是否为空或仅包含占位符"""

    content = (section.content or "").strip()
    if not content:
        return True

    normalized = content.strip()
    if normalized in {"{}", "[]", '""'}:
        return True

    try:
        parsed = json.loads(normalized)
    except Exception:
        return False

    if isinstance(parsed, dict):
        return len(parsed) == 0
    if isinstance(parsed, list):
        return len(parsed) == 0
    return False


def _normalize_section_id(raw_identifier: Optional[str], fallback: str) -> str:
    """规范化章节 ID，确保可用于字典键与前端锚点"""

    candidate = (raw_identifier or "").strip()
    if candidate:
        slug = re.sub(r"[^A-Za-z0-9]+", "_", candidate).strip("_").lower()
        if slug:
            return slug

    slug = re.sub(r"[^A-Za-z0-9]+", "_", fallback).strip("_").lower()
    if slug:
        return slug

    return f"section_{uuid.uuid4().hex[:8]}"


def _derive_section_identity(role_id: str, agent_result: Dict[str, Any]) -> Tuple[str, str]:
    """根据智能体输出推断章节 ID 与标题，支持动态角色"""

    metadata = agent_result.get("metadata") or {}

    candidate_ids = [
        metadata.get("section_id"),
        agent_result.get("section_id"),
        agent_result.get("report_section_id"),
    ]

    candidate_titles = [
        metadata.get("section_title"),
        agent_result.get("section_title"),
        agent_result.get("display_name"),
        agent_result.get("role_name"),
    ]

    if role_id == "requirements_analyst":
        candidate_ids.append("requirements_analysis")
        candidate_titles.append("需求分析")

    section_id = _normalize_section_id(next((cid for cid in candidate_ids if cid), None), role_id)
    section_title = next((title for title in candidate_titles if title), None) or role_id

    return section_id, section_title


def _sanitize_structured_data(data: Any) -> Tuple[Any, List[str]]:
    """清理结构化数据，滤除不符合约束的命名项"""

    warnings: List[str] = []

    if not isinstance(data, dict):
        return data, warnings

    sanitized: Dict[str, Any] = {}

    for key, value in data.items():
        if key == "custom_analysis" and isinstance(value, dict):
            cleaned_custom, custom_warnings = _sanitize_custom_analysis(value)
            sanitized[key] = cleaned_custom
            warnings.extend(custom_warnings)
        elif isinstance(value, dict):
            cleaned_value, nested_warnings = _sanitize_structured_data(value)
            sanitized[key] = cleaned_value
            warnings.extend(nested_warnings)
        else:
            sanitized[key] = value

    return sanitized, warnings


def _sanitize_custom_analysis(data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """针对定制分析部分的命名长度做约束过滤"""

    sanitized: Dict[str, Any] = {}
    warnings: List[str] = []

    for key, value in data.items():
        if isinstance(value, list):
            valid_entries = []
            removed_entries = []

            for entry in value:
                if isinstance(entry, dict):
                    name = entry.get("命名本身") or entry.get("命名") or entry.get("名称")
                    name_str = name.strip() if isinstance(name, str) else ""
                    if name_str and len(name_str) == 4:
                        valid_entries.append(entry)
                    else:
                        removed_entries.append(name_str or "<未命名>")
                else:
                    valid_entries.append(entry)

            if removed_entries:
                warnings.append(f"{key}: 已移除{len(removed_entries)}个未满足四字要求的命名")

            sanitized[key] = valid_entries

        elif isinstance(value, dict):
            cleaned_value, nested_warnings = _sanitize_custom_analysis(value)
            sanitized[key] = cleaned_value
            warnings.extend(nested_warnings)
        else:
            sanitized[key] = value

    return sanitized, warnings


def _format_agent_payload(agent_result: Dict[str, Any]) -> Optional[OrderedDict]:
    """将智能体输出格式化为结构化payload"""

    if not agent_result:
        return None

    structured_raw = agent_result.get("structured_data") or {}
    structured, validation_warnings = _sanitize_structured_data(structured_raw)
    content = agent_result.get("content")

    payload = OrderedDict()

    if structured:
        payload["structured_data"] = structured

    if isinstance(content, str) and content.strip():
        payload["narrative_summary"] = content.strip()

    if validation_warnings:
        payload["validation_warnings"] = validation_warnings

    return payload if payload else None


def _enrich_sections_with_agent_results(
    sections: List[ReportSectionResponse], session: Dict[str, Any]
) -> List[ReportSectionResponse]:
    """补全或替换缺失的章节内容"""

    agent_results = session.get("agent_results") or {}
    if not agent_results:
        return sections

    active_agents = session.get("active_agents") or list(agent_results.keys())

    section_lookup: Dict[str, ReportSectionResponse] = {}
    unlabeled_sections: List[ReportSectionResponse] = []

    for sec in sections:
        if sec.section_id:
            section_lookup[sec.section_id] = sec
        else:
            unlabeled_sections.append(sec)

    # 收集各章节的补充数据
    section_contributions: Dict[str, OrderedDict] = {}
    section_titles: Dict[str, str] = {}
    section_confidences: Dict[str, List[float]] = defaultdict(list)
    agent_section_sequence: List[str] = []

    for role_id in active_agents:
        agent_result = agent_results.get(role_id) or {}
        payload = _format_agent_payload(agent_result)
        if not payload:
            continue

        section_id, section_title = _derive_section_identity(role_id, agent_result)
        agent_section_sequence.append(section_id)

        source_name = agent_result.get("display_name") or agent_result.get("role_name") or role_id

        section_contributions.setdefault(section_id, OrderedDict())
        section_contributions[section_id][source_name] = payload

        if section_title:
            section_titles.setdefault(section_id, section_title)

        confidence = agent_result.get("confidence")
        try:
            if confidence is not None:
                section_confidences[section_id].append(float(confidence))
        except (TypeError, ValueError):
            pass

    if not section_contributions:
        return sections

    for section_id, payload in section_contributions.items():
        if not payload:
            continue

        section = section_lookup.get(section_id)
        if section is None:
            section = ReportSectionResponse(
                section_id=section_id,
                title=section_titles.get(section_id, section_id),
                content="",
                confidence=0.0,
            )
            section_lookup[section_id] = section

        if not section.title:
            section.title = section_titles.get(section_id, section_id)

        if _is_blank_section(section):
            section.content = json.dumps(payload, ensure_ascii=False, indent=2)

        #  Phase 1.4+: 修复置信度为0%的问题
        # 无论章节内容是否为空，都应该补全confidence值
        confidence_values = section_confidences.get(section_id, [])
        if confidence_values:
            section.confidence = max(confidence_values)
        elif not section.confidence or section.confidence == 0.0:
            # 如果confidence为0或未设置，使用默认值0.8
            section.confidence = 0.8

    ordered_sections: List[ReportSectionResponse] = []
    added_ids: Set[str] = set()

    for section in sections:
        section_id = section.section_id
        if section_id and section_id not in added_ids:
            ordered_sections.append(section)
            added_ids.add(section_id)

    for section_id in agent_section_sequence:
        section = section_lookup.get(section_id)
        if section and section.section_id not in added_ids:
            ordered_sections.append(section)
            added_ids.add(section.section_id)

    for section in section_lookup.values():
        if section.section_id not in added_ids:
            ordered_sections.append(section)
            added_ids.add(section.section_id)

    ordered_sections.extend(unlabeled_sections)

    return ordered_sections
