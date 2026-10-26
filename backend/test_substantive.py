import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "d:/RAGENG/files (1)/backend")
from app.embeddings.embedding_service import EmbeddingService
from app.vector_store.faiss_store import FaissStore
from app.retrieval.retrieval_service import RetrievalService

es = EmbeddingService(model_name="all-MiniLM-L6-v2")
fs = FaissStore(index_path="d:/RAGENG/files (1)/backend/storage/vector_store", dimension=384)
fs.load_index()
rs = RetrievalService(embedding_service=es, faiss_store=fs, default_top_k=5)

hits = rs.search(query="What does the Cyber Resilience Act regulate?", top_k=40)
cra_hits = [h for h in hits if "ImplementingtheCyberResilienceAct" in str(h.get("file_path",""))]
filtered = [c for c in cra_hits if len(c.get("chunk_text","").split()) >= 30]
print(f"Original hits: {len(cra_hits)}, Substantive hits (>=30 words): {len(filtered)}")
for i, c in enumerate(filtered[:7]):
    t = c.get("chunk_text","")
    print(f"Substantive #{i+1} (page {c.get('page_number')}): has_cybersecurity={'cybersecurity' in t.lower()} has_product={'product' in t.lower()}")
    print("  ", t[:100].strip())
