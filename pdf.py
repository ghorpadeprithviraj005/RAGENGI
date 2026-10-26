"""
Pydantic schemas for the PDF Extraction Service (Module 1).

These are the request/response contracts shared between the ingestion module
(app/ingestion/pdf_extractor.py) and the API layer (app/api/routes/documents.py).
Keeping them in a dedicated schemas module -- rather than defining them inline
in the router or the extractor -- means later modules (chunking, embedding)
can import and reuse `PageText`/`PDFExtractionResult` without creating a
circular import between `ingestion` and `api`.
"""

from typing import List

from pydantic import BaseModel, Field


class PageText(BaseModel):
    """Extracted content for a single PDF page."""

    page_number: int = Field(..., ge=1, description="1-indexed page number")
    text: str = Field(..., description="Extracted native text content of the page")
    has_native_text: bool = Field(
        ...,
        description=(
            "False if the page had little/no extractable text and is therefore "
            "a candidate for OCR in a later module. This service does not "
            "perform OCR itself -- it only flags the need for it."
        ),
    )


class PDFExtractionResult(BaseModel):
    """Full result of extracting a PDF, returned by the /documents/extract endpoint."""

    file_path: str = Field(..., description="Path to the PDF that was processed")
    page_count: int = Field(..., ge=1, description="Total number of pages in the PDF")
    pages: List[PageText] = Field(..., description="Per-page extraction results, in page order")


class PDFExtractionRequest(BaseModel):
    """Request body for POST /api/v1/documents/extract."""

    file_path: str = Field(
        ...,
        description="Absolute or relative path to a PDF file already present on disk",
        examples=["storage/uploads/sample.pdf"],
    )
