import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app
from app.schemas.chunk import ChunkingResult, Chunk
from app.schemas.ocr import DocumentExtractionResult, OCRPageResult

client = TestClient(app)

@pytest.fixture
def mock_pipeline():
    with patch("app.api.routes.rag._pipeline") as mock:
        yield mock

@pytest.fixture
def mock_chunker():
    with patch("app.api.routes.rag._chunker") as mock:
        yield mock

@pytest.fixture
def mock_embedding_service():
    with patch("app.api.routes.rag._embedding_service") as mock:
        yield mock

@pytest.fixture
def mock_faiss_store():
    with patch("app.api.routes.rag._faiss_store") as mock:
        yield mock

@pytest.fixture
def mock_retrieval_service():
    with patch("app.api.routes.rag._retrieval_service") as mock:
        yield mock

@pytest.fixture
def mock_llm_service():
    with patch("app.api.routes.rag._llm_service") as mock:
        yield mock

def test_ingest_document_success(mock_pipeline, mock_chunker, mock_embedding_service, mock_faiss_store):
    # Setup mocks
    mock_pipeline.process.return_value = DocumentExtractionResult(
        file_path="test.pdf", page_count=1, pages=[OCRPageResult(page_number=1, text="test", source="native_text")], ocr_pages_count=0
    )
    mock_chunker.chunk_document.return_value = ChunkingResult(
        file_path="test.pdf", chunks=[Chunk(chunk_id=1, page_number=1, chunk_text="test", chunk_type="text")], total_chunks=1
    )
    mock_embedding_service.generate_embeddings.return_value = [{"embedding": [0.1], "metadata": {"chunk_id": 1}}]
    
    # Run test with multipart file upload
    response = client.post(
        "/api/v1/rag/ingest",
        files={"file": ("test.pdf", b"%PDF-1.4 dummy", "application/pdf")}
    )
    
    # Asserts
    assert response.status_code == 200
    data = response.json()
    assert "test.pdf" in data["file_path"]
    assert data["total_chunks"] == 1
    assert data["status"] == "success"
    mock_faiss_store.add_embeddings.assert_called_once()
    mock_faiss_store.save_index.assert_called_once()

def test_ask_question_success(mock_retrieval_service, mock_llm_service):
    # Setup mocks
    mock_retrieval_service.search.return_value = [{"chunk_id": 1, "page_number": 1, "chunk_text": "test context"}]
    mock_llm_service.generate_answer.return_value = {
        "answer": "This is the answer.",
        "citations": [{"chunk_id": 1, "page_number": 1}]
    }
    
    # Run test
    response = client.post(
        "/api/v1/rag/ask",
        json={"query": "What is the answer?"}
    )
    
    # Asserts
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "What is the answer?"
    assert data["answer"] == "This is the answer."
    assert len(data["citations"]) == 1

def test_ask_question_no_context(mock_retrieval_service, mock_llm_service):
    # Setup mocks
    mock_retrieval_service.search.return_value = []
    
    # Run test
    response = client.post(
        "/api/v1/rag/ask",
        json={"query": "What is the answer?"}
    )
    
    # Asserts
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "The uploaded document does not contain enough information."
    mock_llm_service.generate_answer.assert_not_called()

def test_ask_question_exception(mock_retrieval_service):
    # Setup mocks
    mock_retrieval_service.search.side_effect = Exception("Database error")
    
    # Run test
    response = client.post(
        "/api/v1/rag/ask",
        json={"query": "What is the answer?"}
    )
    
    # Asserts
    assert response.status_code == 500
    assert "QA failed" in response.json()["detail"]
