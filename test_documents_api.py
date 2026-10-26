"""
API-level tests for POST /api/v1/documents/extract.

These use FastAPI's TestClient to exercise the endpoint exactly as an HTTP
client would, verifying that PDFExtractor's exceptions are correctly mapped
to HTTP status codes by the route (app/api/routes/documents.py).
"""

import fitz
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _make_pdf(tmp_path, text: str = "API test content", filename: str = "api_test.pdf"):
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    path = tmp_path / filename
    document.save(path)
    document.close()
    return path


def test_health_check():
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_extract_endpoint_success(tmp_path):
    pdf_path = _make_pdf(tmp_path)

    response = client.post("/api/v1/documents/extract", json={"file_path": str(pdf_path)})

    assert response.status_code == 200
    body = response.json()
    assert body["page_count"] == 1
    assert "API test content" in body["pages"][0]["text"]
    assert body["pages"][0]["has_native_text"] is True


def test_extract_endpoint_missing_file_returns_404():
    response = client.post(
        "/api/v1/documents/extract", json={"file_path": "/no/such/file.pdf"}
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_extract_endpoint_corrupted_pdf_returns_422(tmp_path):
    bad_path = tmp_path / "corrupted.pdf"
    bad_path.write_bytes(b"not a real pdf")

    response = client.post("/api/v1/documents/extract", json={"file_path": str(bad_path)})

    assert response.status_code == 422


def test_extract_endpoint_empty_pdf_returns_422(tmp_path):
    # See tests/test_pdf_extractor.py::_make_zero_page_pdf for why this is
    # hand-built rather than written via fitz.Document.save().
    pdf_bytes = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"
        b"trailer\n<< /Size 3 /Root 1 0 R >>\n%%EOF\n"
    )
    empty_path = tmp_path / "empty.pdf"
    empty_path.write_bytes(pdf_bytes)

    response = client.post("/api/v1/documents/extract", json={"file_path": str(empty_path)})

    assert response.status_code == 422


def test_extract_endpoint_rejects_missing_field():
    response = client.post("/api/v1/documents/extract", json={})

    assert response.status_code == 422  # Pydantic validation error, not our custom exceptions
