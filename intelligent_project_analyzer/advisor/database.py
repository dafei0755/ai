import json
from contextlib import contextmanager
from datetime import datetime
from typing import Generator

from sqlalchemy import create_engine, Column, String, DateTime, Text, Boolean, Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


class ProjectRow(Base):
    __tablename__ = "advisor_projects"
    project_id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    object_state = Column(String, nullable=False, default="draft")
    object_version = Column(String, nullable=False, default="0.1.0")
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class ProjectContextRow(Base):
    __tablename__ = "advisor_project_contexts"
    project_id = Column(String, primary_key=True)
    raw_description = Column(Text, nullable=False)
    structured_data = Column(Text, nullable=False, default="{}")
    evidence_status = Column(String, nullable=False, default="none")


class AdvisorActionDraftRow(Base):
    __tablename__ = "advisor_action_drafts"
    draft_id = Column(String, primary_key=True)
    project_id = Column(String, nullable=False)
    trace_id = Column(String, nullable=False)
    actor = Column(String, nullable=False)
    action = Column(String, nullable=False)
    payload = Column(Text, nullable=False, default="{}")
    object_state = Column(String, nullable=False, default="draft")
    created_at = Column(DateTime, nullable=False)


class ProjectBasePatchRow(Base):
    __tablename__ = "advisor_project_base_patches"
    patch_id = Column(String, primary_key=True)
    project_id = Column(String, nullable=False)
    draft_id = Column(String, nullable=False)
    content = Column(Text, nullable=False, default="{}")
    object_state = Column(String, nullable=False, default="draft")
    created_at = Column(DateTime, nullable=False)


class SyncExecutionTicketRow(Base):
    __tablename__ = "advisor_sync_execution_tickets"
    ticket_id = Column(String, primary_key=True)
    trace_id = Column(String, nullable=False)
    draft_id = Column(String, nullable=False)
    actor = Column(String, nullable=False)
    action = Column(String, nullable=False)
    object_id = Column(String, nullable=False)
    object_version = Column(String, nullable=False)
    execution_state = Column(String, nullable=False, default="pending")
    created_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=True)


class AuditLogRow(Base):
    __tablename__ = "advisor_audit_log"
    log_id = Column(String, primary_key=True)
    trace_id = Column(String, nullable=False)
    ticket_id = Column(String, nullable=False)
    actor = Column(String, nullable=False)
    action = Column(String, nullable=False)
    object_id = Column(String, nullable=False)
    object_version_before = Column(String, nullable=False)
    object_version_after = Column(String, nullable=False)
    result = Column(String, nullable=False)
    detail = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, nullable=False)


class QuickNoteRow(Base):
    __tablename__ = "quick_notes"
    quicknote_id = Column(String, primary_key=True)
    raw_text = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False)
    source = Column(String, nullable=False, default="web")
    status = Column(String, nullable=False, default="raw")
    original_preserved = Column(Boolean, nullable=False, default=True)


def init_db(url: str = "sqlite:///advisor_objects.db") -> Engine:
    if url == "sqlite:///:memory:":
        from sqlalchemy.pool import StaticPool
        engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        engine = create_engine(url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return engine


@contextmanager
def get_session(engine: Engine) -> Generator[Session, None, None]:
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
