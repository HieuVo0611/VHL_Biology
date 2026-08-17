# backend/tests/test_pipeline.py
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_create_session_returns_session_id():
    resp = client.post("/session")
    assert resp.status_code == 200
    body = resp.json()
    assert "session_id" in body
    assert len(body["session_id"]) > 0


def test_unknown_session_id_returns_404():
    resp = client.get("/session/does-not-exist/export")
    assert resp.status_code == 404
