"""
Pydantic schemas for the merged text-extraction result (Module 2).

`OCRPageResult` / `DocumentExtractionResult` are distinct from Module 1's
`PageText` / `PDFExtractionResult` (app/schemas/pdf.py) on purpose: Module 1's
schema is the raw output of native-text extraction only (it still contains
the `has_native_text` flag but no OCR text). This schema represents the final,
merged, page-wise result the *pipeline* produces after applying OCR to
whichever pages needed it -- every page here has real text (or an
intentionally empty string if OCR genuinely found nothing) plus a `source`
label telling the caller exactly where that text came from.

Keeping these separate avoids overloading one model with two different
meanings of "this page's text" as the pipeline gains more stages later
(chunking will introduce yet another shape again).
"""

from typing import List, Literal

from pydantic import BaseModel, Field

TextSource = Literal["native_text", "ocr"]


class OCRPageResult(BaseModel):
    """Final text result for a single page after native extraction + OCR fallback."""

    page_number: int = Field(..., ge=1, description="1-indexed page number")
    text: str = Field(..., description="Final extracted text for this page")
    source: TextSource = Field(
        ...,
        description=(
            "'native_text' if taken directly from the PDF's text layer, "
            "'ocr' if recovered by running Tesseract on a rasterized page image"
        ),
    )


class DocumentExtractionResult(BaseModel):
    """Full merged result for a document, returned by the ingestion pipeline."""

    file_path: str = Field(..., description="Path to the PDF that was processed")
    page_count: int = Field(..., ge=1, description="Total number of pages in the PDF")
    pages: List[OCRPageResult] = Field(..., description="Per-page results, in page order")
    ocr_pages_count: int = Field(
        ..., ge=0, description="Number of pages that had no native text and required OCR"
    )
