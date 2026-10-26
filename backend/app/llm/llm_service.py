import os
import re
import logging
from typing import List, Dict, Any, Optional

try:
    from llama_cpp import Llama
except ImportError:
    # Handle environment where llama-cpp-python might not be installed during early dev/tests
    Llama = None

logger = logging.getLogger(__name__)

class LLMServiceError(Exception):
    """Base exception for Local LLM Service errors."""
    pass

class LLMService:
    """
    Local LLM Service using llama.cpp to generate answers from retrieved context.
    Strictly CPU-only and offline-only processing supporting GGUF models.
    """

    def __init__(self, model_path: str, context_window: int = 2048, max_tokens: int = 128, chat_format: str = "llama-2", n_threads: Optional[int] = None):
        """
        Initialize the local LLM with llama.cpp.

        Args:
            model_path (str): Absolute or relative path to the local GGUF model file.
            context_window (int): Desired context window size. Defaults to 2048, but will be adjusted to the
                actual capacity reported by the model after loading.
            max_tokens (int): The maximum number of tokens to generate in the response.
            chat_format (str): The llama-cpp chat template format to use (default: "llama-2").
            n_threads (int, optional): Number of CPU threads to use for inference.
        """
        self.model_path = model_path
        self.context_window = context_window
        self.max_tokens = max_tokens
        self.n_threads = n_threads
        
        if Llama is None:
            logger.warning("llama-cpp-python is not installed. LLM generation will fail.")
            self.llm = None
        else:
            try:
                logger.info(f"Loading local GGUF model from {self.model_path} (CPU-only, threads={self.n_threads})...")
                llama_kwargs = {
                    "model_path": self.model_path,
                    "n_ctx": self.context_window,
                    "n_gpu_layers": 0,
                    "chat_format": chat_format,
                    "verbose": False
                }
                if self.n_threads is not None:
                    llama_kwargs["n_threads"] = self.n_threads
                self.llm = Llama(**llama_kwargs)
                
                # Adjust context window based on actual model capacity if available
                actual_ctx = None
                if self.llm is not None:
                    try:
                        raw_ctx = getattr(self.llm, "n_ctx", None)
                        if callable(raw_ctx):
                            val = raw_ctx()
                            if isinstance(val, int) and val > 0:
                                actual_ctx = val
                        elif isinstance(raw_ctx, int) and raw_ctx > 0:
                            actual_ctx = raw_ctx

                        if actual_ctx is None:
                            raw_model_ctx = getattr(self.llm, "model_n_ctx", None)
                            if callable(raw_model_ctx):
                                val = raw_model_ctx()
                                if isinstance(val, int) and val > 0:
                                    actual_ctx = val
                            elif isinstance(raw_model_ctx, int) and raw_model_ctx > 0:
                                actual_ctx = raw_model_ctx
                    except Exception as inspect_err:
                        logger.debug("Could not inspect n_ctx on model: %s", inspect_err)
                        actual_ctx = None

                if actual_ctx and actual_ctx != self.context_window:
                    logger.info(f"Model reports context window {actual_ctx}, adjusting from requested {self.context_window}.")
                    self.context_window = actual_ctx
                logger.info(f"Local LLM successfully loaded with context_window={self.context_window}.")
            except Exception as e:
                logger.warning(f"Failed to load LLM model: {str(e)} - proceeding without LLM. This may affect generation features.")
                self.llm = None

    def _token_len(self, text: str) -> int:
        """Helper to count tokens using the model's tokenizer if available, with heuristic fallback."""
        try:
            if self.llm and hasattr(self.llm, "tokenize"):
                return len(self.llm.tokenize(text.encode("utf-8", errors="replace")))
        except Exception:
            pass
        return max(1, len(text) // 4)

    def build_messages(self, query: str, retrieved_chunks: Optional[List[Dict[str, Any]]] = None, active_filename: str = None) -> List[Dict[str, str]]:
        """
        Build a messages list for create_chat_completion from the user query and retrieved chunks.
        Applies context selection: respects model's actual token budget and formats context chunks.

        Args:
            query (str): The user's question.
            retrieved_chunks (List[Dict[str, Any]], optional): Context chunks from the Retrieval Service.
            active_filename (str, optional): The name of the currently active document.

        Returns:
            List[Dict[str, str]]: Messages in OpenAI-style format for create_chat_completion.
        """
        if retrieved_chunks is None:
            retrieved_chunks = []

        # Context Selection: respect model's actual token budget
        ordered_chunks = list(retrieved_chunks)
        context_parts: List[str] = []
        used_tokens = 0
        # Reserve tokens for system prompt, question and answer generation
        reserved_tokens = self.max_tokens + 150  # safety margin for prompt overhead
        available_tokens = max(0, self.context_window - reserved_tokens)
        logger.debug(
            f"Token budget: window={self.context_window}, max_tokens={self.max_tokens}, reserved={reserved_tokens}, available={available_tokens}"
        )

        for chunk in ordered_chunks[:10]:
            chunk_text = chunk.get("chunk_text", "").strip()
            if not chunk_text:
                continue
            page_num = chunk.get("page_number", "Unknown")
            chunk_id = chunk.get("chunk_id", "Unknown")
            part = f"[Citation: Page {page_num}, Chunk {chunk_id}]\n{chunk_text}"
            part_tokens = self._token_len(part)
            # If this is the first chunk and it alone exceeds the budget, truncate it to fit.
            if used_tokens == 0 and part_tokens > available_tokens:
                max_chars = max(80, available_tokens * 3)
                truncated_text = chunk_text[:max_chars].rsplit(" ", 1)[0] + " [truncated]"
                part = f"[Citation: Page {page_num}, Chunk {chunk_id}]\n{truncated_text}"
                part_tokens = self._token_len(part)
            if used_tokens + part_tokens > available_tokens:
                break
            context_parts.append(part)
            used_tokens += part_tokens

        context_str = "\n\n".join(context_parts) if context_parts else ""

        return [
            {
                "role": "system",
                "content": (
                    "You are RAGENGI, an expert engineering document assistant. Your answers must be grounded in the provided CONTEXT.\n\n"
                    "Instructions:\n"
                    "1. Answer questions accurately, clearly, and conversationally based on the facts in the CONTEXT.\n"
                    "2. State facts directly. When referencing information, cite using [Citation: Page X, Chunk Y] or [Page X].\n"
                    "3. Support summaries, explanations, and comparisons across documents.\n"
                    "4. If the CONTEXT does not contain enough information to answer the question, output:\n"
                    "   The uploaded document does not contain enough information.\n"
                    "5. Do not invent or assume facts that are not supported by the context."
                ),
            },
            {
                "role": "user",
                "content": f"CONTEXT:\n{context_str}\n\nQUESTION: {query}",
            },
        ]

    def build_prompt(self, query: str, retrieved_chunks: Optional[List[Dict[str, Any]]] = None, active_filename: str = None) -> str:
        """Helper for prompt generation compatibility."""
        messages = self.build_messages(query, retrieved_chunks, active_filename)
        return messages[1]["content"]

    def generate_answer(self, query: str, retrieved_chunks: Optional[List[Dict[str, Any]]] = None, active_filename: str = None) -> Dict[str, Any]:
        """
        Generate an answer using the local LLM based on retrieved context and append citations.

        Args:
            query (str): The user query.
            retrieved_chunks (List[Dict[str, Any]], optional): Retrieved chunks from Module 6.
            active_filename (str, optional): Name of the uploaded file.

        Returns:
            Dict[str, Any]: A dictionary containing the generated answer and the list of citations.
        """
        if not self.llm:
            raise LLMServiceError("LLM model is not loaded (llama_cpp may be missing).")

        if not query or not query.strip():
            logger.warning("Empty query provided for generation.")
            return {"answer": "I cannot answer an empty query.", "citations": []}

        if retrieved_chunks is None:
            retrieved_chunks = []

        try:
            logger.info("Building messages with context for query: %r (active=%s)", query[:80], active_filename)
            messages = self.build_messages(query, retrieved_chunks, active_filename)

            logger.info(f"Generating answer via create_chat_completion (max_tokens={self.max_tokens})...")
            try:
                output = self.llm.create_chat_completion(
                    messages=messages,
                    max_tokens=self.max_tokens,
                )
            except Exception as context_exc:
                logger.error(f"LLM generation failed: {context_exc}")
                raise LLMServiceError(f"Failed to generate answer: {context_exc}") from context_exc

            choice = output["choices"][0]
            answer_text = choice["message"]["content"].strip()
            finish_reason = choice.get("finish_reason", "")
            usage = output.get("usage", {})

            # Build citations only if answer was successfully generated
            unique_citations = []
            cited_refs = set()
            missing_phrases = [
                "does not contain enough information",
                "do not contain enough information",
                "could not find that in the documents",
                "not enough information",
                "cannot be answered from the provided context",
            ]
            is_missing = any(phrase in answer_text.lower() for phrase in missing_phrases)

            if not is_missing:
                # Match [Citation: Page X, Chunk Y] or [Page X, Chunk Y] or [Page X]
                citation_pattern = re.compile(
                    r"\[(?:Citation:\s*)?Page\s*(\d+)(?:,\s*Chunk\s*(\d+))?\]",
                    re.IGNORECASE,
                )
                for match in citation_pattern.finditer(answer_text):
                    page_num = int(match.group(1))
                    chunk_id = int(match.group(2)) if match.group(2) else None
                    cited_refs.add((page_num, chunk_id))

                for chunk in (retrieved_chunks or [])[:12]:
                    page_num = chunk.get("page_number")
                    chunk_id = chunk.get("chunk_id")
                    if (page_num, chunk_id) in cited_refs or any(p == page_num and c is None for p, c in cited_refs):
                        if not any(c["chunk_id"] == chunk_id and c["page_number"] == page_num for c in unique_citations):
                            unique_citations.append({
                                "chunk_id": chunk_id,
                                "page_number": page_num,
                                "file_path": chunk.get("file_path"),
                            })

            # If no citations were explicitly matched by tag, but answer was generated factually, include top retrieved chunks
            if not unique_citations and not cited_refs and not is_missing and retrieved_chunks:
                for chunk in (retrieved_chunks or [])[:12]:
                    citation_entry = {
                        "chunk_id": chunk.get("chunk_id"),
                        "page_number": chunk.get("page_number"),
                        "file_path": chunk.get("file_path"),
                    }
                    if citation_entry not in unique_citations:
                        unique_citations.append(citation_entry)

            return {
                "answer": answer_text,
                "citations": unique_citations,
                "finish_reason": finish_reason,
                "usage": usage,
            }

        except LLMServiceError:
            raise
        except Exception as e:
            logger.error(f"Error during LLM generation: {str(e)}")
            raise LLMServiceError(f"Failed to generate answer: {str(e)}") from e
