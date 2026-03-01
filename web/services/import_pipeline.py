"""Import pipeline: merchant matching, deduplication, staging, and commit."""

import re
from datetime import datetime
from web.models import db, Transaction, MerchantMapping, Category, Account


def parse_amount(amount_str):
    """Parse an amount string into a float. Returns (value, ok).

    Handles: "$1,086", "$720", "600", "386", "1662.01"
    Rejects: "NA", "Bank", "Ink", "", "$0" is valid (returns 0.0).
    """
    s = amount_str.strip()
    if not s:
        return 0.0, False

    # Remove $ and commas
    cleaned = s.replace("$", "").replace(",", "").strip()
    if not cleaned:
        return 0.0, False

    try:
        return float(cleaned), True
    except ValueError:
        return 0.0, False


def parse_date(date_str, month):
    """Parse a date string into YYYY-MM-DD format.

    Handles: "1/1/25", "12/30/25", "10/1/2016", "All", ""
    Falls back to 1st of the month if date is unclear.
    """
    s = date_str.strip()

    # "All" or empty → 1st of month
    if not s or s.lower() == "all":
        return f"{month}-01"

    # Try M/D/YY or M/D/YYYY
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", s)
    if m:
        mon, day, yr = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if yr < 100:
            yr += 2000
        return f"{yr:04d}-{mon:02d}-{day:02d}"

    # Fallback
    return f"{month}-01"


def build_merchant_map():
    """Load all MerchantMapping rows into a dict keyed by lowercase merchant name."""
    mappings = MerchantMapping.query.all()
    return {m.merchant_name.lower(): m for m in mappings}


def get_existing_source_refs():
    """Get set of existing source_ref values for google_sheet transactions."""
    refs = db.session.query(Transaction.source_ref).filter(
        Transaction.source == "google_sheet"
    ).all()
    return {r[0] for r in refs}


def make_source_ref(sheet_tab, month, merchant_name):
    """Build a unique source reference key."""
    return f"{sheet_tab}:{month}:{merchant_name}"


def stage_records(records, selected_months):
    """Process parsed records into staged transactions for review.

    Args:
        records: List of RawSheetRecord from the parser.
        selected_months: Set of YYYY-MM strings to import.

    Returns:
        List of staged transaction dicts, each with:
            merchant, date, amount, month, category_id, category_name,
            account_id, account_name, type, source_ref, status, skip_reason,
            sheet_tab, row_index
    """
    merchant_map = build_merchant_map()
    existing_refs = get_existing_source_refs()

    staged = []
    for r in records:
        if r.month not in selected_months:
            continue

        source_ref = make_source_ref(r.sheet_tab, r.month, r.merchant_name)
        amount, amount_ok = parse_amount(r.amount_str)
        date = parse_date(r.date_str, r.month)
        mapping = merchant_map.get(r.merchant_name.lower())

        # Determine status
        if not amount_ok:
            status = "skipped"
            skip_reason = f"Non-numeric amount: {r.amount_str!r}" if r.amount_str else "Empty amount"
        elif source_ref in existing_refs:
            status = "duplicate"
            skip_reason = "Already imported"
        elif mapping is None:
            status = "unmatched"
            skip_reason = "No merchant mapping"
        else:
            status = "ready"
            skip_reason = ""

        entry = {
            "merchant": r.merchant_name,
            "date": date,
            "amount": amount,
            "amount_str": r.amount_str,
            "month": r.month,
            "category_id": mapping.category_id if mapping else None,
            "category_name": mapping.category.name if mapping and mapping.category else "",
            "account_id": mapping.account_id if mapping else None,
            "account_name": mapping.account.name if mapping and mapping.account else "",
            "type": mapping.default_type if mapping else "expense",
            "source_ref": source_ref,
            "status": status,
            "skip_reason": skip_reason,
            "sheet_tab": r.sheet_tab,
            "row_index": r.row_index,
        }
        staged.append(entry)

    return staged


def commit_staged(staged_transactions):
    """Commit approved staged transactions to the database.

    Args:
        staged_transactions: List of staged dicts with status='ready'.

    Returns:
        Number of transactions created.
    """
    count = 0
    for s in staged_transactions:
        if s["status"] != "ready":
            continue

        txn = Transaction(
            date=s["date"],
            amount=s["amount"],
            type=s["type"],
            category_id=s["category_id"],
            account_id=s["account_id"],
            merchant=s["merchant"],
            description="",
            source="google_sheet",
            source_ref=s["source_ref"],
        )
        db.session.add(txn)
        count += 1

    db.session.commit()
    return count


def get_import_history():
    """Get summary of previously imported months.

    Returns list of dicts: [{month, count, total, imported_at}, ...]
    """
    results = (
        db.session.query(
            db.func.substr(Transaction.date, 1, 7).label("month"),
            db.func.count(Transaction.id).label("count"),
            db.func.sum(Transaction.amount).label("total"),
            db.func.min(Transaction.created_at).label("imported_at"),
        )
        .filter(Transaction.source == "google_sheet")
        .group_by(db.func.substr(Transaction.date, 1, 7))
        .order_by(db.func.substr(Transaction.date, 1, 7).desc())
        .all()
    )

    return [
        {
            "month": r.month,
            "count": r.count,
            "total": r.total or 0,
            "imported_at": r.imported_at,
        }
        for r in results
    ]


# ── Bank CSV import helpers ───────────────────────────────────────────

def _make_bank_source_ref(last_four, date, description, amount):
    """Build a unique source reference for a bank CSV transaction.

    Format: bank:{last4}:{date}:{desc_hash}:{amount}
    """
    cleaned = re.sub(r"[^A-Z0-9]", "_", description.upper())[:20]
    return f"bank:{last_four}:{date}:{cleaned}:{amount:.2f}"


def _get_existing_bank_refs():
    """Get set of existing source_ref values for bank_csv transactions."""
    refs = db.session.query(Transaction.source_ref).filter(
        Transaction.source == "bank_csv"
    ).all()
    return {r[0] for r in refs}


def stage_bank_csv_records(transactions, account_last_four):
    """Process parsed bank CSV transactions into staged records for review.

    Args:
        transactions: List of BankTransaction from bank_csv_parser.
        account_last_four: Last 4 digits of the checking account.

    Returns:
        List of staged transaction dicts.
    """
    merchant_map = build_merchant_map()
    existing_refs = _get_existing_bank_refs()

    staged = []
    for t in transactions:
        source_ref = _make_bank_source_ref(
            account_last_four, t.date, t.merchant, t.amount
        )
        mapping = merchant_map.get(t.merchant.lower())

        if t.is_skip:
            status = "skipped"
            skip_reason = f"Skipped type: {t.chase_type}"
        elif source_ref in existing_refs:
            status = "duplicate"
            skip_reason = "Already imported"
        elif mapping is None:
            status = "unmatched"
            skip_reason = "No merchant mapping"
        else:
            status = "ready"
            skip_reason = ""

        entry = {
            "merchant": t.merchant,
            "date": t.date,
            "amount": t.amount,
            "chase_type": t.chase_type,
            "direction": t.direction,
            "category_id": mapping.category_id if mapping else None,
            "category_name": mapping.category.name if mapping and mapping.category else "",
            "account_id": mapping.account_id if mapping else None,
            "account_name": mapping.account.name if mapping and mapping.account else "",
            "type": mapping.default_type if mapping else t.direction,
            "source_ref": source_ref,
            "status": status,
            "skip_reason": skip_reason,
            "is_skip": t.is_skip,
        }
        staged.append(entry)

    return staged


def commit_bank_csv_staged(staged_transactions):
    """Commit approved bank CSV transactions to the database.

    Returns number of transactions created.
    """
    count = 0
    for s in staged_transactions:
        if s["status"] != "ready":
            continue
        txn = Transaction(
            date=s["date"],
            amount=abs(s["amount"]),
            type=s["type"],
            category_id=s["category_id"],
            account_id=s["account_id"],
            merchant=s["merchant"],
            description=f"Bank {s.get('chase_type', '')}",
            source="bank_csv",
            source_ref=s["source_ref"],
        )
        db.session.add(txn)
        count += 1
    db.session.commit()
    return count


def get_bank_csv_import_history():
    """Get summary of previously imported bank CSV transactions grouped by month."""
    results = (
        db.session.query(
            db.func.substr(Transaction.date, 1, 7).label("month"),
            db.func.count(Transaction.id).label("count"),
            db.func.sum(Transaction.amount).label("total"),
            db.func.min(Transaction.created_at).label("imported_at"),
        )
        .filter(Transaction.source == "bank_csv")
        .group_by(db.func.substr(Transaction.date, 1, 7))
        .order_by(db.func.substr(Transaction.date, 1, 7).desc())
        .all()
    )

    return [
        {
            "month": r.month,
            "count": r.count,
            "total": r.total or 0,
            "imported_at": r.imported_at,
        }
        for r in results
    ]

# ── Statement import helpers ──────────────────────────────────────────

def _make_stmt_source_ref(last_four, date, merchant, amount):
    """Build a unique source reference for a statement transaction.

    Format: stmt:{last4}:{date}:{merchant_hash}:{amount}
    """
    cleaned = re.sub(r"[^A-Z0-9]", "_", merchant.upper())[:20]
    return f"stmt:{last_four}:{date}:{cleaned}:{amount:.2f}"


def _get_existing_stmt_refs():
    """Get set of existing source_ref values for statement_import transactions."""
    refs = db.session.query(Transaction.source_ref).filter(
        Transaction.source == "statement_import"
    ).all()
    return {r[0] for r in refs}


def stage_statement_records(transactions, account_last_four, card_category_overrides=None):
    """Process parsed statement transactions into staged records for review.

    Args:
        transactions: List of StatementTransaction from chase_parser.
        account_last_four: Last 4 digits of the account (from folder config).
        card_category_overrides: Dict of card_last_four -> category_id.
            Transactions on these cards get this category regardless of merchant mapping.

    Returns:
        List of staged transaction dicts.
    """
    merchant_map = build_merchant_map()
    existing_refs = _get_existing_stmt_refs()
    card_overrides = card_category_overrides or {}

    # Pre-load override categories
    override_cats = {}
    for card, cat_id in card_overrides.items():
        cat = Category.query.get(cat_id)
        if cat:
            override_cats[card] = cat

    staged = []
    for t in transactions:
        source_ref = _make_stmt_source_ref(account_last_four, t.date, t.merchant, t.amount)
        mapping = merchant_map.get(t.merchant.lower())
        card_override = override_cats.get(t.card_last_four)

        if source_ref in existing_refs:
            status = "duplicate"
            skip_reason = "Already imported"
        elif t.is_payment:
            status = "payment"
            skip_reason = "Payment/credit"
        elif card_override:
            # Card-level override — always ready
            status = "ready"
            skip_reason = ""
        elif mapping is None:
            status = "unmatched"
            skip_reason = "No merchant mapping"
        else:
            status = "ready"
            skip_reason = ""

        # Card override takes precedence over merchant mapping
        if card_override and status not in ("duplicate", "payment"):
            cat_id = card_override.id
            cat_name = card_override.name
            acct_id = mapping.account_id if mapping else None
            acct_name = mapping.account.name if mapping and mapping.account else ""
        elif mapping:
            cat_id = mapping.category_id
            cat_name = mapping.category.name if mapping.category else ""
            acct_id = mapping.account_id
            acct_name = mapping.account.name if mapping.account else ""
        else:
            cat_id = None
            cat_name = ""
            acct_id = None
            acct_name = ""

        entry = {
            "merchant": t.merchant,
            "date": t.date,
            "amount": t.amount,
            "card_last_four": t.card_last_four,
            "category_id": cat_id,
            "category_name": cat_name,
            "account_id": acct_id,
            "account_name": acct_name,
            "type": mapping.default_type if mapping else "expense",
            "source_ref": source_ref,
            "status": status,
            "skip_reason": skip_reason,
            "is_payment": t.is_payment,
        }
        staged.append(entry)

    return staged


def commit_statement_staged(staged_transactions):
    """Commit approved statement transactions to the database.

    Returns number of transactions created.
    """
    count = 0
    for s in staged_transactions:
        if s["status"] != "ready":
            continue
        txn = Transaction(
            date=s["date"],
            amount=abs(s["amount"]),
            type=s["type"],
            category_id=s["category_id"],
            account_id=s["account_id"],
            merchant=s["merchant"],
            description=f"Card {s.get('card_last_four', '')}",
            source="statement_import",
            source_ref=s["source_ref"],
        )
        db.session.add(txn)
        count += 1
    db.session.commit()
    return count


def get_statement_import_history():
    """Get summary of previously imported statement transactions.

    Returns list of dicts grouped by source_ref prefix (account + month).
    """
    results = (
        db.session.query(
            db.func.substr(Transaction.source_ref, 1, 16).label("key"),
            db.func.substr(Transaction.date, 1, 7).label("month"),
            db.func.count(Transaction.id).label("count"),
            db.func.sum(Transaction.amount).label("total"),
            db.func.min(Transaction.created_at).label("imported_at"),
        )
        .filter(Transaction.source == "statement_import")
        .group_by(db.func.substr(Transaction.date, 1, 7))
        .order_by(db.func.substr(Transaction.date, 1, 7).desc())
        .all()
    )

    return [
        {
            "month": r.month,
            "count": r.count,
            "total": r.total or 0,
            "imported_at": r.imported_at,
        }
        for r in results
    ]
