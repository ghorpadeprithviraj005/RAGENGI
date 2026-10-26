"""
OCR Service.

Module 2 of the ingestion pipeline. Responsibility (narrow, mirroring
PDFExtractor's single-purpose design from Module 1): given a PDF file path
and a specific page number, render that page to an image and run Tesseract
OCR on it to recover text from pages that have no native text layer (i.e.
scanned pages, or pages that are effectively just an embedded image).

This service does NOT decide which pages need OCR -- that decision belongs
to the ingestion pipeline (app/ingestion/pipeline.py), which uses the
`has_native_text` flag already produced by PDFExtractor (Module 1). Keeping
that decision out of this class means OCRService has exactly one job: turn a
page image into text.

Rasterization uses PyMuPDF's own `Page.get_pixmap()`, not a separate library
such as pdf2image/poppler. PyMuPDF is already a hard dependency from Module 1
and needs no extra system binary for page-to-image conversion -- pulling in
poppler-utils just for rasterization would be redundant.
"""

import io
import logging
from pathlib import Path

import fitz  # PyMuPDF
import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)


class OCRError(Exception):
    """Base class for all OCR Service errors."""


class OCREngineNotAvailableError(OCRError):
    """Raised when the Tesseract binary is not installed or not on PATH."""


class PageRasterizationError(OCRError):
    """Raised when a PDF page cannot be opened or rendered to an image."""


class OCRService:
    """Renders PDF pages to images and extracts text from them via Tesseract."""

    def __init__(self, dpi: int = 300, language: str = "eng") -> None:
        """
        Args:
            dpi: resolution used when rasterizing a page before OCR. 300 DPI
                is the standard sweet spot for OCR accuracy vs. CPU time on
                scanned technical documents -- higher rarely improves
                accuracy enough to justify the extra processing cost on a
                CPU-only system.
            language: Tesseract language code. "eng" covers the
                English-language engineering PDFs this project targets.
                Additional language packs can be installed and passed here
                later with no code change.
        """
        self._dpi = dpi
        self._language = language

    def extract_text_from_page(self, file_path: str, page_number: int) -> str:
        """
        Run OCR on a single page (1-indexed) of the given PDF.

        Raises:
            PageRasterizationError: the page could not be opened/rendered to
                an image (missing/corrupted file, out-of-range page number).
            OCREngineNotAvailableError: Tesseract is not installed / not on PATH.
            OCRError: OCR itself failed for a reason other than the above.
        """
        image = self._rasterize_page(file_path, page_number)
        return self._run_tesseract(image, page_number, file_path)

    def _rasterize_page(self, file_path: str, page_number: int) -> Image.Image:
        path = Path(file_path)
        logger.info(
            "Rasterizing page %d of %s at %d DPI for OCR", page_number, path, self._dpi
        )

        try:
            document = fitz.open(path)
        except Exception as exc:  # noqa: BLE001 - any open failure becomes our own error type
            logger.error("Failed to open PDF for rasterization: %s (%s)", path, exc)
            raise PageRasterizationError(f"Could not open PDF for OCR: {path}") from exc

        try:
            page_index = page_number - 1
            if page_index < 0 or page_index >= document.page_count:
                logger.error(
                    "Page %d out of range for %s (document has %d page(s))",
                    page_number, path, document.page_count,
                )
                raise PageRasterizationError(
                    f"Page {page_number} out of range for {path} "
                    f"(document has {document.page_count} page(s))"
                )

            page = document.load_page(page_index)
            zoom = self._dpi / 72  # PDF base resolution is defined as 72 DPI
            matrix = fitz.Matrix(zoom, zoom)
            pixmap = page.get_pixmap(matrix=matrix)

            image = Image.open(io.BytesIO(pixmap.tobytes("png")))
            image.load()  # decode fully now, while the pixmap-backed buffer is still valid
            return image
        except PageRasterizationError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to rasterize page %d of %s: %s", page_number, path, exc)
            raise PageRasterizationError(
                f"Failed to render page {page_number} of {path} to an image"
            ) from exc
        finally:
            document.close()

    def _run_tesseract(self, image: Image.Image, page_number: int, file_path: str) -> str:
        try:
            raw_text = pytesseract.image_to_string(image, lang=self._language)
        except pytesseract.TesseractNotFoundError as exc:
            logger.error("Tesseract binary not found on PATH")
            raise OCREngineNotAvailableError(
                "Tesseract is not installed or not on PATH. Install the "
                "system package (see module README) before using OCR."
            ) from exc
        except Exception as exc:  # noqa: BLE001
            logger.error("OCR failed for page %d of %s: %s", page_number, file_path, exc)
            raise OCRError(f"OCR failed for page {page_number} of {file_path}") from exc

        cleaned_text = raw_text.strip()
        logger.info(
            "OCR complete for page %d of %s: %d character(s) recovered",
            page_number, file_path, len(cleaned_text),
        )
        return cleaned_text
