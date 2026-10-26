import os
import shutil
import tempfile
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.vector_store.faiss_store import FaissStore
from app.retrieval.retrieval_service import RetrievalService
from app.core.config import settings
import app.api.routes.rag as rag_module

client = TestClient(app)
API_KEY_HEADER = {"X-API-Key": "ragengi-secure-cleanup-key"}

@pytest.fixture
def temp_environment():
    """Create a temporary sandbox for vector store and upload files."""
    tmp_dir = tempfile.mkdtemp(prefix="ragengi_test_cleanup_")
    uploads_dir = os.path.join(tmp_dir, "storage", "uploads")
    vector_dir = os.path.join(tmp_dir, "storage", "vector_store")
    os.makedirs(uploads_dir, exist_ok=True)
    os.makedirs(vector_dir, exist_ok=True)

    # Backup original state
    orig_base = settings.BASE_DIR
    orig_store = rag_module._faiss_store
    orig_retrieval = rag_module._retrieval_service
    orig_active = rag_module._active_filename

    # Point to temp environment
    settings.BASE_DIR = tmp_dir
    test_faiss = FaissStore(index_path=vector_dir, dimension=384)
    rag_module._faiss_store = test_faiss
    rag_module._retrieval_service.faiss_store = test_faiss
    rag_module._active_filename = None

    yield {
        "root": tmp_dir,
        "uploads": uploads_dir,
        "vector_store": test_faiss,
    }

    # Restore
    settings.BASE_DIR = orig_base
    rag_module._faiss_store = orig_store
    rag_module._retrieval_service = orig_retrieval
    rag_module._active_filename = orig_active
    shutil.rmtree(tmp_dir, ignore_errors=True)


def test_last_access_initialized_on_embeddings_add(temp_environment):
    store: FaissStore = temp_environment["vector_store"]
    sample_data = [{
        "embedding": [0.1] * 384,
        "metadata": {"chunk_id": 1, "file_path": "sample.pdf"}
    }]
    store.add_embeddings(sample_data)
    meta = store.get_metadata(0)
    assert "last_access" in meta
    assert datetime.fromisoformat(meta["last_access"]) is not None


def test_update_last_access_and_retrieval(temp_environment):
    store: FaissStore = temp_environment["vector_store"]
    sample_data = [{
        "embedding": [0.0] * 384,
        "metadata": {"chunk_id": 1, "file_path": "research.pdf", "chunk_text": "Sample text"}
    }]
    store.add_embeddings(sample_data)
    old_time = "2026-01-01T00:00:00+00:00"
    store.metadata_store[0]["last_access"] = old_time
    store.save_index()

    # Touch via API
    resp = client.post("/api/v1/rag/documents/research.pdf/touch")
    assert resp.status_code == 200
    data = resp.json()
    assert data["vectors_updated"] == 1
    new_time = data["last_access"]
    assert new_time > old_time
    assert store.get_metadata(0)["last_access"] == new_time


def test_missing_timestamp_never_triggers_cleanup(temp_environment):
    """Missing or corrupted timestamps must NEVER trigger deletion."""
    store: FaissStore = temp_environment["vector_store"]
    upload_dir = temp_environment["uploads"]
    
    # Create physical dummy file
    file_path = os.path.join(upload_dir, "legacy_doc.pdf")
    with open(file_path, "w") as f:
        f.write("legacy document content")

    # Add embedding without last_access
    store.add_embeddings([{
        "embedding": [0.2] * 384,
        "metadata": {"chunk_id": 1, "file_path": file_path}
    }])
    # Explicitly clear last_access
    store.metadata_store[0]["last_access"] = None
    store.save_index()

    simulated_future = "2027-01-01T00:00:00+00:00"
    
    # Check eligible endpoint
    resp = client.get(f"/api/v1/rag/cleanup/eligible?days=30&simulated_now={simulated_future}")
    assert resp.status_code == 200
    assert resp.json()["eligible_count"] == 0

    # Run cleanup
    clean_resp = client.post(
        "/api/v1/rag/cleanup/run",
        json={"days": 30, "simulated_now": simulated_future},
        headers=API_KEY_HEADER
    )
    assert clean_resp.status_code == 200
    assert len(clean_resp.json()["deleted_documents"]) == 0
    # File must still exist
    assert os.path.exists(file_path)
    assert store.index.ntotal == 1


def test_inactivity_cutoff_30_days_simulation(temp_environment):
    """
    Documents under 30 days are preserved.
    Documents at or beyond 30 days are deleted along with FAISS entries.
    """
    store: FaissStore = temp_environment["vector_store"]
    upload_dir = temp_environment["uploads"]

    # Doc 1: Active 20 days ago (preserved)
    doc1_file = os.path.join(upload_dir, "recent_doc.pdf")
    with open(doc1_file, "w") as f:
        f.write("recent doc")
    # Doc 2: Inactive 35 days ago (eligible)
    doc2_file = os.path.join(upload_dir, "expired_doc.pdf")
    with open(doc2_file, "w") as f:
        f.write("expired doc")

    sim_now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    time_20_days_ago = (sim_now - timedelta(days=20)).isoformat()
    time_35_days_ago = (sim_now - timedelta(days=35)).isoformat()

    store.add_embeddings([
        {
            "embedding": [0.1] * 384,
            "metadata": {"chunk_id": 1, "file_path": doc1_file, "last_access": time_20_days_ago}
        },
        {
            "embedding": [0.2] * 384,
            "metadata": {"chunk_id": 2, "file_path": doc2_file, "last_access": time_35_days_ago}
        }
    ])
    # Manually ensure timestamps reflect the simulated ages
    store.metadata_store[0]["last_access"] = time_20_days_ago
    store.metadata_store[1]["last_access"] = time_35_days_ago
    store.save_index()

    # 1. Check eligible list
    sim_now_iso = sim_now.isoformat()
    resp = client.get(f"/api/v1/rag/cleanup/eligible?days=30&simulated_now={sim_now_iso}")
    assert resp.status_code == 200
    eligible_docs = resp.json()["documents"]
    assert len(eligible_docs) == 1
    assert "expired_doc.pdf" in eligible_docs[0]["filename"]

    # 2. Run cleanup
    run_resp = client.post(
        "/api/v1/rag/cleanup/run",
        json={"days": 30, "simulated_now": sim_now_iso},
        headers=API_KEY_HEADER
    )
    assert run_resp.status_code == 200
    res_data = run_resp.json()
    assert len(res_data["deleted_documents"]) == 1
    assert "expired_doc.pdf" in res_data["deleted_documents"][0]
    assert res_data["total_vectors_removed"] == 1

    # Verify physical file deletions
    assert not os.path.exists(doc2_file)
    assert os.path.exists(doc1_file)

    # Verify FAISS index consistency
    assert store.index.ntotal == 1
    assert store.get_metadata(0)["file_path"] == doc1_file


def test_active_document_protection(temp_environment):
    """Currently active document must never be deleted by cleanup or manual deletion."""
    store: FaissStore = temp_environment["vector_store"]
    upload_dir = temp_environment["uploads"]

    file_path = os.path.join(upload_dir, "important_active.pdf")
    with open(file_path, "w") as f:
        f.write("important")

    old_time = "2025-01-01T00:00:00+00:00"
    store.add_embeddings([{
        "embedding": [0.3] * 384,
        "metadata": {"chunk_id": 1, "file_path": file_path, "last_access": old_time}
    }])
    store.metadata_store[0]["last_access"] = old_time
    store.save_index()

    # Set as active document
    rag_module._active_filename = "important_active.pdf"

    # Attempt cleanup
    clean_resp = client.post(
        "/api/v1/rag/cleanup/run",
        json={"days": 30, "simulated_now": "2026-06-01T00:00:00+00:00"},
        headers=API_KEY_HEADER
    )
    assert len(clean_resp.json()["deleted_documents"]) == 0
    assert os.path.exists(file_path)

    # Attempt manual deletion
    del_resp = client.delete(
        "/api/v1/rag/documents/important_active.pdf",
        headers=API_KEY_HEADER
    )
    assert del_resp.status_code == 400
    assert "Cannot delete active document" in del_resp.json()["detail"]


def test_model_file_and_system_protection(temp_environment):
    """Never allow deleting models or vector store files."""
    del_resp = client.delete(
        "/api/v1/rag/documents/llama-2-7b.gguf",
        headers=API_KEY_HEADER
    )
    assert del_resp.status_code == 400
    assert "Safety violation" in del_resp.json()["detail"]


def test_api_key_protection_unauthorized(temp_environment):
    """Protected endpoints require valid API key."""
    # Invalid key
    bad_resp = client.post(
        "/api/v1/rag/cleanup/run",
        json={"days": 30},
        headers={"X-API-Key": "wrong-key"}
    )
    assert bad_resp.status_code == 401

    # Missing key
    missing_resp = client.post(
        "/api/v1/rag/cleanup/run",
        json={"days": 30}
    )
    assert missing_resp.status_code == 401
