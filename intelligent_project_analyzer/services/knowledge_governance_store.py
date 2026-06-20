"""PostgreSQL-ready storage for governed knowledge facts.

The store is intentionally small: it creates durable fact tables and exposes a
repository API that can be tested with SQLite while remaining compatible with
PostgreSQL deployments.
"""

from __future__ import annotations

import json
import os
import yaml
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    create_engine,
    func,
    select,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker


Base = declarative_base()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _dumps(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False, sort_keys=True)


def _loads(value: Optional[str], fallback: Any = None) -> Any:
    if not value:
        return fallback if fallback is not None else {}
    return json.loads(value)


class KnowledgeAssetDraftRecord(Base):
    __tablename__ = "knowledge_asset_drafts"
    __table_args__ = (
        Index("idx_knowledge_draft_tenant_workspace_status", "tenant_id", "workspace_id", "review_status"),
        Index("idx_knowledge_draft_user_created", "user_id", "created_at"),
    )

    draft_id = Column(String(120), primary_key=True)
    tenant_id = Column(String(120), primary_key=True, nullable=False, index=True)
    workspace_id = Column(String(120), primary_key=True, nullable=False, index=True)
    user_id = Column(String(120), nullable=False, index=True)
    owner_type = Column(String(40), nullable=False, default="user")
    owner_id = Column(String(120), nullable=False)
    visibility = Column(String(40), nullable=False, default="private")
    review_status = Column(String(40), nullable=False, default="pending", index=True)
    version = Column(Integer, nullable=False, default=1)
    payload_json = Column(Text, nullable=False)
    source_ref_json = Column(Text, nullable=False)
    created_by = Column(String(120), nullable=False)
    created_at = Column(DateTime, nullable=False, default=_utcnow)
    updated_at = Column(DateTime, nullable=False, default=_utcnow)


class BlueprintFragmentDraftRecord(Base):
    __tablename__ = "blueprint_fragment_drafts"
    __table_args__ = (
        Index("idx_blueprint_fragment_draft_tenant_workspace_status", "tenant_id", "workspace_id", "review_status"),
        Index("idx_blueprint_fragment_draft_user_created", "user_id", "created_at"),
    )

    draft_id = Column(String(120), primary_key=True)
    tenant_id = Column(String(120), primary_key=True, nullable=False, index=True)
    workspace_id = Column(String(120), primary_key=True, nullable=False, index=True)
    user_id = Column(String(120), nullable=False, index=True)
    review_status = Column(String(40), nullable=False, default="pending", index=True)
    version = Column(Integer, nullable=False, default=1)
    payload_json = Column(Text, nullable=False)
    source_ref_json = Column(Text, nullable=False)
    created_by = Column(String(120), nullable=False)
    created_at = Column(DateTime, nullable=False, default=_utcnow)
    updated_at = Column(DateTime, nullable=False, default=_utcnow)


class ApprovedKnowledgeCardRecord(Base):
    __tablename__ = "approved_knowledge_cards"
    __table_args__ = (
        Index("idx_approved_card_tenant_workspace", "tenant_id", "workspace_id"),
        Index("idx_approved_card_owner_visibility", "owner_type", "owner_id", "visibility"),
        Index("idx_approved_card_status_version", "review_status", "version"),
    )

    card_id = Column(String(160), primary_key=True)
    tenant_id = Column(String(120), primary_key=True, nullable=False, index=True)
    workspace_id = Column(String(120), primary_key=True, nullable=False, index=True)
    user_id = Column(String(120), nullable=False, index=True)
    owner_type = Column(String(40), nullable=False, default="system")
    owner_id = Column(String(120), nullable=False, default="public")
    visibility = Column(String(40), nullable=False, default="public")
    review_status = Column(String(40), nullable=False, default="approved", index=True)
    version = Column(Integer, nullable=False, default=1)
    package_ids_json = Column(Text, nullable=False, default="[]")
    ontology_dimension_ids_json = Column(Text, nullable=False, default="[]")
    allowed_use_json = Column(Text, nullable=False, default="[]")
    not_allowed_use_json = Column(Text, nullable=False, default="[]")
    evidence_level = Column(String(80), nullable=True)
    payload_json = Column(Text, nullable=False)
    reviewed_by = Column(String(120), nullable=False)
    reviewed_at = Column(DateTime, nullable=False, default=_utcnow)
    created_at = Column(DateTime, nullable=False, default=_utcnow)
    updated_at = Column(DateTime, nullable=False, default=_utcnow)


class ApprovedKnowledgeCardVersionRecord(Base):
    __tablename__ = "approved_knowledge_card_versions"
    __table_args__ = (
        Index("idx_approved_card_version_scope", "tenant_id", "workspace_id", "card_id"),
        Index("idx_approved_card_version_number", "card_id", "version"),
    )

    card_id = Column(String(160), primary_key=True)
    version = Column(Integer, primary_key=True)
    tenant_id = Column(String(120), primary_key=True, nullable=False, index=True)
    workspace_id = Column(String(120), primary_key=True, nullable=False, index=True)
    user_id = Column(String(120), nullable=False, index=True)
    owner_type = Column(String(40), nullable=False)
    owner_id = Column(String(120), nullable=False)
    visibility = Column(String(40), nullable=False)
    review_status = Column(String(40), nullable=False)
    package_ids_json = Column(Text, nullable=False, default="[]")
    ontology_dimension_ids_json = Column(Text, nullable=False, default="[]")
    allowed_use_json = Column(Text, nullable=False, default="[]")
    not_allowed_use_json = Column(Text, nullable=False, default="[]")
    evidence_level = Column(String(80), nullable=True)
    payload_json = Column(Text, nullable=False)
    reviewed_by = Column(String(120), nullable=False)
    created_at = Column(DateTime, nullable=False, default=_utcnow)


class GovernanceReviewItemRecord(Base):
    __tablename__ = "governance_review_items"
    __table_args__ = (
        Index("idx_review_queue_tenant_workspace_status", "tenant_id", "workspace_id", "review_status"),
        Index("idx_review_queue_module_object", "module", "object_id"),
    )

    id = Column(String(220), primary_key=True)
    tenant_id = Column(String(120), primary_key=True, nullable=False, index=True)
    workspace_id = Column(String(120), primary_key=True, nullable=False, index=True)
    user_id = Column(String(120), nullable=False, index=True)
    module = Column(String(80), nullable=False)
    object_type = Column(String(80), nullable=False)
    object_id = Column(String(160), nullable=False)
    title = Column(String(300), nullable=False)
    review_status = Column(String(40), nullable=False, default="pending", index=True)
    source = Column(String(120), nullable=False)
    risk = Column(String(20), nullable=False, default="P1")
    target_admin_path = Column(String(220), nullable=False)
    metadata_json = Column(Text, nullable=False, default="{}")
    version = Column(Integer, nullable=False, default=1)
    created_by = Column(String(120), nullable=False)
    created_at = Column(DateTime, nullable=False, default=_utcnow)
    updated_at = Column(DateTime, nullable=False, default=_utcnow)


class LearningCandidateRecord(Base):
    __tablename__ = "learning_candidates"
    __table_args__ = (
        Index("idx_learning_candidate_tenant_workspace_status", "tenant_id", "workspace_id", "review_status"),
        Index("idx_learning_candidate_source_session", "source_session_id"),
    )

    candidate_id = Column(String(160), primary_key=True)
    tenant_id = Column(String(120), primary_key=True, nullable=False, index=True)
    workspace_id = Column(String(120), primary_key=True, nullable=False, index=True)
    user_id = Column(String(120), nullable=False, index=True)
    review_status = Column(String(40), nullable=False, default="pending", index=True)
    source_session_id = Column(String(160), nullable=True, index=True)
    payload_json = Column(Text, nullable=False)
    version = Column(Integer, nullable=False, default=1)
    created_by = Column(String(120), nullable=False)
    created_at = Column(DateTime, nullable=False, default=_utcnow)
    updated_at = Column(DateTime, nullable=False, default=_utcnow)


class AuditEventRecord(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("idx_audit_tenant_action", "tenant_id", "action"),
        Index("idx_audit_object", "object_type", "object_id"),
    )

    event_id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(120), nullable=False, index=True)
    workspace_id = Column(String(120), nullable=False, index=True)
    user_id = Column(String(120), nullable=False, index=True)
    action = Column(String(120), nullable=False)
    object_type = Column(String(120), nullable=False)
    object_id = Column(String(180), nullable=False)
    payload_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, nullable=False, default=_utcnow)


class KnowledgeGovernanceStore:
    """Repository for governed knowledge facts and review queues."""

    def __init__(self, database_url: Optional[str] = None, engine: Optional[Engine] = None) -> None:
        resolved_url = (
            database_url
            or os.getenv("KNOWLEDGE_GOVERNANCE_DATABASE_URL")
            or os.getenv("DATABASE_URL")
            or "postgresql://postgres:password@localhost:5432/project_analyzer"
        )
        self._engine_options = self._build_engine_options(resolved_url)
        self.engine = engine or create_engine(resolved_url, **self._engine_options)
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)

    @staticmethod
    def _build_engine_options(database_url: str) -> Dict[str, Any]:
        options: Dict[str, Any] = {"pool_pre_ping": True}
        if database_url.startswith(("postgresql://", "postgresql+")):
            options.update(
                {
                    "pool_size": int(os.getenv("KNOWLEDGE_GOVERNANCE_POOL_SIZE", "10")),
                    "max_overflow": int(os.getenv("KNOWLEDGE_GOVERNANCE_MAX_OVERFLOW", "20")),
                    "pool_timeout": int(os.getenv("KNOWLEDGE_GOVERNANCE_POOL_TIMEOUT", "30")),
                    "pool_recycle": int(os.getenv("KNOWLEDGE_GOVERNANCE_POOL_RECYCLE", "3600")),
                }
            )
        return options

    def create_all(self) -> None:
        Base.metadata.create_all(self.engine)

    def create_asset_draft(
        self,
        *,
        draft_id: str,
        tenant_id: str,
        workspace_id: str,
        user_id: str,
        payload: Dict[str, Any],
        source_ref: Dict[str, Any],
        created_by: str,
        owner_type: str = "user",
        owner_id: Optional[str] = None,
        visibility: str = "private",
    ) -> Dict[str, Any]:
        owner_id = owner_id or user_id
        with self._session() as session:
            record = KnowledgeAssetDraftRecord(
                draft_id=draft_id,
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                user_id=user_id,
                owner_type=owner_type,
                owner_id=owner_id,
                visibility=visibility,
                review_status="pending",
                payload_json=_dumps(payload),
                source_ref_json=_dumps(source_ref),
                created_by=created_by,
            )
            session.merge(record)
            self._enqueue_review_item(
                session,
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                user_id=user_id,
                module="knowledge_asset",
                object_type="asset_draft",
                object_id=draft_id,
                title=str(payload.get("title") or draft_id),
                source="knowledge_asset_draft",
                risk="P0",
                target_admin_path="/admin/knowledge-base",
                metadata={"source_ref": source_ref},
                created_by=created_by,
            )
            self._append_audit(
                session,
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                user_id=user_id,
                action="create_asset_draft",
                object_type="knowledge_asset_draft",
                object_id=draft_id,
                payload={"review_status": "pending"},
            )
        return {"draft_id": draft_id, "review_status": "pending"}

    def create_learning_candidate(
        self,
        *,
        candidate_id: str,
        tenant_id: str,
        workspace_id: str,
        user_id: str,
        payload: Dict[str, Any],
        source_session_id: Optional[str],
        created_by: str,
    ) -> Dict[str, Any]:
        with self._session() as session:
            session.merge(
                LearningCandidateRecord(
                    candidate_id=candidate_id,
                    tenant_id=tenant_id,
                    workspace_id=workspace_id,
                    user_id=user_id,
                    review_status="pending",
                    source_session_id=source_session_id,
                    payload_json=_dumps(payload),
                    created_by=created_by,
                )
            )
            self._enqueue_review_item(
                session,
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                user_id=user_id,
                module="learning_candidate",
                object_type="model_inferred_candidate",
                object_id=candidate_id,
                title=str(payload.get("title") or payload.get("suggested_type") or candidate_id),
                source="runtime_learning",
                risk="P0",
                target_admin_path="/admin/review-queue",
                metadata={"source_session_id": source_session_id, "payload": payload},
                created_by=created_by,
            )
            self._append_audit(
                session,
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                user_id=user_id,
                action="create_learning_candidate",
                object_type="learning_candidate",
                object_id=candidate_id,
                payload={"source_session_id": source_session_id},
            )
        return {"candidate_id": candidate_id, "review_status": "pending"}

    def publish_approved_card(
        self,
        *,
        card_id: str,
        tenant_id: str,
        workspace_id: str,
        user_id: str,
        payload: Dict[str, Any],
        owner_type: str,
        owner_id: str,
        visibility: str,
        reviewer_id: str,
    ) -> Dict[str, Any]:
        payload = dict(payload)
        payload["card_id"] = card_id
        payload["status"] = "approved"
        package_ids = [str(item) for item in payload.get("package_ids") or [] if item]
        dimension_ids = [str(item) for item in payload.get("ontology_dimension_ids") or [] if item]
        with self._session() as session:
            existing = (
                session.execute(
                    select(ApprovedKnowledgeCardRecord)
                    .where(
                        ApprovedKnowledgeCardRecord.card_id == card_id,
                        ApprovedKnowledgeCardRecord.tenant_id == tenant_id,
                        ApprovedKnowledgeCardRecord.workspace_id == workspace_id,
                    )
                    .with_for_update()
                )
                .scalars()
                .first()
            )
            version = (existing.version if existing else 0) + 1
            now = _utcnow()
            record = ApprovedKnowledgeCardRecord(
                card_id=card_id,
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                user_id=user_id,
                owner_type=owner_type,
                owner_id=owner_id,
                visibility=visibility,
                review_status="approved",
                version=version,
                package_ids_json=_dumps(package_ids),
                ontology_dimension_ids_json=_dumps(dimension_ids),
                allowed_use_json=_dumps(payload.get("allowed_use") or []),
                not_allowed_use_json=_dumps(payload.get("not_allowed_use") or []),
                evidence_level=payload.get("evidence_level"),
                payload_json=_dumps(payload),
                reviewed_by=reviewer_id,
                created_at=existing.created_at if existing else now,
                updated_at=now,
            )
            session.merge(record)
            self._append_approved_card_version(session, record)
            self._append_audit(
                session,
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                user_id=user_id,
                action="publish_approved_card",
                object_type="approved_knowledge_card",
                object_id=card_id,
                payload={"owner_type": owner_type, "visibility": visibility, "version": version},
            )
        return {"card_id": card_id, "review_status": "approved", "version": version}

    def list_approved_card_versions(
        self,
        *,
        card_id: str,
        tenant_id: str,
        workspace_id: str,
    ) -> List[Dict[str, Any]]:
        with self.SessionLocal() as session:
            records = (
                session.execute(
                    select(ApprovedKnowledgeCardVersionRecord)
                    .where(
                        ApprovedKnowledgeCardVersionRecord.card_id == card_id,
                        ApprovedKnowledgeCardVersionRecord.tenant_id == tenant_id,
                        ApprovedKnowledgeCardVersionRecord.workspace_id == workspace_id,
                    )
                    .order_by(ApprovedKnowledgeCardVersionRecord.version)
                )
                .scalars()
                .all()
            )
            return [self._approved_card_version_to_dict(record) for record in records]

    def rollback_approved_card(
        self,
        *,
        card_id: str,
        tenant_id: str,
        workspace_id: str,
        target_version: int,
        reviewer_id: str,
    ) -> Dict[str, Any]:
        with self._session() as session:
            current = (
                session.execute(
                    select(ApprovedKnowledgeCardRecord)
                    .where(
                        ApprovedKnowledgeCardRecord.card_id == card_id,
                        ApprovedKnowledgeCardRecord.tenant_id == tenant_id,
                        ApprovedKnowledgeCardRecord.workspace_id == workspace_id,
                    )
                    .with_for_update()
                )
                .scalars()
                .first()
            )
            target = session.get(
                ApprovedKnowledgeCardVersionRecord,
                {
                    "card_id": card_id,
                    "version": target_version,
                    "tenant_id": tenant_id,
                    "workspace_id": workspace_id,
                },
            )
            if not current or not target:
                raise KeyError(card_id)
            new_version = (current.version or 0) + 1
            now = _utcnow()
            payload = dict(_loads(target.payload_json))
            payload["card_id"] = card_id
            payload["status"] = "approved"

            current.user_id = target.user_id
            current.owner_type = target.owner_type
            current.owner_id = target.owner_id
            current.visibility = target.visibility
            current.review_status = "approved"
            current.version = new_version
            current.package_ids_json = target.package_ids_json
            current.ontology_dimension_ids_json = target.ontology_dimension_ids_json
            current.allowed_use_json = target.allowed_use_json
            current.not_allowed_use_json = target.not_allowed_use_json
            current.evidence_level = target.evidence_level
            current.payload_json = _dumps(payload)
            current.reviewed_by = reviewer_id
            current.updated_at = now
            self._append_approved_card_version(session, current)
            self._append_audit(
                session,
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                user_id=current.user_id,
                action="rollback_approved_card",
                object_type="approved_knowledge_card",
                object_id=card_id,
                payload={"target_version": target_version, "new_version": new_version, "reviewer_id": reviewer_id},
            )
        return {"card_id": card_id, "review_status": "approved", "version": new_version}

    def deprecate_approved_card(
        self,
        *,
        card_id: str,
        tenant_id: str,
        workspace_id: str,
        reviewer_id: str,
        reason: str,
    ) -> Dict[str, Any]:
        with self._session() as session:
            record = (
                session.execute(
                    select(ApprovedKnowledgeCardRecord)
                    .where(
                        ApprovedKnowledgeCardRecord.card_id == card_id,
                        ApprovedKnowledgeCardRecord.tenant_id == tenant_id,
                        ApprovedKnowledgeCardRecord.workspace_id == workspace_id,
                    )
                    .with_for_update()
                )
                .scalars()
                .first()
            )
            if not record:
                raise KeyError(card_id)
            record.review_status = "deprecated"
            record.reviewed_by = reviewer_id
            record.updated_at = _utcnow()
            self._append_audit(
                session,
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                user_id=record.user_id,
                action="deprecate_approved_card",
                object_type="approved_knowledge_card",
                object_id=card_id,
                payload={"reason": reason, "reviewer_id": reviewer_id},
            )
        return {"card_id": card_id, "review_status": "deprecated"}

    def request_approved_card_rereview(
        self,
        *,
        card_id: str,
        tenant_id: str,
        workspace_id: str,
        reviewer_id: str,
        reason: str,
    ) -> Dict[str, Any]:
        with self._session() as session:
            record = (
                session.execute(
                    select(ApprovedKnowledgeCardRecord)
                    .where(
                        ApprovedKnowledgeCardRecord.card_id == card_id,
                        ApprovedKnowledgeCardRecord.tenant_id == tenant_id,
                        ApprovedKnowledgeCardRecord.workspace_id == workspace_id,
                    )
                    .with_for_update()
                )
                .scalars()
                .first()
            )
            if not record:
                raise KeyError(card_id)
            record.review_status = "pending_review"
            record.reviewed_by = reviewer_id
            record.updated_at = _utcnow()
            payload = _loads(record.payload_json)
            self._enqueue_review_item(
                session,
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                user_id=record.user_id,
                module="approved_knowledge_card",
                object_type="approved_card_rereview",
                object_id=card_id,
                title=str(payload.get("title") or card_id),
                source="approved_card_rereview",
                risk="P0",
                target_admin_path="/admin/knowledge-base",
                metadata={"reason": reason, "version": record.version},
                created_by=reviewer_id,
            )
            self._append_audit(
                session,
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                user_id=record.user_id,
                action="request_approved_card_rereview",
                object_type="approved_knowledge_card",
                object_id=card_id,
                payload={"reason": reason, "reviewer_id": reviewer_id},
            )
        return {"card_id": card_id, "review_status": "pending_review"}

    def approve_asset_draft(
        self,
        *,
        draft_id: str,
        tenant_id: str,
        workspace_id: str,
        reviewer_id: str,
    ) -> Dict[str, Any]:
        with self._session() as session:
            draft = (
                session.execute(
                    select(KnowledgeAssetDraftRecord)
                    .where(
                        KnowledgeAssetDraftRecord.draft_id == draft_id,
                        KnowledgeAssetDraftRecord.tenant_id == tenant_id,
                        KnowledgeAssetDraftRecord.workspace_id == workspace_id,
                    )
                    .with_for_update()
                )
                .scalars()
                .first()
            )
            if not draft:
                raise KeyError(draft_id)
            existing_payload = dict(_loads(draft.payload_json))
            existing_card_id = str(existing_payload.get("card_id") or draft_id)
            if draft.review_status == "approved":
                approved_card = session.get(
                    ApprovedKnowledgeCardRecord,
                    {
                        "card_id": existing_card_id,
                        "tenant_id": tenant_id,
                        "workspace_id": workspace_id,
                    },
                )
                if approved_card and approved_card.review_status == "approved":
                    return {
                        "draft_id": draft_id,
                        "card_id": existing_card_id,
                        "review_status": "approved",
                        "idempotent": True,
                    }
            if draft.review_status != "pending":
                raise ValueError(f"asset draft is not pending: {draft_id}")

            payload = existing_payload
            card_id = existing_card_id
            payload["card_id"] = card_id
            payload["status"] = "approved"
            package_ids = [str(item) for item in payload.get("package_ids") or [] if item]
            dimension_ids = [str(item) for item in payload.get("ontology_dimension_ids") or [] if item]
            now = _utcnow()

            approved_record = ApprovedKnowledgeCardRecord(
                card_id=card_id,
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                user_id=draft.user_id,
                owner_type=draft.owner_type,
                owner_id=draft.owner_id,
                visibility=draft.visibility,
                review_status="approved",
                version=1,
                package_ids_json=_dumps(package_ids),
                ontology_dimension_ids_json=_dumps(dimension_ids),
                allowed_use_json=_dumps(payload.get("allowed_use") or []),
                not_allowed_use_json=_dumps(payload.get("not_allowed_use") or []),
                evidence_level=payload.get("evidence_level"),
                payload_json=_dumps(payload),
                reviewed_by=reviewer_id,
                created_at=now,
                updated_at=now,
            )
            session.merge(approved_record)
            self._append_approved_card_version(session, approved_record)

            draft.review_status = "approved"
            draft.version = (draft.version or 0) + 1
            draft.updated_at = now

            review_item = session.get(
                GovernanceReviewItemRecord,
                {
                    "id": f"knowledge_asset:{draft_id}",
                    "tenant_id": tenant_id,
                    "workspace_id": workspace_id,
                },
            )
            if review_item:
                review_item.review_status = "approved"
                review_item.version = (review_item.version or 0) + 1
                review_item.updated_at = now

            self._append_audit(
                session,
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                user_id=draft.user_id,
                action="approve_asset_draft",
                object_type="knowledge_asset_draft",
                object_id=draft_id,
                payload={"card_id": card_id, "reviewer_id": reviewer_id},
            )
        return {"draft_id": draft_id, "card_id": card_id, "review_status": "approved"}

    def approve_blueprint_fragment_draft(
        self,
        *,
        draft_id: str,
        tenant_id: str,
        workspace_id: str,
        reviewer_id: str,
    ) -> Dict[str, Any]:
        with self._session() as session:
            draft = (
                session.execute(
                    select(BlueprintFragmentDraftRecord)
                    .where(
                        BlueprintFragmentDraftRecord.draft_id == draft_id,
                        BlueprintFragmentDraftRecord.tenant_id == tenant_id,
                        BlueprintFragmentDraftRecord.workspace_id == workspace_id,
                    )
                    .with_for_update()
                )
                .scalars()
                .first()
            )
            if not draft:
                raise KeyError(draft_id)
            payload = dict(_loads(draft.payload_json))
            registry_patch = payload.get("registry_patch")
            if draft.review_status == "approved" and registry_patch:
                return {
                    "draft_id": draft_id,
                    "review_status": "approved",
                    "registry_patch": registry_patch,
                    "idempotent": True,
                }
            if draft.review_status != "pending":
                raise ValueError(f"blueprint fragment draft is not pending: {draft_id}")

            registry_patch = self._blueprint_fragment_registry_patch(payload)
            payload["registry_patch"] = registry_patch
            payload["status"] = "approved_for_registry_patch"
            draft.payload_json = _dumps(payload)
            draft.review_status = "approved"
            draft.version = (draft.version or 0) + 1
            draft.updated_at = _utcnow()

            review_item = session.get(
                GovernanceReviewItemRecord,
                {
                    "id": f"demand_reconstruction:{draft_id}",
                    "tenant_id": tenant_id,
                    "workspace_id": workspace_id,
                },
            )
            if review_item:
                review_item.review_status = "approved"
                review_item.version = (review_item.version or 0) + 1
                review_item.updated_at = _utcnow()

            self._append_audit(
                session,
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                user_id=draft.user_id,
                action="approve_blueprint_fragment_draft",
                object_type="blueprint_fragment_draft",
                object_id=draft_id,
                payload={"reviewer_id": reviewer_id, "registry_patch": registry_patch},
            )
        return {"draft_id": draft_id, "review_status": "approved", "registry_patch": registry_patch}

    def get_blueprint_fragment_registry_patch(
        self,
        *,
        draft_id: str,
        tenant_id: str,
        workspace_id: str,
    ) -> Dict[str, Any]:
        with self.SessionLocal() as session:
            draft = (
                session.execute(
                    select(BlueprintFragmentDraftRecord).where(
                        BlueprintFragmentDraftRecord.draft_id == draft_id,
                        BlueprintFragmentDraftRecord.tenant_id == tenant_id,
                        BlueprintFragmentDraftRecord.workspace_id == workspace_id,
                    )
                )
                .scalars()
                .first()
            )
            if not draft:
                raise KeyError(draft_id)
            payload = dict(_loads(draft.payload_json))
            registry_patch = payload.get("registry_patch")
            if draft.review_status != "approved" or not registry_patch:
                raise ValueError(f"blueprint fragment draft has no approved registry patch: {draft_id}")
            return {
                "draft_id": draft_id,
                "review_status": draft.review_status,
                "registry_patch": registry_patch,
                "registry_patch_yaml": yaml.safe_dump(
                    registry_patch,
                    allow_unicode=True,
                    sort_keys=False,
                ),
            }

    def apply_blueprint_fragment_registry_patch(
        self,
        *,
        draft_id: str,
        tenant_id: str,
        workspace_id: str,
        reviewer_id: str,
        registry_path: Optional[Any] = None,
    ) -> Dict[str, Any]:
        with self._session() as session:
            draft = (
                session.execute(
                    select(BlueprintFragmentDraftRecord)
                    .where(
                        BlueprintFragmentDraftRecord.draft_id == draft_id,
                        BlueprintFragmentDraftRecord.tenant_id == tenant_id,
                        BlueprintFragmentDraftRecord.workspace_id == workspace_id,
                    )
                    .with_for_update()
                )
                .scalars()
                .first()
            )
            if not draft:
                raise KeyError(draft_id)

            payload = dict(_loads(draft.payload_json))
            registry_patch = dict(payload.get("registry_patch") or {})
            if draft.review_status != "approved" or not registry_patch:
                raise ValueError(f"blueprint fragment draft has no approved registry patch: {draft_id}")

            fragment = dict(registry_patch.get("fragment") or {})
            fragment_id = str(fragment.get("fragment_id") or "").strip()
            if not fragment_id:
                raise ValueError(f"blueprint fragment registry patch has no fragment_id: {draft_id}")

            resolved_registry_path = Path(
                registry_path
                or registry_patch.get("registry_file")
                or "intelligent_project_analyzer/config/registries/demand_reconstruction_blueprints.yaml"
            )
            if not resolved_registry_path.is_absolute():
                resolved_registry_path = Path.cwd() / resolved_registry_path
            resolved_registry_path.parent.mkdir(parents=True, exist_ok=True)

            if resolved_registry_path.exists():
                registry_data = yaml.safe_load(resolved_registry_path.read_text(encoding="utf-8")) or {}
            else:
                registry_data = {}
            if not isinstance(registry_data, dict):
                raise ValueError(f"blueprint registry file must contain a mapping: {resolved_registry_path}")

            root_key = str(registry_patch.get("target_root") or "demand_reconstruction_blueprint_fragments")
            root = registry_data.setdefault(root_key, {})
            if not isinstance(root, dict):
                raise ValueError(f"blueprint registry root must contain a mapping: {root_key}")
            governed_candidates = root.setdefault("governed_candidates", {})
            if not isinstance(governed_candidates, dict):
                raise ValueError("governed_candidates must contain a mapping")

            governed_candidates[fragment_id] = fragment
            resolved_registry_path.write_text(
                yaml.safe_dump(registry_data, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )

            applied_patch = dict(registry_patch)
            applied_patch["operation"] = "applied"
            applied_patch["applied_to"] = str(resolved_registry_path)
            applied_patch["applied_by"] = reviewer_id
            applied_patch["applied_at"] = _utcnow().isoformat()
            payload["registry_patch"] = applied_patch
            payload["status"] = "applied_to_registry"
            draft.payload_json = _dumps(payload)
            draft.version = (draft.version or 0) + 1
            draft.updated_at = _utcnow()

            self._append_audit(
                session,
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                user_id=draft.user_id,
                action="apply_blueprint_fragment_registry_patch",
                object_type="blueprint_fragment_draft",
                object_id=draft_id,
                payload={"reviewer_id": reviewer_id, "registry_patch": applied_patch},
            )

        return {"draft_id": draft_id, "review_status": "approved", "registry_patch": applied_patch}


    @staticmethod
    def _blueprint_fragment_registry_patch(payload: Dict[str, Any]) -> Dict[str, Any]:
        fragment_id = str(payload.get("fragment_id") or "untitled_fragment").strip()
        project_object = str(payload.get("project_object") or "未覆盖空间项目").strip()
        evidence = list(payload.get("evidence") or [])
        return {
            "registry_file": "intelligent_project_analyzer/config/registries/demand_reconstruction_blueprints.yaml",
            "target_root": "demand_reconstruction_blueprint_fragments",
            "operation": "manual_merge_required",
            "fragment": {
                "fragment_id": fragment_id,
                "project_object": project_object,
                "task_reframe": f"先把“{project_object}”的成立条件、使用者与关键约束讲清楚，再判断是否需要沉淀为稳定需求重构蓝图片段。",
                "primary_risk": "当前仅来自治理审核候选，必须经人工补全 sections/key_forks/unknowns 后才能进入稳定 registry。",
                "evidence": evidence,
                "source_summary": payload.get("summary"),
            },
        }

    def get_database_health(
        self,
        *,
        tenant_id: str,
        workspace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        table_models = {
            "knowledge_asset_drafts": KnowledgeAssetDraftRecord,
            "blueprint_fragment_drafts": BlueprintFragmentDraftRecord,
            "approved_knowledge_cards": ApprovedKnowledgeCardRecord,
            "approved_knowledge_card_versions": ApprovedKnowledgeCardVersionRecord,
            "governance_review_items": GovernanceReviewItemRecord,
            "learning_candidates": LearningCandidateRecord,
            "audit_events": AuditEventRecord,
        }
        table_counts: Dict[str, int] = {}
        with self.SessionLocal() as session:
            for table_name, model in table_models.items():
                stmt = select(func.count()).select_from(model).where(model.tenant_id == tenant_id)
                if workspace_id:
                    stmt = stmt.where(model.workspace_id == workspace_id)
                table_counts[table_name] = int(session.execute(stmt).scalar_one())

        pool = getattr(self.engine, "pool", None)
        pool_status = None
        if pool is not None and hasattr(pool, "status"):
            try:
                pool_status = pool.status()
            except Exception:
                pool_status = None

        return {
            "schema_version": "knowledge_governance_database_health.v1",
            "status": "healthy",
            "backend": self.engine.dialect.name,
            "tenant_id": tenant_id,
            "workspace_id": workspace_id,
            "table_counts": table_counts,
            "connection_pool": {
                "pool_pre_ping": bool(self._engine_options.get("pool_pre_ping")),
                "pool_size": self._engine_options.get("pool_size"),
                "max_overflow": self._engine_options.get("max_overflow"),
                "pool_timeout": self._engine_options.get("pool_timeout"),
                "pool_recycle": self._engine_options.get("pool_recycle"),
                "status": pool_status,
            },
        }

    def list_review_items(
        self,
        *,
        tenant_id: str,
        workspace_id: Optional[str] = None,
        review_status: str = "pending",
    ) -> List[Dict[str, Any]]:
        with self.SessionLocal() as session:
            stmt = select(GovernanceReviewItemRecord).where(
                GovernanceReviewItemRecord.tenant_id == tenant_id,
                GovernanceReviewItemRecord.review_status == review_status,
            )
            if workspace_id:
                stmt = stmt.where(GovernanceReviewItemRecord.workspace_id == workspace_id)
            records = session.execute(stmt.order_by(GovernanceReviewItemRecord.created_at)).scalars().all()
            return [self._review_item_to_dict(record) for record in records]

    def enqueue_review_item(
        self,
        *,
        tenant_id: str,
        workspace_id: str,
        user_id: str,
        module: str,
        object_type: str,
        object_id: str,
        title: str,
        source: str,
        risk: str,
        target_admin_path: str,
        metadata: Optional[Dict[str, Any]] = None,
        created_by: str,
    ) -> Dict[str, Any]:
        with self._session() as session:
            record = self._enqueue_review_item(
                session,
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                user_id=user_id,
                module=module,
                object_type=object_type,
                object_id=object_id,
                title=title,
                source=source,
                risk=risk,
                target_admin_path=target_admin_path,
                metadata=metadata or {},
                created_by=created_by,
            )
            session.flush()
            self._append_audit(
                session,
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                user_id=user_id,
                action="enqueue_governance_review_item",
                object_type=object_type,
                object_id=object_id,
                payload={"module": module, "source": source, "risk": risk},
            )
            return self._review_item_to_dict(record)

    def update_review_item_status(
        self,
        *,
        tenant_id: str,
        workspace_id: str,
        item_id: str,
        review_status: str,
        reviewer_id: str,
        note: Optional[str] = None,
    ) -> Dict[str, Any]:
        allowed_statuses = {"pending", "approved", "rejected", "ignored"}
        if review_status not in allowed_statuses:
            raise ValueError(f"unsupported review_status: {review_status}")
        with self._session() as session:
            record = session.get(
                GovernanceReviewItemRecord,
                {
                    "id": item_id,
                    "tenant_id": tenant_id,
                    "workspace_id": workspace_id,
                },
            )
            if record is None:
                raise KeyError(item_id)
            metadata = _loads(record.metadata_json)
            if note:
                metadata["reviewer_note"] = note
            metadata["reviewed_by"] = reviewer_id
            followup = None
            if review_status == "approved":
                followup = self._governance_followup_for_approval(metadata)
                if followup and followup.get("type") == "blueprint_fragment_candidate_draft":
                    self._persist_blueprint_fragment_candidate_draft(
                        session,
                        record=record,
                        followup=followup,
                        reviewer_id=reviewer_id,
                    )
                elif followup and followup.get("type") == "knowledge_asset_candidate_draft":
                    self._persist_knowledge_asset_candidate_draft(
                        session,
                        record=record,
                        followup=followup,
                        reviewer_id=reviewer_id,
                    )
            if review_status == "approved" and followup:
                metadata["governance_followup"] = followup
            record.review_status = review_status
            record.metadata_json = _dumps(metadata)
            record.updated_at = _utcnow()
            self._append_audit(
                session,
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                user_id=reviewer_id,
                action="update_governance_review_item_status",
                object_type=record.object_type,
                object_id=record.object_id,
                payload={
                    "item_id": item_id,
                    "review_status": review_status,
                    "note": note,
                    "governance_followup": followup,
                },
            )
            return self._review_item_to_dict(record)

    @staticmethod
    def _governance_followup_for_approval(metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        code = str(metadata.get("code") or "").strip()
        signal = metadata.get("signal") if isinstance(metadata.get("signal"), dict) else {}
        if code == "new_fragment_candidate":
            fragment_id = str(signal.get("fragment_id") or "").strip()
            project_object = str(signal.get("project_object") or "").strip()
            if not fragment_id and not project_object:
                return None
            return {
                "type": "blueprint_fragment_candidate_draft",
                "status": "draft",
                "next_admin_action": "review_blueprint_fragment_draft",
                "draft": {
                    "fragment_id": fragment_id,
                    "project_object": project_object,
                    "summary": signal.get("summary"),
                    "source": signal.get("source") or metadata.get("source") or "governance_review",
                    "evidence": list(signal.get("evidence") or []),
                    "scan_result": signal.get("scan_result"),
                },
            }
        if code == "knowledge_gap_ticket":
            project_type = str(signal.get("project_type") or "").strip()
            gap_type = str(signal.get("gap_type") or "").strip()
            if not project_type and not gap_type:
                return None
            return {
                "type": "knowledge_asset_candidate_draft",
                "status": "draft",
                "next_admin_action": "review_knowledge_asset_draft",
                "draft": {
                    "project_type": project_type,
                    "gap_type": gap_type,
                    "summary": signal.get("summary"),
                    "source": signal.get("source") or metadata.get("source") or "governance_review",
                    "evidence": list(signal.get("evidence") or []),
                    "scan_result": signal.get("scan_result"),
                    "matched_targets": list(signal.get("matched_targets") or []),
                    "package_ids": list(signal.get("package_ids") or []),
                    "ontology_dimension_ids": list(signal.get("ontology_dimension_ids") or []),
                },
            }
        return None

    def _persist_blueprint_fragment_candidate_draft(
        self,
        session: Session,
        *,
        record: GovernanceReviewItemRecord,
        followup: Dict[str, Any],
        reviewer_id: str,
    ) -> None:
        draft = followup.get("draft") if isinstance(followup.get("draft"), dict) else {}
        fragment_id = str(draft.get("fragment_id") or "untitled_fragment").strip()
        project_object = str(draft.get("project_object") or "未覆盖空间项目").strip()
        draft_id = f"blueprint_fragment_{uuid.uuid5(uuid.NAMESPACE_URL, record.id).hex[:12]}"
        payload = {
            "fragment_id": fragment_id,
            "project_object": project_object,
            "summary": draft.get("summary"),
            "evidence": list(draft.get("evidence") or []),
            "scan_result": draft.get("scan_result"),
            "status": "candidate",
            "allowed_use": ["仅作为人工复核前的需求重构蓝图片段候选，不可直接进入运行时规则检索。"],
            "not_allowed_use": ["不得在未审核并迁入 registry 前作为稳定规则蓝图片段使用。"],
        }
        source_ref = {
            "source": "demand_reconstruction_governance_review",
            "review_item_id": record.id,
            "review_queue": _loads(record.metadata_json).get("review_queue"),
            "reviewed_by": reviewer_id,
        }
        session.merge(
            BlueprintFragmentDraftRecord(
                draft_id=draft_id,
                tenant_id=record.tenant_id,
                workspace_id=record.workspace_id,
                user_id=record.user_id,
                review_status="pending",
                payload_json=_dumps(payload),
                source_ref_json=_dumps(source_ref),
                created_by=reviewer_id,
            )
        )
        self._enqueue_review_item(
            session,
            tenant_id=record.tenant_id,
            workspace_id=record.workspace_id,
            user_id=record.user_id,
            module="demand_reconstruction",
            object_type="blueprint_fragment_draft",
            object_id=draft_id,
            title=f"{project_object} 蓝图片段候选",
            source="demand_reconstruction_governance_review",
            risk="P1",
            target_admin_path="/admin/review-queue?queue=blueprint_fragment_review",
            metadata={"source_ref": source_ref, "governance_followup": followup},
            created_by=reviewer_id,
        )
        self._append_audit(
            session,
            tenant_id=record.tenant_id,
            workspace_id=record.workspace_id,
            user_id=record.user_id,
            action="create_blueprint_fragment_draft_from_governance_followup",
            object_type="blueprint_fragment_draft",
            object_id=draft_id,
            payload={"review_item_id": record.id, "fragment_id": fragment_id},
        )
        followup["blueprint_fragment_draft_id"] = draft_id

    def _persist_knowledge_asset_candidate_draft(
        self,
        session: Session,
        *,
        record: GovernanceReviewItemRecord,
        followup: Dict[str, Any],
        reviewer_id: str,
    ) -> None:
        draft = followup.get("draft") if isinstance(followup.get("draft"), dict) else {}
        project_type = str(draft.get("project_type") or "未覆盖空间类型").strip()
        draft_id = f"demand_gap_{uuid.uuid5(uuid.NAMESPACE_URL, record.id).hex[:12]}"
        payload = {
            "title": f"{project_type} 知识缺口候选",
            "knowledge_status": "candidate",
            "source_gap_type": draft.get("gap_type"),
            "project_type": project_type,
            "summary": draft.get("summary"),
            "evidence": list(draft.get("evidence") or []),
            "matched_targets": list(draft.get("matched_targets") or []),
            "package_ids": list(draft.get("package_ids") or []),
            "ontology_dimension_ids": list(draft.get("ontology_dimension_ids") or []),
            "allowed_use": ["仅作为人工复核前的候选知识资产，不可直接进入运行时召回。"],
            "not_allowed_use": ["不得在未审核通过前作为专科知识结论或规则蓝图片段使用。"],
            "evidence_level": "governance_signal",
        }
        source_ref = {
            "source": "demand_reconstruction_governance_review",
            "review_item_id": record.id,
            "review_queue": _loads(record.metadata_json).get("review_queue"),
            "reviewed_by": reviewer_id,
        }
        session.merge(
            KnowledgeAssetDraftRecord(
                draft_id=draft_id,
                tenant_id=record.tenant_id,
                workspace_id=record.workspace_id,
                user_id=record.user_id,
                owner_type="user",
                owner_id=record.user_id,
                visibility="private",
                review_status="pending",
                payload_json=_dumps(payload),
                source_ref_json=_dumps(source_ref),
                created_by=reviewer_id,
            )
        )
        self._enqueue_review_item(
            session,
            tenant_id=record.tenant_id,
            workspace_id=record.workspace_id,
            user_id=record.user_id,
            module="knowledge_asset",
            object_type="asset_draft",
            object_id=draft_id,
            title=payload["title"],
            source="demand_reconstruction_governance_review",
            risk="P1",
            target_admin_path="/admin/knowledge-base",
            metadata={"source_ref": source_ref, "governance_followup": followup},
            created_by=reviewer_id,
        )
        self._append_audit(
            session,
            tenant_id=record.tenant_id,
            workspace_id=record.workspace_id,
            user_id=record.user_id,
            action="create_asset_draft_from_governance_followup",
            object_type="knowledge_asset_draft",
            object_id=draft_id,
            payload={"review_item_id": record.id, "project_type": project_type},
        )
        followup["asset_draft_id"] = draft_id

    def list_audit_events(
        self,
        *,
        tenant_id: str,
        workspace_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        with self.SessionLocal() as session:
            stmt = select(AuditEventRecord).where(AuditEventRecord.tenant_id == tenant_id)
            if workspace_id:
                stmt = stmt.where(AuditEventRecord.workspace_id == workspace_id)
            stmt = stmt.order_by(AuditEventRecord.event_id)
            if limit:
                stmt = stmt.limit(limit)
            records = (
                session.execute(stmt)
                .scalars()
                .all()
            )
            return [
                {
                    "event_id": record.event_id,
                    "tenant_id": record.tenant_id,
                    "workspace_id": record.workspace_id,
                    "user_id": record.user_id,
                    "action": record.action,
                    "object_type": record.object_type,
                    "object_id": record.object_id,
                    "payload": _loads(record.payload_json),
                    "created_at": record.created_at.isoformat(),
                }
                for record in records
            ]

    def find_approved_cards(
        self,
        *,
        tenant_id: str,
        workspace_id: str,
        user_id: str,
        package_ids: Optional[Iterable[str]] = None,
        ontology_dimension_ids: Optional[Iterable[str]] = None,
    ) -> List[Dict[str, Any]]:
        package_filter = {str(item) for item in package_ids or [] if item}
        dimension_filter = {str(item) for item in ontology_dimension_ids or [] if item}
        with self.SessionLocal() as session:
            records = (
                session.execute(
                    select(ApprovedKnowledgeCardRecord).where(
                        ApprovedKnowledgeCardRecord.tenant_id == tenant_id,
                        ApprovedKnowledgeCardRecord.workspace_id == workspace_id,
                        ApprovedKnowledgeCardRecord.review_status == "approved",
                    )
                )
                .scalars()
                .all()
            )

        cards = []
        for record in records:
            if not self._is_visible(record, user_id):
                continue
            record_package_ids = set(_loads(record.package_ids_json, []))
            record_dimension_ids = set(_loads(record.ontology_dimension_ids_json, []))
            if package_filter and not (package_filter & record_package_ids):
                continue
            if dimension_filter and not (dimension_filter & record_dimension_ids):
                continue
            cards.append(self._approved_card_to_dict(record))
        return sorted(cards, key=lambda item: item.get("card_id") or "")

    def get_approved_card(
        self,
        *,
        card_id: str,
        tenant_id: str,
        workspace_id: str,
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        with self.SessionLocal() as session:
            record = session.get(
                ApprovedKnowledgeCardRecord,
                {
                    "card_id": card_id,
                    "tenant_id": tenant_id,
                    "workspace_id": workspace_id,
                },
            )
            if (
                not record
                or record.review_status != "approved"
                or not self._is_visible(record, user_id)
            ):
                return None
            return self._approved_card_to_dict(record)

    @contextmanager
    def _session(self) -> Iterator[Session]:
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _enqueue_review_item(self, session: Session, **kwargs: Any) -> GovernanceReviewItemRecord:
        review_id = f"{kwargs['module']}:{kwargs['object_id']}"
        return session.merge(
            GovernanceReviewItemRecord(
                id=review_id,
                tenant_id=kwargs["tenant_id"],
                workspace_id=kwargs["workspace_id"],
                user_id=kwargs["user_id"],
                module=kwargs["module"],
                object_type=kwargs["object_type"],
                object_id=kwargs["object_id"],
                title=kwargs["title"],
                review_status="pending",
                source=kwargs["source"],
                risk=kwargs["risk"],
                target_admin_path=kwargs["target_admin_path"],
                metadata_json=_dumps(kwargs.get("metadata") or {}),
                created_by=kwargs["created_by"],
            )
        )

    def _append_audit(self, session: Session, **kwargs: Any) -> None:
        session.add(
            AuditEventRecord(
                tenant_id=kwargs["tenant_id"],
                workspace_id=kwargs["workspace_id"],
                user_id=kwargs["user_id"],
                action=kwargs["action"],
                object_type=kwargs["object_type"],
                object_id=kwargs["object_id"],
                payload_json=_dumps(kwargs.get("payload") or {}),
            )
        )

    def _append_approved_card_version(
        self,
        session: Session,
        record: ApprovedKnowledgeCardRecord,
    ) -> None:
        session.merge(
            ApprovedKnowledgeCardVersionRecord(
                card_id=record.card_id,
                version=record.version,
                tenant_id=record.tenant_id,
                workspace_id=record.workspace_id,
                user_id=record.user_id,
                owner_type=record.owner_type,
                owner_id=record.owner_id,
                visibility=record.visibility,
                review_status=record.review_status,
                package_ids_json=record.package_ids_json,
                ontology_dimension_ids_json=record.ontology_dimension_ids_json,
                allowed_use_json=record.allowed_use_json,
                not_allowed_use_json=record.not_allowed_use_json,
                evidence_level=record.evidence_level,
                payload_json=record.payload_json,
                reviewed_by=record.reviewed_by,
            )
        )

    @staticmethod
    def _is_visible(record: ApprovedKnowledgeCardRecord, user_id: str) -> bool:
        if record.owner_type == "system":
            return True
        if record.visibility in {"public", "workspace"}:
            return True
        return record.owner_type == "user" and record.owner_id == user_id

    @staticmethod
    def _approved_card_to_dict(record: ApprovedKnowledgeCardRecord) -> Dict[str, Any]:
        payload = _loads(record.payload_json)
        payload["card_id"] = record.card_id
        payload["status"] = "approved"
        payload["package_ids"] = _loads(record.package_ids_json, [])
        payload["ontology_dimension_ids"] = _loads(record.ontology_dimension_ids_json, [])
        payload["allowed_use"] = _loads(record.allowed_use_json, [])
        payload["not_allowed_use"] = _loads(record.not_allowed_use_json, [])
        return payload

    @staticmethod
    def _approved_card_version_to_dict(record: ApprovedKnowledgeCardVersionRecord) -> Dict[str, Any]:
        payload = _loads(record.payload_json)
        payload["card_id"] = record.card_id
        payload["status"] = record.review_status
        payload["package_ids"] = _loads(record.package_ids_json, [])
        payload["ontology_dimension_ids"] = _loads(record.ontology_dimension_ids_json, [])
        payload["allowed_use"] = _loads(record.allowed_use_json, [])
        payload["not_allowed_use"] = _loads(record.not_allowed_use_json, [])
        return {
            "card_id": record.card_id,
            "version": record.version,
            "tenant_id": record.tenant_id,
            "workspace_id": record.workspace_id,
            "review_status": record.review_status,
            "payload": payload,
            "reviewed_by": record.reviewed_by,
            "created_at": record.created_at.isoformat(),
        }

    @staticmethod
    def _review_item_to_dict(record: GovernanceReviewItemRecord) -> Dict[str, Any]:
        return {
            "id": record.id,
            "module": record.module,
            "object_type": record.object_type,
            "object_id": record.object_id,
            "title": record.title,
            "review_status": record.review_status,
            "source": record.source,
            "risk": record.risk,
            "target_admin_path": record.target_admin_path,
            "metadata": _loads(record.metadata_json),
            "reviewer_note": _loads(record.metadata_json).get("reviewer_note"),
            "tenant_id": record.tenant_id,
            "workspace_id": record.workspace_id,
            "user_id": record.user_id,
            "version": record.version,
        }


class DbBackedKnowledgeAssetRegistry:
    """Adapter compatible with runtime approved-card lookup."""

    def __init__(
        self,
        store: KnowledgeGovernanceStore,
        *,
        tenant_id: str,
        workspace_id: str,
        user_id: str,
    ) -> None:
        self.store = store
        self.tenant_id = tenant_id
        self.workspace_id = workspace_id
        self.user_id = user_id

    def load_index(self) -> Dict[str, Any]:
        cards = self.find_cards()
        package_index: Dict[str, List[str]] = {}
        dimension_index: Dict[str, List[str]] = {}
        card_index: Dict[str, Dict[str, Any]] = {}
        for card in cards:
            card_id = str(card.get("card_id"))
            card_index[card_id] = {
                "title": card.get("title"),
                "status": "approved",
                "evidence_level": card.get("evidence_level"),
                "knowledge_status": card.get("knowledge_status"),
                "package_ids": card.get("package_ids") or [],
                "ontology_dimension_ids": card.get("ontology_dimension_ids") or [],
            }
            for package_id in card.get("package_ids") or []:
                package_index.setdefault(str(package_id), []).append(card_id)
            for dimension_id in card.get("ontology_dimension_ids") or []:
                dimension_index.setdefault(str(dimension_id), []).append(card_id)
        return {"cards": card_index, "package_index": package_index, "dimension_index": dimension_index}

    def get_card(self, card_id: str) -> Optional[Dict[str, Any]]:
        return self.store.get_approved_card(
            card_id=card_id,
            tenant_id=self.tenant_id,
            workspace_id=self.workspace_id,
            user_id=self.user_id,
        )

    def find_cards(
        self,
        package_ids: Optional[Iterable[str]] = None,
        ontology_dimension_ids: Optional[Iterable[str]] = None,
    ) -> List[Dict[str, Any]]:
        return self.store.find_approved_cards(
            tenant_id=self.tenant_id,
            workspace_id=self.workspace_id,
            user_id=self.user_id,
            package_ids=package_ids,
            ontology_dimension_ids=ontology_dimension_ids,
        )
