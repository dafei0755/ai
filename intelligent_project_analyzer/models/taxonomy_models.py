"""
分类维度学习系统数据模型

提供自演化的分类体系，支持从用户反馈和LLM分析中学习新的设计概念。
"""

from datetime import datetime
from sqlalchemy import Column, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class TaxonomyExtendedType(Base):
    """扩展维度类型（经过验证晋升的标签）"""

    __tablename__ = "taxonomy_extended_types"

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 维度信息
    dimension = Column(String(50), nullable=False, index=True)  # 所属维度（motivation, style等）
    type_id = Column(String(100), nullable=False, index=True)  # 类型ID（snake_case）

    # 标签信息
    label_zh = Column(String(100), nullable=False)  # 中文标签
    label_en = Column(String(100), nullable=False)  # 英文标签
    keywords = Column(Text, nullable=True)  # 关键词列表（JSON数组）

    # 使用统计
    usage_count = Column(Integer, default=0)  # 累计使用次数
    success_count = Column(Integer, default=0)  # 用户确认的成功次数

    # 时间戳
    promoted_at = Column(DateTime, default=datetime.now, nullable=False)  # 晋升时间
    last_used_at = Column(DateTime, nullable=True)  # 最后使用时间

    # 索引
    __table_args__ = (
        Index("idx_ext_dimension_type", "dimension", "type_id", unique=True),
        Index("idx_ext_usage", "usage_count"),
        Index("idx_ext_success_rate", "success_count"),
    )


class TaxonomyEmergingType(Base):
    """新兴维度类型（待验证的候选标签）"""

    __tablename__ = "taxonomy_emerging_types"

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 维度信息
    dimension = Column(String(50), nullable=False, index=True)
    type_id = Column(String(100), nullable=False, index=True)

    # 标签信息
    label_zh = Column(String(100), nullable=False)
    label_en = Column(String(100), nullable=False)
    keywords = Column(Text, nullable=True)  # JSON数组

    # 验证统计
    case_count = Column(Integer, default=0)  # 使用案例数
    success_count = Column(Integer, default=0)  # 确认为有效的次数

    # 来源信息
    source = Column(String(50), nullable=False)  # user_suggest | llm_discover
    confidence_score = Column(Float, default=0.0)  # 置信度（0.0-1.0）
    task_type = Column(String(20), default="user_demand", nullable=False)  # v7.501: user_demand | research

    # 时间戳
    created_at = Column(DateTime, default=datetime.now, nullable=False, index=True)
    last_used_at = Column(DateTime, nullable=True)

    # 索引
    __table_args__ = (
        Index("idx_emg_dimension_type", "dimension", "type_id", unique=True),
        Index("idx_emg_case_count", "case_count"),
        Index("idx_emg_confidence", "confidence_score"),
        Index("idx_emg_source", "source"),
        Index("idx_emg_task_type", "task_type"),  # v7.501新增
    )


class TaxonomyUserFeedback(Base):
    """用户反馈记录"""

    __tablename__ = "taxonomy_user_feedback"

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 关联信息
    task_id = Column(String(100), nullable=False, index=True)  # 关联的任务/会话ID
    dimension = Column(String(50), nullable=False, index=True)
    type_id = Column(String(100), nullable=False, index=True)

    # 反馈信息
    action = Column(String(20), nullable=False)  # confirm | reject | edit
    edited_label = Column(String(100), nullable=True)  # 用户修改后的标签（如果有）
    comment = Column(Text, nullable=True)  # 用户备注

    # 时间戳
    created_at = Column(DateTime, default=datetime.now, nullable=False, index=True)

    # 索引
    __table_args__ = (
        Index("idx_fb_task_dimension", "task_id", "dimension"),
        Index("idx_fb_type_action", "type_id", "action"),
        Index("idx_fb_created", "created_at"),
    )


class TaxonomyUserSuggestion(Base):
    """用户建议（用户主动提交的新概念）"""

    __tablename__ = "taxonomy_user_suggestions"

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 关联信息
    task_id = Column(String(100), nullable=False, index=True)
    dimension = Column(String(50), nullable=False, index=True)

    # 建议内容
    suggested_label = Column(String(100), nullable=False)  # 建议的标签
    keywords = Column(Text, nullable=True)  # 关键词（JSON数组）
    reason = Column(Text, nullable=True)  # 建议理由

    # 审核状态
    status = Column(String(20), default="pending", nullable=False, index=True)  # pending | approved | rejected
    reviewed_at = Column(DateTime, nullable=True)
    reviewer_comment = Column(Text, nullable=True)

    # 时间戳
    submitted_at = Column(DateTime, default=datetime.now, nullable=False, index=True)

    # 索引
    __table_args__ = (
        Index("idx_sug_dimension_status", "dimension", "status"),
        Index("idx_sug_submitted", "submitted_at"),
    )


class TaxonomyConceptDiscovery(Base):
    """LLM概念发现记录"""

    __tablename__ = "taxonomy_concept_discoveries"

    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 概念信息
    concept_cluster = Column(String(200), nullable=False, index=True)  # 概念集群名称
    keywords = Column(Text, nullable=False)  # 提取的关键词（JSON数组）
    sample_inputs = Column(Text, nullable=False)  # 样本输入（JSON数组）

    # 发现统计
    occurrence_count = Column(Integer, default=1)  # 出现频次
    confidence = Column(Float, default=0.0)  # 置信度（0.0-1.0）

    # 映射信息
    suggested_dimension = Column(String(50), nullable=True, index=True)  # 建议的维度
    suggested_type_id = Column(String(100), nullable=True)  # 建议的类型ID
    task_type = Column(String(20), default="user_demand", nullable=False)  # v7.501: user_demand | research

    # 时间戳
    discovered_at = Column(DateTime, default=datetime.now, nullable=False, index=True)
    last_seen_at = Column(DateTime, nullable=True)

    # 索引
    __table_args__ = (
        Index("idx_disc_cluster", "concept_cluster", unique=True),
        Index("idx_disc_confidence", "confidence"),
        Index("idx_disc_suggested_dim", "suggested_dimension"),
        Index("idx_disc_task_type", "task_type"),  # v7.501新增
    )
