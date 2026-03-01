# Session Handover — Budget App

## Current State (Feb 18, 2026)

### What's Done

| Phase | Status | Description |
|---|---|---|
| Phase 1 | DONE | Data model, seed data, Flask app with 6 pages |
| Phase 2 | DONE | Google Sheet import (preview/review/commit, dedup, inline mapping) |
| CC Transfers | DONE | CC bill payments from Google Sheet marked as `type='transfer'` |
| Statement Import | DONE | Chase PDF statements from Google Drive (batch folder import) |
| Bank CSV Import | DONE | Chase checking CSV parser, staging/commit pipeline, UI, 317 transactions loaded |
| Overlap Migration | DONE | 54 Google Sheet expense entries for Sep 2025+ marked as transfers |
| Income Categories | DONE | Salary/Payroll, Reimbursements, Misc Income categories created |
| Merchant Review | DONE | All 81 bank CSV mappings reviewed and corrected |
| UX Polish | DONE | Inter font, comma-formatted $, refined CSS, renamed to "Erlichman Household Budget" |
| Dashboard Trends | DONE | 6-month bar+line chart (income, expenses, net) |
| Edit Transactions | DONE | Inline HTMX edit rows (pencil icon → edit → save/cancel) |
| Sort Transactions | DONE | Clickable column headers with asc/desc toggle + arrow indicators |

### Database Counts
- `google_sheet`: 332 transactions (54 marked as transfer for Sep 2025+ overlap)
- `statement_import`: 349 transactions
- `bank_csv`: 317 transactions (143 income, 169 expense, 5 brokerage transfers)
- **Total: ~998 transactions**

### Categories
- 1=Mortgage, 2=Cleaning, 3=Utilities, 4=Subscriptions, 5=Insurance, 6=Loans, 7=Tuition
- 8=CC+Retail, 9=Groceries, 10=Dining, 11=Therapy, 12=Charitable, 13=Medical
- 14=Transportation, 15=Vacation, 16=Israel(Abigail)
- 18=Salary/Payroll, 19=Reimbursements, 20=Misc Income
- 21=Taxes, 22=Events/Simchas

---

## What's Next — Phase 3 Remaining

- [ ] Inline budget editing (HTMX)
- [ ] Budget copy across months improvement
- [ ] Any additional UI polish

## Phase 4: PDF Statement Parsing
- Chase PDF parser works (done in statement import step)
- Still need: Amex, Capital One, Nordstrom parsers

---

## Key Files

```
budget_app/
├── run_web.py                          # Flask entry point (port 5001)
├── budget_v2.db                        # SQLite database (~998 transactions)
├── Chase2745_Activity_20260216.CSV     # Personal checking CSV (307 rows)
├── Chase6227_Activity_20260216.CSV     # Primary/joint checking CSV (809 rows)
├── credentials.json                    # Google OAuth client credentials
├── token.json                          # Google OAuth token
├── WORKPLAN.md                         # Full 4-phase plan
├── HANDOVER.md                         # This file
│
├── web/
│   ├── app.py                          # Flask app factory + |money filter
│   ├── config.py                       # Config (DB, Google Sheet ID, Drive folders, card overrides)
│   ├── models.py                       # SQLAlchemy models (7 tables)
│   ├── seed.py                         # Seed data (12 groups, 22 categories, 22 accounts, 81+ mappings)
│   │
│   ├── services/
│   │   ├── bank_csv_parser.py          # Chase bank CSV parser + merchant extraction
│   │   ├── import_pipeline.py          # Sheet + statement + bank CSV stage/commit/history
│   │   ├── sheet_service.py            # Google Sheets API
│   │   ├── sheet_parser.py             # Google Sheet side-by-side month parser
│   │   ├── drive_service.py            # Google Drive API (list/download PDFs)
│   │   └── chase_parser.py             # Chase CC PDF statement parser
│   │
│   ├── routes/
│   │   ├── imports.py                  # All import routes (sheet, statement, bank CSV, overlap migration)
│   │   ├── dashboard.py                # Dashboard with month nav + 6-month trend chart
│   │   ├── transactions.py             # Transaction CRUD + inline edit + sort
│   │   ├── budgets.py                  # Budget management
│   │   ├── categories.py               # Category/group management
│   │   └── accounts.py                 # Account management
│   │
│   └── templates/
│       ├── base.html                   # Layout with Inter font, polished CSS
│       ├── imports.html                # Sheet + statement + bank CSV import + migration
│       ├── dashboard.html              # Monthly summary + doughnut + trend chart
│       ├── transactions.html           # Sortable table with inline edit
│       ├── partials/
│       │   ├── txn_display_row.html    # Normal transaction row (HTMX partial)
│       │   └── txn_edit_row.html       # Inline edit form row (HTMX partial)
│       └── ...                         # budgets, categories, accounts, mappings
```

## Gotchas
- macOS port 5000 = AirPlay. Use 5001+
- pip needs `--break-system-packages` on macOS
- Python path: `/opt/homebrew/bin/python3.13`
- Sheet merchant names have typos ("Saphire" not "Sapphire") — match exact
- Don't store parsed records in Flask session — cookie too large. Use temp files
- Bank CSV uses `utf-8-sig` encoding (BOM)
- Stripe source refs include invoice numbers making each unique — 12 separate Stripe mappings exist
- The overlap migration is a one-way operation — no undo
- Transaction sort preserves all filter params in the URL
