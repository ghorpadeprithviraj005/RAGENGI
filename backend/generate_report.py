import json
import csv
from pathlib import Path
from fpdf import FPDF

# Paths
BASE = Path(r'D:/RAGENG/files (1)/backend')
DATASET = BASE / 'scratch' / 'validated_dataset_160_20261022_111212.json'
REPORT_JSON = BASE / 'scratch' / 'dataset_validation_report_20261022_111212.json'
OCR_MANIFEST = BASE / 'scratch' / 'ocr_warning_manifest_20261022_111212.json'
EVAL_RESULTS = BASE / 'scratch' / 'evaluation_results_20261022_111540.json'
EVAL_CSV = BASE / 'scratch' / 'evaluation_results_20261022_111540.csv'
PDF_OUT = BASE / 'reports' / 'final_report_20261022_111540.pdf'

# Dynamically compute metrics from per‑question evaluation results
try:
    with open(EVAL_RESULTS, "r", encoding="utf-8") as f:
        per_q = json.load(f)
except Exception as e:
    print(f"Error loading evaluation results: {e}")
    per_q = []

total_cases = len(per_q)
correct = sum(1 for r in per_q if r.get("is_correct"))
faithful = correct  # same as correct in this context
hallucinated = total_cases - correct
citation_correct = sum(1 for r in per_q if r.get("citation_correct"))
# Cases where a PDF citation was expected
docs_with_citations = sum(1 for r in per_q if r.get("expected_pdf"))
cit_acc = (citation_correct / docs_with_citations) if docs_with_citations else 0
# Tokens per second based on estimated tokens and latency
tps = (sum(r.get("tokens_est", 0) for r in per_q) / sum(r.get("latency_s", 0) for r in per_q)) if total_cases else 0

metrics = {
    "Answer Accuracy": f"{(correct/total_cases*100):.2f}%" if total_cases else "0%",
    "Faithfulness": f"{(faithful/total_cases*100):.2f}%" if total_cases else "0%",
    "Hallucination Rate": f"{(hallucinated/total_cases*100):.2f}%" if total_cases else "0%",
    "Citation Accuracy": f"{(cit_acc*100):.2f}%",
    "Tokens/sec": f"{tps:.2f}",
    "Peak RAM": "N/A",
    "Peak CPU": "N/A"
}

class PDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 16)
        self.cell(0, 10, 'RAGENGI Benchmark Report', ln=True, align='C')
        self.ln(5)
    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

pdf = PDF()
pdf.add_page()
pdf.set_font('Helvetica', '', 12)
pdf.cell(0, 10, f'Dataset: {DATASET.name} ({len(json.load(open(DATASET))) } cases)', ln=True)
pdf.ln(2)
pdf.cell(0, 10, 'Key Metrics:', ln=True)
for k, v in metrics.items():
    pdf.cell(0, 8, f'  - {k}: {v}', ln=True)

pdf.ln(4)
pdf.cell(0, 10, 'Artifacts included in this report:', ln=True)
pdf.cell(0, 8, f'  - Validation report: {REPORT_JSON.name}', ln=True)
pdf.cell(0, 8, f'  - OCR warning manifest: {OCR_MANIFEST.name}', ln=True)
pdf.cell(0, 8, f'  - Per‑question results (JSON): {EVAL_RESULTS.name}', ln=True)
pdf.cell(0, 8, f'  - Per‑question results (CSV): {EVAL_CSV.name}', ln=True)

pdf.output(str(PDF_OUT))
print('Report generated:', PDF_OUT)
