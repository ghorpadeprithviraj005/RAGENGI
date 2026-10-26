import pytest
import numpy as np
from unittest.mock import MagicMock

from app.retrieval.retrieval_service import RetrievalService, RetrievalServiceError

@pytest.fixture
def mock_embedding_service():
    service = MagicMock()
    service.model.encode.return_value = np.array([[0.1, 0.2, 0.3]], dtype=np.float32)
    return service

@pytest.fixture
def mock_faiss_store():
    store = MagicMock()
    
    # Mocking FAISS index search return
    # returns distances, indices
    store.index.search.return_value = (
        np.array([[0.01, 0.05, 0.1]], dtype=np.float32),  # distances
        np.array([[0, 1, -1]], dtype=np.int64)            # indices
    )
    
    def mock_get_metadata(idx):
        if idx == 0:
            return {"chunk_id": 1, "page_number": 1, "chunk_text": "First matching chunk"}
        elif idx == 1:
            return {"chunk_id": 2, "page_number": 2, "chunk_text": "Second matching chunk"}
        return None
        
    store.get_metadata.side_effect = mock_get_metadata
    store.index.ntotal = 2 # Simulate non-empty index
    return store

def test_retrieval_service_initialization(mock_embedding_service, mock_faiss_store):
    service = RetrievalService(mock_embedding_service, mock_faiss_store, default_top_k=3)
    assert service.default_top_k == 3

def test_retrieval_search_success(mock_embedding_service, mock_faiss_store):
    service = RetrievalService(mock_embedding_service, mock_faiss_store, default_top_k=3)
    
    results = service.search("test query", top_k=3)
    
    # Assert model encode called
    mock_embedding_service.model.encode.assert_called_once()
    
    # Assert FAISS search called
    mock_faiss_store.index.search.assert_called_once()
    
    # Should skip the -1 index and only return 2 results
    assert len(results) == 2
    
    # Verify results
    assert results[0]["chunk_id"] == 1
    assert results[0]["page_number"] == 1
    assert results[0]["chunk_text"] == "First matching chunk"
    assert pytest.approx(results[0]["similarity_score"], 0.001) == 0.01
    
    assert results[1]["chunk_id"] == 2
    assert results[1]["page_number"] == 2
    assert results[1]["chunk_text"] == "Second matching chunk"
    assert pytest.approx(results[1]["similarity_score"], 0.001) == 0.05

def test_retrieval_search_empty_query(mock_embedding_service, mock_faiss_store):
    service = RetrievalService(mock_embedding_service, mock_faiss_store)
    
    results = service.search("")
    assert results == []
    mock_embedding_service.model.encode.assert_not_called()

def test_retrieval_search_empty_index(mock_embedding_service, mock_faiss_store):
    mock_faiss_store.index.ntotal = 0
    service = RetrievalService(mock_embedding_service, mock_faiss_store)
    
    results = service.search("query")
    assert results == []
    mock_faiss_store.index.search.assert_not_called()

def test_retrieval_search_exception(mock_embedding_service, mock_faiss_store):
    mock_faiss_store.index.search.side_effect = Exception("FAISS crash")
    service = RetrievalService(mock_embedding_service, mock_faiss_store)
    
    with pytest.raises(RetrievalServiceError) as exc_info:
        service.search("test query")
    assert "Failed to execute search" in str(exc_info.value)


def test_retrieval_deduplication(mock_embedding_service, mock_faiss_store):
    mock_faiss_store.index.search.return_value = (
        np.array([[0.05, 0.06, 0.07]], dtype=np.float32),
        np.array([[0, 1, 2]], dtype=np.int64)
    )
    mock_faiss_store.index.ntotal = 3
    # Return duplicate chunk text for index 0 and 1
    mock_faiss_store.get_metadata.side_effect = lambda idx: {
        0: {"chunk_id": 1, "page_number": 1, "chunk_text": "Identical paragraph text in both chunks."},
        1: {"chunk_id": 2, "page_number": 1, "chunk_text": "Identical paragraph text in both chunks."},
        2: {"chunk_id": 3, "page_number": 2, "chunk_text": "Completely distinct second chunk text."}
    }.get(idx)

    service = RetrievalService(mock_embedding_service, mock_faiss_store, default_top_k=3)
    results = service.search("paragraph text", top_k=3)

    # Duplicate should be filtered out
    assert len(results) == 2
    assert results[0]["chunk_id"] == 1
    assert results[1]["chunk_id"] == 3
