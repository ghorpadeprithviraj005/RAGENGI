import importlib
import os
import sys
import pathlib
import tempfile

# Ensure project root is on sys.path for imports
project_root = pathlib.Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def test_import_real_services():
    """Verify that the core service classes can be imported.
    This ensures the benchmark can initialise the real services.
    """
    embedding_mod = importlib.import_module('app.embeddings.embedding_service')
    vector_mod = importlib.import_module('app.vector_store.faiss_store')
    llm_mod = importlib.import_module('app.llm.llm_service')
    assert hasattr(embedding_mod, 'EmbeddingService')
    assert hasattr(vector_mod, 'FaissStore')
    assert hasattr(llm_mod, 'LLMService')

def test_runner_import_side_effect_free(tmp_path: pathlib.Path, monkeypatch):
    """Import the benchmark runner without triggering filesystem side‑effects.
    The runner should not create any report directories or checkpoint files on import.
    """
    # Record existing report dirs before import
    reports_dir = pathlib.Path('backend/reports')
    pre_existing = set(p for p in reports_dir.iterdir() if p.is_dir()) if reports_dir.exists() else set()

    # Import the runner module
    runner_mod = importlib.import_module('backend.scratch.run_authoritative_100_subset_benchmark')

    # After import, no new directories should have been created under reports/
    post_existing = set(p for p in reports_dir.iterdir() if p.is_dir()) if reports_dir.exists() else set()
    assert pre_existing == post_existing, "Importing the runner created report directories"

    # Ensure that calling main() would raise an error if services cannot be instantiated (we don't call it here)
    assert hasattr(runner_mod, 'main')
