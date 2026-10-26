import os
import tempfile
import json
import pytest
import numpy as np
from unittest.mock import patch, MagicMock

from app.vector_store.faiss_store import FaissStore, FaissStoreError

@pytest.fixture
def temp_index_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir

@pytest.fixture
def sample_embeddings():
    return [
        {
            "embedding": [0.1] * 384,
            "metadata": {"chunk_id": 1, "page_number": 1, "chunk_text": "First chunk"}
        },
        {
            "embedding": [0.2] * 384,
            "metadata": {"chunk_id": 2, "page_number": 1, "chunk_text": "Second chunk"}
        }
    ]

def test_faiss_store_initialization(temp_index_dir):
    store = FaissStore(index_path=temp_index_dir, dimension=384)
    assert store.dimension == 384
    assert store.index is not None
    assert store._current_id == 0
    assert store.metadata_store == {}

def test_add_embeddings(temp_index_dir, sample_embeddings):
    store = FaissStore(index_path=temp_index_dir, dimension=384)
    store.add_embeddings(sample_embeddings)
    
    assert store.index.ntotal == 2
    assert store._current_id == 2
    assert len(store.metadata_store) == 2
    assert store.metadata_store[0]["chunk_id"] == 1
    assert store.metadata_store[1]["chunk_id"] == 2

def test_add_embeddings_dimension_mismatch(temp_index_dir):
    store = FaissStore(index_path=temp_index_dir, dimension=384)
    bad_embeddings = [
        {"embedding": [0.1] * 100, "metadata": {}}
    ]
    with pytest.raises(FaissStoreError) as exc_info:
        store.add_embeddings(bad_embeddings)
    assert "Embedding dimension mismatch" in str(exc_info.value)

def test_save_and_load_index(temp_index_dir, sample_embeddings):
    # Initialize and add data
    store1 = FaissStore(index_path=temp_index_dir, dimension=384)
    store1.add_embeddings(sample_embeddings)
    store1.save_index()
    
    # Verify files created
    assert os.path.exists(os.path.join(temp_index_dir, "vector_store.index"))
    assert os.path.exists(os.path.join(temp_index_dir, "metadata.json"))
    
    # Load into a new instance
    store2 = FaissStore(index_path=temp_index_dir, dimension=384)
    
    assert store2.index.ntotal == 2
    assert store2._current_id == 2
    assert len(store2.metadata_store) == 2
    
    # Verify metadata restoration
    meta0 = store2.get_metadata(0)
    assert meta0["chunk_id"] == 1
    assert meta0["page_number"] == 1
    assert meta0["chunk_text"] == "First chunk"
    assert "last_access" in meta0

    meta1 = store2.get_metadata(1)
    assert meta1["chunk_id"] == 2
    assert meta1["page_number"] == 1
    assert meta1["chunk_text"] == "Second chunk"
    assert "last_access" in meta1

def test_load_index_not_found(temp_index_dir):
    store = FaissStore(index_path=temp_index_dir, dimension=384)
    # Delete the newly created files (if any) or specify a non-existent path
    if os.path.exists(store.faiss_file_path):
        os.remove(store.faiss_file_path)
    
    with pytest.raises(FaissStoreError) as exc_info:
        store.load_index()
    assert "File not found" in str(exc_info.value) or "No such file or directory" in str(exc_info.value) or "Index file not found" in str(exc_info.value)
