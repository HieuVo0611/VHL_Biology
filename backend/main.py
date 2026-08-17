"""FastAPI app entrypoint. Run with: uvicorn backend.main:app"""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.pipeline import router as pipeline_router

app = FastAPI(title="VHL Biology API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pipeline_router)


@app.get("/health")
def health():
    return {"status": "ok"}
