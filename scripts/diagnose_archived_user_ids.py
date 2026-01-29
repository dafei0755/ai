"""
诊断归档会话的 user_id 分布

用于排查历史对话丢失问题

使用方法:
    python scripts/diagnose_archived_user_ids.py
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import func, text

from intelligent_project_analyzer.services.session_archive_manager import ArchivedSession, SessionArchiveManager


def diagnose_user_ids():
    """诊断归档会话的 user_id 分布"""
    print("=" * 60)
    print("📊 归档会话 user_id 诊断报告")
    print("=" * 60)

    manager = SessionArchiveManager()
    db = manager._get_db()

    # 1. 统计 user_id 分布
    print("\n📈 user_id 分布统计:")
    print("-" * 40)

    results = (
        db.query(ArchivedSession.user_id, func.count(ArchivedSession.session_id).label("count"))
        .group_by(ArchivedSession.user_id)
        .order_by(text("count DESC"))
        .all()
    )

    total = 0
    for user_id, count in results:
        display_id = user_id if user_id else "(空/NULL)"
        print(f"  {display_id}: {count} 条会话")
        total += count

    print(f"\n  总计: {total} 条会话")

    # 2. 检查空 user_id 的会话
    print("\n🔍 空/web_user user_id 会话详情:")
    print("-" * 40)

    empty_sessions = (
        db.query(ArchivedSession)
        .filter(
            (ArchivedSession.user_id == None)
            | (ArchivedSession.user_id == "")
            | (ArchivedSession.user_id == "web_user")
        )
        .order_by(ArchivedSession.created_at.desc())
        .limit(10)
        .all()
    )

    if empty_sessions:
        for s in empty_sessions:
            print(f"  - {s.session_id}")
            print(f"    user_id: {s.user_id or '(空)'}")
            print(f"    created_at: {s.created_at}")
            user_input = s.user_input[:50] if s.user_input else "(空)"
            print(f"    user_input: {user_input}...")
            print()
    else:
        print("  ✅ 没有空/web_user user_id 的会话")

    # 3. 检查最近的会话
    print("\n📅 最近10条会话:")
    print("-" * 40)

    recent_sessions = db.query(ArchivedSession).order_by(ArchivedSession.created_at.desc()).limit(10).all()

    for s in recent_sessions:
        print(f"  - {s.session_id}")
        print(f"    user_id: {s.user_id or '(空)'}")
        print(f"    created_at: {s.created_at}")
        print()

    # 4. 按日期统计
    print("\n📆 按日期统计会话数量:")
    print("-" * 40)

    from sqlalchemy import Date, cast

    date_stats = (
        db.query(
            cast(ArchivedSession.created_at, Date).label("date"), func.count(ArchivedSession.session_id).label("count")
        )
        .group_by(cast(ArchivedSession.created_at, Date))
        .order_by(text("date DESC"))
        .limit(14)
        .all()
    )

    for date, count in date_stats:
        print(f"  {date}: {count} 条会话")

    print("\n" + "=" * 60)
    print("诊断完成")
    print("\n💡 如果发现 user_id 不一致，请运行修复脚本:")
    print("   python scripts/fix_archived_user_ids.py <用户名> --execute")


if __name__ == "__main__":
    diagnose_user_ids()
