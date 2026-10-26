import pytest
from unittest.mock import patch, MagicMock
from app.embeddings.embedding_service import EmbeddingService, EmbeddingServiceError
from app.schemas.chunk import Chunk

@pytest.fixture
def sample_chunks():
    return [
        Chunk(chunk_id=1, page_number=1, chunk_text="This is the first test chunk."),
        Chunk(chunk_id=2, page_number=1, chunk_text="This is the second test chunk.")
    ]

@patch("app.embeddings.embedding_service.SentenceTransformer")
def test_embedding_service_initialization(mock_sentence_transformer):
    service = EmbeddingService()
    mock_sentence_transformer.assert_called_once_with("all-MiniLM-L6-v2", device="cpu")
    assert service.model_name == "all-MiniLM-L6-v2"
    assert service.device == "cpu"

@patch("app.embeddings.embedding_service.SentenceTransformer")
def test_embedding_service_initialization_error(mock_sentence_transformer):
    mock_sentence_transformer.side_effect = Exception("Download failed")
    with pytest.raises(EmbeddingServiceError) as exc_info:
        EmbeddingService()
    assert "Model initialization failed" in str(exc_info.value)

@patch("app.embeddings.embedding_service.SentenceTransformer")
def test_generate_embeddings_success(mock_sentence_transformer, sample_chunks):
    # Setup mock model and its encode method
    mock_model_instance = MagicMock()
    # Mocking encode to return a 2D list/array of embeddings
    mock_model_instance.encode.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    
    # Mock SentenceTransformer return value to be our mock instance
    # We patch it directly on the already instantiated service to avoid rebuilding
    service = EmbeddingService()
    service.model = mock_model_instance
    
    results = service.generate_embeddings(sample_chunks, batch_size=2)
    
    assert len(results) == 2
    
    # Check first result
    assert results[0]["embedding"] == [0.1, 0.2, 0.3]
    assert results[0]["metadata"]["chunk_id"] == 1
    assert results[0]["metadata"]["page_number"] == 1
    assert results[0]["metadata"]["chunk_text"] == "This is the first test chunk."
    
    # Check second result
    assert results[1]["embedding"] == [0.4, 0.5, 0.6]
    assert results[1]["metadata"]["chunk_id"] == 2
    assert results[1]["metadata"]["page_number"] == 1
    assert results[1]["metadata"]["chunk_text"] == "This is the second test chunk."

    # Ensure encode was called with correct arguments
    mock_model_instance.encode.assert_called_once_with(
        ["This is the first test chunk.", "This is the second test chunk."],
        batch_size=2,
        show_progress_bar=False,
        convert_to_numpy=True
    )

@patch("app.embeddings.embedding_service.SentenceTransformer")
def test_generate_embeddings_empty_list(mock_sentence_transformer):
    service = EmbeddingService()
    results = service.generate_embeddings([])
    assert results == []

@patch("app.embeddings.embedding_service.SentenceTransformer")
def test_generate_embeddings_error(mock_sentence_transformer, sample_chunks):
    mock_model_instance = MagicMock()
    mock_model_instance.encode.side_effect = Exception("Encoding failed")
    
    service = EmbeddingService()
    service.model = mock_model_instance
    
    with pytest.raises(EmbeddingServiceError) as exc_info:
        service.generate_embeddings(sample_chunks)
    assert "Failed to generate embeddings" in str(exc_info.value)
