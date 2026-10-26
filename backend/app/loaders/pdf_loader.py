"""PDF Loader

Wraps the existing PDFExtractor to produce a PDFExtractionResult compatible with
the universal loader pipeline.
"""

import logging
from app.ingestion.pdf_extractor import PDFExtractor
from app.schemas.pdf import PDFExtractionResult

logger = logging.getLogger(__name__)


class PDFLoader:
    """Load a PDF file using the existing PDFExtractor."""

    def __init__(self) -> None:
        self._extractor = PDFExtractor()

    def load(self, file_path: str) -> PDFExtractionResult:
        logger.debug("Loading PDF file %s via PDFLoader", file_path)
        return self._extractor.extract(file_path)
