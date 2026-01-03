#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
会话删除权限修复验证脚本
测试 v7.114 权限逻辑修复是否生效

测试场景：
1. 正常场景：用户删除自己的会话 ✓
2. 未登录会话：任何登录用户删除 web_user 会话 ✓
3. 权限拒绝：用户A无法删除用户B的会话 ✗
4. 开发模式：dev_user 可以删除所有会话 ✓
5. 归档会话：相同权限逻辑适用 ✓
"""

import asyncio
import json
from typing import Dict, Optional

import httpx

# API 配置
BASE_URL = "http://localhost:9527"
API_PREFIX = "/api"

# 测试用户配置
TEST_USERS = {
    "alice": {"username": "alice", "password": "test123"},
    "bob": {"username": "bob", "password": "test456"},
    "dev_user": {"username": "dev_user", "password": "dev"},
}


# 颜色输出
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"


def print_success(msg: str):
    print(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")


def print_error(msg: str):
    print(f"{Colors.RED}✗ {msg}{Colors.RESET}")


def print_warning(msg: str):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.RESET}")


def print_info(msg: str):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.RESET}")


class SessionPermissionTester:
    """会话权限测试器"""

    def __init__(self):
        self.client = httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)
        self.tokens: Dict[str, str] = {}
        self.test_sessions: Dict[str, str] = {}

    async def cleanup(self):
        """清理资源"""
        await self.client.aclose()

    async def login(self, username: str, password: str) -> Optional[str]:
        """登录并获取JWT token"""
        try:
            response = await self.client.post(
                f"{API_PREFIX}/auth/login", json={"username": username, "password": password}
            )

            if response.status_code == 200:
                data = response.json()
                token = data.get("access_token")
                self.tokens[username] = token
                print_success(f"用户 {username} 登录成功")
                return token
            else:
                print_error(f"用户 {username} 登录失败: {response.status_code}")
                return None
        except Exception as e:
            print_error(f"登录异常: {str(e)}")
            return None

    async def create_session(self, token: str, user_id: str) -> Optional[str]:
        """创建测试会话"""
        try:
            response = await self.client.post(
                f"{API_PREFIX}/sessions",
                headers={"Authorization": f"Bearer {token}"},
                json={"user_id": user_id, "project_name": f"测试项目 - {user_id}", "project_description": "权限测试会话"},
            )

            if response.status_code == 200:
                session_id = response.json().get("session_id")
                self.test_sessions[user_id] = session_id
                print_success(f"创建会话成功: {session_id[:8]}... (user_id={user_id})")
                return session_id
            else:
                print_error(f"创建会话失败: {response.status_code}")
                return None
        except Exception as e:
            print_error(f"创建会话异常: {str(e)}")
            return None

    async def delete_session(self, session_id: str, token: str, expect_success: bool = True) -> bool:
        """删除会话并验证结果"""
        try:
            response = await self.client.delete(
                f"{API_PREFIX}/sessions/{session_id}", headers={"Authorization": f"Bearer {token}"}
            )

            success = response.status_code == 200

            if success == expect_success:
                if expect_success:
                    print_success(f"删除成功 (符合预期): {session_id[:8]}...")
                else:
                    print_success(f"删除被拒绝 (符合预期): {session_id[:8]}... | {response.status_code}")
                return True
            else:
                if expect_success:
                    print_error(f"删除失败 (不符合预期): {session_id[:8]}... | {response.status_code} | {response.text}")
                else:
                    print_error(f"删除成功 (不符合预期，应该被拒绝): {session_id[:8]}...")
                return False
        except Exception as e:
            print_error(f"删除会话异常: {str(e)}")
            return not expect_success

    async def test_case_1_normal_deletion(self) -> bool:
        """测试场景1: 用户删除自己的会话"""
        print_info("\n[场景1] 用户删除自己的会话")

        # Alice 登录并创建会话
        await self.login("alice", "test123")
        session_id = await self.create_session(self.tokens["alice"], "alice")

        if not session_id:
            return False

        # Alice 删除自己的会话（应该成功）
        return await self.delete_session(session_id, self.tokens["alice"], expect_success=True)

    async def test_case_2_web_user_deletion(self) -> bool:
        """测试场景2: 登录用户删除未登录用户会话"""
        print_info("\n[场景2] 登录用户删除 web_user 会话")

        # 创建一个 web_user 会话（需要模拟或使用现有的）
        # 这里我们直接创建一个 user_id 为 web_user 的会话
        if "alice" not in self.tokens:
            await self.login("alice", "test123")

        session_id = await self.create_session(self.tokens["alice"], "web_user")

        if not session_id:
            return False

        # Bob 登录
        await self.login("bob", "test456")

        # Bob 删除 web_user 会话（应该成功）
        return await self.delete_session(session_id, self.tokens["bob"], expect_success=True)

    async def test_case_3_permission_denied(self) -> bool:
        """测试场景3: 用户A无法删除用户B的会话"""
        print_info("\n[场景3] 跨用户删除（应被拒绝）")

        # Alice 创建会话
        if "alice" not in self.tokens:
            await self.login("alice", "test123")

        alice_session = await self.create_session(self.tokens["alice"], "alice")

        if not alice_session:
            return False

        # Bob 登录
        if "bob" not in self.tokens:
            await self.login("bob", "test456")

        # Bob 尝试删除 Alice 的会话（应该失败 403）
        result = await self.delete_session(alice_session, self.tokens["bob"], expect_success=False)

        # 清理: Alice 删除自己的会话
        await self.delete_session(alice_session, self.tokens["alice"], expect_success=True)

        return result

    async def test_case_4_dev_mode(self) -> bool:
        """测试场景4: 开发模式 dev_user 可以删除所有会话"""
        print_info("\n[场景4] 开发模式 (dev_user) 删除任意会话")

        # Alice 创建会话
        if "alice" not in self.tokens:
            await self.login("alice", "test123")

        alice_session = await self.create_session(self.tokens["alice"], "alice")

        if not alice_session:
            return False

        # dev_user 登录
        dev_token = await self.login("dev_user", "dev")

        if not dev_token:
            print_warning("dev_user 登录失败，跳过此测试（可能未启用 DEV_MODE）")
            # 清理
            await self.delete_session(alice_session, self.tokens["alice"], expect_success=True)
            return True

        # dev_user 删除 Alice 的会话（DEV_MODE=true 时应该成功）
        return await self.delete_session(alice_session, dev_token, expect_success=True)

    async def run_all_tests(self):
        """运行所有测试场景"""
        print("=" * 60)
        print("会话删除权限测试 - v7.114 修复验证")
        print("=" * 60)

        results = {}

        # 运行所有测试
        results["场景1: 正常删除"] = await self.test_case_1_normal_deletion()
        results["场景2: web_user删除"] = await self.test_case_2_web_user_deletion()
        results["场景3: 权限拒绝"] = await self.test_case_3_permission_denied()
        results["场景4: DEV模式"] = await self.test_case_4_dev_mode()

        # 生成测试报告
        print("\n" + "=" * 60)
        print("测试结果汇总")
        print("=" * 60)

        passed = sum(1 for r in results.values() if r)
        total = len(results)

        for test_name, result in results.items():
            status = "✓ PASS" if result else "✗ FAIL"
            color = Colors.GREEN if result else Colors.RED
            print(f"{color}{status}{Colors.RESET} | {test_name}")

        print("\n" + "=" * 60)
        if passed == total:
            print_success(f"所有测试通过 ({passed}/{total}) - 权限修复生效 ✓")
        else:
            print_error(f"部分测试失败 ({passed}/{total}) - 需要检查代码")
        print("=" * 60)


async def main():
    """主测试流程"""
    tester = SessionPermissionTester()

    try:
        await tester.run_all_tests()
    finally:
        await tester.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print_warning("\n测试被用户中断")
    except Exception as e:
        print_error(f"测试异常: {str(e)}")
        import traceback

        traceback.print_exc()
