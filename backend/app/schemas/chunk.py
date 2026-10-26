"""
Pydantic schemas for the Chunking Service (Module 3).

These define the data structures for text chunks generated from extracted documents
and the requests/responses handled by the API routing layer.

`faiss_vector_id` is added here (as Optional[int], defaulting to None) so that
Module 4 (Embedding + FAISS) can populate it in-place without requiring a
breaking schema change. While ingesting, Module 4 will set this field to the
integer position of the chunk's embedding vector in the FAISS index, giving the
SQLite metadata store a stable foreign key into the index.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

ChunkType = Literal["text", "table", "figure"]


class Chunk(BaseModel):
    """A single page-aware text chunk with source citations."""

    chunk_id: int = Field(
        ...,
        description="Unique sequential chunk ID within the document, starting at 1"
    )
    page_number: int = Field(
        ...,
        ge=1,
        description="1-indexed page number from which this chunk was extracted"
    )
    chunk_text: str = Field(
        ...,
        description="The actual text content of this chunk"
    )
    chunk_type: ChunkType = Field(
        default="text",
        description="The classification of this chunk content (text, table, figure)"
    )
    faiss_vector_id: Optional[int] = Field(
        default=None,
        description=(
            "Position of this chunk's embedding vector in the FAISS index. "
            "Populated by Module 4 (EmbeddingService) after the vector is written. "
            "None until the chunk has been embedded and indexed."
        ),
    )


class ChunkingRequest(BaseModel):
    """Request schema for document processing and chunking."""

    file_path: str = Field(
        ...,
        description="Absolute or relative path to a PDF file already present on disk",
        examples=["storage/uploads/sample.pdf"],
    )
    chunk_size: Optional[int] = Field(
        None,
        ge=1,
        description="Override the default chunk size in characters"
    )
    chunk_overlap: Optional[int] = Field(
        None,
        ge=0,
        description="Override the default chunk overlap in characters"
    )


class ChunkingResult(BaseModel):
    """Full result of the document processing and chunking pipeline."""

    file_path: str = Field(
        ...,
        description="Path to the PDF file that was chunked"
    )
    chunks: List[Chunk] = Field(
        ...,
        description="List of generated chunks sorted by page and order"
    )
    total_chunks: int = Field(
        ...,
        ge=0,
        description="Total number of chunks generated from the document"
    )
