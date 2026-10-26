# tests/unit/test_llm_citation.py
import pytest
from unittest.mock import patch, MagicMock
from app.llm.llm_service import LLMService, LLMServiceError

@pytest.fixture
def mock_llama():
    with patch("app.llm.llm_service.Llama") as MockLlamaClass:
        mock_instance = MagicMock()
        # Default successful response
        mock_instance.create_chat_completion.return_value = {
            "choices": [{"message": {"content": "Answer with citation. [Citation: Page 3, Chunk 7]"}}]
        }
        MockLlamaClass.return_value = mock_instance
        yield MockLlamaClass

def test_generate_answer_with_matching_citation(mock_llama):
    service = LLMService(model_path="dummy.gguf")
    chunks = [{
        "chunk_id": 7,
        "page_number": 3,
        "file_path": "doc.pdf",
        "chunk_text": "Some context"
    }]
    result = service.generate_answer("Question?", chunks)
    assert "[Citation: Page 3, Chunk 7]" in result["answer"]
    assert len(result["citations"]) == 1
    cit = result["citations"][0]
    assert cit["chunk_id"] == 7 and cit["page_number"] == 3

def test_generate_answer_with_mismatched_citation(mock_llama):
    # Answer contains a citation that is not in retrieved chunks
    mock_llama.return_value.create_chat_completion.return_value = {
        "choices": [{"message": {"content": "Answer with wrong citation. [Citation: Page 5, Chunk 2]"}}]
    }
    service = LLMService(model_path="dummy.gguf")
    chunks = [{
        "chunk_id": 1,
        "page_number": 1,
        "file_path": "doc.pdf",
        "chunk_text": "Context"
    }]
    result = service.generate_answer("Question?", chunks)
    # No matching citation should be returned
    assert result["citations"] == []

def test_generate_answer_abstention(mock_llama):
    mock_llama.return_value.create_chat_completion.return_value = {
        "choices": [{"message": {"content": "The uploaded document does not contain enough information."}}]
    }
    service = LLMService(model_path="dummy.gguf")
    result = service.generate_answer("Question?", [])
    assert result["answer"].startswith("The uploaded document does not contain enough information")
    assert result["citations"] == []

def test_generate_answer_failure(mock_llama):
    mock_llama.return_value.create_chat_completion.side_effect = Exception("LLM crash")
    service = LLMService(model_path="dummy.gguf")
    with pytest.raises(LLMServiceError):
        service.generate_answer("Question?", [])
