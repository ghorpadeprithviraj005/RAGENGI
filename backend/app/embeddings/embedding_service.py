import logging
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import torch

from app.schemas.chunk import Chunk

logger = logging.getLogger(__name__)

class EmbeddingServiceError(Exception):
    """Base exception for Embedding Service errors."""
    pass

class EmbeddingService:
    """
    Service for generating vector embeddings from text chunks using SentenceTransformers.
    """
    
    def __init__(
        self, 
        model_name: str = "all-MiniLM-L6-v2", 
        batch_size: int = 32,
        device: str = "cpu"
    ):
        """
        Initialize the embedding service.
        
        Args:
            model_name (str): The name of the SentenceTransformer model to use.
            batch_size (int): Default batch size for processing chunks.
            device (str): Device to run the model on ('cpu' forced for this module).
        """
        self.model_name = model_name
        self.batch_size = batch_size
        self.device = "cpu"  # Requirement: CPU-only execution
        
        try:
            logger.info(f"Loading embedding model '{self.model_name}' on {self.device}...")
            # Initialize model. Will use local cache if available (offline operation support).
            self.model = SentenceTransformer(self.model_name, device=self.device)
            logger.info("Embedding model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {str(e)}")
            raise EmbeddingServiceError(f"Model initialization failed: {str(e)}") from e

    def generate_embeddings(
        self, 
        chunks: List[Chunk], 
        batch_size: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate embeddings for a list of document chunks.
        
        Args:
            chunks (List[Chunk]): List of Chunk objects from the chunking service.
            batch_size (Optional[int]): Optional override for batch processing size.
            
        Returns:
            List[Dict[str, Any]]: List of dictionaries containing the embedding and preserved metadata.
        """
        if not chunks:
            logger.warning("Empty chunk list provided for embedding generation.")
            return []

        actual_batch_size = batch_size or self.batch_size
        
        # Extract text for embedding
        texts = [chunk.chunk_text for chunk in chunks]
        
        results = []
        try:
            logger.info(f"Generating embeddings for {len(texts)} chunks in batches of {actual_batch_size}...")
            
            # SentenceTransformer encode method supports batching internally
            # We use it directly as it handles batching efficiently
            embeddings = self.model.encode(
                texts,
                batch_size=actual_batch_size,
                show_progress_bar=False,
                convert_to_numpy=True
            )
            
            # Preserve metadata as required
            for i, chunk in enumerate(chunks):
                emb = embeddings[i]
                results.append({
                    "embedding": emb.tolist() if hasattr(emb, "tolist") else emb,
                    "metadata": {
                        "chunk_id": chunk.chunk_id,
                        "page_number": chunk.page_number,
                        "chunk_text": chunk.chunk_text
                    }
                })
                
            logger.info(f"Successfully generated {len(results)} embeddings.")
            return results
            
        except Exception as e:
            logger.error(f"Error during embedding generation: {str(e)}")
            raise EmbeddingServiceError(f"Failed to generate embeddings: {str(e)}") from e
