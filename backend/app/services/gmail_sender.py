import base64
import os
from email.message import EmailMessage
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]
BASE_DIR = Path(__file__).resolve().parents[2]


class GmailSender:
    """Small Gmail API wrapper for the demo procurement-send flow."""

    def __init__(self) -> None:
        self.account = os.getenv("EMAIL_ACCOUNT", "josephtestemail0@gmail.com")
        self.token_path = BASE_DIR / os.getenv("GMAIL_TOKEN_PATH", "gmail_token.json")

    def send(self, *, recipient_email: str, subject: str, body: str) -> str:
        service = build("gmail", "v1", credentials=self._credentials())
        response = service.users().messages().send(
            userId="me",
            body={"raw": self._raw_message(recipient_email=recipient_email, subject=subject, body=body)},
        ).execute()
        return response.get("id", "")

    def _credentials(self) -> Credentials:
        if not self.token_path.exists():
            raise FileNotFoundError(f"Missing Gmail token file: {self.token_path}")

        credentials = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            self.token_path.write_text(credentials.to_json())
        return credentials

    def _raw_message(self, *, recipient_email: str, subject: str, body: str) -> str:
        message = EmailMessage()
        message["To"] = recipient_email
        message["From"] = self.account
        message["Subject"] = subject
        message.set_content(body)
        return base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
