# backend/schemas.py
"""Pydantic request/response models for the pipeline API."""
from typing import List, Optional

from pydantic import BaseModel


class SessionCreateResponse(BaseModel):
    session_id: str


class UploadResponse(BaseModel):
    sample_name: str
    signal_points: int
    do_min: float
    do_max: float
    do_array: List[float]


class ClassifyResponse(BaseModel):
    cls_pred: str
    cls_prob: float


class ToxicityResponse(BaseModel):
    tox_val: Optional[float]
    stage1: Optional[str]
    stage2: Optional[str]
    s1_ddo: Optional[float]
    s2_ddo: Optional[float]


class BodCalibrationRequest(BaseModel):
    bod1: float
    ddo1: float
    bod2: float
    ddo2: float


class BodResponse(BaseModel):
    a: float
    b: float
    bod_phase1: float
    bod_phase2: float
