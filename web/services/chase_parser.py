"""Parse Chase credit card PDF statements into transaction records."""

import re
import io
from dataclasses import dataclass
import pdfplumber


@dataclass
class StatementTransaction:
    date: str            # YYYY-MM-DD
    merchant: str        # cleaned merchant description
    amount: float        # positive = purchase, negative = payment/credit
    card_last_four: str  # which card on the account
    is_payment: bool     # True for payments/credits section


# Regex for a transaction line: MM/DD  description  [-]amount
_TXN_RE = re.compile(
    r"^(\d{2}/\d{2})\s+(.+?)\s+([-]?[\d,]+\.\d{2})$"
)

# Exchange rate continuation: "123.45 X 1.234567890 (EXCHG RATE)"
_EXCHG_RE = re.compile(r"^\d+\.?\d*\s+X\s+[\d.]+\s+\(EXCHG RATE\)")

# Currency name line (appears before exchange rate): "EURO", "SHEQEL", etc.
_CURRENCY_RE = re.compile(r"^[A-Z]{3,10}$")

# Flight segment continuation: "090325 1 R JFK CDG" or "2 E CDG TLV"
_FLIGHT_RE = re.compile(r"^(\d{6}\s+)?\d+\s+[A-Z]\s+[A-Z]{3}\s+[A-Z]{3}")

# Cardholder transaction summary line
_CARDHOLDER_RE = re.compile(r"^TRANSACTIONS THIS CYCLE \(CARD (\d{4})\)")

# Section headers
_PAYMENTS_HEADER = "PAYMENTS AND OTHER CREDITS"
_PURCHASE_HEADER = "PURCHASE"

# Lines to skip
_SKIP_PATTERNS = [
    re.compile(r"^ACCOUNT ACTIVITY"),
    re.compile(r"^Date of$"),
    re.compile(r"^Transaction\s+Merchant"),
    re.compile(r"^\$ Amount$"),
    re.compile(r"^Page\s*\d+"),
    re.compile(r"^0000001\s+FIS"),
    re.compile(r"^MMaannaaggee"),
    re.compile(r"^www\.chase\.com"),
    re.compile(r"^11--880"),
    re.compile(r"^CChhaassee"),
    re.compile(r"^Denotes Flex"),
    re.compile(r"^\d{4} Totals"),
    re.compile(r"^Total (fees|interest)"),
    re.compile(r"^YYeeaarr--ttoo"),
    re.compile(r"^yyoouu mmaayy"),
    re.compile(r"^INCLUDING PAYMENTS"),
    re.compile(r"^IINNTTEERREESSTT"),
    re.compile(r"^Your Annual"),
    re.compile(r"^Annual\s+Balance"),
    re.compile(r"^Balance Type"),
    re.compile(r"^Rate \(APR\)"),
    re.compile(r"^PURCHASES$"),
    re.compile(r"^CASH ADVANCES$"),
    re.compile(r"^BALANCE TRANSFERS$"),
    re.compile(r"^Flex for Business"),
    re.compile(r"^Cash Advances"),
    re.compile(r"^Balance Transfers"),
    re.compile(r"^Purchases\s+\d"),
    re.compile(r"^\d+ Days in Billing"),
    re.compile(r"^\(v\) ="),
    re.compile(r"^\(d\) ="),
    re.compile(r"^\(a\) ="),
    re.compile(r"^Please see Info"),
    re.compile(r"^other important"),
    re.compile(r"^x$"),
    re.compile(r"^This Statem"),
    re.compile(r"^Statement Date:"),
]


def parse_chase_pdf(pdf_bytes, statement_date):
    """Parse a Chase credit card PDF into transaction records.

    Args:
        pdf_bytes: Raw PDF file content as bytes.
        statement_date: Statement date as 'YYYY-MM-DD' string.

    Returns:
        List of StatementTransaction.
    """
    stmt_year = int(statement_date[:4])
    stmt_month = int(statement_date[5:7])

    pdf = pdfplumber.open(io.BytesIO(pdf_bytes))
    all_lines = []
    for page in pdf.pages:
        text = page.extract_text()
        if text:
            all_lines.extend(text.split("\n"))
    pdf.close()

    # Find where ACCOUNT ACTIVITY starts
    # Chase PDFs have doubled letters on some pages: "AACCCCOOUUNNTT AACCTTIIVVIITTYY"
    start_idx = 0
    for i, line in enumerate(all_lines):
        if ("ACCOUNT ACTIVITY" in line or "AACCCCOOUUNNTT AACCTTIIVVIITTYY" in line) \
                and "SUMMARY" not in line and "SSUUMMMMAARRYY" not in line:
            start_idx = i
            break

    transactions = []
    in_payments_section = False
    # Index in transactions[] where current card's block started
    card_block_start = 0

    for i in range(start_idx, len(all_lines)):
        line = all_lines[i].strip()
        if not line:
            continue

        # Check for section headers
        if line == _PAYMENTS_HEADER:
            in_payments_section = True
            continue
        if line.startswith("PURCHASE") and len(line) < 30 \
                and "SUMMARY" not in line and "Purchases" not in line:
            in_payments_section = False
            continue

        # Check for cardholder summary line → retroactively assign card
        m_card = _CARDHOLDER_RE.match(line)
        if m_card:
            card = m_card.group(1)
            for t in transactions[card_block_start:]:
                t.card_last_four = card
            card_block_start = len(transactions)
            continue

        # Skip cardholder name lines (ALL CAPS name, e.g. "YAAKOV Y ERLICHMAN")
        if re.match(r"^[A-Z][A-Z ]+$", line) and len(line) > 4 \
                and not _CURRENCY_RE.match(line):
            continue

        # Skip continuation lines
        if _EXCHG_RE.match(line):
            continue
        if _CURRENCY_RE.match(line):
            continue
        if _FLIGHT_RE.match(line):
            continue

        # Skip known noise
        if any(p.match(line) for p in _SKIP_PATTERNS):
            continue

        # Try to match a transaction line
        m_txn = _TXN_RE.match(line)
        if m_txn:
            raw_date = m_txn.group(1)  # MM/DD
            merchant = m_txn.group(2).strip()
            amount_str = m_txn.group(3).replace(",", "")
            amount = float(amount_str)

            txn_date = _resolve_date(raw_date, stmt_year, stmt_month)

            is_payment = amount < 0 or in_payments_section

            transactions.append(StatementTransaction(
                date=txn_date,
                merchant=merchant,
                amount=amount,
                card_last_four="",
                is_payment=is_payment,
            ))

    # If there are remaining transactions without a card assignment
    # (e.g., single cardholder statement), leave card_last_four empty
    return transactions


def _resolve_date(mm_dd, stmt_year, stmt_month):
    """Resolve MM/DD to YYYY-MM-DD using statement date context.

    Transaction month > statement month means it's from the prior year
    (e.g., transaction 12/15 on a Jan 2024 statement = 2023-12-15).
    """
    parts = mm_dd.split("/")
    txn_month = int(parts[0])
    txn_day = int(parts[1])

    if txn_month > stmt_month:
        year = stmt_year - 1
    else:
        year = stmt_year

    return f"{year:04d}-{txn_month:02d}-{txn_day:02d}"
