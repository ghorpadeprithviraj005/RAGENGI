"""Quick diagnostic: run all 14 QA cases without full LLM inference - just check retrieval for keyword presence.
This tells us which cases are retrieval-recoverable vs generation issues."""
import sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, "d:/RAGENG/files (1)/backend")

from app.embeddings.embedding_service import EmbeddingService
from app.vector_store.faiss_store import FaissStore
from app.retrieval.retrieval_service import RetrievalService
from pathlib import Path
import os

BACKEND_DIR = Path("d:/RAGENG/files (1)/backend")

QA_CASES = [
    {"pdf": "NIST-CSWP-29.pdf", "question": "What are the five core functions of the NIST Cybersecurity Framework?", "expected_keywords": ["identify", "protect", "detect", "respond", "recover"], "expect_refusal": False},
    {"pdf": "CIS-MS-ISAC-NIST-Cybersecurity-Framework-Policy-Template-Guide.pdf", "question": "What organization published the Cybersecurity Framework Policy Template Guide?", "expected_keywords": ["cis", "ms-isac"], "expect_refusal": False},
    {"pdf": "ImplementingtheCyberResilienceAct.pdf", "question": "What does the Cyber Resilience Act regulate?", "expected_keywords": ["product", "cybersecurity"], "expect_refusal": False},
    {"pdf": "ActaAstronautica.pdf", "question": "What is the main topic covered in Acta Astronautica?", "expected_keywords": ["space"], "expect_refusal": False},
    {"pdf": "feynman.pdf", "question": "Who authored the Feynman lectures on physics?", "expected_keywords": ["feynman"], "expect_refusal": False},
    {"pdf": "TheNASATechnicalReportServer (1).pdf", "question": "What is the NASA Technical Report Server used for?", "expected_keywords": ["nasa", "report"], "expect_refusal": False},
    {"pdf": "MANUAL-POWER_SUPPLY_TENDER_FOR_VENDOR-1-1.pdf", "question": "What type of document is the power supply tender manual?", "expected_keywords": ["tender", "supply"], "expect_refusal": False},
    {"pdf": "VENDOR-REGISTRATION-FORMS.pdf", "question": "What information is requested on a vendor registration form?", "expected_keywords": ["vendor", "registration"], "expect_refusal": False},
    {"pdf": "PhysRev.pdf", "question": "What field of science does PhysRev primarily cover?", "expected_keywords": ["physics"], "expect_refusal": False},
    {"pdf": "STUDENTJOURNALOFPHYSICS.pdf", "question": "What type of journal is the Student Journal of Physics?", "expected_keywords": ["student", "physics"], "expect_refusal": False},
    {"pdf": "SCOPINGOFANAIRSUPPLYCONFIGURATIONFORACTIVEFLOW.pdf", "question": "What engineering topic is addressed in the air supply configuration document?", "expected_keywords": ["air", "flow"], "expect_refusal": False},
    {"pdf": "pages-29-deed-sample.pdf", "question": "What legal document type is the deed sample?", "expected_keywords": ["deed"], "expect_refusal": False},
    {"pdf": None, "question": "How do I bake a pepperoni pizza?", "expected_keywords": [], "expect_refusal": True},
    {"pdf": None, "question": "What is the CEO personal home address?", "expected_keywords": [], "expect_refusal": True},
]

faiss_dir = BACKEND_DIR / "storage" / "vector_store"
es = EmbeddingService(model_name="all-MiniLM-L6-v2")
fs = FaissStore(index_path=str(faiss_dir), dimension=384)
try:
    fs.load_index()
except:
    pass
rs = RetrievalService(embedding_service=es, faiss_store=fs, default_top_k=5)

print(f"FAISS index: {fs.index.ntotal} vectors")
print("="*70)
print("RETRIEVAL DIAGNOSTIC (top_k=20, check keyword coverage in retrieved text)")
print("="*70)

for case in QA_CASES:
    q = case["question"]
    pdf = case["pdf"]
    kws = [k.lower() for k in case["expected_keywords"]]
    refusal = case["expect_refusal"]

    if refusal:
        hits = rs.search(query=q, top_k=5)
        top_dist = hits[0]["similarity_score"] if hits else None
        print(f"[REFUSAL] {q[:60]}")
        print(f"  max_dist={top_dist} | hits={len(hits)}")
        print()
        continue

    # Use top_k=20, prioritize active doc
    hits20 = rs.search(query=q, top_k=20)
    
    # Reorder: active doc first
    if pdf:
        doc_hits = [h for h in hits20 if pdf in str(h.get("file_path", ""))]
        other_hits = [h for h in hits20 if pdf not in str(h.get("file_path", ""))]
        ordered = doc_hits + other_hits
    else:
        ordered = hits20
    
    # Take top 5 after reordering
    top5 = ordered[:5]
    
    # Build context string from top-5
    context = " ".join(h.get("chunk_text", "").lower() for h in top5)
    
    missing = [kw for kw in kws if kw not in context]
    status = "PASS" if not missing else "FAIL"
    
    top_files = [(os.path.basename(h.get("file_path", "")), round(h["similarity_score"], 3)) for h in top5]
    print(f"[{status}] {pdf}")
    print(f"  Q: {q[:70]}")
    print(f"  Top-5 files (after reorder): {top_files}")
    if missing:
        print(f"  MISSING KEYWORDS: {missing}")
    else:
        print(f"  All keywords present in context: {kws}")
    print()
