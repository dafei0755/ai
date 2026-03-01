"""
P3 能力验证数据收集测试

目标：
1. 运行10个代表性场景
2. 收集真实能力验证数据
3. 分析验证通过率、失败模式、质量问题
4. 生成优化建议

测试流程：
场景加载 → 模拟专家输出 → 能力验证 → 数据聚合 → 分析报告
"""

import sys
import yaml
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from collections import defaultdict, Counter

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from intelligent_project_analyzer.services.ability_validator import AbilityValidator
from intelligent_project_analyzer.utils.ability_query import AbilityQueryTool


class P3ValidationDataCollector:
    """P3验证数据收集器"""

    def __init__(self, scenarios_path: Path):
        self.scenarios_path = scenarios_path
        self.scenarios = self._load_scenarios()
        self.ability_tool = AbilityQueryTool()
        self.validator = AbilityValidator()
        self.validation_reports = []
        self.raw_data = []

    def _load_scenarios(self) -> List[Dict[str, Any]]:
        """加载测试场景"""
        with open(self.scenarios_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return config["scenarios"]

    def _generate_mock_expert_output(
        self, scenario: Dict[str, Any], expert_id: str, quality_level: str = "good"
    ) -> Dict[str, Any]:
        """
        生成模拟专家输出

        Args:
            scenario: 场景配置
            expert_id: 专家ID
            quality_level: 质量等级 ["excellent", "good", "fair", "poor"]

        Returns:
            模拟的专家输出结构
        """
        # 获取场景预期能力
        expected_abilities = scenario.get("expected_abilities", {})
        primary_abilities = expected_abilities.get("primary", [])

        # 基础输出结构
        output = {
            "scenario_id": scenario["scenario_id"],
            "expert_id": expert_id,
            "project_name": scenario["project_name"],
            "mode": scenario["mode"],
            "quality_level": quality_level,
        }

        # 根据质量等级生成不同完整度的输出
        if quality_level == "excellent":
            # 90-100%完整度：所有字段+关键词
            output.update(self._generate_complete_output(primary_abilities, 1.0))
        elif quality_level == "good":
            # 75-90%完整度：大部分字段+部分关键词
            output.update(self._generate_complete_output(primary_abilities, 0.85))
        elif quality_level == "fair":
            # 60-75%完整度：部分字段+少量关键词
            output.update(self._generate_complete_output(primary_abilities, 0.68))
        else:  # poor
            # <60%完整度：缺失关键字段和关键词
            output.update(self._generate_complete_output(primary_abilities, 0.45))

        return output

    def _generate_complete_output(self, abilities: List[str], completeness: float) -> Dict[str, Any]:
        """
        根据能力列表和完整度生成输出

        Args:
            abilities: 能力ID列表
            completeness: 完整度 (0.0-1.0)

        Returns:
            输出字典
        """
        output = {}

        # A1 概念建构能力
        if "A1" in abilities:
            fields = (
                {}
                if completeness < 0.3
                else {
                    "conceptual_foundation": {
                        "core_concept": "核心概念：空间作为时间的容器" if completeness > 0.5 else None,
                        "philosophical_framework": "哲学框架：现象学空间理论，海德格尔的'居住'概念" if completeness > 0.7 else None,
                        "spatial_interpretation": "空间诠释：通过材料的时间性表达记忆的堆叠" if completeness > 0.6 else None,
                        "concept_structure": "概念结构：压缩-释放-回归的三段式逻辑" if completeness > 0.4 else None,
                    }
                }
            )
            # 移除None值
            if fields and "conceptual_foundation" in fields:
                fields["conceptual_foundation"] = {
                    k: v for k, v in fields["conceptual_foundation"].items() if v is not None
                }
            output.update(fields)

        # A9 社会关系建模能力
        if "A9" in abilities:
            fields = (
                {}
                if completeness < 0.3
                else {
                    "social_structure_analysis": {
                        "power_distance_model": "权力距离模型：采用Hofstede权力距离理论，空间中心为长辈区域" if completeness > 0.6 else None,
                        "privacy_hierarchy": "隐私层级：公共区→半公共区→半私密区→完全私密区四级隐私体系" if completeness > 0.7 else None,
                        "conflict_buffer_design": "冲突缓冲设计：灰空间作为情绪缓冲带，独立入口系统避免强制交互" if completeness > 0.5 else None,
                        "evolution_adaptability": "演化适应性：可拆分房间，未来10年适配家庭变化" if completeness > 0.4 else None,
                        "intergenerational_balance": "代际平衡：垂直分层而非平面分区，减少代际冲突" if completeness > 0.8 else None,
                    }
                }
            )
            # 移除None值
            if fields and "social_structure_analysis" in fields:
                fields["social_structure_analysis"] = {
                    k: v for k, v in fields["social_structure_analysis"].items() if v is not None
                }
            output.update(fields)

        # A10 环境适应能力
        if "A10" in abilities:
            fields = (
                {}
                if completeness < 0.3
                else {
                    "environmental_adaptation_analysis": {
                        "climate_analysis": "气候分析：年均温-5℃，温差40℃，需三层保温系统。关键词：气候" if completeness > 0.6 else None,
                        "structural_resistance": "结构抗性：8级风压，雪载150kg/㎡，钢结构+木包覆。关键词：抗性" if completeness > 0.7 else None,
                        "material_adaptation": "材料适应：本地石材（抗冻）+碳化木（防腐）+LOW-E玻璃。关键词：材料，适应"
                        if completeness > 0.5
                        else None,
                        "energy_system": "能源系统：地源热泵+太阳能辅助，低能耗供暖。关键词：能源" if completeness > 0.4 else None,
                        "comfort_assurance": "舒适保障：新风系统+温湿度自动调节，室内恒温20℃" if completeness > 0.8 else None,
                    }
                }
            )
            # 移除None值
            if fields and "environmental_adaptation_analysis" in fields:
                fields["environmental_adaptation_analysis"] = {
                    k: v for k, v in fields["environmental_adaptation_analysis"].items() if v is not None
                }
            output.update(fields)

        # A3 叙事节奏能力
        if "A3" in abilities:
            fields = (
                {}
                if completeness < 0.3
                else {
                    "narrative_rhythm": {
                        "compression_phase": "压缩阶段：入口狭窄，天花2.2米，制造压迫感" if completeness > 0.6 else None,
                        "release_phase": "释放阶段：大堂天花6米，视线打开，情绪释放" if completeness > 0.7 else None,
                        "climax_phase": "高潮阶段：中庭自然光顶，成为空间焦点" if completeness > 0.5 else None,
                    }
                }
            )
            if fields and "narrative_rhythm" in fields:
                fields["narrative_rhythm"] = {k: v for k, v in fields["narrative_rhythm"].items() if v is not None}
            output.update(fields)

        # A4 材料系统能力
        if "A4" in abilities:
            materials_list = []
            if completeness > 0.5:
                materials_list.append("木材")
            if completeness > 0.6:
                materials_list.append("石材")
            if completeness > 0.7:
                materials_list.append("混凝土")
            if completeness > 0.8:
                materials_list.append("金属")

            if materials_list:
                output["material_system"] = {
                    "materials": materials_list,
                    "description": f"材料系统包含{len(materials_list)}种主材：{', '.join(materials_list)}",
                }

        # A6 功能效率能力
        if "A6" in abilities:
            if completeness > 0.5:
                output["functional_optimization"] = {
                    "circulation_efficiency": "动线效率：主动线单一，次动线分离，无交叉冲突" if completeness > 0.7 else None,
                    "space_utilization": "空间利用率：85%，无效空间<10%" if completeness > 0.6 else None,
                    "interference_control": "干扰控制：声学分区，视觉隔离，气味控制" if completeness > 0.5 else None,
                }
                output["functional_optimization"] = {
                    k: v for k, v in output["functional_optimization"].items() if v is not None
                }

        # A7 资本策略能力
        if "A7" in abilities:
            if completeness > 0.5:
                output["capital_strategy"] = {
                    "target_client": "目标客群：高净值家庭，资产规模1000万+" if completeness > 0.6 else None,
                    "revenue_model": "收益模型：销售溢价30%，年租金回报6%" if completeness > 0.7 else None,
                    "cost_control": "成本控制：建安成本5000元/㎡，5年回收" if completeness > 0.5 else None,
                }
                output["capital_strategy"] = {k: v for k, v in output["capital_strategy"].items() if v is not None}

        # A8 技术整合能力
        if "A8" in abilities:
            if completeness > 0.5:
                output["technology_integration"] = {
                    "smart_systems": "智能系统：全屋智能，系统隐形化设计" if completeness > 0.6 else None,
                    "automation_level": "自动化等级：L3级，数据反馈驱动" if completeness > 0.7 else None,
                    "future_interface": "未来接口：预留模块化升级接口" if completeness > 0.5 else None,
                }
                output["technology_integration"] = {
                    k: v for k, v in output["technology_integration"].items() if v is not None
                }

        # A11 运营与产品化能力
        if "A11" in abilities:
            if completeness > 0.5:
                output["operation_strategy"] = {
                    "operation_model": "运营模型：自营+委托管理混合模式" if completeness > 0.6 else None,
                    "service_system": "服务体系：三级服务标准，客户满意度>90%" if completeness > 0.7 else None,
                    "scalability": "可复制性：标准化模块，可异地复制" if completeness > 0.5 else None,
                }
                output["operation_strategy"] = {k: v for k, v in output["operation_strategy"].items() if v is not None}

        return output

    def run_scenario_validation(
        self, scenario: Dict[str, Any], quality_distribution: Dict[str, float] = None
    ) -> List[Dict[str, Any]]:
        """
        运行单个场景的验证测试

        Args:
            scenario: 场景配置
            quality_distribution: 质量分布 {"excellent": 0.2, "good": 0.5, "fair": 0.2, "poor": 0.1}

        Returns:
            验证报告列表
        """
        if quality_distribution is None:
            quality_distribution = {
                "excellent": 0.2,  # 20%优秀
                "good": 0.5,  # 50%良好
                "fair": 0.2,  # 20%合格
                "poor": 0.1,  # 10%不合格
            }

        scenario_reports = []
        expected_experts = scenario.get("expected_experts", [])

        print(f"\n{'='*80}")
        print(f"🎬 场景: {scenario['scenario_id']} - {scenario['project_name']}")
        print(f"   模式: {scenario['mode']}")
        print(f"   预期专家: {', '.join(expected_experts)}")
        print(f"{'='*80}\n")

        # 为每个预期专家生成不同质量的输出并验证
        for expert_id in expected_experts:
            # 获取专家能力配置
            expert_profile = self.ability_tool.get_expert_abilities(expert_id)

            if not expert_profile:
                print(f"⚠️ 专家 {expert_id} 没有能力配置，跳过")
                continue

            # 合并primary和secondary能力
            declared_abilities = []
            if expert_profile.primary:
                for ability in expert_profile.primary:
                    declared_abilities.append(
                        {"id": ability.id, "maturity_level": ability.maturity_level, "confidence": ability.confidence}
                    )
            if expert_profile.secondary:
                for ability in expert_profile.secondary:
                    declared_abilities.append(
                        {"id": ability.id, "maturity_level": ability.maturity_level, "confidence": ability.confidence}
                    )

            # 测试不同质量等级
            for quality_level in quality_distribution.keys():
                # 生成模拟输出
                mock_output = self._generate_mock_expert_output(scenario, expert_id, quality_level)

                # 执行验证
                validation_report = self.validator.validate_expert_output(
                    expert_id=expert_id, output=mock_output, declared_abilities=declared_abilities
                )

                # 记录原始数据
                self.raw_data.append(
                    {
                        "scenario_id": scenario["scenario_id"],
                        "scenario_name": scenario["project_name"],
                        "mode": scenario["mode"],
                        "expert_id": expert_id,
                        "quality_level": quality_level,
                        "validation_report": validation_report,
                    }
                )

                # 打印结果
                status = "✅" if validation_report.overall_passed else "❌"
                print(f"{status} {expert_id} [{quality_level}]: {validation_report.overall_score:.1%}")

                scenario_reports.append(validation_report)

        return scenario_reports

    def collect_all_data(self):
        """收集所有场景的验证数据"""
        print("\n🚀 开始P3验证数据收集")
        print(f"   场景总数: {len(self.scenarios)}")
        print(f"   预计测试: {sum(len(s.get('expected_experts', [])) for s in self.scenarios)} × 4质量等级\n")

        for scenario in self.scenarios:
            reports = self.run_scenario_validation(scenario)
            self.validation_reports.extend(reports)

        print("\n✅ 数据收集完成")
        print(f"   验证报告总数: {len(self.validation_reports)}")

    def analyze_data(self) -> Dict[str, Any]:
        """分析收集的验证数据"""
        print("\n📊 开始数据分析...\n")

        analysis = {
            "timestamp": datetime.now().isoformat(),
            "total_validations": len(self.validation_reports),
            "overall_statistics": {},
            "mode_analysis": {},
            "ability_analysis": {},
            "quality_analysis": {},
            "failure_patterns": {},
            "recommendations": [],
        }

        # 1. 整体统计
        passed_count = sum(1 for r in self.validation_reports if r.overall_passed)
        analysis["overall_statistics"] = {
            "total_reports": len(self.validation_reports),
            "passed_count": passed_count,
            "failed_count": len(self.validation_reports) - passed_count,
            "pass_rate": passed_count / len(self.validation_reports) if self.validation_reports else 0,
            "average_score": sum(r.overall_score for r in self.validation_reports) / len(self.validation_reports)
            if self.validation_reports
            else 0,
        }

        print("整体统计:")
        print(f"  通过率: {analysis['overall_statistics']['pass_rate']:.1%}")
        print(f"  平均分: {analysis['overall_statistics']['average_score']:.1%}\n")

        # 2. 按模式分析
        mode_data = defaultdict(lambda: {"reports": [], "scores": []})
        for data in self.raw_data:
            mode = data["mode"]
            report = data["validation_report"]
            mode_data[mode]["reports"].append(report)
            mode_data[mode]["scores"].append(report.overall_score)

        for mode, data in mode_data.items():
            passed = sum(1 for r in data["reports"] if r.overall_passed)
            analysis["mode_analysis"][mode] = {
                "total": len(data["reports"]),
                "passed": passed,
                "pass_rate": passed / len(data["reports"]),
                "average_score": sum(data["scores"]) / len(data["scores"]),
            }

        print("模式分析:")
        for mode, stats in sorted(analysis["mode_analysis"].items()):
            print(f"  {mode}: {stats['pass_rate']:.1%} (avg: {stats['average_score']:.1%})")
        print()

        # 3. 按能力分析
        ability_checks = defaultdict(lambda: {"total": 0, "passed": 0, "scores": []})
        for report in self.validation_reports:
            for ability_result in report.abilities_validated:
                aid = ability_result.ability_id
                ability_checks[aid]["total"] += 1
                if ability_result.passed:
                    ability_checks[aid]["passed"] += 1
                ability_checks[aid]["scores"].append(ability_result.overall_score)

        for aid, data in ability_checks.items():
            analysis["ability_analysis"][aid] = {
                "total_checks": data["total"],
                "passed_checks": data["passed"],
                "pass_rate": data["passed"] / data["total"] if data["total"] > 0 else 0,
                "average_score": sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0,
            }

        print("能力分析:")
        for aid, stats in sorted(analysis["ability_analysis"].items()):
            print(f"  {aid}: {stats['pass_rate']:.1%} (avg: {stats['average_score']:.1%}, n={stats['total_checks']})")
        print()

        # 4. 按质量等级分析
        quality_data = defaultdict(lambda: {"reports": [], "scores": []})
        for data in self.raw_data:
            quality = data["quality_level"]
            report = data["validation_report"]
            quality_data[quality]["reports"].append(report)
            quality_data[quality]["scores"].append(report.overall_score)

        for quality, data in quality_data.items():
            passed = sum(1 for r in data["reports"] if r.overall_passed)
            analysis["quality_analysis"][quality] = {
                "total": len(data["reports"]),
                "passed": passed,
                "pass_rate": passed / len(data["reports"]),
                "average_score": sum(data["scores"]) / len(data["scores"]),
            }

        print("质量等级分析:")
        for quality in ["excellent", "good", "fair", "poor"]:
            if quality in analysis["quality_analysis"]:
                stats = analysis["quality_analysis"][quality]
                print(f"  {quality}: {stats['pass_rate']:.1%} (avg: {stats['average_score']:.1%})")
        print()

        # 5. 失败模式分析
        missing_fields_counter = Counter()
        missing_keywords_counter = Counter()
        failed_checks_counter = Counter()

        for report in self.validation_reports:
            for ability_result in report.abilities_validated:
                missing_fields_counter.update(ability_result.missing_fields)
                missing_keywords_counter.update(ability_result.missing_keywords)
                for check in ability_result.checks:
                    if not check.passed:
                        failed_checks_counter[f"{ability_result.ability_id}:{check.check_name}"] += 1

        analysis["failure_patterns"] = {
            "top_missing_fields": dict(missing_fields_counter.most_common(10)),
            "top_missing_keywords": dict(missing_keywords_counter.most_common(10)),
            "top_failed_checks": dict(failed_checks_counter.most_common(10)),
        }

        print("失败模式分析:")
        print("  高频缺失字段 (Top 5):")
        for field, count in list(missing_fields_counter.most_common(5)):
            print(f"    {field}: {count}次")
        print("  高频缺失关键词 (Top 5):")
        for keyword, count in list(missing_keywords_counter.most_common(5)):
            print(f"    {keyword}: {count}次")
        print("  高频失败检查 (Top 5):")
        for check, count in list(failed_checks_counter.most_common(5)):
            print(f"    {check}: {count}次")
        print()

        # 6. 生成优化建议
        recommendations = []

        # 基于整体通过率的建议
        overall_pass_rate = analysis["overall_statistics"]["pass_rate"]
        if overall_pass_rate < 0.7:
            recommendations.append(
                {
                    "priority": "高",
                    "category": "整体质量",
                    "issue": f"整体通过率仅{overall_pass_rate:.1%}，低于70%目标",
                    "suggestion": "建议全面检查专家system_prompt，确保明确要求输出能力相关内容",
                }
            )

        # 基于能力分析的建议
        low_score_abilities = [
            (aid, stats) for aid, stats in analysis["ability_analysis"].items() if stats["average_score"] < 0.7
        ]
        if low_score_abilities:
            ability_list = ", ".join([aid for aid, _ in low_score_abilities[:3]])
            recommendations.append(
                {
                    "priority": "中",
                    "category": "能力质量",
                    "issue": f"以下能力平均分<70%: {ability_list}",
                    "suggestion": "建议优化这些能力对应专家的输出结构，增强相关字段和关键词",
                }
            )

        # 基于失败检查的建议
        if failed_checks_counter:
            top_failed_check, count = failed_checks_counter.most_common(1)[0]
            total_validations = len(self.validation_reports)
            failure_rate = count / total_validations
            if failure_rate > 0.3:
                recommendations.append(
                    {
                        "priority": "中",
                        "category": "验证规则",
                        "issue": f"检查项'{top_failed_check}'失败率{failure_rate:.1%}，超过30%",
                        "suggestion": "建议降低该检查项阈值或优化专家输出指导",
                    }
                )

        # 基于模式分析的建议
        low_pass_modes = [
            (mode, stats) for mode, stats in analysis["mode_analysis"].items() if stats["pass_rate"] < 0.7
        ]
        if low_pass_modes:
            mode_list = ", ".join([mode for mode, _ in low_pass_modes])
            recommendations.append(
                {
                    "priority": "中",
                    "category": "模式适配",
                    "issue": f"以下模式通过率<70%: {mode_list}",
                    "suggestion": "建议检查这些模式对应专家的能力声明是否准确，可能需要补充能力",
                }
            )

        analysis["recommendations"] = recommendations

        print("优化建议:")
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. [{rec['priority']}] {rec['category']}: {rec['issue']}")
            print(f"     → {rec['suggestion']}")
        print()

        return analysis

    def save_results(self, output_dir: Path):
        """保存分析结果"""
        output_dir.mkdir(parents=True, exist_ok=True)

        # 1. 保存原始数据
        raw_data_path = output_dir / "p3_raw_validation_data.json"
        with open(raw_data_path, "w", encoding="utf-8") as f:
            # 转换ExpertValidationReport为dict
            serializable_data = []
            for item in self.raw_data:
                report = item["validation_report"]
                serializable_item = {
                    "scenario_id": item["scenario_id"],
                    "scenario_name": item["scenario_name"],
                    "mode": item["mode"],
                    "expert_id": item["expert_id"],
                    "quality_level": item["quality_level"],
                    "validation_report": {
                        "expert_id": report.expert_id,
                        "timestamp": report.timestamp,
                        "overall_passed": report.overall_passed,
                        "overall_score": report.overall_score,
                        "abilities_validated": [
                            {
                                "ability_id": ability.ability_id,
                                "passed": ability.passed,
                                "overall_score": ability.overall_score,
                                "checks": [
                                    {
                                        "check_name": check.check_name,
                                        "passed": check.passed,
                                        "score": check.score,
                                        "threshold": check.threshold,
                                        "message": check.message,
                                    }
                                    for check in ability.checks
                                ],
                                "missing_fields": ability.missing_fields,
                                "missing_keywords": ability.missing_keywords,
                            }
                            for ability in report.abilities_validated
                        ],
                        "summary": report.summary,
                    },
                }
                serializable_data.append(serializable_item)

            json.dump(serializable_data, f, ensure_ascii=False, indent=2)
        print(f"✅ 原始数据已保存: {raw_data_path}")

        # 2. 分析数据
        analysis = self.analyze_data()

        # 3. 保存分析报告 (JSON)
        analysis_json_path = output_dir / "p3_analysis_report.json"
        with open(analysis_json_path, "w", encoding="utf-8") as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)
        print(f"✅ 分析报告(JSON)已保存: {analysis_json_path}")

        # 4. 保存分析报告 (TXT)
        analysis_txt_path = output_dir / "p3_analysis_report.txt"
        with open(analysis_txt_path, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write("P3 能力验证数据分析报告\n")
            f.write("=" * 80 + "\n\n")

            f.write(f"生成时间: {analysis['timestamp']}\n")
            f.write(f"验证总数: {analysis['total_validations']}\n\n")

            f.write("一、整体统计\n")
            f.write("-" * 80 + "\n")
            stats = analysis["overall_statistics"]
            f.write(f"通过率: {stats['pass_rate']:.1%}\n")
            f.write(f"平均分: {stats['average_score']:.1%}\n")
            f.write(f"通过数: {stats['passed_count']}/{stats['total_reports']}\n\n")

            f.write("二、模式分析\n")
            f.write("-" * 80 + "\n")
            for mode, stats in sorted(analysis["mode_analysis"].items()):
                f.write(f"{mode}:\n")
                f.write(f"  通过率: {stats['pass_rate']:.1%}\n")
                f.write(f"  平均分: {stats['average_score']:.1%}\n")
                f.write(f"  统计量: {stats['passed']}/{stats['total']}\n\n")

            f.write("三、能力分析\n")
            f.write("-" * 80 + "\n")
            for aid, stats in sorted(analysis["ability_analysis"].items()):
                f.write(f"{aid}:\n")
                f.write(f"  通过率: {stats['pass_rate']:.1%}\n")
                f.write(f"  平均分: {stats['average_score']:.1%}\n")
                f.write(f"  检查次数: {stats['passed_checks']}/{stats['total_checks']}\n\n")

            f.write("四、质量等级分析\n")
            f.write("-" * 80 + "\n")
            for quality in ["excellent", "good", "fair", "poor"]:
                if quality in analysis["quality_analysis"]:
                    stats = analysis["quality_analysis"][quality]
                    f.write(f"{quality}:\n")
                    f.write(f"  通过率: {stats['pass_rate']:.1%}\n")
                    f.write(f"  平均分: {stats['average_score']:.1%}\n")
                    f.write(f"  统计量: {stats['passed']}/{stats['total']}\n\n")

            f.write("五、失败模式分析\n")
            f.write("-" * 80 + "\n")
            patterns = analysis["failure_patterns"]

            f.write("高频缺失字段 (Top 10):\n")
            for field, count in patterns["top_missing_fields"].items():
                f.write(f"  {field}: {count}次\n")
            f.write("\n")

            f.write("高频缺失关键词 (Top 10):\n")
            for keyword, count in patterns["top_missing_keywords"].items():
                f.write(f"  {keyword}: {count}次\n")
            f.write("\n")

            f.write("高频失败检查 (Top 10):\n")
            for check, count in patterns["top_failed_checks"].items():
                f.write(f"  {check}: {count}次\n")
            f.write("\n")

            f.write("六、优化建议\n")
            f.write("-" * 80 + "\n")
            for i, rec in enumerate(analysis["recommendations"], 1):
                f.write(f"{i}. [{rec['priority']}] {rec['category']}\n")
                f.write(f"   问题: {rec['issue']}\n")
                f.write(f"   建议: {rec['suggestion']}\n\n")

        print(f"✅ 分析报告(TXT)已保存: {analysis_txt_path}")

        return analysis


def main():
    """主函数"""
    # 路径配置
    project_root = Path(__file__).parent.parent.parent
    scenarios_path = project_root / "tests" / "fixtures" / "p3_validation_scenarios.yaml"
    output_dir = project_root / "tests" / "results" / "p3_validation_data"

    # 创建收集器
    collector = P3ValidationDataCollector(scenarios_path)

    # 收集数据
    collector.collect_all_data()

    # 保存结果
    collector.save_results(output_dir)

    print(f"\n{'='*80}")
    print("🎉 P3数据收集与分析完成！")
    print(f"   结果目录: {output_dir}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
