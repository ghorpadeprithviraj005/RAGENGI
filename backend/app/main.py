"""
FastAPI application entrypoint.

This file is the thin composition root for the RAGENGI backend. It wires up
routers from each module and should never accumulate business logic.

Current routers:
  - documents  (Modules 1, 2, 3): /api/v1/documents/{extract,process,chunk}

Planned additions (later modules):
  - rag        (Module 8): /api/v1/rag
  - query      (Module 4+): /api/v1/query
  - models     (Module 4+): /api/v1/models
  - settings             : /api/v1/settings

Each new module adds its own router here following the same
`app.include_router(router, prefix=settings.API_V1_PREFIX)` pattern.
"""

from fastapi import FastAPI

from app.api.routes import documents, rag
from app.core.config import settings
from app.core.logging import configure_logging

configure_logging()

app = FastAPI(
    title=settings.APP_NAME,
    description="Offline CPU-only RAG Engineering Assistant — API",
    version="0.3.0",
)

app.include_router(documents.router, prefix=settings.API_V1_PREFIX)
app.include_router(rag.router, prefix=settings.API_V1_PREFIX)


@app.get(f"{settings.API_V1_PREFIX}/health", tags=["system"])
def health_check() -> dict:
    """Basic liveness check. Extended in later modules to report model load status."""
    return {"status": "ok", "service": settings.APP_NAME}
