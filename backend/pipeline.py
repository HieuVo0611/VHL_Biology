# backend/pipeline.py
"""Router: one endpoint per analysis pipeline stage, wrapping src/ functions."""
import os
import tempfile
from typing import Any, Dict

import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.schemas import ClassifyResponse, SessionCreateResponse, UploadResponse
from backend.session_store import store
from src.phase_detector import update_phase_tags
from src.utils import catboost_inference_from_csv, extract_peaks_from_txt

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


@router.post("/session/{session_id}/peaks")
def extract_peaks(session_id: str):
    session = require_session(session_id)
    if "file_bytes" not in session:
        raise HTTPException(status_code=409, detail="Upload a file before extracting peaks")

    tmp = tempfile.NamedTemporaryFile(suffix=".txt", delete=False)
    tmp.write(session["file_bytes"])
    tmp.close()
    try:
        peaks_df = extract_peaks_from_txt(tmp.name)
        for col in ("Doin (mV)", "No.peak", "DOmin (mV)", "DDO (mV)"):
            peaks_df[col] = pd.to_numeric(peaks_df[col], errors="coerce")
    finally:
        os.unlink(tmp.name)

    session["peaks_df"] = peaks_df
    return peaks_df.where(pd.notnull(peaks_df), None).to_dict(orient="records")


@router.post("/session/{session_id}/classify", response_model=ClassifyResponse)
def classify(session_id: str):
    session = require_session(session_id)
    if session.get("peaks_df") is None:
        raise HTTPException(status_code=409, detail="Extract peaks before classifying")

    results = catboost_inference_from_csv(
        session["peaks_df"],
        model_path="model/catboost_model.cbm",
        label_encoder_path="model/label_encoder_classes.npy",
    )
    _, pred, prob = results[0]
    session["cls_pred"] = str(pred)
    session["cls_prob"] = float(prob.max())
    return ClassifyResponse(cls_pred=session["cls_pred"], cls_prob=session["cls_prob"])


@router.post("/session/{session_id}/phase")
def detect_phase(session_id: str):
    session = require_session(session_id)
    if session.get("peaks_df") is None:
        raise HTTPException(status_code=409, detail="Extract peaks before phase detection")
    if session.get("cls_pred") is None:
        raise HTTPException(status_code=409, detail="Classify before phase detection")

    peaks_df = update_phase_tags(session["peaks_df"], session["cls_pred"])
    session["peaks_df"] = peaks_df
    return peaks_df.where(pd.notnull(peaks_df), None).to_dict(orient="records")
