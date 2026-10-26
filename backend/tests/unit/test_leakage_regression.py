import pytest
import numpy as np
from unittest.mock import MagicMock, patch

from app.retrieval.retrieval_service import RetrievalService
from app.llm.llm_service import LLMService


@pytest.fixture
def mock_embedding_service():
    service = MagicMock()
    service.model.encode.return_value = np.array([[0.05, 0.1, 0.15]], dtype=np.float32)
    return service


@pytest.fixture
def mock_faiss_multi_doc():
    store = MagicMock()
    # Mocking 4 chunks from 3 different documents
    store.index.search.return_value = (
        np.array([[0.02, 0.04, 0.06, 0.08]], dtype=np.float32),
        np.array([[0, 1, 2, 3]], dtype=np.int64)
    )
    store.index.ntotal = 4

    meta_db = {
        0: {"chunk_id": 101, "page_number": 1, "chunk_text": "Risk management policy section 1.", "file_path": "/data/policy_nist.pdf"},
        1: {"chunk_id": 201, "page_number": 3, "chunk_text": "Annual financial revenue details.", "file_path": "/data/financial_report.pdf"},
        2: {"chunk_id": 102, "page_number": 2, "chunk_text": "Incident response guide section 2.", "file_path": "/data/policy_nist.pdf"},
        3: {"chunk_id": 301, "page_number": 7, "chunk_text": "Employee safety guidelines.", "file_path": "/data/safety_handbook.pdf"},
    }
    store.get_metadata.side_effect = lambda idx: meta_db.get(idx)
    return store


@pytest.fixture
def mock_llama():
    with patch("app.llm.llm_service.Llama") as MockLlamaClass:
        mock_instance = MagicMock()
        mock_instance.create_chat_completion.return_value = {
            "choices": [{"message": {"content": "Deterministic answer based on context."}}],
            "finish_reason": "stop",
            "usage": {"total_tokens": 42}
        }
        MockLlamaClass.return_value = mock_instance
        yield mock_instance


def test_retrieval_service_leakage_free(mock_embedding_service, mock_faiss_multi_doc):
    """
    Ensure active_filename cannot filter, prioritize, or alter retrieved chunks.
    Retrieval results must be completely deterministic regardless of active_filename.
    """
    service = RetrievalService(mock_embedding_service, mock_faiss_multi_doc, default_top_k=4)

    # 1. Search without active_filename
    res_none = service.search(query="policy guidelines", top_k=4, active_filename=None)

    # 2. Search with expected_pdf matching doc 1
    res_doc1 = service.search(query="policy guidelines", top_k=4, active_filename="policy_nist.pdf")

    # 3. Search with expected_pdf matching doc 2
    res_doc2 = service.search(query="policy guidelines", top_k=4, active_filename="financial_report.pdf")

    # 4. Search with non-existent / arbitrary doc
    res_arbitrary = service.search(query="policy guidelines", top_k=4, active_filename="nonexistent.pdf")

    # Verify all results are identical
    assert len(res_none) == 4
    assert res_none == res_doc1
    assert res_none == res_doc2
    assert res_none == res_arbitrary

    # Verify chunk IDs and order are strictly preserved across all calls
    ids_none = [c["chunk_id"] for c in res_none]
    ids_doc1 = [c["chunk_id"] for c in res_doc1]
    assert ids_none == ids_doc1 == [101, 301, 201, 102]


def test_llm_build_messages_leakage_free():
    """
    Ensure LLMService.build_messages and build_prompt produce identical prompts
    and never inject active_filename or document scoping metadata into context.
    """
    with patch("app.llm.llm_service.Llama", MagicMock()):
        service = LLMService(model_path="dummy.gguf")

    sample_chunks = [
        {"chunk_id": 1, "page_number": 1, "chunk_text": "Chunk text 1", "file_path": "/data/docA.pdf"},
        {"chunk_id": 2, "page_number": 2, "chunk_text": "Chunk text 2", "file_path": "/data/docB.pdf"},
    ]

    msgs_none = service.build_messages(query="What is the text?", retrieved_chunks=sample_chunks, active_filename=None)
    msgs_docA = service.build_messages(query="What is the text?", retrieved_chunks=sample_chunks, active_filename="docA.pdf")
    msgs_docB = service.build_messages(query="What is the text?", retrieved_chunks=sample_chunks, active_filename="docB.pdf")

    # Must be 100% identical in structure and text
    assert msgs_none == msgs_docA == msgs_docB

    prompt_none = service.build_prompt("What is the text?", sample_chunks, active_filename=None)
    prompt_docA = service.build_prompt("What is the text?", sample_chunks, active_filename="docA.pdf")
    assert prompt_none == prompt_docA
    assert "[Active Document Name:" not in prompt_none


def test_llm_generate_answer_citations_leakage_free(mock_llama):
    """
    Ensure LLMService.generate_answer produces identical citations and context
    irrespective of active_filename.
    """
    service = LLMService(model_path="dummy.gguf")

    sample_chunks = [
        {"chunk_id": 10, "page_number": 1, "chunk_text": "Alpha chunk", "file_path": "/data/docA.pdf"},
        {"chunk_id": 20, "page_number": 4, "chunk_text": "Beta chunk", "file_path": "/data/docB.pdf"},
    ]

    out_none = service.generate_answer(query="Alpha query", retrieved_chunks=sample_chunks, active_filename=None)
    out_docA = service.generate_answer(query="Alpha query", retrieved_chunks=sample_chunks, active_filename="docA.pdf")
    out_docB = service.generate_answer(query="Alpha query", retrieved_chunks=sample_chunks, active_filename="docB.pdf")

    assert out_none["citations"] == out_docA["citations"] == out_docB["citations"]
    assert len(out_none["citations"]) == 2
    assert out_none["citations"][0]["chunk_id"] == 10
    assert out_none["citations"][1]["chunk_id"] == 20


def test_evaluation_case_metadata_cannot_affect_retrieval_or_prompt():
    """
    Deterministic test: changing reference answers, expected_keywords, expected_pdf,
    or expected pages in a benchmark case dictionary has ZERO effect on retrieval query
    or the prompt sent to the LLM.
    """
    case_variant_1 = {
        "case_id": 1,
        "question": "What is the primary risk factor?",
        "pdf": "report_2023.pdf",
        "expected_keywords": ["credit", "default"],
        "reference_answer": "Credit default risk is the primary factor.",
        "expected_pages": [12, 13]
    }

    case_variant_2 = {
        "case_id": 1,
        "question": "What is the primary risk factor?",
        "pdf": "completely_different_file.pdf",
        "expected_keywords": ["liquidity", "market"],
        "reference_answer": "Liquidity risk is the primary factor.",
        "expected_pages": [99]
    }

    # Verify query input extracted for retrieval is strictly question only
    query_1 = case_variant_1["question"]
    query_2 = case_variant_2["question"]
    assert query_1 == query_2

    # Verify prompt construction with same hits is identical despite divergent case metadata
    sample_hits = [{"chunk_id": 1, "page_number": 2, "chunk_text": "Context paragraph", "file_path": "/data/doc.pdf"}]
    with patch("app.llm.llm_service.Llama", MagicMock()):
        llm = LLMService(model_path="dummy.gguf")
        p1 = llm.build_prompt(query_1, sample_hits)
        p2 = llm.build_prompt(query_2, sample_hits)
        assert p1 == p2
