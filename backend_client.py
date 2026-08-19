"""
Module: backend_client.py
Purpose: Thin HTTP client wrapping the FastAPI backend (backend/) pipeline
         endpoints, so app.py never imports src/ directly.
"""
import os
from typing import Any, Dict, List, Optional

import pandas as pd
import requests

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

_NUMERIC_COLUMNS = ["Doin (mV)", "No.peak", "DOmin (mV)", "DDO (mV)", "phase_confidence"]


class BackendError(Exception):
    """Raised when the backend is unreachable or returns a non-2xx response."""


def _request(method: str, path: str, **kwargs) -> requests.Response:
    try:
        resp = requests.request(method, f"{BACKEND_URL}{path}", timeout=60, **kwargs)
    except requests.ConnectionError as e:
        raise BackendError(
            f"Backend không khả dụng tại {BACKEND_URL}. "
            f"Hãy chạy `uvicorn backend.main:app` trước khi dùng ứng dụng."
        ) from e
    except requests.RequestException as e:
        raise BackendError(f"Lỗi kết nối backend: {e}") from e

    if not resp.ok:
        detail = resp.text
        try:
            detail = resp.json().get("detail", detail)
        except ValueError:
            pass
        raise BackendError(f"Backend lỗi ({resp.status_code}): {detail}")
    return resp


def records_to_df(records: List[Dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    for col in _NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def create_session() -> str:
    resp = _request("POST", "/session")
    return resp.json()["session_id"]


def upload(session_id: str, filename: str, file_bytes: bytes) -> Dict[str, Any]:
    resp = _request(
        "POST", f"/session/{session_id}/upload",
        files={"file": (filename, file_bytes, "text/plain")},
    )
    return resp.json()


def extract_peaks(session_id: str) -> List[Dict[str, Any]]:
    resp = _request("POST", f"/session/{session_id}/peaks")
    return resp.json()


def classify(session_id: str) -> Dict[str, Any]:
    resp = _request("POST", f"/session/{session_id}/classify")
    return resp.json()


def detect_phase(session_id: str) -> List[Dict[str, Any]]:
    resp = _request("POST", f"/session/{session_id}/phase")
    return resp.json()


def toxicity(session_id: str) -> Dict[str, Any]:
    resp = _request("POST", f"/session/{session_id}/toxicity")
    return resp.json()


def bod_calibration(session_id: str, bod1: float, ddo1: float,
                     bod2: float, ddo2: float) -> Dict[str, Any]:
    resp = _request(
        "POST", f"/session/{session_id}/bod",
        json={"bod1": bod1, "ddo1": ddo1, "bod2": bod2, "ddo2": ddo2},
    )
    return resp.json()


def export_report(session_id: str) -> bytes:
    resp = _request("GET", f"/session/{session_id}/export")
    return resp.content
