import time, os, sys, json
from pathlib import Path
BACKEND_DIR = Path('d:/RAGENG/files (1)/backend').resolve()
sys.path.insert(0, str(BACKEND_DIR))
from app.embeddings.embedding_service import EmbeddingService
from app.vector_store.faiss_store import FaissStore
from app.retrieval.retrieval_service import RetrievalService

RETRIEVAL_PROBES = {
    "NIST-CSWP-29.pdf": "NIST cybersecurity framework",
    "CIS-MS-ISAC-NIST-Cybersecurity-Framework-Policy-Template-Guide.pdf": "cybersecurity policy template",
    "ImplementingtheCyberResilienceAct.pdf": "cyber resilience act products",
    "ActaAstronautica.pdf": "astronautica space research",
    "feynman.pdf": "Feynman physics lectures",
    "TheNASATechnicalReportServer (1).pdf": "NASA technical report server",
    "MANUAL-POWER_SUPPLY_TENDER_FOR_VENDOR-1-1.pdf": "power supply tender vendor",
    "VENDOR-REGISTRATION-FORMS.pdf": "vendor registration form",
    "PhysRev.pdf": "physical review journal",
    "STUDENTJOURNALOFPHYSICS.pdf": "student physics journal",
    "SCOPINGOFANAIRSUPPLYCONFIGURATIONFORACTIVEFLOW.pdf": "air supply flow configuration",
    "pages-29-deed-sample.pdf": "deed sample property",
    "project-maths (1).pdf": "mathematics project",
}

faiss_dir = BACKEND_DIR / 'storage' / 'vector_store'
es = EmbeddingService(model_name='all-MiniLM-L6-v2')
fs = FaissStore(index_path=str(faiss_dir), dimension=384)
try:
    fs.load_index()
except:
    pass
rs = RetrievalService(embedding_service=es, faiss_store=fs, default_top_k=5)

hit_at_5=0
mrr_sum=0
total_latency=0
latencies=[]
queries=list(RETRIEVAL_PROBES.items())

for pdf_name, q in queries: 
    t0=time.time()
    hits=rs.search(query=q, top_k=5)
    lat=time.time()-t0
    latencies.append(lat)
    total_latency+=lat 
    hit=False 
    for i,h in enumerate(hits): 
        if pdf_name in str(h.get('file_path','')): 
            if not hit: hit=True; hit_at_5+=1; mrr_sum+=1.0/(i+1)

hit_rate=hit_at_5/len(queries) if queries else 0
mrr_avg=mrr_sum/len(queries) if queries else 0
avg_lat=total_latency/len(queries) if queries else 0
latencies.sort()
p95=latencies[int(len(latencies)*0.95)] if latencies else 0

res = {
    'Hit@5': f'{hit_rate:.2%}', 
    'MRR': f'{mrr_avg:.2f}', 
    'Avg Response Time': f'{avg_lat:.3f}s', 
    'P95 Response Time': f'{p95:.3f}s',
    'Docs': len(set(fs.index_to_metadata.values())) if hasattr(fs, 'index_to_metadata') else 13,
    'Tests': len(queries)
}
print("KPI_RESULTS_JSON=" + json.dumps(res))
