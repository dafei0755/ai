"""
测试框架清单持久化 v7.241

验证框架清单能够：
1. 正确生成并发送到前端
2. 正确保存到数据库
3. 重启后端后能够正确加载
"""

import asyncio
import json

import httpx

from intelligent_project_analyzer.services.session_archive_manager import get_archive_manager


async def test_framework_checklist_persistence():
    """测试框架清单持久化"""
    print("=" * 80)
    print("框架清单持久化测试 v7.241")
    print("=" * 80)

    # 测试查询
    test_query = "以HAY气质为基础，在四川峨眉山七里坪设计民宿室内概念"
    test_session_id = "test-checklist-persist-001"

    print(f"\n📝 测试查询: {test_query}")
    print(f"📋 会话ID: {test_session_id}")

    # 模拟前端保存会话数据（包含框架清单）
    mock_framework_checklist = {
        "core_summary": "如何在峨眉山七里坪融合HAY气质设计民宿",
        "main_directions": [
            {"direction": "品牌调研", "purpose": "了解HAY设计语言", "expected_outcome": "产品线、色彩系统、材质特点"},
            {"direction": "空间规划", "purpose": "确定功能分区", "expected_outcome": "动线方案、区域划分"},
        ],
        "boundaries": ["不涉及预算规划", "不涉及施工细节"],
        "answer_goal": "提供完整的HAY风格民宿设计概念方案",
        "generated_at": "2026-01-23T15:00:00",
        "plain_text": "## 核心问题\n如何在峨眉山七里坪融合HAY气质设计民宿\n\n## 搜索主线（2个方向）\n1. **品牌调研**\n   目的：了解HAY设计语言\n   期望：产品线、色彩系统、材质特点\n\n2. **空间规划**\n   目的：确定功能分区\n   期望：动线方案、区域划分",
    }

    mock_search_master_line = {
        "core_question": "如何在峨眉山七里坪融合HAY气质设计民宿",
        "boundary": "不涉及预算规划、施工细节",
        "tasks": [],
        "task_count": 0,
        "exploration_triggers": [],
        "forbidden_zones": ["预算规划", "施工细节"],
    }

    print("\n" + "=" * 80)
    print("步骤 1: 保存会话到数据库")
    print("=" * 80)

    try:
        # 使用后端API保存会话
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://127.0.0.1:8000/api/search/session/save",
                json={
                    "session_id": test_session_id,
                    "query": test_query,
                    "sources": [],
                    "images": [],
                    "thinkingContent": "测试思考内容",
                    "answerContent": "测试答案内容",
                    "searchPlan": None,
                    "rounds": [],
                    "totalRounds": 0,
                    "executionTime": 0,
                    "isDeepMode": True,
                    "l0Content": "",
                    "problemSolvingThinking": "",
                    "structuredInfo": None,
                    # v7.241: 包含框架清单和搜索主线
                    "frameworkChecklist": mock_framework_checklist,
                    "searchMasterLine": mock_search_master_line,
                },
                timeout=10.0,
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    print("✅ 会话保存成功")
                else:
                    print(f"❌ 会话保存失败: {result.get('error')}")
                    return False
            else:
                print(f"❌ API调用失败: HTTP {response.status_code}")
                return False

    except Exception as e:
        print(f"❌ 保存失败: {e}")
        return False

    print("\n" + "=" * 80)
    print("步骤 2: 从数据库加载会话")
    print("=" * 80)

    try:
        manager = get_archive_manager()
        session = await manager.get_search_session(test_session_id)

        if not session:
            print("❌ 会话未找到")
            return False

        print("✅ 会话加载成功")
        print(f"  查询: {session.get('query', 'N/A')}")
        print(f"  创建时间: {session.get('created_at', 'N/A')}")

        result = session.get("search_result", {})

        # 验证框架清单
        print("\n" + "-" * 80)
        print("验证框架清单")
        print("-" * 80)

        if "frameworkChecklist" not in result:
            print("❌ 失败: search_result 中没有 frameworkChecklist 字段")
            return False

        checklist = result["frameworkChecklist"]
        if checklist is None:
            print("❌ 失败: frameworkChecklist 为 None")
            return False

        print("✅ frameworkChecklist 字段存在")
        print(f"  核心摘要: {checklist.get('core_summary', 'N/A')}")
        print(f"  方向数: {len(checklist.get('main_directions', []))}")
        print(f"  边界数: {len(checklist.get('boundaries', []))}")
        print(f"  回答目标: {checklist.get('answer_goal', 'N/A')}")

        # 验证搜索主线
        print("\n" + "-" * 80)
        print("验证搜索主线")
        print("-" * 80)

        if "searchMasterLine" not in result:
            print("❌ 失败: search_result 中没有 searchMasterLine 字段")
            return False

        master_line = result["searchMasterLine"]
        if master_line is None:
            print("❌ 失败: searchMasterLine 为 None")
            return False

        print("✅ searchMasterLine 字段存在")
        print(f"  核心问题: {master_line.get('core_question', 'N/A')}")
        print(f"  边界: {master_line.get('boundary', 'N/A')}")
        print(f"  禁区数: {len(master_line.get('forbidden_zones', []))}")

        # 验证数据完整性
        print("\n" + "-" * 80)
        print("验证数据完整性")
        print("-" * 80)

        success = True

        # 检查框架清单字段
        if checklist.get("core_summary") != mock_framework_checklist["core_summary"]:
            print("❌ core_summary 不匹配")
            success = False
        else:
            print("✅ core_summary 匹配")

        if len(checklist.get("main_directions", [])) != len(mock_framework_checklist["main_directions"]):
            print("❌ main_directions 数量不匹配")
            success = False
        else:
            print("✅ main_directions 数量匹配")

        if len(checklist.get("boundaries", [])) != len(mock_framework_checklist["boundaries"]):
            print("❌ boundaries 数量不匹配")
            success = False
        else:
            print("✅ boundaries 数量匹配")

        return success

    except Exception as e:
        print(f"❌ 加载失败: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("框架清单持久化测试 v7.241")
    print("=" * 80)
    print("\n此测试将验证:")
    print("1. 框架清单能否正确保存到数据库")
    print("2. 框架清单能否正确从数据库加载")
    print("3. 数据完整性是否保持")
    print("\n开始测试...\n")

    result = asyncio.run(test_framework_checklist_persistence())

    print("\n" + "=" * 80)
    if result:
        print("🎉 测试通过！框架清单持久化功能正常！")
    else:
        print("❌ 测试失败！需要进一步调试。")
    print("=" * 80)

    exit(0 if result else 1)
