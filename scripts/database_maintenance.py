"""
数据库维护脚本 v7.200

执行数据库维护任务：
1. VACUUM 压缩
2. 冷存储归档
3. 性能监控
4. 数据清理

使用方法：
    python scripts/database_maintenance.py --vacuum              # 仅压缩
    python scripts/database_maintenance.py --archive --days 30  # 归档30天前的会话
    python scripts/database_maintenance.py --stats              # 查看统计信息
    python scripts/database_maintenance.py --all                # 执行所有维护任务
"""

import argparse
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

from intelligent_project_analyzer.services.session_archive_manager import SessionArchiveManager


async def show_stats(manager: SessionArchiveManager):
    """显示数据库统计信息"""
    logger.info("📊 获取数据库统计信息...")

    stats = await manager.get_database_stats()

    print("\n" + "=" * 60)
    print("📊 数据库统计信息")
    print("=" * 60)

    if "error" in stats:
        print(f"❌ 错误: {stats['error']}")
        return

    # 基本信息
    print(f"\n📁 数据库文件:")
    print(f"   大小: {stats['size_mb']:.2f} MB ({stats['size_gb']:.2f} GB)")
    print(f"   状态: {stats['health_status'].upper()}")

    # 记录统计
    print(f"\n📝 记录统计:")
    print(f"   总会话数: {stats['total_sessions']:,}")
    print(f"   搜索会话数: {stats['total_search_sessions']:,}")
    print(f"   完成会话: {stats['completed_count']:,}")
    print(f"   失败会话: {stats['failed_count']:,}")
    print(f"   平均大小: {stats['avg_size_mb']:.2f} MB/会话")

    # 健康警告
    if stats["warnings"]:
        print(f"\n⚠️  健康警告:")
        for warning in stats["warnings"]:
            print(f"   • {warning}")
    else:
        print(f"\n✅ 数据库健康状态良好")

    print(f"\n⏰ 统计时间: {stats['timestamp']}")
    print("=" * 60 + "\n")


async def vacuum_database(manager: SessionArchiveManager):
    """执行数据库压缩"""
    logger.info("🔧 开始 VACUUM 压缩...")

    success = await manager.vacuum_database()

    if success:
        print("\n✅ 数据库压缩完成！")
    else:
        print("\n❌ 数据库压缩失败")
        return False

    return True


async def archive_old_sessions(manager: SessionArchiveManager, days: int, dry_run: bool = False):
    """归档旧会话到冷存储"""
    logger.info(f"📦 开始归档 {days} 天前的会话...")

    result = await manager.archive_old_sessions_to_cold_storage(days_threshold=days, dry_run=dry_run)

    if "error" in result:
        print(f"\n❌ 归档失败: {result['error']}")
        return False

    print("\n" + "=" * 60)
    print("📦 冷存储归档结果")
    print("=" * 60)
    print(f"\n检查会话数: {result['total_checked']}")
    print(f"成功归档: {result['archived_count']}")
    print(f"失败数量: {result.get('failed_count', 0)}")  # 修复：使用 get 提供默认值
    print(f"存储位置: {result.get('cold_storage_dir', 'N/A')}")

    if dry_run:
        print(f"\n🔍 模拟运行模式（未实际删除）")
    else:
        print(f"\n✅ 归档完成")

    print("=" * 60 + "\n")

    return True


async def clean_old_failed_sessions(manager: SessionArchiveManager, days: int, dry_run: bool = False):
    """清理旧的失败会话"""
    logger.info(f"🗑️  清理 {days} 天前的失败会话...")

    from datetime import datetime, timedelta

    try:
        threshold_date = datetime.now() - timedelta(days=days)

        # 获取数据库会话
        db = manager._get_db()

        # 查询失败会话
        from intelligent_project_analyzer.services.session_archive_manager import ArchivedSession

        failed_sessions = (
            db.query(ArchivedSession)
            .filter(ArchivedSession.status == "failed", ArchivedSession.created_at < threshold_date)
            .all()
        )

        if not failed_sessions:
            logger.info(f"✓ 无需清理：未找到 {days} 天前的失败会话")
            db.close()
            return True

        deleted_count = len(failed_sessions)

        if not dry_run:
            for session in failed_sessions:
                db.delete(session)
            db.commit()

        db.close()

        print("\n" + "=" * 60)
        print("🗑️  失败会话清理结果")
        print("=" * 60)
        print(f"\n清理数量: {deleted_count}")

        if dry_run:
            print(f"\n🔍 模拟运行模式（未实际删除）")
        else:
            print(f"\n✅ 清理完成")

        print("=" * 60 + "\n")

        return True

    except Exception as e:
        logger.error(f"❌ 清理失败: {e}")
        return False


async def main():
    parser = argparse.ArgumentParser(
        description="数据库维护工具 v7.200",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 查看统计信息
  python scripts/database_maintenance.py --stats

  # 执行 VACUUM 压缩
  python scripts/database_maintenance.py --vacuum

  # 归档30天前的会话（模拟运行）
  python scripts/database_maintenance.py --archive --days 30 --dry-run

  # 归档30天前的会话（实际执行）
  python scripts/database_maintenance.py --archive --days 30

  # 清理90天前的失败会话
  python scripts/database_maintenance.py --clean-failed --days 90

  # 执行所有维护任务
  python scripts/database_maintenance.py --all
        """,
    )

    parser.add_argument("--stats", action="store_true", help="显示数据库统计信息")
    parser.add_argument("--vacuum", action="store_true", help="执行 VACUUM 压缩")
    parser.add_argument("--archive", action="store_true", help="归档旧会话到冷存储")
    parser.add_argument("--clean-failed", action="store_true", help="清理旧的失败会话")
    parser.add_argument("--all", action="store_true", help="执行所有维护任务")
    parser.add_argument("--days", type=int, default=30, help="天数阈值（默认30天）")
    parser.add_argument("--dry-run", action="store_true", help="模拟运行（不实际删除）")

    args = parser.parse_args()

    # 初始化管理器
    manager = SessionArchiveManager()

    # 默认显示统计信息
    if not any([args.stats, args.vacuum, args.archive, args.clean_failed, args.all]):
        args.stats = True

    try:
        # 执行所有任务
        if args.all:
            print("\n🚀 执行完整维护流程...\n")

            # 1. 显示统计信息（前）
            print("📊 维护前统计:\n")
            await show_stats(manager)

            # 2. 归档旧会话
            await archive_old_sessions(manager, args.days, args.dry_run)

            # 3. 清理失败会话
            await clean_old_failed_sessions(manager, 90, args.dry_run)  # 90天前的失败会话

            # 4. VACUUM 压缩
            if not args.dry_run:
                await vacuum_database(manager)

            # 5. 显示统计信息（后）
            print("\n📊 维护后统计:\n")
            await show_stats(manager)

            print("✅ 完整维护流程已完成！\n")

        else:
            # 执行单独任务
            if args.stats:
                await show_stats(manager)

            if args.vacuum:
                await vacuum_database(manager)

            if args.archive:
                await archive_old_sessions(manager, args.days, args.dry_run)

            if args.clean_failed:
                await clean_old_failed_sessions(manager, args.days, args.dry_run)

    except Exception as e:
        logger.error(f"❌ 维护任务执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
