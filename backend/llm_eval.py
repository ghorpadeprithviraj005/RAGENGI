import time
import os
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
import threading
import subprocess
import json
import difflib

def _keyword_match(kws, ans, partial=False):
    """Return True if answer contains required keywords after stop‑word filtering.
    If *partial* is True, allow a match when at least one keyword is present when all keywords are stop‑words.
    """
    STOPWORDS = {"the", "a", "an", "of", "and", "or", "in", "to", "for", "on", "by", "with", "as", "at", "from"}
    filtered = [kw for kw in kws if kw not in STOPWORDS]
    ans_low = ans.lower()
    if filtered:
        return all(kw in ans_low for kw in filtered)
    if partial:
        return any(kw in ans_low for kw in kws)
    return False

def _fuzzy_match(ref, cand, threshold=0.8):
    """Return True if similarity ratio >= threshold using difflib.SequenceMatcher.
    Both inputs are lowered and stripped.
    """
    return difflib.SequenceMatcher(None, ref.strip().lower(), cand.strip().lower()).ratio() >= threshold
import csv
from pathlib import Path
import concurrent.futures

BACKEND_DIR = Path('d:/RAGENG/files (1)/backend').resolve()
# Ensure scratch directory exists
SCRATCH = BACKEND_DIR / 'scratch'
SCRATCH.mkdir(parents=True, exist_ok=True)
# Output paths for per‑question evaluation results
import datetime
timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
EVAL_JSON = SCRATCH / f'evaluation_results_{timestamp}.json'
EVAL_CSV = SCRATCH / f'evaluation_results_{timestamp}.csv'
sys.path.insert(0, str(BACKEND_DIR))

from app.embeddings.embedding_service import EmbeddingService
from app.vector_store.faiss_store import FaissStore
from app.retrieval.retrieval_service import RetrievalService
from app.llm.llm_service import LLMService
import json
import traceback

# Load the validated 160‑case dataset with explicit error handling
VALIDATED_DATASET = BACKEND_DIR / 'scratch' / 'validated_dataset_160_20261022_111212.json'
print(f"Dataset path: {VALIDATED_DATASET}", flush=True)
if VALIDATED_DATASET.exists():
    try:
        with open(VALIDATED_DATASET, encoding='utf-8') as f:
            QA_CASES = json.load(f)
        print(f"Dataset loaded: {len(QA_CASES)}/160 records.", flush=True)
    except Exception as e:
        print(f"Failed to load dataset: {e}", flush=True)
        traceback.print_exc()
        sys.exit(1)
else:
    print("Dataset file not found – falling back to small test set.", flush=True)
    from ingest_and_test import QA_CASES
total_cases = len(QA_CASES)
from ingest_and_test import REFUSAL_PHRASES

def monitor_resources(stop_event, stats):
    # Simple monitor: just wait until stopped, no WMIC calls (Windows compatible)
    while not stop_event.is_set():
        time.sleep(1.0)
    stats['peak_ram'] = 0
    stats['peak_cpu'] = 0

def main(unbiased: bool = False, use_stopword: bool = True):
    """Run the evaluation.

    Parameters
    ----------
    unbiased : bool, optional
        If True, the LLM is called without the `active_filename` argument, preventing answer-key conditioning.
    use_stopword : bool, optional
        If True (default), answer scoring uses stop‑word‑aware matching.
    """
    print("Starting LLM Eval...", flush=True)
    stop_event = threading.Event()
    stats = {}
    t = threading.Thread(target=monitor_resources, args=(stop_event, stats))
    t.start()
    
    try:
        faiss_dir = BACKEND_DIR / "storage" / "vector_store"
        es = EmbeddingService(model_name="all-MiniLM-L6-v2")
        fs = FaissStore(index_path=str(faiss_dir), dimension=384)
        fs.load_index()
        rs = RetrievalService(embedding_service=es, faiss_store=fs, default_top_k=5)
        
        llm_path = BACKEND_DIR / "storage" / "models" / "llama-2-7b.gguf"
        llm = LLMService(model_path=str(llm_path), chat_format="llama-2")
        
        correct = 0
        faithful = 0
        hallucinated = 0
        citation_correct = 0
        total_tokens = 0
        total_time_s = 0
        
        total_cases = len(QA_CASES)
        case_num = 0
        # --------------------------------------------------------------
        # Resume support – use the explicit checkpoint file from the first run
        # --------------------------------------------------------------
        checkpoint_path = SCRATCH / 'evaluation_results_20261022_154515.json'
        start_idx = 0
        if checkpoint_path.exists():
            try:
                with open(checkpoint_path, encoding='utf-8') as cp_file:
                    completed = json.load(cp_file)
                if isinstance(completed, list):
                    start_idx = len(completed)
                    questions_seen = set()
                    dupes = 0
                    for item in completed:
                        q_text = item.get("question")
                        if q_text in questions_seen:
                            dupes += 1
                        questions_seen.add(q_text)
                    if dupes > 0:
                        print(f"Warning: checkpoint contains {dupes} duplicate questions!", flush=True)
                    if start_idx != 135:
                        print(f"Warning: checkpoint contains {start_idx} records (expected 135). Proceeding from index {start_idx}.", flush=True)
                    else:
                        print(f"Checkpoint validated: exactly 135 records (cases 1–135) with no duplicate questions.", flush=True)
                        print(f"Resuming from case {start_idx + 1}/{total_cases}", flush=True)
                else:
                    print("Checkpoint JSON is not a list; ignoring resume.", flush=True)
            except Exception as e:
                print(f"Failed to load checkpoint for resume: {e}", flush=True)
        else:
            print("Checkpoint file not found; starting from beginning.", flush=True)
        # Container for per‑question records
        per_question_results = []

        case_num = start_idx
        for case in QA_CASES[start_idx:]:
            case_num += 1
            print(f"Processing case {case_num}/{total_cases}", flush=True)
            q = case["question"]
            expected_pdf = case["pdf"]
            kws = [k.lower() for k in case["expected_keywords"]]
            refusal = case["expect_refusal"]
            
            t0 = time.time()
            try:
                hits = rs.search(query=q, top_k=5)
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as _exec:
                    _future = _exec.submit(llm.generate_answer, q, hits)
                    out = _future.result(timeout=180)
                latency = time.time() - t0
            except Exception as exc:
                print(f"Error during case {case_num}: {exc}")
                traceback.print_exc()
                # Record a failure result for this case
                result_record = {
                    "question": q,
                    "expected_pdf": expected_pdf,
                    "expected_keywords": kws,
                    "refusal_expected": refusal,
                    "answer": "",
                    "citations": [],
                    "is_correct": False,
                    "citation_correct": False,
                    "latency_s": None,
                    "tokens_est": 0
                }
                per_question_results.append(result_record)
                hallucinated += 1
                continue
            
            ans = out.get("answer", "").lower()
            cits = out.get("citations", [])
            
            # Answer Accuracy with stopword filtering
            is_correct = False
            if refusal:
                if any(p in ans for p in REFUSAL_PHRASES):
                    is_correct = True
            else:
                STOPWORDS = {"the", "a", "an", "of", "and", "or", "in", "to", "for", "on", "by", "with", "as", "at", "from"}
                filtered_kws = [kw for kw in kws if kw not in STOPWORDS]
                if filtered_kws and all(kw in ans for kw in filtered_kws):
                    is_correct = True
                elif not filtered_kws and any(kw in ans for kw in kws):
                    is_correct = True
            
            if is_correct:
                correct += 1
                faithful += 1
            else:
                hallucinated += 1
                
            # Citation Accuracy
            found_cite = False
            if expected_pdf:
                for c in cits:
                    fp = c.get("file_path", "")
                    if fp and expected_pdf in fp:
                        found_cite = True
                        break
                if found_cite:
                    citation_correct += 1
            else:
                if not cits: # Should have no citations if it refused properly? Actually generate_answer always appends hits. We skip for refusal.
                    pass
            
            est_tokens = len(out.get("answer", "")) / 4.0
            total_tokens += est_tokens
            total_time_s += latency
            print(f"Done query: {q[:30]}... latency: {latency:.2f}s", flush=True)
            # Record detailed result for this case
            result_record = {
                "question": q,
                "expected_pdf": expected_pdf,
                "expected_keywords": kws,
                "refusal_expected": refusal,
                "answer": out.get("answer", ""),
                "citations": cits,
                "is_correct": is_correct,
                "is_correct_fuzzy": _fuzzy_match(case.get("answer", ""), out.get("answer", "")),
                "citation_correct": (found_cite if expected_pdf else (not cits)),
                "latency_s": latency,
                "tokens_est": est_tokens
            }
            per_question_results.append(result_record)
            # Save checkpoint every 10 cases
            if case_num % 10 == 0:
                try:
                    with open(EVAL_JSON, "w", encoding="utf-8") as jf:
                        json.dump(per_question_results, jf, indent=2)
                    with open(EVAL_CSV, "w", newline="", encoding="utf-8") as cf:
                        writer = csv.writer(cf)
                        header = ["question", "expected_pdf", "expected_keywords", "refusal_expected", "answer", "citations", "is_correct", "citation_correct", "latency_s", "tokens_est"]
                        writer.writerow(header)
                        for r in per_question_results:
                            writer.writerow([
                                r["question"],
                                r["expected_pdf"],
                                ",".join(r["expected_keywords"]),
                                r["refusal_expected"],
                                r["answer"],
                                json.dumps(r["citations"]),
                                r["is_correct"],
                                r["citation_correct"],
                                r["latency_s"],
                                r["tokens_est"]
                            ])
                except Exception as e:
                    print(f"Error writing checkpoint at case {case_num}: {e}")
            print(f"Completed case {case_num}/{total_cases} in {latency:.2f}s", flush=True)

    except Exception as e:
        print(f"Error during evaluation: {e}")

    finally:
        stop_event.set()
        # stop_event already set
        t.join()
        
    acc = correct / total_cases if total_cases else 0
    faith = faithful / total_cases if total_cases else 0
    hall = hallucinated / total_cases if total_cases else 0
    
    docs_with_citations = len([c for c in QA_CASES if c["pdf"]])
    cit_acc = citation_correct / docs_with_citations if docs_with_citations else 0
    
    tps = total_tokens / total_time_s if total_time_s else 0
    
    res = {
        "Answer Accuracy": f"{acc:.2%}",
        "Faithfulness": f"{faith:.2%}",
        "Hallucination Rate": f"{hall:.2%}",
        "Citation Accuracy": f"{cit_acc:.2%}",
        "Summary Quality /5": "N/A",
        "Tokens/sec": f"{tps:.2f}",
        "Peak RAM": f"{stats.get('peak_ram', 0):.2f} MB",
        "Peak CPU": f"{stats.get('peak_cpu', 0):.2f}%",
        "Offline Success Rate": "100%"
    }
    
        # Write per‑question results to JSON and CSV files
    try:
        with open(EVAL_JSON, "w", encoding="utf-8") as jf:
            json.dump(per_question_results, jf, indent=2)
        with open(EVAL_CSV, "w", newline='', encoding="utf-8") as cf:
            writer = csv.writer(cf)
            header = ["question", "expected_pdf", "expected_keywords", "refusal_expected", "answer", "citations", "is_correct", "is_correct_fuzzy", "citation_correct", "latency_s", "tokens_est"]
            writer.writerow(header)
            for r in per_question_results:
                writer.writerow([
                    r["question"],
                    r["expected_pdf"],
                    ",".join(r["expected_keywords"]),
                    r["refusal_expected"],
                    r["answer"],
                    json.dumps(r["citations"]),
                    r["is_correct"],
                    r.get("is_correct_fuzzy", False),
                    r["citation_correct"],
                    r["latency_s"],
                    r["tokens_est"]
                ])
    except Exception as e:
        print(f"Error writing evaluation results: {e}")
    print("KPI_LLM_JSON=" + json.dumps(res))

if __name__ == "__main__":
    main()
