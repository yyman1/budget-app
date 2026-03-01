"""Google Sheets API connection and data retrieval."""

import json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class SheetServiceError(Exception):
    """Raised when the sheet service encounters an error."""
    pass


class SheetService:
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.readonly",
    ]

    def __init__(self, token_path, credentials_path, sheet_id):
        self.token_path = token_path
        self.credentials_path = credentials_path
        self.sheet_id = sheet_id
        self._service = None

    def _get_credentials(self):
        """Load and refresh OAuth credentials."""
        try:
            with open(self.token_path, "r") as f:
                token_data = json.load(f)
            creds = Credentials.from_authorized_user_info(token_data, self.SCOPES)
        except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
            raise SheetServiceError(
                f"Cannot load token.json: {e}. "
                "Please re-authorize by running the OAuth flow."
            )

        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                # Write refreshed token back
                with open(self.token_path, "w") as f:
                    f.write(creds.to_json())
            except Exception as e:
                raise SheetServiceError(
                    f"Token refresh failed: {e}. "
                    "Please re-authorize by running the OAuth flow."
                )

        if not creds.valid:
            raise SheetServiceError(
                "Credentials are not valid. Please re-authorize."
            )

        return creds

    def _get_service(self):
        """Build or return cached Sheets API service."""
        if self._service is None:
            creds = self._get_credentials()
            self._service = build("sheets", "v4", credentials=creds)
        return self._service

    def get_sheet_names(self):
        """Return list of sheet tab names in the spreadsheet."""
        try:
            service = self._get_service()
            spreadsheet = service.spreadsheets().get(
                spreadsheetId=self.sheet_id
            ).execute()
            return [s["properties"]["title"] for s in spreadsheet["sheets"]]
        except HttpError as e:
            if e.resp.status == 404:
                raise SheetServiceError("Spreadsheet not found. Check the sheet ID.")
            elif e.resp.status == 403:
                raise SheetServiceError("No access to this spreadsheet. Check sharing settings.")
            raise SheetServiceError(f"Google Sheets API error: {e}")

    def read_all_values(self, sheet_tab_name):
        """Read all cell values from a sheet tab. Returns a 2D list of strings."""
        try:
            service = self._get_service()
            result = service.spreadsheets().values().get(
                spreadsheetId=self.sheet_id,
                range=sheet_tab_name,
            ).execute()
            return result.get("values", [])
        except HttpError as e:
            if e.resp.status == 400:
                raise SheetServiceError(f"Sheet tab '{sheet_tab_name}' not found.")
            raise SheetServiceError(f"Google Sheets API error: {e}")
