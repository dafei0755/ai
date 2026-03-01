"""
清理搜索会话数据（archived_search_sessions）

默认：删除开发环境用户 dev_user 的深度搜索会话（is_deep_mode=1）。
可选：
- --all-search 删除所有搜索会话（不区分深度模式）
- --all-users 删除所有用户的搜索会话
支持：--dry-run 仅统计不删除。
"""

import argparse
from typing import Optional

from loguru import logger
from sqlalchemy import delete, func

from intelligent_project_analyzer.services.session_archive_manager import (
    ArchivedSearchSession,
    SessionArchiveManager,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="清理深度搜索会话 (archived_search_sessions)")
    parser.add_argument(
        "--user",
        dest="user_id",
        default="dev_user",
        help="仅删除该用户的深度搜索会话（默认 dev_user）",
    )
    parser.add_argument(
        "--all-users",
        action="store_true",
        help="删除所有用户的搜索会话（忽略 --user）",
    )
    parser.add_argument(
        "--all-search",
        action="store_true",
        help="删除所有搜索会话（不区分深度模式）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅统计，不执行删除",
    )
    return parser.parse_args()


def cleanup_deep_search_sessions(user_id: Optional[str], all_users: bool, all_search: bool, dry_run: bool) -> int:
    manager = SessionArchiveManager()
    session = manager.SessionLocal()
    try:
        query = session.query(ArchivedSearchSession)

        if not all_search:
            query = query.filter(ArchivedSearchSession.is_deep_mode == 1)

        if not all_users:
            query = query.filter(ArchivedSearchSession.user_id == user_id)

        total = query.count()

        if dry_run:
            logger.info(f"🧪 Dry-run: 将删除 {total} 条搜索会话")
            return total

        if total == 0:
            logger.info("✅ 未找到需要删除的深度搜索会话")
            return 0

        delete_stmt = delete(ArchivedSearchSession)
        if not all_search:
            delete_stmt = delete_stmt.where(ArchivedSearchSession.is_deep_mode == 1)
        if not all_users:
            delete_stmt = delete_stmt.where(ArchivedSearchSession.user_id == user_id)

        result = session.execute(delete_stmt)
        session.commit()

        deleted = result.rowcount or 0
        logger.info(f"🧹 已删除 {deleted} 条搜索会话")
        return deleted

    except Exception as exc:
        session.rollback()
        logger.error(f"❌ 清理失败: {exc}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    args = parse_args()
    target_user = None if args.all_users else args.user_id
    cleanup_deep_search_sessions(target_user, args.all_users, args.all_search, args.dry_run)
