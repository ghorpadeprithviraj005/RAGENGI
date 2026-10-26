"""PowerPoint Loader

Loads Microsoft PowerPoint (.pptx, .ppt) files using python-pptx. Each slide
is treated as a separate page in the PDFExtractionResult.
"""

import logging
from typing import List
from pptx import Presentation
from app.schemas.pdf import PDFExtractionResult, PageText

logger = logging.getLogger(__name__)


class PowerPointLoader:
    """Load a .pptx file and return a PDFExtractionResult."""

    def __init__(self) -> None:
        pass

    def load(self, file_path: str) -> PDFExtractionResult:
        logger.debug("Loading PowerPoint file %s", file_path)
        prs = Presentation(file_path)

        pages: List[PageText] = []
        for idx, slide in enumerate(prs.slides, start=1):
            texts = []
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text:
                    texts.append(shape.text.strip())
            slide_text = "\n".join(filter(None, texts))
            pages.append(
                PageText(
                    page_number=idx,
                    text=slide_text,
                    has_native_text=bool(slide_text),
                )
            )

        page_count = len(pages)
        logger.info("PowerPointLoader extracted %d slide(s) from %s", page_count, file_path)
        return PDFExtractionResult(file_path=file_path, page_count=page_count, pages=pages)
