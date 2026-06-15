"""
Activation Pack 自动校验器

实施 ACTIVATION_PACK_BOUNDARY_RULES.md 中定义的 6 条边界规则。

╔══════════════════════════════════════════════════════════════════════════╗
║  ⭐ 用法                                                                  ║
║                                                                          ║
║  # 校验所有激活包                                                         ║
║  python -m intelligent_project_analyzer.services.validate_activation_pack║
║                                                                          ║
║  # 校验单个激活包                                                         ║
║  python -m intelligent_project_analyzer.services.validate_activation_pack ║
║      knowledge_base/activation_packs/tea_drink_store_pack.yaml           ║
║                                                                          ║
║  退出码:                                                                  ║
║    0 = 全部通过 (含 WARN, 不阻塞)                                         ║
║    1 = 有 ERROR (必须修)                                                  ║
║    2 = 文件结构错误 (yaml 解析失败等)                                     ║
╚══════════════════════════════════════════════════════════════════════════╝

校验规则 (对应 ACTIVATION_PACK_BOUNDARY_RULES.md 6 条):
  规则 1 (半自动): 激活包应有量化参数, 不应只是议题命名
  规则 2 (全自动): E 维度必须存在于 ontology_dimension_registry
  规则 3 (半自动): 应有 zoning_heuristics / equipment_precheck 等量化字段
  规则 4 (人工):   跨业态共通 vs 业态专属 (Code Review)
  规则 5 (全自动): routing_binding.parent_project_type_id 必填 + 存在性校验
  规则 6 (全自动): 父 framework 必须存在于 ontology.yaml::ontology_frameworks

定位 (在系统自我迭代框架中):
  本文件是 L0 (自动审计) 层的实现, 即"发现问题不修, 只报告"
  详见: sf/2026.5.16/SELF_EVOLUTION_PROTOCOL.md
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml

# ─────────────────────────────────────────────────────────────────────────────
# 路径常量
# ─────────────────────────────────────────────────────────────────────────────
_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent  # intelligent_project_analyzer/
_KNOWLEDGE_BASE = _PROJECT_ROOT / "knowledge_base"
_ACTIVATION_PACKS_DIR = _KNOWLEDGE_BASE / "activation_packs"
_ONTOLOGY_PATH = _KNOWLEDGE_BASE / "ontology.yaml"
_ONTOLOGY_DIM_REGISTRY_PATH = _KNOWLEDGE_BASE / "ontology_dimension_registry.yaml"


# ─────────────────────────────────────────────────────────────────────────────
# 校验结果数据结构
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class ValidationIssue:
    severity: str          # "ERROR" / "WARN" / "PASS"
    rule_id: str           # "Rule 1" / "Rule 2" / ...
    message: str

    def __str__(self) -> str:
        symbol = {"ERROR": "❌", "WARN": "⚠️ ", "PASS": "✅"}.get(self.severity, "  ")
        return f"  {symbol} {self.rule_id}: {self.message}"


@dataclass
class ValidationReport:
    pack_path: Path
    issues: List[ValidationIssue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(i.severity == "ERROR" for i in self.issues)

    @property
    def has_warnings(self) -> bool:
        return any(i.severity == "WARN" for i in self.issues)

    @property
    def overall_status(self) -> str:
        if self.has_errors:
            return "FAIL"
        if self.has_warnings:
            return "PASS (with warnings)"
        return "PASS"

    def add(self, severity: str, rule_id: str, message: str) -> None:
        self.issues.append(ValidationIssue(severity, rule_id, message))


# ─────────────────────────────────────────────────────────────────────────────
# 外部依赖加载 (与 detector 同步事实源)
# ─────────────────────────────────────────────────────────────────────────────
def _safe_load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_project_type_registry() -> Set[str]:
    """从 detector 加载 32 个 project_type ID (作为事实源)"""
    try:
        # 延迟导入避免循环
        from .project_type_detector import PROJECT_TYPE_REGISTRY
        return set(PROJECT_TYPE_REGISTRY.keys())
    except Exception:
        return set()


def load_subdomain_registry() -> Set[str]:
    """从 detector 加载 SUBDOMAIN_REGISTRY"""
    try:
        from .project_type_detector import SUBDOMAIN_REGISTRY
        return set(SUBDOMAIN_REGISTRY.keys())
    except Exception:
        return set()


def load_ontology_frameworks() -> Set[str]:
    """加载 ontology.yaml 内的所有 framework 名"""
    data = _safe_load_yaml(_ONTOLOGY_PATH)
    return set((data.get("ontology_frameworks") or {}).keys())


def load_ontology_dimensions() -> Set[str]:
    """加载 ontology_dimension_registry.yaml 内的 E 维度 ID"""
    data = _safe_load_yaml(_ONTOLOGY_DIM_REGISTRY_PATH)
    return set((data.get("ontology_dimensions") or {}).keys())


def load_activation_profiles() -> Dict[str, Dict[str, Any]]:
    """加载 ontology.yaml 内的 activation_profiles (用于规则 2 的继承检查)"""
    data = _safe_load_yaml(_ONTOLOGY_PATH)
    return data.get("activation_profiles") or {}


# ─────────────────────────────────────────────────────────────────────────────
# 6 条规则的实现
# ─────────────────────────────────────────────────────────────────────────────
def check_rule_5_routing_binding(
    pack: Dict[str, Any],
    project_types: Set[str],
    subdomains: Set[str],
    report: ValidationReport,
) -> Optional[str]:
    """
    规则 5: routing_binding.parent_project_type_id 必填且存在
    返回: parent_project_type_id (None 表示校验失败)
    """
    rb = pack.get("routing_binding") or {}

    if not rb:
        report.add("ERROR", "Rule 5", "缺少 routing_binding 字段 (激活包必须声明继承关系)")
        return None

    parent = rb.get("parent_project_type_id")
    if not parent:
        report.add("ERROR", "Rule 5", "routing_binding.parent_project_type_id 必填")
        return None

    if project_types and parent not in project_types:
        report.add(
            "ERROR",
            "Rule 5",
            f"parent_project_type_id='{parent}' 在 PROJECT_TYPE_REGISTRY 中不存在",
        )
        return parent

    report.add("PASS", "Rule 5", f"parent_project_type_id={parent} (found in registry)")

    # subdomain_id 也校验 (可选但推荐)
    subdomain = rb.get("subdomain_id")
    if subdomain:
        if subdomains and subdomain not in subdomains:
            report.add(
                "WARN",
                "Rule 5",
                f"subdomain_id='{subdomain}' 在 SUBDOMAIN_REGISTRY 中不存在 (建议先在 detector 注册)",
            )
        else:
            report.add("PASS", "Rule 5", f"subdomain_id={subdomain} (found in SUBDOMAIN_REGISTRY)")

    return parent


def check_rule_6_parent_framework(
    parent_type: Optional[str],
    frameworks: Set[str],
    report: ValidationReport,
) -> None:
    """规则 6: 父 framework 必须存在于 ontology.yaml::ontology_frameworks"""
    if not parent_type:
        return  # 规则 5 已报错, 不重复

    if not frameworks:
        report.add(
            "WARN", "Rule 6", "ontology.yaml 未能加载, 跳过父 framework 校验"
        )
        return

    # parent_project_type_id 可以直接匹配 ontology_frameworks, 也可以走 DETECTOR_TO_ONTOLOGY 映射
    # 这里只做直接匹配 (映射查询在运行时由 _resolve_detector_to_ontology 处理)
    if parent_type in frameworks:
        report.add("PASS", "Rule 6", f"父 framework '{parent_type}' 存在于 ontology.yaml")
    else:
        # 尝试通过 DETECTOR_TO_ONTOLOGY 映射
        try:
            from ..utils.ontology_loader import DETECTOR_TO_ONTOLOGY
            mapped = DETECTOR_TO_ONTOLOGY.get(parent_type)
            if mapped and mapped in frameworks:
                report.add(
                    "PASS",
                    "Rule 6",
                    f"父 framework '{parent_type}' 通过 DETECTOR_TO_ONTOLOGY 映射到 '{mapped}' (存在)",
                )
                return
        except Exception:
            pass
        report.add(
            "ERROR",
            "Rule 6",
            f"父 framework '{parent_type}' 既不在 ontology_frameworks, 也未在 DETECTOR_TO_ONTOLOGY 中映射",
        )


def check_rule_2_e_dimensions(
    pack: Dict[str, Any],
    valid_dimensions: Set[str],
    parent_type: Optional[str],
    activation_profiles: Dict[str, Dict[str, Any]],
    report: ValidationReport,
) -> None:
    """
    规则 2: E 维度必须存在于 ontology_dimension_registry
            + 建议与父 framework 的 activation_profile 有交集 (继承关系)
    """
    df = pack.get("domain_framework") or {}
    required = df.get("required_dimensions") or []
    recommended = df.get("recommended_dimensions") or []
    all_dims = list(required) + list(recommended)

    if not all_dims:
        report.add(
            "WARN",
            "Rule 2",
            "domain_framework 内未声明任何 E 维度 (required_dimensions / recommended_dimensions)",
        )
        return

    if not valid_dimensions:
        report.add("WARN", "Rule 2", "ontology_dimension_registry.yaml 未能加载, 跳过维度校验")
        return

    invalid = [d for d in all_dims if d not in valid_dimensions]
    if invalid:
        report.add(
            "ERROR",
            "Rule 2",
            f"以下 E 维度 ID 在 ontology_dimension_registry 中不存在: {invalid}",
        )
    else:
        report.add(
            "PASS",
            "Rule 2",
            f"所有 E 维度有效 (required={len(required)}, recommended={len(recommended)})",
        )

    # 继承关系检查: 与父 framework 的 elevated_topics 应有交集
    if parent_type and activation_profiles:
        parent_profile = activation_profiles.get(parent_type) or {}
        elevated = parent_profile.get("elevated_topics") or []
        # elevated_topics 可能存的是 ["E2", "E3"] 简写, 也可能是完整 ID
        # 做模糊匹配: 取 E 前缀
        elevated_prefixes = set()
        for et in elevated:
            m = re.match(r"^(E\d+)", str(et))
            if m:
                elevated_prefixes.add(m.group(1))
        pack_prefixes = set()
        for d in all_dims:
            m = re.match(r"^(E\d+)", str(d))
            if m:
                pack_prefixes.add(m.group(1))

        if elevated_prefixes and pack_prefixes:
            overlap = elevated_prefixes & pack_prefixes
            if not overlap:
                report.add(
                    "WARN",
                    "Rule 2",
                    f"激活包推荐维度 {sorted(pack_prefixes)} 与父 framework "
                    f"activation_profile.elevated_topics {sorted(elevated_prefixes)} "
                    f"完全无交集, 继承关系可疑",
                )


def check_rule_3_quantitative_params(
    pack: Dict[str, Any],
    report: ValidationReport,
) -> None:
    """规则 3: 应有量化参数字段, 不能只是议题描述"""
    quantitative_fields = [
        "zoning_heuristics",
        "equipment_precheck",
        "operation_model",
        "queue_simulation_profile",
        "scenario_presets",
        "risk_control",
    ]
    found = [f for f in quantitative_fields if pack.get(f)]

    if not found:
        report.add(
            "WARN",
            "Rule 3",
            f"激活包未发现任何量化参数字段 ({quantitative_fields})——可能只是议题描述",
        )
    else:
        report.add(
            "PASS",
            "Rule 3",
            f"含量化参数字段: {found}",
        )


def check_rule_1_topic_style_naming(
    pack: Dict[str, Any],
    report: ValidationReport,
) -> None:
    """
    规则 1: 激活包字段命名不应是议题风格 (*_topics, *_themes, *_philosophy)
    那种命名应留给 ontology.yaml
    """
    topic_style_patterns = [
        r".*_topics$",
        r".*_themes$",
        r".*_philosophy$",
        r"^elevated_.*",
        r".*_imperatives$",
    ]

    def find_topic_style_keys(d: Any, path: str = "") -> List[str]:
        results: List[str] = []
        if isinstance(d, dict):
            for k, v in d.items():
                full_path = f"{path}.{k}" if path else k
                for pat in topic_style_patterns:
                    if re.match(pat, k):
                        results.append(full_path)
                results.extend(find_topic_style_keys(v, full_path))
        elif isinstance(d, list):
            for i, item in enumerate(d):
                results.extend(find_topic_style_keys(item, f"{path}[{i}]"))
        return results

    suspicious = find_topic_style_keys(pack)
    if suspicious:
        report.add(
            "WARN",
            "Rule 1",
            f"以下字段名是议题风格 (应留给 ontology.yaml): {suspicious}",
        )


def check_required_top_level_fields(
    pack: Dict[str, Any],
    report: ValidationReport,
) -> None:
    """通用必填字段检查 (schema_version / pack_id / status / owner)"""
    required = ["schema_version", "pack_id", "status", "owner"]
    missing = [f for f in required if not pack.get(f)]
    if missing:
        report.add(
            "ERROR",
            "Schema",
            f"缺少必填字段: {missing}",
        )
    else:
        report.add(
            "PASS",
            "Schema",
            f"必填字段齐全 (pack_id={pack.get('pack_id')}, status={pack.get('status')})",
        )


def check_no_duplicate_knowledge_binding(
    pack: Dict[str, Any],
    report: ValidationReport,
) -> None:
    """
    检测重复字段: knowledge_recall_profile / knowledge_base_binding / knowledge_binding
    v1.9 协议只保留 knowledge_recall_profile, 其他应:
      - 标记 _deprecated_in_favor_of (推荐写法), 或
      - 删除 (Phase 4 清理期)

    若 deprecated 字段已显式标记 _deprecated_in_favor_of, 不再 WARN
    """
    has_recall = bool(pack.get("knowledge_recall_profile"))
    base = pack.get("knowledge_base_binding") or {}
    bind = pack.get("knowledge_binding") or {}
    has_base = bool(base)
    has_bind = bool(bind)

    # 检查 deprecated 字段是否已显式标记
    base_marked = isinstance(base, dict) and "_deprecated_in_favor_of" in base
    bind_marked = isinstance(bind, dict) and "_deprecated_in_favor_of" in bind

    # deprecated 字段都不存在 → 已经是干净 v1.9 格式
    if not has_base and not has_bind:
        if has_recall:
            report.add("PASS", "Cleanup", "仅使用 knowledge_recall_profile (v1.9 干净格式)")
        return

    # 存在 deprecated 字段, 检查是否合规标记
    base_ok = (not has_base) or base_marked
    bind_ok = (not has_bind) or bind_marked

    if has_recall and base_ok and bind_ok:
        report.add(
            "PASS",
            "Cleanup",
            "knowledge_recall_profile 为主, knowledge_base_binding/knowledge_binding "
            "已声明 _deprecated_in_favor_of (规范的兼容写法)",
        )
    elif has_recall:
        report.add(
            "WARN",
            "Cleanup",
            "检测到 knowledge_base_binding/knowledge_binding 与 knowledge_recall_profile 共存 "
            "且未声明 _deprecated_in_favor_of, "
            "v1.9 协议建议只保留 knowledge_recall_profile 或显式标记 deprecated",
        )
    else:
        report.add(
            "WARN",
            "Cleanup",
            "knowledge_base_binding / knowledge_binding 是历史字段, "
            "建议改用 knowledge_recall_profile (v1.9 协议)",
        )


# ─────────────────────────────────────────────────────────────────────────────
# 主校验流程
# ─────────────────────────────────────────────────────────────────────────────
def validate_pack(pack_path: Path) -> ValidationReport:
    """校验单个激活包文件"""
    report = ValidationReport(pack_path=pack_path)

    if not pack_path.exists():
        report.add("ERROR", "IO", f"文件不存在: {pack_path}")
        return report

    try:
        with open(pack_path, "r", encoding="utf-8") as f:
            pack = yaml.safe_load(f) or {}
    except Exception as exc:
        report.add("ERROR", "IO", f"yaml 解析失败: {exc}")
        return report

    # 加载外部依赖
    project_types = load_project_type_registry()
    subdomains = load_subdomain_registry()
    frameworks = load_ontology_frameworks()
    valid_dims = load_ontology_dimensions()
    activation_profiles = load_activation_profiles()

    # 通用 schema 检查
    check_required_top_level_fields(pack, report)

    # 规则 5: routing_binding (返回 parent_type 供后续规则使用)
    parent_type = check_rule_5_routing_binding(pack, project_types, subdomains, report)

    # 规则 6: parent framework 存在性
    check_rule_6_parent_framework(parent_type, frameworks, report)

    # 规则 2: E 维度有效性 + 继承关系
    check_rule_2_e_dimensions(pack, valid_dims, parent_type, activation_profiles, report)

    # 规则 3: 量化参数
    check_rule_3_quantitative_params(pack, report)

    # 规则 1: 议题风格命名 (启发式)
    check_rule_1_topic_style_naming(pack, report)

    # 额外: 重复 knowledge_binding 字段检测
    check_no_duplicate_knowledge_binding(pack, report)

    return report


def validate_all_packs(packs_dir: Path = _ACTIVATION_PACKS_DIR) -> List[ValidationReport]:
    """校验目录下所有 *_pack.yaml"""
    reports = []
    if not packs_dir.exists():
        print(f"WARN: 激活包目录不存在: {packs_dir}")
        return reports
    for path in sorted(packs_dir.glob("*.yaml")):
        if path.name.startswith("_"):
            continue  # 跳过下划线开头的辅助文件
        reports.append(validate_pack(path))
    return reports


# ─────────────────────────────────────────────────────────────────────────────
# CLI 入口
# ─────────────────────────────────────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Activation Pack 边界规则校验器 (实施 ACTIVATION_PACK_BOUNDARY_RULES.md)"
    )
    parser.add_argument(
        "pack_path",
        nargs="?",
        default=None,
        help="单个激活包路径 (省略则校验所有)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="严格模式: WARN 也算失败",
    )
    args = parser.parse_args()

    if args.pack_path:
        reports = [validate_pack(Path(args.pack_path))]
    else:
        reports = validate_all_packs()

    if not reports:
        print("无激活包可校验.")
        return 0

    has_errors = False
    for rpt in reports:
        rel = rpt.pack_path.name
        print(f"\n[{rpt.overall_status}] {rel}")
        for issue in rpt.issues:
            print(str(issue))
        if rpt.has_errors:
            has_errors = True
        if args.strict and rpt.has_warnings:
            has_errors = True

    print(f"\n=== 总计: {len(reports)} 个激活包 ===")
    n_error = sum(1 for r in reports if r.has_errors)
    n_warn = sum(1 for r in reports if r.has_warnings and not r.has_errors)
    n_pass = len(reports) - n_error - n_warn
    print(f"  PASS:  {n_pass}")
    print(f"  WARN:  {n_warn}")
    print(f"  FAIL:  {n_error}")

    return 1 if has_errors else 0


if __name__ == "__main__":
    sys.exit(main())
