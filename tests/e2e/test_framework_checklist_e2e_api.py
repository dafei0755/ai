"""
框架清单持久化 - 端到端测试 v7.241

测试完整的用户流程：从搜索到保存到加载
"""

import asyncio
from datetime import datetime

import httpx


async def test_e2e_api_flow():
    """测试端到端 API 流程"""
    print("=" * 80)
    print("端到端测试：API 流程 v7.241")
    print("=" * 80)

    test_session_id = f"e2e-api-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    test_query = "以HAY气质为基础，在四川峨眉山七里坪设计民宿室内概念"

    print(f"\n[Query] {test_query}")
    print(f"[Session ID] {test_session_id}")

    # 步骤 1: 通过 API 保存会话
    print("\n" + "=" * 80)
    print("步骤 1: 通过 API 保存会话")
    print("=" * 80)

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
                "frameworkChecklist": {
                    "core_summary": "如何在峨眉山七里坪融合HAY气质设计民宿",
                    "main_directions": [
                        {"direction": "品牌调研", "purpose": "了解HAY设计语言", "expected_outcome": "产品线、色彩系统、材质特点"},
                        {"direction": "空间规划", "purpose": "确定功能分区", "expected_outcome": "动线方案、区域划分"},
                    ],
                    "boundaries": ["不涉及预算规划", "不涉及施工细节"],
                    "answer_goal": "提供完整的HAY风格民宿设计概念方案",
                    "generated_at": datetime.now().isoformat(),
                },
                "searchMasterLine": {
                    "core_question": "如何在峨眉山七里坪融合HAY气质设计民宿",
                    "boundary": "不涉及预算规划、施工细节",
                    "tasks": [],
                    "task_count": 0,
                },
            },
            timeout=10.0,
        )

        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print("[OK] API save successful")
            else:
                print(f"[ERROR] API save failed: {result.get('error')}")
                return False
        else:
            print(f"[ERROR] API call failed: HTTP {response.status_code}")
            return False

    # 步骤 2: 通过 API 加载会话
    print("\n" + "=" * 80)
    print("步骤 2: 通过 API 加载会话")
    print("=" * 80)

    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://127.0.0.1:8000/api/search/session/{test_session_id}", timeout=10.0)

        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print("[OK] API load successful")
                session = result.get("session", {})
                search_result = session.get("search_result", {})

                # 验证框架清单
                if "frameworkChecklist" in search_result:
                    checklist = search_result["frameworkChecklist"]
                    if checklist:
                        print("\n[OK] Framework checklist exists")
                        print(f"  Core summary: {checklist.get('core_summary', 'N/A')}")
                        print(f"  Directions count: {len(checklist.get('main_directions', []))}")
                        print(f"  Boundaries count: {len(checklist.get('boundaries', []))}")
                        print(f"  Answer goal: {checklist.get('answer_goal', 'N/A')}")
                    else:
                        print("[ERROR] Framework checklist is empty")
                        return False
                else:
                    print("[ERROR] Missing frameworkChecklist field")
                    return False

                # 验证搜索主线
                if "searchMasterLine" in search_result:
                    master_line = search_result["searchMasterLine"]
                    if master_line:
                        print("\n[OK] Search master line exists")
                        print(f"  Core question: {master_line.get('core_question', 'N/A')}")
                        print(f"  Boundary: {master_line.get('boundary', 'N/A')}")
                    else:
                        print("[WARN] Search master line is empty")
                else:
                    print("[WARN] Missing searchMasterLine field")

                return True
            else:
                print(f"[ERROR] API load failed: {result.get('error')}")
                return False
        else:
            print(f"[ERROR] API call failed: HTTP {response.status_code}")
            return False


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("端到端测试：API 流程 v7.241")
    print("=" * 80)
    print("\n此测试将验证:")
    print("1. 通过 API 保存框架清单")
    print("2. 通过 API 加载框架清单")
    print("3. 数据完整性验证")
    print("\n开始测试...\n")

    result = asyncio.run(test_e2e_api_flow())

    print("\n" + "=" * 80)
    if result:
        print("[SUCCESS] End-to-end test passed! API flow is working!")
    else:
        print("[FAILED] End-to-end test failed! Please check logs.")
    print("=" * 80)

    exit(0 if result else 1)
