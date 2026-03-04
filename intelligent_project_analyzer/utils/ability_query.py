"""
能力查询工具（Ability Query Tool）
===================================

本模块提供能力查询、专家匹配、覆盖率分析等工具函数，用于：
1. 查询专家的能力声明
2. 根据能力查找合适的专家
3. 生成能力覆盖报告
4. 分析能力覆盖缺口

创建日期: 2026-02-12
版本: v1.0
作者: Ability Core P1 Implementation
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List

import yaml

from intelligent_project_analyzer.utils.ability_schemas import (
    ABILITY_NAMES,
    AbilityCoverageReport,
    AbilityID,
    AbilityMaturityLevel,
    ExpertAbilityProfile,
    SystemAbilityCoverageReport,
    get_coverage_status,
    maturity_level_to_numeric,
)


class AbilityQueryTool:
    """
    能力查询工具类

    提供以下功能：
    - 加载所有专家配置文件
    - 查询专家的能力声明
    - 根据能力查找专家
    - 生成能力覆盖报告
    """

    def __init__(self, config_dir: Path | None = None):
        """
        初始化能力查询工具

        Args:
            config_dir: 专家配置文件目录路径，默认为项目标准路径
        """
        if config_dir is None:
            # 默认路径：intelligent_project_analyzer/config/roles/
            project_root = Path(__file__).parent.parent.parent
            config_dir = project_root / "intelligent_project_analyzer" / "config" / "roles"

        self.config_dir = config_dir
        self._expert_configs = {}
        self._load_all_configs()

    def _load_all_configs(self) -> None:
        """加载所有专家配置文件"""
        if not self.config_dir.exists():
            raise FileNotFoundError(f"配置目录不存在: {self.config_dir}")

        yaml_files = list(self.config_dir.glob("*.yaml"))

        for yaml_file in yaml_files:
            try:
                with open(yaml_file, encoding="utf-8") as f:
                    config = yaml.safe_load(f)

                    # 提取专家ID（从文件名或配置中）
                    expert_id = yaml_file.stem  # 如 v2_design_director
                    self._expert_configs[expert_id] = config

            except Exception as e:
                print(f"⚠️  加载配置文件失败: {yaml_file.name} - {e}")

        print(f"✅ 成功加载 {len(self._expert_configs)} 个专家配置文件")

    def get_expert_abilities(self, expert_id: str) -> ExpertAbilityProfile | None:
        """
        获取专家的能力声明

        Args:
            expert_id: 专家ID（如 'v7_emotional_insight_expert'）

        Returns:
            ExpertAbilityProfile 或 None（如果专家不存在或未声明能力）
        """
        config = self._expert_configs.get(expert_id)
        if not config:
            return None

        # 遍历配置文件中的所有角色定义
        for key, value in config.items():
            if isinstance(value, dict) and "core_abilities" in value:
                try:
                    return ExpertAbilityProfile(**value["core_abilities"])
                except Exception as e:
                    print(f"⚠️  解析能力声明失败: {expert_id} - {e}")
                    return None

        return None

    def find_experts_by_ability(
        self, ability_id: AbilityID, min_level: AbilityMaturityLevel = "L1", include_secondary: bool = True
    ) -> Dict[str, List[str]]:
        """
        根据能力查找专家

        Args:
            ability_id: 能力ID（如 'A9'）
            min_level: 最低成熟度要求（默认L1）
            include_secondary: 是否包含辅助能力专家（默认True）

        Returns:
            {"primary": [...], "secondary": [...]}
        """
        min_level_numeric = maturity_level_to_numeric(min_level)
        primary_experts = []
        secondary_experts = []

        for expert_id, config in self._expert_configs.items():
            abilities = self.get_expert_abilities(expert_id)
            if not abilities:
                continue

            # 检查主能力
            for ability in abilities.primary:
                if ability.id == ability_id and maturity_level_to_numeric(ability.maturity_level) >= min_level_numeric:
                    primary_experts.append(expert_id)
                    break

            # 检查辅助能力
            if include_secondary:
                for ability in abilities.secondary:
                    if (
                        ability.id == ability_id
                        and maturity_level_to_numeric(ability.maturity_level) >= min_level_numeric
                    ):
                        secondary_experts.append(expert_id)
                        break

        return {"primary": primary_experts, "secondary": secondary_experts}

    def get_ability_coverage_report(self) -> SystemAbilityCoverageReport:
        """
        生成完整的能力覆盖报告

        Returns:
            SystemAbilityCoverageReport - 包含所有12个能力的覆盖情况
        """
        abilities_reports = []

        # 预期专家数量（可根据实际调整）
        EXPECTED_EXPERT_COUNT = {
            "A1": 3,  # 概念建构：V2, V3, V4
            "A2": 2,  # 空间结构：V2, V6-1
            "A3": 2,  # 叙事节奏：V3, V7
            "A4": 2,  # 材料系统：V6-3, V6-1
            "A5": 1,  # 灯光系统：V6-5
            "A6": 2,  # 功能效率：V6-1, V6-2
            "A7": 2,  # 资本策略：V2, V6-4
            "A8": 2,  # 技术整合：V6-2, V4
            "A9": 2,  # 社会关系建模：V7, V3
            "A10": 3,  # 环境适应：V6-1, V6-2, V6-3
            "A11": 2,  # 运营产品化：V5, V2
            "A12": 2,  # 文明表达：V4, V2
        }

        for ability_id in ABILITY_NAMES.keys():
            experts = self.find_experts_by_ability(ability_id, min_level="L1")

            primary_experts = experts["primary"]
            secondary_experts = experts["secondary"]
            total_experts = len(primary_experts) + len(secondary_experts)

            # 计算平均成熟度
            maturity_sum = 0
            maturity_count = 0

            for expert_id in primary_experts + secondary_experts:
                abilities = self.get_expert_abilities(expert_id)
                if abilities:
                    for ability in abilities.primary + abilities.secondary:
                        if ability.id == ability_id:
                            maturity_sum += maturity_level_to_numeric(ability.maturity_level)
                            maturity_count += 1

            avg_maturity = maturity_sum / maturity_count if maturity_count > 0 else 0.0

            # 计算覆盖率
            expected_count = EXPECTED_EXPERT_COUNT.get(ability_id, 2)
            coverage_rate = min(1.0, total_experts / expected_count)

            abilities_reports.append(
                AbilityCoverageReport(
                    ability_id=ability_id,
                    ability_name=ABILITY_NAMES[ability_id],
                    expert_count=total_experts,
                    primary_experts=primary_experts,
                    secondary_experts=secondary_experts,
                    average_maturity_level=avg_maturity,
                    coverage_rate=coverage_rate,
                    coverage_status=get_coverage_status(coverage_rate),
                )
            )

        # 计算整体覆盖率
        overall_coverage = sum(r.coverage_rate for r in abilities_reports) / len(abilities_reports)

        # 找出弱覆盖和严重缺口
        weak_abilities = [r.ability_id for r in abilities_reports if r.coverage_rate < 0.7]
        critical_abilities = [r.ability_id for r in abilities_reports if r.coverage_rate < 0.5]

        return SystemAbilityCoverageReport(
            report_date=datetime.now().strftime("%Y-%m-%d"),
            total_experts=len(self._expert_configs),
            abilities=abilities_reports,
            overall_coverage_rate=overall_coverage,
            weak_abilities=weak_abilities,
            critical_abilities=critical_abilities,
        )

    def print_coverage_report(self) -> None:
        """打印能力覆盖报告（格式化输出）"""
        report = self.get_ability_coverage_report()

        print("\n" + "=" * 80)
        print(f"{'12 Ability Core 能力覆盖报告':^80}")
        print("=" * 80)
        print(f"报告日期: {report.report_date}")
        print(f"专家总数: {report.total_experts}")
        print(f"整体覆盖率: {report.overall_coverage_rate:.1%}")
        print("=" * 80)

        print(f"\n{'能力ID':<6} {'能力名称':<45} {'专家数':<8} {'覆盖率':<8} {'状态':<10}")
        print("-" * 80)

        for ability in report.abilities:
            status_icon = {
                "excellent": "✅ 优秀",
                "good": "✅ 良好",
                "fair": "⚠️  一般",
                "weak": "⚠️  偏弱",
                "critical": "❌ 严重",
            }.get(ability.coverage_status, "❓")

            print(
                f"{ability.ability_id:<6} "
                f"{ability.ability_name:<45} "
                f"{ability.expert_count:<8} "
                f"{ability.coverage_rate:<7.1%} "
                f"{status_icon:<10}"
            )

        print("=" * 80)

        if report.critical_abilities:
            print(f"\n❌ 严重缺口能力: {', '.join(report.critical_abilities)}")

        if report.weak_abilities:
            print(f"\n⚠️  覆盖偏弱能力: {', '.join(report.weak_abilities)}")

        print("\n" + "=" * 80)


# ============================================================================
# 快捷函数
# ============================================================================


def query_expert_abilities(expert_id: str) -> ExpertAbilityProfile | None:
    """查询专家能力（快捷函数）"""
    tool = AbilityQueryTool()
    return tool.get_expert_abilities(expert_id)


def find_experts_with_ability(ability_id: AbilityID, min_level: AbilityMaturityLevel = "L3") -> Dict[str, List[str]]:
    """查找拥有某能力的专家（快捷函数）"""
    tool = AbilityQueryTool()
    return tool.find_experts_by_ability(ability_id, min_level)


def generate_coverage_report() -> SystemAbilityCoverageReport:
    """生成能力覆盖报告（快捷函数）"""
    tool = AbilityQueryTool()
    return tool.get_ability_coverage_report()


def print_coverage_report() -> None:
    """打印能力覆盖报告（快捷函数）"""
    tool = AbilityQueryTool()
    tool.print_coverage_report()


# ============================================================================
# CLI 入口
# ============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "report":
        # 运行: python ability_query.py report
        print_coverage_report()
    else:
        # 默认：显示使用说明
        print("能力查询工具 (Ability Query Tool)")
        print("=" * 50)
        print("\n使用方法:")
        print("  python ability_query.py report    # 生成覆盖报告")
        print("\nPython API:")
        print("  from ability_query import query_expert_abilities")
        print("  from ability_query import find_experts_with_ability")
        print("  from ability_query import generate_coverage_report")
