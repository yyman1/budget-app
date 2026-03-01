from flask import Blueprint, render_template, request, redirect, url_for, flash
from datetime import date
from web.models import db, Transaction, Category, CategoryGroup, Account

transactions_bp = Blueprint("transactions", __name__)


@transactions_bp.route("/")
def list_transactions():
    month = request.args.get("month", date.today().strftime("%Y-%m"))
    group_id = request.args.get("group_id", type=int)
    category_id = request.args.get("category_id", type=int)
    account_id = request.args.get("account_id", type=int)

    sort = request.args.get("sort", "date")
    order = request.args.get("order", "desc")

    query = (
        Transaction.query
        .join(Category, Transaction.category_id == Category.id, isouter=True)
        .join(CategoryGroup, Category.group_id == CategoryGroup.id, isouter=True)
        .join(Account, Transaction.account_id == Account.id, isouter=True)
    )

    if month:
        query = query.filter(Transaction.date.like(f"{month}%"))
    if group_id:
        query = query.filter(CategoryGroup.id == group_id)
    if category_id:
        query = query.filter(Transaction.category_id == category_id)
    if account_id:
        query = query.filter(Transaction.account_id == account_id)

    sort_columns = {
        "date": Transaction.date,
        "merchant": Transaction.merchant,
        "category": Category.name,
        "account": Account.name,
        "type": Transaction.type,
        "amount": Transaction.amount,
        "source": Transaction.source,
    }
    col = sort_columns.get(sort, Transaction.date)
    order_clause = col.asc() if order == "asc" else col.desc()
    transactions = query.order_by(order_clause, Transaction.id.desc()).all()

    groups = CategoryGroup.query.order_by(CategoryGroup.sort_order).all()
    categories = Category.query.filter_by(is_active=True).order_by(Category.name).all()
    accounts = Account.query.filter_by(is_active=True).order_by(Account.name).all()

    return render_template(
        "transactions.html",
        transactions=transactions,
        groups=groups,
        categories=categories,
        accounts=accounts,
        month=month,
        selected_group=group_id,
        selected_category=category_id,
        selected_account=account_id,
        sort=sort,
        order=order,
    )


@transactions_bp.route("/add", methods=["POST"])
def add_transaction():
    txn = Transaction(
        date=request.form["date"],
        amount=float(request.form["amount"]),
        type=request.form["type"],
        category_id=int(request.form["category_id"]) if request.form.get("category_id") else None,
        account_id=int(request.form["account_id"]) if request.form.get("account_id") else None,
        merchant=request.form.get("merchant", ""),
        description=request.form.get("description", ""),
        source="manual",
    )
    db.session.add(txn)
    db.session.commit()
    return redirect(url_for("transactions.list_transactions", month=txn.date[:7]))


@transactions_bp.route("/<int:txn_id>/edit-row", methods=["GET"])
def edit_row(txn_id):
    """Return an inline edit form row via HTMX."""
    txn = Transaction.query.get_or_404(txn_id)
    categories = Category.query.filter_by(is_active=True).order_by(Category.name).all()
    accounts = Account.query.filter_by(is_active=True).order_by(Account.name).all()
    return render_template(
        "partials/txn_edit_row.html",
        txn=txn,
        categories=categories,
        accounts=accounts,
    )


@transactions_bp.route("/<int:txn_id>/display-row", methods=["GET"])
def display_row(txn_id):
    """Return the normal display row via HTMX (cancel edit)."""
    txn = Transaction.query.get_or_404(txn_id)
    return render_template("partials/txn_display_row.html", txn=txn)


@transactions_bp.route("/<int:txn_id>/update", methods=["POST"])
def update_transaction(txn_id):
    """Save edits and return the display row via HTMX."""
    txn = Transaction.query.get_or_404(txn_id)
    txn.date = request.form["date"]
    txn.amount = float(request.form["amount"])
    txn.type = request.form["type"]
    txn.category_id = int(request.form["category_id"]) if request.form.get("category_id") else None
    txn.account_id = int(request.form["account_id"]) if request.form.get("account_id") else None
    txn.merchant = request.form.get("merchant", "")
    db.session.commit()
    return render_template("partials/txn_display_row.html", txn=txn)


@transactions_bp.route("/<int:txn_id>/delete", methods=["POST"])
def delete_transaction(txn_id):
    txn = Transaction.query.get_or_404(txn_id)
    month = txn.date[:7]
    db.session.delete(txn)
    db.session.commit()
    return redirect(url_for("transactions.list_transactions", month=month))
