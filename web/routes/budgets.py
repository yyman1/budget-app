from flask import Blueprint, render_template, request, redirect, url_for
from datetime import date
from web.models import db, Budget, GroupBudget, Category, CategoryGroup
from sqlalchemy import func

budgets_bp = Blueprint("budgets", __name__)


@budgets_bp.route("/")
def list_budgets():
    month = request.args.get("month", date.today().strftime("%Y-%m"))

    # Category-level budgets with group info
    cat_budgets = (
        db.session.query(Budget, Category, CategoryGroup)
        .join(Category, Budget.category_id == Category.id)
        .join(CategoryGroup, Category.group_id == CategoryGroup.id)
        .filter(Budget.month == month)
        .order_by(CategoryGroup.sort_order, Category.sort_order)
        .all()
    )

    # Group-level budgets
    grp_budgets = (
        db.session.query(GroupBudget, CategoryGroup)
        .join(CategoryGroup, GroupBudget.group_id == CategoryGroup.id)
        .filter(GroupBudget.month == month)
        .order_by(CategoryGroup.sort_order)
        .all()
    )

    groups = CategoryGroup.query.order_by(CategoryGroup.sort_order).all()
    categories = Category.query.filter_by(is_active=True).order_by(Category.name).all()

    return render_template(
        "budgets.html",
        month=month,
        cat_budgets=cat_budgets,
        grp_budgets=grp_budgets,
        groups=groups,
        categories=categories,
    )


@budgets_bp.route("/set", methods=["POST"])
def set_budget():
    month = request.form["month"]
    level = request.form["level"]  # "category" or "group"

    if level == "category":
        category_id = int(request.form["category_id"])
        amount = float(request.form["amount"])
        existing = Budget.query.filter_by(category_id=category_id, month=month).first()
        if existing:
            existing.amount_limit = amount
        else:
            db.session.add(Budget(category_id=category_id, month=month, amount_limit=amount))
    else:
        group_id = int(request.form["group_id"])
        amount = float(request.form["amount"])
        existing = GroupBudget.query.filter_by(group_id=group_id, month=month).first()
        if existing:
            existing.amount_limit = amount
        else:
            db.session.add(GroupBudget(group_id=group_id, month=month, amount_limit=amount))

    db.session.commit()
    return redirect(url_for("budgets.list_budgets", month=month))


@budgets_bp.route("/copy", methods=["POST"])
def copy_budgets():
    """Copy all budgets from one month to another."""
    from_month = request.form["from_month"]
    to_month = request.form["to_month"]

    # Copy category budgets
    for b in Budget.query.filter_by(month=from_month).all():
        existing = Budget.query.filter_by(category_id=b.category_id, month=to_month).first()
        if not existing:
            db.session.add(Budget(category_id=b.category_id, month=to_month, amount_limit=b.amount_limit))

    # Copy group budgets
    for gb in GroupBudget.query.filter_by(month=from_month).all():
        existing = GroupBudget.query.filter_by(group_id=gb.group_id, month=to_month).first()
        if not existing:
            db.session.add(GroupBudget(group_id=gb.group_id, month=to_month, amount_limit=gb.amount_limit))

    db.session.commit()
    return redirect(url_for("budgets.list_budgets", month=to_month))
