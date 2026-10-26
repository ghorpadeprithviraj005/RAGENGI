import sys
sys.path.insert(0, "d:/RAGENG/files (1)/backend")
from app.embeddings.embedding_service import EmbeddingService
from app.vector_store.faiss_store import FaissStore
from app.retrieval.retrieval_service import RetrievalService

es = EmbeddingService(model_name="all-MiniLM-L6-v2")
fs = FaissStore(index_path="d:/RAGENG/files (1)/backend/storage/vector_store", dimension=384)
fs.load_index()
rs = RetrievalService(embedding_service=es, faiss_store=fs, default_top_k=5)

for pdf, q, kws in [
    ("ImplementingtheCyberResilienceAct.pdf", "What does the Cyber Resilience Act regulate?", ["product", "cybersecurity"]),
    ("ActaAstronautica.pdf", "What is the main topic covered in Acta Astronautica?", ["space"]),
    ("CIS-MS-ISAC-NIST-Cybersecurity-Framework-Policy-Template-Guide.pdf", "What organization published the Cybersecurity Framework Policy Template Guide?", ["cis", "ms-isac"]),
    ("NIST-CSWP-29.pdf", "What are the five core functions of the NIST Cybersecurity Framework?", ["identify", "protect", "detect", "respond", "recover"]),
]:
    print("=" * 60)
    print(f"PDF: {pdf} | Q: {q}")
    hits = rs.search(query=q, top_k=40)
    matching = [h for h in hits if pdf in str(h.get("file_path", ""))]
    print(f"Total hits from this doc in top-40: {len(matching)}")
    for i, h in enumerate(matching):
        txt = h.get("chunk_text", "")
        kw_status = {k: (k in txt.lower()) for k in kws}
        print(f"  Hit {i+1} (page {h.get('page_number')}, sim {h.get('similarity_score', 0):.3f}): {kw_status}")
        print(f"    Excerpt: {txt[:120].strip()}")
