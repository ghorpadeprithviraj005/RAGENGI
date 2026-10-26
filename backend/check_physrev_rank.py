from app.vector_store.faiss_store import FaissStore
from app.embeddings.embedding_service import EmbeddingService
from pathlib import Path
import numpy as np

es = EmbeddingService('all-MiniLM-L6-v2')
fs = FaissStore('storage/vector_store')

q = "What field of science does PhysRev primarily cover?"
query_embedding = np.array(es.model.encode([q]), dtype=np.float32)
distances, indices = fs.index.search(query_embedding, 100)

KEY_PHRASES = [
    "physical review",
    "cybersecurity framework",
    "cyber resilience act",
    "active flow control",
    "power supply",
    "tender manual",
    "vendor registration",
    "technical report server",
    "sale deed",
    "student journal of physics"
]

def phrase_in_query(phrase: str, query: str) -> bool:
    q_low = query.lower()
    content_words = [w for w in phrase.split() if w not in ["of", "the", "in", "for", "an", "a"]]
    for w in content_words:
        if w in q_low:
            continue
        if w in ["physical", "physics"] and "phys" in q_low:
            continue
        if w == "review" and "rev" in q_low:
            continue
        if w == "cybersecurity" and "cyber" in q_low:
            continue
        return False
    return True

candidates = []
words_in_q = {"field", "science", "physrev", "primarily", "cover", "physical", "review", "physics"}

for rank in range(len(indices[0])):
    idx = int(indices[0][rank])
    distance = float(distances[0][rank])
    meta = fs.get_metadata(idx)
    if meta:
        txt_lower = meta.get("chunk_text", "").lower()
        
        # Check matching key phrases that are genuinely queried
        phrase_matches = sum(1 for p in KEY_PHRASES if p in txt_lower and phrase_in_query(p, q))
        matched_words = {w for w in words_in_q if w in txt_lower}
        
        final_score = distance - (0.15 * len(matched_words)) - (0.40 * phrase_matches)
        candidates.append({
            "file": Path(meta.get("file_path", "")).name,
            "dist": distance,
            "phrase_m": phrase_matches,
            "matched_words": matched_words,
            "final_score": final_score,
            "snippet": meta.get("chunk_text", "")[:60]
        })

candidates.sort(key=lambda x: x["final_score"])

print("Top 10 sorted candidates:")
for i, c in enumerate(candidates[:10]):
    print(f"{i+1:2d}. {c['file']:35s} raw={c['dist']:.3f} final={c['final_score']:.3f} phrase={c['phrase_m']} words={c['matched_words']}")
