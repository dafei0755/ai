"""
外部项目数据库模型

PostgreSQL + pgvector 支持向量搜索
"""

import os
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict

from loguru import logger
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    text,
)

# PostgreSQL JSONB（支持 GIN 索引）
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker

JSONType = JSONB

try:
    from pgvector.sqlalchemy import Vector

    PGVECTOR_AVAILABLE = True
except ImportError:
    PGVECTOR_AVAILABLE = False

    # 回退到Text类型（开发模式）
    def Vector(dim):
        return Text


Base = declarative_base()


class ExternalProject(Base):
    """外部项目主表"""

    __tablename__ = "external_projects"

    # 主键 (SQLite需要用Integer才能自动递增)
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 数据源标识
    source = Column(String(50), nullable=False, index=True)  # archdaily/gooood/dezeen
    source_id = Column(String(200), nullable=False)  # 网站内部ID
    url = Column(Text, nullable=False, unique=True)

    # 基本信息（双语存储）
    title = Column(Text, nullable=False)  # 保留用于向后兼容
    title_en = Column(Text)  # 英文标题
    title_zh = Column(Text)  # 中文标题

    description = Column(Text)  # 保留用于向后兼容
    description_en = Column(Text)  # 英文描述
    description_zh = Column(Text)  # 中文描述
    lang = Column(String(20), nullable=True)  # 页面语言: "zh" / "en" / "bilingual"

    description_vector = Column(Vector(1536) if PGVECTOR_AVAILABLE else Text)  # OpenAI Embeddings

    # 翻译元数据
    translation_engine = Column(String(50))  # 'deepseek', 'gpt4', 'claude', 'human'
    translation_quality = Column(Float)  # 翻译质量评分 0-1
    translated_at = Column(DateTime)  # 翻译时间
    is_human_reviewed = Column(Boolean, default=False)  # 人工审核标志

    # 元数据（JSON格式，灵活存储）
    architects = Column(JSONType)  # [{"name": "xxx", "firm": "xxx"}]
    location = Column(JSONType)  # {"country": "xxx", "city": "xxx", "lat": 0, "lng": 0}
    area_sqm = Column(Float)  # 统一为平方米
    year = Column(Integer, index=True)
    cost = Column(JSONType)  # {"currency": "USD", "amount": 1000000}

    # 分类与标签（SQLite用JSON，PostgreSQL用ARRAY）
    primary_category = Column(String(100), index=True)  # 主分类
    sub_categories = Column(JSONB)  # 子分类数组
    tags = Column(JSONB)  # 标签数组

    # 社交数据
    views = Column(Integer, default=0, index=True)
    likes = Column(Integer, default=0)
    shares = Column(Integer, default=0)

    # 质量评分
    quality_score = Column(Float, index=True)  # 0-1分数
    quality_factors = Column(JSONType)  # 质量因子详情

    # 时间戳
    publish_date = Column(DateTime, index=True)
    crawled_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 原始数据（调试用）
    raw_html = Column(Text)  # 可选，压缩存储

    # 内容哈希（防止无意义重写，content_hash 相同时只更新 updated_at）
    # sha256( title + description_zh + description_en )，64 hex 字符
    content_hash = Column(String(64), index=True, nullable=True)

    # 站点特有字段（JSONB catch-all）
    # 存储各网站独有但不値得单独加列的字段，例如：
    #   gooood: {"owner": "xx", "landscape_architect": "xx"}
    #   archdaily_cn: {"programme": "Office", "structural_engineer": "xx"}
    #   dezeen: {"article_type": "architecture", "author": "xx"}
    extra_fields = Column(JSONB, nullable=True)

    # 关系
    images = relationship("ExternalProjectImage", back_populates="project", cascade="all, delete-orphan")

    # 索引
    __table_args__ = (
        UniqueConstraint("source", "source_id", name="uq_source_id"),
        Index("idx_source_publish_date", "source", "publish_date"),
        Index("idx_source_category", "source", "primary_category"),
        Index("idx_quality_score_desc", quality_score.desc()),
        # GIN 索引（仅 PostgreSQL，对 JSONB 字段快速查询）
        Index("idx_architects_gin", "architects", postgresql_using="gin"),
        Index("idx_tags_gin", "tags", postgresql_using="gin"),
        # 标题 trgm 模糊搜索（需 pg_trgm 扩展）
        Index("idx_title_trgm", "title", postgresql_using="gin", postgresql_ops={"title": "gin_trgm_ops"}),
    )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "source": self.source,
            "source_id": self.source_id,
            "url": self.url,
            "title": self.title,
            "description": self.description,
            "architects": self.architects,
            "location": self.location,
            "area_sqm": self.area_sqm,
            "year": self.year,
            "primary_category": self.primary_category,
            "tags": self.tags,
            "quality_score": self.quality_score,
            "views": self.views,
            "publish_date": self.publish_date.isoformat() if self.publish_date else None,
            "crawled_at": self.crawled_at.isoformat() if self.crawled_at else None,
        }


class ExternalProjectImage(Base):
    """项目图片表"""

    __tablename__ = "external_project_images"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("external_projects.id", ondelete="CASCADE"), nullable=False)

    url = Column(Text, nullable=False)
    caption = Column(Text)
    width = Column(Integer)
    height = Column(Integer)
    file_size = Column(Integer)  # 字节
    storage_path = Column(Text)  # MinIO/S3路径
    order_index = Column(Integer, default=0)
    is_cover = Column(Boolean, default=False)

    # 关系
    project = relationship("ExternalProject", back_populates="images")

    # 索引
    __table_args__ = (
        Index("idx_project_id", "project_id"),
        Index("idx_is_cover", "is_cover"),
    )


class SyncHistory(Base):
    """同步历史记录表"""

    __tablename__ = "sync_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(50), nullable=False, index=True)
    category = Column(String(100))  # 可选（特定分类同步）

    started_at = Column(DateTime, nullable=False, default=datetime.now)
    completed_at = Column(DateTime)
    status = Column(String(20), nullable=False, default="running")  # running/completed/failed

    projects_total = Column(Integer, default=0)
    projects_new = Column(Integer, default=0)
    projects_updated = Column(Integer, default=0)
    projects_failed = Column(Integer, default=0)

    error_message = Column(Text)

    # 索引
    __table_args__ = (Index("idx_source_started", "source", started_at.desc()),)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "source": self.source,
            "category": self.category,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status,
            "projects_total": self.projects_total,
            "projects_new": self.projects_new,
            "projects_updated": self.projects_updated,
            "projects_failed": self.projects_failed,
            "error_message": self.error_message,
        }


class QualityIssue(Base):
    """数据质量问题表"""

    __tablename__ = "quality_issues"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("external_projects.id", ondelete="CASCADE"))

    issue_type = Column(String(50), nullable=False, index=True)  # missing_description/low_quality/...
    severity = Column(String(20), nullable=False, index=True)  # low/medium/high/critical

    detected_at = Column(DateTime, default=datetime.now, nullable=False)
    resolved_at = Column(DateTime)

    # 索引
    __table_args__ = (Index("idx_unresolved", "resolved_at", postgresql_where=(resolved_at.is_(None))),)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "issue_type": self.issue_type,
            "severity": self.severity,
            "detected_at": self.detected_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


class ProjectDiscovery(Base):
    """已发现的项目URL索引（替代原 project_index.db）"""

    __tablename__ = "project_discovery"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(50), nullable=False, index=True)
    source_id = Column(String(200), nullable=False)
    url = Column(String(500), nullable=False, unique=True, index=True)
    category = Column(String(100), index=True)
    sub_category = Column(String(100))
    title = Column(String(500))
    preview_image = Column(String(500))

    # 爬取状态追踪
    discovered_at = Column(DateTime, default=datetime.now, nullable=False)
    crawled_at = Column(DateTime)
    is_crawled = Column(Boolean, default=False, nullable=False, index=True)
    crawl_attempts = Column(Integer, default=0)
    last_error = Column(Text)

    __table_args__ = (
        Index("idx_discovery_source_crawled", "source", "is_crawled"),
        Index("idx_discovery_source_category", "source", "category"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "url": self.url,
            "title": self.title,
            "category": self.category,
            "is_crawled": self.is_crawled,
            "crawl_attempts": self.crawl_attempts,
            "discovered_at": self.discovered_at.isoformat() if self.discovered_at else None,
            "crawled_at": self.crawled_at.isoformat() if self.crawled_at else None,
            "last_error": self.last_error,
        }


# ============================================================================
# 数据库连接与会话管理
# ============================================================================


class ExternalProjectDatabase:
    """外部项目数据库管理器"""

    def __init__(self, database_url: str | None = None):
        """
        初始化数据库连接

        Args:
            database_url: 数据库URL（默认从环境变量EXTERNAL_DB_URL读取）
        """
        self.database_url = database_url or os.getenv(
            "EXTERNAL_DB_URL", "postgresql://postgres:password@localhost:5432/external_projects"
        )

        # 创建 PostgreSQL 引擎
        self.engine = create_engine(self.database_url, pool_size=10, max_overflow=20, pool_pre_ping=True, echo=False)
        logger.info(f"✅ 外部项目数据库已连接: {self.database_url.split('@')[-1] if '@' in self.database_url else 'local'}")

        # 创建会话工厂
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def create_tables(self):
        """创建所有表"""
        Base.metadata.create_all(bind=self.engine)
        logger.info("✅ 数据库表已创建")

        # PostgreSQL: 启用扩展并创建额外索引
        if "postgresql" in self.database_url or "postgres://" in self.database_url:
            try:
                with self.engine.connect() as conn:
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gin"))
                    conn.commit()
                    logger.info("✅ PostgreSQL 扩展已启用 (pg_trgm, btree_gin)")
            except Exception as e:
                logger.warning(f"扩展启用失败（可能已存在）: {e}")

        # 创建向量索引（需要pgvector）
        if PGVECTOR_AVAILABLE:
            try:
                with self.engine.connect() as conn:
                    # 创建pgvector扩展
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                    conn.commit()

                    # 创建向量索引
                    conn.execute(
                        text(
                            """
                        CREATE INDEX IF NOT EXISTS idx_description_vector
                        ON external_projects
                        USING ivfflat (description_vector vector_cosine_ops)
                        WITH (lists = 100)
                    """
                        )
                    )
                    conn.commit()
                    logger.info("✅ 向量索引已创建")
            except Exception as e:
                logger.warning(f"⚠️ 向量索引创建失败（需要PostgreSQL + pgvector）: {e}")

    @contextmanager
    def get_session(self) -> Session:
        """获取数据库会话（上下文管理器）"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_db(self) -> Session:
        """获取数据库会话（依赖注入用）"""
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()


# 全局数据库实例
_db_instance: ExternalProjectDatabase | None = None


def get_external_db() -> ExternalProjectDatabase:
    """获取全局数据库实例"""
    global _db_instance
    if _db_instance is None:
        _db_instance = ExternalProjectDatabase()
    return _db_instance


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    "ExternalProject",
    "ExternalProjectImage",
    "SyncHistory",
    "QualityIssue",
    "ProjectDiscovery",
    "ExternalProjectDatabase",
    "get_external_db",
]
