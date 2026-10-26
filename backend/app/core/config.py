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

    # backend/app/core/config.py -> parents[3] == repo root
    # parents[0] = core/, parents[1] = app/, parents[2] = backend/, parents[3] = repo root
    BASE_DIR: Path = Path(__file__).resolve().parents[2]

    # --- Module 2: OCR Service ---
    OCR_DPI: int = 300  # rasterization resolution; see OCRService docstring for rationale
    OCR_LANGUAGE: str = "eng"

    # --- Module 3: Chunking Service ---
    CHUNK_SIZE: int = 800   # default chunk size in characters
    CHUNK_OVERLAP: int = 100  # default overlap in characters

    # --- Module 4: Embedding Service ---
    EMBEDDING_MODEL_PATH: str = "models/embeddings"
    EMBEDDING_DEVICE: str = "cpu"
    EMBEDDING_BATCH_SIZE: int = 32

    # --- Module 4: FAISS Vector Store ---
    FAISS_INDEX_PATH: str = "storage/faiss_index/index.faiss"
    FAISS_INDEX_TYPE: str = "IndexFlatIP"

    # --- Document Cleanup Configuration ---
    CLEANUP_API_KEY: str = "ragengi-secure-cleanup-key"
    CLEANUP_INACTIVITY_DAYS: int = 30


settings = Settings()
