"""Unit tests for PDF ingestion service."""

from pathlib import Path
import pymupdf
import pytest

from aml_copilot.exceptions import PDFInvalidFormatError, PDFNotFoundError
from aml_copilot.services.pdf_parser import extract_pdf_text


def create_test_pdf(file_path: Path, pages_content: list[str]) -> Path:
    """Helper function to create temporary PDF files using PyMuPDF."""
    doc = pymupdf.open()

    for content in pages_content:
        page = doc.new_page()
        if content:
            page.insert_text((50, 50), content)
    doc.save(str(file_path))
    doc.close()
    return file_path


def test_extract_valid_single_page_pdf(tmp_path):
    """Verify single-page PDF extraction text and metadata."""
    pdf_file = create_test_pdf(
        tmp_path / "single_page.pdf",
        ["Account Statement\nCustomer: John Doe\nBalance: $10,000"],
    )

    result = extract_pdf_text(pdf_file)

    assert result.file_name == "single_page.pdf"
    assert result.total_pages == 1
    assert len(result.pages) == 1
    assert result.pages[0].page_number == 1
    assert not result.pages[0].is_empty
    assert "Account Statement" in result.pages[0].text
    assert "Balance: $10,000" in result.pages[0].text


def test_extract_multi_page_pdf(tmp_path):
    """Verify multi-page PDF page preservation and page numbering."""
    pages_text = [
        "Statement Header - Page 1",
        "Transaction Records - Page 2",
        "Summary & Disclosures - Page 3",
    ]
    pdf_file = create_test_pdf(tmp_path / "multi_page.pdf", pages_text)

    result = extract_pdf_text(pdf_file)

    assert result.total_pages == 3
    assert len(result.pages) == 3

    for idx, expected_text in enumerate(pages_text, start=1):
        page = result.pages[idx - 1]
        assert page.page_number == idx
        assert not page.is_empty
        assert expected_text in page.text


def test_extract_empty_page_pdf(tmp_path):
    """Verify empty/blank page handling."""
    pdf_file = create_test_pdf(
        tmp_path / "empty_page.pdf",
        ["First Page Content", ""],  # Page 2 is empty
    )

    result = extract_pdf_text(pdf_file)

    assert result.total_pages == 2
    assert not result.pages[0].is_empty
    assert result.pages[1].is_empty
    assert result.pages[1].text == ""


def test_invalid_file_path():
    """Verify exception raised for non-existent file path."""
    non_existent_path = Path("/tmp/definitely_does_not_exist_12345.pdf")

    with pytest.raises(PDFNotFoundError) as exc_info:
        extract_pdf_text(non_existent_path)

    assert "File not found" in str(exc_info.value)


def test_non_pdf_file_extension(tmp_path):
    """Verify exception raised for non-PDF file extension."""
    txt_file = tmp_path / "statement.txt"
    txt_file.write_text("This is plain text, not a PDF.")

    with pytest.raises(PDFInvalidFormatError) as exc_info:
        extract_pdf_text(txt_file)

    assert "not a PDF" in str(exc_info.value)


def test_corrupted_pdf_file(tmp_path):
    """Verify exception raised for invalid/corrupted PDF content."""
    corrupted_pdf = tmp_path / "corrupted.pdf"
    corrupted_pdf.write_bytes(b"%PDF-1.4 corrupted invalid content bytes")

    with pytest.raises(PDFInvalidFormatError) as exc_info:
        extract_pdf_text(corrupted_pdf)

    assert "Failed to open or parse PDF file" in str(exc_info.value)
