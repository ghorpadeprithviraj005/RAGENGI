import sys
import os

backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from app.api.routes.rag import _retrieval_service, _llm_service, _faiss_store

print("Fixing context_window on _llm_service...")
if hasattr(_llm_service.llm, "n_ctx") and callable(_llm_service.llm.n_ctx):
    _llm_service.context_window = _llm_service.llm.n_ctx()
    print("Fixed context_window:", _llm_service.context_window)

chunks = _retrieval_service.search("NASA Technical Report Server", top_k=5)
print("Retrieved chunks count:", len(chunks))

query = "What is the NASA Technical Report Server?"
messages = _llm_service.build_messages(query, retrieved_chunks=chunks)
print("Messages built successfully! Count:", len(messages))
print("User content preview:\n", messages[1]["content"][:300])

print("\nGenerating answer...")
res = _llm_service.generate_answer(query, retrieved_chunks=chunks)
print("\n--- Answer ---")
print(res["answer"])
print("\n--- Citations ---")
print(res["citations"])
