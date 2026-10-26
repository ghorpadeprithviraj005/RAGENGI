"""
Document routes.

Module 1 added a single endpoint that runs the PDF Extraction Service against
a file already present on disk. Module 2 adds a second endpoint,
`/documents/process`, that runs the full native-text + OCR pipeline via
`DocumentIngestionPipeline`. Both endpoints take a file path rather than an
uploaded file -- file upload and storage (storage/uploads/, the SQLite
`documents` table) belong to a later module.
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
_pipeline = DocumentIngestionPipeline(
    pdf_extractor=_extractor,
    ocr_service=OCRService(dpi=settings.OCR_DPI, language=settings.OCR_LANGUAGE),
)
_chunker = PDFChunker()


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
    `has_native_text`, which future modules (OCR Service) will use to decide
    which pages need OCR. This endpoint does not perform OCR, chunking,
    embedding, or retrieval.
    """
    try:
        return _extractor.extract(request.file_path)
    except PDFNotFoundError as exc:
        logger.warning("Extraction request failed - file not found: %s", exc)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PDFEmptyError as exc:
        logger.warning("Extraction request failed - empty PDF: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except PDFCorruptedError as exc:
        logger.warning("Extraction request failed - corrupted PDF: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except Exception as exc:  # noqa: BLE001 - last-resort safety net, never leak raw tracebacks
        logger.exception("Unexpected error during PDF extraction for request: %s", request)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while extracting the PDF.",
        ) from exc


@router.post(
    "/process",
    response_model=DocumentExtractionResult,
    status_code=status.HTTP_200_OK,
    summary="Extract text from a PDF, falling back to OCR on pages with no native text",
)
def process_document(request: PDFExtractionRequest) -> DocumentExtractionResult:
    """
    Run the full Module 1 + Module 2 pipeline (DocumentIngestionPipeline)
    against a PDF on disk.

    For each page: native text is used if present; otherwise the page is
    rasterized and passed through Tesseract OCR. Every page in the response
    carries a `source` field ("native_text" or "ocr") so downstream
    consumers (and, eventually, citation display) know exactly how each
    page's text was obtained. This endpoint does not perform chunking,
    embedding, or retrieval.
    """
    try:
        return _pipeline.process(request.file_path)
    except PDFNotFoundError as exc:
        logger.warning("Processing request failed - file not found: %s", exc)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PDFEmptyError as exc:
        logger.warning("Processing request failed - empty PDF: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except PDFCorruptedError as exc:
        logger.warning("Processing request failed - corrupted PDF: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except OCREngineNotAvailableError as exc:
        # This is an environment/deployment problem (Tesseract missing), not a
        # bad request -- 503 tells the client "try again once the server is
        # correctly configured", not "fix your input".
        logger.error("Processing request failed - OCR engine unavailable: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except Exception as exc:  # noqa: BLE001 - last-resort safety net, never leak raw tracebacks
        logger.exception("Unexpected error during document processing for request: %s", request)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing the PDF.",
        ) from exc


@router.post(
    "/chunk",
    response_model=ChunkingResult,
    status_code=status.HTTP_200_OK,
    summary="Extract text from a PDF and split it into page-aware chunks",
)
def chunk_document(request: ChunkingRequest) -> ChunkingResult:
    """
    Run the full Module 1 + Module 2 extraction pipeline (DocumentIngestionPipeline),
    then split the resulting page-wise text into overlapping, page-aware chunks.

    Supports optional dynamic overrides for chunk_size and chunk_overlap in
    the request body. If not provided, configuration defaults are used.
    """
    try:
        extraction_result = _pipeline.process(request.file_path)
        return _chunker.chunk_document(
            extraction_result,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
        )
    except PDFNotFoundError as exc:
        logger.warning("Chunking request failed - file not found: %s", exc)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PDFEmptyError as exc:
        logger.warning("Chunking request failed - empty PDF: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except PDFCorruptedError as exc:
        logger.warning("Chunking request failed - corrupted PDF: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except OCREngineNotAvailableError as exc:
        logger.error("Chunking request failed - OCR engine unavailable: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except ChunkerValueError as exc:
        logger.warning("Chunking request failed - invalid parameters: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error during document chunking for request: %s", request)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while chunking the PDF.",
        ) from exc
