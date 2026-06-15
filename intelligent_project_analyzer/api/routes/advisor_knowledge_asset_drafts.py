"""Advisor knowledge asset draft generation API routes."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from intelligent_project_analyzer.services.knowledge_asset_draft_generation import (
    generate_asset_draft_from_document,
    generate_asset_draft_from_observation,
    generate_asset_drafts_from_directory,
)
from intelligent_project_analyzer.services.knowledge_governance_store import (
    KnowledgeGovernanceStore,
)


router = APIRouter(
    prefix="/api/v1/advisor-knowledge/asset-drafts",
    tags=["方案高参知识资产草稿"],
)


class DocumentDraftRequest(BaseModel):
    source_path: str = Field(..., description="Explicit local text document path.")
    persist_to_governance_store: bool = Field(False, description="Queue the draft for governance review.")
    tenant_id: Optional[str] = Field(None, description="Tenant id for governance persistence.")
    workspace_id: Optional[str] = Field(None, description="Workspace id for governance persistence.")
    user_id: Optional[str] = Field(None, description="User id for governance persistence.")
    created_by: Optional[str] = Field(None, description="Actor id for governance persistence.")


class ObservationDraftRequest(BaseModel):
    observation_id: str = Field(..., description="Explicit observation id.")
    observation_root: str = Field(..., description="Directory containing observation folders.")


class DirectoryDraftRequest(BaseModel):
    directory_path: str = Field(..., description="Explicit directory to process at one level.")


def _translate_generation_error(exc: Exception) -> HTTPException:
    if isinstance(exc, FileNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, (ValueError, UnicodeDecodeError)):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail="Failed to generate asset draft.")


def _get_governance_store() -> KnowledgeGovernanceStore:
    store = KnowledgeGovernanceStore()
    store.create_all()
    return store


def _persist_asset_draft_if_requested(
    draft: Dict[str, Any],
    request: DocumentDraftRequest,
) -> Dict[str, Any]:
    if not request.persist_to_governance_store:
        return draft

    missing = [
        field
        for field in ("tenant_id", "workspace_id", "user_id")
        if not getattr(request, field)
    ]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"governance persistence requires: {', '.join(missing)}",
        )

    source_path = str((draft.get("source_ref") or {}).get("source_path") or request.source_path)
    digest = hashlib.sha1(source_path.encode("utf-8")).hexdigest()[:12]
    draft_id = f"asset-draft:{digest}"
    actor = request.created_by or request.user_id or "system"
    result = _get_governance_store().create_asset_draft(
        draft_id=draft_id,
        tenant_id=str(request.tenant_id),
        workspace_id=str(request.workspace_id),
        user_id=str(request.user_id),
        payload=draft.get("asset_card_candidate") or draft,
        source_ref=draft.get("source_ref") or {"source_path": source_path},
        created_by=str(actor),
    )
    return {
        **draft,
        "governance_persistence": {
            "status": "queued_for_review",
            "draft_id": result["draft_id"],
            "review_status": result["review_status"],
        },
    }


@router.post("/from-document")
def create_asset_draft_from_document(request: DocumentDraftRequest) -> Dict[str, Any]:
    try:
        draft = generate_asset_draft_from_document(Path(request.source_path))
        return _persist_asset_draft_if_requested(draft, request)
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise exc
        raise _translate_generation_error(exc) from exc


@router.post("/from-observation")
def create_asset_draft_from_observation(request: ObservationDraftRequest) -> Dict[str, Any]:
    try:
        return generate_asset_draft_from_observation(
            request.observation_id,
            observation_root=Path(request.observation_root),
        )
    except Exception as exc:
        raise _translate_generation_error(exc) from exc


@router.post("/from-directory")
def create_asset_drafts_from_directory(request: DirectoryDraftRequest) -> Dict[str, Any]:
    try:
        return generate_asset_drafts_from_directory(Path(request.directory_path))
    except Exception as exc:
        raise _translate_generation_error(exc) from exc
