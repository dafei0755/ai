"""
能力验证报告生成器 (Ability Validation Report Generator)

生成能力验证的聚合报告，用于系统级监控和优化决策。

创建日期: 2026-02-12
版本: v1.0
"""

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..services.ability_validator import AbilityValidator, ExpertValidationReport
from ..utils.ability_query import AbilityQueryTool


class ValidationReportGenerator:
    """
    能力验证报告生成器

    功能：
    1. 聚合多个专家的验证结果
    2. 生成系统级统计报告
    3. 识别能力缺口和质量问题
    4. 生成优化建议
    """

    def __init__(self):
        self.validator = AbilityValidator()
        self.ability_tool = AbilityQueryTool()

    def generate_session_report(
        self, validation_reports: List[ExpertValidationReport], session_id: str, output_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        生成会话级别的验证报告

        Args:
            validation_reports: 多个专家的验证报告列表
            session_id: 会话ID
            output_dir: 报告输出目录（可选）

        Returns:
            Dict: 聚合报告
        """
        if not validation_reports:
            return {"session_id": session_id, "timestamp": datetime.now().isoformat(), "error": "无验证报告"}

        report = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "experts_count": len(validation_reports),
            "overall_statistics": self._calculate_overall_statistics(validation_reports),
            "ability_statistics": self._calculate_ability_statistics(validation_reports),
            "expert_rankings": self._rank_experts(validation_reports),
            "quality_issues": self._identify_quality_issues(validation_reports),
            "recommendations": self._generate_recommendations(validation_reports),
        }

        # 如果指定了输出目录，保存报告
        if output_dir:
            self._save_report(report, output_dir, session_id)

        return report

    def _calculate_overall_statistics(self, validation_reports: List[ExpertValidationReport]) -> Dict[str, Any]:
        """计算整体统计数据"""
        total_experts = len(validation_reports)
        passed_experts = sum(1 for r in validation_reports if r.overall_passed)
        total_score = sum(r.overall_score for r in validation_reports)

        # 收集所有能力验证结果
        all_ability_scores = []
        for report in validation_reports:
            all_ability_scores.extend([a.overall_score for a in report.abilities_validated])

        return {
            "total_experts": total_experts,
            "experts_passed": passed_experts,
            "experts_failed": total_experts - passed_experts,
            "expert_pass_rate": passed_experts / total_experts if total_experts > 0 else 0.0,
            "average_expert_score": total_score / total_experts if total_experts > 0 else 0.0,
            "average_ability_score": sum(all_ability_scores) / len(all_ability_scores) if all_ability_scores else 0.0,
            "total_abilities_checked": len(all_ability_scores),
            "score_distribution": self._calculate_score_distribution(all_ability_scores),
        }

    def _calculate_score_distribution(self, scores: List[float]) -> Dict[str, int]:
        """计算分数分布"""
        distribution = {"优秀(≥90%)": 0, "良好(75-90%)": 0, "合格(60-75%)": 0, "不合格(<60%)": 0}

        for score in scores:
            if score >= 0.90:
                distribution["优秀(≥90%)"] += 1
            elif score >= 0.75:
                distribution["良好(75-90%)"] += 1
            elif score >= 0.60:
                distribution["合格(60-75%)"] += 1
            else:
                distribution["不合格(<60%)"] += 1

        return distribution

    def _calculate_ability_statistics(self, validation_reports: List[ExpertValidationReport]) -> Dict[str, Any]:
        """计算各能力的统计数据"""
        ability_stats = defaultdict(lambda: {"total_checks": 0, "passed_checks": 0, "scores": [], "experts": []})

        for report in validation_reports:
            for ability_result in report.abilities_validated:
                ability_id = ability_result.ability_id
                ability_stats[ability_id]["total_checks"] += 1
                if ability_result.passed:
                    ability_stats[ability_id]["passed_checks"] += 1
                ability_stats[ability_id]["scores"].append(ability_result.overall_score)
                ability_stats[ability_id]["experts"].append(report.expert_id)

        # 转换为最终统计格式
        result = {}
        for ability_id, stats in ability_stats.items():
            scores = stats["scores"]
            result[ability_id] = {
                "ability_name": self._get_ability_name(ability_id),
                "total_checks": stats["total_checks"],
                "passed_checks": stats["passed_checks"],
                "pass_rate": stats["passed_checks"] / stats["total_checks"] if stats["total_checks"] > 0 else 0.0,
                "average_score": sum(scores) / len(scores) if scores else 0.0,
                "min_score": min(scores) if scores else 0.0,
                "max_score": max(scores) if scores else 0.0,
                "expert_count": len(set(stats["experts"])),
            }

        # 按平均分数排序
        result = dict(sorted(result.items(), key=lambda x: x[1]["average_score"], reverse=True))

        return result

    def _rank_experts(self, validation_reports: List[ExpertValidationReport]) -> List[Dict[str, Any]]:
        """对专家进行排名"""
        rankings = []

        for report in validation_reports:
            rankings.append(
                {
                    "expert_id": report.expert_id,
                    "overall_score": report.overall_score,
                    "passed": report.overall_passed,
                    "abilities_count": len(report.abilities_validated),
                    "abilities_passed": sum(1 for a in report.abilities_validated if a.passed),
                    "pass_rate": sum(1 for a in report.abilities_validated if a.passed)
                    / len(report.abilities_validated)
                    if report.abilities_validated
                    else 0.0,
                }
            )

        # 按overall_score降序排序
        rankings.sort(key=lambda x: x["overall_score"], reverse=True)

        # 添加排名
        for idx, ranking in enumerate(rankings, 1):
            ranking["rank"] = idx

        return rankings

    def _identify_quality_issues(self, validation_reports: List[ExpertValidationReport]) -> List[Dict[str, Any]]:
        """识别质量问题"""
        issues = []

        for report in validation_reports:
            # 检查专家整体评分
            if report.overall_score < 0.60:
                issues.append(
                    {
                        "severity": "严重",
                        "type": "专家整体评分过低",
                        "expert_id": report.expert_id,
                        "score": report.overall_score,
                        "description": f"{report.expert_id} 整体评分仅{report.overall_score:.1%}，低于60%阈值",
                    }
                )

            # 检查单个能力
            for ability_result in report.abilities_validated:
                if not ability_result.passed:
                    issues.append(
                        {
                            "severity": "中等" if ability_result.overall_score >= 0.50 else "严重",
                            "type": "能力验证不通过",
                            "expert_id": report.expert_id,
                            "ability_id": ability_result.ability_id,
                            "score": ability_result.overall_score,
                            "missing_fields": ability_result.missing_fields[:3],
                            "missing_keywords": ability_result.missing_keywords[:3],
                            "description": f"{report.expert_id} 的 {ability_result.ability_id} 能力验证失败 ({ability_result.overall_score:.1%})",
                        }
                    )

        # 按严重程度排序
        severity_order = {"严重": 0, "中等": 1, "轻微": 2}
        issues.sort(key=lambda x: (severity_order.get(x["severity"], 3), -x["score"]))

        return issues

    def _generate_recommendations(self, validation_reports: List[ExpertValidationReport]) -> List[str]:
        """生成优化建议"""
        recommendations = []

        # 计算整体统计
        overall_stats = self._calculate_overall_statistics(validation_reports)
        ability_stats = self._calculate_ability_statistics(validation_reports)

        # 建议1: 整体通过率低
        if overall_stats["expert_pass_rate"] < 0.70:
            recommendations.append(f"⚠️ 专家整体通过率仅{overall_stats['expert_pass_rate']:.1%}，" f"建议检查提示词是否明确要求输出能力相关内容")

        # 建议2: 识别低分能力
        low_score_abilities = [(aid, stats) for aid, stats in ability_stats.items() if stats["average_score"] < 0.70]
        if low_score_abilities:
            ability_list = ", ".join([aid for aid, _ in low_score_abilities[:3]])
            recommendations.append(f"⚠️ 以下能力平均分较低: {ability_list}，" f"建议优化对应专家的system_prompt以强化这些能力的输出")

        # 建议3: 识别高失败率的检查项
        common_failures = defaultdict(int)
        for report in validation_reports:
            for ability_result in report.abilities_validated:
                for check in ability_result.checks:
                    if not check.passed:
                        common_failures[check.check_name] += 1

        if common_failures:
            most_common = max(common_failures.items(), key=lambda x: x[1])
            check_name, fail_count = most_common
            if fail_count >= len(validation_reports) * 0.3:  # 30%以上专家失败
                recommendations.append(f"⚠️ '{check_name}' 检查项失败率较高({fail_count}次)，" f"建议调整验证规则阈值或增强专家输出指导")

        # 建议4: 优秀案例推荐
        excellent_experts = [report.expert_id for report in validation_reports if report.overall_score >= 0.90]
        if excellent_experts:
            recommendations.append(f"✅ 以下专家表现优秀: {', '.join(excellent_experts[:3])}，" f"可作为配置参考模板")

        # 如果没有任何问题，给出正面反馈
        if not recommendations:
            recommendations.append("✅ 所有专家能力验证表现良好，系统运行正常")

        return recommendations

    def _get_ability_name(self, ability_id: str) -> str:
        """获取能力名称"""
        ability_names = {
            "A1": "Concept Architecture",
            "A2": "Spatial Structuring",
            "A3": "Narrative Orchestration",
            "A4": "Material Intelligence",
            "A5": "Lighting Architecture",
            "A6": "Functional Optimization",
            "A7": "Capital Strategy Intelligence",
            "A8": "Technology Integration",
            "A9": "Social Structure Modeling",
            "A10": "Environmental Adaptation",
            "A11": "Operation & Productization",
            "A12": "Civilizational Expression",
        }
        return ability_names.get(ability_id, ability_id)

    def generate_session_report_from_dicts(
        self, validation_dicts: List[Dict[str, Any]], session_id: str, output_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        从原始字典列表生成会话级别的验证报告。

        当 ability_validation 以 dict 形式存储在 agent_results 中时使用此方法，
        避免需要重新构造 ExpertValidationReport 对象。

        Args:
            validation_dicts: 能力验证结果的字典列表（来自 execute_expert 的 result["ability_validation"]）
            session_id: 会话ID
            output_dir: 报告输出目录（可选）

        Returns:
            Dict: 聚合报告
        """
        if not validation_dicts:
            return {"session_id": session_id, "timestamp": datetime.now().isoformat(), "error": "无验证报告"}

        # 从 dict 中提取统计数据
        total_experts = len(validation_dicts)
        passed_experts = sum(1 for d in validation_dicts if d.get("overall_passed", False))
        total_score = sum(d.get("overall_score", 0) for d in validation_dicts)

        # 收集能力级别数据
        all_ability_scores = []
        ability_stats_raw = defaultdict(lambda: {"total": 0, "passed": 0, "scores": [], "experts": []})

        expert_rankings = []
        quality_issues = []

        for vd in validation_dicts:
            expert_id = vd.get("expert_id", "unknown")
            abilities = vd.get("abilities_validated", [])

            abilities_passed = 0
            for ab in abilities:
                if isinstance(ab, dict):
                    aid = ab.get("ability_id", "")
                    score = ab.get("overall_score", 0)
                    passed = ab.get("passed", False)
                else:
                    aid = getattr(ab, "ability_id", "")
                    score = getattr(ab, "overall_score", 0)
                    passed = getattr(ab, "passed", False)

                all_ability_scores.append(score)
                ability_stats_raw[aid]["total"] += 1
                if passed:
                    ability_stats_raw[aid]["passed"] += 1
                    abilities_passed += 1
                ability_stats_raw[aid]["scores"].append(score)
                ability_stats_raw[aid]["experts"].append(expert_id)

                if not passed:
                    missing_fields = (
                        ab.get("missing_fields", []) if isinstance(ab, dict) else getattr(ab, "missing_fields", [])
                    )
                    missing_keywords = (
                        ab.get("missing_keywords", []) if isinstance(ab, dict) else getattr(ab, "missing_keywords", [])
                    )
                    quality_issues.append(
                        {
                            "severity": "中等" if score >= 0.50 else "严重",
                            "type": "能力验证不通过",
                            "expert_id": expert_id,
                            "ability_id": aid,
                            "score": score,
                            "missing_fields": (missing_fields or [])[:3],
                            "missing_keywords": (missing_keywords or [])[:3],
                            "description": f"{expert_id} 的 {aid} 能力验证失败 ({score:.1%})",
                        }
                    )

            expert_rankings.append(
                {
                    "expert_id": expert_id,
                    "overall_score": vd.get("overall_score", 0),
                    "passed": vd.get("overall_passed", False),
                    "abilities_count": len(abilities),
                    "abilities_passed": abilities_passed,
                    "pass_rate": abilities_passed / len(abilities) if abilities else 0.0,
                }
            )

            if vd.get("overall_score", 0) < 0.60:
                quality_issues.append(
                    {
                        "severity": "严重",
                        "type": "专家整体评分过低",
                        "expert_id": expert_id,
                        "score": vd.get("overall_score", 0),
                        "description": f"{expert_id} 整体评分仅{vd.get('overall_score', 0):.1%}，低于60%阈值",
                    }
                )

        expert_rankings.sort(key=lambda x: x["overall_score"], reverse=True)
        for idx, r in enumerate(expert_rankings, 1):
            r["rank"] = idx

        severity_order = {"严重": 0, "中等": 1}
        quality_issues.sort(key=lambda x: (severity_order.get(x["severity"], 2), -x.get("score", 0)))

        # 构建能力统计
        ability_statistics = {}
        for aid, stats in ability_stats_raw.items():
            scores = stats["scores"]
            ability_statistics[aid] = {
                "ability_name": self._get_ability_name(aid),
                "total_checks": stats["total"],
                "passed_checks": stats["passed"],
                "pass_rate": stats["passed"] / stats["total"] if stats["total"] > 0 else 0.0,
                "average_score": sum(scores) / len(scores) if scores else 0.0,
                "min_score": min(scores) if scores else 0.0,
                "max_score": max(scores) if scores else 0.0,
                "expert_count": len(set(stats["experts"])),
            }
        ability_statistics = dict(sorted(ability_statistics.items(), key=lambda x: x[1]["average_score"], reverse=True))

        # 生成建议
        recommendations = []
        pass_rate = passed_experts / total_experts if total_experts > 0 else 0
        if pass_rate < 0.70:
            recommendations.append(f"专家整体通过率仅{pass_rate:.1%}，建议检查提示词是否明确要求输出能力相关内容")
        low_abilities = [aid for aid, s in ability_statistics.items() if s["average_score"] < 0.70]
        if low_abilities:
            recommendations.append(f"以下能力平均分较低: {', '.join(low_abilities[:3])}，建议优化对应专家的system_prompt")
        if not recommendations:
            recommendations.append("所有专家能力验证表现良好，系统运行正常")

        report = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "experts_count": total_experts,
            "overall_statistics": {
                "total_experts": total_experts,
                "experts_passed": passed_experts,
                "experts_failed": total_experts - passed_experts,
                "expert_pass_rate": pass_rate,
                "average_expert_score": total_score / total_experts if total_experts > 0 else 0.0,
                "average_ability_score": sum(all_ability_scores) / len(all_ability_scores)
                if all_ability_scores
                else 0.0,
                "total_abilities_checked": len(all_ability_scores),
                "score_distribution": self._calculate_score_distribution(all_ability_scores),
            },
            "ability_statistics": ability_statistics,
            "expert_rankings": expert_rankings,
            "quality_issues": quality_issues,
            "recommendations": recommendations,
        }

        if output_dir:
            self._save_report(report, output_dir, session_id)

        return report

    def _save_report(self, report: Dict[str, Any], output_dir: Path, session_id: str):
        """保存报告到文件"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # JSON格式
        json_path = output_dir / f"validation_report_{session_id}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        # 文本格式（可读性更好）
        txt_path = output_dir / f"validation_report_{session_id}.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            self._write_text_report(f, report)

    def _write_text_report(self, f, report: Dict[str, Any]):
        """写入文本格式报告"""
        f.write("=" * 80 + "\n")
        f.write(f"能力验证聚合报告 - Session: {report['session_id']}\n")
        f.write("=" * 80 + "\n")
        f.write(f"生成时间: {report['timestamp']}\n")
        f.write(f"专家数量: {report['experts_count']}\n\n")

        # 整体统计
        stats = report["overall_statistics"]
        f.write("【整体统计】\n")
        f.write("-" * 80 + "\n")
        f.write(f"专家通过率: {stats['expert_pass_rate']:.1%} " f"({stats['experts_passed']}/{stats['total_experts']})\n")
        f.write(f"平均专家评分: {stats['average_expert_score']:.1%}\n")
        f.write(f"平均能力评分: {stats['average_ability_score']:.1%}\n")
        f.write(f"能力检查次数: {stats['total_abilities_checked']}\n\n")

        f.write("分数分布:\n")
        for level, count in stats["score_distribution"].items():
            f.write(f"  {level}: {count}\n")
        f.write("\n")

        # 能力统计
        f.write("【能力统计】\n")
        f.write("-" * 80 + "\n")
        ability_stats = report["ability_statistics"]
        for ability_id, data in list(ability_stats.items())[:12]:  # 最多显示12个能力
            status = "✅" if data["pass_rate"] >= 0.75 else "⚠️" if data["pass_rate"] >= 0.60 else "❌"
            f.write(f"{status} {ability_id} - {data['ability_name']}\n")
            f.write(
                f"   通过率: {data['pass_rate']:.1%}, "
                f"平均分: {data['average_score']:.1%}, "
                f"检查次数: {data['total_checks']}\n"
            )
        f.write("\n")

        # 专家排名
        f.write("【专家排名】\n")
        f.write("-" * 80 + "\n")
        for ranking in report["expert_rankings"][:10]:  # 最多显示前10名
            status = "✅" if ranking["passed"] else "❌"
            f.write(
                f"{status} 第{ranking['rank']}名: {ranking['expert_id']} - "
                f"{ranking['overall_score']:.1%} "
                f"({ranking['abilities_passed']}/{ranking['abilities_count']}能力通过)\n"
            )
        f.write("\n")

        # 质量问题
        if report["quality_issues"]:
            f.write("【质量问题】\n")
            f.write("-" * 80 + "\n")
            for issue in report["quality_issues"][:10]:  # 最多显示前10个问题
                f.write(f"[{issue['severity']}] {issue['description']}\n")
                if "missing_keywords" in issue and issue["missing_keywords"]:
                    f.write(f"  缺失关键词: {', '.join(issue['missing_keywords'])}\n")
            f.write("\n")

        # 优化建议
        f.write("【优化建议】\n")
        f.write("-" * 80 + "\n")
        for idx, recommendation in enumerate(report["recommendations"], 1):
            f.write(f"{idx}. {recommendation}\n")
        f.write("\n")

        f.write("=" * 80 + "\n")

    def print_session_report(self, report: Dict[str, Any]):
        """打印会话报告到控制台"""
        print("\n" + "=" * 80)
        print(f"📊 能力验证聚合报告 - Session: {report['session_id']}")
        print("=" * 80)

        stats = report["overall_statistics"]
        print(f"\n整体通过率: {stats['expert_pass_rate']:.1%} " f"({stats['experts_passed']}/{stats['total_experts']}专家)")
        print(f"平均专家评分: {stats['average_expert_score']:.1%}")
        print(f"平均能力评分: {stats['average_ability_score']:.1%}")

        if report["quality_issues"]:
            print(f"\n⚠️  发现 {len(report['quality_issues'])} 个质量问题")
            for issue in report["quality_issues"][:5]:  # 显示前5个
                print(f"  [{issue['severity']}] {issue['description']}")

        print("\n【优化建议】")
        for idx, rec in enumerate(report["recommendations"], 1):
            print(f"{idx}. {rec}")

        print("=" * 80 + "\n")


# 快捷函数
def generate_validation_report(
    validation_reports: List[ExpertValidationReport],
    session_id: str,
    output_dir: Optional[Path] = None,
    print_report: bool = True,
) -> Dict[str, Any]:
    """
    生成验证报告的快捷函数

    Args:
        validation_reports: 验证报告列表
        session_id: 会话ID
        output_dir: 输出目录（可选）
        print_report: 是否打印到控制台

    Returns:
        Dict: 聚合报告
    """
    generator = ValidationReportGenerator()
    report = generator.generate_session_report(validation_reports, session_id, output_dir)

    if print_report:
        generator.print_session_report(report)

    return report
