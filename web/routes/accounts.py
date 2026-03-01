from flask import Blueprint, render_template, request, redirect, url_for
from web.models import db, Account

accounts_bp = Blueprint("accounts", __name__)


@accounts_bp.route("/")
def list_accounts():
    accounts = Account.query.order_by(Account.institution, Account.name).all()
    return render_template("accounts.html", accounts=accounts)


@accounts_bp.route("/add", methods=["POST"])
def add_account():
    acct = Account(
        name=request.form["name"],
        account_type=request.form["account_type"],
        institution=request.form.get("institution", ""),
        last_four=request.form.get("last_four", ""),
    )
    db.session.add(acct)
    db.session.commit()
    return redirect(url_for("accounts.list_accounts"))


@accounts_bp.route("/<int:acct_id>/toggle", methods=["POST"])
def toggle_account(acct_id):
    acct = Account.query.get_or_404(acct_id)
    acct.is_active = not acct.is_active
    db.session.commit()
    return redirect(url_for("accounts.list_accounts"))
