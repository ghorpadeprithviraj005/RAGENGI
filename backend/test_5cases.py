"""Test only the 3 most-likely-failing cases with the LLM (post top_k=20 fix)."""
import sys, warnings, os, time
warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "d:/RAGENG/files (1)/backend")

from pathlib import Path
from app.embeddings.embedding_service import EmbeddingService
from app.vector_store.faiss_store import FaissStore
from app.retrieval.retrieval_service import RetrievalService
from app.llm.llm_service import LLMService

BACKEND_DIR = Path("d:/RAGENG/files (1)/backend")

CASES = [
    {"name": "NIST",   "pdf": "NIST-CSWP-29.pdf",       "question": "What are the five core functions of the NIST Cybersecurity Framework?", "kws": ["identify","protect","detect","respond","recover"]},
    {"name": "CIS",    "pdf": "CIS-MS-ISAC-NIST-Cybersecurity-Framework-Policy-Template-Guide.pdf", "question": "What organization published the Cybersecurity Framework Policy Template Guide?", "kws": ["cis","ms-isac"]},
    {"name": "CRA",    "pdf": "ImplementingtheCyberResilienceAct.pdf", "question": "What does the Cyber Resilience Act regulate?", "kws": ["product","cybersecurity"]},
    {"name": "Acta",   "pdf": "ActaAstronautica.pdf",    "question": "What is the main topic covered in Acta Astronautica?", "kws": ["space"]},
    {"name": "Manual", "pdf": "MANUAL-POWER_SUPPLY_TENDER_FOR_VENDOR-1-1.pdf", "question": "What type of document is the power supply tender manual?", "kws": ["tender","supply"]},
]

faiss_dir = BACKEND_DIR / "storage" / "vector_store"
es = EmbeddingService(model_name="all-MiniLM-L6-v2")
fs = FaissStore(index_path=str(faiss_dir), dimension=384)
fs.load_index()
rs = RetrievalService(embedding_service=es, faiss_store=fs, default_top_k=5)
llm = LLMService(model_path=str(BACKEND_DIR / "storage" / "models" / "llama-2-7b.gguf"), chat_format="llama-2", max_tokens=600)

print("=== TARGETED 5-CASE LLM TEST (top_k=20 with active_filename reorder) ===")
passed = 0
for c in CASES:
    hits = rs.search(query=c["question"], top_k=40)
    t0 = time.time()
    out = llm.generate_answer(c["question"], hits)
    lat = time.time() - t0
    ans = out["answer"].lower()
    missing = [kw for kw in c["kws"] if kw not in ans]
    status = "PASS" if not missing else "FAIL"
    if not missing:
        passed += 1
    usage = out.get("usage", {})
    p_tokens = usage.get("prompt_tokens", "N/A")
    c_tokens = usage.get("completion_tokens", "N/A")
    f_reason = out.get("finish_reason", "N/A")
    print(f"[{status}] {c['name']} ({lat:.1f}s) | Prompt Tokens: {p_tokens}, Completion Tokens: {c_tokens}, Finish Reason: {f_reason}")
    print(f"  Answer: {out['answer']}")
    if missing:
        print(f"  MISSING: {missing}")
    print()

print(f"Result: {passed}/{len(CASES)} passed")
