<div align="center">

# ⚙️ RAGENGI
### Engineering Intelligence. Completely Offline.

**An AI-powered Engineering Assistant that runs entirely on your device —**  
**no internet, no cloud, no data leakage.**

---

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Android](https://img.shields.io/badge/Android-API%2024%2B-3DDC84?logo=android&logoColor=white)](https://developer.android.com)
[![Kotlin](https://img.shields.io/badge/Kotlin-2.0-7F52FF?logo=kotlin&logoColor=white)](https://kotlinlang.org)
[![Jetpack Compose](https://img.shields.io/badge/Jetpack%20Compose-Material%203-4285F4?logo=jetpackcompose&logoColor=white)](https://developer.android.com/compose)
[![llama.cpp](https://img.shields.io/badge/LLM-llama.cpp%20GGUF-FF6B35)](https://github.com/ggerganov/llama.cpp)
[![FAISS](https://img.shields.io/badge/VectorDB-FAISS-0067B8?logo=meta)](https://faiss.ai)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Offline](https://img.shields.io/badge/Operation-100%25%20Offline-success)](.)

</div>

---

## 📖 Project Overview

**RAGENGI** is a fully offline, CPU-only, privacy-first AI assistant designed specifically for engineers. It combines **Retrieval-Augmented Generation (RAG)** with a specialized **Engineering Intelligence Layer** to allow users to query their own engineering documents — PDFs, IS codes, ASTM standards, IEEE papers — and receive structured, cited, and domain-aware answers.

Unlike generic AI tools that depend on cloud APIs, RAGENGI keeps **every byte of your data on-device**. Upload your confidential engineering documents, ask complex technical questions, and receive answers complete with formulas, standard references, page citations, and unit-aware reasoning — all without a single network request after setup.

> 💡 **Use Case:** An engineer uploads a 300-page structural design PDF and the IS 456:2000 code, then asks: *"What is the minimum reinforcement ratio for beams?"* RAGENGI finds the exact chunks, runs the local LLM, and returns a structured answer with the relevant formula, IS code citation, and page number.

---

## ✨ Features

### Core RAG Pipeline
| Feature | Description |
|---|---|
| 📄 **PDF Extraction** | Native text extraction using `pdfplumber` with per-page awareness |
| 👁️ **OCR Fallback** | Automatic Tesseract OCR for scanned/image-based pages |
| ✂️ **Smart Chunking** | Page-aware, overlapping chunking that preserves context boundaries |
| 🧮 **Dense Embeddings** | `all-MiniLM-L6-v2` via `sentence-transformers` at 384 dimensions |
| 🔍 **FAISS Vector Store** | `IndexFlatL2` with full disk persistence and incremental updates |
| 🎯 **Semantic Retrieval** | Configurable Top-K retrieval with L2 distance scoring |
| 🤖 **Local LLM** | `llama.cpp` with GGUF models — CPU-only, zero GPU dependency |

### Engineering Intelligence Layer
| Feature | Description |
|---|---|
| 🏗️ **Domain Classifier** | Auto-detects Civil / Mechanical / Electrical / Computer Engineering |
| ➕ **Formula Extractor** | Regex-based mathematical equation detection and storage |
| 📋 **Table Extractor** | Heuristic detection of tabular data from PDF text |
| 📏 **Standards Detector** | Extracts IS, ASTM, IEEE, ISO, IEC code references automatically |
| ⚖️ **Unit Intelligence** | Detects 30+ engineering units; supports conversion (MPa↔kPa, °C↔K) |
| 📐 **Reference Linker** | Links Figure/Table/Appendix references to source pages |
| 📑 **Answer Formatter** | Structured output: Summary + Formulas + Standards + Citations |

### Multi-Document Knowledge Base
| Feature | Description |
|---|---|
| 📚 **Multi-PDF Indexing** | Index and manage hundreds of documents simultaneously |
| 📁 **Collections** | Organize documents into folders/categories |
| 📊 **Document Statistics** | Pages, Chunks, Embeddings, Index Size per document |
| 🔄 **Re-indexing** | Update embeddings when a document changes |
| 🗑️ **Safe Deletion** | Removes document from Room DB with FAISS garbage collection |

### Android Application
| Feature | Description |
|---|---|
| 💬 **ChatGPT-Style UI** | Modern Jetpack Compose chat interface with message bubbles |
| 🎓 **Engineering Answer Cards** | Color-coded domain badges, expandable formula/standards sections |
| 🧙 **First-Time Setup Wizard** | Guided model download with progress bar and RAM safety check |
| 📱 **Material Design 3** | Premium, dark-mode-ready UI with smooth animations |
| 💾 **Room Database** | Full local chat history with search and delete |
| 🔒 **Privacy Banner** | Persistent "No Cloud, No Data Leakage" indicator |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    📱 ANDROID APPLICATION                        │
│   Jetpack Compose UI → ViewModel → Repository → Retrofit/Room   │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTP (localhost / 10.0.2.2:8000)
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    🖥️ FASTAPI BACKEND                            │
│                                                                 │
│  POST /api/v1/rag/ingest          POST /api/v1/rag/ask          │
│         │                                  │                    │
│    ┌────▼────────────────┐     ┌───────────▼──────────┐        │
│    │  INGESTION PIPELINE │     │   QA PIPELINE        │        │
│    │                     │     │                      │        │
│    │  PDF Extractor       │     │  EmbeddingService    │        │
│    │      ↓              │     │      ↓               │        │
│    │  OCR Service         │     │  FAISS Search        │        │
│    │      ↓              │     │      ↓               │        │
│    │  Chunker             │     │  LLM (llama.cpp)     │        │
│    │      ↓              │     │      ↓               │        │
│    │  EmbeddingService    │     │  EngineeringFormatter│        │
│    │      ↓              │     └──────────────────────┘        │
│    │  FaissStore          │                                     │
│    └─────────────────────┘                                     │
│                                                                 │
│         Engineering Intelligence Layer (Module 12)             │
│    Domain · Formulas · Standards · Units · Tables · Refs        │
└─────────────────────────────────────────────────────────────────┘
                               │
              ┌────────────────┼─────────────────┐
              ▼                ▼                  ▼
    llama-2-7b.gguf   all-MiniLM-L6-v2.onnx  vector_store.index
     (GGUF Model)       (Embedding Model)      (FAISS Index)
```

---

## 🛠️ Technology Stack

### Backend
| Layer | Technology | Version |
|---|---|---|
| API Framework | FastAPI + Uvicorn | 0.111+ |
| PDF Parsing | pdfplumber | Latest |
| OCR | Tesseract + pytesseract + pdf2image | Latest |
| Embeddings | sentence-transformers | 3.x |
| Embedding Model | all-MiniLM-L6-v2 | — |
| Vector Store | FAISS (faiss-cpu) | 1.7+ |
| Local LLM | llama-cpp-python | Latest |
| LLM Format | GGUF (e.g., Llama 2 7B Q4) | — |
| Schema Validation | Pydantic v2 | 2.x |
| Testing | pytest + unittest.mock | Latest |

### Android
| Layer | Technology |
|---|---|
| Language | Kotlin 2.0 |
| UI Framework | Jetpack Compose + Material Design 3 |
| Architecture | MVVM (ViewModel + StateFlow) |
| Networking | Retrofit 2 + OkHttp + Gson |
| Local Database | Room (SQLite) |
| Settings | DataStore |
| Concurrency | Kotlin Coroutines + Flow |
| Min SDK | API 24 (Android 7.0) |
| Target SDK | API 36 |

---

## 📁 Folder Structure

```
RAGENGI/
│
├── backend/                          # Python FastAPI Backend
│   ├── app/
│   │   ├── main.py                   # FastAPI entry point
│   │   ├── core/
│   │   │   ├── config.py             # Application-wide settings
│   │   │   └── logging.py            # Logging configuration
│   │   ├── ingestion/
│   │   │   ├── pdf_extractor.py      # Module 1: PDF Extraction
│   │   │   ├── ocr_service.py        # Module 2: OCR Service
│   │   │   ├── chunker.py            # Module 3: Chunking Service
│   │   │   └── pipeline.py           # Ingestion Orchestrator
│   │   ├── embeddings/
│   │   │   └── embedding_service.py  # Module 4: Embedding Service
│   │   ├── vector_store/
│   │   │   └── faiss_store.py        # Module 5: FAISS Vector Store
│   │   ├── retrieval/
│   │   │   └── retrieval_service.py  # Module 6: Retrieval Service
│   │   ├── llm/
│   │   │   └── llm_service.py        # Module 7: Local LLM (llama.cpp)
│   │   ├── intelligence/
│   │   │   ├── detectors.py          # Module 12: All Extractors
│   │   │   ├── analyzer.py           # Module 12: Engineering Analyzer
│   │   │   └── formatter.py          # Module 12: Answer Formatter
│   │   ├── api/
│   │   │   └── routes/
│   │   │       ├── documents.py      # Modules 1–3 endpoints
│   │   │       └── rag.py            # Module 8: E2E RAG endpoints
│   │   └── schemas/
│   │       ├── pdf.py                # PDF request/response schemas
│   │       ├── ocr.py                # OCR schemas
│   │       ├── chunk.py              # Chunk schemas
│   │       └── rag.py                # RAG request/response schemas
│   ├── tests/
│   │   └── unit/
│   │       ├── test_embedding_service.py
│   │       ├── test_faiss_store.py
│   │       ├── test_retrieval_service.py
│   │       ├── test_llm_service.py
│   │       ├── test_rag_routes.py
│   │       └── test_engineering_intelligence.py
│   └── storage/
│       ├── uploads/                  # Uploaded PDFs
│       ├── faiss_index/              # Persisted FAISS index
│       └── models/                   # Local GGUF model files
│
└── android/                          # Android Application
    └── app/src/main/java/com/example/ragengi/
        ├── MainActivity.kt
        ├── data/
        │   ├── model/
        │   │   ├── Models.kt         # Core data classes
        │   │   └── EngineeringModels.kt
        │   ├── remote/
        │   │   └── RagApi.kt         # Retrofit interface
        │   ├── repository/
        │   │   ├── RagRepository.kt
        │   │   └── KnowledgeBaseRepository.kt
        │   └── local/
        │       ├── StorageManager.kt
        │       └── db/
        │           ├── Entities.kt
        │           ├── DocumentDao.kt
        │           └── KnowledgeBaseDb.kt
        └── ui/
            ├── theme/
            │   └── Theme.kt
            ├── viewmodel/
            │   └── ChatViewModel.kt
            ├── screens/
            │   ├── HomeScreen.kt
            │   ├── SetupWizardScreen.kt
            │   └── KnowledgeBaseScreen.kt
            └── components/
                └── EngineeringAnswerCard.kt
```

---

## ⚙️ Installation Guide

### Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | 3.10+ | Backend runtime |
| pip | Latest | `python -m pip install --upgrade pip` |
| Tesseract OCR | 5.x | [Download](https://github.com/tesseract-ocr/tesseract) |
| Android Studio | Meerkat 2025.1+ | For Android app |
| JDK | 17 | Required for Android build |
| GGUF Model | Any Q4 | e.g., `llama-2-7b-chat.Q4_K_M.gguf` |

---

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/ragengi.git
cd ragengi
```

### 2. Backend Setup

```bash
# Navigate to backend
cd backend

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Download a GGUF model and place it in storage/models/
# Example: https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF

# Start the FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at: **http://localhost:8000**  
Interactive docs at: **http://localhost:8000/docs**

### 3. Android Setup

```bash
# Open the android/ directory in Android Studio
# Sync Gradle dependencies
# Connect a device or start an emulator (API 24+)
# Run the app using the green ▶ button
```

> **Note:** The Android app connects to the FastAPI backend at `http://10.0.2.2:8000` by default (Android emulator localhost alias). Update the base URL in `RagApi.kt` if running on a physical device.

### 4. Running Tests

```bash
# From the backend directory
cd backend
pytest tests/ -v
```

---

## 🚀 Usage Instructions

### Ingest a Document

```bash
curl -X POST "http://localhost:8000/api/v1/rag/ingest" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "storage/uploads/IS_456_2000.pdf"}'
```

**Response:**
```json
{
  "file_path": "storage/uploads/IS_456_2000.pdf",
  "total_chunks": 412,
  "status": "success"
}
```

### Ask a Question

```bash
curl -X POST "http://localhost:8000/api/v1/rag/ask" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the minimum cover for reinforcement in beams?", "top_k": 5}'
```

**Response:**
```json
{
  "query": "What is the minimum cover for reinforcement in beams?",
  "answer": "As per IS 456:2000 Clause 26.4, the minimum clear cover for beams is 25 mm for mild exposure and 45 mm for severe exposure conditions...",
  "citations": [
    {"chunk_id": 87, "page_number": 54},
    {"chunk_id": 88, "page_number": 55}
  ]
}
```

### Health Check

```bash
curl http://localhost:8000/api/v1/health
# {"status": "ok", "service": "RAGENGI"}
```

---

## 📱 Android App Features

### Setup Wizard
On first launch, the app detects missing models and walks the user through a guided download process with a live progress bar and RAM safety validation (minimum 4 GB required).

### Chat Interface
- **ChatGPT-style bubbles** with user and AI messages clearly distinguished
- **Typing indicator** while the local LLM processes
- **EngineeringAnswerCard** for structured responses with collapsible sections

### Engineering Answer Card
```
┌──────────────────────────────────────┐
│ 🟢 Civil Engineering                 │
│                                      │
│ Technical Summary:                   │
│ The minimum cover for beams is...   │
│                                      │
│ ▶ Formulas Detected (1)             │
│ ▶ Standards Referenced (2)          │
│   • IS: IS 456:2000                 │
│ ▶ Engineering Units (3)             │
│ ▶ Figures / Tables                  │
│                                      │
│ Citations: [P54, C87] • [P55, C88]  │
└──────────────────────────────────────┘
```

### Knowledge Base Screen
- View all indexed documents with statistics
- Organize documents into collections/folders
- One-tap Re-index or Safe Delete
- Shows Pages, Chunks, Embeddings, and Index Size

---

## 🔒 Offline AI Capabilities

RAGENGI is engineered from the ground up for **complete offline operation**:

| Capability | Implementation |
|---|---|
| **No internet required** | All models cached on-device after first setup |
| **CPU-only execution** | `n_gpu_layers=0` in llama.cpp; `device="cpu"` in sentence-transformers |
| **Local vector search** | FAISS flat index runs entirely in RAM |
| **Local LLM inference** | llama.cpp with memory-mapped GGUF (mmap for RAM efficiency) |
| **RAM optimization** | Minimum 4 GB check before model loading; mmap prevents full model load |
| **No telemetry** | Zero analytics, no crash reporting, no usage tracking |
| **Offline embedding** | `all-MiniLM-L6-v2` runs locally via sentence-transformers |

> **Privacy Guarantee:** Your documents never leave your device. Zero API calls to OpenAI, Google, or any cloud provider.

---

## 🔭 Future Scope

| Enhancement | Description |
|---|---|
| 📲 **Full On-Device Android** | Replace Retrofit with llama.cpp JNI bindings — no laptop backend needed |
| 🎙️ **Voice-to-Text Input** | Offline STT using Vosk or Whisper.cpp |
| 🔊 **Text-to-Speech** | Read answers aloud using Android TTS API |
| 🌐 **Multi-Language PDF** | Support for Hindi, French, German engineering documents |
| 🔗 **LAN Knowledge Sharing** | Share indexed documents over local WiFi — still offline, never cloud |
| 🧠 **Fine-Tuned LLM** | A domain-adapted engineering LLM for higher answer accuracy |
| 📊 **Chart & Graph QA** | Visual question answering over engineering graphs and diagrams |
| 🔐 **Document Encryption** | AES-256 encryption for stored PDFs and indexes on Android |

---

## 👥 Contributors

| Name | Role |
|---|---|
| **Prithviraj** | Project Lead, System Architect, Full-Stack Developer |

> *Contributions welcome! Please open an issue before submitting a pull request.*

---

## 📄 License

```
MIT License

Copyright (c) 2026 RAGENGI Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```

---

<div align="center">

**Built with ❤️ for Engineers, by Engineers.**

*No cloud. No compromise. No data leakage.*

⭐ **Star this repository if RAGENGI helped your engineering workflow!**

</div>
