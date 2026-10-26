"""Excel Loader

Loads spreadsheet files (.xlsx, .xls) using openpyxl. Each worksheet is treated
as a separate page in the PDFExtractionResult.
"""

import logging
from typing import List
from openpyxl import load_workbook
from app.schemas.pdf import PDFExtractionResult, PageText

logger = logging.getLogger(__name__)


class ExcelLoader:
    """Load an Excel workbook and return a PDFExtractionResult."""

    def __init__(self) -> None:
        pass

    def load(self, file_path: str) -> PDFExtractionResult:
        logger.debug("Loading Excel file %s", file_path)
        wb = load_workbook(filename=file_path, data_only=True, read_only=True)

        pages: List[PageText] = []
        for idx, sheet in enumerate(wb.worksheets, start=1):
            rows = []
            for row in sheet.iter_rows(values_only=True):
                row_vals = [str(v) for v in row if v is not None]
                if row_vals:
                    rows.append("\t".join(row_vals))
            sheet_text = "\n".join(rows)
            pages.append(
                PageText(
                    page_number=idx,
                    text=sheet_text,
                    has_native_text=bool(sheet_text),
                )
            )

        page_count = len(pages)
        logger.info("ExcelLoader extracted %d sheet(s) from %s", page_count, file_path)
        return PDFExtractionResult(file_path=file_path, page_count=page_count, pages=pages)
