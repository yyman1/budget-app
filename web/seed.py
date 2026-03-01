"""Seed the database with category groups, categories, accounts, and merchant mappings
derived from the Google Sheet 'Bill Payment History'."""

from web.models import db, CategoryGroup, Category, Account, MerchantMapping, Budget


# ---------- Groups & Categories ----------

SEED_DATA = {
    "Housing": {
        "description": "Mortgage and home-related expenses",
        "sort_order": 1,
        "categories": [
            {"name": "Mortgage (Wells Fargo)", "description": "Fixed monthly housing payment", "budget": 3700.00},
            {"name": "Cleaning/Household Help", "description": "Regular home cleaning services", "budget": 720.00},
        ],
    },
    "Utilities": {
        "description": "Water, electric, internet, phone",
        "sort_order": 2,
        "categories": [
            {"name": "Utilities (Water + PSEG)", "description": "Combined utility and water bills", "budget": 600.00},
            {"name": "Subscriptions/Internet/Phone", "description": "Optimum and Chase Ink phone plan", "budget": 280.00},
        ],
    },
    "Insurance": {
        "description": "Insurance premiums",
        "sort_order": 3,
        "categories": [
            {"name": "Insurance (MetLife)", "description": "Life or home insurance premium", "budget": 167.97},
        ],
    },
    "Loans": {
        "description": "Loan payments",
        "sort_order": 4,
        "categories": [
            {"name": "Loans (DCU + Student)", "description": "DCU auto/personal loan + student loan", "budget": 1145.00},
        ],
    },
    "Education": {
        "description": "Tuition and education expenses",
        "sort_order": 5,
        "categories": [
            {"name": "Tuition", "description": "Combined education payments for children", "budget": 5100.00},
        ],
    },
    "Credit Cards & Retail": {
        "description": "Credit card payments and retail purchases",
        "sort_order": 6,
        "categories": [
            {"name": "Credit Card and Retail", "description": "Ongoing discretionary purchases (Amazon, Nordstrom, etc.)", "budget": 1400.00},
        ],
    },
    "Food & Dining": {
        "description": "Groceries, restaurants, and dining",
        "sort_order": 7,
        "categories": [
            {"name": "Groceries and Essentials", "description": "Card charges and Amazon orders", "budget": 1800.00},
            {"name": "Dining and Entertainment", "description": "Restaurants, outings, events", "budget": 850.00},
        ],
    },
    "Personal Care": {
        "description": "Therapy and personal care",
        "sort_order": 8,
        "categories": [
            {"name": "Therapy/Personal Care", "description": "$1,500 therapy + $1,000 Avigayil", "budget": 2500.00},
        ],
    },
    "Giving": {
        "description": "Charitable giving and memberships",
        "sort_order": 9,
        "categories": [
            {"name": "Charitable Donations / YM dues", "description": "Regular contributions", "budget": 500.00},
        ],
    },
    "Medical": {
        "description": "Healthcare and medical expenses",
        "sort_order": 10,
        "categories": [
            {"name": "Medical and Miscellaneous", "description": "Co-pays, prescriptions, unplanned needs", "budget": 400.00},
        ],
    },
    "Transportation": {
        "description": "Fuel and vehicle expenses",
        "sort_order": 11,
        "categories": [
            {"name": "Transportation (Fuel + Misc.)", "description": "Fuel and small car expenses", "budget": 300.00},
        ],
    },
    "Savings & Vacation": {
        "description": "Savings goals and vacation fund",
        "sort_order": 12,
        "categories": [
            {"name": "Vacation", "description": "Emergency, event, or tax fund deposits", "budget": 1500.00},
        ],
    },
}


# ---------- Accounts (from sheet merchant list) ----------

SEED_ACCOUNTS = [
    # Credit Cards
    {"name": "YYE Sapphire", "account_type": "credit_card", "institution": "Chase"},
    {"name": "SLK Sapphire", "account_type": "credit_card", "institution": "Chase"},
    {"name": "SLK Blue", "account_type": "credit_card", "institution": "Amex"},
    {"name": "Reserve Biz", "account_type": "credit_card", "institution": "Chase"},
    {"name": "YYE Plat", "account_type": "credit_card", "institution": "Amex"},
    {"name": "YYE United", "account_type": "credit_card", "institution": "Chase"},
    {"name": "Amazon Card", "account_type": "credit_card", "institution": "Chase"},
    {"name": "Capital One", "account_type": "credit_card", "institution": "Capital One"},
    {"name": "Amex Plat New", "account_type": "credit_card", "institution": "Amex"},
    {"name": "Nordstrom", "account_type": "credit_card", "institution": "TD Bank"},
    {"name": "Chase Ink (Sole)", "account_type": "credit_card", "institution": "Chase"},
    {"name": "Ink (YYESM)", "account_type": "credit_card", "institution": "Chase"},
    {"name": "Ink (Old)", "account_type": "credit_card", "institution": "Chase"},
    {"name": "Ink YYESM LLC", "account_type": "credit_card", "institution": "Chase"},
    {"name": "Ink Teaneck 0272", "account_type": "credit_card", "institution": "Chase"},
    {"name": "Ink Teaneck 5107", "account_type": "credit_card", "institution": "Chase"},
    # Bank / Mortgage
    {"name": "Wells Fargo", "account_type": "bank", "institution": "Wells Fargo"},
    {"name": "Chase Checking (2745)", "account_type": "bank", "institution": "Chase", "last_four": "2745"},
    {"name": "Chase Checking (6227)", "account_type": "bank", "institution": "Chase", "last_four": "6227"},
    # Loans
    {"name": "DCU (YYE)", "account_type": "loan", "institution": "DCU"},
    {"name": "DCU (SL)", "account_type": "loan", "institution": "DCU"},
    {"name": "Student Loan", "account_type": "loan", "institution": ""},
]


# ---------- Merchant → Category + Account Mappings ----------
# Maps the exact merchant names from the Google Sheet to categories and accounts

SEED_MERCHANT_MAPPINGS = [
    # Housing
    {"merchant_name": "Wells Fargo", "category": "Mortgage (Wells Fargo)", "account": "Wells Fargo"},
    {"merchant_name": "Cleaning", "category": "Cleaning/Household Help", "account": None},
    # Utilities
    {"merchant_name": "Water", "category": "Utilities (Water + PSEG)", "account": None},
    {"merchant_name": "Pseg", "category": "Utilities (Water + PSEG)", "account": None},
    {"merchant_name": "Optimum", "category": "Subscriptions/Internet/Phone", "account": None},
    # Insurance
    {"merchant_name": "Metlife", "category": "Insurance (MetLife)", "account": None},
    # Loans
    {"merchant_name": "DCU (YYE)", "category": "Loans (DCU + Student)", "account": "DCU (YYE)"},
    {"merchant_name": "DCU (SL)", "category": "Loans (DCU + Student)", "account": "DCU (SL)"},
    {"merchant_name": "Student Loan", "category": "Loans (DCU + Student)", "account": "Student Loan"},
    # Education
    {"merchant_name": "Tuiton", "category": "Tuition", "account": None},
    # Credit Cards (these are bill payments — the card itself is the account)
    {"merchant_name": "YYE Saphire", "category": "Credit Card and Retail", "account": "YYE Sapphire"},
    {"merchant_name": "SLK Saphire", "category": "Credit Card and Retail", "account": "SLK Sapphire"},
    {"merchant_name": "SLK Blue", "category": "Credit Card and Retail", "account": "SLK Blue"},
    {"merchant_name": "Reserve Biz", "category": "Credit Card and Retail", "account": "Reserve Biz"},
    {"merchant_name": "YYE Plat", "category": "Credit Card and Retail", "account": "YYE Plat"},
    {"merchant_name": "YYE United", "category": "Credit Card and Retail", "account": "YYE United"},
    {"merchant_name": "Amazon Card", "category": "Credit Card and Retail", "account": "Amazon Card"},
    {"merchant_name": "Capital One", "category": "Credit Card and Retail", "account": "Capital One"},
    {"merchant_name": "Amex Plat New", "category": "Credit Card and Retail", "account": "Amex Plat New"},
    {"merchant_name": "Nordstrom", "category": "Credit Card and Retail", "account": "Nordstrom"},
    {"merchant_name": "Chase Ink (Sole)", "category": "Subscriptions/Internet/Phone", "account": "Chase Ink (Sole)"},
    {"merchant_name": "Ink (YYESM)", "category": "Credit Card and Retail", "account": "Ink (YYESM)"},
    {"merchant_name": "Ink (Old)", "category": "Credit Card and Retail", "account": "Ink (Old)"},
    {"merchant_name": "Ink YYESM LLC", "category": "Credit Card and Retail", "account": "Ink YYESM LLC"},
    {"merchant_name": "Ink Teaneck 0272", "category": "Credit Card and Retail", "account": "Ink Teaneck 0272"},
    {"merchant_name": "Ink Teaneck 5107", "category": "Credit Card and Retail", "account": "Ink Teaneck 5107"},
    # Personal
    {"merchant_name": "Monthly Therapy", "category": "Therapy/Personal Care", "account": None},
    {"merchant_name": "Y/M", "category": "Charitable Donations / YM dues", "account": None},
]


def seed_database():
    """Populate the database with initial groups, categories, accounts, and mappings."""

    # 1. Create groups and categories
    category_lookup = {}  # name -> Category object
    for group_name, group_data in SEED_DATA.items():
        group = CategoryGroup(
            name=group_name,
            description=group_data["description"],
            sort_order=group_data["sort_order"],
        )
        db.session.add(group)
        db.session.flush()  # get the group.id

        for i, cat_data in enumerate(group_data["categories"]):
            cat = Category(
                group_id=group.id,
                name=cat_data["name"],
                description=cat_data.get("description", ""),
                sort_order=i,
            )
            db.session.add(cat)
            db.session.flush()
            category_lookup[cat.name] = cat

    # 2. Create accounts
    account_lookup = {}  # name -> Account object
    for acct_data in SEED_ACCOUNTS:
        acct = Account(**acct_data)
        db.session.add(acct)
        db.session.flush()
        account_lookup[acct.name] = acct

    # 3. Create merchant mappings
    for mapping in SEED_MERCHANT_MAPPINGS:
        cat = category_lookup.get(mapping["category"])
        acct = account_lookup.get(mapping["account"]) if mapping["account"] else None
        mm = MerchantMapping(
            merchant_name=mapping["merchant_name"],
            category_id=cat.id if cat else None,
            account_id=acct.id if acct else None,
            default_type="expense",
        )
        db.session.add(mm)

    # 4. Seed default budgets for the current month
    from datetime import date
    current_month = date.today().strftime("%Y-%m")
    for group_data in SEED_DATA.values():
        for cat_data in group_data["categories"]:
            cat = category_lookup.get(cat_data["name"])
            if cat and cat_data.get("budget"):
                budget = Budget(
                    category_id=cat.id,
                    month=current_month,
                    amount_limit=cat_data["budget"],
                )
                db.session.add(budget)

    db.session.commit()
    print(f"Seeded: {len(SEED_DATA)} groups, {len(category_lookup)} categories, "
          f"{len(account_lookup)} accounts, {len(SEED_MERCHANT_MAPPINGS)} merchant mappings, "
          f"{len(category_lookup)} budgets for {current_month}")
