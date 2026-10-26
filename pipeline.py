"""
Document ingestion pipeline orchestrator (partial -- native text + OCR only).

Combines Module 1 (PDFExtractor) and Module 2 (OCRService): for every page,
use native text if PDFExtractor found it; otherwise fall back to OCR on a
rasterized image of that page.

This class deliberately stops there. Chunking, embedding, and vector storage
are separate, later modules per the architecture document and are NOT
implemented here -- this orchestrator's only job is to produce one final,
merged, page-wise text result per document with an accurate `source` label
on every page.
"""

import logging
from typing import List, Optional

from app.ingestion.ocr_service import OCRError, OCRService
from app.ingestion.pdf_extractor import PDFExtractor
from app.schemas.ocr import DocumentExtractionResult, OCRPageResult

logger = logging.getLogger(__name__)


class DocumentIngestionPipeline:
    """Orchestrates native text extraction (Module 1) with OCR fallback (Module 2)."""

    def __init__(
        self,
        pdf_extractor: Optional[PDFExtractor] = None,
        ocr_service: Optional[OCRService] = None,
    ) -> None:
        # Dependencies are injectable (for testing with mocks/fakes) but default
        # to real instances so callers don't have to wire this up themselves.
        self._pdf_extractor = pdf_extractor or PDFExtractor()
        self._ocr_service = ocr_service or OCRService()

    def process(self, file_path: str) -> DocumentExtractionResult:
        """
        Run native extraction, then OCR any page PDFExtractor flagged as
        having no native text.

        Propagates PDFExtractor's own exceptions (PDFNotFoundError,
        PDFCorruptedError, PDFEmptyError) unchanged -- callers already handle
        those from the Module 1 integration, and this pipeline can never
        produce a *different* answer than PDFExtractor about whether a file
        is missing/corrupted/empty, since it calls PDFExtractor first.

        An OCR failure on an individual page is logged and that page is
        returned with empty text and source="ocr" rather than aborting the
        whole document -- one unreadable scanned page should not block
        access to the rest of a multi-page engineering PDF.
        """
        extraction_result = self._pdf_extractor.extract(file_path)

        pages: List[OCRPageResult] = []
        ocr_pages_count = 0

        for page in extraction_result.pages:
            if page.has_native_text:
                pages.append(
                    OCRPageResult(
                        page_number=page.page_number,
                        text=page.text,
                        source="native_text",
                    )
                )
                continue

            ocr_pages_count += 1
            logger.info(
                "Page %d of %s has no native text - running OCR",
                page.page_number, file_path,
            )
            try:
                ocr_text = self._ocr_service.extract_text_from_page(
                    file_path, page.page_number
                )
            except OCRError as exc:
                logger.error(
                    "OCR failed for page %d of %s, returning empty text: %s",
                    page.page_number, file_path, exc,
                )
                ocr_text = ""

            pages.append(
                OCRPageResult(
                    page_number=page.page_number,
                    text=ocr_text,
                    source="ocr",
                )
            )

        logger.info(
            "Pipeline complete for %s: %d page(s) total, %d required OCR",
            file_path, extraction_result.page_count, ocr_pages_count,
        )

        return DocumentExtractionResult(
            file_path=extraction_result.file_path,
            page_count=extraction_result.page_count,
            pages=pages,
            ocr_pages_count=ocr_pages_count,
        )
