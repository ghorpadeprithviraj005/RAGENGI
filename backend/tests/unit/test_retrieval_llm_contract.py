import pytest
from unittest.mock import MagicMock, patch
import numpy as np

from app.retrieval.retrieval_service import RetrievalService
from app.llm.llm_service import LLMService

@pytest.fixture
def mock_embedding_service():
    service = MagicMock()
    service.model.encode.return_value = np.array([[0.1, 0.2, 0.3]], dtype=np.float32)
    return service

@pytest.fixture
def mock_faiss_empty():
    store = MagicMock()
    store.index.ntotal = 0
    return store

@pytest.fixture
def mock_faiss_with_data():
    store = MagicMock()
    store.index.ntotal = 2
    store.index.search.return_value = (
        np.array([[0.12, 0.85]], dtype=np.float32),
        np.array([[0, 1]], dtype=np.int64)
    )
    store.get_metadata.side_effect = lambda idx: {
        0: {"chunk_id": 1, "page_number": 1, "chunk_text": "Sample document text", "file_path": "/path/doc.pdf"},
        1: {"chunk_id": 2, "page_number": 2, "chunk_text": "Another document text", "file_path": "/path/doc2.pdf"},
    }.get(idx)
    return store

def test_no_hit_retrieval_returns_empty_list(mock_embedding_service, mock_faiss_empty):
    service = RetrievalService(mock_embedding_service, mock_faiss_empty)
    res = service.search("any query")
    assert isinstance(res, list)
    assert len(res) == 0

def test_successful_retrieval_returns_candidates(mock_embedding_service, mock_faiss_with_data):
    service = RetrievalService(mock_embedding_service, mock_faiss_with_data)
    res = service.search("sample document query")
    assert isinstance(res, list)
    assert len(res) == 2
    assert res[0]["chunk_id"] == 1
    assert "similarity_score" in res[0]

def test_llm_build_messages_with_none_and_empty():
    with patch("app.llm.llm_service.Llama", MagicMock()):
        llm = LLMService(model_path="dummy.gguf")
        
        # Test None
        msgs_none = llm.build_messages("test query", retrieved_chunks=None)
        assert isinstance(msgs_none, list)
        assert "QUESTION: test query" in msgs_none[1]["content"]

        # Test Empty List
        msgs_empty = llm.build_messages("test query", retrieved_chunks=[])
        assert isinstance(msgs_empty, list)
        assert msgs_empty == msgs_none

def test_llm_generate_answer_with_none_retrieved_chunks():
    with patch("app.llm.llm_service.Llama") as mock_llama_class:
        mock_instance = MagicMock()
        mock_instance.create_chat_completion.return_value = {
            "choices": [{"message": {"content": "The uploaded document does not contain enough information."}}],
            "finish_reason": "stop",
            "usage": {"total_tokens": 15}
        }
        mock_llama_class.return_value = mock_instance

        llm = LLMService(model_path="dummy.gguf")
        out = llm.generate_answer("What is the secret?", retrieved_chunks=None)
        
        assert isinstance(out, dict)
        assert "answer" in out
        assert out["citations"] == []
        assert "does not contain enough information" in out["answer"].lower()
