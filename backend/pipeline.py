# backend/pipeline.py
"""Router: one endpoint per analysis pipeline stage, wrapping src/ functions."""
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from backend.schemas import SessionCreateResponse
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
