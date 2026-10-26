import json,statistics
path='D:/RAGENG/files (1)/backend/reports/benchmark_100_subset_final_20261023_101046/evaluation_results_100_subset_checkpoint.jsonl'
records=[]
with open(path,encoding='utf-8') as f:
    for line in f:
        records.append(json.loads(line))
latencies=[r['latency_s'] for r in records]
tokens=[r['tokens_est'] for r in records]
mean_latency=sum(latencies)/len(latencies)
# 95th percentile using nearest-rank method
sorted_lat=sorted(latencies)
index=int(0.95*len(sorted_lat))-1
p95=sorted_lat[index]
tps=sum(tokens)/sum(latencies)
print('Mean latency (s):',mean_latency)
print('P95 latency (s):',p95)
print('Tokens per second:',tps)
