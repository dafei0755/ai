"""
自动归档调度器 v7.200

定期执行数据库维护任务，防止数据库无限增长

使用方法：
    # 运行一次
    python scripts/auto_archive_scheduler.py --once

    # 持续运行（每24小时执行一次）
    python scripts/auto_archive_scheduler.py --daemon --interval 24

    # Windows 任务计划程序（每周日凌晨2点）
    schtasks /create /tn "LangGraph自动归档" /tr "python D:\11-20\langgraph-design\scripts\auto_archive_scheduler.py --once" /sc weekly /d SUN /st 02:00
"""

import argparse
import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

from intelligent_project_analyzer.services.session_archive_manager import SessionArchiveManager


async def run_maintenance_task():
    """执行维护任务"""
    logger.info(f"🚀 开始执行自动维护任务 - {datetime.now()}")

    try:
        manager = SessionArchiveManager()

        # 1. 显示维护前状态
        stats_before = await manager.get_database_stats()
        logger.info(f"📊 维护前: {stats_before['size_mb']:.2f}MB, " f"{stats_before['total_sessions']} 个会话")

        # 2. 归档30天前的会话
        logger.info("📦 归档30天前的会话...")
        archive_result = await manager.archive_old_sessions_to_cold_storage(days_threshold=30, dry_run=False)
        logger.success(f"✅ 归档完成: {archive_result['archived_count']} 个会话")

        # 3. 清理90天前的失败会话
        logger.info("🗑️  清理90天前的失败会话...")
        from datetime import timedelta

        from intelligent_project_analyzer.services.session_archive_manager import ArchivedSession

        db = manager._get_db()
        threshold_date = datetime.now() - timedelta(days=90)

        failed_sessions = (
            db.query(ArchivedSession)
            .filter(ArchivedSession.status == "failed", ArchivedSession.created_at < threshold_date)
            .all()
        )

        deleted_count = len(failed_sessions)
        for session in failed_sessions:
            db.delete(session)
        db.commit()
        db.close()

        logger.success(f"✅ 清理完成: {deleted_count} 个失败会话")

        # 4. VACUUM 压缩
        logger.info("🔧 执行 VACUUM 压缩...")
        vacuum_success = await manager.vacuum_database()

        # 5. 显示维护后状态
        stats_after = await manager.get_database_stats()
        logger.info(f"📊 维护后: {stats_after['size_mb']:.2f}MB, " f"{stats_after['total_sessions']} 个会话")

        # 6. 计算收益
        saved_mb = stats_before["size_mb"] - stats_after["size_mb"]
        saved_count = archive_result["archived_count"] + deleted_count

        logger.success(f"🎉 维护任务完成! " f"节省 {saved_mb:.2f}MB 空间, " f"清理 {saved_count} 条记录")

        # 7. 健康检查
        if stats_after["health_status"] == "warning":
            logger.warning("⚠️ 数据库仍处于警告状态，建议手动检查")
        elif stats_after["health_status"] == "critical":
            logger.error("🔴 数据库处于严重状态，请立即手动处理！")

        return True

    except Exception as e:
        logger.error(f"❌ 维护任务执行失败: {e}")
        return False


async def daemon_mode(interval_hours: int):
    """守护进程模式，定期执行维护任务"""
    logger.info(f"🤖 守护进程已启动，每 {interval_hours} 小时执行一次维护")

    while True:
        try:
            success = await run_maintenance_task()

            if success:
                logger.info(f"⏰ 下次执行时间: {interval_hours} 小时后")
            else:
                logger.warning("⚠️ 任务执行失败，将在下个周期重试")

            # 等待指定时间
            await asyncio.sleep(interval_hours * 3600)

        except KeyboardInterrupt:
            logger.info("👋 守护进程已停止")
            break
        except Exception as e:
            logger.error(f"❌ 守护进程异常: {e}")
            logger.info("⏰ 5分钟后重试...")
            await asyncio.sleep(300)


async def main():
    parser = argparse.ArgumentParser(
        description="自动归档调度器 v7.200",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 运行一次（适合定时任务）
  python scripts/auto_archive_scheduler.py --once

  # 守护进程模式（每24小时执行）
  python scripts/auto_archive_scheduler.py --daemon --interval 24

  # 守护进程模式（每周执行，168小时）
  python scripts/auto_archive_scheduler.py --daemon --interval 168

Windows 任务计划程序设置:
  schtasks /create /tn "LangGraph自动归档" ^
    /tr "python D:\\11-20\\langgraph-design\\scripts\\auto_archive_scheduler.py --once" ^
    /sc weekly /d SUN /st 02:00
        """,
    )

    parser.add_argument("--once", action="store_true", help="运行一次后退出")
    parser.add_argument("--daemon", action="store_true", help="守护进程模式（持续运行）")
    parser.add_argument("--interval", type=int, default=24, help="守护进程执行间隔（小时，默认24）")

    args = parser.parse_args()

    if not args.once and not args.daemon:
        parser.print_help()
        sys.exit(1)

    try:
        if args.once:
            # 运行一次
            success = await run_maintenance_task()
            sys.exit(0 if success else 1)

        elif args.daemon:
            # 守护进程模式
            await daemon_mode(args.interval)

    except KeyboardInterrupt:
        logger.info("👋 程序已停止")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ 程序异常退出: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
