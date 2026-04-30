"""
外部项目数据库模型

PostgreSQL + pgvector 支持向量搜索
"""

from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, Float, DateTime, 
    Boolean, JSON, Index, UniqueConstraint, ForeignKey, ARRAY
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional, List, Dict, Any

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
    
    # 主键
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # 数据源标识
    source = Column(String(50), nullable=False, index=True)  # archdaily/gooood/dezeen
    source_id = Column(String(200), nullable=False)  # 网站内部ID
    url = Column(Text, nullable=False, unique=True)
    
    # 基本信息
    title = Column(Text, nullable=False)
    description = Column(Text)  # 核心内容，用于向量化
    description_vector = Column(Vector(1536) if PGVECTOR_AVAILABLE else Text)  # OpenAI Embeddings
    
    # 元数据（JSONB格式，灵活存储）
    architects = Column(JSONB)  # [{"name": "xxx", "firm": "xxx"}]
    location = Column(JSONB)  # {"country": "xxx", "city": "xxx", "lat": 0, "lng": 0}
    area_sqm = Column(Float)  # 统一为平方米
    year = Column(Integer, index=True)
    cost = Column(JSONB)  # {"currency": "USD", "amount": 1000000}
    
    # 分类与标签
    primary_category = Column(String(100), index=True)  # 主分类
    sub_categories = Column(ARRAY(String))  # 子分类数组
    tags = Column(ARRAY(String))  # 标签数组
    
    # 社交数据
    views = Column(Integer, default=0, index=True)
    likes = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    
    # 质量评分
    quality_score = Column(Float, index=True)  # 0-1分数
    quality_factors = Column(JSONB)  # 质量因子详情
    
    # 时间戳
    publish_date = Column(DateTime, index=True)
    crawled_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 原始数据（调试用）
    raw_html = Column(Text)  # 可选，压缩存储
    
    # 关系
    images = relationship("ExternalProjectImage", back_populates="project", cascade="all, delete-orphan")
    
    # 索引
    __table_args__ = (
        UniqueConstraint('source', 'source_id', name='uq_source_id'),
        Index('idx_source_publish_date', 'source', 'publish_date'),
        Index('idx_quality_score_desc', quality_score.desc()),
        # 向量索引（需要在数据库中手动创建：CREATE INDEX ON external_projects USING ivfflat (description_vector vector_cosine_ops)）
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
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    project_id = Column(BigInteger, ForeignKey('external_projects.id', ondelete='CASCADE'), nullable=False)
    
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
        Index('idx_project_id', 'project_id'),
        Index('idx_is_cover', 'is_cover'),
    )


class SyncHistory(Base):
    """同步历史记录表"""
    __tablename__ = "sync_history"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    source = Column(String(50), nullable=False, index=True)
    category = Column(String(100))  # 可选（特定分类同步）
    
    started_at = Column(DateTime, nullable=False, default=datetime.now)
    completed_at = Column(DateTime)
    status = Column(String(20), nullable=False, default='running')  # running/completed/failed
    
    projects_total = Column(Integer, default=0)
    projects_new = Column(Integer, default=0)
    projects_updated = Column(Integer, default=0)
    projects_failed = Column(Integer, default=0)
    
    error_message = Column(Text)
    
    # 索引
    __table_args__ = (
        Index('idx_source_started', 'source', started_at.desc()),
    )
    
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
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    project_id = Column(BigInteger, ForeignKey('external_projects.id', ondelete='CASCADE'))
    
    issue_type = Column(String(50), nullable=False, index=True)  # missing_description/low_quality/...
    severity = Column(String(20), nullable=False, index=True)  # low/medium/high/critical
    
    detected_at = Column(DateTime, default=datetime.now, nullable=False)
    resolved_at = Column(DateTime)
    
    # 索引
    __table_args__ = (
        Index('idx_unresolved', 'resolved_at', postgresql_where=(resolved_at.is_(None))),
    )
    
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


# ============================================================================
# 数据库连接与会话管理
# ============================================================================

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from loguru import logger
import os

class ExternalProjectDatabase:
    """外部项目数据库管理器"""
    
    def __init__(self, database_url: Optional[str] = None):
        """
        初始化数据库连接
        
        Args:
            database_url: 数据库URL（默认从环境变量EXTERNAL_DB_URL读取）
        """
        self.database_url = database_url or os.getenv(
            'EXTERNAL_DB_URL',
            'postgresql://postgres:password@localhost:5432/external_projects'
        )
        
        # 创建引擎
        self.engine = create_engine(
            self.database_url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,  # 连接前检查
            echo=False  # 生产环境关闭SQL日志
        )
        
        # 创建会话工厂
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        logger.info(f"✅ 外部项目数据库已连接")
    
    def create_tables(self):
        """创建所有表"""
        Base.metadata.create_all(bind=self.engine)
        logger.info("✅ 数据库表已创建")
        
        # 创建向量索引（需要pgvector扩展）
        if PGVECTOR_AVAILABLE:
            try:
                with self.engine.connect() as conn:
                    # 创建pgvector扩展
                    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
                    conn.commit()
                    
                    # 创建向量索引
                    conn.execute("""
                        CREATE INDEX IF NOT EXISTS idx_description_vector 
                        ON external_projects 
                        USING ivfflat (description_vector vector_cosine_ops)
                        WITH (lists = 100)
                    """)
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
_db_instance: Optional[ExternalProjectDatabase] = None

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
    'ExternalProject',
    'ExternalProjectImage',
    'SyncHistory',
    'QualityIssue',
    'ExternalProjectDatabase',
    'get_external_db',
]
