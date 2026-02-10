from __future__ import annotations
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt

from constants import INCOME_COLOR, EXPENSE_COLOR, BALANCE_COLOR
from database import Database
from utils import format_currency, current_month_str, get_month_choices
from ui.chart_helpers import create_pie_chart, create_bar_chart


class DashboardFrame(ttk.Frame):
    def __init__(self, parent, db: Database):
        super().__init__(parent)
        self.db = db
        self._chart_widgets = []
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

        # Summary cards
        self.cards_frame = ttk.Frame(self)
        self.cards_frame.pack(fill=tk.X, padx=10, pady=8)

        self.income_label = self._make_card(self.cards_frame, "Total Income", "$0.00", INCOME_COLOR)
        self.expense_label = self._make_card(self.cards_frame, "Total Expenses", "$0.00", EXPENSE_COLOR)
        self.balance_label = self._make_card(self.cards_frame, "Net Balance", "$0.00", BALANCE_COLOR)

        # Charts area
        self.charts_frame = ttk.Frame(self)
        self.charts_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)

        # Empty state label
        self.empty_label = ttk.Label(
            self.charts_frame, text="No data for this month.\nAdd some transactions to see charts!",
            font=("Helvetica", 12), foreground="#95a5a6", anchor=tk.CENTER, justify=tk.CENTER,
        )

    def _make_card(self, parent, title: str, value: str, color: str) -> tk.Label:
        card = tk.Frame(parent, bg="white", highlightbackground="#ddd", highlightthickness=1, padx=16, pady=10)
        card.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        tk.Label(card, text=title, font=("Helvetica", 10), bg="white", fg="#7f8c8d").pack()
        val_label = tk.Label(card, text=value, font=("Helvetica", 18, "bold"), bg="white", fg=color)
        val_label.pack()
        return val_label

    def refresh(self):
        month = self.month_var.get()

        # Update summary cards
        summary = self.db.get_monthly_summary(month)
        self.income_label.config(text=format_currency(summary.total_income))
        self.expense_label.config(text=format_currency(summary.total_expenses))
        bal_color = INCOME_COLOR if summary.net_balance >= 0 else EXPENSE_COLOR
        self.balance_label.config(text=format_currency(summary.net_balance), fg=bal_color)

        # Clear old charts
        for w in self._chart_widgets:
            w.get_tk_widget().destroy()
            w.figure.clear()
            plt.close(w.figure)
        self._chart_widgets.clear()
        self.empty_label.pack_forget()

        # Pie chart data
        cat_spending = self.db.get_category_spending(month)
        pie_data = {cs.category: cs.total_spent for cs in cat_spending}

        # Bar chart data
        budget_vs = self.db.get_budget_vs_actual(month)
        bar_cats = [bv.category for bv in budget_vs]
        bar_actual = [bv.total_spent for bv in budget_vs]
        bar_limits = [bv.budget_limit or 0 for bv in budget_vs]

        has_data = bool(pie_data) or bool(bar_cats)

        if not has_data:
            self.empty_label.pack(expand=True)
            return

        # Create charts side by side
        pie_canvas = create_pie_chart(self.charts_frame, pie_data, "Spending by Category")
        if pie_canvas:
            pie_canvas.get_tk_widget().pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)
            pie_canvas.draw()
            self._chart_widgets.append(pie_canvas)

        bar_canvas = create_bar_chart(self.charts_frame, bar_cats, bar_actual, bar_limits, "Budget vs Actual")
        if bar_canvas:
            bar_canvas.get_tk_widget().pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)
            bar_canvas.draw()
            self._chart_widgets.append(bar_canvas)
