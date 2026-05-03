import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc

from intelligent_project_analyzer.advisor.database import init_db, get_session, QuickNoteRow

router = APIRouter()
_engine = init_db()


class CreateQuickNoteRequest(BaseModel):
    raw_text: str
    source: str = "web"


@router.post("/v1/quick-notes", status_code=201)
async def create_quick_note(req: CreateQuickNoteRequest):
    if not req.raw_text.strip():
        raise HTTPException(status_code=400, detail="raw_text cannot be empty")
    note_id = str(uuid.uuid4())
    now = datetime.utcnow()
    row = QuickNoteRow(
        quicknote_id=note_id,
        raw_text=req.raw_text,
        created_at=now,
        source=req.source,
        status="raw",
        original_preserved=True,
    )
    with get_session(_engine) as session:
        session.add(row)
    return {"quicknote_id": note_id, "created_at": now.isoformat() + "Z", "status": "raw"}


@router.get("/v1/quick-notes")
async def list_quick_notes(hours: int = 24, limit: int = 20):
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    with get_session(_engine) as session:
        rows = (
            session.query(QuickNoteRow)
            .filter(QuickNoteRow.created_at >= cutoff)
            .order_by(desc(QuickNoteRow.created_at))
            .limit(limit)
            .all()
        )
        items = [
            {
                "quicknote_id": r.quicknote_id,
                "raw_text": r.raw_text,
                "created_at": r.created_at.isoformat() + "Z",
                "source": r.source,
                "status": r.status,
            }
            for r in rows
        ]
    return {"items": items}
