import tkinter as tk
from tkinter import ttk

from constants import APP_NAME, WINDOW_WIDTH, WINDOW_HEIGHT
from database import Database


class AppWindow:
    def __init__(self, root: tk.Tk, db: Database):
        self.root = root
        self.db = db

        self.root.title(APP_NAME)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.minsize(900, 600)

        self._setup_styles()

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Frames will be added by main.py after all UI modules are created
        self.dashboard_frame = None
        self.transactions_frame = None
        self.budgets_frame = None

        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook.Tab", padding=[16, 8], font=("Helvetica", 11))
        style.configure("Treeview", rowheight=28, font=("Helvetica", 10))
        style.configure("Treeview.Heading", font=("Helvetica", 10, "bold"))

    def add_tab(self, frame: ttk.Frame, title: str):
        self.notebook.add(frame, text=title)

    def _on_tab_changed(self, event):
        tab_index = self.notebook.index(self.notebook.select())
        if tab_index == 0 and self.dashboard_frame:
            self.dashboard_frame.refresh()
        elif tab_index == 1 and self.transactions_frame:
            self.transactions_frame.refresh()
        elif tab_index == 2 and self.budgets_frame:
            self.budgets_frame.refresh()

    def refresh_all(self):
        """Called after data mutations to sync all tabs."""
        if self.dashboard_frame:
            self.dashboard_frame.refresh()
        if self.transactions_frame:
            self.transactions_frame.refresh()
        if self.budgets_frame:
            self.budgets_frame.refresh()
