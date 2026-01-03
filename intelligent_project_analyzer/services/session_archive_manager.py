"""
会话归档管理器

负责将会话数据归档到数据库，实现永久保存
解决Redis TTL限制（7天）的问题
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, defer, sessionmaker

Base = declarative_base()


class ArchivedSession(Base):
    """归档会话数据模型"""

    __tablename__ = "archived_sessions"

    # 主键
    session_id = Column(String(100), primary_key=True, index=True)

    # 🆕 P0修复: 添加user_id列
    user_id = Column(String(100), nullable=True, index=True)

    # 基本信息
    user_input = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, index=True)
    mode = Column(String(20), default="api")

    # 时间戳
    created_at = Column(DateTime, nullable=False, index=True)
    archived_at = Column(DateTime, default=datetime.now, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # 会话数据（JSON存储）
    session_data = Column(Text, nullable=False)  # 完整会话状态
    final_report = Column(Text, nullable=True)  # 最终报告

    # 统计信息
    progress = Column(Integer, default=0)
    current_stage = Column(String(100), nullable=True)

    # 用户管理字段
    display_name = Column(String(200), nullable=True)  # 用户自定义名称
    pinned = Column(Boolean, default=False, index=True)  # 是否置顶
    tags = Column(String(500), nullable=True)  # 标签（逗号分隔）

    # 索引
    __table_args__ = (
        Index("idx_created_at_status", "created_at", "status"),
        Index("idx_pinned_created_at", "pinned", "created_at"),
        Index("idx_user_created", "user_id", "created_at"),  # 🆕 P0修复: 用户+时间复合索引
    )


class SessionArchiveManager:
    """会话归档管理器"""

    def __init__(self, database_url: str = None):
        """
        初始化归档管理器

        Args:
            database_url: 数据库URL（默认使用SQLite）
        """
        if database_url is None:
            # 默认使用SQLite，存储在data目录
            data_dir = Path(__file__).parent.parent.parent / "data"
            data_dir.mkdir(exist_ok=True)
            database_url = f"sqlite:///{data_dir / 'archived_sessions.db'}"

        self.database_url = database_url
        self.engine = create_engine(
            database_url,
            echo=False,  # 生产环境关闭SQL日志
            pool_pre_ping=True,  # 连接池健康检查
            connect_args={"check_same_thread": False} if "sqlite" in database_url else {},
        )

        # 创建表
        Base.metadata.create_all(self.engine)

        # 🆕 P0修复: Schema自检与自动迁移
        self._verify_and_migrate_schema()

        # 创建会话工厂
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        logger.info(f"✅ 会话归档管理器已初始化: {database_url}")

    def _verify_and_migrate_schema(self):
        """
        🆕 P0修复: 验证Schema并自动迁移

        检查archived_sessions表是否包含user_id列，不存在则自动添加
        """
        if "sqlite" not in self.database_url:
            # 非SQLite数据库暂不支持自动迁移
            return

        try:
            import sqlite3

            # 从database_url提取文件路径
            db_path = self.database_url.replace("sqlite:///", "")

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # 检查user_id列是否存在
            cursor.execute("PRAGMA table_info(archived_sessions)")
            columns = [col[1] for col in cursor.fetchall()]

            if "user_id" not in columns:
                logger.warning("⚠️ 检测到Schema缺陷：archived_sessions表缺少user_id列")
                logger.info("🔧 执行自动迁移...")

                # 添加user_id列
                cursor.execute(
                    """
                    ALTER TABLE archived_sessions
                    ADD COLUMN user_id VARCHAR(100) DEFAULT NULL
                """
                )

                # 创建索引
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_user_id
                    ON archived_sessions(user_id)
                """
                )

                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_user_created
                    ON archived_sessions(user_id, created_at DESC)
                """
                )

                conn.commit()
                logger.success("✅ Schema迁移完成：已添加user_id列及索引")
            else:
                logger.debug("✓ Schema验证通过：user_id列已存在")

            conn.close()

        except Exception as e:
            logger.error(f"❌ Schema验证失败: {e}")
            logger.warning("⚠️ 建议手动运行迁移脚本: python scripts/migrate_archived_sessions.py")

    def _get_db(self) -> Session:
        """获取数据库会话"""
        return self.SessionLocal()

    async def archive_session(self, session_id: str, session_data: Dict[str, Any], force: bool = False) -> bool:
        """
        归档会话到数据库

        Args:
            session_id: 会话ID
            session_data: 会话数据
            force: 是否强制覆盖已存在的归档

        Returns:
            是否归档成功
        """
        try:
            db = self._get_db()

            # 检查是否已归档
            existing = db.query(ArchivedSession).filter(ArchivedSession.session_id == session_id).first()

            if existing and not force:
                logger.warning(f"⚠️ 会话已归档，跳过: {session_id}")
                db.close()
                return False  # 🔥 v3.6修复：已存在且不强制时返回False

            # 提取关键字段
            user_input = session_data.get("user_input", "")
            status = session_data.get("status", "unknown")
            mode = session_data.get("mode", "api")
            progress = session_data.get("progress", 0)
            current_stage = session_data.get("current_node", "")
            final_report = session_data.get("final_report", "")

            # 解析时间
            created_at_str = session_data.get("created_at")
            if isinstance(created_at_str, str):
                created_at = datetime.fromisoformat(created_at_str)
            else:
                created_at = datetime.now()

            completed_at_str = session_data.get("completed_at")
            completed_at = None
            if completed_at_str:
                try:
                    completed_at = datetime.fromisoformat(completed_at_str)
                except:
                    pass

            # 序列化完整会话数据
            session_json = json.dumps(session_data, ensure_ascii=False)
            report_json = json.dumps(final_report, ensure_ascii=False) if final_report else None

            if existing:
                # 更新现有归档
                existing.user_input = user_input
                existing.status = status
                existing.mode = mode
                existing.session_data = session_json
                existing.final_report = report_json
                existing.progress = progress
                existing.current_stage = current_stage
                existing.completed_at = completed_at
                existing.archived_at = datetime.now()

                logger.info(f"🔄 更新归档会话: {session_id}")
            else:
                # 创建新归档
                archived = ArchivedSession(
                    session_id=session_id,
                    user_input=user_input,
                    status=status,
                    mode=mode,
                    created_at=created_at,
                    archived_at=datetime.now(),
                    completed_at=completed_at,
                    session_data=session_json,
                    final_report=report_json,
                    progress=progress,
                    current_stage=current_stage,
                )
                db.add(archived)

                logger.info(f"📦 新增归档会话: {session_id}")

            db.commit()
            db.close()
            return True

        except Exception as e:
            logger.error(f"❌ 归档会话失败: {session_id}, 错误: {e}")
            if db:
                db.rollback()
                db.close()
            return False

    async def get_archived_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取归档会话

        Args:
            session_id: 会话ID

        Returns:
            会话数据（不存在返回None）
        """
        try:
            db = self._get_db()
            archived = db.query(ArchivedSession).filter(ArchivedSession.session_id == session_id).first()

            if not archived:
                db.close()
                return None

            # 反序列化会话数据
            session_data = json.loads(archived.session_data)

            # 添加归档元数据
            session_data["_archived"] = True
            session_data["_archived_at"] = archived.archived_at.isoformat()

            db.close()
            return session_data

        except Exception as e:
            logger.error(f"❌ 获取归档会话失败: {session_id}, 错误: {e}")
            if db:
                db.close()
            return None

    async def list_archived_sessions(
        self, limit: int = 50, offset: int = 0, status: Optional[str] = None, pinned_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        列出归档会话

        Args:
            limit: 返回数量限制
            offset: 偏移量（分页）
            status: 过滤状态（可选）
            pinned_only: 仅返回置顶会话

        Returns:
            会话列表
        """
        try:
            db = self._get_db()

            # ✅ Fix 2.1: 构建查询 - DEFER大字段避免加载35MB session_data和11MB final_report
            query = db.query(ArchivedSession).options(
                defer(ArchivedSession.session_data),  # 不加载session_data (最大35MB)
                defer(ArchivedSession.final_report),  # 不加载final_report (最大11MB)
            )

            if status:
                query = query.filter(ArchivedSession.status == status)

            if pinned_only:
                query = query.filter(ArchivedSession.pinned == True)

            # 排序：置顶优先，然后按创建时间倒序
            query = query.order_by(ArchivedSession.pinned.desc(), ArchivedSession.created_at.desc())

            # 分页
            query = query.offset(offset).limit(limit)

            # 执行查询
            results = query.all()

            # 转换为字典列表
            sessions = []
            for archived in results:
                sessions.append(
                    {
                        "session_id": archived.session_id,
                        "user_input": archived.user_input,
                        "status": archived.status,
                        "mode": archived.mode,
                        "created_at": archived.created_at.isoformat(),
                        "archived_at": archived.archived_at.isoformat(),
                        "progress": archived.progress,
                        "current_stage": archived.current_stage,
                        "display_name": archived.display_name,
                        "pinned": archived.pinned,
                        "tags": archived.tags.split(",") if archived.tags else [],
                        "_archived": True,
                    }
                )

            db.close()
            return sessions

        except Exception as e:
            logger.error(f"❌ 列出归档会话失败: {e}")
            if db:
                db.close()
            return []

    async def update_metadata(
        self,
        session_id: str,
        display_name: Optional[str] = None,
        pinned: Optional[bool] = None,
        tags: Optional[List[str]] = None,
    ) -> bool:
        """
        更新会话元数据（重命名、置顶、标签）

        Args:
            session_id: 会话ID
            display_name: 显示名称
            pinned: 是否置顶
            tags: 标签列表

        Returns:
            是否更新成功
        """
        try:
            db = self._get_db()
            archived = db.query(ArchivedSession).filter(ArchivedSession.session_id == session_id).first()

            if not archived:
                logger.warning(f"归档会话不存在: {session_id}")
                db.close()
                return False

            # 更新字段
            if display_name is not None:
                archived.display_name = display_name

            if pinned is not None:
                archived.pinned = pinned

            if tags is not None:
                archived.tags = ",".join(tags)

            db.commit()
            db.close()

            logger.info(f"✅ 更新归档会话元数据: {session_id}")
            return True

        except Exception as e:
            logger.error(f"❌ 更新归档会话元数据失败: {session_id}, 错误: {e}")
            if db:
                db.rollback()
                db.close()
            return False

    async def delete_archived_session(self, session_id: str) -> bool:
        """
        删除归档会话

        Args:
            session_id: 会话ID

        Returns:
            是否删除成功
        """
        try:
            db = self._get_db()
            result = db.query(ArchivedSession).filter(ArchivedSession.session_id == session_id).delete()

            db.commit()
            db.close()

            if result > 0:
                logger.info(f"🗑️ 删除归档会话: {session_id}")
                return True
            else:
                logger.warning(f"归档会话不存在: {session_id}")
                return False

        except Exception as e:
            logger.error(f"❌ 删除归档会话失败: {session_id}, 错误: {e}")
            if db:
                db.rollback()
                db.close()
            return False

    async def count_archived_sessions(
        self, status: Optional[str] = None, pinned_only: bool = False  # 🔥 v3.6修复：添加 pinned_only 参数
    ) -> int:
        """
        统计归档会话数量

        Args:
            status: 过滤状态（可选）
            pinned_only: 是否只统计置顶会话（默认False）

        Returns:
            会话数量
        """
        try:
            db = self._get_db()
            query = db.query(ArchivedSession)

            if status:
                query = query.filter(ArchivedSession.status == status)

            if pinned_only:
                query = query.filter(ArchivedSession.pinned == True)

            count = query.count()
            db.close()

            return count

        except Exception as e:
            logger.error(f"❌ 统计归档会话失败: {e}")
            if db:
                db.close()
            return 0

    async def archive_old_sessions(self, days_threshold: int = 30) -> int:
        """
        ✅ Fix 2.2: 将旧的已归档会话移至冷存储

        Args:
            days_threshold: 归档阈值（天数），默认30天

        Returns:
            归档的会话数
        """
        try:
            db = self._get_db()
            cutoff_date = datetime.now() - timedelta(days=days_threshold)

            # 查找旧会话
            old_sessions = db.query(ArchivedSession).filter(ArchivedSession.archived_at < cutoff_date).all()

            archived_count = 0
            cold_storage_dir = Path("data/cold_storage")
            cold_storage_dir.mkdir(parents=True, exist_ok=True)

            for session in old_sessions:
                try:
                    # 导出为JSON文件
                    file_path = cold_storage_dir / f"{session.session_id}.json"
                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(
                            {
                                "session_id": session.session_id,
                                "user_id": session.user_id,
                                "user_input": session.user_input,
                                "status": session.status,
                                "mode": session.mode,
                                "created_at": session.created_at.isoformat(),
                                "archived_at": session.archived_at.isoformat(),
                                "session_data": session.session_data,
                                "final_report": session.final_report,
                                "progress": session.progress,
                                "current_stage": session.current_stage,
                                "display_name": session.display_name,
                                "pinned": session.pinned,
                                "tags": session.tags,
                            },
                            f,
                            ensure_ascii=False,
                            indent=2,
                        )

                    # 从数据库删除
                    db.delete(session)
                    archived_count += 1

                except Exception as e:
                    logger.error(f"❌ 归档会话 {session.session_id} 失败: {e}")
                    continue

            db.commit()
            db.close()

            logger.info(f"✅ 归档完成: {archived_count} 个会话移至冷存储")
            return archived_count

        except Exception as e:
            logger.error(f"❌ 归档旧会话失败: {e}")
            if db:
                db.close()
            return 0

    async def vacuum_database(self) -> bool:
        """
        ✅ Fix 2.2: 压缩数据库文件（回收已删除数据占用的空间）

        Returns:
            是否成功
        """
        try:
            db = self._get_db()
            db.execute("VACUUM")
            db.close()

            # 检查压缩后的大小
            db_path = Path(self.db_path)
            size_mb = db_path.stat().st_size / (1024 * 1024)
            logger.info(f"✅ 数据库压缩完成，当前大小: {size_mb:.1f} MB")
            return True

        except Exception as e:
            logger.error(f"❌ 数据库压缩失败: {e}")
            if db:
                db.close()
            return False


# 全局单例实例
_archive_manager: Optional[SessionArchiveManager] = None


def get_archive_manager() -> SessionArchiveManager:
    """
    获取全局归档管理器实例（单例模式）

    Returns:
        SessionArchiveManager 实例
    """
    global _archive_manager

    if _archive_manager is None:
        from ...settings import settings

        _archive_manager = SessionArchiveManager(settings.database_url)

    return _archive_manager
