"""Parse Chase bank account CSV exports into transaction records."""

import csv
import io
import re
from dataclasses import dataclass
from datetime import datetime


@dataclass
class BankTransaction:
    date: str           # YYYY-MM-DD
    merchant: str       # cleaned merchant/description
    amount: float       # original signed amount (negative = debit)
    chase_type: str     # e.g. ACH_DEBIT, DEBIT_CARD, QUICKPAY_CREDIT
    is_skip: bool       # True for ACCT_XFER, LOAN_PMT
    direction: str      # "income", "expense", or "skip"


# Types that should be skipped entirely
_SKIP_TYPES = {"ACCT_XFER", "LOAN_PMT"}

# Credit types → income
_CREDIT_TYPES = {
    "ACH_CREDIT", "MISC_CREDIT", "PARTNERFI_TO_CHASE",
    "QUICKPAY_CREDIT", "CHECK_DEPOSIT", "ATM_DEPOSIT",
}

# Debit types → expense
_DEBIT_TYPES = {
    "ACH_DEBIT", "DEBIT_CARD", "BILLPAY", "CHECK_PAID",
    "ATM", "QUICKPAY_DEBIT", "CHASE_TO_PARTNERFI", "MISC_DEBIT",
}


def _classify(chase_type):
    """Return (is_skip, direction) for a Chase transaction type."""
    if chase_type in _SKIP_TYPES:
        return True, "skip"
    if chase_type in _CREDIT_TYPES:
        return False, "income"
    if chase_type in _DEBIT_TYPES:
        return False, "expense"
    # Unknown type — default to expense for debits, income for credits
    return False, "expense"


# ── Merchant name extraction ────────────────────────────────────────

# Zelle: "Zelle payment to/from NAME REF"
# Ref is the last non-space token: JPM..., BAC..., USAM..., TDP..., CTI..., or digits
_ZELLE_TO_RE = re.compile(r"^Zelle payment to (.+?)\s+\S{8,}$", re.IGNORECASE)
_ZELLE_FROM_RE = re.compile(r"^Zelle payment from (.+?)\s+\S{8,}$", re.IGNORECASE)

# Online Payment (billpay): "Online Payment REFNUM To MERCHANT MM/DD"
_BILLPAY_RE = re.compile(r"^Online Payment \d+ To (.+?) \d{2}/\d{2}$", re.IGNORECASE)

# ACH/WEB pattern: "MERCHANT   DETAIL   ...   PPD/WEB/CCD ID: NUM"
_ACH_ID_RE = re.compile(r"^(.+?)\s{2,}.*(?:PPD|WEB|CCD)\s+ID:\s*\S+$")

# Debit card pattern: "MERCHANT CITY STATE  DATE"
_DEBIT_CARD_RE = re.compile(
    r"^(.+?)\s{2,}.*\d{2}/\d{2}$"
)

# ATM patterns
_ATM_WITHDRAW_RE = re.compile(r"^(?:NON-CHASE )?ATM WITHDRAW", re.IGNORECASE)
_ATM_DEPOSIT_RE = re.compile(r"^ATM DEPOSIT", re.IGNORECASE)

# Check patterns
_CHECK_RE = re.compile(r"^CHECK\s+(\d+)", re.IGNORECASE)

# Remote deposit
_REMOTE_DEPOSIT_RE = re.compile(r"^REMOTE ONLINE DEPOSIT", re.IGNORECASE)

# Skip patterns (handled by type classification)
_PAYMENT_TO_CHASE_RE = re.compile(r"^Payment to Chase card", re.IGNORECASE)
_ONLINE_TRANSFER_RE = re.compile(r"^Online Transfer", re.IGNORECASE)


def _extract_merchant(description, chase_type):
    """Extract a clean merchant name from a Chase bank CSV description."""
    desc = description.strip()

    # Zelle to
    m = _ZELLE_TO_RE.match(desc)
    if m:
        return f"Zelle to {m.group(1).strip()}"

    # Zelle from
    m = _ZELLE_FROM_RE.match(desc)
    if m:
        return f"Zelle from {m.group(1).strip()}"

    # Billpay: "Online Payment REF To MERCHANT MM/DD"
    m = _BILLPAY_RE.match(desc)
    if m:
        return m.group(1).strip()

    # Payment to Chase card / Online Transfer → skip (already handled by type)
    if _PAYMENT_TO_CHASE_RE.match(desc) or _ONLINE_TRANSFER_RE.match(desc):
        return desc

    # ATM
    if _ATM_WITHDRAW_RE.match(desc):
        return "ATM Withdrawal"
    if _ATM_DEPOSIT_RE.match(desc):
        return "ATM Deposit"

    # Check
    m = _CHECK_RE.match(desc)
    if m:
        return f"Check {m.group(1)}"

    # Remote deposit
    if _REMOTE_DEPOSIT_RE.match(desc):
        return "Remote Deposit"

    # Interest
    if desc.upper() == "INTEREST PAYMENT":
        return "Interest Payment"

    # ACH with PPD/WEB/CCD ID — take first segment before multi-space
    m = _ACH_ID_RE.match(desc)
    if m:
        return m.group(1).strip()

    # Debit card — merchant before multi-space gap
    m = _DEBIT_CARD_RE.match(desc)
    if m:
        return m.group(1).strip()

    # Fallback: return full description
    return desc


def parse_bank_csv(csv_content, min_date=None):
    """Parse a Chase bank CSV into BankTransaction records.

    Args:
        csv_content: CSV file content as string.
        min_date: Optional minimum date as 'YYYY-MM-DD' string. Rows before this are excluded.

    Returns:
        List of BankTransaction.
    """
    reader = csv.DictReader(io.StringIO(csv_content))
    transactions = []

    for row in reader:
        # Parse posting date: MM/DD/YYYY
        raw_date = row.get("Posting Date", "").strip()
        if not raw_date:
            continue
        try:
            dt = datetime.strptime(raw_date, "%m/%d/%Y")
        except ValueError:
            continue

        date_str = dt.strftime("%Y-%m-%d")

        # Apply date filter
        if min_date and date_str < min_date:
            continue

        description = row.get("Description", "").strip()
        amount_str = row.get("Amount", "").strip()
        chase_type = row.get("Type", "").strip()

        try:
            amount = float(amount_str.replace(",", ""))
        except (ValueError, AttributeError):
            continue

        is_skip, direction = _classify(chase_type)
        merchant = _extract_merchant(description, chase_type)

        transactions.append(BankTransaction(
            date=date_str,
            merchant=merchant,
            amount=amount,
            chase_type=chase_type,
            is_skip=is_skip,
            direction=direction,
        ))

    return transactions
