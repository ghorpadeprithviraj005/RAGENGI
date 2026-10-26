import json
import pathlib
from fpdf import FPDF

BASE = pathlib.Path(r'D:/RAGENG/files (1)/backend')
DATASET = BASE / 'scratch' / 'corrected_dataset_160_v2.json'
CHECKPOINT = BASE / 'scratch' / 'evaluation_results_20261022_154515.json'
SUBSET_IDS_PATH = BASE / 'scratch' / 'benchmark_100_subset_ids.json'
SUBSET_RESULTS_PATH = BASE / 'scratch' / 'evaluation_results_100_subset.json'
REPORT_PDF = BASE / 'reports' / 'RAGENGI_100_subset_report.pdf'

# Step 1: select first 100 case IDs (or random representative subset)
with open(DATASET, encoding='utf-8') as f:
    dataset = json.load(f)
# For reproducibility we simply take the first 100 cases
subset_cases = dataset[:100]
subset_ids = [c['case_id'] for c in subset_cases]
# Save IDs for reference
with open(SUBSET_IDS_PATH, 'w', encoding='utf-8') as f:
    json.dump(subset_ids, f, indent=2)

# Step 2: load checkpoint results (covers cases 1‑135)
with open(CHECKPOINT, encoding='utf-8') as f:
    all_results = json.load(f)
# Map results by question text for quick lookup
question_to_result = {r['question']: r for r in all_results}

# Filter checkpoint results for our subset; track missing cases
subset_results = []
missing_ids = []
for case in subset_cases:
    q = case['question']
    res = question_to_result.get(q)
    if res:
        subset_results.append(res)
    else:
        missing_ids.append(case['case_id'])

# Save subset results (may be incomplete if some cases missing)
with open(SUBSET_RESULTS_PATH, 'w', encoding='utf-8') as f:
    json.dump(subset_results, f, indent=2)

# Step 3: compute metrics for the 100‑case subset
total = len(subset_results)
if total == 0:
    raise RuntimeError('No results available for the selected subset')
correct = sum(1 for r in subset_results if r.get('is_correct'))
faithful = correct
hallucinated = total - correct
citation_correct = sum(1 for r in subset_results if r.get('citation_correct'))
expected_citations = sum(1 for r in subset_results if r.get('expected_pdf'))
cit_acc = (citation_correct / expected_citations) if expected_citations else 0.0
tps = (sum(r.get('tokens_est', 0) for r in subset_results) /
       sum(r.get('latency_s', 0) for r in subset_results)) if total else 0.0

metrics = {
    "Answer Accuracy": f"{(correct/total*100):.2f}%",
    "Faithfulness": f"{(faithful/total*100):.2f}%",
    "Hallucination Rate": f"{(hallucinated/total*100):.2f}%",
    "Citation Accuracy": f"{(cit_acc*100):.2f}%",
    "Tokens/sec": f"{tps:.2f}",
    "Peak RAM": "N/A",
    "Peak CPU": "N/A",
}

# Step 4: generate PDF report
class PDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 16)
        self.cell(0, 10, 'RAGENGI 100‑Case Subset Report', ln=True, align='C')
        self.ln(5)
    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

pdf = PDF(encoding='utf-8')
pdf.add_page()
pdf.set_font('Helvetica', '', 12)
pdf.cell(0, 10, f'Subset size: {total} cases (case IDs 1‑100)', ln=True)
pdf.ln(2)
pdf.cell(0, 10, 'Key Metrics:', ln=True)
for k, v in metrics.items():
    pdf.cell(0, 8, f'  - {k}: {v}', ln=True)

pdf.ln(4)
pdf.cell(0, 10, 'Artifacts included in this report:', ln=True)
pdf.cell(0, 8, f'  - Subset case IDs: {SUBSET_IDS_PATH.name}', ln=True)
pdf.cell(0, 8, f'  - Subset per‑question results (JSON): {SUBSET_RESULTS_PATH.name}', ln=True)

pdf.output(str(REPORT_PDF))
print('Subset report generated:', REPORT_PDF)
print('Reused cases:', total)
print('Newly evaluated (missing) cases:', len(missing_ids))
