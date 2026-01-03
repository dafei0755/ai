#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
会话历史清理脚本
清理所有异常或未完整执行的会话数据

清理范围：
1. 状态异常的会话（failed, error, timeout等）
2. 未完成的会话（processing超过24小时）
3. 测试会话（project_name包含"测试"）
4. 孤立会话（无user_id或user_id异常）
5. 空会话（无任何数据）
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Set

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 设置UTF-8输出
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from intelligent_project_analyzer.services.device_session_manager import DeviceSessionManager
from intelligent_project_analyzer.services.session_archive_manager import SessionArchiveManager
from intelligent_project_analyzer.settings import settings


class SessionHistoryCleaner:
    """会话历史清理器"""

    def __init__(self):
        self.session_manager = DeviceSessionManager()
        self.archive_manager = None

        # 初始化归档管理器
        if settings.ENABLE_SESSION_ARCHIVE:
            try:
                self.archive_manager = SessionArchiveManager(settings.ARCHIVE_DB_PATH)
                print("✓ 归档管理器已初始化")
            except Exception as e:
                print(f"⚠ 归档管理器初始化失败: {e}")

        # 清理统计
        self.stats = {"total_active": 0, "total_archived": 0, "deleted_active": 0, "deleted_archived": 0, "failed": 0}

        # 异常会话标准
        self.ABNORMAL_STATUSES = {"failed", "error", "timeout", "cancelled", "aborted"}

        self.TEST_KEYWORDS = ["测试", "test", "demo", "example", "样例", "临时", "temp", "tmp", "调试", "debug"]

    async def initialize(self):
        """异步初始化"""
        # Redis连接检查
        try:
            await self.session_manager.redis.ping()
            print("✓ Redis连接成功")
        except Exception as e:
            print(f"✗ Redis连接失败: {e}")
            raise

        # 归档数据库检查
        if self.archive_manager:
            try:
                await self.archive_manager.initialize()
                print("✓ 归档数据库连接成功")
            except Exception as e:
                print(f"⚠ 归档数据库连接失败: {e}")

    def is_abnormal_session(self, session: Dict, session_type: str = "active") -> tuple[bool, str]:
        """
        判断会话是否异常

        Returns:
            (is_abnormal, reason)
        """
        # 1. 检查状态
        status = session.get("status", "unknown").lower()
        if status in self.ABNORMAL_STATUSES:
            return True, f"异常状态: {status}"

        # 2. 检查未完成的会话（超过24小时仍在processing）
        if status == "processing":
            created_at = session.get("created_at")
            if created_at:
                try:
                    if isinstance(created_at, str):
                        created_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    else:
                        created_time = datetime.fromtimestamp(created_at)

                    if datetime.now() - created_time > timedelta(hours=24):
                        return True, "超时未完成（>24小时）"
                except Exception:
                    pass

        # 3. 检查测试会话
        project_name = session.get("project_name", "").lower()
        if any(keyword in project_name for keyword in self.TEST_KEYWORDS):
            return True, f"测试会话: {session.get('project_name', 'N/A')}"

        # 4. 检查空会话（无关键数据）
        has_roles = bool(session.get("roles"))
        has_dimensions = bool(session.get("dimensions"))
        has_tasks = bool(session.get("tasks"))

        if not (has_roles or has_dimensions or has_tasks):
            # 检查创建时间，如果创建超过1小时仍为空，则认为异常
            created_at = session.get("created_at")
            if created_at:
                try:
                    if isinstance(created_at, str):
                        created_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    else:
                        created_time = datetime.fromtimestamp(created_at)

                    if datetime.now() - created_time > timedelta(hours=1):
                        return True, "空会话（无数据且>1小时）"
                except Exception:
                    pass

        # 5. 检查user_id异常（仅活跃会话）
        if session_type == "active":
            user_id = session.get("user_id", "")
            # 允许 web_user，但检查完全空值或异常值
            if not user_id or user_id in ["null", "undefined", "None"]:
                return True, f"异常user_id: {user_id}"

        return False, ""

    async def scan_active_sessions(self) -> tuple[List[str], Dict[str, str]]:
        """
        扫描活跃会话，返回需要清理的会话列表

        Returns:
            (session_ids, reasons)
        """
        print("\n" + "=" * 60)
        print("扫描活跃会话（Redis）...")
        print("=" * 60)

        to_delete = []
        reasons = {}

        try:
            # 获取所有会话ID
            all_session_ids = await self.session_manager.get_all_session_ids()
            self.stats["total_active"] = len(all_session_ids)

            print(f"→ 找到 {len(all_session_ids)} 个活跃会话")

            for session_id in all_session_ids:
                try:
                    session = await self.session_manager.get_session(session_id)

                    if not session:
                        print(f"  ⚠ 跳过无法读取的会话: {session_id[:8]}...")
                        continue

                    is_abnormal, reason = self.is_abnormal_session(session, "active")

                    if is_abnormal:
                        to_delete.append(session_id)
                        reasons[session_id] = reason

                        user_id = session.get("user_id", "N/A")
                        project_name = session.get("project_name", "N/A")
                        status = session.get("status", "N/A")

                        print(f"  ✗ {session_id[:8]}... | {user_id} | {project_name} | {status}")
                        print(f"    原因: {reason}")

                except Exception as e:
                    print(f"  ⚠ 扫描会话失败: {session_id[:8]}... | {e}")
                    continue

            print(f"\n→ 发现 {len(to_delete)} 个异常活跃会话")

        except Exception as e:
            print(f"✗ 扫描活跃会话失败: {e}")

        return to_delete, reasons

    async def scan_archived_sessions(self) -> tuple[List[str], Dict[str, str]]:
        """
        扫描归档会话，返回需要清理的会话列表

        Returns:
            (session_ids, reasons)
        """
        print("\n" + "=" * 60)
        print("扫描归档会话（SQLite）...")
        print("=" * 60)

        to_delete = []
        reasons = {}

        if not self.archive_manager:
            print("⚠ 归档管理器未启用，跳过")
            return to_delete, reasons

        try:
            # 获取所有归档会话
            all_sessions = await self.archive_manager.list_archived_sessions(limit=10000, offset=0)  # 获取所有

            sessions = all_sessions.get("sessions", [])
            self.stats["total_archived"] = len(sessions)

            print(f"→ 找到 {len(sessions)} 个归档会话")

            for session in sessions:
                try:
                    session_id = session.get("session_id")
                    if not session_id:
                        continue

                    is_abnormal, reason = self.is_abnormal_session(session, "archived")

                    if is_abnormal:
                        to_delete.append(session_id)
                        reasons[session_id] = reason

                        user_id = session.get("user_id", "N/A")
                        project_name = session.get("project_name", "N/A")
                        status = session.get("status", "N/A")

                        print(f"  ✗ {session_id[:8]}... | {user_id} | {project_name} | {status}")
                        print(f"    原因: {reason}")

                except Exception as e:
                    print(f"  ⚠ 扫描归档会话失败: {e}")
                    continue

            print(f"\n→ 发现 {len(to_delete)} 个异常归档会话")

        except Exception as e:
            print(f"✗ 扫描归档会话失败: {e}")

        return to_delete, reasons

    async def delete_active_sessions(self, session_ids: List[str]) -> int:
        """删除活跃会话"""
        if not session_ids:
            return 0

        print("\n" + "=" * 60)
        print(f"删除活跃会话（共 {len(session_ids)} 个）...")
        print("=" * 60)

        deleted = 0
        for session_id in session_ids:
            try:
                success = await self.session_manager.delete_session(session_id)

                if success:
                    deleted += 1
                    print(f"  ✓ 已删除: {session_id[:8]}...")
                else:
                    print(f"  ✗ 删除失败: {session_id[:8]}...")
                    self.stats["failed"] += 1

            except Exception as e:
                print(f"  ✗ 删除异常: {session_id[:8]}... | {e}")
                self.stats["failed"] += 1

        self.stats["deleted_active"] = deleted
        print(f"\n→ 成功删除 {deleted} 个活跃会话")
        return deleted

    async def delete_archived_sessions(self, session_ids: List[str]) -> int:
        """删除归档会话"""
        if not session_ids or not self.archive_manager:
            return 0

        print("\n" + "=" * 60)
        print(f"删除归档会话（共 {len(session_ids)} 个）...")
        print("=" * 60)

        deleted = 0
        for session_id in session_ids:
            try:
                success = await self.archive_manager.delete_archived_session(session_id)

                if success:
                    deleted += 1
                    print(f"  ✓ 已删除: {session_id[:8]}...")
                else:
                    print(f"  ✗ 删除失败: {session_id[:8]}...")
                    self.stats["failed"] += 1

            except Exception as e:
                print(f"  ✗ 删除异常: {session_id[:8]}... | {e}")
                self.stats["failed"] += 1

        self.stats["deleted_archived"] = deleted
        print(f"\n→ 成功删除 {deleted} 个归档会话")
        return deleted

    def print_summary(self):
        """打印清理摘要"""
        print("\n" + "=" * 60)
        print("清理摘要")
        print("=" * 60)
        print(f"活跃会话: {self.stats['total_active']} 个 → 删除 {self.stats['deleted_active']} 个")
        print(f"归档会话: {self.stats['total_archived']} 个 → 删除 {self.stats['deleted_archived']} 个")
        print(f"失败: {self.stats['failed']} 个")
        print("=" * 60)

        total_deleted = self.stats["deleted_active"] + self.stats["deleted_archived"]
        if total_deleted > 0:
            print(f"✓ 成功清理 {total_deleted} 个异常会话")
        else:
            print("✓ 无需清理，所有会话状态正常")

    async def run(self, auto_confirm: bool = False):
        """执行清理流程"""
        print("=" * 60)
        print("会话历史清理工具")
        print("=" * 60)
        print("\n清理标准:")
        print("  1. 状态异常（failed, error, timeout等）")
        print("  2. 超时未完成（processing > 24小时）")
        print("  3. 测试会话（包含测试关键词）")
        print("  4. 空会话（无数据且 > 1小时）")
        print("  5. 异常user_id（null, undefined等）")
        print()

        try:
            # 初始化
            await self.initialize()

            # 扫描异常会话
            active_to_delete, active_reasons = await self.scan_active_sessions()
            archived_to_delete, archived_reasons = await self.scan_archived_sessions()

            total_to_delete = len(active_to_delete) + len(archived_to_delete)

            if total_to_delete == 0:
                print("\n✓ 未发现异常会话，无需清理")
                return

            # 确认删除
            if not auto_confirm:
                print("\n" + "=" * 60)
                print(f"⚠️  即将删除 {total_to_delete} 个异常会话")
                print("=" * 60)
                print(f"  活跃会话: {len(active_to_delete)} 个")
                print(f"  归档会话: {len(archived_to_delete)} 个")
                print()

                confirm = input("确认删除？[y/N]: ").strip().lower()

                if confirm != "y":
                    print("\n✗ 用户取消，未执行删除操作")
                    return

            # 执行删除
            await self.delete_active_sessions(active_to_delete)
            await self.delete_archived_sessions(archived_to_delete)

            # 打印摘要
            self.print_summary()

        except KeyboardInterrupt:
            print("\n\n⚠ 用户中断")
        except Exception as e:
            print(f"\n✗ 清理失败: {e}")
            import traceback

            traceback.print_exc()
        finally:
            # 清理资源
            if self.archive_manager:
                await self.archive_manager.close()


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="清理异常会话历史")
    parser.add_argument("--auto-confirm", "-y", action="store_true", help="自动确认，不询问")
    parser.add_argument("--dry-run", action="store_true", help="仅扫描，不删除")

    args = parser.parse_args()

    cleaner = SessionHistoryCleaner()

    if args.dry_run:
        print("⚠️  DRY RUN 模式 - 仅扫描，不执行删除\n")
        await cleaner.initialize()
        await cleaner.scan_active_sessions()
        await cleaner.scan_archived_sessions()
    else:
        await cleaner.run(auto_confirm=args.auto_confirm)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠ 程序被用户中断")
    except Exception as e:
        print(f"\n✗ 程序异常: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
