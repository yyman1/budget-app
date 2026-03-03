from flask import Blueprint, render_template, request, redirect, url_for, flash
from datetime import date
from web.models import db, Obligation, Transaction, Category

obligations_bp = Blueprint("obligations", __name__)


def _match_transactions(obligation, month):
    """Return all transactions in `month` that match this obligation."""
    patterns = [p.strip() for p in (obligation.merchant_pattern or "").split(",") if p.strip()]

    # Category fallback: no pattern → match all expense txns in that category
    if not patterns and obligation.category_id:
        return Transaction.query.filter(
            Transaction.date.like(f"{month}-%"),
            Transaction.category_id == obligation.category_id,
            Transaction.type == "expense",
        ).all()

    if not patterns:
        return []

    # ILIKE substring match — handles raw bank CSV names like "ALLSTATE NJ INS", "TMOBILE*AUTO PAY..."
    return Transaction.query.filter(
        Transaction.date.like(f"{month}-%"),
        db.or_(*[Transaction.merchant.ilike(f"%{p}%") for p in patterns]),
    ).all()


def _in_season(obligation, month_num):
    start = obligation.month_start or 1
    end = obligation.month_end or 12
    if start <= end:
        return start <= month_num <= end
    # Wraps around year (e.g. Nov–Feb)
    return month_num >= start or month_num <= end


@obligations_bp.route("/")
def list_obligations():
    month = request.args.get("month", date.today().strftime("%Y-%m"))
    month_num = int(month.split("-")[1])

    obligations = Obligation.query.filter_by(active=True).order_by(
        Obligation.section, Obligation.sort_order, Obligation.name
    ).all()

    items = []
    met = 0
    total_in_season = 0

    for ob in obligations:
        in_season = _in_season(ob, month_num)
        txns = _match_transactions(ob, month) if in_season else []
        actual = sum(t.amount for t in txns)

        if in_season:
            total_in_season += 1
            if txns:
                met += 1

        items.append({
            "obligation": ob,
            "in_season": in_season,
            "txns": txns,
            "actual": actual,
            "found": bool(txns),
        })

    # Group by section
    sections = {}
    section_order = ["fixed", "variable", "credit_card", "seasonal"]
    section_labels = {
        "fixed": "Fixed Monthly",
        "variable": "Variable / Recurring",
        "credit_card": "Credit Card Payments",
        "seasonal": "Seasonal",
    }
    for key in section_order:
        sections[key] = [i for i in items if i["obligation"].section == key]

    return render_template(
        "obligations.html",
        month=month,
        sections=sections,
        section_labels=section_labels,
        section_order=section_order,
        met=met,
        total=total_in_season,
    )


@obligations_bp.route("/add", methods=["POST"])
def add_obligation():
    month = request.form.get("month", date.today().strftime("%Y-%m"))
    ob = Obligation(
        name=request.form["name"],
        merchant_pattern=request.form.get("merchant_pattern", ""),
        expected_amount=float(request.form["expected_amount"]) if request.form.get("expected_amount") else None,
        amount_min=float(request.form["amount_min"]) if request.form.get("amount_min") else None,
        amount_max=float(request.form["amount_max"]) if request.form.get("amount_max") else None,
        is_fixed=request.form.get("is_fixed") == "1",
        month_start=int(request.form.get("month_start", 1)),
        month_end=int(request.form.get("month_end", 12)),
        section=request.form.get("section", "variable"),
        notes=request.form.get("notes", ""),
        sort_order=int(request.form.get("sort_order", 0)),
    )
    db.session.add(ob)
    db.session.commit()
    flash(f'Added obligation "{ob.name}"', "success")
    return redirect(url_for("obligations.list_obligations", month=month))


@obligations_bp.route("/<int:ob_id>/delete", methods=["POST"])
def delete_obligation(ob_id):
    month = request.form.get("month", date.today().strftime("%Y-%m"))
    ob = Obligation.query.get_or_404(ob_id)
    db.session.delete(ob)
    db.session.commit()
    flash(f'Deleted "{ob.name}"', "success")
    return redirect(url_for("obligations.list_obligations", month=month))
