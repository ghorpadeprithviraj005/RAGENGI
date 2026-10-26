"""Image Loader

Loads raster image files (PNG, JPG, JPEG, BMP, TIFF, WEBP) via Pillow and
returns a PDFExtractionResult with one page and empty text so that the OCR
module runs on it.
"""

import logging
from PIL import Image
from app.schemas.pdf import PDFExtractionResult, PageText

logger = logging.getLogger(__name__)


class ImageLoader:
    """Load a raster image and return a single-page PDFExtractionResult.

    has_native_text is always False so the OCR fallback processes the image.
    """

    def __init__(self) -> None:
        pass

    def load(self, file_path: str) -> PDFExtractionResult:
        logger.debug("Loading image file %s", file_path)
        try:
            Image.open(file_path).verify()
        except Exception as exc:
            logger.error("Failed to open image %s: %s", file_path, exc)
            raise

        page = PageText(page_number=1, text="", has_native_text=False)
        logger.info("ImageLoader created single-page result for %s", file_path)
        return PDFExtractionResult(file_path=file_path, page_count=1, pages=[page])
