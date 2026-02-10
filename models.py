from dataclasses import dataclass
from typing import Optional


@dataclass
class Transaction:
    id: Optional[int]
    date: str
    amount: float
    type: str  # "income" or "expense"
    category: str
    description: str
    created_at: Optional[str] = None


@dataclass
class Budget:
    id: Optional[int]
    category: str
    month: str  # YYYY-MM
    amount_limit: float


@dataclass
class CategorySpending:
    category: str
    total_spent: float
    budget_limit: Optional[float] = None


@dataclass
class MonthlySummary:
    month: str
    total_income: float
    total_expenses: float
    net_balance: float
