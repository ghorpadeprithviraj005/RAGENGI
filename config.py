"""
Application-wide configuration.

Kept deliberately minimal for Module 1 (PDF Extraction Service). Later modules
(OCR, embeddings, FAISS, LLM) will extend this Settings class with their own
config values (model paths, chunk size, top_k, etc.) rather than each module
inventing its own config mechanism.
"""

from pathlib import Path


class Settings:
    APP_NAME: str = "RAGENGI"
    API_V1_PREFIX: str = "/api/v1"
    LOG_LEVEL: str = "INFO"

    # backend/app/core/config.py -> parents[2] == backend/
    BASE_DIR: Path = Path(__file__).resolve().parents[2]

    # --- Module 2: OCR Service ---
    OCR_DPI: int = 300  # rasterization resolution; see OCRService docstring for rationale
    OCR_LANGUAGE: str = "eng"

    # --- Module 3: Chunking Service ---
    CHUNK_SIZE: int = 500  # default chunk size in characters
    CHUNK_OVERLAP: int = 50  # default overlap in characters


settings = Settings()
