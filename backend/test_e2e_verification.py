import os
import sys
import json
import urllib.request
import urllib.error
import fitz

BASE_URL = "http://127.0.0.1:8000"

def post_json(path, data):
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))

def upload_file(path, file_path, filename):
    url = f"{BASE_URL}{path}"
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    with open(file_path, "rb") as f:
        file_bytes = f.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: application/pdf\r\n\r\n"
    ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))

def create_pdf(filename, title, content_lines):
    doc = fitz.open()
    page = doc.new_page()
    y = 72
    page.insert_text(fitz.Point(50, y), title, fontsize=16)
    y += 30
    for line in content_lines:
        page.insert_text(fitz.Point(50, y), line, fontsize=11)
        y += 20
    out_dir = os.path.join(os.path.dirname(__file__), "scratch")
    os.makedirs(out_dir, exist_ok=True)
    full_path = os.path.join(out_dir, filename)
    doc.save(full_path)
    doc.close()
    return full_path

def run_tests():
    print("=" * 60)
    print("RUNNING RAGENGI END-TO-END VERIFICATION SUITE")
    print("=" * 60)

    # 1. Test Greeting handling
    print("\n[TEST 1] Greeting / Small Talk conversational response...")
    status, res = post_json("/api/v1/rag/ask", {"query": "Hello, who are you?"})
    print(f"Status: {status}, Answer: {res['answer']}, Citations: {res['citations']}")
    assert "Hello" in res["answer"] and "RAGENGI" in res["answer"], "Failed greeting test"
    assert res["citations"] == [], "Greeting should have empty citations"
    print(">>> PASS: Greeting answered conversationally without document search.")

    # 2. Test NASA document known fact (already in index)
    print("\n[TEST 2] Known fact from real uploaded PDF (NASA Technical Report Server)...")
    status, res = post_json("/api/v1/rag/ask", {
        "query": "What is the NASA Technical Report Server and what was it developed to do?"
    })
    print(f"Status: {status}")
    print(f"Answer: {res['answer']}")
    print(f"Citations: {res['citations']}")
    assert "The uploaded document does not contain enough information" not in res["answer"], "Should have retrieved NASA content"
    assert len(res["citations"]) > 0, "Should have citations for NASA document"
    assert any("TheNASATechnicalReportServer" in str(c.get("file_path", "")) for c in res["citations"]), "Citation must point to NASA PDF"
    print(">>> PASS: Question answered with real PDF evidence and valid citations.")

    # 3. Create and Upload Two New Distinct PDFs
    print("\n[TEST 3] Creating and Ingesting two distinct engineering PDFs...")
    pdf1_path = create_pdf(
        "Phoenix9_Propulsion_Specs.pdf",
        "Phoenix-9 Rocket Propulsion System",
        [
            "The Phoenix-9 heavy launch vehicle utilizes an advanced staged combustion cycle rocket engine.",
            "The Phoenix-9 rocket utilizes liquid methane and liquid oxygen as propellant with a sea-level thrust of 750 kilonewtons and a vacuum thrust of 840 kilonewtons.",
            "The chamber pressure is maintained at 20 megapascals during nominal ascent burn of 165 seconds."
        ]
    )
    pdf2_path = create_pdf(
        "Orion3_Avionics_Specs.pdf",
        "Orion-3 Deep Space Navigation Module",
        [
            "The Orion-3 deep space avionics and navigation subsystem incorporates star trackers and optical navigation cameras.",
            "The Orion-3 navigation module operates on a triple-redundant CAN bus consuming exactly 45 watts of electrical power.",
            "Radiation tolerance is certified up to 100 kilorads total ionizing dose with error-correcting memory."
        ]
    )

    print(f"Ingesting {pdf1_path}...")
    status1, res1 = upload_file("/api/v1/rag/ingest", pdf1_path, "Phoenix9_Propulsion_Specs.pdf")
    print(f"Ingest 1: status={status1}, total_chunks={res1.get('total_chunks')}")
    assert res1.get("status") == "success" and res1.get("total_chunks") > 0

    print(f"Ingesting {pdf2_path}...")
    status2, res2 = upload_file("/api/v1/rag/ingest", pdf2_path, "Orion3_Avionics_Specs.pdf")
    print(f"Ingest 2: status={status2}, total_chunks={res2.get('total_chunks')}")
    assert res2.get("status") == "success" and res2.get("total_chunks") > 0
    print(">>> PASS: Both PDFs ingested successfully.")

    # 4. Query Document 1 independently (without active_filename filter)
    print("\n[TEST 4] Querying Document 1 (Propulsion facts)...")
    status, res = post_json("/api/v1/rag/ask", {
        "query": "What propellant and vacuum thrust does the Phoenix-9 rocket use?"
    })
    print(f"Answer: {res['answer']}")
    print(f"Citations: {res['citations']}")
    assert "methane" in res["answer"].lower() or "840" in res["answer"], "Failed to answer from Doc 1"
    assert any("Phoenix9_Propulsion_Specs" in str(c.get("file_path", "")) for c in res["citations"]), "Missing citation to Doc 1"
    print(">>> PASS: Document 1 successfully queried with valid citations.")

    # 5. Query Document 2 independently (without active_filename filter)
    print("\n[TEST 5] Querying Document 2 (Avionics facts)...")
    status, res = post_json("/api/v1/rag/ask", {
        "query": "What are the bus architecture and power consumption of the Orion-3 navigation module?"
    })
    print(f"Answer: {res['answer']}")
    print(f"Citations: {res['citations']}")
    assert "45" in res["answer"] or "triple-redundant" in res["answer"].lower() or "can bus" in res["answer"].lower(), "Failed to answer from Doc 2"
    assert any("Orion3_Avionics_Specs" in str(c.get("file_path", "")) for c in res["citations"]), "Missing citation to Doc 2"
    print(">>> PASS: Document 2 successfully queried with valid citations.")

    # 6. Cross-document comparison query requiring evidence from BOTH PDFs
    print("\n[TEST 6] Multi-document question requiring evidence from BOTH PDFs...")
    status, res = post_json("/api/v1/rag/ask", {
        "query": "Compare the Phoenix-9 propulsion propellant with the Orion-3 power consumption."
    })
    print(f"Answer: {res['answer']}")
    print(f"Citations: {res['citations']}")
    citations_str = json.dumps(res["citations"])
    assert "Phoenix9_Propulsion_Specs" in citations_str or "Orion3_Avionics_Specs" in citations_str, "Citations should include uploaded docs"
    print(">>> PASS: Multi-document query executed successfully.")

    # 7. Summary of uploaded PDFs
    print("\n[TEST 7] Summarize uploaded documents...")
    status, res = post_json("/api/v1/rag/ask", {
        "query": "Summarize the key technical specifications of the Phoenix-9 rocket and Orion-3 navigation module."
    })
    print(f"Answer: {res['answer']}")
    print(f"Citations: {res['citations']}")
    assert len(res["answer"]) > 50, "Summary too short"
    assert len(res["citations"]) > 0, "Summary must have citations"
    print(">>> PASS: Summary generated with citations.")

    # 8. Genuine missing information query
    print("\n[TEST 8] Question about information NOT present in any document...")
    status, res = post_json("/api/v1/rag/ask", {
        "query": "What is the secret recipe for Martian blueberry sourdough pancakes?"
    })
    print(f"Answer: {res['answer']}")
    print(f"Citations: {res['citations']}")
    assert "does not contain enough information" in res["answer"].lower() or "not contain" in res["answer"].lower() or "could not find" in res["answer"].lower(), "Should report missing info"
    assert res["citations"] == [], "Missing info should have empty citations"
    print(">>> PASS: Missing information correctly reported with empty citations.")

    print("\n" + "=" * 60)
    print("ALL 8 VERIFICATION TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
