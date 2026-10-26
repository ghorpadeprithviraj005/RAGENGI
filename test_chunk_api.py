"""
API-level tests for POST /api/v1/documents/chunk (Module 3).
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


def _make_mixed_pdf(tmp_path, filename: str = "mixed_chunk_api.pdf"):
    """2-page PDF: page 1 native text, page 2 image-only (no text layer)."""
    doc = fitz.open()

    native_page = doc.new_page(width=600, height=150)
    native_page.insert_text((20, 90), "This is a native page with some text for chunking.", fontsize=16)

    scanned_page = doc.new_page(width=600, height=150)
    png_bytes = _render_text_to_png_bytes("SCANNED OCR TEXT CONTENT")
    scanned_page.insert_image(scanned_page.rect, stream=png_bytes)

    path = tmp_path / filename
    doc.save(path)
    doc.close()
    return path


def test_chunk_endpoint_processes_and_chunks(tmp_path):
    pdf_path = _make_mixed_pdf(tmp_path)

    # Call with chunk_size and chunk_overlap overrides
    response = client.post(
        "/api/v1/documents/chunk",
        json={
            "file_path": str(pdf_path),
            "chunk_size": 20,
            "chunk_overlap": 5,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["file_path"] == str(pdf_path)
    assert body["total_chunks"] > 0

    chunks = body["chunks"]
    # Check structure
    for chunk in chunks:
        assert "chunk_id" in chunk
        assert "page_number" in chunk
        assert "chunk_text" in chunk
        assert chunk["chunk_type"] == "text"

    # Make sure text from both pages is represented in chunks
    all_text = " ".join([c["chunk_text"] for c in chunks])
    assert "native" in all_text.lower()
    assert "scanned" in all_text.lower() or "ocr" in all_text.lower()


def test_chunk_endpoint_invalid_params(tmp_path):
    pdf_path = _make_mixed_pdf(tmp_path)

    # Call with invalid chunk parameters (overlap >= size)
    response = client.post(
        "/api/v1/documents/chunk",
        json={
            "file_path": str(pdf_path),
            "chunk_size": 10,
            "chunk_overlap": 10,
        },
    )

    assert response.status_code == 422
    assert "overlap" in response.json()["detail"].lower()


def test_chunk_endpoint_missing_file():
    response = client.post(
        "/api/v1/documents/chunk",
        json={"file_path": "/no/such/file.pdf"},
    )

    assert response.status_code == 404


def test_chunk_endpoint_corrupted_pdf(tmp_path):
    bad_path = tmp_path / "corrupted_api.pdf"
    bad_path.write_bytes(b"not a real pdf")

    response = client.post(
        "/api/v1/documents/chunk",
        json={"file_path": str(bad_path)},
    )

    assert response.status_code == 422
