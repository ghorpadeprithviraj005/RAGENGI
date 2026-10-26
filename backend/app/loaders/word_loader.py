"""Word Loader

Loads Microsoft Word (.docx) files using python-docx. Each paragraph is treated
as a separate page in the PDFExtractionResult.
"""

import logging
from typing import List
from docx import Document
from app.schemas.pdf import PDFExtractionResult, PageText

logger = logging.getLogger(__name__)


class WordLoader:
    """Load a .docx file and return a PDFExtractionResult."""

    def __init__(self) -> None:
        pass

    def load(self, file_path: str) -> PDFExtractionResult:
        logger.debug("Loading Word document %s", file_path)
        doc = Document(file_path)

        pages: List[PageText] = []
        for idx, paragraph in enumerate(doc.paragraphs, start=1):
            text = paragraph.text.strip()
            if not text:
                continue
            pages.append(PageText(page_number=idx, text=text, has_native_text=True))

        page_count = len(pages)
        logger.info("WordLoader extracted %d paragraph(s) from %s", page_count, file_path)
        return PDFExtractionResult(file_path=file_path, page_count=page_count, pages=pages)
