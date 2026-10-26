"""Loader Factory

Maps file extensions to the appropriate loader class.
"""

import logging
import os
from typing import Type

from .pdf_loader import PDFLoader
from .word_loader import WordLoader
from .powerpoint_loader import PowerPointLoader
from .excel_loader import ExcelLoader
from .image_loader import ImageLoader
from .text_loader import TextLoader
from .code_loader import CodeLoader

logger = logging.getLogger(__name__)

_LOADER_MAP: dict = {
    # PDF
    ".pdf": PDFLoader,
    # Word
    ".docx": WordLoader,
    ".doc": WordLoader,
    # PowerPoint
    ".pptx": PowerPointLoader,
    ".ppt": PowerPointLoader,
    # Excel
    ".xlsx": ExcelLoader,
    ".xls": ExcelLoader,
    # Text / CSV
    ".txt": TextLoader,
    ".csv": TextLoader,
    # Code
    ".py": CodeLoader,
    ".java": CodeLoader,
    ".js": CodeLoader,
    ".ts": CodeLoader,
    ".cpp": CodeLoader,
    ".c": CodeLoader,
    ".html": CodeLoader,
    ".css": CodeLoader,
    ".json": CodeLoader,
    ".xml": CodeLoader,
    ".yaml": CodeLoader,
    ".yml": CodeLoader,
    # Images
    ".png": ImageLoader,
    ".jpg": ImageLoader,
    ".jpeg": ImageLoader,
    ".bmp": ImageLoader,
    ".tiff": ImageLoader,
    ".webp": ImageLoader,
}


class LoaderFactory:
    """Return an instantiated loader appropriate for the given file path."""

    def __init__(self) -> None:
        self._loader_map = _LOADER_MAP

    def get_loader(self, file_path: str):
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        if not ext:
            raise ValueError("File has no extension")
        loader_cls = self._loader_map.get(ext)
        if loader_cls is None:
            raise ValueError(f"Unsupported file type: {ext}")
        logger.debug("Selected %s for extension %s", loader_cls.__name__, ext)
        return loader_cls()
