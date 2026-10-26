"""Targeted ingestion of PhysRev.pdf into the existing FAISS index (additive, no rebuild)."""
import sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, "d:/RAGENG/files (1)/backend")

from pathlib import Path
import numpy as np
import os

from app.ingestion.pipeline import DocumentIngestionPipeline
from app.ingestion.chunker import PDFChunker
from app.embeddings.embedding_service import EmbeddingService
from app.vector_store.faiss_store import FaissStore

BACKEND_DIR = Path("d:/RAGENG/files (1)/backend")
FAISS_DIR = BACKEND_DIR / "storage" / "vector_store"
PHYSREV_PATH = str(BACKEND_DIR / "test_data" / "PhysRev.pdf")

print("=== Ingesting PhysRev.pdf ===")
print(f"Source: {PHYSREV_PATH}")
print(f"FAISS:  {FAISS_DIR}")

# Load existing index
es = EmbeddingService(model_name="all-MiniLM-L6-v2")
fs = FaissStore(index_path=str(FAISS_DIR), dimension=384)
try:
    fs.load_index()
    print(f"Loaded existing index: {fs.index.ntotal} vectors")
except Exception as e:
    print(f"Warning loading index: {e}")

# Check if PhysRev already indexed
physrev_count = 0
for i in range(fs.index.ntotal):
    meta = fs.get_metadata(i)
    if meta and "PhysRev" in str(meta.get("file_path", "")):
        physrev_count += 1
print(f"Existing PhysRev chunks in index: {physrev_count}")

if physrev_count > 0:
    print("PhysRev already indexed! Doing retrieval check only.")
else:
    # Extract text
    pipeline = DocumentIngestionPipeline()
    result = pipeline.process(PHYSREV_PATH)
    print(f"Extracted {result.page_count} pages from PhysRev.pdf")

    # Chunk using chunk_document()
    chunker = PDFChunker()
    chunking_result = chunker.chunk_document(result)
    chunks = chunking_result.chunks
    print(f"Created {len(chunks)} chunks")

    if not chunks:
        print("ERROR: No chunks created - PhysRev may be image-only (OCR needed)")
        # Print some page text to debug
        for pg in result.pages[:3]:
            print(f"  Page {pg.page_number} ({pg.source}): {repr(pg.text[:100]) if pg.text else 'EMPTY'}")
        sys.exit(1)

    # Sample chunk text
    print("Sample chunks:")
    for c in chunks[:3]:
        print(f"  p{c.page_number}: {repr(c.chunk_text[:80])}")

    # Embed
    texts = [c.chunk_text for c in chunks]
    embeddings = es.model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
    embeddings = np.array(embeddings, dtype=np.float32)
    print(f"Embedded {len(embeddings)} chunks, shape={embeddings.shape}")

    # Add to FAISS index
    embeddings_data = []
    for emb, c in zip(embeddings, chunks):
        embeddings_data.append({
            "embedding": emb,
            "metadata": {
                "chunk_id": c.chunk_id,
                "page_number": c.page_number,
                "chunk_text": c.chunk_text,
                "file_path": PHYSREV_PATH,
            }
        })

    fs.add_embeddings(embeddings_data)
    fs.save_index()
    print(f"Saved index. Total vectors now: {fs.index.ntotal}")

# Quick retrieval check
from app.retrieval.retrieval_service import RetrievalService
rs = RetrievalService(embedding_service=es, faiss_store=fs, default_top_k=5)
hits = rs.search("What field of science does PhysRev primarily cover?", top_k=5)
print("\nRetrieval check for PhysRev question:")
for h in hits:
    fn = os.path.basename(h.get("file_path", ""))
    txt = str(h.get("chunk_text", ""))[:80]
    print(f"  [{h['similarity_score']:.3f}] {fn}: {txt}")

physrev_hits = [h for h in hits if "PhysRev" in str(h.get("file_path", ""))]
if physrev_hits:
    print(f"\nPASS: PhysRev.pdf in top-5 ({len(physrev_hits)} hits)")
else:
    print("\nFAIL: PhysRev.pdf NOT in top-5 - may need wider search")
    hits20 = rs.search("What field of science does PhysRev primarily cover?", top_k=20)
    physrev_hits20 = [(i+1, h) for i, h in enumerate(hits20) if "PhysRev" in str(h.get("file_path", ""))]
    if physrev_hits20:
        print(f"  Found at rank(s): {[r for r, _ in physrev_hits20]}")
    else:
        print("  Not found in top-20 either")
print("=== Done ===")
