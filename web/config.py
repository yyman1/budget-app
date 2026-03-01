import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-budget-app-key")
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'budget_v2.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Google Sheets
    GOOGLE_CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")
    GOOGLE_TOKEN_PATH = os.path.join(BASE_DIR, "token.json")
    GOOGLE_SHEET_ID = "17KPfSR3rlRaIMAkVkKRBeGmr2QyVFfPl5vUQF-64i_0"

    # Chase Drive folders
    CHASE_DRIVE_FOLDERS = [
        {"folder_id": "1TYp_RXxqyASDD3R-1tk99aIervrpCTq5", "label": "Chase Business (2163)", "last_four": "2163"},
        {"folder_id": "171JaVSJEgIPzQIyurqdGWTvVuCEMTVFH", "label": "Chase Personal (5540)", "last_four": "5540"},
    ]

    # Card-level category overrides: card_last_four -> category_id
    # All transactions on these cards get this category regardless of merchant mapping
    CARD_CATEGORY_OVERRIDES = {
        "1659": 16,  # Abigail's card → "Israel (Abigail)"
    }
