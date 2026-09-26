"""Script to generate a deterministic synthetic bank statement PDF for AML testing."""

from pathlib import Path
from typing import List, Tuple
import pymupdf


def generate_independent_suspicious_statement(output_path: Path) -> Path:
    """Generate a synthetic suspicious bank statement PDF compatible with transaction_parser."""
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)  # Standard A4

    # Document metadata
    doc.set_metadata({
        "title": "Synthetic Bank Statement",
        "author": "AML Investigation Copilot",
        "subject": "Synthetic AML Test Statement",
        "keywords": "synthetic, aml, test",
        "creator": "AML Copilot Test Generator",
        "producer": "PyMuPDF",
    })

    # Header styling
    # Title banner
    page.draw_rect(
        pymupdf.Rect(30, 25, 565, 50),
        color=(0.12, 0.22, 0.38),
        fill=(0.93, 0.95, 0.98),
        width=0.8,
    )
    page.insert_text(
        (40, 42),
        "SYNTHETIC BANK TRANSACTION STATEMENT",
        fontname="helv",
        fontsize=12,
        color=(0.12, 0.22, 0.38),
    )

    # Customer & statement metadata (each on a distinct line for extract_metadata)
    y_meta = 68
    meta_lines = [
        "Customer: Vikramaditya Singhania",
        "Account: SYNTH-ACC-882194",
        "Statement period: 01 Jul 2026 - 31 Jul 2026",
        "Purpose: Synthetic test data for AML AI prototype",
    ]
    for line in meta_lines:
        page.insert_text(
            (40, y_meta),
            line,
            fontname="helv",
            fontsize=8.5,
            color=(0.2, 0.2, 0.2),
        )
        y_meta += 13

    # Table Header background
    y_table_header = y_meta + 10
    page.draw_rect(
        pymupdf.Rect(30, y_table_header - 11, 565, y_table_header + 6),
        color=(0.12, 0.22, 0.38),
        fill=(0.88, 0.91, 0.95),
        width=0.5,
    )

    # Column x positions
    col_x = {
        "date": 36,
        "txn_id": 100,
        "desc": 165,
        "debit": 370,
        "credit": 440,
        "balance": 505,
    }

    # Table Header labels
    page.insert_text((col_x["date"], y_table_header), "Date", fontname="helv", fontsize=8, color=(0.1, 0.1, 0.1))
    page.insert_text((col_x["txn_id"], y_table_header), "Transaction ID", fontname="helv", fontsize=8, color=(0.1, 0.1, 0.1))
    page.insert_text((col_x["desc"], y_table_header), "Description", fontname="helv", fontsize=8, color=(0.1, 0.1, 0.1))
    page.insert_text((col_x["debit"], y_table_header), "Debit (INR)", fontname="helv", fontsize=8, color=(0.1, 0.1, 0.1))
    page.insert_text((col_x["credit"], y_table_header), "Credit (INR)", fontname="helv", fontsize=8, color=(0.1, 0.1, 0.1))
    page.insert_text((col_x["balance"], y_table_header), "Balance (INR)", fontname="helv", fontsize=8, color=(0.1, 0.1, 0.1))

    # 22 Synthetic Transactions
    # Each row is (Date, TxnID, Description, Debit, Credit, Balance)
    # With explicit '-' placeholder in empty debit/credit cells
    transactions: List[Tuple[str, str, str, str, str, str]] = [
        ("01 Jul 2026", "TXN101", "SALARY CREDIT - NEXUS TECH LABS", "-", "110,000.00", "195,000.00"),
        ("02 Jul 2026", "TXN102", "RENT - UPI", "28,000.00", "-", "167,000.00"),
        ("03 Jul 2026", "TXN103", "GROCERY MART - UPI", "4,350.00", "-", "162,650.00"),
        ("05 Jul 2026", "TXN104", "UTILITY ELECTRICITY BILL", "3,200.00", "-", "159,450.00"),
        ("07 Jul 2026", "TXN105", "NEFT - APEX OVERSEAS LOGISTICS", "-", "520,000.00", "679,450.00"),
        ("08 Jul 2026", "TXN106", "RTGS - ZENITH GLOBAL MINERALS", "-", "680,000.00", "1,359,450.00"),
        ("09 Jul 2026", "TXN107", "NEFT - PACIFIC TRADING CORP", "-", "450,000.00", "1,809,450.00"),
        ("09 Jul 2026", "TXN108", "IMPS - KAVITA CONSULTING SERVICES", "510,000.00", "-", "1,299,450.00"),
        ("10 Jul 2026", "TXN109", "WIRE - MARUTI EXPORTS", "650,000.00", "-", "649,450.00"),
        ("10 Jul 2026", "TXN110", "IMPS - KAVITA CONSULTING SERVICES", "430,000.00", "-", "219,450.00"),
        ("12 Jul 2026", "TXN111", "CAFE COFFEE - CARD", "620.00", "-", "218,830.00"),
        ("14 Jul 2026", "TXN112", "ONLINE RETAIL STORE", "2,150.00", "-", "216,680.00"),
        ("16 Jul 2026", "TXN113", "NEFT - DELTA HORIZON HOLDINGS", "-", "380,000.00", "596,680.00"),
        ("16 Jul 2026", "TXN114", "UPI - NEW COUNTERPARTY A1", "95,000.00", "-", "501,680.00"),
        ("16 Jul 2026", "TXN115", "UPI - NEW COUNTERPARTY B2", "92,500.00", "-", "409,180.00"),
        ("17 Jul 2026", "TXN116", "UPI - NEW COUNTERPARTY C3", "94,000.00", "-", "315,180.00"),
        ("17 Jul 2026", "TXN117", "UPI - NEW COUNTERPARTY D4", "89,000.00", "-", "226,180.00"),
        ("20 Jul 2026", "TXN118", "IMPS - APEX OVERSEAS LOGISTICS", "-", "320,000.00", "546,180.00"),
        ("21 Jul 2026", "TXN119", "IMPS - KAVITA CONSULTING SERVICES", "310,000.00", "-", "236,180.00"),
        ("24 Jul 2026", "TXN120", "ATM CASH WITHDRAWAL", "15,000.00", "-", "221,180.00"),
        ("26 Jul 2026", "TXN121", "PHARMACY MEDICAL - UPI", "1,850.00", "-", "219,330.00"),
        ("28 Jul 2026", "TXN122", "INTEREST CREDIT", "-", "820.00", "220,150.00"),
    ]

    y_row = y_table_header + 16
    for idx, row in enumerate(transactions):
        # Alternating subtle row fill
        if idx % 2 == 1:
            page.draw_rect(
                pymupdf.Rect(30, y_row - 10, 565, y_row + 5),
                color=None,
                fill=(0.97, 0.98, 0.99),
            )
        # Separator line
        page.draw_line(
            (30, y_row + 5),
            (565, y_row + 5),
            color=(0.85, 0.88, 0.92),
            width=0.4,
        )

        page.insert_text((col_x["date"], y_row), row[0], fontname="helv", fontsize=7.5, color=(0.15, 0.15, 0.15))
        page.insert_text((col_x["txn_id"], y_row), row[1], fontname="helv", fontsize=7.5, color=(0.15, 0.15, 0.15))
        page.insert_text((col_x["desc"], y_row), row[2], fontname="helv", fontsize=7.5, color=(0.15, 0.15, 0.15))
        page.insert_text((col_x["debit"], y_row), row[3], fontname="helv", fontsize=7.5, color=(0.15, 0.15, 0.15))
        page.insert_text((col_x["credit"], y_row), row[4], fontname="helv", fontsize=7.5, color=(0.15, 0.15, 0.15))
        page.insert_text((col_x["balance"], y_row), row[5], fontname="helv", fontsize=7.5, color=(0.15, 0.15, 0.15))

        y_row += 15.5

    # Footer note
    y_footer = y_row + 15
    page.draw_line((30, y_footer - 8), (565, y_footer - 8), color=(0.7, 0.7, 0.7), width=0.5)
    page.insert_text(
        (36, y_footer),
        "Dataset note: Synthetic bank statement for AML automated testing. Contains planted suspicious patterns for testing purposes only.",
        fontname="helv",
        fontsize=7,
        color=(0.4, 0.4, 0.4),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    doc.close()
    return output_path


if __name__ == "__main__":
    out_dir = Path("data/statements")
    target_pdf = out_dir / "independent_suspicious_statement.pdf"
    generate_independent_suspicious_statement(target_pdf)
    print(f"Generated: {target_pdf} ({target_pdf.stat().st_size} bytes)")

    v2_in_data = out_dir / "independent_suspicious_bank_statement_v2.pdf"
    generate_independent_suspicious_statement(v2_in_data)
    print(f"Generated: {v2_in_data} ({v2_in_data.stat().st_size} bytes)")

    downloads_dir = Path.home() / "Downloads"
    try:
        v2_pdf = downloads_dir / "independent_suspicious_bank_statement_v2.pdf"
        generate_independent_suspicious_statement(v2_pdf)
        print(f"Updated: {v2_pdf} ({v2_pdf.stat().st_size} bytes)")
    except Exception as exc:
        print(f"Note: Could not update Downloads folder directly ({exc})")
