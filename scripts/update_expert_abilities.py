"""
批量更新专家配置文件 - 添加能力声明
======================================

本脚本用于批量更新 V2-V7 所有专家配置文件，添加 core_abilities 字段。

创建日期: 2026-02-12
版本: v1.0
作者: Ability Core P1 Implementation
"""

import yaml
import sys
from pathlib import Path
from typing import Dict, Any


# ============================================================================
# 专家能力映射配置
# ============================================================================

EXPERT_ABILITIES_MAPPING = {
    "v7_emotional_insight_expert": {
        "primary": [
            {
                "id": "A9",
                "name": "Social Structure Modeling",
                "maturity_level": "L4",
                "sub_abilities": [
                    "A9-1_power_distance",
                    "A9-2_privacy_hierarchy",
                    "A9-3_conflict_buffer",
                    "A9-4_evolution_adaptability",
                ],
                "confidence": 0.9,
                "focus": "多代同堂住宅、再婚家庭、合租大平层、联合办公、养老社区",
                "note": "V7专家核心能力，填补12 Ability Core中A9社会关系建模的系统性缺口",
            },
            {
                "id": "A3",
                "name": "Narrative Orchestration",
                "maturity_level": "L3",
                "confidence": 0.8,
                "focus": "情绪节奏、五感调动、记忆锚点",
                "note": "通过叙事节奏强化社会关系的空间表达",
            },
        ],
        "secondary": [
            {
                "id": "A1",
                "name": "Concept Architecture",
                "maturity_level": "L2",
                "confidence": 0.6,
                "focus": "人性关怀主题、社会关系概念化",
                "note": "辅助将社会关系转译为概念主线",
            }
        ],
    },
    "v6_5_lighting_engineer": {
        "primary": [
            {
                "id": "A5",
                "name": "Lighting Architecture",
                "maturity_level": "L4",
                "sub_abilities": [
                    "A5-1_natural_lighting",
                    "A5-2_artificial_lighting_system",
                    "A5-3_lighting_scene_design",
                    "A5-4_energy_efficiency",
                ],
                "confidence": 0.95,
                "focus": "灯光系统设计、照明场景、智能控制",
                "note": "V6-5独立配置，专注A5灯光系统能力",
            }
        ],
        "secondary": [
            {
                "id": "A3",
                "name": "Narrative Orchestration",
                "maturity_level": "L3",
                "confidence": 0.75,
                "focus": "灯光与叙事节奏结合",
                "note": "通过灯光强化空间情绪",
            }
        ],
    },
    "v6_chief_engineer": {
        "primary": [
            {
                "id": "A2",
                "name": "Spatial Structuring",
                "maturity_level": "L5",
                "confidence": 0.95,
                "focus": "结构力学、空间形态实现",
                "note": "V6-1核心能力，结构工程师",
            },
            {
                "id": "A6",
                "name": "Functional Optimization",
                "maturity_level": "L4",
                "confidence": 0.9,
                "focus": "功能效率、MEP系统优化",
                "note": "V6-1/V6-2核心能力，功能性优化",
            },
            {
                "id": "A8",
                "name": "Technology Integration",
                "maturity_level": "L5",
                "confidence": 0.95,
                "focus": "MEP系统整合、智能化技术",
                "note": "V6-2核心能力，技术系统专家",
            },
            {
                "id": "A10",
                "name": "Environmental Adaptation",
                "maturity_level": "L4",
                "sub_abilities": ["A10-1_climate_analysis", "A10-2_envelope_integration", "A10-3_energy_coordination"],
                "confidence": 0.85,
                "focus": "极端环境、被动式设计、能源系统",
                "note": "V6-1/V6-2核心能力，环境适应性设计",
            },
        ],
        "secondary": [
            {
                "id": "A4",
                "name": "Material Intelligence",
                "maturity_level": "L3",
                "confidence": 0.7,
                "focus": "材料选择、材料性能",
                "note": "V6-3专长，V6-1/V6-2辅助",
            },
            {
                "id": "A7",
                "name": "Capital Strategy Intelligence",
                "maturity_level": "L3",
                "confidence": 0.7,
                "focus": "成本控制、价值工程",
                "note": "V6-4专长，成本工程师",
            },
        ],
    },
    "v5_scenario_expert": {
        "primary": [
            {
                "id": "A11",
                "name": "Operation & Productization",
                "maturity_level": "L4",
                "sub_abilities": [
                    "A11-1_scenario_operation",
                    "A11-2_customer_flow",
                    "A11-3_business_model",
                    "A11-4_long_term_revenue",
                ],
                "confidence": 0.9,
                "focus": "场景运营、商业模式、客流组织",
                "note": "V5核心能力，场景专家",
            }
        ],
        "secondary": [
            {
                "id": "A3",
                "name": "Narrative Orchestration",
                "maturity_level": "L3",
                "confidence": 0.75,
                "focus": "商业叙事、体验设计",
                "note": "辅助场景体验设计",
            },
            {
                "id": "A7",
                "name": "Capital Strategy Intelligence",
                "maturity_level": "L3",
                "confidence": 0.7,
                "focus": "商业回报、坪效优化",
                "note": "辅助商业价值分析",
            },
        ],
    },
    "v4_design_researcher": {
        "primary": [
            {
                "id": "A12",
                "name": "Civilizational Expression",
                "maturity_level": "L4",
                "sub_abilities": [
                    "A12-1_cultural_context",
                    "A12-2_cross_discipline",
                    "A12-3_future_trends",
                    "A12-4_design_philosophy",
                ],
                "confidence": 0.85,
                "focus": "跨学科研究、文化文脉、设计哲学",
                "note": "V4核心能力，研究专家",
            }
        ],
        "secondary": [
            {
                "id": "A1",
                "name": "Concept Architecture",
                "maturity_level": "L4",
                "confidence": 0.8,
                "focus": "概念挖掘、案例对标",
                "note": "辅助概念建构",
            },
            {
                "id": "A8",
                "name": "Technology Integration",
                "maturity_level": "L3",
                "confidence": 0.7,
                "focus": "前沿技术研究",
                "note": "辅助技术趋势分析",
            },
        ],
    },
    "v3_narrative_expert": {
        "primary": [
            {
                "id": "A3",
                "name": "Narrative Orchestration",
                "maturity_level": "L5",
                "sub_abilities": [
                    "A3-1_emotion_rhythm",
                    "A3-2_sensory_design",
                    "A3-3_memory_anchor",
                    "A3-4_experience_climax",
                ],
                "confidence": 0.95,
                "focus": "叙事节奏、情绪体验、五感调动",
                "note": "V3核心能力，叙事专家",
            }
        ],
        "secondary": [
            {
                "id": "A1",
                "name": "Concept Architecture",
                "maturity_level": "L4",
                "confidence": 0.85,
                "focus": "品牌叙事、人物建模",
                "note": "辅助概念主线构建",
            },
            {
                "id": "A9",
                "name": "Social Structure Modeling",
                "maturity_level": "L3",
                "sub_abilities": ["A9-1_power_distance", "A9-4_evolution_adaptability"],
                "confidence": 0.7,
                "focus": "人物关系、家庭生命周期",
                "note": "V3-1人物专家补充A9能力，辅助V7",
            },
        ],
    },
    "v2_design_director": {
        "primary": [
            {
                "id": "A1",
                "name": "Concept Architecture",
                "maturity_level": "L5",
                "sub_abilities": [
                    "A1-1_spirit_modeling",
                    "A1-2_concept_structuring",
                    "A1-3_cultural_motif",
                    "A1-4_spatial_narrative",
                ],
                "confidence": 0.95,
                "focus": "精神主轴、概念结构化、文化母题",
                "note": "V2核心能力，设计总监战略定位",
            },
            {
                "id": "A7",
                "name": "Capital Strategy Intelligence",
                "maturity_level": "L4",
                "sub_abilities": [
                    "A7-1_client_asset_model",
                    "A7-2_value_optimization",
                    "A7-3_premium_construction",
                    "A7-4_lifecycle_revenue",
                ],
                "confidence": 0.9,
                "focus": "资本策略、溢价构建、长期收益",
                "note": "V2核心能力，资产型项目战略",
            },
        ],
        "secondary": [
            {
                "id": "A2",
                "name": "Spatial Structuring",
                "maturity_level": "L5",
                "confidence": 0.9,
                "focus": "空间秩序、总体规划",
                "note": "V2总监级空间能力",
            },
            {
                "id": "A11",
                "name": "Operation & Productization",
                "maturity_level": "L3",
                "confidence": 0.75,
                "focus": "商业策略、运营模式",
                "note": "辅助商业项目决策",
            },
            {
                "id": "A12",
                "name": "Civilizational Expression",
                "maturity_level": "L3",
                "confidence": 0.7,
                "focus": "文化建筑、设计哲学",
                "note": "V2-6文化公共建筑专长",
            },
        ],
    },
}


def add_ability_declaration_to_config(config_path: Path, expert_id: str) -> bool:
    """
    为专家配置文件添加能力声明

    Args:
        config_path: 配置文件路径
        expert_id: 专家ID

    Returns:
        bool - 是否成功更新
    """
    if expert_id not in EXPERT_ABILITIES_MAPPING:
        print(f"⚠️  跳过 {expert_id}: 未配置能力映射")
        return False

    try:
        # 读取配置文件
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 检查是否已经有 core_abilities
        if "core_abilities:" in content:
            print(f"✅ 跳过 {expert_id}: 已包含 core_abilities")
            return True

        # 找到插入位置（通常在 description 之后、core_expertise 或 roles 之前）
        abilities_yaml = yaml.dump(
            {"core_abilities": EXPERT_ABILITIES_MAPPING[expert_id]},
            allow_unicode=True,
            default_flow_style=False,
            indent=2,
        )

        # 添加注释
        header = """
  # ============================================================================
  # 🔧 P1 实施: 能力显式化声明 (Ability Explicitation)
  # ============================================================================
  # 创建日期: 2026-02-12
  # 目的: 显式声明专家所拥有的 12 Ability Core 能力，用于：
  #   1. 能力覆盖度追踪
  #   2. 专家-能力匹配分析
  #   3. 能力验证系统
  # ============================================================================
"""

        full_insertion = header + "  " + abilities_yaml.replace("\n", "\n  ")

        # 插入到合适位置
        lines = content.split("\n")
        insertion_line = -1

        for i, line in enumerate(lines):
            if "  description:" in line:
                # 找到下一个主要字段（core_expertise 或 roles）
                for j in range(i + 1, len(lines)):
                    if "  core_expertise:" in lines[j] or "  roles:" in lines[j] or "  system_prompt:" in lines[j]:
                        insertion_line = j
                        break
                break

        if insertion_line == -1:
            print(f"❌ 失败 {expert_id}: 无法找到插入位置")
            return False

        # 插入能力声明
        lines.insert(insertion_line, full_insertion)
        new_content = "\n".join(lines)

        # 写回文件
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        print(f"✅ 成功 {expert_id}: 已添加能力声明")
        return True

    except Exception as e:
        print(f"❌ 失败 {expert_id}: {e}")
        return False


def main():
    """主函数：批量更新所有专家配置文件"""
    print("=" * 80)
    print("批量更新专家配置文件 - 添加能力声明 (Ability Explicitation)")
    print("=" * 80)
    print()

    # 获取配置文件目录
    project_root = Path(__file__).parent.parent.parent
    config_dir = project_root / "intelligent_project_analyzer" / "config" / "roles"

    if not config_dir.exists():
        print(f"❌ 错误: 配置目录不存在 - {config_dir}")
        return

    # 遍历所有专家配置文件
    yaml_files = list(config_dir.glob("*.yaml"))
    print(f"📁 找到 {len(yaml_files)} 个配置文件\n")

    success_count = 0
    skip_count = 0
    fail_count = 0

    for yaml_file in yaml_files:
        expert_id = yaml_file.stem
        result = add_ability_declaration_to_config(yaml_file, expert_id)

        if result:
            success_count += 1
        elif "core_abilities:" in yaml_file.read_text(encoding="utf-8"):
            skip_count += 1
        else:
            fail_count += 1

    print()
    print("=" * 80)
    print(f"✅ 成功: {success_count}  ⏭️  跳过: {skip_count}  ❌ 失败: {fail_count}")
    print("=" * 80)


if __name__ == "__main__":
    main()
