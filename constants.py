APP_NAME = "Budget Manager"
WINDOW_WIDTH = 1100
WINDOW_HEIGHT = 750

EXPENSE_CATEGORIES = [
    "Housing",
    "Food & Groceries",
    "Transportation",
    "Utilities",
    "Entertainment",
    "Healthcare",
    "Shopping",
    "Education",
    "Personal Care",
    "Other",
]

INCOME_CATEGORIES = [
    "Salary",
    "Freelance",
    "Investments",
    "Gifts",
    "Other Income",
]

ALL_CATEGORIES = EXPENSE_CATEGORIES + INCOME_CATEGORIES

CATEGORY_COLORS = {
    "Housing": "#e74c3c",
    "Food & Groceries": "#e67e22",
    "Transportation": "#f1c40f",
    "Utilities": "#2ecc71",
    "Entertainment": "#1abc9c",
    "Healthcare": "#3498db",
    "Shopping": "#9b59b6",
    "Education": "#34495e",
    "Personal Care": "#e84393",
    "Other": "#95a5a6",
    "Salary": "#27ae60",
    "Freelance": "#2980b9",
    "Investments": "#8e44ad",
    "Gifts": "#d35400",
    "Other Income": "#7f8c8d",
}

INCOME_COLOR = "#27ae60"
EXPENSE_COLOR = "#e74c3c"
BALANCE_COLOR = "#2980b9"

DATE_FORMAT = "%Y-%m-%d"
MONTH_FORMAT = "%Y-%m"

DB_NAME = "budget.db"
