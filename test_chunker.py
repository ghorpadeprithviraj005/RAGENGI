"""
Unit tests for app/ingestion/chunker.py.
"""

import pytest

from app.ingestion.chunker import (
    ChunkerValueError,
    PDFChunker,
    RecursiveCharacterChunker,
)
from app.schemas.ocr import DocumentExtractionResult, OCRPageResult


def test_recursive_splitter_validation():
    # Negative chunk size
    with pytest.raises(ChunkerValueError):
        RecursiveCharacterChunker(chunk_size=-10, chunk_overlap=2)

    # Negative overlap
    with pytest.raises(ChunkerValueError):
        RecursiveCharacterChunker(chunk_size=10, chunk_overlap=-2)

    # Overlap equal to chunk size
    with pytest.raises(ChunkerValueError):
        RecursiveCharacterChunker(chunk_size=10, chunk_overlap=10)

    # Overlap greater than chunk size
    with pytest.raises(ChunkerValueError):
        RecursiveCharacterChunker(chunk_size=10, chunk_overlap=15)


def test_recursive_splitter_simple():
    splitter = RecursiveCharacterChunker(chunk_size=10, chunk_overlap=2)
    text = "abcde fghij klmno"
    # Separators: ["\n\n", "\n", " ", ""]
    # "abcde" is len 5, "fghij" is len 5, "klmno" is len 5.
    # Combined with space, "abcde fghij" is len 11 (>10).
    # First chunk: "abcde" (since "abcde" + " " + "fghij" is 11 > 10).
    # Overlap check: we try to carry over parts of "abcde". "abcde" is len 5 > 2. So no overlap.
    # Next chunk starts with "fghij".
    # Resulting splits: ["abcde", "fghij", "klmno"]
    chunks = splitter.split_text(text)
    assert chunks == ["abcde", "fghij", "klmno"]


def test_recursive_splitter_with_overlap():
    # Simple overlap test where words are short
    splitter = RecursiveCharacterChunker(chunk_size=10, chunk_overlap=4)
    # separators list splits by space first.
    # parts: ["a", "b", "c", "d"]
    # part lengths: 1
    # 1 + 1 (space) + 1 + 1 (space) + 1 + 1 (space) + 1 = 7. Fits in 10.
    # "a b c d" fits.
    # Let's test a larger text: "a b c d e f g"
    # len("a b c") = 5. len("a b c d") = 7. len("a b c d e") = 9. len("a b c d e f") = 11 (> 10).
    # First chunk: "a b c d e" (len 9)
    # Overlap calculation: chunk_overlap = 4.
    # reversed parts: "e" (len 1), "d" (len 1), "c" (len 1), "b" (len 1), "a" (len 1).
    # overlap_parts:
    # "e" -> len 1 <= 4
    # "d" -> next_overlap_len = 1 + 1 + 1(space) = 3 <= 4
    # "c" -> next_overlap_len = 3 + 1 + 1(space) = 5 > 4. Stop.
    # So overlap_parts = ["d", "e"] (len 3).
    # Second chunk starts with "d", "e" and appends "f" (len 1) and "g" (len 1).
    # Chunk 2 parts: ["d", "e", "f", "g"] -> "d e f g" (len 7).
    text = "a b c d e f g"
    chunks = splitter.split_text(text)
    assert chunks == ["a b c d e", "d e f g"]


def test_recursive_splitter_fallback():
    # Test fallback to character slice when a single word exceeds chunk_size
    splitter = RecursiveCharacterChunker(chunk_size=5, chunk_overlap=2)
    text = "abcdefgh"
    # "abcdefgh" has no separators (no spaces, no newlines).
    # Brute force character split with step = chunk_size - chunk_overlap = 5 - 2 = 3.
    # Chunk 1: text[0:5] -> "abcde"
    # Chunk 2: text[3:8] -> "defgh"
    chunks = splitter.split_text(text)
    assert chunks == ["abcde", "defgh"]


def test_pdf_chunker_basic():
    extraction_result = DocumentExtractionResult(
        file_path="dummy.pdf",
        page_count=2,
        pages=[
            OCRPageResult(page_number=1, text="Hello World from page one", source="native_text"),
            OCRPageResult(page_number=2, text="This is page two text content", source="ocr"),
        ],
        ocr_pages_count=1,
    )

    chunker = PDFChunker(default_chunk_size=15, default_chunk_overlap=5)
    result = chunker.chunk_document(extraction_result)

    assert result.file_path == "dummy.pdf"
    assert result.total_chunks > 0

    # Ensure chunk_ids are sequential starting at 1
    chunk_ids = [c.chunk_id for c in result.chunks]
    assert chunk_ids == list(range(1, len(result.chunks) + 1))

    # Ensure page numbers are correct
    for chunk in result.chunks:
        assert chunk.chunk_type == "text"
        if chunk.page_number == 1:
            assert chunk.chunk_text in "Hello World from page one"
        elif chunk.page_number == 2:
            assert chunk.chunk_text in "This is page two text content"
        else:
            pytest.fail("Unexpected page number")


def test_pdf_chunker_ignores_empty_pages():
    extraction_result = DocumentExtractionResult(
        file_path="dummy.pdf",
        page_count=3,
        pages=[
            OCRPageResult(page_number=1, text="Page one text", source="native_text"),
            OCRPageResult(page_number=2, text="", source="ocr"),  # Empty page
            OCRPageResult(page_number=3, text="   ", source="native_text"),  # Whitespace-only page
        ],
        ocr_pages_count=1,
    )

    chunker = PDFChunker(default_chunk_size=20, default_chunk_overlap=5)
    result = chunker.chunk_document(extraction_result)

    assert result.total_chunks == 1
    assert result.chunks[0].page_number == 1
    assert result.chunks[0].chunk_text == "Page one text"
