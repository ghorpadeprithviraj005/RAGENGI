"""
Document ingestion pipeline orchestrator (universal loader + OCR fallback).

Uses LoaderFactory to select the appropriate loader for any supported file type,
then falls back to OCR on pages lacking native text.
"""

import logging
from typing import List, Optional

from app.ingestion.ocr_service import OCRError, OCRService
from app.schemas.ocr import DocumentExtractionResult, OCRPageResult
from app.loaders.loader_factory import LoaderFactory
from app.schemas.pdf import PDFExtractionResult

logger = logging.getLogger(__name__)


class DocumentIngestionPipeline:
    """Orchestrates loader selection, native text extraction, and OCR fallback."""

    def __init__(
        self,
        ocr_service: Optional[OCRService] = None,
    ) -> None:
        self._ocr_service = ocr_service or OCRService()
        self._loader_factory = LoaderFactory()

    def process(self, file_path: str) -> DocumentExtractionResult:
        """Run format-specific extraction, then OCR any page lacking native text."""
        # 1. Select and run the appropriate loader
        loader = self._loader_factory.get_loader(file_path)
        extraction_result: PDFExtractionResult = loader.load(file_path)

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

            # No native text — run OCR fallback
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
