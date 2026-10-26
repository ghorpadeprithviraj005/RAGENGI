#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Evaluation script for the RAGENGI 100‑case benchmark.

* Reference data         : backend/reports/benchmark_160/qa_dataset_160.json
* Model predictions      : backend/reports/benchmark_100_subset_final_20261023_101046/evaluation_results_100_subset.json
* Metrics                : ROUGE‑L (official rouge-score) and BERTScore
* Output                : a new timestamped report directory containing
    - per‑case CSV
    - JSON summary
    - Markdown report
* The factual‑correctness score (83 / 100 = 83 %) is **preserved** and reported
  but never recomputed.

The script performs exhaustive validation (unique IDs, 100 matched cases,
no missing reference answers or predictions) and records the exact
environment used for the run.
"""

import json
import os
import sys
import subprocess
import datetime
from pathlib import Path
from collections import Counter

# --------------------------------------------------------------------------- #
# Helper – safe import with optional installation
# --------------------------------------------------------------------------- #
def safe_import(package_name: str, import_name: str = None):
    """
    Try to import a package; if it fails, attempt a pip install inside the
    current virtual environment.  Return the imported module.
    """
    try:
        if import_name is None:
            import_name = package_name
        module = __import__(import_name)
        return module
    except ImportError as exc:
        print(f"[INFO] Package '{package_name}' not found. Attempting installation...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
            module = __import__(import_name)
            return module
        except subprocess.CalledProcessError as cpe:
            raise RuntimeError(
                f"Failed to install required package '{package_name}'. "
                f"Original error: {cpe}"
            ) from cpe

# --------------------------------------------------------------------------- #
# Imports (install on‑demand if missing)
# --------------------------------------------------------------------------- #
torch = safe_import("torch")
rouge_score = safe_import("rouge_score")
bert_score = safe_import("bert_score")

# Specific classes/functions
from rouge_score import rouge_scorer
from bert_score import score as bert_score_func

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
ROOT = Path("D:/RAGENG/files (1)")

REF_FILE = ROOT / "backend" / "reports" / "benchmark_160" / "qa_dataset_160.json"
PRED_FILE = (
    ROOT
    / "backend"
    / "reports"
    / "benchmark_100_subset_final_20261023_101046"
    / "evaluation_results_100_subset.json"
)

# --------------------------------------------------------------------------- #
# Validation utilities
# --------------------------------------------------------------------------- #
def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def validate_data(ref_data, pred_data):
    """Return (joined list, errors)."""
    errors = []

    # Build dicts keyed by case_id
    ref_by_id = {int(item["case_id"]): item for item in ref_data}
    pred_by_id = {int(item["case_id"]): item for item in pred_data}

    # Unique‑ID checks
    if len(ref_by_id) != len(ref_data):
        errors.append("Duplicate case_id(s) found in reference file.")
    if len(pred_by_id) != len(pred_data):
        errors.append("Duplicate case_id(s) found in prediction file.")

    # Ensure we have exactly 100 cases in predictions (benchmark size)
    if len(pred_by_id) != 100:
        errors.append(f"Prediction file contains {len(pred_by_id)} cases (expected 100).")

    # Intersection
    common_ids = set(ref_by_id) & set(pred_by_id)
    missing_in_pred = set(ref_by_id) - common_ids
    missing_in_ref = set(pred_by_id) - common_ids

    # It's expected that reference contains many IDs not present in the 100‑case subset.
    # Only treat missing IDs in the reference as an error (predictions referring to unknown IDs).
    if missing_in_ref:
        errors.append(f"{len(missing_in_ref)} case_id(s) missing in references: {sorted(missing_in_ref)}")

    # Ensure we have exactly 100 matched cases.
    if len(common_ids) != 100:
        errors.append(f"Expected 100 matched case_id(s), but found {len(common_ids)} common IDs.")

    # Build joined list (preserve order by case_id)
    joined = []
    for cid in sorted(common_ids):
        ref_item = ref_by_id[cid]
        pred_item = pred_by_id[cid]

        # check that reference answer exists
        if "answer" not in ref_item or not ref_item["answer"]:
            errors.append(f"Reference answer missing for case_id {cid}.")
        # check that model output exists
        if "model_output" not in pred_item or not pred_item["model_output"]:
            errors.append(f"Model output missing for case_id {cid}.")

        joined.append(
            {
                "case_id": cid,
                "question": ref_item.get("question", ""),
                "reference": ref_item.get("answer", ""),
                "prediction": pred_item.get("model_output", ""),
            }
        )
    return joined, errors

# --------------------------------------------------------------------------- #
# Metric computation
# --------------------------------------------------------------------------- #
def compute_rouge_l(reference: str, prediction: str, scorer):
    """
    Returns the F1 score of ROUGE‑L.  Stemming is enabled via the scorer’s
    ``use_stemmer=True`` flag (the official rouge‑score package defaults to
    stemming when that flag is set).
    """
    scores = scorer.score(target=reference, prediction=prediction)
    return scores["rougeL"].fmeasure

def compute_bertscore(references, predictions, device):
    """Returns three lists: precision, recall, f1."""
    P, R, F1 = bert_score_func(
        predictions,
        references,
        lang="en",
        model_type="roberta-large",
        device=device,
        rescale_with_baseline=True,
    )
    return P.tolist(), R.tolist(), F1.tolist()

# --------------------------------------------------------------------------- #
# Main workflow
# --------------------------------------------------------------------------- #
def main():
    # ------------------------------------------------------------------- #
    # 1️⃣ Load data
    # ------------------------------------------------------------------- #
    if not REF_FILE.is_file():
        sys.exit(f"[ERROR] Reference file not found: {REF_FILE}")
    if not PRED_FILE.is_file():
        sys.exit(f"[ERROR] Prediction file not found: {PRED_FILE}")

    ref_data = load_json(REF_FILE)
    pred_data = load_json(PRED_FILE)

    # ------------------------------------------------------------------- #
    # 2️⃣ Validate & join
    # ------------------------------------------------------------------- #
    joined, validation_errors = validate_data(ref_data, pred_data)

    if validation_errors:
        print("[VALIDATION ERRORS]")
        for err in validation_errors:
            print(f"  - {err}")
        sys.exit(1)

    # ------------------------------------------------------------------- #
    # 3️⃣ Prepare metric calculators
    # ------------------------------------------------------------------- #
    rouge_scorer_obj = rouge_scorer.RougeScorer([
        "rougeL"], use_stemmer=True
    )  # stemming enabled

    device = "cuda" if torch.cuda.is_available() else "cpu"

    # ------------------------------------------------------------------- #
    # 4️⃣ Compute per‑case metrics
    # ------------------------------------------------------------------- #
    rouge_scores = []
    predictions = []
    references = []

    for entry in joined:
        ref = entry["reference"]
        pred = entry["prediction"]
        predictions.append(pred)
        references.append(ref)
        rouge_f1 = compute_rouge_l(ref, pred, rouge_scorer_obj)
        rouge_scores.append(rouge_f1)

    bert_P, bert_R, bert_F1 = compute_bertscore(references, predictions, device)

    # ------------------------------------------------------------------- #
    # 5️⃣ Combine results
    # ------------------------------------------------------------------- #
    for i, entry in enumerate(joined):
        entry["rouge_l_f1"] = rouge_scores[i]
        entry["bertscore_precision"] = bert_P[i]
        entry["bertscore_recall"] = bert_R[i]
        entry["bertscore_f1"] = bert_F1[i]

    # ------------------------------------------------------------------- #
    # 6️⃣ Summary statistics
    # ------------------------------------------------------------------- #
    import numpy as np
    from importlib import metadata

    def stats(arr):
        arr_np = np.array(arr, dtype=float)
        return {"mean": float(arr_np.mean()), "median": float(np.median(arr_np))}

    summary = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "environment": {
            "python_version": sys.version.split()[0],
            "torch_version": metadata.version("torch"),
            "rouge_score_version": metadata.version("rouge_score"),
            "bert_score_version": metadata.version("bert_score"),
            "device": device,
            "bert_model": "roberta-large",
            "bert_language": "en",
            "bert_rescale_with_baseline": True,
        },
        "metrics": {
            "rouge_l_f1": stats(rouge_scores),
            "bertscore_precision": stats(bert_P),
            "bertscore_recall": stats(bert_R),
            "bertscore_f1": stats(bert_F1),
        },
        "case_count": len(joined),
        "factual_correctness": {
            "preserved_score": "83/100 (83%)",
            "note": "The original factual‑correctness result is retained unchanged.",
        },
        "failed_cases": [],
    }

    # ------------------------------------------------------------------- #
    # 7️⃣ Write outputs
    # ------------------------------------------------------------------- #
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / "backend" / "reports" / f"benchmark_rouge_bertscore_{ts}"
    out_dir.mkdir(parents=True, exist_ok=False)

    # CSV
    csv_path = out_dir / "per_case_metrics.csv"
    import csv
    csv_fields = ["case_id","question","reference","prediction","rouge_l_f1","bertscore_precision","bertscore_recall","bertscore_f1"]
    with open(csv_path, "w", newline="", encoding="utf-8") as csvf:
        writer = csv.DictWriter(csvf, fieldnames=csv_fields)
        writer.writeheader()
        for entry in joined:
            writer.writerow({k: entry.get(k, "") for k in csv_fields})

    # JSON summary
    json_path = out_dir / "summary.json"
    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump(summary, jf, indent=2, ensure_ascii=False)

    # Markdown report
    md_path = out_dir / "report.md"
    with open(md_path, "w", encoding="utf-8") as mf:
        mf.write(f"# RAGENGI 100‑case benchmark – ROUGE‑L & BERTScore evaluation\n")
        mf.write(f"**Timestamp**: {summary['timestamp']}\n\n")
        mf.write("## Environment\n")
        for k, v in summary["environment"].items():
            mf.write(f"- **{k}**: {v}\n")
        mf.write("\n## Metric definitions\n")
        mf.write("- **ROUGE‑L** – Longest‑common‑subsequence based F1 score. Stemming is enabled (`use_stemmer=True`).\n")
        mf.write("- **BERTScore** – Token‑level similarity using `roberta-large`. Precision, Recall and F1 are rescored with baseline (`rescale_with_baseline=True`).\n")
        mf.write("\n## Results (per‑case CSV attached)\n")
        mf.write("\n### Aggregate statistics\n")
        for metric, vals in summary["metrics"].items():
            mf.write(f"- **{metric.replace('_', ' ').title()}** – mean: {vals['mean']:.4f}, median: {vals['median']:.4f}\n")
        mf.write("\n### Factual‑correctness (unchanged)\n")
        mf.write(f"- Preserved score: **{summary['factual_correctness']['preserved_score']}**\n")
        mf.write("\n---\n")
        mf.write("All 100 benchmark cases were successfully matched and evaluated. No missing references or predictions were detected.\n")

    # ------------------------------------------------------------------- #
    # 8️⃣ Final console output
    # ------------------------------------------------------------------- #
    print("\n=== Evaluation completed ===")
    print(f"Report directory : {out_dir}")
    print(f"CSV file         : {csv_path}")
    print(f"JSON summary     : {json_path}")
    print(f"Markdown report  : {md_path}\n")
    print("Summary statistics:")
    for metric, vals in summary["metrics"].items():
        print(f"  {metric.replace('_', ' ').title():<25} mean={vals['mean']:.4f}  median={vals['median']:.4f}")

if __name__ == "__main__":
    main()
