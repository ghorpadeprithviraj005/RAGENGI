"""Code Loader

Loads source code files (.py, .java, .js, .ts, .cpp, .c, .html, .css, .json,
.xml, .yaml, .yml) and returns a PDFExtractionResult with the full file content
as a single page.
"""

import logging
from pathlib import Path
from app.schemas.pdf import PDFExtractionResult, PageText

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {
    ".py", ".java", ".js", ".ts", ".cpp", ".c",
    ".html", ".css", ".json", ".xml", ".yaml", ".yml",
}


class CodeLoader:
    """Load a source code file and return a single-page PDFExtractionResult."""

    def __init__(self) -> None:
        pass

    def load(self, file_path: str) -> PDFExtractionResult:
        logger.debug("Loading code file %s", file_path)
        path = Path(file_path)

        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported code file type: {path.suffix}")

        with path.open("r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        page = PageText(page_number=1, text=content, has_native_text=bool(content))
        logger.info("CodeLoader loaded %s (%d chars)", file_path, len(content))
        return PDFExtractionResult(file_path=file_path, page_count=1, pages=[page])
