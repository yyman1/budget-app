from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable

from constants import EXPENSE_CATEGORIES
from database import Database
from models import Budget
from utils import format_currency, current_month_str, get_month_choices


class BudgetsFrame(ttk.Frame):
    def __init__(self, parent, db: Database, on_data_changed: Callable):
        super().__init__(parent)
        self.db = db
        self.on_data_changed = on_data_changed
        self._entries: dict[str, tk.StringVar] = {}
        self._spent_labels: dict[str, ttk.Label] = {}
        self._progress_bars: dict[str, ttk.Progressbar] = {}
        self._pct_labels: dict[str, ttk.Label] = {}
        self._build_ui()

    def _build_ui(self):
        # Month selector
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=10, pady=(10, 4))

        ttk.Label(top, text="Month:").pack(side=tk.LEFT, padx=(0, 4))
        self.month_var = tk.StringVar(value=current_month_str())
        month_combo = ttk.Combobox(
            top, textvariable=self.month_var,
            values=get_month_choices(), state="readonly", width=10,
        )
        month_combo.pack(side=tk.LEFT)
        month_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        ttk.Button(top, text="Save All Budgets", command=self._on_save).pack(side=tk.RIGHT)

        # Scrollable category rows
        canvas = tk.Canvas(self, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=canvas.yview)
        self.rows_frame = ttk.Frame(canvas)

        self.rows_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.rows_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=4)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Header row
        header = ttk.Frame(self.rows_frame)
        header.pack(fill=tk.X, pady=(4, 8))
        ttk.Label(header, text="Category", font=("Helvetica", 10, "bold"), width=18).pack(side=tk.LEFT, padx=4)
        ttk.Label(header, text="Budget Limit ($)", font=("Helvetica", 10, "bold"), width=14).pack(side=tk.LEFT, padx=4)
        ttk.Label(header, text="Spent", font=("Helvetica", 10, "bold"), width=12).pack(side=tk.LEFT, padx=4)
        ttk.Label(header, text="Progress", font=("Helvetica", 10, "bold"), width=20).pack(side=tk.LEFT, padx=4)
        ttk.Label(header, text="%", font=("Helvetica", 10, "bold"), width=8).pack(side=tk.LEFT, padx=4)

        # Create a row for each expense category
        style = ttk.Style()
        style.configure("green.Horizontal.TProgressbar", troughcolor="#ecf0f1", background="#2ecc71")
        style.configure("red.Horizontal.TProgressbar", troughcolor="#ecf0f1", background="#e74c3c")

        for cat in EXPENSE_CATEGORIES:
            row = ttk.Frame(self.rows_frame)
            row.pack(fill=tk.X, pady=2)

            ttk.Label(row, text=cat, width=18).pack(side=tk.LEFT, padx=4)

            var = tk.StringVar(value="")
            entry = ttk.Entry(row, textvariable=var, width=14)
            entry.pack(side=tk.LEFT, padx=4)
            self._entries[cat] = var

            spent_lbl = ttk.Label(row, text="$0.00", width=12)
            spent_lbl.pack(side=tk.LEFT, padx=4)
            self._spent_labels[cat] = spent_lbl

            pb = ttk.Progressbar(row, length=160, mode="determinate", style="green.Horizontal.TProgressbar")
            pb.pack(side=tk.LEFT, padx=4)
            self._progress_bars[cat] = pb

            pct_lbl = ttk.Label(row, text="", width=8)
            pct_lbl.pack(side=tk.LEFT, padx=4)
            self._pct_labels[cat] = pct_lbl

    def refresh(self):
        month = self.month_var.get()
        budgets = self.db.get_budgets(month)
        spending_list = self.db.get_budget_vs_actual(month)
        spending = {cs.category: cs.total_spent for cs in spending_list}

        for cat in EXPENSE_CATEGORIES:
            limit = budgets.get(cat, 0)
            spent = spending.get(cat, 0)

            self._entries[cat].set(f"{limit:.2f}" if limit else "")
            self._spent_labels[cat].config(text=format_currency(spent))

            if limit and limit > 0:
                pct = (spent / limit) * 100
                self._progress_bars[cat]["value"] = min(pct, 100)
                over = pct > 100
                self._progress_bars[cat].configure(
                    style="red.Horizontal.TProgressbar" if over else "green.Horizontal.TProgressbar"
                )
                self._pct_labels[cat].config(
                    text=f"{pct:.0f}%",
                    foreground="#e74c3c" if over else "#2ecc71",
                )
            else:
                self._progress_bars[cat]["value"] = 0
                self._pct_labels[cat].config(text="")

    def _on_save(self):
        month = self.month_var.get()
        for cat in EXPENSE_CATEGORIES:
            val = self._entries[cat].get().strip()
            if not val:
                continue
            try:
                amount = float(val)
                if amount < 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Invalid Budget", f"Invalid amount for {cat}.", parent=self)
                return
            self.db.set_budget(Budget(id=None, category=cat, month=month, amount_limit=amount))
        self.on_data_changed()
        messagebox.showinfo("Saved", "Budgets saved successfully.", parent=self)
