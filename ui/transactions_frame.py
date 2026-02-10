from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable

from constants import EXPENSE_CATEGORIES, INCOME_CATEGORIES, ALL_CATEGORIES
from database import Database
from models import Transaction
from utils import format_currency, current_month_str, get_month_choices
from ui.dialogs import TransactionDialog


class TransactionsFrame(ttk.Frame):
    def __init__(self, parent, db: Database, on_data_changed: Callable):
        super().__init__(parent)
        self.db = db
        self.on_data_changed = on_data_changed
        self._build_ui()

    def _build_ui(self):
        # --- Filter bar ---
        filter_frame = ttk.Frame(self)
        filter_frame.pack(fill=tk.X, padx=10, pady=(10, 4))

        ttk.Label(filter_frame, text="Month:").pack(side=tk.LEFT, padx=(0, 4))
        self.month_var = tk.StringVar(value=current_month_str())
        month_combo = ttk.Combobox(
            filter_frame, textvariable=self.month_var,
            values=get_month_choices(), state="readonly", width=10,
        )
        month_combo.pack(side=tk.LEFT, padx=(0, 12))
        month_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        ttk.Label(filter_frame, text="Category:").pack(side=tk.LEFT, padx=(0, 4))
        self.category_var = tk.StringVar(value="All")
        cat_combo = ttk.Combobox(
            filter_frame, textvariable=self.category_var,
            values=["All"] + ALL_CATEGORIES, state="readonly", width=16,
        )
        cat_combo.pack(side=tk.LEFT, padx=(0, 12))
        cat_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        ttk.Label(filter_frame, text="Type:").pack(side=tk.LEFT, padx=(0, 4))
        self.type_var = tk.StringVar(value="All")
        type_combo = ttk.Combobox(
            filter_frame, textvariable=self.type_var,
            values=["All", "income", "expense"], state="readonly", width=10,
        )
        type_combo.pack(side=tk.LEFT, padx=(0, 12))
        type_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        ttk.Button(filter_frame, text="+ Add Transaction", command=self._on_add).pack(side=tk.RIGHT)

        # --- Treeview ---
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)

        columns = ("date", "type", "category", "amount", "description")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("date", text="Date")
        self.tree.heading("type", text="Type")
        self.tree.heading("category", text="Category")
        self.tree.heading("amount", text="Amount")
        self.tree.heading("description", text="Description")

        self.tree.column("date", width=100, anchor=tk.CENTER)
        self.tree.column("type", width=80, anchor=tk.CENTER)
        self.tree.column("category", width=140)
        self.tree.column("amount", width=100, anchor=tk.E)
        self.tree.column("description", width=300)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Tag styling
        self.tree.tag_configure("income", foreground="#27ae60")
        self.tree.tag_configure("expense", foreground="#e74c3c")

        # --- Action buttons ---
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=(4, 10))
        ttk.Button(btn_frame, text="Edit", command=self._on_edit).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_frame, text="Delete", command=self._on_delete).pack(side=tk.LEFT)

        # Store txn ids for selection lookup
        self._txn_ids: list[int] = []

    def refresh(self):
        month = self.month_var.get()
        category = self.category_var.get()
        txn_type = self.type_var.get()

        transactions = self.db.get_transactions(
            month=month,
            category=category if category != "All" else None,
            txn_type=txn_type if txn_type != "All" else None,
        )

        self.tree.delete(*self.tree.get_children())
        self._txn_ids.clear()

        for txn in transactions:
            tag = txn.type
            amount_str = format_currency(txn.amount)
            if txn.type == "expense":
                amount_str = f"-{amount_str}"
            self.tree.insert(
                "", tk.END,
                values=(txn.date, txn.type.capitalize(), txn.category, amount_str, txn.description),
                tags=(tag,),
            )
            self._txn_ids.append(txn.id)

    def _get_selected_txn(self) -> Transaction | None:
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("No Selection", "Select a transaction first.")
            return None
        index = self.tree.index(sel[0])
        txn_id = self._txn_ids[index]
        # Fetch fresh from db
        txns = self.db.get_transactions()
        for t in txns:
            if t.id == txn_id:
                return t
        return None

    def _on_add(self):
        dlg = TransactionDialog(self)
        if dlg.result:
            self.db.add_transaction(dlg.result)
            self.on_data_changed()

    def _on_edit(self):
        txn = self._get_selected_txn()
        if not txn:
            return
        dlg = TransactionDialog(self, transaction=txn)
        if dlg.result:
            self.db.update_transaction(dlg.result)
            self.on_data_changed()

    def _on_delete(self):
        txn = self._get_selected_txn()
        if not txn:
            return
        if messagebox.askyesno("Confirm Delete", f"Delete this {txn.type} of {format_currency(txn.amount)}?"):
            self.db.delete_transaction(txn.id)
            self.on_data_changed()
