import json
import pytest
from pathlib import Path

BACKEND_DIR = Path('d:/RAGENG/files (1)/backend').resolve()
TEST_DATA = BACKEND_DIR / 'test_data'
CORRECTED_DS_PATH = BACKEND_DIR / 'scratch' / 'corrected_dataset_160_v2.json'


@pytest.fixture
def dataset():
    assert CORRECTED_DS_PATH.exists(), "Corrected dataset file does not exist"
    data = json.loads(CORRECTED_DS_PATH.read_text(encoding='utf-8'))
    return data


def test_dataset_count_and_uniqueness(dataset):
    """Ensure exactly 160 records, unique case IDs, and no duplicate questions."""
    assert len(dataset) == 160

    case_ids = [c["case_id"] for c in dataset]
    assert len(set(case_ids)) == 160
    assert sorted(case_ids) == list(range(1, 161))

    questions = [c["question"].strip() for c in dataset]
    assert len(set(questions)) == 160, f"Found {160 - len(set(questions))} duplicate questions"


def test_dataset_schema_conformance(dataset):
    """Ensure all required schema fields are present and correctly typed."""
    required_fields = {
        "case_id": int,
        "question": str,
        "answer": str,
        "expected_keywords": list,
        "expect_refusal": bool,
        "is_answerable": bool,
        "provenance": str
    }
    for item in dataset:
        for field, f_type in required_fields.items():
            assert field in item, f"Case {item.get('case_id')} missing field {field}"
            assert isinstance(item[field], f_type), f"Case {item['case_id']} field {field} invalid type"


def test_refusal_cases_integrity(dataset):
    """Verify out-of-domain refusal cases have expect_refusal=True and pdf=None."""
    refusals = [c for c in dataset if c["expect_refusal"]]
    assert len(refusals) == 5
    for r in refusals:
        assert r["pdf"] is None
        assert r["is_answerable"] is False
        assert len(r["page_numbers"]) == 0


def test_document_grounding_and_provenance(dataset):
    """Verify that all answerable cases reference existing PDFs in test_data."""
    available_pdfs = {p.name.lower() for p in TEST_DATA.glob('*.pdf')}
    answerable = [c for c in dataset if c.get("is_answerable", True) and not c["expect_refusal"]]
    assert len(answerable) == 148  # 155 minus 7 documented noise cases

    for c in answerable:
        pdf_name = c["pdf"]
        assert pdf_name is not None
        assert pdf_name.lower() in available_pdfs, f"PDF {pdf_name} not found in test_data"
        assert len(c["answer"]) > 0
        assert len(c["expected_keywords"]) > 0
        assert len(c["page_numbers"]) > 0
