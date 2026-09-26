"""Pydantic schemas for PDF document extraction results."""

from typing import List
from pydantic import BaseModel, Field


class PDFPage(BaseModel):
    """Extraction results for an individual PDF page."""

    page_number: int = Field(..., ge=1, description="1-indexed page number")
    text: str = Field(default="", description="Raw text extracted from the page")
    is_empty: bool = Field(
        default=False,
        description="Flag indicating if page contains no textual content",
    )


class PDFDocumentExtraction(BaseModel):
    """Structured extraction results for a PDF document."""

    file_path: str = Field(..., description="Absolute or relative file path")
    file_name: str = Field(..., description="Basename of the PDF file")
    total_pages: int = Field(..., ge=0, description="Total number of pages extracted")
    pages: List[PDFPage] = Field(
        default_factory=list, description="List of page extraction objects"
    )
