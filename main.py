"""
FastAPI application entrypoint.

For Module 1, this wires up only the `documents` router (PDF extraction) and
a health check. Later modules will add their own routers here (query, models,
settings) following the same `app.include_router(...)` pattern -- this file
should stay a thin composition root and not accumulate business logic.
"""

from fastapi import FastAPI

from app.api.routes import documents
from app.core.config import settings
from app.core.logging import configure_logging

configure_logging()

app = FastAPI(
    title=settings.APP_NAME,
    description="Offline CPU-only RAG Engineering Assistant - API",
    version="0.1.0",
)

app.include_router(documents.router, prefix=settings.API_V1_PREFIX)


@app.get(f"{settings.API_V1_PREFIX}/health", tags=["system"])
def health_check() -> dict:
    """Basic liveness check. Extended in later modules to report model load status."""
    return {"status": "ok", "service": settings.APP_NAME}
