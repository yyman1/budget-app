"""Batch-import Chase PDF statements from Google Drive.

Usage:
    python scripts/batch_import_statements.py [--min-date YYYY-MM]

Downloads all PDFs from configured Drive folders, parses them,
and commits new transactions. Duplicates are skipped automatically.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web.app import create_app
from web.config import Config
from web.models import db
from web.services.drive_service import DriveService
from web.services.chase_parser import parse_chase_pdf
from web.services.import_pipeline import stage_statement_records, commit_statement_staged


def batch_import(min_date="2025-09"):
    """Import all Chase statements from Drive folders.

    Args:
        min_date: Only import statements dated >= this YYYY-MM prefix.
    """
    app = create_app()

    with app.app_context():
        drv = DriveService(Config.GOOGLE_TOKEN_PATH, Config.GOOGLE_CREDENTIALS_PATH)
        folders = Config.CHASE_DRIVE_FOLDERS

        total_imported = 0
        total_dupes = 0
        total_skipped = 0

        for folder in folders:
            label = folder["label"]
            last_four = folder["last_four"]
            print(f"\n{'='*60}")
            print(f"Folder: {label}")
            print(f"{'='*60}")

            pdfs = drv.list_pdfs(folder["folder_id"])
            print(f"Found {len(pdfs)} PDFs")

            for pdf_info in sorted(pdfs, key=lambda p: p["statement_date"]):
                stmt_date = pdf_info["statement_date"]
                stmt_month = stmt_date[:7] if len(stmt_date) >= 7 else ""

                if stmt_month < min_date:
                    print(f"  SKIP {pdf_info['name']} — before {min_date}")
                    total_skipped += 1
                    continue

                print(f"\n  Processing: {pdf_info['name']} (date: {stmt_date})")

                pdf_bytes = drv.download_pdf(pdf_info["id"])
                transactions = parse_chase_pdf(pdf_bytes, stmt_date)
                print(f"    Parsed {len(transactions)} transactions")

                staged = stage_statement_records(
                    transactions, last_four,
                    card_category_overrides=Config.CARD_CATEGORY_OVERRIDES,
                )

                ready = [s for s in staged if s["status"] == "ready"]
                dupes = [s for s in staged if s["status"] == "duplicate"]
                unmatched = [s for s in staged if s["status"] == "unmatched"]
                payments = [s for s in staged if s["status"] == "payment"]

                print(f"    Ready: {len(ready)}, Duplicate: {len(dupes)}, "
                      f"Unmatched: {len(unmatched)}, Payment: {len(payments)}")

                if unmatched:
                    merchants = set(s["merchant"] for s in unmatched)
                    print(f"    Unmatched merchants: {merchants}")

                if ready:
                    count = commit_statement_staged(ready)
                    print(f"    Committed {count} transactions")
                    total_imported += count
                else:
                    print(f"    Nothing new to commit")

                total_dupes += len(dupes)

        print(f"\n{'='*60}")
        print(f"SUMMARY")
        print(f"{'='*60}")
        print(f"  New transactions imported: {total_imported}")
        print(f"  Duplicates skipped:        {total_dupes}")
        print(f"  Statements before cutoff:  {total_skipped}")


if __name__ == "__main__":
    min_date = "2025-09"
    for arg in sys.argv[1:]:
        if arg.startswith("--min-date"):
            if "=" in arg:
                min_date = arg.split("=", 1)[1]
            else:
                idx = sys.argv.index(arg)
                if idx + 1 < len(sys.argv):
                    min_date = sys.argv[idx + 1]

    print(f"Batch importing Chase statements (min date: {min_date})")
    batch_import(min_date)
