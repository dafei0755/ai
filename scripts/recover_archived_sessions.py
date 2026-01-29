#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
历史会话数据恢复工具 (v7.145)

从 checkpoint 数据库恢复已归档会话的完整数据，修复归档时数据不完整的问题。

用法：
    # 恢复单个会话
    python scripts/recover_archived_sessions.py 8pdwoxj8-20260106154858-dc82c8eb

    # 批量恢复所有不完整会话
    python scripts/recover_archived_sessions.py --all

    # 恢复最近N天的会话
    python scripts/recover_archived_sessions.py --days 7

    # 检查但不修复（dry-run）
    python scripts/recover_archived_sessions.py --all --dry-run
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from types import MethodType

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

# 配置日志
logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")


def _ensure_aiosqlite_is_alive(conn):
    """为缺少 is_alive() 方法的 aiosqlite 连接打补丁"""
    if hasattr(conn, "is_alive") and callable(getattr(conn, "is_alive")):
        return conn

    def _is_alive(self) -> bool:
        thread = getattr(self, "_thread", None)
        running = getattr(self, "_running", False)
        return bool(thread and thread.is_alive() and running)

    conn.is_alive = MethodType(_is_alive, conn)
    logger.debug("🩹 AsyncSqliteSaver 兼容补丁：已为 aiosqlite.Connection 注入 is_alive()")
    return conn


def _deep_convert_to_dict(obj):
    """深度转换对象为基本类型（dict, list, str等）"""
    # Pydantic 模型
    if hasattr(obj, "model_dump"):
        return _deep_convert_to_dict(obj.model_dump())
    elif hasattr(obj, "dict"):
        return _deep_convert_to_dict(obj.dict())
    # dict
    elif isinstance(obj, dict):
        return {k: _deep_convert_to_dict(v) for k, v in obj.items()}
    # list/tuple
    elif isinstance(obj, (list, tuple)):
        return [_deep_convert_to_dict(item) for item in obj]
    # 基本类型
    else:
        return obj


class SessionRecoveryTool:
    """会话数据恢复工具"""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.workspace_root = Path(__file__).parent.parent
        self.checkpoint_db = self.workspace_root / "data" / "checkpoints" / "workflow.db"
        self.archive_manager = None

    async def initialize(self):
        """初始化归档管理器"""
        from intelligent_project_analyzer.services.session_archive_manager import SessionArchiveManager

        self.archive_manager = SessionArchiveManager()
        logger.info("✅ 归档管理器已初始化")

    async def check_session_completeness(self, session_id: str) -> tuple[bool, list[str]]:
        """
        检查会话数据完整性

        Returns:
            (is_complete, missing_fields)
        """
        try:
            archived = await self.archive_manager.get_archived_session(session_id)
            if not archived:
                return False, ["session_not_found"]

            # 关键字段列表
            required_fields = ["structured_requirements", "strategic_analysis", "execution_batches", "agent_results"]

            missing_fields = []
            for field in required_fields:
                value = archived.get(field)
                if value is None or (isinstance(value, (dict, list)) and len(value) == 0):
                    missing_fields.append(field)

            is_complete = len(missing_fields) == 0
            return is_complete, missing_fields

        except Exception as e:
            logger.error(f"❌ 检查会话失败: {session_id}, 错误: {e}")
            return False, [f"error: {e}"]

    async def recover_session_from_checkpoint(self, session_id: str) -> bool:
        """
        从 checkpoint 恢复会话数据

        Returns:
            是否恢复成功
        """
        try:
            # 1. 获取归档数据
            archived = await self.archive_manager.get_archived_session(session_id)
            if not archived:
                logger.error(f"❌ 归档会话不存在: {session_id}")
                return False

            # 2. 获取 checkpoint 数据
            import aiosqlite
            from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

            if not self.checkpoint_db.exists():
                logger.error(f"❌ Checkpoint 数据库不存在: {self.checkpoint_db}")
                return False

            # 创建连接并应用兼容补丁（与 server.py 保持一致）
            conn = await aiosqlite.connect(str(self.checkpoint_db))
            conn = _ensure_aiosqlite_is_alive(conn)
            checkpointer = AsyncSqliteSaver(conn)

            config = {"configurable": {"thread_id": session_id}}
            checkpoint = await checkpointer.aget(config)

            if not checkpoint:
                logger.warning(f"⚠️ Checkpoint 不存在（可能已清理）: {session_id}")
                await conn.close()
                return False

            # 3. 提取 checkpoint 数据
            state = checkpoint["channel_values"]

            # 4. 合并数据
            updated_fields = []
            merge_fields = [
                "structured_requirements",
                "restructured_requirements",
                "strategic_analysis",
                "execution_batches",
                "total_batches",
                "current_batch",
                "active_agents",
                "agent_results",
                "aggregated_results",
                "pdf_path",
            ]

            for field in merge_fields:
                value = state.get(field)
                if value is not None:
                    # 深度转换为基本类型
                    value = _deep_convert_to_dict(value)
                    archived[field] = value
                    updated_fields.append(field)

            # final_report 特殊处理：优先使用 checkpoint，但保留归档的完整报告
            checkpoint_report = state.get("final_report")
            if checkpoint_report and (not archived.get("final_report") or len(str(archived.get("final_report"))) < 100):
                archived["final_report"] = _deep_convert_to_dict(checkpoint_report)
                updated_fields.append("final_report")

            if not updated_fields:
                logger.warning(f"⚠️ Checkpoint 无可恢复数据: {session_id}")
                await conn.close()
                return False

            # 5. 更新归档
            if self.dry_run:
                logger.info(f"🔍 [DRY-RUN] 会恢复 {len(updated_fields)} 个字段: {', '.join(updated_fields)}")
                await conn.close()
                return True
            else:
                # 测试 JSON 序列化
                try:
                    test_json = json.dumps(archived, ensure_ascii=False, default=str)
                    logger.debug(f"✅ JSON 序列化测试通过，数据大小: {len(test_json)} bytes")
                except Exception as json_err:
                    logger.error(f"❌ JSON 序列化失败: {json_err}")
                    # 逐字段测试
                    for key, value in archived.items():
                        try:
                            json.dumps({key: value}, ensure_ascii=False, default=str)
                        except Exception as field_err:
                            logger.error(f"   问题字段: {key}, 类型: {type(value)}, 错误: {field_err}")
                    await conn.close()
                    return False

                success = await self.archive_manager.archive_session(
                    session_id=session_id, session_data=archived, force=True  # 强制覆盖
                )

                await conn.close()

                if success:
                    logger.info(f"✅ 恢复会话数据: {session_id} ({len(updated_fields)} 个字段)")
                    logger.debug(f"   恢复字段: {', '.join(updated_fields)}")
                    return True
                else:
                    logger.error(f"❌ 更新归档失败: {session_id}")
                    return False

        except Exception as e:
            logger.error(f"❌ 恢复会话失败: {session_id}, 错误: {e}")
            import traceback

            logger.debug(traceback.format_exc())
            return False

    async def recover_single_session(self, session_id: str):
        """恢复单个会话"""
        logger.info(f"\n{'='*80}")
        logger.info(f"恢复会话: {session_id}")
        logger.info(f"{'='*80}\n")

        # 检查完整性
        is_complete, missing_fields = await self.check_session_completeness(session_id)

        if is_complete:
            logger.info(f"✅ 会话数据完整，无需恢复")
            return True
        else:
            logger.warning(f"⚠️ 缺失字段: {', '.join(missing_fields)}")

        # 执行恢复
        success = await self.recover_session_from_checkpoint(session_id)

        if success:
            logger.success(f"✅ 恢复成功: {session_id}")
        else:
            logger.error(f"❌ 恢复失败: {session_id}")

        return success

    async def recover_all_incomplete_sessions(self, days: int = None):
        """批量恢复不完整会话"""
        logger.info(f"\n{'='*80}")
        logger.info(f"批量恢复不完整会话")
        if days:
            logger.info(f"时间范围: 最近 {days} 天")
        logger.info(f"{'='*80}\n")

        # 获取所有归档会话
        try:
            cutoff_date = datetime.now() - timedelta(days=days) if days else None

            # 分页获取所有会话
            all_sessions = []
            offset = 0
            limit = 100

            while True:
                sessions = await self.archive_manager.list_archived_sessions(limit=limit, offset=offset)

                if not sessions:
                    break

                # 过滤时间范围
                if cutoff_date:
                    sessions = [s for s in sessions if datetime.fromisoformat(s["archived_at"]) >= cutoff_date]

                all_sessions.extend(sessions)
                offset += limit

                if len(sessions) < limit:
                    break

            logger.info(f"📊 找到 {len(all_sessions)} 个归档会话")

            # 检查并恢复
            incomplete_sessions = []

            for session in all_sessions:
                session_id = session["session_id"]
                is_complete, missing_fields = await self.check_session_completeness(session_id)

                if not is_complete:
                    incomplete_sessions.append((session_id, missing_fields))

            logger.info(f"⚠️ 发现 {len(incomplete_sessions)} 个不完整会话")

            if len(incomplete_sessions) == 0:
                logger.success("✅ 所有会话数据完整，无需恢复")
                return

            # 执行恢复
            success_count = 0
            fail_count = 0

            for session_id, missing_fields in incomplete_sessions:
                logger.info(f"\n恢复会话: {session_id}")
                logger.info(f"  缺失字段: {', '.join(missing_fields)}")

                success = await self.recover_session_from_checkpoint(session_id)

                if success:
                    success_count += 1
                else:
                    fail_count += 1

            # 统计结果
            logger.info(f"\n{'='*80}")
            logger.info(f"恢复完成")
            logger.info(f"{'='*80}")
            logger.info(f"  总数: {len(incomplete_sessions)}")
            logger.success(f"  成功: {success_count}")
            if fail_count > 0:
                logger.error(f"  失败: {fail_count}")

            if self.dry_run:
                logger.info("\n💡 这是 dry-run 模式，未实际修改数据")
                logger.info("   移除 --dry-run 参数以执行恢复")

        except Exception as e:
            logger.error(f"❌ 批量恢复失败: {e}")
            import traceback

            logger.error(traceback.format_exc())


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="历史会话数据恢复工具 (v7.145)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 恢复单个会话
  python scripts/recover_archived_sessions.py 8pdwoxj8-20260106154858-dc82c8eb

  # 批量恢复所有不完整会话
  python scripts/recover_archived_sessions.py --all

  # 恢复最近7天的会话
  python scripts/recover_archived_sessions.py --days 7

  # 检查但不修复（dry-run）
  python scripts/recover_archived_sessions.py --all --dry-run
        """,
    )

    parser.add_argument("session_id", nargs="?", help="要恢复的会话ID")
    parser.add_argument("--all", action="store_true", help="批量恢复所有不完整会话")
    parser.add_argument("--days", type=int, help="限制恢复最近N天的会话")
    parser.add_argument("--dry-run", action="store_true", help="检查但不实际修改数据")

    args = parser.parse_args()

    # 参数验证
    if not args.session_id and not args.all:
        parser.error("必须指定会话ID或使用 --all 参数")

    if args.session_id and args.all:
        parser.error("不能同时指定会话ID和 --all 参数")

    # 创建工具实例
    tool = SessionRecoveryTool(dry_run=args.dry_run)
    await tool.initialize()

    # 执行恢复
    if args.session_id:
        await tool.recover_single_session(args.session_id)
    elif args.all:
        await tool.recover_all_incomplete_sessions(days=args.days)


if __name__ == "__main__":
    asyncio.run(main())
