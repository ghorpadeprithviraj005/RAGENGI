import time, os, sys, json
from pathlib import Path

BACKEND_DIR = Path('d:/RAGENG/files (1)/backend').resolve()
sys.path.insert(0, str(BACKEND_DIR))

from app.embeddings.embedding_service import EmbeddingService
from app.vector_store.faiss_store import FaissStore
from app.retrieval.retrieval_service import RetrievalService
from app.llm.llm_service import LLMService

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

REFUSAL_PHRASES = ["not found in the uploaded document", "not present in the context",
                   "no relevant context", "i cannot", "this information is not", "does not contain enough information"]

def main():
    faiss_dir = BACKEND_DIR / "storage" / "vector_store"
    es = EmbeddingService(model_name="all-MiniLM-L6-v2")
    fs = FaissStore(index_path=str(faiss_dir), dimension=384)
    try: fs.load_index()
    except: pass
    rs = RetrievalService(embedding_service=es, faiss_store=fs, default_top_k=5)
    
    llm_path = BACKEND_DIR / "storage" / "models" / "llama-2-7b.gguf"
    llm = LLMService(model_path=str(llm_path), chat_format="llama-2")
    
    failed_cases = []
    
    for case in QA_CASES:
        q = case["question"]
        expected_pdf = case["pdf"]
        kws = [k.lower() for k in case["expected_keywords"]]
        refusal = case["expect_refusal"]
        
        hits = rs.search(query=q, top_k=5)
        out = llm.generate_answer(q, hits)
        ans = out.get("answer", "").lower()
        
        is_correct = False
        if refusal:
            if any(p in ans for p in REFUSAL_PHRASES):
                is_correct = True
        else:
            if all(kw in ans for kw in kws):
                is_correct = True
        
        if not is_correct:
            failed_cases.append({
                "question": q,
                "retrieved_chunks": [h.get("chunk_text", "") for h in hits],
                "llama_answer": out.get("answer", ""),
                "expected": "Refusal" if refusal else f"Keywords: {kws}"
            })
            
    print(json.dumps(failed_cases, indent=2))

if __name__ == "__main__":
    main()
