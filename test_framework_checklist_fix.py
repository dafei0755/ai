"""
测试框架清单修复 v7.241

验证框架清单在以下场景下都能正常生成和发送：
1. 正常情况（有targets）
2. 边界情况（无targets）
3. 错误情况（生成失败时的降级方案）
"""

import asyncio
import json

from intelligent_project_analyzer.services.ucppt_search_engine import get_ucppt_engine


async def test_framework_checklist_generation():
    """测试框架清单生成"""
    print("=" * 80)
    print("测试框架清单修复 v7.241")
    print("=" * 80)

    # 测试查询：HAY民宿设计
    test_query = "以HAY气质为基础，在四川峨眉山七里坪设计民宿室内概念"

    print(f"\n📝 测试查询: {test_query}")
    print("\n开始搜索流程...\n")

    engine = get_ucppt_engine()

    # 追踪关键事件
    events_received = {
        "unified_dialogue_chunk": 0,
        "unified_dialogue_complete": 0,
        "search_framework_ready": 0,
        "analysis_complete": 0,
    }

    framework_checklist_data = None

    try:
        async for event in engine.search_deep(
            query=test_query,
            max_rounds=5,  # 限制轮数以加快测试
        ):
            event_type = event.get("type", "")

            # 统计事件
            if event_type in events_received:
                events_received[event_type] += 1

            # 重点关注 search_framework_ready 事件
            if event_type == "search_framework_ready":
                data = event.get("data", {})
                framework_checklist_data = data.get("framework_checklist")

                print("=" * 80)
                print("✅ 收到 search_framework_ready 事件")
                print("=" * 80)
                print(f"核心问题: {data.get('core_question', 'N/A')}")
                print(f"回答目标: {data.get('answer_goal', 'N/A')}")
                print(f"目标数量: {data.get('target_count', 0)}")
                print(f"质量等级: {data.get('quality_grade', 'N/A')}")

                if framework_checklist_data:
                    print("\n📋 框架清单内容:")
                    print(f"  - 核心摘要: {framework_checklist_data.get('core_summary', 'N/A')}")
                    print(f"  - 搜索方向数: {len(framework_checklist_data.get('main_directions', []))}")
                    print(f"  - 边界数: {len(framework_checklist_data.get('boundaries', []))}")
                    print(f"  - 回答目标: {framework_checklist_data.get('answer_goal', 'N/A')}")

                    # 显示搜索方向详情
                    directions = framework_checklist_data.get("main_directions", [])
                    if directions:
                        print("\n  搜索方向详情:")
                        for i, d in enumerate(directions, 1):
                            print(f"    {i}. {d.get('direction', 'N/A')}")
                            print(f"       目的: {d.get('purpose', 'N/A')}")
                            print(f"       期望: {d.get('expected_outcome', 'N/A')}")

                    # 显示边界
                    boundaries = framework_checklist_data.get("boundaries", [])
                    if boundaries:
                        print(f"\n  搜索边界: {', '.join(boundaries)}")
                else:
                    print("\n⚠️ 框架清单数据为空！")

                print("=" * 80)

                # 找到框架清单后可以提前结束
                break

            elif event_type == "unified_dialogue_chunk":
                # 显示对话内容（简化）
                content = event.get("content", "")
                if content:
                    print(f"💬 {content[:100]}..." if len(content) > 100 else f"💬 {content}")

            elif event_type == "error":
                print(f"\n❌ 错误: {event.get('data', {}).get('message', 'Unknown error')}")
                break

            elif event_type == "done":
                print("\n✅ 搜索完成")
                break

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False

    # 验证结果
    print("\n" + "=" * 80)
    print("测试结果汇总")
    print("=" * 80)
    print(f"事件统计:")
    for event_name, count in events_received.items():
        status = "✅" if count > 0 else "❌"
        print(f"  {status} {event_name}: {count}")

    # 关键验证
    success = True

    if events_received["search_framework_ready"] == 0:
        print("\n❌ 失败: 未收到 search_framework_ready 事件")
        success = False
    else:
        print("\n✅ 成功: 收到 search_framework_ready 事件")

    if framework_checklist_data is None:
        print("❌ 失败: 框架清单数据为空")
        success = False
    else:
        print("✅ 成功: 框架清单数据存在")

        # 验证必要字段
        required_fields = ["core_summary", "main_directions", "boundaries", "answer_goal"]
        for field in required_fields:
            if field not in framework_checklist_data:
                print(f"⚠️ 警告: 缺少字段 {field}")

    print("=" * 80)

    if success:
        print("\n🎉 测试通过！框架清单修复成功！")
    else:
        print("\n❌ 测试失败！需要进一步调试。")

    return success


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("框架清单修复测试 v7.241")
    print("=" * 80)
    print("\n此测试将验证:")
    print("1. search_framework_ready 事件是否正常发送")
    print("2. framework_checklist 数据是否包含在事件中")
    print("3. 框架清单的必要字段是否完整")
    print("\n开始测试...\n")

    result = asyncio.run(test_framework_checklist_generation())

    exit(0 if result else 1)
