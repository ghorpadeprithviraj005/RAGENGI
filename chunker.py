"""
Chunking Service.

Responsibility (single, narrow): given a DocumentExtractionResult from the PDF/OCR
pipeline, split its page-wise text into structured, overlapping, page-aware chunks.
Respects page boundaries so that a chunk belongs to exactly one page, maintaining
precise citation information.
"""

import logging
from typing import List, Optional

from app.core.config import settings
from app.schemas.chunk import Chunk, ChunkingResult
from app.schemas.ocr import DocumentExtractionResult

logger = logging.getLogger(__name__)


class ChunkerError(Exception):
    """Base class for all errors raised by the Chunking Service."""


class ChunkerValueError(ChunkerError, ValueError):
    """Raised when invalid chunking configuration parameters are provided."""


class RecursiveCharacterChunker:
    """
    Splits text recursively using a sequence of separators to keep semantically
    coherent units (paragraphs, sentences, words) together when possible.
    """

    def __init__(
        self,
        chunk_size: int,
        chunk_overlap: int,
        separators: Optional[List[str]] = None,
    ) -> None:
        """
        Args:
            chunk_size: Maximum length of a chunk in characters.
            chunk_overlap: Maximum character overlap between successive chunks.
            separators: Hierarchical list of separators to try splitting on.
        """
        if chunk_size <= 0:
            raise ChunkerValueError("chunk_size must be a positive integer.")
        if chunk_overlap < 0:
            raise ChunkerValueError("chunk_overlap must be a non-negative integer.")
        if chunk_overlap >= chunk_size:
            raise ChunkerValueError("chunk_overlap must be strictly less than chunk_size.")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", " ", ""]

    def split_text(self, text: str) -> List[str]:
        """Splits the input text into overlapping chunks recursively."""
        return self._split_text(text, self.separators)

    def _split_text(self, text: str, separators: List[str]) -> List[str]:
        if len(text) <= self.chunk_size:
            return [text] if text else []

        if not separators:
            # Fall back to brute-force split when no separators remain
            chunks = []
            step = self.chunk_size - self.chunk_overlap
            if step <= 0:
                step = max(1, self.chunk_size // 2)
            for i in range(0, len(text), step):
                chunk = text[i : i + self.chunk_size]
                if chunk:
                    chunks.append(chunk)
            return chunks

        separator = separators[0]
        next_separators = separators[1:]

        # Split text by current separator
        parts = text.split(separator) if separator != "" else list(text)

        chunks = []
        current_chunk_parts = []
        current_length = 0
        sep_len = len(separator)

        for part in parts:
            part_len = len(part)

            # If a single part is larger than chunk_size, split it recursively using remaining separators
            if part_len > self.chunk_size:
                # Flush whatever is in the current chunk first
                if current_chunk_parts:
                    chunks.append(separator.join(current_chunk_parts))
                    current_chunk_parts = []
                    current_length = 0

                sub_chunks = self._split_text(part, next_separators)
                chunks.extend(sub_chunks)
                continue

            # Calculate total length if this part is appended to the current chunk
            added_len = part_len + (sep_len if current_length > 0 else 0)

            if current_length + added_len <= self.chunk_size:
                current_chunk_parts.append(part)
                current_length += added_len
            else:
                # Flush the current chunk
                if current_chunk_parts:
                    chunks.append(separator.join(current_chunk_parts))

                # Calculate overlap parts to carry over to the next chunk
                overlap_parts = []
                overlap_len = 0
                for p in reversed(current_chunk_parts):
                    p_len = len(p)
                    next_overlap_len = overlap_len + p_len + (sep_len if overlap_len > 0 else 0)
                    if next_overlap_len <= self.chunk_overlap:
                        overlap_parts.insert(0, p)
                        overlap_len = next_overlap_len
                    else:
                        break

                current_chunk_parts = overlap_parts + [part]
                current_length = overlap_len + part_len + (sep_len if overlap_len > 0 else 0)

        # Flush the final chunk if any parts remain
        if current_chunk_parts:
            chunks.append(separator.join(current_chunk_parts))

        return chunks


class PDFChunker:
    """Orchestrates page-aware text splitting across an extracted document's pages."""

    def __init__(
        self,
        default_chunk_size: Optional[int] = None,
        default_chunk_overlap: Optional[int] = None,
    ) -> None:
        self._default_chunk_size = default_chunk_size or settings.CHUNK_SIZE
        self._default_chunk_overlap = default_chunk_overlap or settings.CHUNK_OVERLAP

    def chunk_document(
        self,
        extraction_result: DocumentExtractionResult,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ) -> ChunkingResult:
        """
        Processes a DocumentExtractionResult, splitting the text page-by-page.

        Each generated chunk is guaranteed to be page-contained (no chunks span
        across page boundaries) to guarantee perfect citation accuracy.
        """
        size = chunk_size if chunk_size is not None else self._default_chunk_size
        overlap = chunk_overlap if chunk_overlap is not None else self._default_chunk_overlap

        logger.info(
            "Starting chunking for %s (size=%d, overlap=%d)",
            extraction_result.file_path,
            size,
            overlap,
        )

        splitter = RecursiveCharacterChunker(chunk_size=size, chunk_overlap=overlap)
        chunks: List[Chunk] = []
        chunk_counter = 1

        for page in extraction_result.pages:
            cleaned_text = (page.text or "").strip()
            if not cleaned_text:
                logger.debug(
                    "Skipping chunk generation for page %d (no text content)",
                    page.page_number,
                )
                continue

            page_chunks = splitter.split_text(cleaned_text)
            logger.debug(
                "Split page %d text (%d chars) into %d chunk(s)",
                page.page_number,
                len(cleaned_text),
                len(page_chunks),
            )

            for chunk_text in page_chunks:
                chunks.append(
                    Chunk(
                        chunk_id=chunk_counter,
                        page_number=page.page_number,
                        chunk_text=chunk_text,
                        chunk_type="text",
                    )
                )
                chunk_counter += 1

        logger.info(
            "Chunking complete for %s: generated %d chunk(s) across %d page(s)",
            extraction_result.file_path,
            len(chunks),
            extraction_result.page_count,
        )

        return ChunkingResult(
            file_path=extraction_result.file_path,
            chunks=chunks,
            total_chunks=len(chunks),
        )
