import pytest
from unittest.mock import patch, MagicMock

from app.llm.llm_service import LLMService, LLMServiceError

@pytest.fixture
def mock_llama():
    with patch("app.llm.llm_service.Llama") as MockLlamaClass:
        # Create a mock instance
        mock_instance = MagicMock()
        
        # Mock create_chat_completion method of the llama instance
        mock_instance.create_chat_completion.return_value = {
            "choices": [
                {"message": {"content": " This is a mocked LLM response."}}
            ]
        }
        
        MockLlamaClass.return_value = mock_instance
        yield MockLlamaClass

@pytest.fixture
def sample_chunks():
    return [
        {"chunk_id": 1, "page_number": 5, "chunk_text": "France is a country in Europe."},
        {"chunk_id": 2, "page_number": 5, "chunk_text": "The capital of France is Paris."}
    ]

def test_llm_service_initialization(mock_llama):
    service = LLMService(model_path="dummy/path/model.gguf")
    
    mock_llama.assert_called_once_with(
        model_path="dummy/path/model.gguf",
        n_ctx=2048,
        n_gpu_layers=0,  # Ensure CPU-only
        chat_format="llama-2",
        verbose=False
    )
    assert service.llm is not None

def test_build_prompt():
    # We can test build_prompt even if llama is not installed, so we bypass init
    # But wait, LLMService requires Llama. Let's just mock it or handle None
    with patch("app.llm.llm_service.Llama", MagicMock()):
        service = LLMService(model_path="dummy")
        
    chunks = [
        {"chunk_id": 1, "page_number": 2, "chunk_text": "Chunk text here."}
    ]
    prompt = service.build_prompt("What is the text?", chunks)
    
    assert "[Citation: Page 2, Chunk 1]" in prompt
    assert "Chunk text here." in prompt
    assert "What is the text?" in prompt

def test_generate_answer_success(mock_llama, sample_chunks):
    service = LLMService(model_path="dummy.gguf")
    
    result = service.generate_answer("What is the capital of France?", sample_chunks)
    
    # Assert create_chat_completion was invoked
    service.llm.create_chat_completion.assert_called_once()
    
    # Check returned structure
    assert result["answer"] == "This is a mocked LLM response."
    
    # Check citations
    assert len(result["citations"]) == 2
    assert result["citations"][0]["chunk_id"] == 1
    assert result["citations"][0]["page_number"] == 5
    assert result["citations"][1]["chunk_id"] == 2
    assert result["citations"][1]["page_number"] == 5

def test_generate_answer_empty_query(mock_llama, sample_chunks):
    service = LLMService(model_path="dummy.gguf")
    result = service.generate_answer("   ", sample_chunks)
    
    assert "cannot answer an empty query" in result["answer"]
    assert result["citations"] == []
    service.llm.create_chat_completion.assert_not_called()

def test_generate_answer_error(mock_llama, sample_chunks):
    service = LLMService(model_path="dummy.gguf")
    service.llm.create_chat_completion.side_effect = Exception("LLM crash")
    
    with pytest.raises(LLMServiceError) as exc_info:
        service.generate_answer("Test query", sample_chunks)
    assert "Failed to generate answer" in str(exc_info.value)
