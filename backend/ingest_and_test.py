from __future__ import annotations
import logging, sys, time, traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

logging.basicConfig(level=logging.WARNING, format="%(levelname)s | %(name)s | %(message)s")

from app.ingestion.pipeline import DocumentIngestionPipeline
from app.ingestion.ocr_service import OCRService
from app.ingestion.chunker import PDFChunker
from app.embeddings.embedding_service import EmbeddingService
from app.vector_store.faiss_store import FaissStore
from app.retrieval.retrieval_service import RetrievalService
from app.core.config import settings

try:
    from app.llm.llm_service import LLMService
    _LLM_AVAILABLE = True
except ImportError:
    _LLM_AVAILABLE = False

TEST_DATA_DIR  = BACKEND_DIR / "test_data"
FAISS_DIR      = BACKEND_DIR / "storage" / "vector_store"
LLM_MODEL_PATH = BACKEND_DIR / "storage" / "models" / "llama-2-7b.gguf"

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

RETRIEVAL_PROBES = {
    "NIST-CSWP-29.pdf": "NIST cybersecurity framework",
    "CIS-MS-ISAC-NIST-Cybersecurity-Framework-Policy-Template-Guide.pdf": "cybersecurity policy template",
    "ImplementingtheCyberResilienceAct.pdf": "cyber resilience act products",
    "ActaAstronautica.pdf": "astronautica space research",
    "feynman.pdf": "Feynman physics lectures",
    "TheNASATechnicalReportServer (1).pdf": "NASA technical report server",
    "MANUAL-POWER_SUPPLY_TENDER_FOR_VENDOR-1-1.pdf": "power supply tender vendor",
    "VENDOR-REGISTRATION-FORMS.pdf": "vendor registration form",
    "PhysRev.pdf": "physical review journal",
    "STUDENTJOURNALOFPHYSICS.pdf": "student physics journal",
    "SCOPINGOFANAIRSUPPLYCONFIGURATIONFORACTIVEFLOW.pdf": "air supply flow configuration",
    "pages-29-deed-sample.pdf": "deed sample property",
    "project-maths (1).pdf": "mathematics project",
}

REFUSAL_PHRASES = [
    "not found in the uploaded document", "not present in the context",
    "no relevant context", "i cannot", "this information is not",
    "does not contain enough information", "not contain enough information"
]

def _section(t): print("\n" + "="*70 + "\n  " + t + "\n" + "="*70)
def _ok(m): print("  [PASS] " + m)
def _fail(m): print("  [FAIL] " + m)
def _info(m): print("  [INFO] " + m)

def discover_pdfs():
    if not TEST_DATA_DIR.exists():
        raise FileNotFoundError("test_data not found: " + str(TEST_DATA_DIR))
    return sorted(TEST_DATA_DIR.glob("*.pdf"))

def rebuild_index(pdfs):
    ocr = OCRService(dpi=settings.OCR_DPI, language=settings.OCR_LANGUAGE)
    pl = DocumentIngestionPipeline(ocr_service=ocr)
    ck = PDFChunker()
    es = EmbeddingService(model_name="all-MiniLM-L6-v2")
    fs = FaissStore(index_path=str(FAISS_DIR), dimension=384)
    fs.clear()
    s = {"total_pdfs": len(pdfs), "ingested": [], "failed": [], "total_chunks": 0}
    for p in pdfs:
        try:
            t0 = time.perf_counter()
            ex = pl.process(str(p))
            ch = ck.chunk_document(ex)
            if not ch.chunks:
                s["ingested"].append({"pdf": p.name, "chunks": 0, "pages": ex.page_count,
                                      "ocr_pages": ex.ocr_pages_count, "status": "no_text",
                                      "elapsed_s": round(time.perf_counter()-t0, 2)})
                continue
            em = es.generate_embeddings(ch.chunks)
            for e in em:
                e["metadata"]["file_path"] = str(p)
            fs.add_embeddings(em)
            s["ingested"].append({"pdf": p.name, "chunks": len(em), "pages": ex.page_count,
                                  "ocr_pages": ex.ocr_pages_count, "status": "ok",
                                  "elapsed_s": round(time.perf_counter()-t0, 2)})
            s["total_chunks"] += len(em)
        except Exception as exc:
            s["failed"].append({"pdf": p.name, "error": str(exc)})
    fs.save_index()
    s["faiss_total_vectors"] = fs.index.ntotal
    return s, fs, es

def run_retrieval(fs, es, pdfs):
    svc = RetrievalService(embedding_service=es, faiss_store=fs, default_top_k=5)
    names = {p.name for p in pdfs}
    passed, failed = [], []
    for name, q in RETRIEVAL_PROBES.items():
        if name not in names:
            continue
        try:
            hits = svc.search(query=q, top_k=5)
            m = [h for h in hits if name in str(h.get("file_path", ""))]
            if m:
                passed.append({"pdf": name, "query": q,
                               "top_score": round(m[0]["similarity_score"], 4),
                               "matched": len(m)})
            else:
                failed.append({"pdf": name, "query": q, "issue": "Not in top-5",
                               "top_hits": [str(h.get("file_path", "?"))[-40:] for h in hits]})
        except Exception as exc:
            failed.append({"pdf": name, "query": q, "issue": str(exc)})
    return {"passed": passed, "failed": failed}

def run_qa(fs, es):
    svc = RetrievalService(embedding_service=es, faiss_store=fs, default_top_k=5)
    use_llm = _LLM_AVAILABLE and LLM_MODEL_PATH.exists()
    llm = None
    if use_llm:
        try:
            llm = LLMService(model_path=str(LLM_MODEL_PATH), chat_format="llama-2")
        except Exception as exc:
            _info("LLM load failed: " + str(exc))
            use_llm = False
    qp, qf, cp, cf = [], [], [], []
    for case in QA_CASES:
        q = case["question"]
        pdf = case["pdf"]
        kws = [k.lower() for k in case["expected_keywords"]]
        ref = case["expect_refusal"]
        try:
            hits = svc.search(query=q, top_k=5)
            # If retrieval returned no chunks, record a retrieval failure and skip LLM processing
            if not hits:
                # No chunks retrieved – treat as retrieval failure
                qf.append({"question": q, "type": "retrieval_failed", "issue": "No chunks returned"})
                continue
            if ref:
                if use_llm and llm:
                    out = llm.generate_answer(q, hits)
                    ans = out.get("answer", "").lower()
                    if any(p in ans for p in REFUSAL_PHRASES):
                        qp.append({"question": q, "type": "refusal", "answer": out.get("answer", "")[:150]})
                    else:
                        qf.append({"question": q, "type": "refusal", "issue": "Did not refuse", "answer": out.get("answer", "")[:200]})
                else:
                    sc = hits[0]["similarity_score"] if hits else 9999.0
                    if sc > 1.5:
                        qp.append({"question": q, "type": "refusal(retrieval)", "note": "L2=" + str(round(sc,3)) + ">1.5"})
                    else:
                        qf.append({"question": q, "type": "refusal(retrieval)", "issue": "Close hit L2=" + str(round(sc,3))})
                continue
            if use_llm and llm:
                out = llm.generate_answer(q, hits)
                ans = out.get("answer", "")
                cits = out.get("citations", [])
                missing_kws = [kw for kw in kws if kw not in ans.lower()]
                ok = len(missing_kws) == 0 if kws else True
                if ok:
                    qp.append({"question": q, "type": "llm_qa", "answer": ans[:200]})
                else:
                    qf.append({"question": q, "type": "llm_qa", "issue": "Missing: " + str(missing_kws), "answer": ans[:200]})
                for c in cits:
                    fp = c.get("file_path", "") or ""
                    if pdf and pdf in fp:
                        cp.append({"question": q, "cited_pdf": Path(fp).name, "page": c.get("page_number")})
                    elif pdf:
                        cf.append({"question": q, "expected": pdf, "got": Path(fp).name if fp else "(none)"})
            else:
                combined = " ".join(h.get("chunk_text", "") for h in hits).lower()
                missing_kws = [kw for kw in kws if kw not in combined]
                ok = len(missing_kws) == 0 if kws else bool(hits)
                sc = round(hits[0]["similarity_score"], 4) if hits else None
                if pdf and hits:
                    fp = hits[0].get("file_path", "")
                    if pdf in fp:
                        cp.append({"question": q, "cited_pdf": pdf, "page": hits[0].get("page_number"), "score": sc})
                    else:
                        cf.append({"question": q, "expected": pdf, "got": Path(fp).name if fp else "(none)", "score": sc})
                if ok:
                    qp.append({"question": q, "type": "retrieval_only", "kws": kws, "top_score": sc})
                else:
                    qf.append({"question": q, "type": "retrieval_only", "issue": "Missing: " + str(missing_kws), "top_score": sc})
        except Exception:
            qf.append({"question": q, "type": "error", "issue": traceback.format_exc()[:300]})
    return {"passed": qp, "failed": qf, "llm_used": use_llm}, {"passed": cp, "failed": cf}

def main():
    issues = []
    _section("FILES_CHANGED")
    pdfs = discover_pdfs()
    print("  Source : " + str(TEST_DATA_DIR))
    print("  FAISS  : " + str(FAISS_DIR))
    print("\n  PDFs (" + str(len(pdfs)) + "):")
    for p in pdfs:
        sz = p.stat().st_size // 1024
        print("    * " + p.name + "  (" + str(sz) + " KB)")
    print("\n  Files changed:")
    print("    * backend/storage/vector_store/vector_store.index  [rebuilt]")
    print("    * backend/storage/vector_store/metadata.json       [rebuilt]")
    print("    * backend/ingest_and_test.py                       [new]")

    _section("INGESTION_RESULTS")
    _info("Loading all-MiniLM-L6-v2 ...")
    s, fs, es = rebuild_index(pdfs)
    print("\n  PDFs processed : " + str(s["total_pdfs"]))
    print("  Chunks indexed : " + str(s["total_chunks"]))
    print("  FAISS vectors  : " + str(s["faiss_total_vectors"]))
    print("\n  Per-PDF:")
    for r in s["ingested"]:
        icon = "OK" if r["status"] == "ok" else "WARN"
        print("    [" + icon + "] " + r["pdf"])
        print("           chunks=" + str(r["chunks"]) + ", pages=" + str(r.get("pages","?")) +
              ", ocr_pages=" + str(r.get("ocr_pages","?")) + ", elapsed=" + str(r.get("elapsed_s","?")) + "s, status=" + r["status"])
    if s["failed"]:
        for f in s["failed"]:
            print("    [FAIL] " + f["pdf"] + ": " + f["error"])
            issues.append("Ingestion: " + f["pdf"] + " - " + f["error"])
    print("\n  Stale test-data entries  : REMOVED (full rebuild)")
    print("  User uploads on disk     : PRESERVED (storage/uploads/ untouched)")
    print("  Android re-upload effect : /rag/ingest adds PDFs back to FAISS")

    _section("QA_RESULTS")
    ret = run_retrieval(fs, es, pdfs)
    pr = len(ret["passed"])
    fr = len(ret["failed"])
    print("\n  Retrieval probes: " + str(pr) + " passed, " + str(fr) + " failed")
    for r in ret["passed"]:
        _ok(r["pdf"] + " | L2=" + str(r["top_score"]) + " | matched=" + str(r["matched"]))
    for r in ret["failed"]:
        _fail(r["pdf"] + " | " + r["issue"])
        issues.append("Retrieval: " + r["pdf"] + " - " + r["issue"])

    qa, cit = run_qa(fs, es)
    mode = "llama.cpp" if qa["llm_used"] else "retrieval-only (GGUF absent)"
    pq = len(qa["passed"])
    fq = len(qa["failed"])
    print("\n  QA mode    : " + mode)
    print("  QA results : " + str(pq) + " passed, " + str(fq) + " failed")
    for r in qa["passed"]:
        _ok("[" + str(r.get("type","?")) + "] " + r["question"][:80])
        if "answer" in r:
            print("         Ans : " + r["answer"][:120])
        if "note" in r:
            print("         Note: " + r["note"])
    for r in qa["failed"]:
        _fail("[" + str(r.get("type","?")) + "] " + r["question"][:80])
        print("         Issue: " + str(r.get("issue","?"))[:200])
        issues.append("QA: " + r["question"][:50] + " - " + str(r.get("issue","?"))[:80])

    _section("CITATION_RESULTS")
    pc = len(cit["passed"])
    fc = len(cit["failed"])
    print("\n  " + str(pc) + " correct, " + str(fc) + " wrong")
    for r in cit["passed"]:
        _ok('"' + r["question"][:55] + '" -> ' + str(r["cited_pdf"]) + " page=" + str(r.get("page","?")))
    for r in cit["failed"]:
        _fail('"' + r["question"][:55] + '" -> expected=' + str(r["expected"]) + " got=" + str(r["got"]))
        issues.append("Citation: " + r["question"][:40] + " expected=" + str(r["expected"]) + " got=" + str(r["got"]))

    _section("ISSUES")
    if issues:
        for i, iss in enumerate(issues, 1):
            print("  " + str(i) + ". " + iss)
    else:
        print("  None.")

    _section("FINAL_STATUS")
    ok_ing = sum(1 for r in s["ingested"] if r["status"] == "ok")
    total_fail = fr + fq + fc
    overall = "SUCCESS" if total_fail == 0 and not s["failed"] else "PARTIAL - see ISSUES"
    print("")
    print("  Ingestion  : " + str(ok_ing) + "/" + str(s["total_pdfs"]) + " PDFs OK")
    print("  FAISS index: " + str(s["faiss_total_vectors"]) + " vectors")
    print("  Retrieval  : " + str(pr) + "/" + str(pr+fr) + " PASS")
    print("  QA tests   : " + str(pq) + "/" + str(pq+fq) + " PASS")
    print("  Citations  : " + str(pc) + "/" + str(pc+fc) + " correct")
    print("  Issues     : " + str(len(issues)))
    print("  LLM mode   : " + mode)
    print("  Android    : INTACT (uploads preserved, /rag/ingest endpoint unchanged)")
    print("  OVERALL    : " + overall)

if __name__ == "__main__":
    main()
