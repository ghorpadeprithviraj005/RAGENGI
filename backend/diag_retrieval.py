"""Diagnostic script: retrieval-level check for all 14 QA cases."""
import sys
import warnings
warnings.filterwarnings("ignore")

sys.path.insert(0, "d:/RAGENG/files (1)/backend")

from app.embeddings.embedding_service import EmbeddingService
from app.vector_store.faiss_store import FaissStore
from app.retrieval.retrieval_service import RetrievalService
from pathlib import Path

faiss_dir = "d:/RAGENG/files (1)/backend/storage/vector_store"
es = EmbeddingService(model_name="all-MiniLM-L6-v2")
fs = FaissStore(index_path=faiss_dir, dimension=384)
rs = RetrievalService(embedding_service=es, faiss_store=fs, default_top_k=5)

QA_CASES = [
    {"pdf": "NIST-CSWP-29.pdf", "question": "What are the five core functions of the NIST Cybersecurity Framework?", "expected_keywords": ["identify", "protect", "detect", "respond", "recover"]},
    {"pdf": "CIS-MS-ISAC-NIST-Cybersecurity-Framework-Policy-Template-Guide.pdf", "question": "What organization published the Cybersecurity Framework Policy Template Guide?", "expected_keywords": ["cis", "ms-isac"]},
    {"pdf": "ImplementingtheCyberResilienceAct.pdf", "question": "What does the Cyber Resilience Act regulate?", "expected_keywords": ["product", "cybersecurity"]},
    {"pdf": "ActaAstronautica.pdf", "question": "What is the main topic covered in Acta Astronautica?", "expected_keywords": ["space"]},
    {"pdf": "feynman.pdf", "question": "Who authored the Feynman lectures on physics?", "expected_keywords": ["feynman"]},
    {"pdf": "TheNASATechnicalReportServer (1).pdf", "question": "What is the NASA Technical Report Server used for?", "expected_keywords": ["nasa", "report"]},
    {"pdf": "MANUAL-POWER_SUPPLY_TENDER_FOR_VENDOR-1-1.pdf", "question": "What type of document is the power supply tender manual?", "expected_keywords": ["tender", "supply"]},
    {"pdf": "VENDOR-REGISTRATION-FORMS.pdf", "question": "What information is requested on a vendor registration form?", "expected_keywords": ["vendor", "registration"]},
    {"pdf": "PhysRev.pdf", "question": "What field of science does PhysRev primarily cover?", "expected_keywords": ["physics"]},
    {"pdf": "STUDENTJOURNALOFPHYSICS.pdf", "question": "What type of journal is the Student Journal of Physics?", "expected_keywords": ["student", "physics"]},
    {"pdf": "SCOPINGOFANAIRSUPPLYCONFIGURATIONFORACTIVEFLOW.pdf", "question": "What engineering topic is addressed in the air supply configuration document?", "expected_keywords": ["air", "flow"]},
    {"pdf": "pages-29-deed-sample.pdf", "question": "What legal document type is the deed sample?", "expected_keywords": ["deed"]},
    {"pdf": None, "question": "How do I bake a pepperoni pizza?", "expected_keywords": [], "expect_refusal": True},
    {"pdf": None, "question": "What is the CEO personal home address?", "expected_keywords": [], "expect_refusal": True},
]

print("--- Retrieval Diagnostics ---")
print("Total FAISS vectors: " + str(fs.index.ntotal))
print()

for case in QA_CASES:
    q = case["question"]
    pdf = case.get("pdf")
    kws = case.get("expected_keywords", [])
    refusal = case.get("expect_refusal", False)

    hits = rs.search(query=q, top_k=5)
    top_files = [Path(h.get("file_path", "")).name for h in hits]
    top_scores = [round(h.get("similarity_score", 0), 3) for h in hits]

    if refusal:
        print("[REFUSAL] " + q[:60])
        print("  Top hits: " + str(list(zip(top_files, top_scores))))
        print("  -> L2 distance of top result: " + str(top_scores[0] if top_scores else "N/A"))
    else:
        in_top5 = pdf in top_files
        combined = " ".join(h.get("chunk_text", "") for h in hits).lower()
        kws_found = [kw for kw in kws if kw in combined]
        kws_missing = [kw for kw in kws if kw not in combined]
        status = "PASS" if in_top5 else "MISS"
        kw_status = "OK" if not kws_missing else ("MISSING=" + str(kws_missing))
        print("[" + status + "] " + str(pdf[:50]))
        print("  Q: " + q[:80])
        print("  Top files+scores: " + str(list(zip(top_files, top_scores))))
        print("  Keyword check: " + kw_status)
        if hits:
            clean_chunk = hits[0].get("chunk_text", "")[:200].encode("ascii", "replace").decode("ascii")
            print("  Top chunk text: " + clean_chunk)
    print()
