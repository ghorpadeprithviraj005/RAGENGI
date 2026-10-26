"""
API-level tests for POST /api/v1/documents/process (Module 2).

Kept in a separate file from tests/test_documents_api.py (Module 1's API
tests) so Module 1's test file is never touched while building Module 2.
"""

import fitz
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _render_text_to_png_bytes(text: str, width: int = 600, height: int = 150) -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=width, height=height)
    page.insert_text((20, height * 0.6), text, fontsize=28)
    pixmap = page.get_pixmap(matrix=fitz.Matrix(3, 3))
    png_bytes = pixmap.tobytes("png")
    doc.close()
    return png_bytes


def _make_mixed_pdf(tmp_path, filename: str = "mixed_api.pdf"):
    """2-page PDF: page 1 native text, page 2 image-only (no text layer)."""
    doc = fitz.open()

    native_page = doc.new_page(width=600, height=150)
    native_page.insert_text((20, 90), "Native API page content", fontsize=16)

    scanned_page = doc.new_page(width=600, height=150)
    png_bytes = _render_text_to_png_bytes("SCANNED API CONTENT")
    scanned_page.insert_image(scanned_page.rect, stream=png_bytes)

    path = tmp_path / filename
    doc.save(path)
    doc.close()
    return path


def test_process_endpoint_merges_native_and_ocr_text(tmp_path):
    pdf_path = _make_mixed_pdf(tmp_path)

    response = client.post("/api/v1/documents/process", json={"file_path": str(pdf_path)})

    assert response.status_code == 200
    body = response.json()
    assert body["page_count"] == 2
    assert body["ocr_pages_count"] == 1

    page_one, page_two = body["pages"]
    assert page_one["source"] == "native_text"
    assert "Native API page content" in page_one["text"]
    assert page_two["source"] == "ocr"
    assert "SCANNED" in page_two["text"].upper()


def test_process_endpoint_missing_file_returns_404():
    response = client.post(
        "/api/v1/documents/process", json={"file_path": "/no/such/file.pdf"}
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_process_endpoint_corrupted_pdf_returns_422(tmp_path):
    bad_path = tmp_path / "corrupted.pdf"
    bad_path.write_bytes(b"not a real pdf")

    response = client.post("/api/v1/documents/process", json={"file_path": str(bad_path)})

    assert response.status_code == 422


def test_process_endpoint_empty_pdf_returns_422(tmp_path):
    pdf_bytes = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"
        b"trailer\n<< /Size 3 /Root 1 0 R >>\n%%EOF\n"
    )
    empty_path = tmp_path / "empty.pdf"
    empty_path.write_bytes(pdf_bytes)

    response = client.post("/api/v1/documents/process", json={"file_path": str(empty_path)})

    assert response.status_code == 422


def test_process_endpoint_rejects_missing_field():
    response = client.post("/api/v1/documents/process", json={})

    assert response.status_code == 422
