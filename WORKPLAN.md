# Budget App Enhancement — Workplan

## Vision
Transform the current Tkinter budget app into a web-based personal finance manager that:
- Imports bill/payment categories from the Google Sheet ("Bill Payment History")
- Supports hierarchical category grouping (groups → categories → transactions)
- Budgets at both group and category level
- Leaves room for future credit card statement (PDF) parsing
- Tracks 3-5 credit card / bank accounts

## Tech Stack
- **Backend**: Flask + SQLAlchemy (SQLite)
- **Frontend**: Jinja2 templates + HTMX (interactive, all-Python, no JS framework)
- **Charts**: Chart.js (lightweight, browser-native)
- **Google Integration**: google-api-python-client (read-only sync from sheet)
- **PDF Parsing (future)**: pdfplumber / tabula-py for major US bank statements

---

## Phase 1: Data Model & Category Hierarchy
**Goal**: Design the new database schema that supports groups, categories, accounts, and transactions.

### New Schema

```sql
-- Category groups (e.g., "Credit Cards", "Housing", "Utilities")
category_groups (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    sort_order INTEGER DEFAULT 0
)

-- Categories belong to a group
categories (
    id INTEGER PRIMARY KEY,
    group_id INTEGER REFERENCES category_groups(id),
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT 1,
    sort_order INTEGER DEFAULT 0
)

-- Accounts (credit cards, bank accounts)
accounts (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,           -- e.g., "YYE Saphire", "Wells Fargo"
    account_type TEXT NOT NULL,   -- 'credit_card', 'bank', 'loan', 'other'
    institution TEXT,             -- e.g., "Chase", "Amex", "Capital One"
    last_four TEXT,               -- optional last 4 digits
    is_active BOOLEAN DEFAULT 1
)

-- Merchant mapping: maps sheet merchant names to categories + accounts
merchant_mappings (
    id INTEGER PRIMARY KEY,
    merchant_name TEXT UNIQUE NOT NULL,  -- as it appears in the sheet
    category_id INTEGER REFERENCES categories(id),
    account_id INTEGER REFERENCES accounts(id),
    default_type TEXT DEFAULT 'expense'  -- 'income' or 'expense'
)

-- Transactions (bill-level from sheet + future transaction-level from statements)
transactions (
    id INTEGER PRIMARY KEY,
    date TEXT NOT NULL,
    amount REAL NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
    category_id INTEGER REFERENCES categories(id),
    account_id INTEGER REFERENCES accounts(id),
    merchant TEXT,
    description TEXT DEFAULT '',
    source TEXT DEFAULT 'manual',  -- 'manual', 'google_sheet', 'statement_import'
    source_ref TEXT,               -- reference to source (sheet row, file name, etc.)
    created_at TEXT DEFAULT (datetime('now'))
)

-- Budgets at category level
budgets (
    id INTEGER PRIMARY KEY,
    category_id INTEGER REFERENCES categories(id),
    month TEXT NOT NULL,          -- 'YYYY-MM'
    amount_limit REAL NOT NULL,
    UNIQUE(category_id, month)
)

-- Budgets at group level
group_budgets (
    id INTEGER PRIMARY KEY,
    group_id INTEGER REFERENCES category_groups(id),
    month TEXT NOT NULL,
    amount_limit REAL NOT NULL,
    UNIQUE(group_id, month)
)
```

### Default Groups & Categories (from Google Sheet)

| Group | Categories | Monthly Budget |
|---|---|---|
| Credit Cards | Credit Card and Retail (Amazon, Nordstrom) | $1,400 |
| Housing | Mortgage (Wells Fargo), Cleaning/Household Help | $3,700 + $720 |
| Utilities | Water + PSEG, Subscriptions/Internet/Phone | $600 + $280 |
| Insurance | MetLife | $168 |
| Loans | DCU + Student Loan | $1,145 |
| Education | Tuition | $5,100 |
| Personal Care | Therapy/Personal Care | $2,500 |
| Food & Dining | Groceries and Essentials, Dining and Entertainment | $1,800 + $850 |
| Giving | Charitable Donations / YM dues | $500 |
| Medical | Medical and Miscellaneous | $400 |
| Transportation | Transportation (Fuel + Misc.) | $300 |
| Savings/Vacation | Vacation | $1,500 |

### Deliverables
- [ ] New SQLAlchemy models
- [ ] Migration script (preserve existing data from old SQLite DB)
- [ ] Seed data: groups, categories, merchant mappings from sheet
- [ ] Unit tests for the data model

---

## Phase 2: Google Sheet Import
**Goal**: One-way sync that pulls bill payment data from the "Bill Payment History" sheet.

### What We Import
1. **From "Cash Flow" sheet**: Categories, budget amounts, descriptions
2. **From "Expense" sheet**: Monthly bill payments (merchant, date, amount) per month
3. **From "Raw Data" sheet**: Flattened transaction history as backup source

### Import Logic
- Parse the side-by-side month columns in the Expense sheet
- Map merchant names to categories via `merchant_mappings` table
- Handle edge cases: "NA", "Bank", "Ink" (paid via another method), missing amounts
- Track import source so we don't duplicate on re-import
- Support incremental import (new months only)

### Deliverables
- [ ] Google Sheets service module (read-only, using existing OAuth credentials)
- [ ] Sheet parser for Expense sheet (handles the multi-month column layout)
- [ ] Import pipeline: parse → map → deduplicate → insert
- [ ] Import status/history tracking
- [ ] Manual trigger from web UI + import log view

---

## Phase 3: Web UI (Flask + HTMX)
**Goal**: Replace Tkinter with a browser-based interface.

### Pages / Views
1. **Dashboard** — Monthly summary, spending by group (pie/bar chart), budget vs actual
2. **Transactions** — Filterable table (by month, category, group, account), add/edit/delete
3. **Budgets** — Set/view budgets at both group and category level, with progress bars
4. **Categories** — Manage groups, categories, and merchant mappings
5. **Accounts** — Manage credit cards and bank accounts
6. **Import** — Trigger Google Sheet sync, view import history
7. **Statements** (future) — Upload and parse credit card PDFs

### UI Approach
- Flask blueprints for each section
- HTMX for dynamic interactions (inline editing, filtering without page reload)
- Clean, responsive layout (CSS framework: Bootstrap 5 or Pico CSS)
- Chart.js for spending visualizations

### Deliverables
- [ ] Flask app structure with blueprints
- [ ] Base template with navigation
- [ ] Dashboard with charts
- [ ] Transaction list with filtering
- [ ] Budget management (group + category level)
- [ ] Category/group management UI
- [ ] Account management UI
- [ ] Google Sheet import trigger UI

---

## Phase 4: Credit Card Statement Parsing (Future)
**Goal**: Parse PDF statements from major US banks to get transaction-level detail.

### Supported Banks (target)
- Chase (Sapphire, Ink, Amazon)
- American Express (Platinum, Blue)
- Capital One
- Nordstrom (TD Bank)

### Approach
- Use pdfplumber to extract tabular data from PDF statements
- Bank-specific parsers (each bank has different PDF formats)
- Auto-categorize transactions based on merchant name matching
- Manual review/categorization for unmatched merchants
- Link statement transactions to the appropriate account

### Deliverables
- [ ] PDF upload interface
- [ ] Parser framework with bank-specific handlers
- [ ] Chase statement parser
- [ ] Amex statement parser
- [ ] Transaction review/categorize workflow
- [ ] Auto-categorization based on merchant history

---

## Build Order
1. **Phase 1** — Data model & category hierarchy (foundation for everything)
2. **Phase 2** — Google Sheet import (populate with real data)
3. **Phase 3** — Web UI (see and interact with the data)
4. **Phase 4** — Statement parsing (add transaction-level detail)

## Google Sheet Reference
- **Sheet ID**: `17KPfSR3rlRaIMAkVkKRBeGmr2QyVFfPl5vUQF-64i_0`
- **Sheet Name**: "Bill Payment History"
- **Key sheets**: Expense (bill payments), Cash Flow (categories + budgets), Raw Data (flat history)
