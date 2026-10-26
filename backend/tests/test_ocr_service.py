"""
Unit tests for app/ingestion/ocr_service.py.

Test PDFs containing "scanned" (image-only, no text layer) pages are built
using PyMuPDF itself, in two steps:
  1. Render a short string to a small in-memory page using fitz's built-in
     font support (Helvetica, always available -- no system font files
     required) and rasterize that page to a PNG at high zoom for crisp text.
  2. Embed that PNG as the sole content of a page in a *separate* PDF, with
     no text layer -- this is a faithful stand-in for a real scanned page.

This keeps the test suite fully offline and self-contained: no checked-in
binary fixtures, no dependency on fonts being present on the test machine.
"""

import fitz
import pytest

from app.ingestion.ocr_service import (
    OCRService,
    PageRasterizationError,
)
from app.ingestion.pdf_extractor import PDFExtractor


@pytest.fixture
def ocr_service() -> OCRService:
    return OCRService()


def _render_text_to_png_bytes(text: str, width: int = 600, height: int = 150) -> bytes:
    """Render `text` onto a blank page and rasterize it to PNG bytes at high zoom."""
    doc = fitz.open()
    page = doc.new_page(width=width, height=height)
    page.insert_text((20, height * 0.6), text, fontsize=28)
    # zoom=3 upsamples the render for cleaner OCR input, independent of OCRService's own DPI.
    pixmap = page.get_pixmap(matrix=fitz.Matrix(3, 3))
    png_bytes = pixmap.tobytes("png")
    doc.close()
    return png_bytes


def _make_scanned_pdf(tmp_path, text: str, filename: str = "scanned.pdf"):
    """Build a PDF page whose ONLY content is an embedded image (no text layer)."""
    png_bytes = _render_text_to_png_bytes(text)

    doc = fitz.open()
    page = doc.new_page(width=600, height=150)
    page.insert_image(page.rect, stream=png_bytes)
    path = tmp_path / filename
    doc.save(path)
    doc.close()
    return path


def test_scanned_pdf_has_no_native_text(tmp_path):
    """Sanity check on the test fixture itself: confirms it truly has no text layer."""
    pdf_path = _make_scanned_pdf(tmp_path, "SANITY CHECK")

    result = PDFExtractor().extract(str(pdf_path))

    assert result.pages[0].has_native_text is False
    assert result.pages[0].text == ""


def test_extract_text_from_page_recovers_ocr_text(tmp_path, ocr_service):
    pdf_path = _make_scanned_pdf(tmp_path, "HELLO OCR WORLD")

    recovered_text = ocr_service.extract_text_from_page(str(pdf_path), 1)

    assert "HELLO" in recovered_text.upper()
    assert "OCR" in recovered_text.upper()


def test_extract_text_from_page_handles_multi_page_document(tmp_path, ocr_service):
    png_1 = _render_text_to_png_bytes("PAGE ONE CONTENT")
    png_2 = _render_text_to_png_bytes("PAGE TWO CONTENT")

    doc = fitz.open()
    for png_bytes in (png_1, png_2):
        page = doc.new_page(width=600, height=150)
        page.insert_image(page.rect, stream=png_bytes)
    path = tmp_path / "multi_page_scanned.pdf"
    doc.save(path)
    doc.close()

    page_1_text = ocr_service.extract_text_from_page(str(path), 1)
    page_2_text = ocr_service.extract_text_from_page(str(path), 2)

    assert "PAGE ONE" in page_1_text.upper()
    assert "PAGE TWO" in page_2_text.upper()


def test_extract_text_from_page_out_of_range_raises(tmp_path, ocr_service):
    pdf_path = _make_scanned_pdf(tmp_path, "ONLY PAGE")

    with pytest.raises(PageRasterizationError):
        ocr_service.extract_text_from_page(str(pdf_path), 2)


def test_extract_text_from_missing_file_raises(ocr_service):
    with pytest.raises(PageRasterizationError):
        ocr_service.extract_text_from_page("/nonexistent/path/does_not_exist.pdf", 1)


def test_extract_text_from_blank_page_returns_empty_or_near_empty_string(tmp_path, ocr_service):
    doc = fitz.open()
    doc.new_page(width=600, height=150)  # truly blank, no image, no text
    path = tmp_path / "blank.pdf"
    doc.save(path)
    doc.close()

    recovered_text = ocr_service.extract_text_from_page(str(path), 1)

    assert recovered_text.strip() == ""


def test_custom_dpi_and_language_are_accepted():
    # Construction should not raise for valid custom settings; this documents
    # the constructor's contract for later modules/config wiring.
    service = OCRService(dpi=150, language="eng")
    assert service is not None
