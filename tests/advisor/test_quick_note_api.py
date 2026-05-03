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


from fastapi import FastAPI
from fastapi.testclient import TestClient
from intelligent_project_analyzer.api.quick_note_routes import router

api_app = FastAPI()
api_app.include_router(router)
client = TestClient(api_app)


def test_create_quick_note_returns_201():
    response = client.post("/v1/quick-notes", json={"raw_text": "测试速记内容"})
    assert response.status_code == 201
    data = response.json()
    assert "quicknote_id" in data
    assert data["status"] == "raw"
    assert "created_at" in data


def test_create_quick_note_empty_text_returns_400():
    response = client.post("/v1/quick-notes", json={"raw_text": "   "})
    assert response.status_code == 400


def test_create_quick_note_missing_text_returns_422():
    response = client.post("/v1/quick-notes", json={})
    assert response.status_code == 422


def test_list_quick_notes_returns_200():
    response = client.get("/v1/quick-notes")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert isinstance(data["items"], list)


def test_list_quick_notes_includes_just_created():
    client.post("/v1/quick-notes", json={"raw_text": "列表测试内容"})
    response = client.get("/v1/quick-notes?hours=24&limit=20")
    texts = [item["raw_text"] for item in response.json()["items"]]
    assert "列表测试内容" in texts
