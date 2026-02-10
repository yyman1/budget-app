from __future__ import annotations
import sqlite3
import os
from models import Transaction, Budget, CategorySpending, MonthlySummary
from constants import DB_NAME, EXPENSE_CATEGORIES


class Database:
    def __init__(self, db_path: str | None = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), DB_NAME)
        self.db_path = db_path
        self._create_tables()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _create_tables(self):
        conn = self._connect()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
                category TEXT NOT NULL,
                description TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                month TEXT NOT NULL,
                amount_limit REAL NOT NULL,
                UNIQUE(category, month)
            );
        """)
        conn.commit()
        conn.close()

    # --- Transactions ---

    def add_transaction(self, txn: Transaction) -> int:
        conn = self._connect()
        cur = conn.execute(
            "INSERT INTO transactions (date, amount, type, category, description) VALUES (?, ?, ?, ?, ?)",
            (txn.date, txn.amount, txn.type, txn.category, txn.description),
        )
        conn.commit()
        txn_id = cur.lastrowid
        conn.close()
        return txn_id

    def update_transaction(self, txn: Transaction):
        conn = self._connect()
        conn.execute(
            "UPDATE transactions SET date=?, amount=?, type=?, category=?, description=? WHERE id=?",
            (txn.date, txn.amount, txn.type, txn.category, txn.description, txn.id),
        )
        conn.commit()
        conn.close()

    def delete_transaction(self, txn_id: int):
        conn = self._connect()
        conn.execute("DELETE FROM transactions WHERE id=?", (txn_id,))
        conn.commit()
        conn.close()

    def get_transactions(
        self, month: str | None = None, category: str | None = None, txn_type: str | None = None
    ) -> list[Transaction]:
        conn = self._connect()
        query = "SELECT * FROM transactions WHERE 1=1"
        params = []
        if month:
            query += " AND strftime('%Y-%m', date) = ?"
            params.append(month)
        if category:
            query += " AND category = ?"
            params.append(category)
        if txn_type:
            query += " AND type = ?"
            params.append(txn_type)
        query += " ORDER BY date DESC, id DESC"
        rows = conn.execute(query, params).fetchall()
        conn.close()
        return [
            Transaction(
                id=r["id"],
                date=r["date"],
                amount=r["amount"],
                type=r["type"],
                category=r["category"],
                description=r["description"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

    # --- Budgets ---

    def set_budget(self, budget: Budget):
        conn = self._connect()
        conn.execute(
            """INSERT INTO budgets (category, month, amount_limit) VALUES (?, ?, ?)
               ON CONFLICT(category, month) DO UPDATE SET amount_limit=excluded.amount_limit""",
            (budget.category, budget.month, budget.amount_limit),
        )
        conn.commit()
        conn.close()

    def get_budgets(self, month: str) -> dict[str, float]:
        conn = self._connect()
        rows = conn.execute(
            "SELECT category, amount_limit FROM budgets WHERE month=?", (month,)
        ).fetchall()
        conn.close()
        return {r["category"]: r["amount_limit"] for r in rows}

    # --- Aggregations ---

    def get_monthly_summary(self, month: str) -> MonthlySummary:
        conn = self._connect()
        row = conn.execute(
            """SELECT
                COALESCE(SUM(CASE WHEN type='income' THEN amount ELSE 0 END), 0) as income,
                COALESCE(SUM(CASE WHEN type='expense' THEN amount ELSE 0 END), 0) as expenses
               FROM transactions WHERE strftime('%Y-%m', date) = ?""",
            (month,),
        ).fetchone()
        conn.close()
        income = row["income"]
        expenses = row["expenses"]
        return MonthlySummary(
            month=month,
            total_income=income,
            total_expenses=expenses,
            net_balance=income - expenses,
        )

    def get_category_spending(self, month: str) -> list[CategorySpending]:
        conn = self._connect()
        rows = conn.execute(
            """SELECT category, SUM(amount) as total
               FROM transactions
               WHERE type='expense' AND strftime('%Y-%m', date) = ?
               GROUP BY category ORDER BY total DESC""",
            (month,),
        ).fetchall()
        conn.close()
        budgets = self.get_budgets(month)
        return [
            CategorySpending(
                category=r["category"],
                total_spent=r["total"],
                budget_limit=budgets.get(r["category"]),
            )
            for r in rows
        ]

    def get_budget_vs_actual(self, month: str) -> list[CategorySpending]:
        """Return all expense categories with budget limits and actual spending."""
        budgets = self.get_budgets(month)
        conn = self._connect()
        rows = conn.execute(
            """SELECT category, SUM(amount) as total
               FROM transactions
               WHERE type='expense' AND strftime('%Y-%m', date) = ?
               GROUP BY category""",
            (month,),
        ).fetchall()
        conn.close()
        spending = {r["category"]: r["total"] for r in rows}
        results = []
        for cat in EXPENSE_CATEGORIES:
            limit = budgets.get(cat)
            spent = spending.get(cat, 0.0)
            if limit or spent > 0:
                results.append(
                    CategorySpending(category=cat, total_spent=spent, budget_limit=limit)
                )
        return results
