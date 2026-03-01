import json
import os
import tempfile
from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from web.config import Config
from web.models import db, Category, Account, MerchantMapping, Transaction
from web.services.sheet_service import SheetService, SheetServiceError
from web.services.sheet_parser import parse_sheet, get_available_months, RawSheetRecord
from web.services.import_pipeline import (
    stage_records, commit_staged, get_import_history, get_existing_source_refs,
    stage_statement_records, commit_statement_staged, get_statement_import_history,
    stage_bank_csv_records, commit_bank_csv_staged, get_bank_csv_import_history,
)
from web.services.bank_csv_parser import parse_bank_csv
from web.services.drive_service import DriveService, DriveServiceError
from web.services.chase_parser import parse_chase_pdf

imports_bp = Blueprint("imports", __name__)

_STAGE_DIR = os.path.join(tempfile.gettempdir(), "budget_app_staging")


def _get_sheet_service():
    return SheetService(
        Config.GOOGLE_TOKEN_PATH,
        Config.GOOGLE_CREDENTIALS_PATH,
        Config.GOOGLE_SHEET_ID,
    )


def _save_staged(staged):
    os.makedirs(_STAGE_DIR, exist_ok=True)
    path = os.path.join(_STAGE_DIR, f"staged_{os.getpid()}_{id(staged)}.json")
    with open(path, "w") as f:
        json.dump(staged, f)
    return path


def _load_staged(path):
    if not path or not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


_BANK_CSV_MIN_DATE = "2025-09-01"

_BANK_ACCOUNT_OPTIONS = [
    {"last_four": "2745", "label": "Chase Checking (2745) — Personal"},
    {"last_four": "6227", "label": "Chase Checking (6227) — Primary/Joint"},
]


def _get_bank_accounts():
    """Return list of bank account options for the CSV upload form."""
    return _BANK_ACCOUNT_OPTIONS


def _ensure_bank_account(last_four):
    """Ensure a Chase Checking account row exists for last_four, return its id."""
    acct = Account.query.filter_by(last_four=last_four, account_type="bank", institution="Chase").first()
    if not acct:
        acct = Account(
            name=f"Chase Checking ({last_four})",
            account_type="bank",
            institution="Chase",
            last_four=last_four,
        )
        db.session.add(acct)
        db.session.commit()
    return acct.id


@imports_bp.route("/")
def import_page():
    """Main import page: step 1 — pick a sheet tab."""
    try:
        svc = _get_sheet_service()
        tabs = svc.get_sheet_names()
        tabs = [t for t in tabs if "expense" in t.lower()]
    except SheetServiceError as e:
        tabs = []
        flash(f"Could not connect to Google Sheet: {e}", "danger")

    history = get_import_history()
    stmt_history = get_statement_import_history()
    bank_history = get_bank_csv_import_history()
    bank_accounts = _get_bank_accounts()
    return render_template(
        "imports.html", step=1, tabs=tabs, history=history,
        config_folders=Config.CHASE_DRIVE_FOLDERS, stmt_history=stmt_history,
        bank_history=bank_history, bank_accounts=bank_accounts,
    )


@imports_bp.route("/months", methods=["POST"])
def load_months():
    """Step 2 — show available months for the selected tab."""
    tab = request.form.get("tab", "")
    if not tab:
        flash("Please select a sheet tab.", "warning")
        return redirect(url_for("imports.import_page"))

    try:
        svc = _get_sheet_service()
        data = svc.read_all_values(tab)
        tabs = [t for t in svc.get_sheet_names() if "expense" in t.lower()]
    except SheetServiceError as e:
        flash(f"Error reading sheet: {e}", "danger")
        return redirect(url_for("imports.import_page"))

    records = parse_sheet(data, tab)
    months = get_available_months(records)

    if not months:
        flash("No months found in this sheet tab.", "warning")
        return redirect(url_for("imports.import_page"))

    # Determine which months are fully imported
    existing_refs = get_existing_source_refs()
    month_total = {}
    month_imported = {}
    for r in records:
        month_total[r.month] = month_total.get(r.month, 0) + 1
        ref = f"{r.sheet_tab}:{r.month}:{r.merchant_name}"
        if ref in existing_refs:
            month_imported[r.month] = month_imported.get(r.month, 0) + 1

    fully_imported = {
        m for m in month_total
        if month_imported.get(m, 0) == month_total[m]
    }

    # Add import status to month list
    for m in months:
        m["imported"] = m["month"] in fully_imported

    history = get_import_history()
    stmt_history = get_statement_import_history()
    bank_history = get_bank_csv_import_history()
    return render_template(
        "imports.html",
        step=2,
        tabs=tabs,
        selected_tab=tab,
        months=months,
        history=history,
        config_folders=Config.CHASE_DRIVE_FOLDERS,
        stmt_history=stmt_history,
        bank_history=bank_history,
        bank_accounts=_get_bank_accounts(),
    )


@imports_bp.route("/preview", methods=["POST"])
def preview():
    """Step 3 — preview transactions before committing."""
    selected_months = set(request.form.getlist("months"))
    tab = request.form.get("tab", "Expense")

    if not selected_months:
        flash("Please select at least one month.", "warning")
        return redirect(url_for("imports.import_page"))

    try:
        svc = _get_sheet_service()
        data = svc.read_all_values(tab)
        tabs = [t for t in svc.get_sheet_names() if "expense" in t.lower()]
    except SheetServiceError as e:
        flash(f"Could not read sheet: {e}", "danger")
        return redirect(url_for("imports.import_page"))

    records = parse_sheet(data, tab)
    staged = stage_records(records, selected_months)

    staged_path = _save_staged(staged)
    session["_staged_path"] = staged_path

    summary = {
        "ready": sum(1 for s in staged if s["status"] == "ready"),
        "duplicate": sum(1 for s in staged if s["status"] == "duplicate"),
        "unmatched": sum(1 for s in staged if s["status"] == "unmatched"),
        "skipped": sum(1 for s in staged if s["status"] == "skipped"),
    }

    categories = Category.query.filter_by(is_active=True).order_by(Category.name).all()
    accounts = Account.query.filter_by(is_active=True).order_by(Account.name).all()
    history = get_import_history()
    stmt_history = get_statement_import_history()
    bank_history = get_bank_csv_import_history()

    return render_template(
        "imports.html",
        step=3,
        tabs=tabs,
        staged=staged,
        summary=summary,
        categories=categories,
        accounts=accounts,
        history=history,
        selected_months=selected_months,
        selected_tab=tab,
        config_folders=Config.CHASE_DRIVE_FOLDERS,
        stmt_history=stmt_history,
        bank_history=bank_history,
        bank_accounts=_get_bank_accounts(),
    )


@imports_bp.route("/commit", methods=["POST"])
def commit():
    """Step 4 — commit checked transactions to the database."""
    staged_path = session.get("_staged_path")
    staged = _load_staged(staged_path)
    if not staged:
        flash("Nothing to commit. Please run a preview first.", "warning")
        return redirect(url_for("imports.import_page"))

    selected_refs = set(request.form.getlist("commit_refs"))
    if selected_refs:
        to_commit = [s for s in staged if s["source_ref"] in selected_refs and s["status"] == "ready"]
    else:
        to_commit = [s for s in staged if s["status"] == "ready"]

    try:
        count = commit_staged(to_commit)
        flash(f"Successfully imported {count} transactions.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Import failed: {e}", "danger")

    session.pop("_staged_path", None)
    if staged_path and os.path.exists(staged_path):
        os.remove(staged_path)

    return redirect(url_for("imports.import_page"))


@imports_bp.route("/add-mapping", methods=["POST"])
def add_mapping():
    """HTMX: create a MerchantMapping inline during preview."""
    merchant_name = request.form.get("merchant_name", "").strip()
    category_id = request.form.get("category_id", type=int)
    account_id = request.form.get("account_id", type=int)

    if not merchant_name or not category_id:
        return '<td colspan="8" class="text-danger">Merchant and category are required.</td>'

    existing = MerchantMapping.query.filter_by(merchant_name=merchant_name).first()
    if existing:
        existing.category_id = category_id
        existing.account_id = account_id
    else:
        db.session.add(MerchantMapping(
            merchant_name=merchant_name,
            category_id=category_id,
            account_id=account_id,
            default_type="expense",
        ))
    db.session.commit()

    mapping = MerchantMapping.query.filter_by(merchant_name=merchant_name).first()

    # Update staged data on disk (works for sheet, statement, and bank CSV staging)
    for key in ("_staged_path", "_stmt_staged_path", "_bank_staged_path"):
        staged_path = session.get(key)
        staged = _load_staged(staged_path)
        if staged:
            changed = False
            for s in staged:
                if s["merchant"].lower() == merchant_name.lower() and s["status"] == "unmatched":
                    s["category_id"] = mapping.category_id
                    s["category_name"] = mapping.category.name if mapping.category else ""
                    s["account_id"] = mapping.account_id
                    s["account_name"] = mapping.account.name if mapping.account else ""
                    s["type"] = mapping.default_type
                    s["status"] = "ready"
                    s["skip_reason"] = ""
                    changed = True
            if changed:
                with open(staged_path, "w") as f:
                    json.dump(staged, f)

    cat_name = mapping.category.name if mapping.category else ""
    acct_name = mapping.account.name if mapping.account else ""
    return (
        f'<td></td>'
        f'<td>{merchant_name}</td>'
        f'<td></td><td></td>'
        f'<td>{cat_name}</td>'
        f'<td>{acct_name}</td>'
        f'<td><span class="badge bg-success">mapped</span></td>'
        f'<td class="small text-success">Re-run preview to commit this merchant</td>'
    )


# ══════════════════════════════════════════════════════════════════════
#  Statement Import Routes
# ══════════════════════════════════════════════════════════════════════

def _get_drive_service():
    return DriveService(Config.GOOGLE_TOKEN_PATH, Config.GOOGLE_CREDENTIALS_PATH)


@imports_bp.route("/statements", methods=["POST"])
def list_statements():
    """Step S1 — list available PDFs in the selected Drive folder."""
    folder_idx = request.form.get("folder_idx", type=int)
    folders = Config.CHASE_DRIVE_FOLDERS
    if folder_idx is None or folder_idx < 0 or folder_idx >= len(folders):
        flash("Please select a folder.", "warning")
        return redirect(url_for("imports.import_page"))

    folder = folders[folder_idx]
    try:
        drv = _get_drive_service()
        pdfs = drv.list_pdfs(folder["folder_id"])
    except DriveServiceError as e:
        flash(f"Drive error: {e}", "danger")
        return redirect(url_for("imports.import_page"))

    # Check which statements are already imported
    stmt_history = get_statement_import_history()
    imported_months = {h["month"] for h in stmt_history}

    for p in pdfs:
        stmt_month = p["statement_date"][:7] if len(p["statement_date"]) >= 7 else ""
        p["imported"] = stmt_month in imported_months

    # Get sheet data for the main import section
    try:
        svc = _get_sheet_service()
        tabs = [t for t in svc.get_sheet_names() if "expense" in t.lower()]
    except SheetServiceError:
        tabs = []

    history = get_import_history()
    stmt_history_all = get_statement_import_history()

    bank_history = get_bank_csv_import_history()

    return render_template(
        "imports.html",
        step=1,
        tabs=tabs,
        history=history,
        stmt_step="list",
        stmt_pdfs=pdfs,
        stmt_folder=folder,
        stmt_folder_idx=folder_idx,
        stmt_folders=folders,
        stmt_history=stmt_history_all,
        bank_history=bank_history,
        bank_accounts=_get_bank_accounts(),
    )


@imports_bp.route("/statement-preview", methods=["POST"])
def statement_preview():
    """Step S2 — download selected PDF, parse, stage, show preview."""
    file_id = request.form.get("file_id", "")
    file_name = request.form.get("file_name", "")
    statement_date = request.form.get("statement_date", "")
    folder_idx = request.form.get("folder_idx", type=int, default=0)

    folders = Config.CHASE_DRIVE_FOLDERS
    folder = folders[folder_idx] if 0 <= folder_idx < len(folders) else folders[0]

    if not file_id:
        flash("Please select a statement.", "warning")
        return redirect(url_for("imports.import_page"))

    try:
        drv = _get_drive_service()
        pdf_bytes = drv.download_pdf(file_id)
    except DriveServiceError as e:
        flash(f"Download error: {e}", "danger")
        return redirect(url_for("imports.import_page"))

    transactions = parse_chase_pdf(pdf_bytes, statement_date)
    staged = stage_statement_records(
        transactions, folder["last_four"],
        card_category_overrides=Config.CARD_CATEGORY_OVERRIDES,
    )

    staged_path = _save_staged(staged)
    session["_stmt_staged_path"] = staged_path

    summary = {
        "ready": sum(1 for s in staged if s["status"] == "ready"),
        "duplicate": sum(1 for s in staged if s["status"] == "duplicate"),
        "unmatched": sum(1 for s in staged if s["status"] == "unmatched"),
        "payment": sum(1 for s in staged if s["status"] == "payment"),
    }

    categories = Category.query.filter_by(is_active=True).order_by(Category.name).all()
    accounts = Account.query.filter_by(is_active=True).order_by(Account.name).all()

    try:
        svc = _get_sheet_service()
        tabs = [t for t in svc.get_sheet_names() if "expense" in t.lower()]
    except SheetServiceError:
        tabs = []

    history = get_import_history()
    stmt_history = get_statement_import_history()
    bank_history = get_bank_csv_import_history()

    return render_template(
        "imports.html",
        step=1,
        tabs=tabs,
        history=history,
        stmt_step="preview",
        stmt_staged=staged,
        stmt_summary=summary,
        stmt_file_name=file_name,
        stmt_statement_date=statement_date,
        stmt_folder=folder,
        stmt_folder_idx=folder_idx,
        stmt_folders=Config.CHASE_DRIVE_FOLDERS,
        stmt_history=stmt_history,
        bank_history=bank_history,
        bank_accounts=_get_bank_accounts(),
        categories=categories,
        accounts=accounts,
    )


@imports_bp.route("/statement-commit", methods=["POST"])
def statement_commit():
    """Step S3 — commit checked statement transactions."""
    staged_path = session.get("_stmt_staged_path")
    staged = _load_staged(staged_path)
    if not staged:
        flash("Nothing to commit. Please run a preview first.", "warning")
        return redirect(url_for("imports.import_page"))

    selected_refs = set(request.form.getlist("commit_refs"))
    if selected_refs:
        to_commit = [s for s in staged if s["source_ref"] in selected_refs and s["status"] == "ready"]
    else:
        to_commit = [s for s in staged if s["status"] == "ready"]

    try:
        count = commit_statement_staged(to_commit)
        flash(f"Successfully imported {count} statement transactions.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Import failed: {e}", "danger")

    session.pop("_stmt_staged_path", None)
    if staged_path and os.path.exists(staged_path):
        os.remove(staged_path)

    return redirect(url_for("imports.import_page"))


# ══════════════════════════════════════════════════════════════════════
#  Bank CSV Import Routes
# ══════════════════════════════════════════════════════════════════════

@imports_bp.route("/bank-csv-upload", methods=["POST"])
def bank_csv_upload():
    """Upload a Chase bank CSV, parse, stage, and show preview."""
    csv_file = request.files.get("csv_file")
    last_four = request.form.get("last_four", "").strip()

    if not csv_file or not csv_file.filename:
        flash("Please select a CSV file.", "warning")
        return redirect(url_for("imports.import_page"))

    if not last_four:
        flash("Please select a bank account.", "warning")
        return redirect(url_for("imports.import_page"))

    _ensure_bank_account(last_four)

    try:
        csv_content = csv_file.read().decode("utf-8-sig")
    except Exception as e:
        flash(f"Could not read CSV file: {e}", "danger")
        return redirect(url_for("imports.import_page"))

    transactions = parse_bank_csv(csv_content, min_date=_BANK_CSV_MIN_DATE)
    if not transactions:
        flash("No transactions found in CSV (after date filter).", "warning")
        return redirect(url_for("imports.import_page"))

    staged = stage_bank_csv_records(transactions, last_four)

    staged_path = _save_staged(staged)
    session["_bank_staged_path"] = staged_path

    summary = {
        "ready": sum(1 for s in staged if s["status"] == "ready"),
        "duplicate": sum(1 for s in staged if s["status"] == "duplicate"),
        "unmatched": sum(1 for s in staged if s["status"] == "unmatched"),
        "skipped": sum(1 for s in staged if s["status"] == "skipped"),
    }

    categories = Category.query.filter_by(is_active=True).order_by(Category.name).all()
    accounts = Account.query.filter_by(is_active=True).order_by(Account.name).all()

    try:
        svc = _get_sheet_service()
        tabs = [t for t in svc.get_sheet_names() if "expense" in t.lower()]
    except SheetServiceError:
        tabs = []

    history = get_import_history()
    stmt_history = get_statement_import_history()
    bank_history = get_bank_csv_import_history()

    return render_template(
        "imports.html",
        step=1,
        tabs=tabs,
        history=history,
        config_folders=Config.CHASE_DRIVE_FOLDERS,
        stmt_history=stmt_history,
        bank_step="preview",
        bank_staged=staged,
        bank_summary=summary,
        bank_file_name=csv_file.filename,
        bank_last_four=last_four,
        bank_history=bank_history,
        bank_accounts=_get_bank_accounts(),
        categories=categories,
        accounts=accounts,
    )


@imports_bp.route("/bank-csv-commit", methods=["POST"])
def bank_csv_commit():
    """Commit checked bank CSV transactions."""
    staged_path = session.get("_bank_staged_path")
    staged = _load_staged(staged_path)
    if not staged:
        flash("Nothing to commit. Please upload a CSV first.", "warning")
        return redirect(url_for("imports.import_page"))

    selected_refs = set(request.form.getlist("commit_refs"))
    if selected_refs:
        to_commit = [s for s in staged if s["source_ref"] in selected_refs and s["status"] == "ready"]
    else:
        to_commit = [s for s in staged if s["status"] == "ready"]

    try:
        count = commit_bank_csv_staged(to_commit)
        flash(f"Successfully imported {count} bank transactions.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Import failed: {e}", "danger")

    session.pop("_bank_staged_path", None)
    if staged_path and os.path.exists(staged_path):
        os.remove(staged_path)

    return redirect(url_for("imports.import_page"))


# ══════════════════════════════════════════════════════════════════════
#  Overlap Migration: mark Google Sheet entries as transfers
# ══════════════════════════════════════════════════════════════════════

@imports_bp.route("/mark-sheet-transfers", methods=["POST"])
def mark_sheet_transfers():
    """Mark Google Sheet expense entries as 'transfer' for Sep 2025+ to avoid
    double-counting with bank CSV imports.

    Targets all non-CC-category expenses from google_sheet source.
    Category ID 8 = "Credit Card and Retail" (CC bill payments — keep as-is).
    """
    cc_category_id = 8  # "Credit Card and Retail"
    count = (
        Transaction.query
        .filter(
            Transaction.source == "google_sheet",
            Transaction.type == "expense",
            Transaction.date >= "2025-09-01",
            Transaction.category_id != cc_category_id,
        )
        .update({"type": "transfer"})
    )
    db.session.commit()
    flash(f"Marked {count} Google Sheet entries as transfers (Sep 2025+).", "info")
    return redirect(url_for("imports.import_page"))
