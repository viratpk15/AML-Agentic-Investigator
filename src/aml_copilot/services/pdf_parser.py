"""PDF ingestion service using PyMuPDF."""

from pathlib import Path
from typing import Union
import pymupdf

from aml_copilot.exceptions import PDFInvalidFormatError, PDFNotFoundError
from aml_copilot.logger import get_logger
from aml_copilot.models.pdf import PDFDocumentExtraction, PDFPage

logger = get_logger(__name__)


def extract_pdf_text(file_path: Union[str, Path]) -> PDFDocumentExtraction:
    """Extract page-by-page textual content and metadata from a PDF file.

    Args:
        file_path: Path to the PDF bank statement.

    Returns:
        PDFDocumentExtraction containing page text and metadata.

    Raises:
        PDFNotFoundError: If the specified file path does not exist.
        PDFInvalidFormatError: If the file is not a valid or readable PDF.
    """
    path = Path(file_path)

    if not path.exists() or not path.is_file():
        logger.error(f"PDF file not found: {path}")
        raise PDFNotFoundError(f"File not found at specified path: {path}")

    if path.suffix.lower() != ".pdf":
        logger.error(f"Invalid file extension for PDF extraction: {path.suffix}")
        raise PDFInvalidFormatError(
            f"File '{path.name}' is not a PDF (expected .pdf extension)."
        )

    try:
        doc = pymupdf.open(str(path))

    except Exception as exc:
        logger.error(f"PyMuPDF failed to open file {path.name}: {exc}")
        raise PDFInvalidFormatError(
            f"Failed to open or parse PDF file '{path.name}': {exc}"
        ) from exc

    try:
        if doc.is_encrypted:
            logger.error(f"Encrypted PDF cannot be read without password: {path.name}")
            raise PDFInvalidFormatError(f"PDF file '{path.name}' is encrypted.")

        pages = []
        for page_idx in range(doc.page_count):
            page = doc.load_page(page_idx)
            raw_text = page.get_text("text")
            text: str = raw_text if isinstance(raw_text, str) else str(raw_text or "")

            is_empty = len(text.strip()) == 0

            pdf_page = PDFPage(
                page_number=page_idx + 1,
                text=text,
                is_empty=is_empty,
            )
            pages.append(pdf_page)


        logger.info(
            f"Successfully extracted {len(pages)} page(s) from PDF: {path.name}"
        )
        return PDFDocumentExtraction(
            file_path=str(path),
            file_name=path.name,
            total_pages=len(pages),
            pages=pages,
        )
    except PDFInvalidFormatError:
        raise
    except Exception as exc:
        logger.error(f"Unexpected error during PDF page extraction from {path.name}: {exc}")
        raise PDFInvalidFormatError(
            f"An error occurred while extracting text from '{path.name}': {exc}"
        ) from exc
    finally:
        doc.close()
