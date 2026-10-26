"""
PDF Extraction Service.

Responsibility (single, narrow): given a path to a PDF file on disk, open it
with PyMuPDF and return native (non-OCR) text, page by page, as a structured
result.

This is stage 1 of the ingestion pipeline described in the architecture
document. It deliberately does NOT:
  - perform OCR on scanned pages (that is a future OCR Service module; this
    service only flags pages with no extractable text via `has_native_text`
    so the OCR Service knows which pages need it),
  - chunk text,
  - generate embeddings,
  - touch FAISS or SQLite.

Keeping this module's responsibility narrow is intentional: it is easy to
unit test in isolation, and every later module (OCR, chunking) can depend on
its output type (`PDFExtractionResult`) without depending on its internals.
"""

import logging
from pathlib import Path

import fitz  # PyMuPDF

from app.schemas.pdf import PageText, PDFExtractionResult

logger = logging.getLogger(__name__)


class PDFExtractionError(Exception):
    """Base class for all errors raised by PDFExtractor."""


class PDFNotFoundError(PDFExtractionError):
    """Raised when the given file path does not exist or is not a file."""


class PDFCorruptedError(PDFExtractionError):
    """Raised when the file cannot be opened/parsed as a valid PDF."""


class PDFEmptyError(PDFExtractionError):
    """Raised when the PDF opens successfully but contains zero pages."""


class PDFExtractor:
    """Extracts native text from a PDF file, page by page, using PyMuPDF."""

    def __init__(self, min_chars_per_page: int = 1) -> None:
        """
        Args:
            min_chars_per_page: minimum number of (stripped) characters a page
                must contain to be considered as having native text. Pages
                below this threshold are flagged `has_native_text=False`,
                which the future OCR Service will use to decide which pages
                to send through OCR.
        """
        self._min_chars_per_page = min_chars_per_page

    def extract(self, file_path: str) -> PDFExtractionResult:
        """
        Extract text from every page of the given PDF.

        Raises:
            PDFNotFoundError: file does not exist / is not a file.
            PDFCorruptedError: file exists but is not a valid, readable PDF.
            PDFEmptyError: file is a valid PDF but contains zero pages.
        """
        path = Path(file_path)
        self._validate_path(path)

        logger.info("Opening PDF for extraction: %s", path)
        document = self._open_document(path)

        try:
            page_count = document.page_count

            if page_count == 0:
                logger.warning("PDF has zero pages: %s", path)
                raise PDFEmptyError(f"PDF contains no pages: {path}")

            pages = [
                self._extract_page(document, page_index, path)
                for page_index in range(page_count)
            ]

            native_text_pages = sum(page.has_native_text for page in pages)
            logger.info(
                "Extraction complete for %s: %d page(s), %d with native text, "
                "%d likely scanned/empty (candidates for future OCR)",
                path,
                page_count,
                native_text_pages,
                page_count - native_text_pages,
            )

            return PDFExtractionResult(
                file_path=str(path),
                page_count=page_count,
                pages=pages,
            )
        finally:
            # Always release the file handle, even if extraction raised.
            document.close()

    def _extract_page(self, document: fitz.Document, page_index: int, path: Path) -> PageText:
        """Extract a single page's text. A failure on one page does not abort the document."""
        page_number = page_index + 1
        try:
            page = document.load_page(page_index)
            raw_text = page.get_text("text") or ""
        except Exception as exc:  # noqa: BLE001 - isolate a bad page, don't fail the whole PDF
            logger.error(
                "Failed to extract text from page %d of %s: %s", page_number, path, exc
            )
            raw_text = ""

        cleaned_text = raw_text.strip()
        has_native_text = len(cleaned_text) >= self._min_chars_per_page

        return PageText(
            page_number=page_number,
            text=cleaned_text,
            has_native_text=has_native_text,
        )

    def _open_document(self, path: Path) -> fitz.Document:
        try:
            return fitz.open(path)
        except fitz.FileDataError as exc:
            # PyMuPDF's specific exception for malformed/corrupted PDF structure.
            logger.error("Corrupted PDF detected: %s (%s)", path, exc)
            raise PDFCorruptedError(f"File is not a valid or readable PDF: {path}") from exc
        except Exception as exc:  # noqa: BLE001 - convert any other open failure consistently
            logger.error("Unexpected error opening PDF: %s (%s)", path, exc)
            raise PDFCorruptedError(f"Failed to open PDF: {path}") from exc

    @staticmethod
    def _validate_path(path: Path) -> None:
        if not path.exists():
            logger.error("PDF file not found: %s", path)
            raise PDFNotFoundError(f"File not found: {path}")
        if not path.is_file():
            logger.error("Path exists but is not a file: %s", path)
            raise PDFNotFoundError(f"Path is not a file: {path}")
        if path.suffix.lower() != ".pdf":
            logger.error("File does not have a .pdf extension: %s", path)
            raise PDFCorruptedError(
                f"File does not appear to be a PDF (extension check failed): {path}"
            )
