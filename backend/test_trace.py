import sys
import os

backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from app.api.routes.rag import _retrieval_service, _llm_service, _faiss_store

print("FAISS ntotal:", getattr(_faiss_store.index, "ntotal", 0))
chunks = _retrieval_service.search("NASA Technical Report Server", top_k=5)
print("Retrieved chunks count:", len(chunks))
for i, c in enumerate(chunks):
    print(f"Chunk {i}: page={c.get('page_number')}, len={len(c.get('chunk_text', ''))}, path={c.get('file_path')}")

try:
    print(f"LLM context_window: {_llm_service.context_window}, max_tokens: {_llm_service.max_tokens}")
    res = _llm_service.generate_answer("What is the NASA Technical Report Server?", retrieved_chunks=chunks)
    print("LLM Res:", res)
except Exception as e:
    import traceback
    traceback.print_exc()
