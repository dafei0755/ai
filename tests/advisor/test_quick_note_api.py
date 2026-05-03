import pytest
from sqlalchemy import create_engine, inspect
from intelligent_project_analyzer.advisor.database import Base


def test_quick_note_table_exists_in_metadata():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    assert "quick_notes" in inspector.get_table_names()


def test_quick_note_table_has_required_columns():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("quick_notes")}
    assert "quicknote_id" in columns
    assert "raw_text" in columns
    assert "created_at" in columns
    assert "source" in columns
    assert "status" in columns
    assert "original_preserved" in columns
