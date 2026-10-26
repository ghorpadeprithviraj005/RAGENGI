import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "d:/RAGENG/files (1)/backend")
from app.embeddings.embedding_service import EmbeddingService
from app.vector_store.faiss_store import FaissStore
from app.retrieval.retrieval_service import RetrievalService

es = EmbeddingService(model_name="all-MiniLM-L6-v2")
fs = FaissStore(index_path="d:/RAGENG/files (1)/backend/storage/vector_store", dimension=384)
fs.load_index()

meta_acta = [m for m in fs.metadata_store.values() if "Acta" in str(m.get("file_path", ""))]
print(f"Total Acta chunks in FAISS: {len(meta_acta)}")
space_chunks = [m for m in meta_acta if "space" in m.get("chunk_text", "").lower()]
print(f"Acta chunks containing 'space': {len(space_chunks)}")
for m in space_chunks:
    print(f"Page {m.get('page_number')}: {m.get('chunk_text', '')[:150]}")
