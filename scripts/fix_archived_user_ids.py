"""
修复归档会话的 user_id

将空的或错误的 user_id 更新为正确的用户名

使用方法:
    # 预览修复（不实际修改）
    python scripts/fix_archived_user_ids.py 8pdwoxj8

    # 实际执行修复
    python scripts/fix_archived_user_ids.py 8pdwoxj8 --execute
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from intelligent_project_analyzer.services.session_archive_manager import ArchivedSession, SessionArchiveManager


def fix_user_ids(target_user_id: str, dry_run: bool = True):
    """
    修复归档会话的 user_id

    Args:
        target_user_id: 目标用户ID（用户名）
        dry_run: 是否仅预览（不实际修改）
    """
    mode = "[预览模式]" if dry_run else "[执行模式]"
    print(f"{mode} 修复 user_id -> {target_user_id}")
    print("=" * 60)

    manager = SessionArchiveManager()
    db = manager._get_db()

    # 查找需要修复的会话
    sessions_to_fix = (
        db.query(ArchivedSession)
        .filter(
            (ArchivedSession.user_id == None)
            | (ArchivedSession.user_id == "")
            | (ArchivedSession.user_id == "web_user")
            | (ArchivedSession.user_id == "unknown")
        )
        .all()
    )

    print(f"\n找到 {len(sessions_to_fix)} 条需要修复的会话")

    if not sessions_to_fix:
        print("✅ 没有需要修复的会话")
        return

    if dry_run:
        print("\n📋 预览将要修复的会话:")
        print("-" * 40)
        for s in sessions_to_fix:
            old_id = s.user_id or "(空)"
            print(f"  {s.session_id}")
            print(f"    {old_id} -> {target_user_id}")
            print(f"    created_at: {s.created_at}")
            print()

        print("-" * 40)
        print(f"\n⚠️  预览完成，共 {len(sessions_to_fix)} 条会话将被修复")
        print(f"   如需执行修复，请添加 --execute 参数:")
        print(f"   python scripts/fix_archived_user_ids.py {target_user_id} --execute")
    else:
        print("\n🔧 正在修复...")
        for s in sessions_to_fix:
            old_id = s.user_id or "(空)"
            s.user_id = target_user_id
            print(f"  ✓ {s.session_id}: {old_id} -> {target_user_id}")

        db.commit()
        print(f"\n✅ 已修复 {len(sessions_to_fix)} 条会话")
        print("\n请重启后端服务以使更改生效:")
        print("   python -B scripts\\run_server_production.py")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="修复归档会话的 user_id")
    parser.add_argument("user_id", help="目标用户ID（用户名）")
    parser.add_argument("--execute", action="store_true", help="实际执行修复（默认仅预览）")

    args = parser.parse_args()
    fix_user_ids(args.user_id, dry_run=not args.execute)
