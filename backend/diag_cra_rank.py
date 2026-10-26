"""Check at what rank the CRA cybersecurity chunk appears."""
import sys, warnings
warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "d:/RAGENG/files (1)/backend")

from pathlib import Path
from app.embeddings.embedding_service import EmbeddingService
from app.vector_store.faiss_store import FaissStore
from app.retrieval.retrieval_service import RetrievalService
import numpy as np

BACKEND_DIR = Path("d:/RAGENG/files (1)/backend")
faiss_dir = BACKEND_DIR / "storage" / "vector_store"
es = EmbeddingService(model_name="all-MiniLM-L6-v2")
fs = FaissStore(index_path=str(faiss_dir), dimension=384)
fs.load_index()
rs = RetrievalService(embedding_service=es, faiss_store=fs, default_top_k=5)

q = "What does the Cyber Resilience Act regulate?"
hits = rs.search(query=q, top_k=50)

print("Rank of CRA chunks containing 'cybersecurity':")
for i, h in enumerate(hits):
    txt = h.get("chunk_text", "").lower()
    if "cybersecurity" in txt:
        print(f"  Rank #{i+1} [{h['similarity_score']:.3f}]: {h.get('chunk_text','')[:100]}")

# Also check max_distance filter 
print()
print("Top-5 by distance (no filter):")
qemb = es.model.encode([q], show_progress_bar=False, convert_to_numpy=True)
qemb = np.array(qemb, dtype=np.float32)
dists, idxs = fs.index.search(qemb, 50)
for i in range(min(5, len(idxs[0]))):
    idx = int(idxs[0][i])
    dist = float(dists[0][i])
    meta = fs.get_metadata(idx)
    if meta:
        txt = meta.get("chunk_text", "")
        has_cyber = "cybersecurity" in txt.lower()
        print(f"  #{i+1} [{dist:.3f}] cyber={has_cyber}: {txt[:80]}")
