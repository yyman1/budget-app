from __future__ import annotations
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk

from constants import CATEGORY_COLORS


def create_pie_chart(parent: tk.Widget, data: dict[str, float], title: str) -> FigureCanvasTkAgg | None:
    """Create a pie chart of spending by category. Returns the canvas or None if no data."""
    if not data:
        return None

    fig = Figure(figsize=(4.5, 3.5), dpi=100)
    ax = fig.add_subplot(111)

    labels = list(data.keys())
    values = list(data.values())
    colors = [CATEGORY_COLORS.get(l, "#95a5a6") for l in labels]

    wedges, texts, autotexts = ax.pie(
        values, labels=None, autopct="%1.0f%%", colors=colors,
        startangle=90, pctdistance=0.8,
    )
    for t in autotexts:
        t.set_fontsize(8)
    ax.legend(labels, loc="center left", bbox_to_anchor=(-0.3, 0.5), fontsize=7)
    ax.set_title(title, fontsize=10, fontweight="bold")
    fig.tight_layout()

    canvas = FigureCanvasTkAgg(fig, master=parent)
    return canvas


def create_bar_chart(
    parent: tk.Widget, categories: list[str], actual: list[float], limits: list[float], title: str
) -> FigureCanvasTkAgg | None:
    """Create a grouped bar chart of budget vs actual spending."""
    if not categories:
        return None

    fig = Figure(figsize=(4.5, 3.5), dpi=100)
    ax = fig.add_subplot(111)

    x = range(len(categories))
    width = 0.35

    ax.bar([i - width / 2 for i in x], actual, width, label="Spent", color="#e74c3c", alpha=0.8)
    ax.bar([i + width / 2 for i in x], limits, width, label="Budget", color="#3498db", alpha=0.8)

    # Shorten long category names
    short = [c[:10] + ".." if len(c) > 12 else c for c in categories]
    ax.set_xticks(list(x))
    ax.set_xticklabels(short, rotation=30, ha="right", fontsize=7)
    ax.set_title(title, fontsize=10, fontweight="bold")
    ax.legend(fontsize=8)
    ax.set_ylabel("$", fontsize=9)
    fig.tight_layout()

    canvas = FigureCanvasTkAgg(fig, master=parent)
    return canvas
