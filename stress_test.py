import os
import time
import shutil
from pathlib import Path
import psutil

# Ensure the backend directory is in the Python path
import sys
sys.path.insert(0, str(Path(r"D:\RAGENG\files (1)\backend")))

from fastapi.testclient import TestClient
from app.main import app
from app.vector_store.faiss_store import FaissStore

client = TestClient(app)

def setup_test_data():
    source_dir = Path(r"D:\RAGENG\files (1)\backend\storage\uploads")
    target_dir = Path(r"D:\RAGENG\files (1)\backend\test_data\pdfs")
    target_dir.mkdir(parents=True, exist_ok=True)
    
    pdfs = list(source_dir.glob("*.pdf"))
    if not pdfs:
        print("No PDFs found in source directory.")
        return []
    
    # We will pick unique files based on size/name heuristic to avoid too many exact duplicates
    # Since filenames have UUID prefixes, let's just grab up to 10 for testing
    copied = []
    for pdf in pdfs[:10]:
        target_path = target_dir / pdf.name
        shutil.copy(pdf, target_path)
        copied.append(target_path)
    
    print(f"Copied {len(copied)} PDFs to {target_dir}")
    return copied

def print_memory_usage(label):
    process = psutil.Process(os.getpid())
    mem = process.memory_info().rss / (1024 * 1024)
    print(f"[{label}] Memory Usage: {mem:.2f} MB")

def run_stress_test():
    print("=== Starting Stress Test ===")
    pdfs = setup_test_data()
    if not pdfs:
        print("Failed to find PDFs for testing.")
        return

    print_memory_usage("Baseline")
    
    # Optional: Corrupt a PDF to test failure handling
    corrupted_pdf = Path(r"D:\RAGENG\files (1)\backend\test_data\pdfs\corrupted.pdf")
    corrupted_pdf.write_text("This is not a real PDF file!")
    pdfs.append(corrupted_pdf)

    total_ingestion_time = 0
    success_count = 0
    failure_count = 0
    
    # Ingest in batches of 1 (to not load all to RAM)
    batch_size = 1
    
    for i in range(0, len(pdfs), batch_size):
        batch = pdfs[i:i+batch_size]
        print(f"\nProcessing Batch {i//batch_size + 1}...")
        
        for pdf_path in batch:
            print(f"Ingesting {pdf_path.name}...")
            start_time = time.time()
            
            try:
                with open(pdf_path, "rb") as f:
                    response = client.post(
                        "/api/v1/rag/ingest",
                        files={"file": (pdf_path.name, f, "application/pdf")}
                    )
                
                duration = time.time() - start_time
                total_ingestion_time += duration
                
                if response.status_code == 200:
                    print(f"Success! Chunks: {response.json().get('total_chunks')} (Time: {duration:.2f}s)")
                    success_count += 1
                else:
                    print(f"Failed to ingest (Status {response.status_code}): {response.text} (Time: {duration:.2f}s)")
                    failure_count += 1
                    
            except Exception as e:
                duration = time.time() - start_time
                total_ingestion_time += duration
                print(f"Exception during ingestion: {e} (Time: {duration:.2f}s)")
                failure_count += 1
                
        print_memory_usage(f"After Batch {i//batch_size + 1}")

    print("\n=== Testing Retrieval (QA) ===")
    query = "What is the Royal Edge Project?"
    print(f"Query: '{query}'")
    
    start_qa_time = time.time()
    qa_response = client.post(
        "/api/v1/rag/ask",
        json={"query": query, "top_k": 3}
    )
    qa_duration = time.time() - start_qa_time
    
    if qa_response.status_code == 200:
        data = qa_response.json()
        print(f"QA Success! Time: {qa_duration:.2f}s")
        print(f"Answer: {data.get('answer')}")
        print(f"Citations: {len(data.get('citations', []))}")
    else:
        print(f"QA Failed! Status: {qa_response.status_code}")
        print(qa_response.text)

    print("\n=== Final Metrics ===")
    print(f"Total PDFs Attempted: {len(pdfs)}")
    print(f"Successful Ingestions: {success_count}")
    print(f"Failed Ingestions: {failure_count}")
    print(f"Total Ingestion Time: {total_ingestion_time:.2f}s")
    print(f"Average Time per PDF: {(total_ingestion_time/len(pdfs)):.2f}s" if len(pdfs) > 0 else "0s")
    print_memory_usage("Final")
    
    # Save results to a file for reporting
    with open("test_results.txt", "w") as f:
        f.write("TEST_RESULTS\n")
        f.write(f"Successful Ingestions: {success_count}\n")
        f.write(f"Failed Ingestions: {failure_count}\n")
        f.write(f"Total Ingestion Time: {total_ingestion_time:.2f}s\n")
        f.write(f"QA Time: {qa_duration:.2f}s\n")
        if qa_response.status_code == 200:
            f.write(f"QA Answer snippet: {qa_response.json().get('answer')[:100]}...\n")

if __name__ == '__main__':
    run_stress_test()
