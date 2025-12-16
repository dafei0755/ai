"""
系统健康检查和会员API诊断脚本
检测 WordPress + SSO + 会员API 的完整流程
"""

import httpx
import json
import sys
import io
from decouple import config

# 设置控制台输出为 UTF-8（兼容 Windows）
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

class SystemHealthChecker:
    def __init__(self):
        self.wp_base_url = config("WORDPRESS_URL", default="https://www.ucppt.com")
        self.wp_username = config("WORDPRESS_ADMIN_USERNAME", default="8pdwoxj8")
        self.wp_password = config("WORDPRESS_ADMIN_PASSWORD", default="")
        self.test_user_id = 1  # 测试用户ID
        self.jwt_token = None

        print("=" * 80)
        print("[系统诊断] WordPress SSO + 会员API 健康检查")
        print("=" * 80)
        print(f"WordPress 地址: {self.wp_base_url}")
        print(f"测试用户: {self.wp_username}")
        print("=" * 80)
        print()

    def test_1_wordpress_connectivity(self):
        """测试 1: WordPress 站点连通性"""
        print("[测试 1] 检查 WordPress 站点连通性...")
        try:
            response = httpx.get(self.wp_base_url, timeout=10, verify=False)
            if response.status_code == 200:
                print("[OK] WordPress 站点可访问")
                return True
            else:
                print(f"[FAIL] WordPress 返回状态码: {response.status_code}")
                return False
        except Exception as e:
            print(f"[FAIL] 无法连接到 WordPress: {e}")
            return False

    def test_2_jwt_token_generation(self):
        """测试 2: JWT Token 获取"""
        print("\n[测试 2] 获取 JWT Token...")
        try:
            url = f"{self.wp_base_url}/wp-json/simple-jwt-login/v1/auth"
            data = {
                "username": self.wp_username,
                "password": self.wp_password
            }

            print(f"请求 URL: {url}")
            print(f"用户名: {self.wp_username}")
            print(f"密码长度: {len(self.wp_password)} 字符")

            response = httpx.post(url, json=data, timeout=30, verify=False)
            print(f"响应状态码: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print(f"响应数据: {json.dumps(result, indent=2, ensure_ascii=False)}")

                if "data" in result and "jwt" in result["data"]:
                    self.jwt_token = result["data"]["jwt"]
                    print(f"[OK] Token 获取成功")
                    print(f"Token (前50字符): {self.jwt_token[:50]}...")
                    return True
                else:
                    print(f"[FAIL] 响应格式错误，缺少 jwt 字段")
                    return False
            else:
                error_text = response.text
                print(f"[FAIL] Token 获取失败: {error_text}")
                return False

        except Exception as e:
            print(f"[FAIL] Token 获取异常: {e}")
            import traceback
            traceback.print_exc()
            return False

    def test_3_api_endpoints_existence(self):
        """测试 3: 检查 API 端点是否存在"""
        print("\n[测试 3] 检查会员 API 端点是否注册...")

        if not self.jwt_token:
            print("[SKIP] 跳过此测试（需要先获取 Token）")
            return False

        try:
            # 测试 API 端点列表
            url = f"{self.wp_base_url}/wp-json/"
            response = httpx.get(url, timeout=10, verify=False)

            if response.status_code == 200:
                routes = response.json()

                # 检查关键路由
                custom_api_found = False
                for route_path in routes.get("routes", {}):
                    if "/custom/v1" in route_path:
                        print(f"[OK] 发现自定义 API 路由: {route_path}")
                        custom_api_found = True

                if custom_api_found:
                    print("[OK] WPCOM Member Custom API 已正确注册")
                    return True
                else:
                    print("[FAIL] 未找到 /custom/v1 路由，WPCOM Member Custom API 可能未激活")
                    return False
            else:
                print(f"[FAIL] 无法获取 API 路由列表: {response.status_code}")
                return False

        except Exception as e:
            print(f"[FAIL] 检查 API 端点异常: {e}")
            return False

    def test_4_user_membership_api(self):
        """测试 4: 调用用户会员信息 API"""
        print(f"\n[测试 4] 调用用户会员信息 API (user_id={self.test_user_id})...")

        if not self.jwt_token:
            print("[SKIP] 跳过此测试（需要先获取 Token）")
            return False

        try:
            url = f"{self.wp_base_url}/wp-json/custom/v1/user-membership/{self.test_user_id}"
            headers = {"Authorization": f"Bearer {self.jwt_token}"}

            print(f"请求 URL: {url}")
            print(f"Authorization: Bearer {self.jwt_token[:30]}...")

            response = httpx.get(url, headers=headers, timeout=30, verify=False)
            print(f"响应状态码: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print("[OK] 会员信息 API 调用成功")
                print(f"响应数据:\n{json.dumps(result, indent=2, ensure_ascii=False)}")

                # 检查关键字段
                if "membership" in result:
                    membership = result["membership"]
                    print(f"\n会员等级: {membership.get('level', 'N/A')}")
                    print(f"到期时间: {membership.get('expire_date', 'N/A')}")
                    print(f"是否激活: {membership.get('is_active', False)}")

                if "meta" in result:
                    meta = result["meta"]
                    print(f"\nMeta 数据:")
                    print(f"  wp_vip_type: {meta.get('wp_vip_type', 'N/A')}")
                    print(f"  wp_vip_end_date: {meta.get('wp_vip_end_date', 'N/A')}")

                return True
            elif response.status_code == 404:
                print(f"[FAIL] API 端点不存在 (404)")
                print("   可能原因: WPCOM Member Custom API 插件未激活或未正确配置")
                print(f"响应内容: {response.text}")
                return False
            elif response.status_code == 401:
                print(f"[FAIL] 认证失败 (401)")
                print("   可能原因: Token 无效或过期")
                print(f"响应内容: {response.text}")
                return False
            elif response.status_code == 403:
                print(f"[FAIL] 权限不足 (403)")
                print("   可能原因: Token 没有访问会员信息的权限")
                print(f"响应内容: {response.text}")
                return False
            else:
                print(f"[FAIL] 未知错误: HTTP {response.status_code}")
                print(f"响应内容: {response.text}")
                return False

        except httpx.TimeoutException as e:
            print(f"[FAIL] 请求超时: {e}")
            return False
        except Exception as e:
            print(f"[FAIL] 调用 API 异常: {e}")
            import traceback
            traceback.print_exc()
            return False

    def test_5_wallet_api(self):
        """测试 5: 调用用户钱包信息 API"""
        print(f"\n[测试 5] 调用用户钱包信息 API (user_id={self.test_user_id})...")

        if not self.jwt_token:
            print("[SKIP] 跳过此测试（需要先获取 Token）")
            return False

        try:
            url = f"{self.wp_base_url}/wp-json/custom/v1/user-wallet/{self.test_user_id}"
            headers = {"Authorization": f"Bearer {self.jwt_token}"}

            response = httpx.get(url, headers=headers, timeout=30, verify=False)
            print(f"响应状态码: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                print("[OK] 钱包信息 API 调用成功")
                print(f"响应数据:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
                return True
            else:
                print(f"[WARN] 钱包 API 调用失败: {response.status_code}")
                print(f"响应内容: {response.text}")
                return False

        except Exception as e:
            print(f"[WARN] 钱包 API 调用异常: {e}")
            return False

    def run_all_tests(self):
        """运行所有测试"""
        results = {}

        results["test_1"] = self.test_1_wordpress_connectivity()
        results["test_2"] = self.test_2_jwt_token_generation()
        results["test_3"] = self.test_3_api_endpoints_existence()
        results["test_4"] = self.test_4_user_membership_api()
        results["test_5"] = self.test_5_wallet_api()

        # 汇总报告
        print("\n" + "=" * 80)
        print("[测试汇总] 结果统计")
        print("=" * 80)

        total_tests = len(results)
        passed_tests = sum(1 for v in results.values() if v)

        for test_name, passed in results.items():
            status = "[OK] 通过" if passed else "[FAIL] 失败"
            print(f"{test_name}: {status}")

        print("-" * 80)
        print(f"总计: {passed_tests}/{total_tests} 通过")
        print("=" * 80)

        # 诊断建议
        print("\n[诊断建议]")

        if not results["test_1"]:
            print("- [FAIL] WordPress 站点无法访问，请检查网络连接或站点状态")

        if not results["test_2"]:
            print("- [FAIL] JWT Token 获取失败，请检查:")
            print("  1. Simple JWT Login 插件是否已激活")
            print("  2. .env 中的 WORDPRESS_USERNAME 和 WORDPRESS_PASSWORD 是否正确")
            print("  3. JWT 密钥配置是否正确")

        if not results["test_3"]:
            print("- [FAIL] 自定义 API 端点未注册，请检查:")
            print("  1. WPCOM Member Custom API 插件是否已激活")
            print("  2. 插件是否正确注册了 REST API 路由")

        if not results["test_4"]:
            print("- [FAIL] 会员信息 API 调用失败，请检查:")
            print("  1. WPCOM Member Custom API 插件是否已激活")
            print("  2. Token 是否有访问会员信息的权限")
            print("  3. 测试用户ID是否存在")

        if all(results.values()):
            print("[OK] 所有测试通过！系统运行正常。")

        print()

if __name__ == "__main__":
    try:
        checker = SystemHealthChecker()
        checker.run_all_tests()
    except KeyboardInterrupt:
        print("\n\n[WARN] 测试被用户中断")
    except Exception as e:
        print(f"\n\n[FAIL] 测试脚本异常: {e}")
        import traceback
        traceback.print_exc()
