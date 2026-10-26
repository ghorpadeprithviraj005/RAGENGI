"""File Type Detector Service

Maps a file's extension to its loader class. Can be used standalone or by
LoaderFactory for validation before instantiating a loader.
"""

import os
from typing import Type

from app.loaders.loader_factory import _LOADER_MAP


class FileTypeDetector:
    """Detect the correct loader class for a given file path."""

    @staticmethod
    def get_loader_class(file_path: str) -> Type:
        """Return the loader class for *file_path*.

        Raises ValueError for unsupported or missing extensions.
        """
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        if not ext:
            raise ValueError("File has no extension")
        loader_cls = _LOADER_MAP.get(ext)
        if loader_cls is None:
            raise ValueError(f"Unsupported file type: {ext}")
        return loader_cls

    @staticmethod
    def is_supported(file_path: str) -> bool:
        """Return True if the file extension is supported."""
        _, ext = os.path.splitext(file_path)
        return ext.lower() in _LOADER_MAP
