"""
能力验证器 (Ability Validator)

验证专家输出是否真正体现了宣称的能力。
包括字段完整性、关键词密度、理论框架等多维度检查。

创建日期: 2026-02-12
版本: v1.0
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

import yaml


@dataclass
class ValidationCheck:
    """单个验证检查结果"""

    check_name: str
    passed: bool
    score: float
    threshold: float
    details: Dict[str, Any] = field(default_factory=dict)
    message: str = ""


@dataclass
class AbilityValidationResult:
    """单个能力的验证结果"""

    ability_id: str
    ability_name: str
    passed: bool
    overall_score: float
    checks: List[ValidationCheck] = field(default_factory=list)
    missing_fields: List[str] = field(default_factory=list)
    missing_keywords: List[str] = field(default_factory=list)


@dataclass
class ExpertValidationReport:
    """专家输出的完整验证报告"""

    expert_id: str
    timestamp: str
    overall_passed: bool
    overall_score: float
    abilities_validated: List[AbilityValidationResult] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)


class AbilityValidator:
    """
    能力验证器

    功能：
    1. 加载验证规则
    2. 验证专家输出是否匹配声明能力
    3. 生成详细验证报告
    4. 根据成熟度等级调整验证阈值
    """

    def __init__(self, rules_path: Path | None = None):
        """
        初始化验证器

        Args:
            rules_path: 验证规则文件路径，如果为None则使用默认路径
        """
        if rules_path is None:
            rules_path = Path(__file__).parent.parent / "config" / "ability_verification_rules.yaml"

        self.rules_path = rules_path
        self.rules = self._load_rules()
        self.global_settings = self.rules.get("global_settings", {})
        self._detected_modes = []  # NEW v7.750: 用于存储检测到的设计模式

    def set_detected_modes(self, detected_modes: List[Dict[str, Any]]):
        """
        设置检测到的设计模式（用于模式验证）

        Args:
            detected_modes: 检测到的模式列表 [{"mode": "M1_concept_driven", "confidence": 0.85}, ...]

        使用方式:
            validator = AbilityValidator()
            validator.set_detected_modes(state.get("detected_design_modes", []))
            report = validator.validate_expert_output(...)
        """
        self._detected_modes = detected_modes

    def _load_rules(self) -> Dict[str, Any]:
        """加载验证规则"""
        try:
            with open(self.rules_path, encoding="utf-8") as f:
                rules = yaml.safe_load(f)
            return rules
        except Exception as e:
            print(f"⚠️  加载验证规则失败: {e}")
            return {}

    def validate_expert_output(
        self, expert_id: str, output: Dict[str, Any], declared_abilities: List[Dict[str, Any]]
    ) -> ExpertValidationReport:
        """
        验证专家输出

        Args:
            expert_id: 专家ID
            output: 专家输出内容（字典格式）
            declared_abilities: 声明的能力列表，每个包含id, maturity_level等

        Returns:
            ExpertValidationReport: 验证报告
        """
        from datetime import datetime

        report = ExpertValidationReport(
            expert_id=expert_id, timestamp=datetime.now().isoformat(), overall_passed=True, overall_score=0.0
        )

        total_score = 0.0
        ability_count = 0

        for ability_decl in declared_abilities:
            ability_id = ability_decl.get("id", "")
            maturity_level = ability_decl.get("maturity_level", "L3")

            # 跳过没有验证规则的能力
            rule_key = self._get_rule_key(ability_id)
            if rule_key not in self.rules:
                continue

            # 验证该能力
            ability_result = self._validate_ability(
                ability_id=ability_id, output=output, rules=self.rules[rule_key], maturity_level=maturity_level
            )

            report.abilities_validated.append(ability_result)
            total_score += ability_result.overall_score
            ability_count += 1

            if not ability_result.passed:
                report.overall_passed = False

        # 计算整体分数
        if ability_count > 0:
            report.overall_score = total_score / ability_count

        # ═══════════════════════════════════════════════════════════
        # NEW v7.750 P1: 模式特征验证（Layer 4增强）
        # ═══════════════════════════════════════════════════════════
        # 如果在验证上下文中提供了detected_modes，执行模式验证
        mode_validation_results = []
        if hasattr(self, "_detected_modes") and self._detected_modes:
            try:
                from .mode_validation_loader import validate_mode_features

                # 提取输出文本（用于关键词匹配）
                output_text = self._extract_text_from_output(output)

                # 执行模式验证
                mode_validation_results = validate_mode_features(
                    detected_modes=self._detected_modes, expert_output=output_text
                )

                # 将模式验证结果添加到报告摘要
                report.summary["mode_validations"] = [
                    {
                        "mode_id": result.mode_id,
                        "mode_name": result.mode_name,
                        "passed": result.passed,
                        "score": result.score,
                        "missing_features": result.missing_features,
                        "summary": result.validation_summary,
                    }
                    for result in mode_validation_results
                ]

                # 如果有模式验证失败，记录警告（但不阻塞）
                failed_modes = [r for r in mode_validation_results if not r.passed]
                if failed_modes:
                    report.summary["mode_validation_warnings"] = [
                        f"{r.mode_name}: {r.validation_summary}" for r in failed_modes
                    ]

            except Exception as e:
                print(f"⚠️  模式验证失败: {e}")
                report.summary["mode_validation_error"] = str(e)
        # ═══════════════════════════════════════════════════════════

        # 生成摘要
        report.summary.update(self._generate_summary(report))

        return report

    def _validate_ability(
        self, ability_id: str, output: Dict[str, Any], rules: Dict[str, Any], maturity_level: str = "L3"
    ) -> AbilityValidationResult:
        """
        验证单个能力

        Args:
            ability_id: 能力ID
            output: 专家输出
            rules: 该能力的验证规则
            maturity_level: 成熟度等级

        Returns:
            AbilityValidationResult: 该能力的验证结果
        """
        result = AbilityValidationResult(
            ability_id=ability_id, ability_name=rules.get("description", ability_id), passed=True, overall_score=0.0
        )

        # 获取调整后的阈值
        thresholds = self._get_adjusted_thresholds(maturity_level)

        # 1. 检查必需字段
        if "required_fields" in rules:
            field_check = self._check_required_fields(output, rules["required_fields"])
            result.checks.append(field_check)
            result.missing_fields = field_check.details.get("missing_fields", [])
            if not field_check.passed:
                result.passed = False

        # 2. 检查关键词
        if "required_keywords" in rules:
            keyword_check = self._check_keywords(
                output, rules["required_keywords"], threshold=thresholds.get("keyword_density", 0.015)
            )
            result.checks.append(keyword_check)
            result.missing_keywords = keyword_check.details.get("missing_keywords", [])
            if not keyword_check.passed:
                result.passed = False

        # 3. 质量检查
        for quality_rule in rules.get("quality_checks", []):
            check_result = self._run_quality_check(output, quality_rule, thresholds)
            result.checks.append(check_result)
            if not check_result.passed:
                result.passed = False

        # 计算整体分数
        if result.checks:
            result.overall_score = sum(c.score for c in result.checks) / len(result.checks)

        return result

    def _check_required_fields(self, output: Dict[str, Any], required_fields: Dict[str, Any]) -> ValidationCheck:
        """检查必需字段是否存在"""
        missing_fields = []
        total_fields = 0
        found_fields = 0

        def check_nested(data: Any, fields: Any, path: str = ""):
            nonlocal total_fields, found_fields

            if isinstance(fields, dict):
                for field_name, sub_fields in fields.items():
                    total_fields += 1
                    full_path = f"{path}.{field_name}" if path else field_name

                    if isinstance(data, dict) and field_name in data:
                        found_fields += 1
                        if sub_fields:
                            check_nested(data[field_name], sub_fields, full_path)
                    else:
                        missing_fields.append(full_path)

            elif isinstance(fields, list):
                for sub_field in fields:
                    total_fields += 1
                    full_path = f"{path}.{sub_field}" if path else sub_field

                    if isinstance(data, dict) and sub_field in data:
                        found_fields += 1
                    else:
                        missing_fields.append(full_path)

        check_nested(output, required_fields)

        # 计算完成度
        completeness = found_fields / total_fields if total_fields > 0 else 0.0
        threshold = 0.75  # 默认阈值

        return ValidationCheck(
            check_name="required_fields",
            passed=completeness >= threshold,
            score=completeness,
            threshold=threshold,
            details={
                "missing_fields": missing_fields,
                "found_fields": found_fields,
                "total_fields": total_fields,
                "completeness": completeness,
            },
            message=f"字段完整性: {completeness:.1%} (阈值: {threshold:.1%})",
        )

    def _check_keywords(self, output: Dict[str, Any], keywords: List[str], threshold: float = 0.015) -> ValidationCheck:
        """检查关键词密度"""
        # 将output转换为文本
        text = self._extract_text_from_output(output)
        text_length = len(text)

        if text_length == 0:
            return ValidationCheck(
                check_name="keyword_density",
                passed=False,
                score=0.0,
                threshold=threshold,
                details={"reason": "输出为空"},
                message="无法检查关键词：输出为空",
            )

        # 统计每个关键词出现次数
        keyword_counts = {}
        missing_keywords = []
        total_keyword_chars = 0

        for keyword in keywords:
            count = text.count(keyword)
            keyword_counts[keyword] = count
            total_keyword_chars += count * len(keyword)

            if count == 0:
                missing_keywords.append(keyword)

        # 计算关键词密度
        density = total_keyword_chars / text_length if text_length > 0 else 0.0

        return ValidationCheck(
            check_name="keyword_density",
            passed=density >= threshold,
            score=min(density / threshold, 1.0) if threshold > 0 else 1.0,
            threshold=threshold,
            details={
                "keyword_counts": keyword_counts,
                "missing_keywords": missing_keywords,
                "text_length": text_length,
                "density": density,
            },
            message=f"关键词密度: {density:.2%} (阈值: {threshold:.2%})",
        )

    def _run_quality_check(
        self, output: Dict[str, Any], quality_rule: Dict[str, Any], thresholds: Dict[str, float]
    ) -> ValidationCheck:
        """运行质量检查"""
        check_type = quality_rule.get("check", "")

        if check_type == "field_completeness":
            threshold = quality_rule.get("threshold", thresholds.get("field_completeness", 0.75))
            return ValidationCheck(
                check_name="field_completeness",
                passed=True,  # 已在required_fields检查中处理
                score=1.0,
                threshold=threshold,
                message=quality_rule.get("description", "字段完整性检查"),
            )

        elif check_type == "keyword_density":
            # 已在_check_keywords中处理
            return ValidationCheck(
                check_name="keyword_density",
                passed=True,
                score=1.0,
                threshold=0.015,
                message=quality_rule.get("description", "关键词密度检查"),
            )

        elif check_type == "depth_score":
            text = self._extract_text_from_output(output)
            min_length = quality_rule.get("min_length", 500)
            actual_length = len(text)

            return ValidationCheck(
                check_name="depth_score",
                passed=actual_length >= min_length,
                score=min(actual_length / min_length, 1.0) if min_length > 0 else 1.0,
                threshold=min_length,
                details={"actual_length": actual_length, "min_length": min_length},
                message=f"内容深度: {actual_length}字符 (最低: {min_length}字符)",
            )

        elif check_type == "rhythm_analysis":
            # 检查是否包含节奏控制阶段
            required_phases = quality_rule.get("required_phases", [])
            text = self._extract_text_from_output(output)

            found_phases = [phase for phase in required_phases if phase in text]
            completeness = len(found_phases) / len(required_phases) if required_phases else 1.0

            return ValidationCheck(
                check_name="rhythm_analysis",
                passed=completeness >= 0.8,
                score=completeness,
                threshold=0.8,
                details={"required_phases": required_phases, "found_phases": found_phases},
                message=f"节奏分析: {len(found_phases)}/{len(required_phases)}个阶段",
            )

        elif check_type == "material_count":
            min_materials = quality_rule.get("min_materials", 3)
            # 简化检查：统计"材料"关键词附近的材质名称
            text = self._extract_text_from_output(output)
            material_keywords = ["木材", "石材", "金属", "玻璃", "混凝土", "砖", "涂料", "陶瓷"]
            found_materials = [m for m in material_keywords if m in text]

            return ValidationCheck(
                check_name="material_count",
                passed=len(found_materials) >= min_materials,
                score=min(len(found_materials) / min_materials, 1.0),
                threshold=min_materials,
                details={"found_materials": found_materials, "count": len(found_materials)},
                message=f"材料分析: {len(found_materials)}种材料 (最低: {min_materials}种)",
            )

        elif check_type == "theoretical_framework":
            required_theories = quality_rule.get("required_theories", [])
            text = self._extract_text_from_output(output)

            found_theories = [theory for theory in required_theories if theory in text]
            completeness = len(found_theories) / len(required_theories) if required_theories else 1.0

            return ValidationCheck(
                check_name="theoretical_framework",
                passed=completeness >= 0.5,  # 至少50%理论框架
                score=completeness,
                threshold=0.5,
                details={"required_theories": required_theories, "found_theories": found_theories},
                message=f"理论框架: {len(found_theories)}/{len(required_theories)}个理论",
            )

        elif check_type == "dimension_completeness":
            required_dimensions = quality_rule.get("required_dimensions", [])
            text = self._extract_text_from_output(output)

            found_dimensions = [dim for dim in required_dimensions if dim in text]
            completeness = len(found_dimensions) / len(required_dimensions) if required_dimensions else 1.0
            threshold = quality_rule.get("threshold", 1.0)

            return ValidationCheck(
                check_name="dimension_completeness",
                passed=completeness >= threshold,
                score=completeness,
                threshold=threshold,
                details={"required_dimensions": required_dimensions, "found_dimensions": found_dimensions},
                message=f"维度完整性: {len(found_dimensions)}/{len(required_dimensions)}个维度",
            )

        elif check_type == "financial_metrics":
            required_metrics = quality_rule.get("required_metrics", [])
            text = self._extract_text_from_output(output)

            found_metrics = [metric for metric in required_metrics if metric in text]
            completeness = len(found_metrics) / len(required_metrics) if required_metrics else 1.0

            return ValidationCheck(
                check_name="financial_metrics",
                passed=completeness >= 0.8,
                score=completeness,
                threshold=0.8,
                details={"required_metrics": required_metrics, "found_metrics": found_metrics},
                message=f"财务指标: {len(found_metrics)}/{len(required_metrics)}个指标",
            )

        # 未知检查类型
        return ValidationCheck(
            check_name=check_type, passed=True, score=1.0, threshold=0.0, message=f"未实现的检查类型: {check_type}"
        )

    def _extract_text_from_output(self, output: Any) -> str:
        """从输出中提取文本内容"""
        if isinstance(output, str):
            return output
        elif isinstance(output, dict):
            texts = []
            for value in output.values():
                texts.append(self._extract_text_from_output(value))
            return " ".join(texts)
        elif isinstance(output, list):
            texts = []
            for item in output:
                texts.append(self._extract_text_from_output(item))
            return " ".join(texts)
        else:
            return str(output)

    def _get_rule_key(self, ability_id: str) -> str:
        """获取规则键名"""
        # A1 -> A1_concept_architecture
        ability_names = {
            "A1": "A1_concept_architecture",
            "A2": "A2_spatial_structuring",
            "A3": "A3_narrative_orchestration",
            "A4": "A4_material_intelligence",
            "A5": "A5_lighting_architecture",
            "A6": "A6_functional_optimization",
            "A7": "A7_capital_strategy_intelligence",
            "A8": "A8_technology_integration",
            "A9": "A9_social_structure_modeling",
            "A10": "A10_environmental_adaptation",
            "A11": "A11_operation_productization",
            "A12": "A12_civilizational_expression",
        }
        return ability_names.get(ability_id, ability_id)

    def _get_adjusted_thresholds(self, maturity_level: str) -> Dict[str, float]:
        """根据成熟度等级调整阈值"""
        maturity_thresholds = self.global_settings.get("maturity_thresholds", {})
        level_config = maturity_thresholds.get(maturity_level, {})

        # 返回调整后的阈值（使用默认值作为基准）
        return {
            "field_completeness": level_config.get("field_completeness", 0.75) / 100,
            "keyword_density": level_config.get("keyword_density", 1.0) * 0.015,
        }

    def _generate_summary(self, report: ExpertValidationReport) -> Dict[str, Any]:
        """生成验证摘要"""
        total_abilities = len(report.abilities_validated)
        passed_abilities = sum(1 for a in report.abilities_validated if a.passed)

        return {
            "total_abilities_checked": total_abilities,
            "abilities_passed": passed_abilities,
            "abilities_failed": total_abilities - passed_abilities,
            "pass_rate": passed_abilities / total_abilities if total_abilities > 0 else 0.0,
            "overall_score": report.overall_score,
            "recommendation": self._get_recommendation(report),
        }

    def _get_recommendation(self, report: ExpertValidationReport) -> str:
        """获取建议"""
        if report.overall_score >= 0.90:
            return "✅ 优秀 - 能力体现充分"
        elif report.overall_score >= 0.75:
            return "✔️  良好 - 能力基本体现"
        elif report.overall_score >= 0.60:
            return "⚠️  合格 - 建议增强能力表达"
        else:
            return "❌ 不合格 - 需要重新生成或调整专家配置"

    def print_report(self, report: ExpertValidationReport, verbose: bool = False):
        """打印验证报告"""
        print("\n" + "=" * 80)
        print(f"📋 能力验证报告 - {report.expert_id}")
        print("=" * 80)
        print(f"时间: {report.timestamp}")
        print(f"整体状态: {'✅ 通过' if report.overall_passed else '❌ 失败'}")
        print(f"整体评分: {report.overall_score:.1%}")
        print(f"建议: {report.summary.get('recommendation', '')}")
        print()

        print("能力验证详情:")
        print("-" * 80)

        for ability_result in report.abilities_validated:
            status_icon = "✅" if ability_result.passed else "❌"
            print(f"{status_icon} {ability_result.ability_id} - {ability_result.ability_name}")
            print(f"   评分: {ability_result.overall_score:.1%}")

            if verbose or not ability_result.passed:
                for check in ability_result.checks:
                    check_icon = "✓" if check.passed else "✗"
                    print(f"     {check_icon} {check.message}")

                if ability_result.missing_fields:
                    print(f"     缺失字段: {', '.join(ability_result.missing_fields[:3])}")
                if ability_result.missing_keywords:
                    print(f"     缺失关键词: {', '.join(ability_result.missing_keywords[:3])}")
            print()

        print("=" * 80)


# 快捷函数
def validate_expert(
    expert_id: str,
    output: Dict[str, Any],
    declared_abilities: List[Dict[str, Any]],
    print_result: bool = True,
    verbose: bool = False,
) -> ExpertValidationReport:
    """
    验证专家输出的快捷函数

    Args:
        expert_id: 专家ID
        output: 专家输出
        declared_abilities: 声明的能力列表
        print_result: 是否打印结果
        verbose: 是否详细输出

    Returns:
        ExpertValidationReport: 验证报告
    """
    validator = AbilityValidator()
    report = validator.validate_expert_output(expert_id, output, declared_abilities)

    if print_result:
        validator.print_report(report, verbose=verbose)

    return report
