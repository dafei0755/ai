"""
快速测试不同密码格式以找到正确的配置

此脚本会尝试多种密码格式来获取 JWT Token，帮助定位配置问题
"""
import httpx
import sys
from decouple import config

# 禁用 SSL 警告
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class PasswordFormatTester:
    def __init__(self):
        self.base_url = config("WORDPRESS_URL")
        self.username = config("WORDPRESS_ADMIN_USERNAME")
        # 读取原始密码（可能包含引号）
        self.password_raw = config("WORDPRESS_ADMIN_PASSWORD")

        print("=" * 80)
        print("[密码格式测试] Simple JWT Login 认证诊断")
        print("=" * 80)
        print(f"WordPress URL: {self.base_url}")
        print(f"用户名: {self.username}")
        print(f"密码（原始读取）: {self.password_raw}")
        print(f"密码长度: {len(self.password_raw)} 字符")
        print("=" * 80)
        print()

    def test_authentication(self, password_variant, description):
        """测试指定密码格式"""
        print(f"\n[测试 {description}]")
        print(f"密码值: {password_variant}")
        print(f"密码长度: {len(password_variant)} 字符")

        try:
            url = f"{self.base_url}/wp-json/simple-jwt-login/v1/auth"
            data = {
                "username": self.username,
                "password": password_variant
            }

            response = httpx.post(url, json=data, timeout=30, verify=False)

            if response.status_code == 200:
                result = response.json()
                if "data" in result and "jwt" in result["data"]:
                    token = result["data"]["jwt"]
                    print(f"[OK] 认证成功！")
                    print(f"Token (前50字符): {token[:50]}...")
                    print(f"\n✅ 找到正确的密码格式：{description}")
                    print(f"请在 .env 中使用以下配置:")
                    print(f"WORDPRESS_ADMIN_PASSWORD={password_variant}")
                    return True
                else:
                    print(f"[FAIL] 响应格式错误: {result}")
                    return False
            else:
                error_data = response.json()
                error_msg = error_data.get("data", {}).get("message", "未知错误")
                error_code = error_data.get("data", {}).get("errorCode", "N/A")
                print(f"[FAIL] HTTP {response.status_code}")
                print(f"错误信息: {error_msg}")
                print(f"错误代码: {error_code}")
                return False

        except Exception as e:
            print(f"[ERROR] 请求异常: {e}")
            return False

    def run_all_tests(self):
        """运行所有密码格式测试"""
        password_variants = []

        # 变体 1: 原始读取（包含可能的引号）
        password_variants.append((self.password_raw, "原始读取（.env 中的值）"))

        # 变体 2: 去除单引号
        if self.password_raw.startswith("'") and self.password_raw.endswith("'"):
            password_variants.append((self.password_raw[1:-1], "去除单引号"))

        # 变体 3: 去除双引号
        if self.password_raw.startswith('"') and self.password_raw.endswith('"'):
            password_variants.append((self.password_raw[1:-1], "去除双引号"))

        # 变体 4: 手动输入密码（用户确认的正确值）
        manual_password = "DRMHVswK%@NKS@ww1Sric&!e"
        if manual_password != self.password_raw:
            password_variants.append((manual_password, "手动输入值（不含引号）"))

        # 执行测试
        print("\n" + "=" * 80)
        print("[开始测试] 尝试不同的密码格式...")
        print("=" * 80)

        for idx, (password, description) in enumerate(password_variants, 1):
            if self.test_authentication(password, f"{idx}. {description}"):
                print("\n" + "=" * 80)
                print("✅ 测试成功！已找到正确的密码格式。")
                print("=" * 80)
                return True

        print("\n" + "=" * 80)
        print("❌ 所有密码格式测试均失败")
        print("=" * 80)
        print("\n可能的原因:")
        print("1. Simple JWT Login 插件未激活")
        print("2. 用户 '{}' 没有使用 Simple JWT Login 的权限".format(self.username))
        print("3. 密码确实不正确")
        print("4. WordPress 插件配置有问题")
        print("\n建议:")
        print("1. 检查 WordPress 后台 → 插件 → Simple JWT Login 是否已激活")
        print("2. 检查 Simple JWT Login → Settings → Allowed User Roles")
        print("3. 确认用户 '{}' 是否为管理员".format(self.username))
        print("4. 尝试在 WordPress 登录页面手动测试此用户名密码")

        return False

if __name__ == "__main__":
    try:
        tester = PasswordFormatTester()
        tester.run_all_tests()
    except KeyboardInterrupt:
        print("\n\n[WARN] 测试被用户中断")
    except Exception as e:
        print(f"\n\n[ERROR] 测试脚本异常: {e}")
        import traceback
        traceback.print_exc()
