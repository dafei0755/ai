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


# 🆕 v7.163: 搜索会话归档模型
class ArchivedSearchSession(Base):
    """归档的搜索会话数据模型"""

    __tablename__ = "archived_search_sessions"

    # 主键
    session_id = Column(String(100), primary_key=True, index=True)

    # 用户信息
    user_id = Column(String(100), nullable=True, index=True)

    # 搜索信息
    query = Column(Text, nullable=False)  # 搜索查询

    # 时间戳
    created_at = Column(DateTime, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.now, nullable=False)

    # 搜索结果（JSON存储）
    sources = Column(Text, nullable=True)  # 来源列表 JSON
    images = Column(Text, nullable=True)  # 图片列表 JSON
    reasoning = Column(Text, nullable=True)  # 推理过程（旧字段，兼容）
    content = Column(Text, nullable=True)  # AI 回答内容（旧字段，兼容）

    # 🆕 v7.177: 新增深度搜索相关字段
    is_deep_mode = Column(Integer, default=0)  # 是否深度搜索模式 (0=否, 1=是)
    thinking_content = Column(Text, nullable=True)  # 深度思考内容
    answer_content = Column(Text, nullable=True)  # AI 回答内容（新字段）
    search_plan = Column(Text, nullable=True)  # 搜索规划 JSON
    rounds = Column(Text, nullable=True)  # 搜索轮次记录 JSON
    total_rounds = Column(Integer, default=0)  # 总轮数

    # 🆕 v7.219: 需求洞察相关字段（完整链路持久化）
    l0_content = Column(Text, nullable=True)  # L0分析对话内容
    problem_solving_thinking = Column(Text, nullable=True)  # 解题思考内容
    structured_info = Column(Text, nullable=True)  # 结构化用户信息 JSON

    # 🆕 v7.235: 搜索框架持久化（支持断点续传）
    search_framework = Column(Text, nullable=True)  # SearchFramework JSON
    search_master_line = Column(Text, nullable=True)  # SearchMasterLine JSON（兼容旧版本）
    current_round = Column(Integer, default=0)  # 当前搜索轮次
    overall_completeness = Column(Integer, default=0)  # 整体完成度(0-100)

    # 统计信息
    execution_time = Column(Integer, default=0)  # 执行时间(毫秒)
    source_count = Column(Integer, default=0)  # 来源数量
    image_count = Column(Integer, default=0)  # 图片数量

    # 索引
    __table_args__ = (
        Index("idx_search_user_created", "user_id", "created_at"),
        Index("idx_search_query", "query"),
    )


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

    # 🆕 v7.178: 分析模式（用于前端显示深度思考标签）
    analysis_mode = Column(String(50), default="normal")

    # 用户管理字段
    display_name = Column(String(200), nullable=True)  # 用户自定义名称
    pinned = Column(Boolean, default=False, index=True)  # 是否置顶
    tags = Column(String(500), nullable=True)  # 标签（逗号分隔）

    # 索引
    __table_args__ = (
        Index("idx_created_at_status", "created_at", "status"),
        Index("idx_pinned_created_at", "pinned", "created_at"),
        Index("idx_user_created", "user_id", "created_at"),  # 🆕 P0修复: 用户+时间复合索引
        Index("idx_user_pinned_created", "user_id", "pinned", "created_at"),  # 🆕 v7.178: 用户+置顶+时间复合索引（优化查询）
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

        # 🆕 v7.200: 性能优化 - 配置连接池参数
        connect_args = {}
        if "sqlite" in database_url:
            connect_args["check_same_thread"] = False

        self.engine = create_engine(
            database_url,
            echo=False,  # 生产环境关闭SQL日志
            pool_pre_ping=True,  # 连接池健康检查
            pool_size=10,  # 增加连接池大小（默认5）
            max_overflow=20,  # 允许20个溢出连接（默认10）
            pool_recycle=3600,  # 1小时回收连接，避免长连接超时
            pool_timeout=30,  # 连接超时30秒
            connect_args=connect_args,
        )

        # 🆕 v7.200: 性能优化 - 启用 WAL 模式（SQLite）
        if "sqlite" in database_url:
            self._enable_wal_mode()

        # 创建表
        Base.metadata.create_all(self.engine)

        # 🆕 P0修复: Schema自检与自动迁移
        self._verify_and_migrate_schema()

        # 创建会话工厂
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        logger.info(f"✅ 会话归档管理器已初始化: {database_url}")

    def _enable_wal_mode(self):
        """
        🆕 v7.200: 启用 WAL (Write-Ahead Logging) 模式

        WAL 模式优势：
        - 并发性能提升 2-5x（读写不互相阻塞）
        - 写入性能提升（批量写入更高效）
        - 更好的崩溃恢复能力
        """
        try:
            conn = self.engine.raw_connection()
            cursor = conn.cursor()

            # 检查当前 journal_mode
            cursor.execute("PRAGMA journal_mode")
            current_mode = cursor.fetchone()[0]

            if current_mode.upper() != "WAL":
                logger.info(f"🔧 切换 SQLite journal_mode: {current_mode} → WAL")

                # 启用 WAL 模式
                cursor.execute("PRAGMA journal_mode=WAL")

                # 优化同步模式（NORMAL 提供足够的安全性和更好的性能）
                cursor.execute("PRAGMA synchronous=NORMAL")

                # WAL 自动检查点阈值（默认1000页，约4MB）
                cursor.execute("PRAGMA wal_autocheckpoint=1000")

                conn.commit()
                logger.success("✅ WAL 模式已启用，并发性能提升 2-5x")
            else:
                logger.debug("✓ WAL 模式已启用")

            cursor.close()
            conn.close()

        except Exception as e:
            logger.warning(f"⚠️ 启用 WAL 模式失败: {e}")

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
            analysis_mode = session_data.get("analysis_mode", "normal")  # 🆕 v7.178: 提取分析模式
            # 🔧 v7.277: 提取 user_id（修复开发模式下分析会话不显示在历史记录的问题）
            user_id = session_data.get("user_id")

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
                existing.analysis_mode = analysis_mode  # 🆕 v7.178: 更新分析模式
                # 🔧 v7.277: 更新 user_id（如果存在且之前未设置）
                if user_id and not existing.user_id:
                    existing.user_id = user_id

                logger.info(f"🔄 更新归档会话: {session_id}")
            else:
                # 创建新归档
                archived = ArchivedSession(
                    session_id=session_id,
                    user_id=user_id,  # 🔧 v7.277: 保存 user_id
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
                    analysis_mode=analysis_mode,  # 🆕 v7.178: 保存分析模式
                )
                db.add(archived)

                logger.info(f"📦 新增归档会话: {session_id} (user_id={user_id})")

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
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        pinned_only: bool = False,
        user_id: Optional[str] = None,  # 🆕 v7.178: 按用户过滤
    ) -> List[Dict[str, Any]]:
        """
        列出归档会话

        Args:
            limit: 返回数量限制
            offset: 偏移量（分页）
            status: 过滤状态（可选）
            pinned_only: 仅返回置顶会话
            user_id: 用户ID（可选，用于过滤当前用户的会话）

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

            # 🆕 v7.178: 按用户过滤（性能优化关键）
            if user_id:
                query = query.filter(ArchivedSession.user_id == user_id)

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
                        "analysis_mode": archived.analysis_mode or "normal",  # 🆕 v7.178: 返回分析模式
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
        self,
        status: Optional[str] = None,
        pinned_only: bool = False,
        user_id: Optional[str] = None,  # 🆕 v7.178: 按用户过滤
    ) -> int:
        """
        统计归档会话数量

        Args:
            status: 过滤状态（可选）
            pinned_only: 是否只统计置顶会话（默认False）
            user_id: 用户ID（可选，用于过滤当前用户的会话）

        Returns:
            会话数量
        """
        try:
            db = self._get_db()
            query = db.query(ArchivedSession)

            # 🆕 v7.178: 按用户过滤
            if user_id:
                query = query.filter(ArchivedSession.user_id == user_id)

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

    # ==================== 🆕 v7.163: 搜索会话归档方法 ====================

    async def archive_search_session(
        self,
        session_id: str,
        query: str,
        search_result: Dict[str, Any],
        user_id: Optional[str] = None,
        force: bool = False,
    ) -> bool:
        """
        归档搜索会话到数据库

        Args:
            session_id: 搜索会话ID
            query: 搜索查询
            search_result: 搜索结果数据
            user_id: 用户ID（可选）
            force: 是否强制覆盖

        Returns:
            是否归档成功
        """
        try:
            db = self._get_db()

            # 检查是否已存在
            existing = db.query(ArchivedSearchSession).filter(ArchivedSearchSession.session_id == session_id).first()

            # 🆕 v7.177: 提取新字段
            is_deep_mode = 1 if search_result.get("isDeepMode", False) else 0
            thinking_content = search_result.get("thinkingContent", "")
            answer_content = search_result.get("answerContent", "")
            search_plan = search_result.get("searchPlan")
            rounds = search_result.get("rounds", [])
            total_rounds = search_result.get("totalRounds", 0)

            # 🆕 v7.219: 提取需求洞察相关字段
            l0_content = search_result.get("l0Content", "")
            problem_solving_thinking = search_result.get("problemSolvingThinking", "")
            structured_info = search_result.get("structuredInfo")

            # 🆕 v7.241: 提取框架清单和搜索主线
            framework_checklist = search_result.get("frameworkChecklist")
            search_master_line = search_result.get("searchMasterLine")

            if existing:
                if force:
                    # 更新现有记录
                    existing.query = query
                    existing.sources = json.dumps(search_result.get("sources", []), ensure_ascii=False)
                    existing.images = json.dumps(search_result.get("images", []), ensure_ascii=False)
                    existing.reasoning = search_result.get("reasoning", "")
                    existing.content = search_result.get("content", "")
                    existing.execution_time = int(search_result.get("executionTime", 0) * 1000)
                    existing.source_count = len(search_result.get("sources", []))
                    existing.image_count = len(search_result.get("images", []))
                    existing.updated_at = datetime.now()
                    # 🆕 v7.177: 更新新字段
                    existing.is_deep_mode = is_deep_mode
                    existing.thinking_content = thinking_content
                    existing.answer_content = answer_content
                    existing.search_plan = json.dumps(search_plan, ensure_ascii=False) if search_plan else None
                    existing.rounds = json.dumps(rounds, ensure_ascii=False) if rounds else None
                    existing.total_rounds = total_rounds
                    # 🆕 v7.219: 更新需求洞察相关字段
                    existing.l0_content = l0_content
                    existing.problem_solving_thinking = problem_solving_thinking
                    existing.structured_info = (
                        json.dumps(structured_info, ensure_ascii=False) if structured_info else None
                    )
                    # 🆕 v7.241: 更新框架清单和搜索主线
                    if framework_checklist:
                        existing.search_framework = json.dumps(framework_checklist, ensure_ascii=False)
                    if search_master_line:
                        existing.search_master_line = json.dumps(search_master_line, ensure_ascii=False)
                    existing.current_round = search_result.get("currentRound", 0)
                    existing.overall_completeness = int(search_result.get("overallCompleteness", 0) * 100)
                    db.commit()
                    logger.info(f"✅ 搜索会话已更新: {session_id} | deep_mode={is_deep_mode} | rounds={total_rounds}")

                    # 🆕 v7.203: 监控告警 - 深度搜索模式下 rounds=0 是异常情况
                    if is_deep_mode and total_rounds == 0 and len(search_result.get("sources", [])) > 0:
                        logger.warning(
                            f"⚠️ [ALERT] 搜索轮次异常: session={session_id} | "
                            f"deep_mode=1 但 rounds=0 | sources={len(search_result.get('sources', []))} | "
                            f"可能是前端未正确传递 totalRounds 字段"
                        )
                else:
                    logger.debug(f"⚠️ 搜索会话已存在，跳过: {session_id}")
                db.close()
                return True

            # 创建新记录
            archived = ArchivedSearchSession(
                session_id=session_id,
                user_id=user_id,
                query=query,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                sources=json.dumps(search_result.get("sources", []), ensure_ascii=False),
                images=json.dumps(search_result.get("images", []), ensure_ascii=False),
                reasoning=search_result.get("reasoning", ""),
                content=search_result.get("content", ""),
                execution_time=int(search_result.get("executionTime", 0) * 1000),
                source_count=len(search_result.get("sources", [])),
                image_count=len(search_result.get("images", [])),
                # 🆕 v7.177: 新增字段
                is_deep_mode=is_deep_mode,
                thinking_content=thinking_content,
                answer_content=answer_content,
                search_plan=json.dumps(search_plan, ensure_ascii=False) if search_plan else None,
                rounds=json.dumps(rounds, ensure_ascii=False) if rounds else None,
                total_rounds=total_rounds,
                # 🆕 v7.219: 需求洞察相关字段
                l0_content=l0_content,
                problem_solving_thinking=problem_solving_thinking,
                structured_info=json.dumps(structured_info, ensure_ascii=False) if structured_info else None,
                # 🆕 v7.241: 框架清单和搜索主线持久化
                search_framework=json.dumps(framework_checklist, ensure_ascii=False) if framework_checklist else None,
                search_master_line=json.dumps(search_master_line, ensure_ascii=False) if search_master_line else None,
                current_round=search_result.get("currentRound", 0),
                overall_completeness=int(search_result.get("overallCompleteness", 0) * 100),
            )

            db.add(archived)
            db.commit()
            db.close()

            logger.info(f"✅ 搜索会话已归档: {session_id}, query={query[:30]}...")

            # 🆕 v7.203: 监控告警 - 深度搜索模式下 rounds=0 是异常情况
            if is_deep_mode and total_rounds == 0 and len(search_result.get("sources", [])) > 0:
                logger.warning(
                    f"⚠️ [ALERT] 搜索轮次异常: session={session_id} | "
                    f"deep_mode=1 但 rounds=0 | sources={len(search_result.get('sources', []))} | "
                    f"可能是前端未正确传递 totalRounds 字段"
                )

            return True

        except Exception as e:
            logger.error(f"❌ 搜索会话归档失败: {e}")
            return False

    async def get_search_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取归档的搜索会话

        Args:
            session_id: 搜索会话ID

        Returns:
            搜索会话数据，不存在返回 None
        """
        try:
            db = self._get_db()

            session = db.query(ArchivedSearchSession).filter(ArchivedSearchSession.session_id == session_id).first()

            db.close()

            if not session:
                return None

            # 🆕 v7.177: 返回新增字段
            # 🆕 v7.241: 将搜索结果包装在 search_result 字段中，以便测试脚本访问
            search_result = {
                "sources": json.loads(session.sources) if session.sources else [],
                "images": json.loads(session.images) if session.images else [],
                "reasoning": session.reasoning or "",
                "content": session.content or "",
                "executionTime": session.execution_time / 1000,
                "status": "done",
                # 🆕 v7.177: 新增深度搜索字段
                "isDeepMode": bool(getattr(session, "is_deep_mode", 0)),
                "thinkingContent": getattr(session, "thinking_content", "") or "",
                "answerContent": getattr(session, "answer_content", "") or "",
                "searchPlan": json.loads(session.search_plan) if getattr(session, "search_plan", None) else None,
                "rounds": json.loads(session.rounds) if getattr(session, "rounds", None) else [],
                "totalRounds": getattr(session, "total_rounds", 0) or 0,
                # 🆕 v7.219: 返回需求洞察相关字段
                "l0Content": getattr(session, "l0_content", "") or "",
                "problemSolvingThinking": getattr(session, "problem_solving_thinking", "") or "",
                "structuredInfo": json.loads(session.structured_info)
                if getattr(session, "structured_info", None)
                else None,
                # 🆕 v7.235: 返回搜索框架（支持断点续传）
                "searchFramework": json.loads(session.search_framework)
                if getattr(session, "search_framework", None)
                else None,
                "searchMasterLine": json.loads(session.search_master_line)
                if getattr(session, "search_master_line", None)
                else None,
                # 🆕 v7.241: 返回框架清单（前端使用 frameworkChecklist 字段名）
                "frameworkChecklist": json.loads(session.search_framework)
                if getattr(session, "search_framework", None)
                else None,
                "currentRound": getattr(session, "current_round", 0) or 0,
                "overallCompleteness": (getattr(session, "overall_completeness", 0) or 0) / 100,
            }

            return {
                "session_id": session.session_id,
                "query": session.query,
                "created_at": session.created_at.isoformat(),
                # 🆕 v7.189: 返回 user_id 用于权限验证
                "user_id": getattr(session, "user_id", None),
                # 🆕 v7.241: 包装搜索结果
                "search_result": search_result,
            }

        except Exception as e:
            logger.error(f"❌ 获取搜索会话失败: {e}")
            return None

    async def list_search_sessions(
        self, user_id: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        获取搜索历史列表

        Args:
            user_id: 用户ID（可选，用于过滤）
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            搜索会话列表
        """
        try:
            db = self._get_db()

            query = db.query(ArchivedSearchSession)

            if user_id:
                query = query.filter(ArchivedSearchSession.user_id == user_id)

            sessions = query.order_by(ArchivedSearchSession.created_at.desc()).offset(offset).limit(limit).all()

            db.close()

            return [
                {
                    "session_id": s.session_id,
                    "query": s.query,
                    "source_count": s.source_count,
                    "image_count": s.image_count,
                    "created_at": s.created_at.isoformat(),
                }
                for s in sessions
            ]

        except Exception as e:
            logger.error(f"❌ 获取搜索历史列表失败: {e}")
            return []

    async def get_database_stats(self) -> Dict[str, Any]:
        """
        🆕 v7.200: 获取数据库统计信息（性能监控）

        Returns:
            数据库统计信息
        """
        try:
            # 获取数据库文件大小
            if "sqlite" in self.database_url:
                db_path = Path(self.database_url.replace("sqlite:///", ""))
                if db_path.exists():
                    size_bytes = db_path.stat().st_size
                    size_mb = size_bytes / (1024 * 1024)
                    size_gb = size_bytes / (1024 * 1024 * 1024)
                else:
                    size_bytes = size_mb = size_gb = 0
            else:
                size_bytes = size_mb = size_gb = -1  # 非 SQLite 数据库

            db = self._get_db()

            # 统计记录数
            total_sessions = db.query(ArchivedSession).count()
            total_search_sessions = db.query(ArchivedSearchSession).count()

            # 统计各状态会话数
            completed_count = db.query(ArchivedSession).filter(ArchivedSession.status == "completed").count()
            failed_count = db.query(ArchivedSession).filter(ArchivedSession.status == "failed").count()

            # 计算平均大小
            avg_size_mb = size_mb / total_sessions if total_sessions > 0 else 0

            db.close()

            # 判断健康状态
            health_status = "healthy"
            warnings = []

            if size_gb > 50:
                health_status = "critical"
                warnings.append("数据库文件超过 50GB，严重影响性能")
            elif size_gb > 10:
                health_status = "warning"
                warnings.append("数据库文件超过 10GB，建议执行清理")

            if avg_size_mb > 20:
                warnings.append(f"平均会话大小 {avg_size_mb:.2f}MB 偏大，建议检查数据结构")

            return {
                "size_bytes": size_bytes,
                "size_mb": round(size_mb, 2),
                "size_gb": round(size_gb, 2),
                "file_size_mb": round(size_mb, 2),  # 前端期望的字段名
                "total_sessions": total_sessions,
                "total_records": total_sessions,  # 前端期望的字段名
                "total_search_sessions": total_search_sessions,
                "completed_count": completed_count,
                "failed_count": failed_count,
                "status_distribution": {  # 前端期望的格式
                    "completed": completed_count,
                    "failed": failed_count,
                },
                "avg_size_mb": round(avg_size_mb, 2),
                "health_status": health_status.upper(),  # 前端期望大写
                "thresholds": {  # 前端期望的阈值信息
                    "healthy_max_mb": 10240,  # 10GB
                    "warning_max_mb": 51200,  # 50GB
                },
                "warnings": warnings,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"❌ 获取数据库统计信息失败: {e}")
            return {
                "error": str(e),
                "health_status": "unknown",
            }

    async def vacuum_database(self) -> bool:
        """
        🆕 v7.200: 执行数据库 VACUUM 压缩

        回收已删除数据占用的空间，重建索引，优化性能
        注意：VACUUM 会锁定整个数据库，建议在低峰期执行

        Returns:
            是否执行成功
        """
        if "sqlite" not in self.database_url:
            logger.warning("⚠️ VACUUM 仅支持 SQLite 数据库")
            return False

        try:
            logger.info("🔧 开始执行 VACUUM 数据库压缩...")

            # 记录压缩前大小
            stats_before = await self.get_database_stats()
            size_before_mb = stats_before.get("size_mb", 0)

            # 执行 VACUUM
            conn = self.engine.raw_connection()
            cursor = conn.cursor()
            cursor.execute("VACUUM")
            conn.commit()
            cursor.close()
            conn.close()

            # 记录压缩后大小
            stats_after = await self.get_database_stats()
            size_after_mb = stats_after.get("size_mb", 0)

            saved_mb = size_before_mb - size_after_mb

            logger.success(
                f"✅ VACUUM 完成: {size_before_mb:.2f}MB → {size_after_mb:.2f}MB "
                f"(节省 {saved_mb:.2f}MB, {saved_mb/size_before_mb*100:.1f}%)"
            )

            return True

        except Exception as e:
            logger.error(f"❌ VACUUM 执行失败: {e}")
            return False

    async def archive_old_sessions_to_cold_storage(
        self, days_threshold: int = 30, dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        🆕 v7.200: 将旧会话归档到冷存储（JSON文件）

        Args:
            days_threshold: 归档阈值（天数）
            dry_run: 是否为模拟运行（不实际删除）

        Returns:
            归档结果统计
        """
        try:
            threshold_date = datetime.now() - timedelta(days=days_threshold)

            db = self._get_db()

            # 查询需要归档的会话
            old_sessions = db.query(ArchivedSession).filter(ArchivedSession.created_at < threshold_date).all()

            if not old_sessions:
                logger.info(f"✓ 无需归档：未找到 {days_threshold} 天前的会话")
                db.close()
                return {
                    "archived_count": 0,
                    "total_checked": 0,
                    "dry_run": dry_run,
                }

            # 创建冷存储目录
            cold_storage_dir = Path(__file__).parent.parent.parent / "data" / "cold_storage"
            cold_storage_dir.mkdir(exist_ok=True)

            archived_count = 0
            failed_count = 0

            for session in old_sessions:
                try:
                    # 导出到 JSON 文件
                    file_path = cold_storage_dir / f"{session.session_id}.json"

                    session_dict = {
                        "session_id": session.session_id,
                        "user_id": session.user_id,
                        "user_input": session.user_input,
                        "status": session.status,
                        "mode": session.mode,
                        "created_at": session.created_at.isoformat(),
                        "archived_at": session.archived_at.isoformat(),
                        "session_data": json.loads(session.session_data) if session.session_data else {},
                        "final_report": session.final_report,
                    }

                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(session_dict, f, ensure_ascii=False, indent=2)

                    # 删除数据库记录
                    if not dry_run:
                        db.delete(session)

                    archived_count += 1

                except Exception as e:
                    logger.error(f"❌ 归档会话失败 {session.session_id}: {e}")
                    failed_count += 1

            if not dry_run:
                db.commit()

            db.close()

            result = {
                "archived_count": archived_count,
                "failed_count": failed_count,
                "total_checked": len(old_sessions),
                "dry_run": dry_run,
                "cold_storage_dir": str(cold_storage_dir),
            }

            if dry_run:
                logger.info(f"🔍 模拟运行: 将归档 {archived_count} 个会话（未实际删除）")
            else:
                logger.success(f"✅ 冷存储归档完成: {archived_count} 个会话已移至 {cold_storage_dir}")

            return result

        except Exception as e:
            logger.error(f"❌ 冷存储归档失败: {e}")
            return {
                "error": str(e),
                "archived_count": 0,
            }

    # 🆕 v7.189: 删除搜索会话
    async def delete_search_session(self, session_id: str) -> bool:
        """
        删除归档的搜索会话

        Args:
            session_id: 搜索会话ID

        Returns:
            是否删除成功
        """
        try:
            db = self._get_db()

            result = db.query(ArchivedSearchSession).filter(ArchivedSearchSession.session_id == session_id).delete()

            db.commit()
            db.close()

            if result > 0:
                logger.info(f"✅ 搜索会话已删除: {session_id}")
                return True
            else:
                logger.warning(f"⚠️ 搜索会话不存在: {session_id}")
                return False

        except Exception as e:
            logger.error(f"❌ 删除搜索会话失败: {session_id} | {e}")
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
        from intelligent_project_analyzer.settings import settings

        _archive_manager = SessionArchiveManager(settings.database_url)

    return _archive_manager
