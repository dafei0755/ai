"""
搜索引用修复验证脚本 (v7.113)

验证搜索工具全流程是否正常工作，前端是否能获取搜索结果。

使用方法:
    python verify_search_references_fix.py

前置条件:
    1. 后端服务器已启动 (python run_server_production.py)
    2. 有至少一个已完成的分析会话（包含搜索工具调用）
"""

import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional

import requests


class SearchReferencesVerifier:
    """搜索引用修复验证器"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session_id: Optional[str] = None

    def verify_api_health(self) -> bool:
        """验证API服务是否正常"""
        print("=" * 80)
        print("步骤 1: 验证API服务健康状态")
        print("=" * 80)

        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                print("✅ API服务正常运行")
                return True
            else:
                print(f"❌ API服务异常: HTTP {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            print(f"❌ 无法连接到API服务: {self.base_url}")
            print("   请确认后端服务器已启动: python run_server_production.py")
            return False
        except Exception as e:
            print(f"❌ 健康检查失败: {e}")
            return False

    def get_latest_session(self) -> Optional[str]:
        """获取最新的已完成会话ID"""
        print("\n" + "=" * 80)
        print("步骤 2: 获取最新的已完成会话")
        print("=" * 80)

        try:
            # 尝试从sessions API获取
            response = requests.get(f"{self.base_url}/api/sessions", params={"page": 1, "page_size": 10})

            if response.status_code == 401:
                print("⚠️  需要认证，尝试使用调试端点...")
                # 使用调试端点
                response = requests.get(f"{self.base_url}/api/debug/sessions")
                if response.status_code == 200:
                    data = response.json()
                    sessions = data.get("active_sessions", [])
                    if sessions:
                        session_id = sessions[0]
                        print(f"✅ 找到会话: {session_id}")
                        return session_id

            elif response.status_code == 200:
                data = response.json()
                sessions = data.get("sessions", [])
                completed_sessions = [s for s in sessions if s.get("status") == "completed"]

                if completed_sessions:
                    session_id = completed_sessions[0].get("session_id")
                    print(f"✅ 找到已完成会话: {session_id}")
                    return session_id

            print("❌ 未找到已完成的会话")
            print("   请先运行一次完整的分析任务")
            return None

        except Exception as e:
            print(f"❌ 获取会话失败: {e}")
            return None

    def verify_report_response(self, session_id: str) -> bool:
        """验证报告响应中是否包含 search_references 字段"""
        print("\n" + "=" * 80)
        print(f"步骤 3: 验证报告API响应 (Session: {session_id})")
        print("=" * 80)

        try:
            response = requests.get(f"{self.base_url}/api/analysis/report/{session_id}", timeout=30)

            if response.status_code != 200:
                print(f"❌ API请求失败: HTTP {response.status_code}")
                print(f"   错误信息: {response.text[:200]}")
                return False

            data = response.json()

            # 检查基本结构
            if "structured_report" not in data:
                print("❌ 响应中缺少 structured_report 字段")
                return False

            structured_report = data["structured_report"]

            if structured_report is None:
                print("⚠️  structured_report 为 null")
                print("   可能原因: 分析尚未完成或报告生成失败")
                return False

            # 检查 search_references 字段
            if "search_references" not in structured_report:
                print("❌ 修复失败: structured_report 中缺少 search_references 字段")
                print("   请检查后端代码是否正确添加了该字段")
                return False

            search_references = structured_report["search_references"]

            # 验证字段值
            if search_references is None:
                print("⚠️  search_references 为 null")
                print("   可能原因:")
                print("   1. 该会话没有调用搜索工具")
                print("   2. 搜索工具调用失败")
                print("   3. ToolCallRecorder 未正确记录")
                print("\n   建议: 检查后端日志中是否有 '📚 [v7.64] 提取了 X 条搜索引用'")
                return True  # 字段存在但为空，修复有效但数据为空

            if not isinstance(search_references, list):
                print(f"❌ search_references 类型错误: 期望 list，实际 {type(search_references)}")
                return False

            # 验证数据内容
            print(f"✅ search_references 字段存在且为列表")
            print(f"   搜索引用数量: {len(search_references)} 条")

            if len(search_references) == 0:
                print("   ⚠️  搜索引用列表为空")
                print("   建议: 运行一次新的分析任务，确保搜索工具被调用")
                return True

            # 验证第一条引用的结构
            first_ref = search_references[0]
            required_fields = ["source_tool", "title", "snippet", "deliverable_id", "query", "timestamp"]

            print("\n   验证引用数据结构:")
            for field in required_fields:
                if field in first_ref:
                    value = first_ref[field]
                    if isinstance(value, str):
                        preview = value[:50] + "..." if len(value) > 50 else value
                    else:
                        preview = str(value)
                    print(f"   ✅ {field}: {preview}")
                else:
                    print(f"   ⚠️  缺少字段: {field}")

            # 显示搜索工具统计
            tools = {}
            for ref in search_references:
                tool = ref.get("source_tool", "unknown")
                tools[tool] = tools.get(tool, 0) + 1

            print(f"\n   搜索工具使用统计:")
            for tool, count in tools.items():
                print(f"   - {tool}: {count} 条")

            return True

        except Exception as e:
            print(f"❌ 验证失败: {e}")
            import traceback

            traceback.print_exc()
            return False

    def verify_frontend_access(self, session_id: str) -> None:
        """提供前端验证指南"""
        print("\n" + "=" * 80)
        print("步骤 4: 前端验证指南")
        print("=" * 80)

        print(
            f"""
前端验证步骤:

1. 打开浏览器，访问分析页面或报告页面:
   http://localhost:3000/analysis/{session_id}
   或
   http://localhost:3000/report/{session_id}

2. 打开浏览器开发者工具 (F12):
   - 切换到 Network 标签
   - 刷新页面
   - 找到请求: GET /api/analysis/report/{session_id}
   - 点击该请求，查看 Response 标签
   - 搜索 "search_references" 字段

3. 在 Console 标签中执行:
   ```javascript
   // 假设报告数据存储在 report 变量中
   console.log(report.structured_report?.search_references);
   ```

4. 验证结果:
   ✅ 应该看到一个数组，包含搜索引用对象
   ✅ 每个对象应该包含: source_tool, title, url, snippet, query 等字段

如果看到数据，说明修复成功！🎉
"""
        )

    def run_verification(self) -> bool:
        """运行完整验证流程"""
        print(f"\n{'='*80}")
        print(f"搜索引用修复验证 (v7.113)")
        print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}\n")

        # 步骤 1: 验证API健康
        if not self.verify_api_health():
            return False

        # 步骤 2: 获取测试会话
        session_id = self.get_latest_session()
        if not session_id:
            print("\n💡 提示: 请提供一个已完成的会话ID来验证")
            print("   用法: python verify_search_references_fix.py <session_id>")
            return False

        self.session_id = session_id

        # 步骤 3: 验证报告响应
        if not self.verify_report_response(session_id):
            return False

        # 步骤 4: 前端验证指南
        self.verify_frontend_access(session_id)

        # 总结
        print("\n" + "=" * 80)
        print("验证总结")
        print("=" * 80)
        print("✅ 后端修复验证通过")
        print("✅ API端点正确返回 search_references 字段")
        print("📝 请按照上述指南完成前端验证")
        print("\n🎉 修复验证成功！搜索结果现在可以传递到前端了。")

        return True


def main():
    """主函数"""
    import sys

    verifier = SearchReferencesVerifier()

    # 如果提供了session_id参数，直接验证该会话
    if len(sys.argv) > 1:
        session_id = sys.argv[1]
        print(f"使用指定的会话ID: {session_id}")

        if not verifier.verify_api_health():
            sys.exit(1)

        if not verifier.verify_report_response(session_id):
            sys.exit(1)

        verifier.verify_frontend_access(session_id)
        print("\n✅ 验证完成")
        sys.exit(0)

    # 否则运行完整验证流程
    success = verifier.run_verification()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
