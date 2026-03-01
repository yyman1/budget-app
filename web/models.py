from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()


class CategoryGroup(db.Model):
    __tablename__ = "category_groups"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, default="")
    sort_order = db.Column(db.Integer, default=0)

    categories = db.relationship("Category", back_populates="group", order_by="Category.sort_order")
    group_budgets = db.relationship("GroupBudget", back_populates="group")

    def __repr__(self):
        return f"<CategoryGroup {self.name}>"


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("category_groups.id"), nullable=False)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, default="")
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)

    group = db.relationship("CategoryGroup", back_populates="categories")
    transactions = db.relationship("Transaction", back_populates="category")
    budgets = db.relationship("Budget", back_populates="category")
    merchant_mappings = db.relationship("MerchantMapping", back_populates="category")

    def __repr__(self):
        return f"<Category {self.name}>"


class Account(db.Model):
    __tablename__ = "accounts"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    account_type = db.Column(db.String(20), nullable=False)  # credit_card, bank, loan, other
    institution = db.Column(db.String(100), default="")
    last_four = db.Column(db.String(4), default="")
    is_active = db.Column(db.Boolean, default=True)

    transactions = db.relationship("Transaction", back_populates="account")
    merchant_mappings = db.relationship("MerchantMapping", back_populates="account")

    def __repr__(self):
        return f"<Account {self.name} ({self.institution})>"


class MerchantMapping(db.Model):
    __tablename__ = "merchant_mappings"

    id = db.Column(db.Integer, primary_key=True)
    merchant_name = db.Column(db.String(200), unique=True, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"))
    account_id = db.Column(db.Integer, db.ForeignKey("accounts.id"))
    default_type = db.Column(db.String(10), default="expense")  # income or expense

    category = db.relationship("Category", back_populates="merchant_mappings")
    account = db.relationship("Account", back_populates="merchant_mappings")

    def __repr__(self):
        return f"<MerchantMapping {self.merchant_name} -> {self.category}>"


class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(10), nullable=False)  # YYYY-MM-DD
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(10), nullable=False)  # income or expense
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"))
    account_id = db.Column(db.Integer, db.ForeignKey("accounts.id"))
    merchant = db.Column(db.String(200), default="")
    description = db.Column(db.Text, default="")
    source = db.Column(db.String(20), default="manual")  # manual, google_sheet, statement_import
    source_ref = db.Column(db.String(200), default="")
    created_at = db.Column(db.String(30), default=lambda: datetime.now(timezone.utc).isoformat())

    category = db.relationship("Category", back_populates="transactions")
    account = db.relationship("Account", back_populates="transactions")

    def __repr__(self):
        return f"<Transaction {self.date} {self.type} ${self.amount:.2f}>"


class Budget(db.Model):
    __tablename__ = "budgets"

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    month = db.Column(db.String(7), nullable=False)  # YYYY-MM
    amount_limit = db.Column(db.Float, nullable=False)

    category = db.relationship("Category", back_populates="budgets")

    __table_args__ = (db.UniqueConstraint("category_id", "month"),)

    def __repr__(self):
        return f"<Budget {self.category} {self.month} ${self.amount_limit:.2f}>"


class Obligation(db.Model):
    __tablename__ = "obligations"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    # Comma-separated merchant names to match against transactions
    merchant_pattern = db.Column(db.String(500), default="")
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"))
    expected_amount = db.Column(db.Float)   # None = variable
    amount_min = db.Column(db.Float)
    amount_max = db.Column(db.Float)
    is_fixed = db.Column(db.Boolean, default=False)
    # Seasonal: month_start/month_end (1=Jan, 12=Dec). Default = all year
    month_start = db.Column(db.Integer, default=1)
    month_end = db.Column(db.Integer, default=12)
    section = db.Column(db.String(50), default="variable")  # fixed, variable, credit_card, seasonal
    notes = db.Column(db.Text, default="")
    active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)

    category = db.relationship("Category")

    def __repr__(self):
        return f"<Obligation {self.name}>"


class GroupBudget(db.Model):
    __tablename__ = "group_budgets"

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("category_groups.id"), nullable=False)
    month = db.Column(db.String(7), nullable=False)  # YYYY-MM
    amount_limit = db.Column(db.Float, nullable=False)

    group = db.relationship("CategoryGroup", back_populates="group_budgets")

    __table_args__ = (db.UniqueConstraint("group_id", "month"),)

    def __repr__(self):
        return f"<GroupBudget {self.group} {self.month} ${self.amount_limit:.2f}>"
