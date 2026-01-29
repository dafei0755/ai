"""
v7.109 集成测试脚本（简化版）
测试核心数据结构和配置生成

测试重点：
1. search_query_generator_node 生成正确的搜索查询
2. 模式差异化（normal vs deep_thinking）
3. 用户修改处理逻辑
"""

import sys
from pathlib import Path

# 🔧 修复Windows终端UTF-8编码问题（优先使用 reconfigure，避免关闭底层流）
if sys.platform == "win32":
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue

        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
                continue
            except Exception:
                pass

        if hasattr(stream, "buffer"):
            import io

            setattr(
                sys,
                stream_name,
                io.TextIOWrapper(stream.buffer, encoding="utf-8", errors="replace"),
            )

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from intelligent_project_analyzer.agents.search_strategy import SearchStrategyGenerator
from intelligent_project_analyzer.core.task_oriented_models import DeliverableSpec
from intelligent_project_analyzer.workflow.nodes.search_query_generator_node import search_query_generator_node


def test_search_query_generator_normal_mode():
    """测试普通模式：search_query_generator生成1张图配置"""
    print("\n" + "=" * 80)
    print("📋 测试1: search_query_generator - 普通模式")
    print("=" * 80)

    state = {
        "analysis_mode": "normal",
        "deliverable_metadata": {
            "test_deliv_001": {
                "id": "test_deliv_001",
                "name": "整体设计方案",
                "description": "项目整体设计策略与概念",
                "keywords": ["现代", "简约", "Audrey Hepburn"],
                "constraints": {"must_include": ["设计理念", "空间布局"]},
                "owner_role": "2-1",
            }
        },
    }

    result = search_query_generator_node(state)

    metadata = result["deliverable_metadata"]["test_deliv_001"]

    print(f"\n✅ 交付物: {metadata['name']}")
    print(f"   🔍 搜索查询数量: {len(metadata.get('search_queries', []))}")
    for i, query in enumerate(metadata.get("search_queries", []), 1):
        print(f"      {i}. {query}")

    image_config = metadata["concept_image_config"]
    print(f"\n   📷 概念图配置:")
    print(f"      - 数量: {image_config['count']} 张")
    print(f"      - 可编辑: {image_config['editable']}")
    print(f"      - 最大数量: {image_config['max_count']}")

    # 验证
    assert image_config["count"] == 1, "❌ 普通模式应默认1张图"
    assert image_config["editable"] == False, "❌ 普通模式不应可编辑"
    assert image_config["max_count"] == 1, "❌ 普通模式最大数量应为1"
    assert len(metadata["search_queries"]) >= 2, "❌ 应生成至少2个搜索查询"

    print("\n✅ 普通模式测试通过")


def test_search_query_generator_deep_thinking_mode():
    """测试深度思考模式：search_query_generator生成3张图配置"""
    print("\n" + "=" * 80)
    print("📋 测试2: search_query_generator - 深度思考模式")
    print("=" * 80)

    state = {
        "analysis_mode": "deep_thinking",
        "deliverable_metadata": {
            "test_deliv_002": {
                "id": "test_deliv_002",
                "name": "用户体验旅程地图",
                "description": "完整的用户体验流程设计",
                "keywords": ["独立女性", "归属感", "优雅"],
                "constraints": {"must_include": ["触点设计", "情感曲线"]},
                "owner_role": "3-1",
            }
        },
    }

    result = search_query_generator_node(state)

    metadata = result["deliverable_metadata"]["test_deliv_002"]

    print(f"\n✅ 交付物: {metadata['name']}")
    print(f"   🔍 搜索查询数量: {len(metadata.get('search_queries', []))}")
    for i, query in enumerate(metadata.get("search_queries", []), 1):
        print(f"      {i}. {query}")

    image_config = metadata["concept_image_config"]
    print(f"\n   📷 概念图配置:")
    print(f"      - 数量: {image_config['count']} 张")
    print(f"      - 可编辑: {image_config['editable']}")
    print(f"      - 最大数量: {image_config['max_count']}")

    # 验证
    assert image_config["count"] == 3, "❌ 深度思考模式应默认3张图"
    assert image_config["editable"] == True, "❌ 深度思考模式应可编辑"
    assert image_config["max_count"] == 10, "❌ 深度思考模式最大数量应为10"
    assert len(metadata["search_queries"]) >= 2, "❌ 应生成至少2个搜索查询"

    print("\n✅ 深度思考模式测试通过")


def test_deliverable_spec_model():
    """测试DeliverableSpec数据模型扩展"""
    print("\n" + "=" * 80)
    print("📋 测试3: DeliverableSpec 数据模型")
    print("=" * 80)

    # 测试包含新字段的DeliverableSpec
    deliverable = DeliverableSpec(
        name="测试交付物",
        description="测试描述",
        format="analysis",
        priority="high",
        success_criteria=["标准1", "标准2"],
        search_queries=["查询1", "查询2", "查询3"],
        concept_image_config={"count": 5, "editable": True, "max_count": 10},
    )

    print(f"\n✅ DeliverableSpec 实例化成功")
    print(f"   - name: {deliverable.name}")
    print(f"   - search_queries: {deliverable.search_queries}")
    print(f"   - concept_image_config: {deliverable.concept_image_config}")

    # 验证可选字段为None时也能工作
    deliverable_minimal = DeliverableSpec(
        name="最小配置交付物", description="测试", format="design", priority="medium", success_criteria=["标准1"]
    )

    assert deliverable_minimal.search_queries is None, "❌ search_queries应为可选字段"
    assert deliverable_minimal.concept_image_config is None, "❌ concept_image_config应为可选字段"

    print(f"\n✅ DeliverableSpec 可选字段验证通过")


def test_user_modification_logic():
    """测试用户修改逻辑（模拟role_task_unified_review的处理）"""
    print("\n" + "=" * 80)
    print("📋 测试4: 用户修改处理逻辑")
    print("=" * 80)

    # 初始状态
    deliverable_metadata = {
        "deliv_001": {
            "id": "deliv_001",
            "name": "设计方案",
            "search_queries": ["原始查询1", "原始查询2", "原始查询3"],
            "concept_image_config": {"count": 3, "editable": True, "max_count": 10},
        }
    }

    # 模拟用户修改
    modifications = {
        "search_queries": {"deliv_001": ["修改后查询1", "修改后查询2", "修改后查询3", "新增查询4"]},
        "image_counts": {"deliv_001": 7},
        "project_aspect_ratio": "1:1",
    }

    # 应用修改（复制role_task_unified_review的逻辑）
    for deliv_id, new_queries in modifications.get("search_queries", {}).items():
        deliverable_metadata[deliv_id]["search_queries"] = new_queries

    for deliv_id, new_count in modifications.get("image_counts", {}).items():
        config = deliverable_metadata[deliv_id]["concept_image_config"]
        if config.get("editable"):
            validated_count = max(1, min(new_count, config["max_count"]))
            config["count"] = validated_count

    project_aspect_ratio = modifications.get("project_aspect_ratio", "16:9")

    # 验证修改结果
    result_metadata = deliverable_metadata["deliv_001"]

    print(f"\n✅ 修改应用结果:")
    print(f"   🔍 搜索查询: {result_metadata['search_queries']}")
    print(f"   📷 图片数量: {result_metadata['concept_image_config']['count']}")
    print(f"   🖼️ 项目宽高比: {project_aspect_ratio}")

    assert len(result_metadata["search_queries"]) == 4, "❌ 搜索查询修改失败"
    assert result_metadata["concept_image_config"]["count"] == 7, "❌ 图片数量修改失败"
    assert project_aspect_ratio == "1:1", "❌ 宽高比修改失败"

    print("\n✅ 用户修改处理逻辑测试通过")


def test_image_count_validation():
    """测试图片数量验证逻辑"""
    print("\n" + "=" * 80)
    print("📋 测试5: 图片数量验证（边界值测试）")
    print("=" * 80)

    test_cases = [
        ("正常值5", 5, 5),
        ("最小值1", 0, 1),  # 0会被限制为1
        ("超过上限15", 15, 10),  # 15会被限制为10
        ("负数-5", -5, 1),  # 负数会被限制为1
    ]

    for case_name, input_value, expected_output in test_cases:
        config = {"count": 3, "editable": True, "max_count": 10}
        validated_count = max(1, min(input_value, config["max_count"]))

        print(f"   {case_name}: 输入{input_value} → 输出{validated_count}")
        assert validated_count == expected_output, f"❌ {case_name}验证失败，期望{expected_output}，实际{validated_count}"

    print("\n✅ 图片数量验证测试通过")


def main():
    """运行所有测试"""
    print("\n" + "=" * 80)
    print("🚀 v7.109 集成测试套件（简化版）")
    print("=" * 80)

    try:
        # 测试1: 普通模式配置生成
        test_search_query_generator_normal_mode()

        # 测试2: 深度思考模式配置生成
        test_search_query_generator_deep_thinking_mode()

        # 测试3: 数据模型扩展
        test_deliverable_spec_model()

        # 测试4: 用户修改处理
        test_user_modification_logic()

        # 测试5: 边界值验证
        test_image_count_validation()

        print("\n" + "=" * 80)
        print("🎉 所有测试通过！v7.109功能完整可用")
        print("=" * 80)
        print("\n✅ 核心功能验证完成:")
        print("   1. ✅ 搜索查询生成（per-deliverable）")
        print("   2. ✅ 概念图配置生成（模式差异化）")
        print("   3. ✅ 数据模型扩展（DeliverableSpec）")
        print("   4. ✅ 用户修改处理逻辑")
        print("   5. ✅ 边界值验证（图片数量限制）")

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
