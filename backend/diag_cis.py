"""Check CIS chunks for keyword coverage."""
import sys, warnings
warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "d:/RAGENG/files (1)/backend")
from app.vector_store.faiss_store import FaissStore
from pathlib import Path

BACKEND_DIR = Path("d:/RAGENG/files (1)/backend")
fs = FaissStore(index_path=str(BACKEND_DIR / "storage" / "vector_store"), dimension=384)
fs.load_index()

CIS_PDF = "CIS-MS-ISAC-NIST-Cybersecurity-Framework-Policy-Template-Guide.pdf"
cis_chunks = []
for i in range(fs.index.ntotal):
    meta = fs.get_metadata(i)
    if meta and CIS_PDF in str(meta.get("file_path", "")):
        cis_chunks.append(meta)

print("Total CIS chunks:", len(cis_chunks))

# Chunks with 'cis' keyword
cis_kw = [c for c in cis_chunks if " cis " in c.get("chunk_text", "").lower() or
          "center for internet security" in c.get("chunk_text", "").lower() or
          c.get("chunk_text", "").lower().startswith("cis")]
print("Chunks with 'cis' keyword:", len(cis_kw))
for c in cis_kw[:5]:
    pn = c["page_number"]
    txt = c["chunk_text"][:200]
    print("  p" + str(pn) + ": " + repr(txt))

# Chunks with ms-isac
ms_kw = [c for c in cis_chunks if "ms-isac" in c.get("chunk_text", "").lower()]
print("Chunks with MS-ISAC:", len(ms_kw))
for c in ms_kw[:5]:
    pn = c["page_number"]
    txt = c["chunk_text"][:200]
    print("  p" + str(pn) + ": " + repr(txt))
