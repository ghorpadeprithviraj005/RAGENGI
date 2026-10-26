import json, time, pathlib, concurrent.futures, logging, sys

BASE = pathlib.Path(r'D:/RAGENG/files (1)/backend').resolve()
DATASET = BASE / 'scratch' / 'validated_dataset_160_20261022_111212.json'
print('Dataset path:', DATASET, flush=True)
if not DATASET.exists():
    print('Dataset not found', flush=True)
    sys.exit(1)
with open(DATASET, encoding='utf-8') as f:
    data = json.load(f)
print(f'Dataset loaded: {len(data)}/160 records.', flush=True)

# Load services
from app.embeddings.embedding_service import EmbeddingService
from app.vector_store.faiss_store import FaissStore
from app.retrieval.retrieval_service import RetrievalService
from app.llm.llm_service import LLMService
logging.basicConfig(level=logging.INFO)
print('Model loading started', flush=True)
faiss_dir = BASE / 'storage' / 'vector_store'
embedding = EmbeddingService(model_name='all-MiniLM-L6-v2')
fs = FaissStore(index_path=str(faiss_dir), dimension=384)
fs.load_index()
retrieval = RetrievalService(embedding_service=embedding, faiss_store=fs, default_top_k=5)
llm_path = BASE / 'storage' / 'models' / 'llama-2-7b.gguf'
llm = LLMService(model_path=str(llm_path), chat_format='llama-2')
print('Model loading completed', flush=True)

# Run first case
case = data[0]
q = case['question']
expected_pdf = case['pdf']
kws = [k.lower() for k in case.get('expected_keywords', [])]
refusal = case.get('expect_refusal', False)
hits = retrieval.search(query=q, top_k=5)
print('Case 1 started', flush=True)
start = time.time()
with concurrent.futures.ThreadPoolExecutor(max_workers=1) as exec:
    future = exec.submit(llm.generate_answer, q, hits)
    out = future.result(timeout=60)
elapsed = time.time() - start
print(f'Answer generation completed in {elapsed:.2f}s', flush=True)
print('Result:', out, flush=True)

# Save result to a temporary file
out_path = BASE / 'scratch' / 'one_case_debug_result.json'
with open(out_path, 'w', encoding='utf-8') as jf:
    json.dump(out, jf, indent=2)
print('Result saved to', out_path, flush=True)
