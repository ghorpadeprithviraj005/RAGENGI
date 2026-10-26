import importlib.util
import json
import types
from pathlib import Path
import pytest

# Helper to import the runner module without executing side‑effects
def load_runner_module():
    # The runner script lives in backend/scratch relative to this test file
    runner_path = Path(__file__).parents[2] / "scratch" / "run_authoritative_100_subset_benchmark.py"
    spec = importlib.util.spec_from_file_location("benchmark_runner", runner_path)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    return runner

def test_import_has_no_side_effects(monkeypatch):
    # Record existing sub‑folders in the reports directory before import
    reports_dir = Path(__file__).parents[3] / "reports"
    before = {p.name for p in reports_dir.iterdir() if p.is_dir()}

    # Load the module (which should not create any new directories)
    runner = load_runner_module()

    after = {p.name for p in reports_dir.iterdir() if p.is_dir()}
    assert before == after, "Importing the runner created unexpected report directories"

def test_inspect_checkpoint_various_cases(tmp_path):
    ck_path = tmp_path / "checkpoint.jsonl"
    # Build lines: valid, malformed, duplicate, missing fields, out‑of‑range
    valid_rec = {
        "case_id": 1,
        "question": "Q?",
        "model_output": "A",
        "is_correct": True,
        "expected_pdf": "file.pdf",
        "tokens_est": 5,
        "latency_s": 0.1,
    }
    duplicate_rec = valid_rec.copy()
    duplicate_rec["model_output"] = "B"
    missing_fields = {"case_id": 2, "question": "Q2"}
    out_of_range = valid_rec.copy()
    out_of_range["case_id"] = 101
    lines = [
        json.dumps(valid_rec),
        "THIS IS NOT JSON",
        json.dumps(duplicate_rec),
        json.dumps(missing_fields),
        json.dumps(out_of_range),
    ]
    ck_path.write_text("\n".join(lines))

    runner = load_runner_module()
    stats = runner.inspect_checkpoint(ck_path)

    assert stats.total_lines == 5
    assert stats.valid_records == 1
    assert stats.malformed == [2]
    assert 4 in stats.missing_fields
    assert stats.duplicate_ids == [1]
    assert stats.out_of_range_ids == [101]
    assert stats.missing_ids == list(set(range(1, 101)) - {1})
    assert 1 in stats.record_ids
    assert stats.records[1]["model_output"] == "A"

def test_conflict_detection():
    runner = load_runner_module()
    old = {1: {"case_id": 1, "question": "Q", "model_output": "A"}}
    new = {1: {"case_id": 1, "question": "Q", "model_output": "B"}}
    conflicts = runner._detect_conflicts(old, new)
    assert len(conflicts) == 1
    conflict = conflicts[0]
    assert conflict["case_id"] == 1
    assert conflict["old"]["model_output"] == "A"
    assert conflict["new"]["model_output"] == "B"

def test_main_rejects_incomplete_results(tmp_path, monkeypatch):
    runner = load_runner_module()

    # Tiny dataset with only 3 cases
    dataset = [
        {"case_id": i, "question": f"Q{i}", "expected_answer": f"A{i}", "pdf": "doc.pdf"}
        for i in range(1, 4)
    ]
    dataset_path = tmp_path / "tiny_dataset.json"
    dataset_path.write_text(json.dumps(dataset))
    monkeypatch.setattr(runner, "DATASET_PATH", dataset_path)

    # Empty checkpoint file
    empty_ck = tmp_path / "empty_checkpoint.jsonl"
    empty_ck.touch()
    monkeypatch.setattr(runner, "READ_CHECKPOINT_PATH", empty_ck)

    # Dummy services to avoid heavy init
    class DummyEmbeddingService:
        def __init__(self, *a, **kw):
            pass
    class DummyFaissStore:
        def __init__(self, *a, **kw):
            self.index = types.SimpleNamespace(ntotal=0, search=lambda *a, **k: ([], [[-1]*0]))
        def load_index(self):
            pass
        def get_metadata(self, i):
            return {}
    class DummyLLMService:
        def __init__(self, *a, **kw):
            pass
        def generate_answer(self, query, chunks):
            return {"answer": "dummy", "citations": []}
    monkeypatch.setattr(runner, "EmbeddingService", DummyEmbeddingService)
    monkeypatch.setattr(runner, "FaissStore", DummyFaissStore)
    monkeypatch.setattr(runner, "LLMService", DummyLLMService)
    monkeypatch.setattr(runner, "hybrid_retrieve", lambda query, top_k=8: [])

    # Use a temporary report directory
    def fake_report_dir():
        p = tmp_path / "report"
        p.mkdir()
        return p
    monkeypatch.setattr(runner, "_timestamped_report_dir", fake_report_dir)

    with pytest.raises(RuntimeError) as exc:
        runner.main()
    assert "expected 100 unique case IDs" in str(exc.value)
