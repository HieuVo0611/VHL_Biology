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


SAMPLE_TXT = "data/GGA/File txt/N4-VS1-25-03-2024/10-5/N4-10-5-01042024-Q=49.81mL_phút-3.txt"


def _new_session() -> str:
    return client.post("/session").json()["session_id"]


def test_upload_returns_signal_stats():
    sid = _new_session()
    with open(SAMPLE_TXT, "rb") as f:
        resp = client.post(f"/session/{sid}/upload", files={"file": ("sample.txt", f, "text/plain")})
    assert resp.status_code == 200
    body = resp.json()
    assert body["signal_points"] > 0
    assert body["do_min"] <= body["do_max"]
    assert len(body["do_array"]) == body["signal_points"]


def test_upload_missing_session_returns_404():
    with open(SAMPLE_TXT, "rb") as f:
        resp = client.post("/session/does-not-exist/upload", files={"file": ("sample.txt", f, "text/plain")})
    assert resp.status_code == 404


def _session_with_upload() -> str:
    sid = _new_session()
    with open(SAMPLE_TXT, "rb") as f:
        client.post(f"/session/{sid}/upload", files={"file": ("sample.txt", f, "text/plain")})
    return sid


def test_peaks_returns_rows_with_ddo():
    sid = _session_with_upload()
    resp = client.post(f"/session/{sid}/peaks")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) > 0
    assert "DDO (mV)" in rows[0]


def test_peaks_without_upload_returns_409():
    sid = _new_session()
    resp = client.post(f"/session/{sid}/peaks")
    assert resp.status_code == 409


def _session_with_peaks() -> str:
    sid = _session_with_upload()
    client.post(f"/session/{sid}/peaks")
    return sid


def test_classify_returns_prediction():
    sid = _session_with_peaks()
    resp = client.post(f"/session/{sid}/classify")
    assert resp.status_code == 200
    body = resp.json()
    assert body["cls_pred"].lower() in ("gga", "metal")
    assert 0.0 <= body["cls_prob"] <= 1.0


def test_classify_without_peaks_returns_409():
    sid = _new_session()
    resp = client.post(f"/session/{sid}/classify")
    assert resp.status_code == 409
