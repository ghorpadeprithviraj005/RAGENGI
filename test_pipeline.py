"""
Unit tests for app/ingestion/pipeline.py.

These verify the merge behaviour that is the whole point of Module 2: pages
with native text keep it (source="native_text"), pages without it get OCR
applied (source="ocr"), and PDFExtractor's own exceptions still propagate
unchanged through the pipeline.
"""

import fitz
import pytest

from app.ingestion.pdf_extractor import PDFEmptyError, PDFNotFoundError
from app.ingestion.pipeline import DocumentIngestionPipeline


@pytest.fixture
def pipeline() -> DocumentIngestionPipeline:
    return DocumentIngestionPipeline()


def _render_text_to_png_bytes(text: str, width: int = 600, height: int = 150) -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=width, height=height)
    page.insert_text((20, height * 0.6), text, fontsize=28)
    pixmap = page.get_pixmap(matrix=fitz.Matrix(3, 3))
    png_bytes = pixmap.tobytes("png")
    doc.close()
    return png_bytes


def _make_mixed_pdf(tmp_path, filename: str = "mixed.pdf"):
    """
    Build a 2-page PDF: page 1 has real, native, selectable text; page 2 has
    no text layer at all, only an embedded image containing rendered text
    (a stand-in for a scanned page).
    """
    doc = fitz.open()

    native_page = doc.new_page(width=600, height=150)
    native_page.insert_text((20, 90), "Native text page content", fontsize=16)

    scanned_page = doc.new_page(width=600, height=150)
    png_bytes = _render_text_to_png_bytes("SCANNED PAGE CONTENT")
    scanned_page.insert_image(scanned_page.rect, stream=png_bytes)

    path = tmp_path / filename
    doc.save(path)
    doc.close()
    return path


def test_pipeline_uses_native_text_when_available(tmp_path, pipeline):
    pdf_path = _make_mixed_pdf(tmp_path)

    result = pipeline.process(str(pdf_path))

    page_one = result.pages[0]
    assert page_one.source == "native_text"
    assert "Native text page content" in page_one.text


def test_pipeline_falls_back_to_ocr_for_pages_with_no_native_text(tmp_path, pipeline):
    pdf_path = _make_mixed_pdf(tmp_path)

    result = pipeline.process(str(pdf_path))

    page_two = result.pages[1]
    assert page_two.source == "ocr"
    assert "SCANNED" in page_two.text.upper()


def test_pipeline_reports_correct_ocr_pages_count(tmp_path, pipeline):
    pdf_path = _make_mixed_pdf(tmp_path)

    result = pipeline.process(str(pdf_path))

    assert result.page_count == 2
    assert result.ocr_pages_count == 1


def test_pipeline_preserves_page_order_and_numbers(tmp_path, pipeline):
    pdf_path = _make_mixed_pdf(tmp_path)

    result = pipeline.process(str(pdf_path))

    page_numbers = [p.page_number for p in result.pages]
    assert page_numbers == [1, 2]


def test_pipeline_propagates_file_not_found(pipeline):
    with pytest.raises(PDFNotFoundError):
        pipeline.process("/nonexistent/path/does_not_exist.pdf")


def test_pipeline_propagates_empty_pdf_error(tmp_path, pipeline):
    pdf_bytes = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"
        b"trailer\n<< /Size 3 /Root 1 0 R >>\n%%EOF\n"
    )
    empty_path = tmp_path / "empty.pdf"
    empty_path.write_bytes(pdf_bytes)

    with pytest.raises(PDFEmptyError):
        pipeline.process(str(empty_path))


def test_pipeline_all_native_pages_reports_zero_ocr_pages(tmp_path, pipeline):
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page(width=600, height=150)
        page.insert_text((20, 90), f"Native page {i + 1}", fontsize=16)
    path = tmp_path / "all_native.pdf"
    doc.save(path)
    doc.close()

    result = pipeline.process(str(path))

    assert result.ocr_pages_count == 0
    assert all(p.source == "native_text" for p in result.pages)
