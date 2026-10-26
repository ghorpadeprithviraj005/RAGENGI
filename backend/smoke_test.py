import time, json, csv, concurrent.futures
from pathlib import Path
import sys

# Paths
BACKEND_DIR = Path(r'D:/RAGENG/files (1)/backend').resolve()
SCRATCH = BACKEND_DIR / 'scratch'
EVAL_JSON = SCRATCH / 'evaluation_results_smoke.json'
EVAL_CSV = SCRATCH / 'evaluation_results_smoke.csv'

# Ensure scratch exists
SCRATCH.mkdir(parents=True, exist_ok=True)

# Add backend to sys.path
sys.path.insert(0, str(BACKEND_DIR))

from app.embeddings.embedding_service import EmbeddingService
from app.vector_store.faiss_store import FaissStore
from app.retrieval.retrieval_service import RetrievalService
from app.llm.llm_service import LLMService
from ingest_and_test import QA_CASES, REFUSAL_PHRASES

# Load resources
faiss_dir = BACKEND_DIR / 'storage' / 'vector_store'
embedding = EmbeddingService(model_name='all-MiniLM-L6-v2')
faiss = FaissStore(index_path=str(faiss_dir), dimension=384)
faiss.load_index()
retrieval = RetrievalService(embedding_service=embedding, faiss_store=faiss, default_top_k=5)

llm_path = BACKEND_DIR / 'storage' / 'models' / 'llama-2-7b-chat.Q4_K_M.gguf'
llm = LLMService(model_path=str(llm_path), chat_format='llama-2')

per_question_results = []

for i, case in enumerate(QA_CASES[:3], start=1):
    q = case['question']
    expected_pdf = case['pdf']
    kws = [k.lower() for k in case.get('expected_keywords', [])]
    refusal = case.get('expect_refusal', False)
    hits = retrieval.search(query=q, top_k=5)
    t0 = time.time()
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as exec:
            fut = exec.submit(llm.generate_answer, q, hits)
            out = fut.result(timeout=30)
    except Exception as e:
        out = {'answer': f'ERROR: {e}', 'citations': []}
    latency = time.time() - t0
    ans = out.get('answer', '').lower()
    cits = out.get('citations', [])
    # correctness check
    is_correct = False
    if refusal:
        if any(p in ans for p in REFUSAL_PHRASES):
            is_correct = True
    else:
        if all(k in ans for k in kws):
            is_correct = True
    # citation check
    citation_correct = False
    if expected_pdf:
        for c in cits:
            fp = c.get('file_path', '')
            if fp and expected_pdf in fp:
                citation_correct = True
                break
    else:
        citation_correct = not cits
    est_tokens = len(out.get('answer', '')) / 4.0
    per_question_results.append({
        'question': q,
        'expected_pdf': expected_pdf,
        'expected_keywords': kws,
        'refusal_expected': refusal,
        'answer': out.get('answer', ''),
        'citations': cits,
        'is_correct': is_correct,
        'citation_correct': citation_correct,
        'latency_s': latency,
        'tokens_est': est_tokens
    })
    print(f'Case {i}/3 completed in {latency:.2f}s, correct={is_correct}, citation_ok={citation_correct}')

# Write JSON
with open(EVAL_JSON, 'w', encoding='utf-8') as jf:
    json.dump(per_question_results, jf, indent=2)
# Write CSV
with open(EVAL_CSV, 'w', newline='', encoding='utf-8') as cf:
    writer = csv.writer(cf)
    header = ['question','expected_pdf','expected_keywords','refusal_expected','answer','citations','is_correct','citation_correct','latency_s','tokens_est']
    writer.writerow(header)
    for r in per_question_results:
        writer.writerow([
            r['question'],
            r['expected_pdf'],
            ','.join(r['expected_keywords']),
            r['refusal_expected'],
            r['answer'],
            json.dumps(r['citations']),
            r['is_correct'],
            r['citation_correct'],
            r['latency_s'],
            r['tokens_est'],
        ])
print('Smoke test finished. JSON:', EVAL_JSON, 'CSV:', EVAL_CSV)
