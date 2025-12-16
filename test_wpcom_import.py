"""
测试 wpcom_member_api 模块导入和初始化
"""
import sys
import os

# 添加项目根目录到路径
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print("=" * 60)
print("测试 WPCOMMemberAPI 模块")
print("=" * 60)

try:
    print("\n[1] 导入模块...")
    from wpcom_member_api import WPCOMMemberAPI
    print("[OK] 模块导入成功")

    print("\n[2] 实例化 API 客户端...")
    api = WPCOMMemberAPI()
    print("[OK] API 客户端实例化成功")

    print("\n[3] 尝试获取 Token...")
    try:
        token = api.get_token()
        print(f"[OK] Token 获取成功")
        print(f"Token (前50字符): {token[:50]}...")
    except Exception as e:
        print(f"[FAIL] Token 获取失败: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)

except Exception as e:
    print(f"[ERROR] 测试失败: {e}")
    import traceback
    traceback.print_exc()
