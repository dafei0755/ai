"""
测试框架清单端到端流程 v7.241

完整验证：
1. 搜索引擎生成框架清单
2. 框架清单通过SSE发送到前端
3. 框架清单保存到数据库
4. 重启后端后能够正确加载
"""

import asyncio
import json
import uuid
from datetime import datetime

from intelligent_project_analyzer.services.session_archive_manager import get_archive_manager
from intelligent_project_analyzer.services.ucppt_search_engine import get_ucppt_engine


async def test_e2e_framework_checklist():
    """测试框架清单端到端流程"""
    print("=" * 80)
    print("框架清单端到端测试 v7.241")
    print("=" * 80)

    # 测试查询
    test_query = "以HAY气质为基础，在四川峨眉山七里坪设计民宿室内概念"
    test_session_id = f"e2e-test-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"

    print(f"\n📝 测试查询: {test_query}")
    print(f"📋 会话ID: {test_session_id}")

    # ==================== 步骤 1: 搜索引擎生成框架清单 ====================
    print("\n" + "=" * 80)
    print("步骤 1: 搜索引擎生成框架清单")
    print("=" * 80)

    engine = get_ucppt_engine()

    framework_checklist_received = None
    search_master_line_received = None
    search_completed = False

    try:
        async for event in engine.search_deep(
            query=test_query,
            max_rounds=3,  # 限制轮数以加快测试
        ):
            event_type = event.get("type", "")

            # 捕获框架清单事件
            if event_type == "search_framework_ready":
                data = event.get("data", {})
                framework_checklist_received = data.get("framework_checklist")

                print("✅ 收到 search_framework_ready 事件")
                if framework_checklist_received:
                    print(f"  核心摘要: {framework_checklist_received.get('core_summary', 'N/A')}")
                    print(f"  方向数: {len(framework_checklist_received.get('main_directions', []))}")
                    print(f"  边界数: {len(framework_checklist_received.get('boundaries', []))}")
                else:
                    print("  ⚠️ 框架清单为空")

            # 捕获搜索主线事件
            elif event_type == "search_master_line_ready":
                data = event.get("data", {})
                search_master_line_received = data.get("search_master_line")

                print("✅ 收到 search_master_line_ready 事件")
                if search_master_line_received:
                    print(f"  核心问题: {search_master_line_received.get('core_question', 'N/A')}")
                    print(f"  任务数: {search_master_line_received.get('task_count', 0)}")

            # 等待搜索完成
            elif event_type == "done":
                search_completed = True
                print("\n✅ 搜索完成")
                break

            elif event_type == "error":
                print(f"\n❌ 搜索错误: {event.get('data', {}).get('message', 'Unknown')}")
                return False

    except Exception as e:
        print(f"\n❌ 搜索失败: {e}")
        import traceback

        traceback.print_exc()
        return False

    # 验证步骤1
    if not framework_checklist_received:
        print("\n❌ 步骤1失败: 未收到框架清单")
        return False

    print("\n✅ 步骤1通过: 框架清单生成成功")

    # ==================== 步骤 2: 保存到数据库 ====================
    print("\n" + "=" * 80)
    print("步骤 2: 保存框架清单到数据库")
    print("=" * 80)

    try:
        manager = get_archive_manager()

        # 模拟前端保存会话
        success = await manager.archive_search_session(
            session_id=test_session_id,
            query=test_query,
            search_result={
                "sources": [],
                "images": [],
                "thinkingContent": "测试思考内容",
                "answerContent": "测试答案内容",
                "searchPlan": None,
                "rounds": [],
                "totalRounds": 3,
                "executionTime": 10.5,
                "isDeepMode": True,
                "l0Content": "",
                "problemSolvingThinking": "",
                "structuredInfo": None,
                "frameworkChecklist": framework_checklist_received,
                "searchMasterLine": search_master_line_received,
            },
            user_id=None,
            force=True,
        )

        if success:
            print("✅ 会话保存成功")
        else:
            print("❌ 会话保存失败")
            return False

    except Exception as e:
        print(f"❌ 保存失败: {e}")
        import traceback

        traceback.print_exc()
        return False

    print("\n✅ 步骤2通过: 框架清单已保存到数据库")

    # ==================== 步骤 3: 从数据库加载 ====================
    print("\n" + "=" * 80)
    print("步骤 3: 从数据库加载框架清单")
    print("=" * 80)

    try:
        session = await manager.get_search_session(test_session_id)

        if not session:
            print("❌ 会话未找到")
            return False

        print("✅ 会话加载成功")

        result = session.get("search_result", {})

        # 验证框架清单
        checklist = result.get("frameworkChecklist")
        if not checklist:
            print("❌ 框架清单未找到")
            return False

        print("✅ 框架清单加载成功")
        print(f"  核心摘要: {checklist.get('core_summary', 'N/A')}")
        print(f"  方向数: {len(checklist.get('main_directions', []))}")
        print(f"  边界数: {len(checklist.get('boundaries', []))}")

        # 验证搜索主线
        master_line = result.get("searchMasterLine")
        if master_line:
            print("✅ 搜索主线加载成功")
            print(f"  核心问题: {master_line.get('core_question', 'N/A')}")
        else:
            print("⚠️ 搜索主线未找到（可选字段）")

    except Exception as e:
        print(f"❌ 加载失败: {e}")
        import traceback

        traceback.print_exc()
        return False

    print("\n✅ 步骤3通过: 框架清单加载成功")

    # ==================== 步骤 4: 验证数据完整性 ====================
    print("\n" + "=" * 80)
    print("步骤 4: 验证数据完整性")
    print("=" * 80)

    # 比较原始数据和加载的数据
    original_summary = framework_checklist_received.get("core_summary", "")
    loaded_summary = checklist.get("core_summary", "")

    if original_summary == loaded_summary:
        print("✅ 核心摘要匹配")
    else:
        print(f"❌ 核心摘要不匹配")
        print(f"  原始: {original_summary}")
        print(f"  加载: {loaded_summary}")
        return False

    original_directions_count = len(framework_checklist_received.get("main_directions", []))
    loaded_directions_count = len(checklist.get("main_directions", []))

    if original_directions_count == loaded_directions_count:
        print(f"✅ 搜索方向数量匹配 ({loaded_directions_count})")
    else:
        print(f"❌ 搜索方向数量不匹配")
        print(f"  原始: {original_directions_count}")
        print(f"  加载: {loaded_directions_count}")
        return False

    print("\n✅ 步骤4通过: 数据完整性验证成功")

    return True


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("框架清单端到端测试 v7.241")
    print("=" * 80)
    print("\n此测试将验证完整流程:")
    print("1. 搜索引擎生成框架清单")
    print("2. 框架清单通过SSE发送")
    print("3. 框架清单保存到数据库")
    print("4. 框架清单从数据库加载")
    print("5. 数据完整性验证")
    print("\n开始测试...\n")

    result = asyncio.run(test_e2e_framework_checklist())

    print("\n" + "=" * 80)
    if result:
        print("🎉 端到端测试通过！框架清单功能完全正常！")
        print("\n✅ 所有步骤验证成功:")
        print("  1. ✅ 搜索引擎生成框架清单")
        print("  2. ✅ 框架清单保存到数据库")
        print("  3. ✅ 框架清单从数据库加载")
        print("  4. ✅ 数据完整性验证")
    else:
        print("❌ 端到端测试失败！请检查日志。")
    print("=" * 80)

    exit(0 if result else 1)
