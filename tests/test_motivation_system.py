"""
动机识别系统测试脚本
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from intelligent_project_analyzer.services.motivation_engine import MotivationTypeRegistry, get_motivation_engine


def test_registry():
    """测试动机类型注册表"""
    print("=" * 80)
    print("🧪 测试动机类型注册表")
    print("=" * 80)

    registry = MotivationTypeRegistry()

    # 测试加载
    all_types = registry.get_all_types()
    print(f"\n✅ 已加载 {len(all_types)} 个动机类型：")

    # 按优先级分组
    p0_types = registry.get_types_by_priority("P0")
    p1_types = registry.get_types_by_priority("P1")
    p2_types = registry.get_types_by_priority("P2")
    baseline_types = registry.get_types_by_priority("BASELINE")

    print(f"\n📊 P0优先级 ({len(p0_types)}个):")
    for t in p0_types:
        print(f"   • {t.label_zh} ({t.id}) - {len(t.keywords)}个关键词")

    print(f"\n📊 P1优先级 ({len(p1_types)}个):")
    for t in p1_types:
        print(f"   • {t.label_zh} ({t.id}) - {len(t.keywords)}个关键词")

    print(f"\n📊 P2优先级 ({len(p2_types)}个):")
    for t in p2_types:
        print(f"   • {t.label_zh} ({t.id}) - {len(t.keywords)}个关键词")

    print(f"\n📊 基线类型 ({len(baseline_types)}个):")
    for t in baseline_types:
        print(f"   • {t.label_zh} ({t.id})")

    # 测试获取单个类型
    print("\n" + "=" * 80)
    print("🔍 测试获取单个类型")
    print("=" * 80)

    cultural = registry.get_type("cultural")
    if cultural:
        print(f"\n✅ 文化认同需求:")
        print(f"   ID: {cultural.id}")
        print(f"   标签: {cultural.label_zh} / {cultural.label_en}")
        print(f"   优先级: {cultural.priority}")
        print(f"   描述: {cultural.description}")
        print(f"   关键词样例: {list(cultural.keywords.keys())[:5]}")
        print(f"   LLM示例: {cultural.llm_examples[0] if cultural.llm_examples else 'None'}")
        print(f"   颜色: {cultural.color}")


def test_engine():
    """测试动机推断引擎"""
    print("\n" + "=" * 80)
    print("🧪 测试动机推断引擎")
    print("=" * 80)

    engine = get_motivation_engine()

    # 测试案例
    test_cases = [
        {
            "title": "蛇口渔村传统文化融入研究",
            "description": "深入调研蛇口渔村的历史文脉和精神内核，提炼可融入设计的文化元素",
            "source_keywords": ["文化", "传统", "渔村"],
        },
        {"title": "咖啡店坪效优化策略", "description": "极致提升坪效，将顾客平均停留时间控制在18分钟以内", "source_keywords": ["商业", "坪效", "运营"]},
        {"title": "自闭症儿童友好空间设计", "description": "为自闭症儿童设计安全、舒适的居住环境", "source_keywords": ["健康", "自闭症", "儿童"]},
        {"title": "华为全屋智能系统集成", "description": "深度植入鸿蒙智能系统，实现隐形智能化", "source_keywords": ["技术", "智能", "系统"]},
    ]

    for i, task in enumerate(test_cases, 1):
        print(f"\n{'─' * 80}")
        print(f"📝 测试案例 {i}: {task['title']}")
        print(f"{'─' * 80}")

        result = engine._keyword_matching(task, "", None)

        print(f"   🎯 识别结果: {result.primary_label} ({result.primary})")
        print(f"   📊 置信度: {result.confidence:.2f}")
        print(f"   💭 推理: {result.reasoning}")
        print(f"   🔧 方法: {result.method}")

        if result.scores:
            print(f"   📈 评分详情:")
            sorted_scores = sorted(result.scores.items(), key=lambda x: -x[1])[:3]
            for type_id, score in sorted_scores:
                mtype = engine.registry.get_type(type_id)
                label = mtype.label_zh if mtype else type_id
                print(f"      • {label}: {score:.2f}")


def main():
    """主函数"""
    print("\n" + "🚀" * 40)
    print("动机识别系统 v7.106 测试")
    print("🚀" * 40 + "\n")

    try:
        test_registry()
        test_engine()

        print("\n" + "=" * 80)
        print("✅ 所有测试通过！")
        print("=" * 80 + "\n")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
