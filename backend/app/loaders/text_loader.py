"""Text Loader

Loads plain-text files (.txt, .csv) and returns a PDFExtractionResult.
Each line becomes a page entry.
"""

import logging
from pathlib import Path
from typing import List
from app.schemas.pdf import PDFExtractionResult, PageText

logger = logging.getLogger(__name__)


class TextLoader:
    """Load a .txt or .csv file and return a PDFExtractionResult."""

    def __init__(self) -> None:
        pass

    def load(self, file_path: str) -> PDFExtractionResult:
        logger.debug("Loading text file %s", file_path)
        path = Path(file_path)

        with path.open("r", encoding="utf-8", errors="replace") as f:
            lines = [line.rstrip("\n") for line in f if line.strip()]

        pages: List[PageText] = [
            PageText(page_number=idx, text=line, has_native_text=bool(line))
            for idx, line in enumerate(lines, start=1)
        ]

        page_count = len(pages)
        logger.info("TextLoader created %d page(s) from %s", page_count, file_path)
        return PDFExtractionResult(file_path=file_path, page_count=page_count, pages=pages)
