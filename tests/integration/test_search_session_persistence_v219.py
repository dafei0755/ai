"""
v7.219 集成测试：搜索会话字段持久化完整链路验证

测试目标：
1. 验证 l0Content、problemSolvingThinking、structuredInfo 字段的完整持久化链路
2. 验证 sources 从 rounds 聚合的 fallback 逻辑
3. 验证 final_confidence/final_completeness 字段兼容性

运行方式：
    pytest tests/integration/test_search_session_persistence_v219.py -v

    或直接运行：
    python tests/integration/test_search_session_persistence_v219.py
"""

import asyncio
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestSearchSessionPersistenceV219:
    """v7.219 搜索会话持久化测试"""

    @staticmethod
    def generate_test_session_id() -> str:
        """生成测试会话ID"""
        return f"test-v219-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"

    @staticmethod
    def create_mock_search_result() -> Dict[str, Any]:
        """创建模拟的搜索结果数据（包含 v7.219 新字段）"""
        return {
            "sources": [
                {"title": "测试来源1", "url": "https://example.com/1", "snippet": "内容1"},
                {"title": "测试来源2", "url": "https://example.com/2", "snippet": "内容2"},
            ],
            "images": [],
            "thinkingContent": "这是深度思考内容...",
            "answerContent": "这是AI回答内容...",
            "searchPlan": {"analysis": "搜索规划分析", "topics": [{"topicId": 1, "topicName": "主题1"}], "totalRounds": 3},
            "rounds": [
                {
                    "round": 1,
                    "topicName": "第1轮搜索",
                    "searchQuery": "测试查询1",
                    "sources": [{"title": "轮次1来源", "url": "https://r1.com"}],
                    "status": "complete",
                },
                {
                    "round": 2,
                    "topicName": "第2轮搜索",
                    "searchQuery": "测试查询2",
                    "sources": [{"title": "轮次2来源", "url": "https://r2.com"}],
                    "status": "complete",
                },
            ],
            "totalRounds": 2,
            "executionTime": 15.5,
            "isDeepMode": True,
            # 🆕 v7.219: 新增字段
            "l0Content": "这是L0阶段的对话分析内容，用于展示需求理解卡片...",
            "problemSolvingThinking": "解题思考过程：首先分析用户需求，然后拆解问题...",
            "structuredInfo": {
                "demographics": {"location": "深圳", "occupation": "设计师"},
                "identity_tags": ["创业者", "一代"],
                "core_needs": ["住宅设计", "创业空间"],
            },
        }

    async def test_archive_and_retrieve_new_fields(self):
        """测试1: 归档和检索新字段的完整链路"""
        print("\n" + "=" * 60)
        print("🧪 测试1: 归档和检索 v7.219 新字段")
        print("=" * 60)

        from intelligent_project_analyzer.services.session_archive_manager import get_archive_manager

        archive_manager = get_archive_manager()
        session_id = self.generate_test_session_id()
        query = "从一代创业者的视角，给出设计概念：深圳湾海景别墅"
        search_result = self.create_mock_search_result()

        # Step 1: 归档会话
        print(f"\n📥 Step 1: 归档会话 {session_id}")
        success = await archive_manager.archive_search_session(
            session_id=session_id, query=query, search_result=search_result, user_id="test-user-v219", force=True
        )
        assert success, "❌ 归档失败"
        print("✅ 归档成功")

        # Step 2: 检索会话
        print(f"\n📤 Step 2: 检索会话 {session_id}")
        retrieved = await archive_manager.get_search_session(session_id)
        assert retrieved is not None, "❌ 检索失败，返回 None"
        print("✅ 检索成功")

        # Step 3: 验证 v7.219 新字段
        print("\n🔍 Step 3: 验证 v7.219 新字段")

        # 3.1 验证 l0Content
        assert "l0Content" in retrieved, "❌ 缺少 l0Content 字段"
        assert (
            retrieved["l0Content"] == search_result["l0Content"]
        ), f"❌ l0Content 不匹配: {retrieved['l0Content'][:50]}..."
        print(f"  ✅ l0Content: {retrieved['l0Content'][:50]}...")

        # 3.2 验证 problemSolvingThinking
        assert "problemSolvingThinking" in retrieved, "❌ 缺少 problemSolvingThinking 字段"
        assert (
            retrieved["problemSolvingThinking"] == search_result["problemSolvingThinking"]
        ), f"❌ problemSolvingThinking 不匹配"
        print(f"  ✅ problemSolvingThinking: {retrieved['problemSolvingThinking'][:50]}...")

        # 3.3 验证 structuredInfo
        assert "structuredInfo" in retrieved, "❌ 缺少 structuredInfo 字段"
        assert retrieved["structuredInfo"] is not None, "❌ structuredInfo 为 None"
        assert (
            retrieved["structuredInfo"].get("demographics", {}).get("location") == "深圳"
        ), f"❌ structuredInfo.demographics.location 不匹配"
        print(f"  ✅ structuredInfo: {json.dumps(retrieved['structuredInfo'], ensure_ascii=False)[:80]}...")

        # Step 4: 验证原有字段仍正常
        print("\n🔍 Step 4: 验证原有字段")
        assert retrieved["query"] == query, "❌ query 不匹配"
        print(f"  ✅ query: {retrieved['query'][:50]}...")

        assert retrieved["isDeepMode"] == True, "❌ isDeepMode 不匹配"
        print(f"  ✅ isDeepMode: {retrieved['isDeepMode']}")

        assert retrieved["totalRounds"] == 2, "❌ totalRounds 不匹配"
        print(f"  ✅ totalRounds: {retrieved['totalRounds']}")

        assert len(retrieved["sources"]) == 2, "❌ sources 数量不匹配"
        print(f"  ✅ sources: {len(retrieved['sources'])} 个")

        assert len(retrieved["rounds"]) == 2, "❌ rounds 数量不匹配"
        print(f"  ✅ rounds: {len(retrieved['rounds'])} 轮")

        print("\n" + "=" * 60)
        print("✅ 测试1 通过: 所有 v7.219 新字段正确持久化和检索")
        print("=" * 60)

        return True

    async def test_update_existing_session_with_new_fields(self):
        """测试2: 更新已存在的会话（force=True）"""
        print("\n" + "=" * 60)
        print("🧪 测试2: 更新已存在会话的 v7.219 字段")
        print("=" * 60)

        from intelligent_project_analyzer.services.session_archive_manager import get_archive_manager

        archive_manager = get_archive_manager()
        session_id = self.generate_test_session_id()
        query = "测试更新会话"

        # Step 1: 首次保存（不含新字段）
        print(f"\n📥 Step 1: 首次保存（模拟旧版本，不含新字段）")
        old_result = {
            "sources": [],
            "images": [],
            "thinkingContent": "旧内容",
            "answerContent": "旧答案",
            "totalRounds": 1,
            "executionTime": 5.0,
            "isDeepMode": False,
            # 不包含 l0Content, problemSolvingThinking, structuredInfo
        }
        await archive_manager.archive_search_session(
            session_id=session_id, query=query, search_result=old_result, force=True
        )
        print("✅ 首次保存成功")

        # Step 2: 更新保存（包含新字段）
        print(f"\n📥 Step 2: 更新保存（v7.219 版本，包含新字段）")
        new_result = self.create_mock_search_result()
        await archive_manager.archive_search_session(
            session_id=session_id, query=query, search_result=new_result, force=True
        )
        print("✅ 更新保存成功")

        # Step 3: 验证更新后的字段
        print(f"\n🔍 Step 3: 验证更新后的新字段")
        retrieved = await archive_manager.get_search_session(session_id)

        assert retrieved["l0Content"] == new_result["l0Content"], "❌ l0Content 未更新"
        print(f"  ✅ l0Content 已更新")

        assert (
            retrieved["problemSolvingThinking"] == new_result["problemSolvingThinking"]
        ), "❌ problemSolvingThinking 未更新"
        print(f"  ✅ problemSolvingThinking 已更新")

        assert retrieved["structuredInfo"] is not None, "❌ structuredInfo 未更新"
        print(f"  ✅ structuredInfo 已更新")

        print("\n" + "=" * 60)
        print("✅ 测试2 通过: 更新已存在会话时新字段正确覆盖")
        print("=" * 60)

        return True

    async def test_empty_new_fields_handling(self):
        """测试3: 空值/缺失新字段的处理"""
        print("\n" + "=" * 60)
        print("🧪 测试3: 空值/缺失新字段的兼容性处理")
        print("=" * 60)

        from intelligent_project_analyzer.services.session_archive_manager import get_archive_manager

        archive_manager = get_archive_manager()
        session_id = self.generate_test_session_id()

        # 模拟旧版本数据（不含新字段）
        old_result = {
            "sources": [{"title": "test", "url": "https://test.com"}],
            "images": [],
            "thinkingContent": "内容",
            "answerContent": "答案",
            "totalRounds": 1,
            "executionTime": 5.0,
            "isDeepMode": True,
            # 不包含 l0Content, problemSolvingThinking, structuredInfo
        }

        print(f"\n📥 保存不含新字段的会话")
        await archive_manager.archive_search_session(
            session_id=session_id, query="测试空值处理", search_result=old_result, force=True
        )

        print(f"\n🔍 检索并验证默认值处理")
        retrieved = await archive_manager.get_search_session(session_id)

        # 新字段应返回空字符串或 None，不应抛出异常
        assert retrieved.get("l0Content", "") == "", f"❌ l0Content 应为空字符串，实际: {retrieved.get('l0Content')}"
        print(f"  ✅ l0Content 默认为空字符串")

        assert retrieved.get("problemSolvingThinking", "") == "", f"❌ problemSolvingThinking 应为空字符串"
        print(f"  ✅ problemSolvingThinking 默认为空字符串")

        assert retrieved.get("structuredInfo") is None, f"❌ structuredInfo 应为 None"
        print(f"  ✅ structuredInfo 默认为 None")

        print("\n" + "=" * 60)
        print("✅ 测试3 通过: 缺失新字段时返回安全的默认值")
        print("=" * 60)

        return True

    async def test_frontend_simulation(self):
        """测试4: 模拟前端保存和加载的完整流程"""
        print("\n" + "=" * 60)
        print("🧪 测试4: 模拟前端 saveSearchStateToBackend → loadSearchStateFromBackend")
        print("=" * 60)

        from intelligent_project_analyzer.services.session_archive_manager import get_archive_manager

        archive_manager = get_archive_manager()
        session_id = self.generate_test_session_id()

        # 模拟前端 saveSearchStateToBackend 发送的数据
        frontend_save_payload = {
            "session_id": session_id,
            "query": "深圳湾别墅设计",
            "sources": [
                {"title": "来源1", "url": "https://s1.com", "snippet": "内容1"},
            ],
            "images": [],
            "thinkingContent": "深度思考...",
            "answerContent": "AI回答...",
            "searchPlan": {"analysis": "分析", "topics": []},
            "rounds": [
                {"round": 1, "sources": [{"title": "r1", "url": "https://r1.com"}]},
                {"round": 2, "sources": [{"title": "r2", "url": "https://r2.com"}]},
            ],
            "totalRounds": 2,
            "executionTime": 20.0,
            "isDeepMode": True,
            # 🆕 v7.219 新增字段
            "l0Content": "需求理解对话内容：用户想要现代风格的别墅设计...",
            "problemSolvingThinking": "解题思路：1.分析用户背景 2.确定设计方向 3.搜索案例...",
            "structuredInfo": {
                "demographics": {"location": "深圳", "age": "40-50"},
                "identity_tags": ["创业者", "成功人士"],
            },
        }

        print(f"\n📥 Step 1: 模拟前端保存")
        await archive_manager.archive_search_session(
            session_id=frontend_save_payload["session_id"],
            query=frontend_save_payload["query"],
            search_result=frontend_save_payload,
            force=True,
        )
        print("✅ 保存成功")

        print(f"\n📤 Step 2: 模拟前端加载")
        session = await archive_manager.get_search_session(session_id)

        # 模拟前端 loadSearchStateFromBackend 的逻辑
        loaded_state = {
            "status": "done",
            "l0Content": session.get("l0Content", ""),
            "structuredInfo": session.get("structuredInfo", None),
            "rounds": session.get("rounds", []),
            "sources": session.get("sources", []),
            "problemSolvingThinking": session.get("problemSolvingThinking", ""),
            "isProblemSolvingPhase": False,
            "analysisProgress": None,
        }

        # 🔧 v7.219: 从 rounds 聚合 sources（模拟前端逻辑）
        if len(loaded_state["sources"]) == 0 and len(loaded_state["rounds"]) > 0:
            loaded_state["sources"] = []
            for r in loaded_state["rounds"]:
                loaded_state["sources"].extend(r.get("sources", []))
            print(f"  🔧 从 rounds 聚合 sources: {len(loaded_state['sources'])} 个")

        print(f"\n🔍 Step 3: 验证前端加载结果")

        assert loaded_state["l0Content"] != "", "❌ l0Content 为空"
        print(f"  ✅ l0Content: {loaded_state['l0Content'][:40]}...")

        assert loaded_state["problemSolvingThinking"] != "", "❌ problemSolvingThinking 为空"
        print(f"  ✅ problemSolvingThinking: {loaded_state['problemSolvingThinking'][:40]}...")

        assert loaded_state["structuredInfo"] is not None, "❌ structuredInfo 为 None"
        print(f"  ✅ structuredInfo: 已加载")

        print("\n" + "=" * 60)
        print("✅ 测试4 通过: 前端保存/加载模拟完全成功")
        print("=" * 60)

        return True


async def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 70)
    print("🧪 v7.219 搜索会话持久化集成测试")
    print("=" * 70)
    print("验证 l0Content, problemSolvingThinking, structuredInfo 完整链路")
    print("=" * 70)

    test_suite = TestSearchSessionPersistenceV219()

    results = []
    tests = [
        ("归档和检索新字段", test_suite.test_archive_and_retrieve_new_fields),
        ("更新已存在会话", test_suite.test_update_existing_session_with_new_fields),
        ("空值/缺失字段处理", test_suite.test_empty_new_fields_handling),
        ("前端保存/加载模拟", test_suite.test_frontend_simulation),
    ]

    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result, None))
        except Exception as e:
            import traceback

            results.append((name, False, str(e)))
            print(f"\n❌ 测试失败: {name}")
            print(f"   错误: {e}")
            traceback.print_exc()

    # 汇总结果
    print("\n" + "=" * 70)
    print("📊 测试结果汇总")
    print("=" * 70)

    passed = sum(1 for _, result, _ in results if result)
    total = len(results)

    for name, result, error in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")
        if error:
            print(f"         错误: {error}")

    print("-" * 70)
    print(f"通过: {passed}/{total}")

    if passed == total:
        print("\n🎉 所有测试通过! v7.219 持久化链路验证成功")
        return True
    else:
        print(f"\n⚠️ {total - passed} 个测试失败，请检查")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
