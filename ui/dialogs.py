from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox

from constants import EXPENSE_CATEGORIES, INCOME_CATEGORIES
from models import Transaction
from utils import today_str, validate_date, validate_amount


class TransactionDialog(tk.Toplevel):
    """Modal dialog for adding/editing a transaction."""

    def __init__(self, parent, transaction: Transaction | None = None):
        super().__init__(parent)
        self.result: Transaction | None = None
        self.editing = transaction

        self.title("Edit Transaction" if transaction else "Add Transaction")
        self.geometry("400x350")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build_form(transaction)
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.wait_window()

    def _build_form(self, txn: Transaction | None):
        frame = ttk.Frame(self, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        # Date
        ttk.Label(frame, text="Date (YYYY-MM-DD):").grid(row=0, column=0, sticky=tk.W, pady=4)
        self.date_var = tk.StringVar(value=txn.date if txn else today_str())
        ttk.Entry(frame, textvariable=self.date_var, width=20).grid(row=0, column=1, sticky=tk.W, pady=4)

        # Type
        ttk.Label(frame, text="Type:").grid(row=1, column=0, sticky=tk.W, pady=4)
        self.type_var = tk.StringVar(value=txn.type if txn else "expense")
        type_combo = ttk.Combobox(
            frame, textvariable=self.type_var, values=["expense", "income"],
            state="readonly", width=17,
        )
        type_combo.grid(row=1, column=1, sticky=tk.W, pady=4)
        type_combo.bind("<<ComboboxSelected>>", self._on_type_changed)

        # Category
        ttk.Label(frame, text="Category:").grid(row=2, column=0, sticky=tk.W, pady=4)
        self.category_var = tk.StringVar(value=txn.category if txn else "")
        self.category_combo = ttk.Combobox(
            frame, textvariable=self.category_var, state="readonly", width=17,
        )
        self.category_combo.grid(row=2, column=1, sticky=tk.W, pady=4)
        self._update_categories()
        if txn:
            self.category_var.set(txn.category)

        # Amount
        ttk.Label(frame, text="Amount ($):").grid(row=3, column=0, sticky=tk.W, pady=4)
        self.amount_var = tk.StringVar(value=f"{txn.amount:.2f}" if txn else "")
        ttk.Entry(frame, textvariable=self.amount_var, width=20).grid(row=3, column=1, sticky=tk.W, pady=4)

        # Description
        ttk.Label(frame, text="Description:").grid(row=4, column=0, sticky=tk.W, pady=4)
        self.desc_var = tk.StringVar(value=txn.description if txn else "")
        ttk.Entry(frame, textvariable=self.desc_var, width=20).grid(row=4, column=1, sticky=tk.W, pady=4)

        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=16)
        ttk.Button(btn_frame, text="Save", command=self._on_save).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_frame, text="Cancel", command=self._on_cancel).pack(side=tk.LEFT, padx=8)

    def _on_type_changed(self, event=None):
        self._update_categories()
        self.category_var.set("")

    def _update_categories(self):
        if self.type_var.get() == "income":
            self.category_combo["values"] = INCOME_CATEGORIES
        else:
            self.category_combo["values"] = EXPENSE_CATEGORIES

    def _on_save(self):
        date = self.date_var.get().strip()
        if not validate_date(date):
            messagebox.showerror("Invalid Date", "Enter date as YYYY-MM-DD.", parent=self)
            return

        amount_str = self.amount_var.get().strip()
        if not validate_amount(amount_str):
            messagebox.showerror("Invalid Amount", "Enter a positive number.", parent=self)
            return

        category = self.category_var.get()
        if not category:
            messagebox.showerror("Missing Category", "Select a category.", parent=self)
            return

        self.result = Transaction(
            id=self.editing.id if self.editing else None,
            date=date,
            amount=float(amount_str),
            type=self.type_var.get(),
            category=category,
            description=self.desc_var.get().strip(),
        )
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.destroy()
