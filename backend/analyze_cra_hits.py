import sys
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
print(f"Total CRA hits in top-40: {len(cra_hits)}")
for i, h in enumerate(cra_hits):
    t = h.get("chunk_text", "")
    print(f"Hit #{i+1}: chars={len(t)}, words={len(t.split())}, page={h.get('page_number')}")
    print(f"   Excerpt: {repr(t[:80])}")
