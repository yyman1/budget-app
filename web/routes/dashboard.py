from flask import Blueprint, render_template, request
from datetime import date, timedelta
from web.models import db, Transaction, Category, CategoryGroup, Budget, GroupBudget
from sqlalchemy import func

dashboard_bp = Blueprint("dashboard", __name__)


def _prev_month(ym):
    """Given 'YYYY-MM', return the previous month string."""
    y, m = int(ym[:4]), int(ym[5:7])
    if m == 1:
        return f"{y-1:04d}-12"
    return f"{y:04d}-{m-1:02d}"


def _next_month(ym):
    """Given 'YYYY-MM', return the next month string."""
    y, m = int(ym[:4]), int(ym[5:7])
    if m == 12:
        return f"{y+1:04d}-01"
    return f"{y:04d}-{m+1:02d}"


@dashboard_bp.route("/")
def index():
    current_month = request.args.get("month", date.today().strftime("%Y-%m"))

    # Monthly totals
    income = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.type == "income",
        Transaction.date.like(f"{current_month}%"),
    ).scalar()

    expenses = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.type == "expense",
        Transaction.date.like(f"{current_month}%"),
    ).scalar()

    # Transfer totals
    transfers = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.type == "transfer",
        Transaction.date.like(f"{current_month}%"),
    ).scalar()

    # Spending by group
    group_spending = (
        db.session.query(CategoryGroup.name, func.sum(Transaction.amount))
        .join(Category, Category.group_id == CategoryGroup.id)
        .join(Transaction, Transaction.category_id == Category.id)
        .filter(Transaction.type == "expense", Transaction.date.like(f"{current_month}%"))
        .group_by(CategoryGroup.name)
        .order_by(func.sum(Transaction.amount).desc())
        .all()
    )

    # Budget vs actual by category
    budgets = (
        db.session.query(
            Category.name,
            CategoryGroup.name.label("group_name"),
            Budget.amount_limit,
            func.coalesce(func.sum(Transaction.amount), 0).label("spent"),
        )
        .join(CategoryGroup, Category.group_id == CategoryGroup.id)
        .join(Budget, Budget.category_id == Category.id)
        .outerjoin(
            Transaction,
            db.and_(
                Transaction.category_id == Category.id,
                Transaction.type == "expense",
                Transaction.date.like(f"{current_month}%"),
            ),
        )
        .filter(Budget.month == current_month)
        .group_by(Category.id, Budget.id)
        .order_by(CategoryGroup.sort_order, Category.sort_order)
        .all()
    )

    # 6-month trend data
    trend_months = []
    m = current_month
    for _ in range(6):
        trend_months.append(m)
        m = _prev_month(m)
    trend_months.reverse()

    trend_income = []
    trend_expenses = []
    for tm in trend_months:
        ti = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
            Transaction.type == "income", Transaction.date.like(f"{tm}%")
        ).scalar()
        te = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
            Transaction.type == "expense", Transaction.date.like(f"{tm}%")
        ).scalar()
        trend_income.append(round(ti, 2))
        trend_expenses.append(round(te, 2))

    return render_template(
        "dashboard.html",
        month=current_month,
        prev_month=_prev_month(current_month),
        next_month=_next_month(current_month),
        income=income,
        expenses=expenses,
        transfers=transfers,
        net=income - expenses,
        group_spending=group_spending,
        budgets=budgets,
        trend_months=trend_months,
        trend_income=trend_income,
        trend_expenses=trend_expenses,
    )
