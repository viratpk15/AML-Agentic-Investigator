"""Deterministic transaction parsing and validation service."""

import datetime as dt
import re
from typing import List, Optional, Tuple

from aml_copilot.exceptions import TransactionParsingError
from aml_copilot.logger import get_logger
from aml_copilot.models.pdf import PDFDocumentExtraction
from aml_copilot.models.transaction import Transaction, TransactionStatement

logger = get_logger(__name__)

# Known transaction channels and payment methods
CHANNEL_PREFIXES = {
    "NEFT",
    "IMPS",
    "RTGS",
    "UPI",
    "SALARY CREDIT",
    "TRANSFER",
    "WIRE",
    "ACH",
}
CHANNEL_SUFFIXES = {
    "UPI",
    "NEFT",
    "IMPS",
    "RTGS",
    "NET BANKING",
    "CARD",
}

DATE_PATTERNS = [
    # 01 Aug 2026, 01 August 2026
    (re.compile(r"^\d{1,2}\s+[A-Za-z]{3,}\s+\d{4}$", re.IGNORECASE), ("%d %b %Y", "%d %B %Y")),
    # 01-Jun-2026, 01-June-2026, 1-JUN-2026
    (re.compile(r"^\d{1,2}-[A-Za-z]{3,}-\d{4}$", re.IGNORECASE), ("%d-%b-%Y", "%d-%B-%Y")),
    # 01/Jun/2026, 01/June/2026
    (re.compile(r"^\d{1,2}/[A-Za-z]{3,}/\d{4}$", re.IGNORECASE), ("%d/%b/%Y", "%d/%B/%Y")),
    # 01.Jun.2026, 01.June.2026
    (re.compile(r"^\d{1,2}\.[A-Za-z]{3,}\.\d{4}$", re.IGNORECASE), ("%d.%b.%Y", "%d.%B.%Y")),
    # Jun 01, 2026, June 1, 2026, Jun 01 2026
    (
        re.compile(r"^[A-Za-z]{3,}\s+\d{1,2},?\s+\d{4}$", re.IGNORECASE),
        ("%b %d %Y", "%b %d, %Y", "%B %d %Y", "%B %d, %Y"),
    ),
    # Standard ISO 2026-06-01
    (re.compile(r"^\d{4}-\d{2}-\d{2}$"), ("%Y-%m-%d",)),
    # 2026/06/01
    (re.compile(r"^\d{4}/\d{2}/\d{2}$"), ("%Y/%m/%d",)),
    # 2026.06.01
    (re.compile(r"^\d{4}\.\d{2}\.\d{2}$"), ("%Y.%m.%d",)),
    # Numeric with slash: 01/06/2026, 06/01/2026
    (re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$"), ("%d/%m/%Y", "%m/%d/%Y")),
    # Numeric with hyphen: 01-06-2026, 06-01-2026
    (re.compile(r"^\d{1,2}-\d{1,2}-\d{4}$"), ("%d-%m-%Y", "%m-%d-%Y")),
    # Numeric with dot: 01.06.2026
    (re.compile(r"^\d{1,2}\.\d{1,2}\.\d{4}$"), ("%d.%m.%Y", "%m.%d.%Y")),
]

# Standard header / footer line patterns that occur across pages and tables
_HEADER_FOOTER_PATTERNS = [
    # Page numbers
    re.compile(r"(?i)^Page\s+\d+(\s*[/of]\s*\d+)?$"),
    re.compile(r"(?i)^-?\s*Page\s+\d+\s*-?$"),
    re.compile(r"(?i)^-?\s*\d+\s*(of\s*\d+)?\s*-?$"),
    re.compile(r"(?i)^Page\s*:\s*\d+(\s*[/of]\s*\d+)?$"),
    # Document title / header banners
    re.compile(r"(?i)^AML Investigation Copilot.*"),
    re.compile(r"(?i)^Synthetic (Bank )?Transaction Statement.*"),
    re.compile(r"(?i)^Synthetic Stress Statement.*"),
    re.compile(r"(?i)^Bank Statement.*"),
    re.compile(r"(?i)^Transaction\s+Details$"),
    re.compile(r"(?i)^(Opening|Closing)\s+Balance$"),
    re.compile(r"(?i)^Transaction\s+Count(\s*:\s*\d+)?$"),
    # Multi-column table header lines (must have Txn/Transaction AND Date AND an amount/flow indicator)
    re.compile(
        r"(?i)^.*?\b(Txn|Transaction)\b.*?\bDate\b.*?\b(Amount|Debit|Credit|Flow|Balance|Description|Particulars)\b.*$"
    ),
    re.compile(
        r"(?i)^.*?\bDate\b.*?\b(Txn|Transaction)\b.*?\b(Amount|Debit|Credit|Flow|Balance|Description|Particulars)\b.*$"
    ),
    # Column header labels (individual tokens)
    re.compile(r"(?i)^(Transaction\s+ID|Txn\s+ID|Trans\s+ID|Txn\s+No|Transaction\s+No|ID)$"),
    re.compile(r"(?i)^(Date|Txn\s+Date|Transaction\s+Date|Posting\s+Date|Value\s+Date)$"),
    re.compile(r"(?i)^(Flow|Flow\s+Type|Transaction\s+Type|Dr\s*/\s*Cr)$"),
    re.compile(r"(?i)^(Amount|Amount\s*\([A-Za-z]+\)|Amount\s*in\s*[A-Za-z]+)$"),
    re.compile(r"(?i)^(Debit\s*\([A-Za-z|₹$€£]+\)|Withdrawals?)$"),
    re.compile(r"(?i)^(Credit\s*\([A-Za-z|₹$€£]+\)|Deposits?)$"),
    re.compile(r"(?i)^(Balance|Balance\s*\([A-Za-z|₹$€£]+\)|Closing\s+Balance)$"),
    re.compile(r"(?i)^(Counterparty|Beneficiary|Party|Entity)$"),
    re.compile(r"(?i)^(Description|Particulars|Narration|Transaction\s+Details)$"),
    re.compile(r"(?i)^(Reference|Ref\s+No\.?|Reference\s+No\.?|Chq/Ref\s+No\.?|Cheque\s+No\.?)$"),
    # Repeated statement metadata headers on later pages
    re.compile(r"(?i)^(Customer|Account|Statement\s+Period|Currency|Branch|IFSC)\s*:"),
]


def is_header_or_footer(line: str) -> bool:
    """Return True if line matches a running header, page number, or table column header."""
    cleaned = line.strip()
    if not cleaned:
        return False
    return any(p.match(cleaned) for p in _HEADER_FOOTER_PATTERNS)


def parse_date(raw_date: str) -> Optional[dt.date]:
    """Parse a date string into a datetime.date object using standard formats."""
    cleaned = raw_date.strip()
    if not cleaned:
        return None
    cleaned_norm = re.sub(r"\s*,\s*", ", ", cleaned)
    for pattern, fmts in DATE_PATTERNS:
        if pattern.match(cleaned):
            for fmt in fmts:
                try:
                    return dt.datetime.strptime(cleaned.title(), fmt).date()
                except ValueError:
                    try:
                        return dt.datetime.strptime(cleaned_norm.title(), fmt).date()
                    except ValueError:
                        continue
    return None


def is_txn_id(raw: str) -> bool:
    """Return True if string matches a standard transaction ID pattern."""
    s = raw.strip()
    return bool(
        re.match(r"^TXN[-_]?\d+$", s, re.IGNORECASE)
        or re.match(r"^[A-Za-z]{2,5}[-_]?\d{3,10}$", s)
    )


def is_valid_amount_str(raw: str) -> bool:
    """Check whether a raw token represents a valid numeric currency amount."""
    cleaned = raw.strip()
    if not cleaned or cleaned in {"—", "–", "-", "N/A", "NA", "nil", "None", "--"}:
        return False
    # Strip currency codes and symbols
    s = re.sub(r"(?i)\b(INR|USD|EUR|GBP|RS)\.?\b", "", cleaned).strip()
    s = re.sub(r"^[₹$€£|Iil\s]+", "", s).strip()
    if (s.startswith("(") and s.endswith(")")) or s.startswith("-") or s.startswith("+"):
        s = s.strip("()+-").strip()
    return bool(
        re.match(r"^\d{1,3}(,\d{2,3})*(\.\d+)?$", s)
        or re.match(r"^\d+(\.\d+)?$", s)
    )


def parse_amount(raw: str, allow_none: bool = True) -> Optional[float]:
    """Parse a monetary amount string into a float.

    Handles:
    - Commas and formatting (e.g., '75,000.00', '1,00,000.00')
    - Currency prefixes/symbols (e.g., 'INR', '₹', '$')
    - OCR artifact characters (e.g., leading 'I', 'l', '|' before digits)
    - Dashes and empty markers ('—', '–', '-', 'N/A')
    - Negative amounts ('-206,200.00' or '(206,200.00)')
    """
    cleaned = raw.strip()
    if not cleaned or cleaned in {"—", "–", "-", "N/A", "NA", "nil", "None", "--"}:
        if allow_none:
            return None
        raise ValueError(f"Expected numeric amount, got empty marker '{raw}'")

    if not is_valid_amount_str(cleaned):
        if allow_none:
            return None
        raise ValueError(f"Could not parse numeric amount from '{raw}'")

    is_negative = False
    s = re.sub(r"(?i)\b(INR|USD|EUR|GBP|RS)\.?\b", "", cleaned).strip()
    s = re.sub(r"^[₹$€£|Iil\s]+", "", s).strip()
    if s.startswith("(") and s.endswith(")"):
        is_negative = True
        s = s[1:-1].strip()
    elif s.startswith("-"):
        is_negative = True
        s = s[1:].strip()
    elif s.startswith("+"):
        s = s[1:].strip()

    digits_only = re.sub(r"[^\d.]", "", s)
    if not digits_only:
        if allow_none:
            return None
        raise ValueError(f"Could not parse numeric amount from '{raw}'")

    try:
        val = float(digits_only)
    except ValueError as exc:
        raise ValueError(f"Invalid numeric amount '{raw}': {exc}") from exc

    return -val if is_negative else val


def extract_counterparty(description: str) -> Optional[str]:
    """Deterministically extract counterparty name from description."""
    desc = description.strip()
    if " - " in desc:
        parts = [p.strip() for p in desc.split(" - ") if p.strip()]
        if len(parts) == 2:
            prefix, suffix = parts[0], parts[1]
            if prefix.upper() in CHANNEL_PREFIXES:
                return suffix
            if suffix.upper() in CHANNEL_SUFFIXES:
                return prefix
            return suffix
        elif len(parts) >= 3:
            if parts[0].upper() in CHANNEL_PREFIXES:
                return parts[1]
            return parts[0]
    return None


def extract_metadata(
    lines: List[str],
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Extract customer name, account number, and statement period from text lines."""
    customer_name = None
    account_number = None
    statement_period = None

    _CUSTOMER_PATS = [
        re.compile(r"(?i)(?:Account\s+Holder|Customer\s+Name|Customer\s+Account\s+Name)\s*:\s*(.+?)(?:\s{2,}|$)"),
        re.compile(r"(?i)^Customer\s*:\s*(.+)$"),
    ]
    _ACCOUNT_PATS = [
        re.compile(r"(?i)(?:Account\s+(?:Number|No\.?))\s*:\s*(\S+)"),
        re.compile(r"(?i)^Account\s*:\s*(\S+)"),
    ]
    _PERIOD_PATS = [
        re.compile(r"(?i)^Statement\s+[Pp]eriod\s*:\s*(.+?)(?:\s{2,}|$)"),
        re.compile(r"(?i)^Period\s*:\s*(.+?)(?:\s{2,}|$)"),
    ]

    _LABEL_CUSTOMER = re.compile(r"(?i)^(?:Account\s+Holder|Customer\s+Name|Customer\s+Account\s+Name|Customer)$")
    _LABEL_ACCOUNT = re.compile(r"(?i)^(?:Account\s+(?:Number|No\.?)|Account)$")
    _LABEL_PERIOD = re.compile(r"(?i)^(?:Statement\s+[Pp]eriod|Period)$")

    for i, line in enumerate(lines):
        line_clean = line.strip()
        if not line_clean:
            continue

        if not customer_name:
            for pat in _CUSTOMER_PATS:
                m = pat.search(line_clean)
                if m:
                    val = m.group(1).strip()
                    if val and not is_header_or_footer(val):
                        customer_name = val
                    break
            if not customer_name and _LABEL_CUSTOMER.match(line_clean) and i + 1 < len(lines):
                nxt = lines[i + 1].strip()
                if nxt and not is_header_or_footer(nxt):
                    customer_name = nxt

        if not account_number:
            for pat in _ACCOUNT_PATS:
                m = pat.search(line_clean)
                if m:
                    val = m.group(1).strip()
                    if val and not is_header_or_footer(val):
                        account_number = val
                    break
            if not account_number and _LABEL_ACCOUNT.match(line_clean) and i + 1 < len(lines):
                nxt = lines[i + 1].strip()
                if nxt and not is_header_or_footer(nxt):
                    account_number = nxt

        if not statement_period:
            for pat in _PERIOD_PATS:
                m = pat.search(line_clean)
                if m:
                    val = m.group(1).strip()
                    if val and not is_header_or_footer(val):
                        statement_period = val
                    break
            if not statement_period and _LABEL_PERIOD.match(line_clean) and i + 1 < len(lines):
                nxt = lines[i + 1].strip()
                if nxt and not is_header_or_footer(nxt):
                    statement_period = nxt

    return customer_name, account_number, statement_period


def is_flow_layout(tokens: List[str]) -> bool:
    """Return True if tokens represent a Flow-based (Debit/Credit indicator + Amount) layout."""
    return any(t.strip().upper() in {"DEBIT", "CREDIT", "DR", "CR"} for t in tokens)


def parse_flow_row(tokens: List[str], running_balance: float = 0.0) -> Tuple[Transaction, float]:
    """Parse a Flow-based transaction row (e.g. Txn ID, Date, Flow, Amount, Counterparty, Description, Reference)."""
    # 1. Date
    txn_date = None
    date_idx = None
    for idx, t in enumerate(tokens):
        d = parse_date(t)
        if d is not None:
            txn_date = d
            date_idx = idx
            break
    if txn_date is None:
        raise TransactionParsingError(f"Missing date in flow row tokens: {tokens}")

    # 2. Flow indicator (DEBIT or CREDIT)
    flow = None
    flow_idx = None
    for idx, t in enumerate(tokens):
        u = t.strip().upper()
        if u in {"DEBIT", "CREDIT", "DR", "CR"}:
            flow = "DEBIT" if u in {"DEBIT", "DR"} else "CREDIT"
            flow_idx = idx
            break
    if flow is None:
        raise TransactionParsingError(f"Missing flow indicator (DEBIT/CREDIT) in tokens: {tokens}")

    # 3. Transaction ID
    txn_id = None
    txn_id_idx = None
    for idx, t in enumerate(tokens):
        if idx in {date_idx, flow_idx}:
            continue
        if is_txn_id(t):
            txn_id = t.strip()
            txn_id_idx = idx
            break

    # 4. Amount(s)
    amount = None
    amount_idx = None
    balance_val = None
    balance_idx = None

    for idx, t in enumerate(tokens):
        if idx in {date_idx, flow_idx, txn_id_idx}:
            continue
        if is_valid_amount_str(t):
            val = parse_amount(t, allow_none=True)
            if val is not None and val > 0:
                if amount is None:
                    amount = val
                    amount_idx = idx
                elif balance_val is None:
                    balance_val = val
                    balance_idx = idx

    if amount is None:
        raise TransactionParsingError(f"Missing valid numeric amount in flow row tokens: {tokens}")

    debit = amount if flow == "DEBIT" else None
    credit = amount if flow == "CREDIT" else None

    # Calculate or update balance
    if balance_val is not None:
        balance = balance_val
        new_running_balance = balance_val
    else:
        if credit:
            new_running_balance = running_balance + credit
        else:
            new_running_balance = running_balance - (debit or 0.0)
        balance = round(new_running_balance, 2)

    consumed_indices = {i for i in [date_idx, flow_idx, txn_id_idx, amount_idx, balance_idx] if i is not None}
    remaining = [t.strip() for idx, t in enumerate(tokens) if idx not in consumed_indices and t.strip()]

    counterparty = None
    if len(remaining) >= 3:
        counterparty = remaining[0]
        description = " - ".join(remaining[1:])
    elif len(remaining) == 2:
        counterparty = remaining[0]
        description = remaining[1]
    elif len(remaining) == 1:
        description = remaining[0]
        counterparty = extract_counterparty(description)
    else:
        description = f"{flow} transfer {amount:.2f}"
        counterparty = None

    if not counterparty:
        counterparty = extract_counterparty(description)

    try:
        txn = Transaction(
            date=txn_date,
            transaction_id=txn_id,
            description=description,
            debit=debit,
            credit=credit,
            balance=balance,
            counterparty=counterparty,
        )
        return txn, new_running_balance
    except Exception as exc:
        raise TransactionParsingError(
            f"Validation failed for flow row tokens {tokens}: {exc}"
        ) from exc


def parse_row_tokens(tokens: List[str]) -> Transaction:
    """Parse a list of tokens representing a single Debit/Credit/Balance transaction row."""
    if len(tokens) < 4:
        raise TransactionParsingError(
            f"Insufficient tokens to form a transaction row (expected at least 4, got {len(tokens)}): {tokens}"
        )

    # First token is Date, or first is Txn ID and second is Date
    txn_date = parse_date(tokens[0])
    transaction_id: Optional[str] = None
    middle_start = 1

    if txn_date is None and len(tokens) >= 5:
        if is_txn_id(tokens[0]) and parse_date(tokens[1]) is not None:
            transaction_id = tokens[0].strip()
            txn_date = parse_date(tokens[1])
            middle_start = 2

    if txn_date is None:
        raise TransactionParsingError(
            f"Invalid transaction date '{tokens[0]}' in row tokens: {tokens}"
        )

    # Last 3 tokens are Debit, Credit, Balance
    balance_str = tokens[-1]
    credit_str = tokens[-2]
    debit_str = tokens[-3]

    try:
        balance = parse_amount(balance_str, allow_none=False)
        if balance is None:
            raise ValueError("Balance cannot be null")
    except Exception as exc:
        raise TransactionParsingError(
            f"Failed to parse balance '{balance_str}' in row: {tokens}: {exc}"
        ) from exc

    try:
        debit = parse_amount(debit_str, allow_none=True)
        if debit == 0.0:
            debit = None
    except Exception as exc:
        raise TransactionParsingError(
            f"Failed to parse debit amount '{debit_str}' in row: {tokens}: {exc}"
        ) from exc

    try:
        credit = parse_amount(credit_str, allow_none=True)
        if credit == 0.0:
            credit = None
    except Exception as exc:
        raise TransactionParsingError(
            f"Failed to parse credit amount '{credit_str}' in row: {tokens}: {exc}"
        ) from exc

    # Middle tokens are Transaction ID and/or Description
    middle = tokens[middle_start:-3]
    description: str

    if transaction_id is not None:
        description = " ".join(middle).strip() if middle else "Transaction"
    elif len(middle) == 1:
        description = middle[0]
    elif len(middle) >= 2:
        first_mid = middle[0].strip()
        if is_txn_id(first_mid) and not any(c in first_mid for c in " "):
            transaction_id = first_mid
            description = " ".join(middle[1:]).strip()
        else:
            description = " ".join(middle).strip()
    else:
        raise TransactionParsingError(
            f"Missing transaction description in row: {tokens}"
        )

    counterparty = extract_counterparty(description)

    try:
        return Transaction(
            date=txn_date,
            transaction_id=transaction_id,
            description=description,
            debit=debit,
            credit=credit,
            balance=balance,
            counterparty=counterparty,
        )
    except Exception as exc:
        raise TransactionParsingError(
            f"Validation failed for parsed transaction {tokens}: {exc}"
        ) from exc


def parse_transactions(extraction: PDFDocumentExtraction) -> TransactionStatement:
    """Parse raw PDF extraction output into a validated TransactionStatement.

    Args:
        extraction: PDFDocumentExtraction object from M2 pdf_parser service.

    Returns:
        TransactionStatement containing account metadata and validated transactions.

    Raises:
        TransactionParsingError: If structured transaction rows cannot be extracted or validated.
    """
    all_lines: List[str] = []
    for page in extraction.pages:
        for line in page.text.splitlines():
            cleaned = line.strip()
            if cleaned:
                all_lines.append(cleaned)

    customer_name, account_number, statement_period = extract_metadata(all_lines)

    # Filter out running page headers, page numbers, and repeated table column headers
    cleaned_lines = [line for line in all_lines if not is_header_or_footer(line)]

    # Locate row start boundaries:
    # 1. Line is a Txn ID followed by a Date (Txn ID-first layout)
    # 2. Line is a Date not preceded by a Txn ID (Date-first layout)
    starts: List[int] = []
    for i, line in enumerate(cleaned_lines):
        if is_txn_id(line):
            if i + 1 < len(cleaned_lines) and parse_date(cleaned_lines[i + 1]) is not None:
                starts.append(i)
                continue
        if parse_date(line) is not None:
            if i > 0 and is_txn_id(cleaned_lines[i - 1]):
                continue
            starts.append(i)

    transactions: List[Transaction] = []
    running_balance: float = 0.0

    _FOOTER_PREFIXES = (
        "dataset note:",
        "notes:",
        "note:",
        "disclaimer:",
        "synthetic",
        "fictional",
        "this statement",
        "not a real",
    )
    _EMPTY_MARKERS = {"—", "–", "-", "N/A", "NA", "nil", "None", "--"}

    for i, start_idx in enumerate(starts):
        end_idx = starts[i + 1] if i + 1 < len(starts) else len(cleaned_lines)
        row_tokens = cleaned_lines[start_idx:end_idx]

        # Stage 1: forward-pass stop at known footer keyword prefixes
        filtered_tokens: List[str] = []
        for token in row_tokens:
            if token.lower().startswith(_FOOTER_PREFIXES):
                break
            filtered_tokens.append(token)

        if not filtered_tokens:
            continue

        try:
            if is_flow_layout(filtered_tokens):
                txn, running_balance = parse_flow_row(filtered_tokens, running_balance)
                transactions.append(txn)
            else:
                # Stage 2: trim trailing tokens that cannot be a valid amount or placeholder
                while len(filtered_tokens) > 4:
                    last = filtered_tokens[-1].strip()
                    if last in _EMPTY_MARKERS:
                        break
                    if is_valid_amount_str(last):
                        break
                    logger.debug(f"Stripping trailing non-amount token from row: {last!r}")
                    filtered_tokens.pop()

                txn = parse_row_tokens(filtered_tokens)
                running_balance = txn.balance
                transactions.append(txn)
        except Exception as row_err:
            logger.warning(
                f"Skipping unparseable row {i + 1}/{len(starts)} ({filtered_tokens[:3]}...): {row_err}"
            )
            continue

    if not transactions:
        raise TransactionParsingError(
            f"No valid transactions could be extracted from statement '{extraction.file_name}'."
        )

    logger.info(
        f"Parsed {len(transactions)} validated transaction(s) from '{extraction.file_name}'"
    )

    return TransactionStatement(
        account_number=account_number,
        customer_name=customer_name,
        statement_period=statement_period,
        transactions=transactions,
    )
