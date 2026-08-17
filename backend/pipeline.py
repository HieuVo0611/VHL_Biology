# backend/pipeline.py
"""Router: one endpoint per analysis pipeline stage, wrapping src/ functions."""
import os
import tempfile
from typing import Any, Dict

import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.schemas import SessionCreateResponse, UploadResponse
from backend.session_store import store

router = APIRouter()


def require_session(session_id: str) -> Dict[str, Any]:
    try:
        return store.get(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found or expired")


@router.post("/session", response_model=SessionCreateResponse)
def create_session():
    session_id = store.create()
    return SessionCreateResponse(session_id=session_id)


@router.get("/session/{session_id}/export")
def export_placeholder(session_id: str):
    require_session(session_id)
    raise HTTPException(status_code=409, detail="Nothing to export yet")


def _parse_signal(file_bytes: bytes):
    tmp = tempfile.NamedTemporaryFile(suffix=".txt", delete=False)
    tmp.write(file_bytes)
    tmp.close()
    try:
        try:
            raw = pd.read_csv(tmp.name, sep="\t", header=None, usecols=[0, 1],
                               names=["Time", "DO"], encoding="utf-16")
        except UnicodeError:
            rows = []
            with open(tmp.name) as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        try:
                            rows.append((float(parts[0].replace("\x00", "")),
                                         float(parts[1].replace("\x00", ""))))
                        except ValueError:
                            pass
            raw = pd.DataFrame(rows, columns=["Time", "DO"])
        do = raw["DO"].values
        return do, len(raw), float(do.min()), float(do.max())
    finally:
        os.unlink(tmp.name)


@router.post("/session/{session_id}/upload", response_model=UploadResponse)
async def upload_file(session_id: str, file: UploadFile = File(...)):
    session = require_session(session_id)
    file_bytes = await file.read()
    sample_name = (file.filename or "sample").replace(".txt", "").strip()
    do_array, points, do_min, do_max = _parse_signal(file_bytes)

    session.update(
        file_bytes=file_bytes,
        sample_name=sample_name,
        do_array=do_array,
        do_min=do_min,
        do_max=do_max,
        signal_points=points,
        peaks_df=None,
        cls_pred=None,
        cls_prob=None,
    )
    return UploadResponse(
        sample_name=sample_name,
        signal_points=points,
        do_min=do_min,
        do_max=do_max,
        do_array=do_array.tolist(),
    )
