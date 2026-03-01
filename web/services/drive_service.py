"""Google Drive API: list PDFs in a folder and download content."""

import json
import re
from datetime import datetime
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class DriveServiceError(Exception):
    pass


class DriveService:
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.readonly",
    ]

    def __init__(self, token_path, credentials_path):
        self.token_path = token_path
        self.credentials_path = credentials_path
        self._service = None

    def _get_credentials(self):
        try:
            with open(self.token_path, "r") as f:
                token_data = json.load(f)
            creds = Credentials.from_authorized_user_info(token_data, self.SCOPES)
        except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
            raise DriveServiceError(f"Cannot load token.json: {e}")

        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                with open(self.token_path, "w") as f:
                    f.write(creds.to_json())
            except Exception as e:
                raise DriveServiceError(f"Token refresh failed: {e}")

        if not creds.valid:
            raise DriveServiceError("Credentials are not valid.")

        return creds

    def _get_service(self):
        if self._service is None:
            creds = self._get_credentials()
            self._service = build("drive", "v3", credentials=creds)
        return self._service

    def list_pdfs(self, folder_id):
        """List PDF files in a Drive folder.

        Returns list of dicts: [{id, name, statement_date}, ...]
        where statement_date is parsed from filename like '20250908-statements-2163-.pdf'.
        """
        try:
            service = self._get_service()
            results = service.files().list(
                q=f"'{folder_id}' in parents and mimeType='application/pdf'",
                fields="files(id, name)",
                orderBy="name desc",
            ).execute()
        except HttpError as e:
            raise DriveServiceError(f"Drive API error: {e}")

        files = results.get("files", [])
        out = []
        for f in files:
            statement_date = self._parse_filename_date(f["name"])
            out.append({
                "id": f["id"],
                "name": f["name"],
                "statement_date": statement_date,
            })
        return out

    def download_pdf(self, file_id):
        """Download a PDF file's content as bytes."""
        try:
            service = self._get_service()
            return service.files().get_media(fileId=file_id).execute()
        except HttpError as e:
            raise DriveServiceError(f"Failed to download file: {e}")

    @staticmethod
    def _parse_filename_date(filename):
        """Extract statement date from filename like '20250908-statements-2163-.pdf'.

        Returns 'YYYY-MM-DD' or the raw filename if pattern doesn't match.
        """
        m = re.match(r"(\d{4})(\d{2})(\d{2})-statements-", filename)
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        return filename
