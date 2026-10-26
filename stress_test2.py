import os
import time
import shutil
from pathlib import Path
import psutil
import sys

sys.path.insert(0, str(Path(r"D:\RAGENG\files (1)\backend")))
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def setup_test_data():
    source_dir = Path(r"D:\RAGENG\files (1)\backend\storage\uploads")
    target_dir = Path(r"D:\RAGENG\files (1)\backend\test_data\pdfs")
    target_dir.mkdir(parents=True, exist_ok=True)
    
    pdfs = list(source_dir.glob("*.pdf"))
    if not pdfs:
        return []
    
    copied = []
    for pdf in pdfs[:3]:
        target_path = target_dir / pdf.name
        shutil.copy(pdf, target_path)
        copied.append(target_path)
    return copied

def run_extended_test():
    print("=== Starting Extended Test ===")
    pdfs = setup_test_data()
    
    # 1. Ingest normal PDFs
    for pdf_path in pdfs:
        with open(pdf_path, "rb") as f:
            response = client.post("/api/v1/rag/ingest", files={"file": (pdf_path.name, f, "application/pdf")})
        print(f"Ingested {pdf_path.name}: Status {response.status_code}")

    # 2. Duplicate ingestion
    duplicate_pdf = pdfs[0]
    print(f"\nIngesting DUPLICATE {duplicate_pdf.name}...")
    with open(duplicate_pdf, "rb") as f:
        dup_res = client.post("/api/v1/rag/ingest", files={"file": (duplicate_pdf.name, f, "application/pdf")})
    print(f"Duplicate Ingest Status: {dup_res.status_code}")

    # 3. Valid QA with citation check
    valid_q = "What is the Royal Edge Project?"
    print(f"\nTesting valid query: '{valid_q}'")
    valid_ans = client.post("/api/v1/rag/ask", json={"query": valid_q, "top_k": 3})
    print(f"Valid QA Status: {valid_ans.status_code}")
    if valid_ans.status_code == 200:
        data = valid_ans.json()
        print(f"Answer: {data.get('answer')[:100]}...")
        print(f"Citations count: {len(data.get('citations', []))}")
        if data.get('citations'):
            print(f"First Citation File: {data['citations'][0].get('file_path')}")

    # 4. Unsupported / Nonsense QA
    nonsense_q = "What is the recipe for chocolate chip cookies in this document?"
    print(f"\nTesting unsupported query: '{nonsense_q}'")
    nons_ans = client.post("/api/v1/rag/ask", json={"query": nonsense_q, "top_k": 3})
    print(f"Unsupported QA Status: {nons_ans.status_code}")
    if nons_ans.status_code == 200:
        print(f"Answer: {nons_ans.json().get('answer')}")

if __name__ == '__main__':
    run_extended_test()
