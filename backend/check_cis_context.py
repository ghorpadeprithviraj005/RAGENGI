import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "d:/RAGENG/files (1)/backend")
from app.embeddings.embedding_service import EmbeddingService
from app.vector_store.faiss_store import FaissStore
from app.retrieval.retrieval_service import RetrievalService
from app.llm.llm_service import LLMService

es = EmbeddingService(model_name="all-MiniLM-L6-v2")
fs = FaissStore(index_path="d:/RAGENG/files (1)/backend/storage/vector_store", dimension=384)
fs.load_index()
rs = RetrievalService(embedding_service=es, faiss_store=fs, default_top_k=5)
llm = LLMService(model_path="d:/RAGENG/files (1)/backend/storage/models/llama-2-7b.gguf", chat_format="llama-2")

q = "What organization published the Cybersecurity Framework Policy Template Guide?"
hits = rs.search(query=q, top_k=40)
msgs = llm.build_messages(q, hits, active_filename="CIS-MS-ISAC-NIST-Cybersecurity-Framework-Policy-Template-Guide.pdf")
print("Selected context for CIS:")
print(msgs[1]["content"])
