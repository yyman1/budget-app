from __future__ import annotations
from datetime import datetime, date

from constants import DATE_FORMAT, MONTH_FORMAT


def format_currency(amount: float) -> str:
    return f"${amount:,.2f}"


def today_str() -> str:
    return date.today().strftime(DATE_FORMAT)


def current_month_str() -> str:
    return date.today().strftime(MONTH_FORMAT)


def get_month_choices(start_year: int = 2024) -> list[str]:
    """Return a list of YYYY-MM strings from start_year-01 through current month."""
    now = date.today()
    months = []
    for year in range(start_year, now.year + 1):
        for month in range(1, 13):
            m = f"{year}-{month:02d}"
            if m <= now.strftime(MONTH_FORMAT):
                months.append(m)
    return list(reversed(months))


def validate_date(date_str: str) -> bool:
    try:
        datetime.strptime(date_str, DATE_FORMAT)
        return True
    except ValueError:
        return False


def validate_amount(amount_str: str) -> bool:
    try:
        val = float(amount_str)
        return val > 0
    except (ValueError, TypeError):
        return False
