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

q = "What does the Cyber Resilience Act regulate?"
stop = {"what", "does", "the", "act", "in", "of", "for", "to", "is", "a", "an"}
q_terms = [w.strip("?,.") for w in q.lower().split() if w.strip("?,.") not in stop and len(w) > 2]
print("Query terms:", q_terms)

hits = rs.search(query=q, top_k=40)
cra_hits = [h for h in hits if "ImplementingtheCyberResilienceAct" in str(h.get("file_path",""))]
scored = []
for h in cra_hits:
    txt = h.get("chunk_text", "").lower()
    score = sum(1 for term in q_terms if term in txt)
    scored.append((score, h["similarity_score"], h))

scored.sort(key=lambda x: (-x[0], x[1]))
print("Top 5 lexical-dense re-ranked CRA hits:")
for sc, sim, h in scored[:5]:
    txt = h.get("chunk_text", "")
    has_cyber = "cybersecurity" in txt.lower()
    has_prod = "product" in txt.lower()
    print(f"score={sc}, sim={sim:.3f}, page={h.get('page_number')}, cyber={has_cyber}, prod={has_prod}")
    print("  ", txt[:120].strip())
