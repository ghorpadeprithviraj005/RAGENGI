"""Inspect chunks for the 3 failing retrieval cases."""
import sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, "d:/RAGENG/files (1)/backend")
from app.embeddings.embedding_service import EmbeddingService
from app.vector_store.faiss_store import FaissStore
from app.retrieval.retrieval_service import RetrievalService
from pathlib import Path
import os

BACKEND_DIR = Path("d:/RAGENG/files (1)/backend")
faiss_dir = BACKEND_DIR / "storage" / "vector_store"
es = EmbeddingService(model_name="all-MiniLM-L6-v2")
fs = FaissStore(index_path=str(faiss_dir), dimension=384)
fs.load_index()
rs = RetrievalService(embedding_service=es, faiss_store=fs, default_top_k=5)

cases = [
    ("CRA", "ImplementingtheCyberResilienceAct.pdf", "What does the Cyber Resilience Act regulate?", ["product", "cybersecurity"]),
    ("Acta", "ActaAstronautica.pdf", "What is the main topic covered in Acta Astronautica?", ["space"]),
    ("Manual", "MANUAL-POWER_SUPPLY_TENDER_FOR_VENDOR-1-1.pdf", "What type of document is the power supply tender manual?", ["tender", "supply"]),
]

for name, pdf, q, kws in cases:
    print("=== " + name + " ===")
    hits = rs.search(query=q, top_k=20)
    doc_hits = [h for h in hits if pdf in str(h.get("file_path", ""))]
    other_hits = [h for h in hits if pdf not in str(h.get("file_path", ""))]
    ordered = (doc_hits + other_hits)[:10]
    print("  Doc chunks in top-20: " + str(len(doc_hits)))
    for i, h in enumerate(ordered):
        fn = os.path.basename(h.get("file_path", ""))
        txt = h.get("chunk_text", "")
        dist = round(h["similarity_score"], 3)
        kw_found = [kw for kw in kws if kw in txt.lower()]
        print("  #" + str(i+1) + " [" + str(dist) + "] " + fn + " kws=" + str(kw_found))
        print("    " + repr(txt[:150]))
    # Also check: does ANY chunk from this doc contain the keyword?
    print()
    print("  Searching all doc chunks for keywords:")
    all_doc_chunks = []
    for i in range(fs.index.ntotal):
        meta = fs.get_metadata(i)
        if meta and pdf in str(meta.get("file_path", "")):
            all_doc_chunks.append(meta)
    print("  Total chunks for " + pdf + ": " + str(len(all_doc_chunks)))
    for kw in kws:
        matching = [c for c in all_doc_chunks if kw in c.get("chunk_text", "").lower()]
        print("  Keyword '" + kw + "': " + str(len(matching)) + " chunks contain it")
        if matching:
            print("    First match p." + str(matching[0]["page_number"]) + ": " + repr(matching[0]["chunk_text"][:120]))
    print()
