"""
快速测试：验证 search_references 字段修复 (v7.113)

这是一个最小化的测试脚本，用于快速验证修复是否生效。
"""


import requests


def test_search_references_field():
    """测试 search_references 字段是否存在"""

    print("🧪 测试: search_references 字段修复验证")
    print("-" * 60)

    # 配置
    BASE_URL = "http://localhost:8000"

    # 测试用的session_id（需要替换为实际的）
    # 你可以通过以下方式获取：
    # curl http://localhost:8000/api/debug/sessions
    SESSION_ID = "your-session-id-here"

    # 如果没有提供session_id，尝试自动获取
    if SESSION_ID == "your-session-id-here":
        print("📝 未提供 session_id，尝试自动获取...")
        try:
            resp = requests.get(f"{BASE_URL}/api/debug/sessions", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                sessions = data.get("active_sessions", [])
                if sessions:
                    SESSION_ID = sessions[0]
                    print(f"✅ 自动获取到 session_id: {SESSION_ID[:20]}...")
                else:
                    print("❌ 未找到活跃会话")
                    print("   请先运行一次分析任务，或手动指定 SESSION_ID")
                    return False
        except Exception as e:
            print(f"❌ 无法连接到服务器: {e}")
            return False

    # 测试API请求
    print(f"\n📡 请求: GET /api/analysis/report/{SESSION_ID[:20]}...")

    try:
        response = requests.get(f"{BASE_URL}/api/analysis/report/{SESSION_ID}", timeout=30)

        if response.status_code != 200:
            print(f"❌ API请求失败: HTTP {response.status_code}")
            return False

        data = response.json()

        # 检查 structured_report
        if "structured_report" not in data:
            print("❌ 响应中缺少 structured_report")
            return False

        structured_report = data["structured_report"]

        if structured_report is None:
            print("⚠️  structured_report 为 null (分析可能未完成)")
            return False

        # 核心测试：检查 search_references 字段
        if "search_references" not in structured_report:
            print("❌ 修复失败: 缺少 search_references 字段")
            print("   提示: 请检查 server.py 中的修改是否已保存")
            return False

        search_refs = structured_report["search_references"]

        # 验证通过
        print("\n✅ 字段验证通过: search_references 存在")

        # 显示数据统计
        if search_refs is None:
            print("   状态: null (该会话可能未调用搜索工具)")
        elif isinstance(search_refs, list):
            print("   状态: 列表")
            print(f"   数量: {len(search_refs)} 条引用")

            if len(search_refs) > 0:
                # 显示第一条引用的信息
                first = search_refs[0]
                print("\n   示例引用:")
                print(f"   - 工具: {first.get('source_tool', 'N/A')}")
                print(f"   - 标题: {first.get('title', 'N/A')[:60]}...")
                print(f"   - 查询: {first.get('query', 'N/A')}")
                print(f"   - 交付物: {first.get('deliverable_id', 'N/A')}")
        else:
            print(f"   ⚠️  类型异常: {type(search_refs)}")

        print("\n" + "=" * 60)
        print("🎉 修复验证成功！")
        print("=" * 60)
        print("\n下一步:")
        print("1. 在浏览器中打开报告页面验证前端展示")
        print("2. 运行完整验证脚本: python verify_search_references_fix.py")
        print("3. 如果需要，创建前端展示组件")

        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_search_references_field()
    exit(0 if success else 1)
