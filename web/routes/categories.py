from flask import Blueprint, render_template, request, redirect, url_for
from web.models import db, Category, CategoryGroup, MerchantMapping

categories_bp = Blueprint("categories", __name__)


@categories_bp.route("/")
def list_categories():
    groups = (
        CategoryGroup.query
        .order_by(CategoryGroup.sort_order)
        .all()
    )
    return render_template("categories.html", groups=groups)


@categories_bp.route("/groups/add", methods=["POST"])
def add_group():
    max_order = db.session.query(db.func.max(CategoryGroup.sort_order)).scalar() or 0
    group = CategoryGroup(
        name=request.form["name"],
        description=request.form.get("description", ""),
        sort_order=max_order + 1,
    )
    db.session.add(group)
    db.session.commit()
    return redirect(url_for("categories.list_categories"))


@categories_bp.route("/add", methods=["POST"])
def add_category():
    max_order = (
        db.session.query(db.func.max(Category.sort_order))
        .filter_by(group_id=int(request.form["group_id"]))
        .scalar() or 0
    )
    cat = Category(
        group_id=int(request.form["group_id"]),
        name=request.form["name"],
        description=request.form.get("description", ""),
        sort_order=max_order + 1,
    )
    db.session.add(cat)
    db.session.commit()
    return redirect(url_for("categories.list_categories"))


@categories_bp.route("/mappings")
def list_mappings():
    mappings = (
        MerchantMapping.query
        .order_by(MerchantMapping.merchant_name)
        .all()
    )
    categories = Category.query.filter_by(is_active=True).order_by(Category.name).all()
    from web.models import Account
    accounts = Account.query.filter_by(is_active=True).order_by(Account.name).all()
    return render_template("mappings.html", mappings=mappings, categories=categories, accounts=accounts)


@categories_bp.route("/mappings/add", methods=["POST"])
def add_mapping():
    mm = MerchantMapping(
        merchant_name=request.form["merchant_name"],
        category_id=int(request.form["category_id"]) if request.form.get("category_id") else None,
        account_id=int(request.form["account_id"]) if request.form.get("account_id") else None,
        default_type=request.form.get("default_type", "expense"),
    )
    db.session.add(mm)
    db.session.commit()
    return redirect(url_for("categories.list_mappings"))
