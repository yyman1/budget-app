"""Seed monthly obligations and related data gaps.

Usage (from project root):
    python -c "from scripts.seed_obligations import run; run()"

Does:
  1. Add 'Summer Camp' category under Education group
  2. Add 'Hyundai Financial' loan account
  3. Add missing merchant mappings (for bank CSV auto-matching)
  4. Seed all Obligation records (skips any that already exist by name)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web.app import create_app
from web.models import db, Category, CategoryGroup, Account, MerchantMapping, Obligation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_or_create_category(name, group_name, description="", sort_order=99):
    group = CategoryGroup.query.filter_by(name=group_name).first()
    if not group:
        raise ValueError(f"Category group '{group_name}' not found in DB")
    cat = Category.query.filter_by(name=name).first()
    if not cat:
        cat = Category(
            group_id=group.id,
            name=name,
            description=description,
            sort_order=sort_order,
        )
        db.session.add(cat)
        db.session.flush()
        print(f"  Created category: {name}")
    else:
        print(f"  Category exists:  {name}")
    return cat


def _get_or_create_account(name, account_type, institution=""):
    acct = Account.query.filter_by(name=name).first()
    if not acct:
        acct = Account(name=name, account_type=account_type, institution=institution)
        db.session.add(acct)
        db.session.flush()
        print(f"  Created account: {name}")
    else:
        print(f"  Account exists:  {name}")
    return acct


def _add_mapping(merchant_name, category, default_type="expense"):
    if MerchantMapping.query.filter_by(merchant_name=merchant_name).first():
        print(f"  Mapping exists:  {merchant_name}")
        return
    mm = MerchantMapping(
        merchant_name=merchant_name,
        category_id=category.id if category else None,
        default_type=default_type,
    )
    db.session.add(mm)
    print(f"  Added mapping:   {merchant_name} → {category.name if category else 'None'}")


def _add_obligation(name, section, merchant_pattern="", expected_amount=None,
                    category=None, month_start=1, month_end=12, notes="", sort_order=0):
    if Obligation.query.filter_by(name=name).first():
        print(f"  Skipped (exists): {name}")
        return
    ob = Obligation(
        name=name,
        section=section,
        merchant_pattern=merchant_pattern,
        expected_amount=expected_amount,
        category_id=category.id if category else None,
        month_start=month_start,
        month_end=month_end,
        notes=notes,
        sort_order=sort_order,
        is_fixed=bool(expected_amount),
        active=True,
    )
    db.session.add(ob)
    print(f"  Added obligation: [{section}] {name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run():
    app = create_app()
    with app.app_context():
        _seed()


def _seed():
    print("=== seed_obligations.py ===\n")

    # ------------------------------------------------------------------
    # 1. Add Summer Camp category
    # ------------------------------------------------------------------
    print("[1] Categories")
    summer_camp_cat = _get_or_create_category(
        "Summer Camp",
        "Education",
        description="Summer camp expenses (Jun–Aug)",
        sort_order=10,
    )

    # ------------------------------------------------------------------
    # 2. Add Hyundai Financial loan account
    # ------------------------------------------------------------------
    print("\n[2] Accounts")
    _get_or_create_account("Hyundai Financial", "loan", "Hyundai")

    # ------------------------------------------------------------------
    # 3. Missing merchant mappings (bank CSV raw names)
    # ------------------------------------------------------------------
    print("\n[3] Merchant Mappings")
    insurance_cat    = Category.query.filter_by(name="Insurance (MetLife)").first()
    therapy_cat      = Category.query.filter_by(name="Therapy/Personal Care").first()
    transport_cat    = Category.query.filter_by(name="Transportation (Fuel + Misc.)").first()
    cleaning_cat     = Category.query.filter_by(name="Cleaning/Household Help").first()
    loans_cat        = Category.query.filter_by(name="Loans (DCU + Student)").first()

    _add_mapping("ALLSTATE NJ INS", insurance_cat)
    _add_mapping("Rena",            therapy_cat)
    _add_mapping("Yael",            therapy_cat)
    _add_mapping("E-ZPass",         transport_cat)
    _add_mapping("E-Z PASS",        transport_cat)
    _add_mapping("Gardener",        cleaning_cat)
    _add_mapping("Hyundai",         loans_cat)

    # ------------------------------------------------------------------
    # 4. Obligations
    # ------------------------------------------------------------------
    print("\n[4] Obligations")

    # Category lookups
    mortgage_cat      = Category.query.filter_by(name="Mortgage (Wells Fargo)").first()
    tuition_cat       = Category.query.filter_by(name="Tuition").first()
    metlife_cat       = Category.query.filter_by(name="Insurance (MetLife)").first()
    utilities_cat     = Category.query.filter_by(name="Utilities (Water + PSEG)").first()
    subscriptions_cat = Category.query.filter_by(name="Subscriptions/Internet/Phone").first()
    cc_cat            = Category.query.filter_by(name="Credit Card and Retail").first()
    vacation_cat      = Category.query.filter_by(name="Vacation").first()
    # Israel (Abigail) — category ID 16, added post-seed
    israel_cat        = Category.query.filter(Category.name.like("%Israel%")).first()

    # --- Fixed ---
    print("\n  -- fixed --")
    _add_obligation("Mortgage",                    "fixed", "Wells Fargo",              3700.00, mortgage_cat,  1, 12, "",                1)
    _add_obligation("Car Loan — DCU/Tesla",        "fixed", "DCU (YYE)",                None,    loans_cat,     1, 12, "",                2)
    _add_obligation("Car Loan — Hyundai/Palisade", "fixed", "Hyundai",                  688.00,  loans_cat,     1, 12, "$1,800 first month (Feb 2026)", 3)
    _add_obligation("Student Loan",                "fixed", "Student Loan, DCU (SL)",   None,    loans_cat,     1, 12, "",                4)
    _add_obligation("Tuition — Noam",              "fixed", "Noam",                     None,    tuition_cat,   1, 12, "",                5)
    _add_obligation("Tuition — Frisch",            "fixed", "Frisch",                   None,    tuition_cat,   1, 12, "",                6)
    _add_obligation("Tuition — Trio",              "fixed", "Trio",                     None,    tuition_cat,   1, 12, "",                7)
    _add_obligation("Life Insurance — MetLife",    "fixed", "Metlife",                  167.97,  metlife_cat,   1, 12, "",                8)

    # --- Variable ---
    print("\n  -- variable --")
    _add_obligation("PSEG",                        "variable", "Pseg, PSEG",                      None, utilities_cat,     1, 12, "",                 1)
    _add_obligation("United Water",                "variable", "Water, United Water",              None, utilities_cat,     1, 12, "",                 2)
    _add_obligation("Allstate (Car + Property)",   "variable", "ALLSTATE",                         None, insurance_cat,     1, 12, "",                 3)
    _add_obligation("Ez-pass",                     "variable", "E-ZPass, E-Z PASS, EZPass",        None, transport_cat,     1, 12, "",                 4)
    _add_obligation("Therapy — Anat J",            "variable", "Anat",                             None, therapy_cat,       1, 12, "",                 5)
    _add_obligation("Therapy — Rena",              "variable", "Rena",                             None, therapy_cat,       1, 12, "",                 6)
    _add_obligation("Therapy — Karen Weiss",       "variable", "Karen",                            None, therapy_cat,       1, 12, "",                 7)
    _add_obligation("Therapy — Yael",              "variable", "Yael",                             None, therapy_cat,       1, 12, "",                 8)
    _add_obligation("T-Mobile",                    "variable", "TMOBILE",                          None, subscriptions_cat, 1, 12, "",                 9)
    _add_obligation("Optimum (Internet)",          "variable", "Optimum",                          None, subscriptions_cat, 1, 12, "",                10)
    _add_obligation("Israel — Abigail",            "variable", "",                                 None, israel_cat,        1, 12, "",                11)

    # --- Credit Cards ---
    print("\n  -- credit_card --")
    _add_obligation("Amazon Card",             "credit_card", "Amazon Card",                      None, cc_cat, 1, 12, "",                  1)
    _add_obligation("Chase Personal Sapphire", "credit_card", "YYE Saphire",                      None, cc_cat, 1, 12, "",                  2)
    _add_obligation("Chase Business Sapphire", "credit_card", "SLK Saphire",                      None, cc_cat, 1, 12, "",                  3)
    _add_obligation("Chase Business Reserve",  "credit_card", "Reserve Biz",                      None, cc_cat, 1, 12, "",                  4)
    _add_obligation("Chase Ink",               "credit_card", "Chase Ink (Sole), Ink (YYESM)",    None, cc_cat, 1, 12, "",                  5)
    _add_obligation("Chase United Card",       "credit_card", "YYE United",                       None, cc_cat, 1, 12, "",                  6)
    _add_obligation("Amex Platinum (YYE)",     "credit_card", "YYE Plat",                         None, cc_cat, 1, 12, "",                  7)
    _add_obligation("Amex Platinum (New)",     "credit_card", "Amex Plat New",                    None, cc_cat, 1, 12, "",                  8)
    _add_obligation("SLK Blue (Amex)",         "credit_card", "SLK Blue",                         None, cc_cat, 1, 12, "",                  9)
    _add_obligation("Nordstrom Card",          "credit_card", "Nordstrom",                        None, cc_cat, 1, 12, "not every month",   10)
    _add_obligation("Capital One Venture Biz", "credit_card", "Capital One",                      None, cc_cat, 1, 12, "not every month",   11)

    # --- Seasonal ---
    print("\n  -- seasonal --")
    _add_obligation("Summer Camp", "seasonal", "Summer Camp, camp", None, summer_camp_cat, 6,  8, "",        1)
    _add_obligation("Vacation",    "seasonal", "",                  None, vacation_cat,    1, 12, "optional", 2)
    _add_obligation("Gardener",    "seasonal", "Gardener, landscap", None, cleaning_cat,   4, 10, "",        3)

    db.session.commit()
    total = Obligation.query.count()
    print(f"\nDone. Total obligations in DB: {total}")


if __name__ == "__main__":
    run()
