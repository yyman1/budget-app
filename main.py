import matplotlib
matplotlib.use("TkAgg")

import tkinter as tk
from database import Database
from ui.app_window import AppWindow
from ui.dashboard_frame import DashboardFrame
from ui.transactions_frame import TransactionsFrame
from ui.budgets_frame import BudgetsFrame


def main():
    root = tk.Tk()
    db = Database()
    app = AppWindow(root, db)

    # Create tab frames
    dashboard = DashboardFrame(app.notebook, db)
    transactions = TransactionsFrame(app.notebook, db, on_data_changed=app.refresh_all)
    budgets = BudgetsFrame(app.notebook, db, on_data_changed=app.refresh_all)

    # Register frames for cross-tab refresh
    app.dashboard_frame = dashboard
    app.transactions_frame = transactions
    app.budgets_frame = budgets

    # Add tabs
    app.add_tab(dashboard, "Dashboard")
    app.add_tab(transactions, "Transactions")
    app.add_tab(budgets, "Budgets")

    # Initial load
    dashboard.refresh()

    root.mainloop()


if __name__ == "__main__":
    main()
