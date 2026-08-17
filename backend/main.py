"""FastAPI app entrypoint. Run with: uvicorn backend.main:app"""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="VHL Biology API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}
