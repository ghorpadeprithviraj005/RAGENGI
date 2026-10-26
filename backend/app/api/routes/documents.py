"""
Document routes â€” Modules 1, 2, and 3.

Module 1: /documents/extract  â€” native PDF text extraction only.
Module 2: /documents/process  â€” native text + OCR fallback (full pipeline).
Module 3: /documents/chunk    â€” full pipeline output split into page-aware chunks.

File upload and storage (storage/uploads/, the SQLite `documents` table) belong
to a later module. These endpoints take a file path so each service can be
exercised and tested end-to-end today.
"""

import logging

from fastapi import APIRouter, HTTPException, status

from app.core.config import settings
from app.ingestion.chunker import ChunkerValueError, PDFChunker
from app.ingestion.ocr_service import OCREngineNotAvailableError, OCRService
from app.ingestion.pdf_extractor import (
    PDFCorruptedError,
    PDFEmptyError,
    PDFExtractor,
    PDFNotFoundError,
)
from app.ingestion.pipeline import DocumentIngestionPipeline
from app.schemas.chunk import ChunkingRequest, ChunkingResult
from app.schemas.ocr import DocumentExtractionResult
from app.schemas.pdf import PDFExtractionRequest, PDFExtractionResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

# Single reused instances -- none of these classes hold per-request state, so
# sharing them across requests avoids repeated construction (and, for
# DocumentIngestionPipeline, avoids reloading OCR configuration per call).
_extractor = PDFExtractor()
_pipeline = DocumentIngestionPipeline(ocr_service=OCRService(dpi=settings.OCR_DPI, language=settings.OCR_LANGUAGE))
_chunker = PDFChunker()


# ---------------------------------------------------------------------------
# Module 1 â€” native text extraction
# ---------------------------------------------------------------------------

@router.post(
    "/extract",
    response_model=PDFExtractionResult,
    status_code=status.HTTP_200_OK,
    summary="Extract native text from a PDF, page by page",
)
def extract_pdf_text(request: PDFExtractionRequest) -> PDFExtractionResult:
    """
    Run the PDF Extraction Service (Module 1) against a PDF on disk.

    Returns structured, page-wise extracted text. Each page also reports
    `has_native_text`, which the OCR Service uses to decide which pages need OCR.
    This endpoint does not perform OCR, chunking, embedding, or retrieval.
    """
    try:
        return _extractor.extract(request.file_path)
    except PDFNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PDFEmptyError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except PDFCorruptedError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error during PDF extraction: %s", request)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="An unexpected error occurred while extracting the PDF.") from exc


# ---------------------------------------------------------------------------
# Module 2 â€” native text + OCR fallback
# ---------------------------------------------------------------------------

@router.post(
    "/process",
    response_model=DocumentExtractionResult,
    status_code=status.HTTP_200_OK,
    summary="Extract text from a PDF, falling back to OCR on pages with no native text",
)
def process_document(request: PDFExtractionRequest) -> DocumentExtractionResult:
    """
    Run the full Module 1 + Module 2 pipeline (DocumentIngestionPipeline).

    For each page: native text is used if present; otherwise the page is
    rasterized and passed through Tesseract OCR. Every page in the response
    carries a `source` field ("native_text" or "ocr").
    """
    try:
        return _pipeline.process(request.file_path)
    except PDFNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PDFEmptyError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except PDFCorruptedError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except OCREngineNotAvailableError as exc:
        logger.error("OCR engine unavailable: %s", exc)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error during document processing: %s", request)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="An unexpected error occurred while processing the PDF.") from exc


# ---------------------------------------------------------------------------
# Module 3 â€” chunking
# ---------------------------------------------------------------------------

@router.post(
    "/chunk",
    response_model=ChunkingResult,
    status_code=status.HTTP_200_OK,
    summary="Extract text from a PDF and split it into page-aware chunks",
)
def chunk_document(request: ChunkingRequest) -> ChunkingResult:
    """
    Run the full Module 1 + Module 2 extraction pipeline, then split the
    resulting page-wise text into overlapping, page-aware chunks.

    Supports optional dynamic overrides for chunk_size and chunk_overlap.
    If not provided, configuration defaults are used.
    """
    try:
        extraction_result = _pipeline.process(request.file_path)
        return _chunker.chunk_document(
            extraction_result,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
        )
    except PDFNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PDFEmptyError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except PDFCorruptedError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except OCREngineNotAvailableError as exc:
        logger.error("OCR engine unavailable: %s", exc)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except ChunkerValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error during document chunking: %s", request)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="An unexpected error occurred while chunking the PDF.") from exc

