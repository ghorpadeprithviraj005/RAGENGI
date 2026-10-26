import os
import re
import logging
import shutil
import uuid
import threading
from datetime import datetime, timezone
import hashlib
from typing import List, Optional, Tuple
from fastapi import APIRouter, HTTPException, status, File, UploadFile, Form, Header, Query, Depends
from app.llm.llm_service import LLMService, LLMServiceError

from app.core.config import settings
from app.ingestion.ocr_service import OCRService
from app.ingestion.pipeline import DocumentIngestionPipeline
from app.ingestion.chunker import PDFChunker
from app.embeddings.embedding_service import EmbeddingService
from app.vector_store.faiss_store import FaissStore
from app.retrieval.retrieval_service import RetrievalService
from app.llm.llm_service import LLMService

from app.schemas.rag import (
    IngestionResponse,
    QARequest,
    QAResponse,
    DeleteDocumentResponse,
    CleanupResponse,
    EligibleDocument,
    EligibleDocumentsResponse,
    TouchDocumentResponse,
    CleanupRunRequest
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["rag"])

# Concurrency lock to coordinate ingestion, cleanup, and deletion
_operation_lock = threading.RLock()

# Initialize all modular services as singletons for the router
_ocr_service = OCRService(dpi=settings.OCR_DPI, language=settings.OCR_LANGUAGE)
_pipeline = DocumentIngestionPipeline(ocr_service=_ocr_service)
_chunker = PDFChunker()

faiss_dir = os.path.join(settings.BASE_DIR, "storage", "vector_store")
llm_model_path = os.path.join(settings.BASE_DIR, "storage", "models", "llama-2-7b.gguf")

# Safe initialization of heavy services
try:
    _embedding_service = EmbeddingService(model_name="all-MiniLM-L6-v2")
except Exception as e:
    logger.warning(f"EmbeddingService failed to initialize: {e}. Using dummy service.")
    class DummyEmbeddingService:
        def __init__(self, *args, **kwargs):
            pass
        def generate_embeddings(self, *args, **kwargs):
            return []
    _embedding_service = DummyEmbeddingService()

_faiss_store = FaissStore(index_path=faiss_dir, dimension=384)
_retrieval_service = RetrievalService(
    embedding_service=_embedding_service,
    faiss_store=_faiss_store,
    default_top_k=40,
)
try:
    _llm_service = LLMService(
        model_path=llm_model_path,
        context_window=4096,
        max_tokens=128,
        chat_format="llama-2",
        n_threads=min(4, os.cpu_count() or 4),
    )
except Exception as e:
    logger.error(f"Failed to initialize LLMService: {e}")
    raise

# Store the active filename globally to include in LLM context
_active_filename: Optional[str] = None

PROTECTED_TERMS = ["models", "llama", ".gguf", ".bin", ".onnx", "vector_store"]


def _verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None)
):
    """
    Protect cleanup and sensitive deletion operations.
    Validates against settings.CLEANUP_API_KEY.
    """
    expected_key = getattr(settings, "CLEANUP_API_KEY", "ragengi-secure-cleanup-key")
    if not expected_key:
        return True

    # Check X-API-Key header
    if x_api_key and x_api_key == expected_key:
        return True

    # Check Authorization: Bearer <key>
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer" and parts[1] == expected_key:
            return True

    logger.warning("Unauthorized access attempt to protected cleanup/delete API")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized: Missing or invalid API key for cleanup/deletion."
    )


def _validate_safe_filename(filename: str) -> str:
    """
    Prevent path traversal, empty filenames, and protect system/model files.
    """
    if not filename or not filename.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename cannot be empty."
        )

    clean_name = filename.strip()
    if ".." in clean_name or "/" in clean_name or "\\" in clean_name:
        # Prevent path traversal
        clean_name = os.path.basename(clean_name)

    lower_name = clean_name.lower()
    for term in PROTECTED_TERMS:
        if term in lower_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Safety violation: Cannot operate on protected system/model file '{clean_name}'."
            )

    return clean_name


def _parse_iso_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    """Parse an ISO 8601 string to a timezone-aware UTC datetime."""
    if not dt_str:
        return None
    try:
        clean_str = dt_str.strip()
        # Handle query parameters where '+' was decoded as a space ' '
        if " " in clean_str and ("+" not in clean_str):
            parts = clean_str.rsplit(" ", 1)
            if len(parts) == 2 and (":" in parts[1] or parts[1].isdigit()):
                clean_str = f"{parts[0]}+{parts[1]}"
        if clean_str.endswith("Z"):
            clean_str = clean_str[:-1] + "+00:00"
        dt = datetime.fromisoformat(clean_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt
    except Exception as e:
        logger.warning(f"Could not parse timestamp '{dt_str}': {e}")
        return None


def _check_inactivity(
    last_access_str: Optional[str],
    now_dt: datetime,
    inactivity_days: int
) -> Tuple[bool, Optional[float], Optional[datetime]]:
    """
    Determines if a document is inactive and eligible for cleanup.
    CRITICAL RULE: Missing timestamps NEVER trigger deletion.
    """
    if not last_access_str:
        return False, None, None

    last_dt = _parse_iso_datetime(last_access_str)
    if last_dt is None:
        # Corrupt or unparseable timestamp: NEVER delete
        return False, None, None

    elapsed_seconds = (now_dt - last_dt).total_seconds()
    if elapsed_seconds < 0:
        # Timestamp is in the future
        return False, 0.0, last_dt

    elapsed_days = elapsed_seconds / 86400.0
    threshold_seconds = inactivity_days * 86400.0
    is_expired = elapsed_seconds >= threshold_seconds
    return is_expired, elapsed_days, last_dt


@router.post(
    "/ingest",
    response_model=IngestionResponse,
    summary="Ingest a document into the RAG pipeline",
)
def ingest_document(
    file: UploadFile = File(
        ...,
        description="Document to ingest (PDF, DOCX, PPTX, XLSX, TXT, CSV, PNG, JPG, JPEG, etc.)",
    ),
    chunk_size: int | None = Form(None, description="Override default chunk size"),
    chunk_overlap: int | None = Form(None, description="Override default chunk overlap"),
) -> IngestionResponse:
    """
    End-to-End Ingestion:
    1. Save uploaded file to storage/uploads/
    2. Detect format and extract text via universal loader pipeline
    3. Chunk, Embed, Store in FAISS with last_access timestamp
    Coordinated safely via _operation_lock.
    """
    global _active_filename

    with _operation_lock:
        _active_filename = file.filename
        upload_dir = os.path.join(settings.BASE_DIR, "storage", "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        unique_filename = f"{uuid.uuid4()}_{file.filename}"
        saved_file_path = os.path.join(upload_dir, unique_filename)

        with open(saved_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Compute SHA-256 hash of the saved file for metadata
        hasher = hashlib.sha256()
        with open(saved_file_path, "rb") as f_hash:
            for chunk in iter(lambda: f_hash.read(8192), b""):
                hasher.update(chunk)
        file_hash_hex = hasher.hexdigest()

        try:
            extraction_result = _pipeline.process(saved_file_path)

            chunking_result = _chunker.chunk_document(
                extraction_result,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )

            if not chunking_result.chunks:
                return IngestionResponse(
                    file_path=saved_file_path, total_chunks=0, status="no_content"
                )

            embeddings_data = _embedding_service.generate_embeddings(chunking_result.chunks)
            now_iso = datetime.now(timezone.utc).isoformat()
            for e in embeddings_data:
                e["metadata"]["file_path"] = saved_file_path
                e["metadata"]["last_access"] = now_iso
                e["metadata"]["page_count"] = extraction_result.page_count
                e["metadata"]["file_hash"] = file_hash_hex
                e["metadata"]["original_filename"] = file.filename

            _faiss_store.add_embeddings(embeddings_data)
            _faiss_store.save_index()

            logger.info(
                "Successfully ingested %d chunks from %s with last_access %s",
                len(embeddings_data),
                saved_file_path,
                now_iso,
            )
            return IngestionResponse(
                file_path=saved_file_path,
                total_chunks=len(embeddings_data),
                status="success",
            )

        except ValueError as ve:
            logger.error("Unsupported file type: %s", file.filename)
            raise HTTPException(status_code=400, detail=str(ve)) from ve
        except Exception as exc:
            logger.exception("Unexpected error during ingestion for %s", file.filename)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ingestion failed: {str(exc)}",
            ) from exc


GREETING_PATTERNS = {
    "hi", "hello", "hey", "greetings", "good morning", "good afternoon",
    "good evening", "who are you", "what can you do", "help"
}


def _is_greeting(query: str) -> bool:
    clean = re.sub(r"[^\w\s]", "", query).strip().lower()
    if clean in GREETING_PATTERNS:
        return True
    return any(clean.startswith(f"{g} ") or clean == g or clean.startswith(g) for g in GREETING_PATTERNS)


@router.post(
    "/ask",
    response_model=QAResponse,
    summary="Ask a question against ingested documents",
)
def ask_question(request: QARequest) -> QAResponse:
    """
    End-to-End Question Answering:
    1. Check for conversational greetings/small talk without searching documents unnecessarily.
    2. Search across ALL uploaded PDFs by default (or scope to active_filename if explicitly requested).
    3. Generate evidence-based answer using local LLM with citations.
    4. Provide distinct handling for empty indexes, missing information, and generation errors.
    """
    try:
        # Handle greetings and small talk conversationally
        if _is_greeting(request.query):
            logger.info("Direct greeting response for query: %r", request.query)
            return QAResponse(
                query=request.query,
                answer=(
                    "Hello! I am RAGENGI, your offline engineering and document assistant. "
                    "Ask me questions about your uploaded documents, request summaries, "
                    "or compare information across documents."
                ),
                citations=[],
            )

        # Search ALL uploaded PDFs by default unless explicitly scoped by caller
        effective_active_file = request.active_filename

        # Verify whether any documents exist in the vector store
        if _faiss_store.index is None or _faiss_store.index.ntotal == 0:
            logger.info("No documents indexed in vector store for query: %r", request.query)
            return QAResponse(
                query=request.query,
                answer="No documents have been uploaded yet. Please upload a PDF to get started.",
                citations=[],
            )

        logger.info(
            "QA Request received: query=%r, top_k=%s, active_file=%s",
            request.query, request.top_k, effective_active_file
        )

        retrieved_chunks = _retrieval_service.search(
            query=request.query,
            top_k=request.top_k,
            active_filename=effective_active_file
        )

        if not retrieved_chunks:
            logger.info("No relevant context found within threshold for query: %r", request.query)
            return QAResponse(
                query=request.query,
                answer="The uploaded document does not contain enough information.",
                citations=[],
            )

        llm_result = _llm_service.generate_answer(
            query=request.query, 
            retrieved_chunks=retrieved_chunks,
            active_filename=effective_active_file
        )

        logger.info(
            "QA Response prepared: citations=%d, answer_snippet=%r",
            len(llm_result.get("citations", [])),
            llm_result.get("answer", "")[:80]
        )

        return QAResponse(
            query=request.query,
            answer=llm_result.get("answer", ""),
            citations=llm_result.get("citations", []),
        )

    except LLMServiceError as llm_exc:
        logger.error("LLMServiceError during QA: %s", str(llm_exc))
        return QAResponse(
            query=request.query,
            answer=f"Error generating answer: {str(llm_exc)}",
            citations=[],
        )
    except Exception as exc:
        logger.exception("Unexpected error during question answering: %s", request)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"QA failed: {str(exc)}",
        ) from exc


@router.get(
    "/cleanup/eligible",
    response_model=EligibleDocumentsResponse,
    summary="List documents eligible for cleanup based on inactivity",
)
def get_eligible_cleanup_documents(
    days: int = Query(30, ge=1, description="Inactivity threshold in days"),
    simulated_now: Optional[str] = Query(None, description="Optional simulated UTC ISO-8601 now"),
) -> EligibleDocumentsResponse:
    """
    Scan tracked documents in FAISS and physical storage to identify candidates
    exceeding the inactivity threshold.
    Missing timestamps are strictly NOT marked eligible.
    Active documents and model files are strictly protected.
    """
    global _active_filename

    now_dt = _parse_iso_datetime(simulated_now) if simulated_now else datetime.now(timezone.utc)
    if now_dt is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid simulated_now ISO timestamp format."
        )

    upload_dir = os.path.join(settings.BASE_DIR, "storage", "uploads")
    docs_summary = _faiss_store.get_documents_metadata()

    eligible_list: List[EligibleDocument] = []

    for norm_fp, doc_info in docs_summary.items():
        filename = doc_info["filename"]
        lower_name = filename.lower()

        # Skip protected system/model files
        if any(term in lower_name for term in PROTECTED_TERMS):
            continue

        # Skip currently active document
        if _active_filename and (lower_name in _active_filename.lower() or _active_filename.lower() in lower_name):
            continue

        last_access = doc_info["last_access"]
        is_expired, inactive_days, _ = _check_inactivity(last_access, now_dt, days)

        if is_expired and inactive_days is not None:
            # Calculate physical file size
            file_size = 0
            real_path = doc_info["file_path"]
            if os.path.isfile(real_path):
                try:
                    file_size = os.path.getsize(real_path)
                except Exception:
                    file_size = 0
            elif os.path.exists(upload_dir):
                # Search for file in upload_dir
                for entry in os.listdir(upload_dir):
                    if filename.lower() in entry.lower():
                        ep = os.path.join(upload_dir, entry)
                        if os.path.isfile(ep):
                            file_size = os.path.getsize(ep)
                            break

            eligible_list.append(
                EligibleDocument(
                    filename=filename,
                    file_path=doc_info["file_path"],
                    last_access=last_access,
                    inactive_days=round(inactive_days, 2),
                    file_size_bytes=file_size,
                    vector_count=doc_info["chunk_count"],
                )
            )

    return EligibleDocumentsResponse(
        inactivity_threshold_days=days,
        current_time=now_dt.isoformat(),
        eligible_count=len(eligible_list),
        documents=eligible_list,
    )


@router.post(
    "/cleanup/run",
    response_model=CleanupResponse,
    summary="Execute cleanup of inactive documents exceeding threshold",
)
def run_cleanup_inactive_documents(
    request: CleanupRunRequest,
    authenticated: bool = Depends(_verify_api_key),
) -> CleanupResponse:
    """
    Safely delete documents after N days of inactivity:
    1. Calculates timezone-aware cutoff.
    2. Identifies documents with verified last_access >= threshold.
    3. Missing timestamps are NEVER deleted.
    4. Safely removes physical files from storage/uploads/.
    5. Safely removes vectors, chunks, and metadata from FAISS.
    6. Rebuilds and synchronizes FAISS index.
    """
    global _active_filename

    with _operation_lock:
        now_dt = _parse_iso_datetime(request.simulated_now) if request.simulated_now else datetime.now(timezone.utc)
        if now_dt is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid simulated_now ISO timestamp format."
            )

        upload_dir = os.path.join(settings.BASE_DIR, "storage", "uploads")
        docs_summary = _faiss_store.get_documents_metadata()

        deleted_docs: List[str] = []
        total_vectors_removed = 0
        total_freed_bytes = 0

        for norm_fp, doc_info in docs_summary.items():
            filename = doc_info["filename"]
            lower_name = filename.lower()

            if any(term in lower_name for term in PROTECTED_TERMS):
                continue

            if _active_filename and (lower_name in _active_filename.lower() or _active_filename.lower() in lower_name):
                continue

            last_access = doc_info["last_access"]
            is_expired, _, _ = _check_inactivity(last_access, now_dt, request.days)

            if not is_expired:
                continue

            # Eligible for deletion
            if request.dry_run:
                deleted_docs.append(filename)
                continue

            # Remove physical files in storage/uploads matching this document safely
            freed_for_doc = 0
            if os.path.exists(upload_dir):
                real_upload_dir = os.path.realpath(upload_dir)
                for entry in os.listdir(upload_dir):
                    if filename.lower() in entry.lower():
                        full_entry_path = os.path.realpath(os.path.join(upload_dir, entry))
                        # Prevent path traversal
                        if os.path.commonpath([full_entry_path, real_upload_dir]) == real_upload_dir:
                            if os.path.isfile(full_entry_path):
                                try:
                                    sz = os.path.getsize(full_entry_path)
                                    os.remove(full_entry_path)
                                    freed_for_doc += sz
                                    logger.info(f"Cleanup removed file: {full_entry_path} ({sz} bytes)")
                                except Exception as e:
                                    logger.warning(f"Error removing physical file {full_entry_path}: {e}")

            # Also delete from FAISS
            removed_vectors = _faiss_store.delete_embeddings_by_filepath(filename)
            total_vectors_removed += removed_vectors
            total_freed_bytes += freed_for_doc
            deleted_docs.append(filename)
            logger.info(f"Cleaned up document '{filename}': {removed_vectors} vectors removed, {freed_for_doc} bytes freed")

        return CleanupResponse(
            inactivity_days=request.days,
            deleted_documents=deleted_docs,
            total_vectors_removed=total_vectors_removed,
            freed_bytes=total_freed_bytes,
            status="success"
        )


@router.post(
    "/cleanup",
    response_model=CleanupResponse,
    summary="Legacy / alternative endpoint for inactive cleanup",
)
def legacy_cleanup(
    days: int = 30,
    simulated_now: Optional[str] = None,
    authenticated: bool = Depends(_verify_api_key),
) -> CleanupResponse:
    """Wrapper forwarding to run_cleanup_inactive_documents."""
    return run_cleanup_inactive_documents(
        CleanupRunRequest(days=days, simulated_now=simulated_now),
        authenticated=authenticated
    )


@router.post(
    "/documents/{filename}/touch",
    response_model=TouchDocumentResponse,
    summary="Update a document's last-access timestamp",
)
def touch_document(filename: str) -> TouchDocumentResponse:
    """
    Called when a document is opened or queried in the client app.
    Updates last_access to current UTC time.
    """
    safe_name = _validate_safe_filename(filename)
    now_iso = datetime.now(timezone.utc).isoformat()
    updated_count = _faiss_store.update_last_access(safe_name, now_iso)

    return TouchDocumentResponse(
        filename=safe_name,
        vectors_updated=updated_count,
        last_access=now_iso,
        status="success"
    )


@router.delete(
    "/documents/{filename}",
    response_model=DeleteDocumentResponse,
    summary="Delete a document and remove its embeddings from FAISS",
)
def delete_document(
    filename: str,
    authenticated: bool = Depends(_verify_api_key),
) -> DeleteDocumentResponse:
    """
    Safely delete a document and its indexed vectors:
    1. Validates filename and protects against path traversal.
    2. Rejects deletion if filename matches protected model files or system files.
    3. Rejects deletion if document is currently the active document.
    4. Removes physical file(s) from storage/uploads/.
    5. Removes embeddings and metadata from FAISS vector store.
    Coordinated via _operation_lock.
    """
    global _active_filename

    with _operation_lock:
        safe_name = _validate_safe_filename(filename)
        lower_name = safe_name.lower()

        if _active_filename and (lower_name in _active_filename.lower() or _active_filename.lower() in lower_name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete active document '{safe_name}'. Please close or switch active document first."
            )

        upload_dir = os.path.join(settings.BASE_DIR, "storage", "uploads")
        deleted_files: List[str] = []

        if os.path.exists(upload_dir):
            real_upload_dir = os.path.realpath(upload_dir)
            for entry in os.listdir(upload_dir):
                if lower_name in entry.lower():
                    full_path = os.path.realpath(os.path.join(upload_dir, entry))
                    # Prevent path traversal
                    if os.path.commonpath([full_path, real_upload_dir]) == real_upload_dir:
                        if os.path.isfile(full_path):
                            try:
                                os.remove(full_path)
                                deleted_files.append(entry)
                            except Exception as e:
                                logger.warning(f"Failed to remove file {full_path}: {e}")

        vectors_removed = _faiss_store.delete_embeddings_by_filepath(safe_name)

        return DeleteDocumentResponse(
            filename=safe_name,
            deleted_files=deleted_files,
            vectors_removed=vectors_removed,
            status="success"
        )


@router.post(
    "/documents/{filename}/delete",
    response_model=DeleteDocumentResponse,
    summary="Confirmed manual deletion endpoint for clients preferring POST",
)
def post_delete_document(
    filename: str,
    authenticated: bool = Depends(_verify_api_key),
) -> DeleteDocumentResponse:
    """Confirmed manual deletion for single document."""
    return delete_document(filename, authenticated=authenticated)
