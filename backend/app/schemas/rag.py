from typing import List, Optional
from pydantic import BaseModel, Field

class IngestionResponse(BaseModel):
    file_path: str = Field(..., description="Path to the ingested PDF")
    total_chunks: int = Field(..., description="Total chunks embedded and saved")
    status: str = Field(default="success", description="Ingestion status")

class QARequest(BaseModel):
    query: str = Field(
        ...,
        description="User question to answer",
        examples=["What is the main finding in the document?"]
    )
    top_k: Optional[int] = Field(None, description="Override number of chunks retrieved")
    active_filename: Optional[str] = Field(None, description="Optional active document filename to scope retrieval")

class Citation(BaseModel):
    chunk_id: int
    page_number: int
    file_path: Optional[str] = Field(None, description="Path to the source PDF file")

class QAResponse(BaseModel):
    query: str = Field(..., description="The original query")
    answer: str = Field(..., description="The generated answer from the LLM")
    citations: List[Citation] = Field(default_factory=list, description="Citations used to generate the answer")

class DeleteDocumentResponse(BaseModel):
    filename: str
    deleted_files: List[str] = Field(default_factory=list)
    vectors_removed: int = 0
    status: str = "success"

class CleanupResponse(BaseModel):
    inactivity_days: int
    deleted_documents: List[str] = Field(default_factory=list)
    total_vectors_removed: int = 0
    freed_bytes: int = 0
    status: str = "success"

class EligibleDocument(BaseModel):
    filename: str = Field(..., description="Document filename")
    file_path: str = Field(..., description="Stored document file path")
    last_access: str = Field(..., description="ISO 8601 UTC timestamp of last access")
    inactive_days: float = Field(..., description="Days since last access")
    file_size_bytes: int = Field(default=0, description="File size in bytes")
    vector_count: int = Field(default=0, description="Number of embeddings in FAISS")

class EligibleDocumentsResponse(BaseModel):
    inactivity_threshold_days: int
    current_time: str
    eligible_count: int
    documents: List[EligibleDocument] = Field(default_factory=list)

class TouchDocumentResponse(BaseModel):
    filename: str
    vectors_updated: int
    last_access: str
    status: str = "success"

class CleanupRunRequest(BaseModel):
    days: int = Field(default=30, ge=1, description="Inactivity threshold in days")
    simulated_now: Optional[str] = Field(None, description="Optional ISO 8601 timestamp for simulation/testing")
    dry_run: bool = Field(default=False, description="Simulate cleanup without deleting data")
