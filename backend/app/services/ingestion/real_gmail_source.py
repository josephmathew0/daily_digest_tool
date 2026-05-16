import base64
import os
import re
from datetime import datetime, timezone
from email.utils import getaddresses, parsedate_to_datetime
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.models.communication_event import CommunicationEvent
from app.models.enums import SourceType
from app.services.ingestion.base_source import CommunicationSource


SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
BASE_DIR = Path(__file__).resolve().parents[3]


class RealGmailSource(CommunicationSource):
    def __init__(self) -> None:
        self.account = os.getenv("EMAIL_ACCOUNT", "josephtestemail0@gmail.com")
        self.project = os.getenv("EMAIL_PROJECT", "warehouse_robot_v2")
        self.lookback_days = int(os.getenv("EMAIL_LOOKBACK_DAYS", "14"))
        self.include_sent = os.getenv("EMAIL_INCLUDE_SENT", "true").lower() == "true"
        self.token_path = BASE_DIR / os.getenv("GMAIL_TOKEN_PATH", "gmail_token.json")
        self.project_terms = self._csv(
            os.getenv(
                "EMAIL_PROJECT_TERMS",
                "warehouse,robot,prototype,motor,mount,tolerance,cad,connector,firmware,pcb,"
                "thermal,evt,dvt,pvt,bom,supplier,vendor,bracket,lead time,demo,milestone,"
                "assembly,risk,blocked,decision,action item",
            )
        )
        self.excluded_senders = self._csv(
            os.getenv(
                "EMAIL_EXCLUDED_SENDERS",
                "no-reply@accounts.google.com,accounts.google.com,google.com",
            )
        )

    def fetch_events(self) -> list[CommunicationEvent]:
        if not self.token_path.exists():
            return []

        service = build("gmail", "v1", credentials=self._credentials())
        events = self._fetch_query(service, "in:inbox", "received")
        if self.include_sent:
            events.extend(self._fetch_query(service, "in:sent", "sent"))
        return sorted(events, key=lambda event: event.timestamp)

    def _credentials(self) -> Credentials:
        credentials = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            self.token_path.write_text(credentials.to_json())
        return credentials

    def _fetch_query(self, service, label_query: str, direction: str) -> list[CommunicationEvent]:
        query = f"{label_query} newer_than:{self.lookback_days}d"
        response = service.users().messages().list(userId="me", q=query, maxResults=50).execute()
        messages = response.get("messages", [])
        events: list[CommunicationEvent] = []

        for message_ref in messages:
            message = service.users().messages().get(
                userId="me",
                id=message_ref["id"],
                format="full",
            ).execute()
            event = self._message_to_event(message, direction)
            if event:
                events.append(event)

        return events

    def _message_to_event(self, message: dict, direction: str) -> CommunicationEvent | None:
        payload = message.get("payload", {})
        headers = {header["name"].lower(): header["value"] for header in payload.get("headers", [])}
        subject = headers.get("subject") or "(No subject)"
        sender = headers.get("from", "")
        recipients = headers.get("to", "")
        timestamp = self._timestamp(headers.get("date"), message.get("internalDate"))
        body = self._body(payload) or message.get("snippet") or ""
        body = self._clean_body(body)

        if not body.strip() and not subject.strip():
            return None
        if not self._is_relevant_email(subject, body, sender):
            return None

        sender_name, sender_email = self._first_address(sender)
        recipient_emails = [email for _, email in getaddresses([recipients]) if email]

        return CommunicationEvent(
            id=f"gmail_{direction}_{message['id']}",
            source_type=SourceType.EMAIL,
            source_ref=f"Gmail {direction}",
            author_name=sender_name,
            author_email=sender_email,
            title=subject,
            text=body[:2000],
            timestamp=timestamp,
            recipients=recipient_emails,
            project=self.project,
            metadata={
                "provider": "gmail",
                "direction": direction,
                "gmail_message_id": message["id"],
                "gmail_thread_id": message.get("threadId"),
                "account": self.account,
                "real_source": True,
            },
        )

    def _timestamp(self, date_header: str | None, internal_date: str | None) -> datetime:
        if date_header:
            try:
                parsed = parsedate_to_datetime(date_header)
                return parsed.astimezone(timezone.utc)
            except (TypeError, ValueError):
                pass
        if internal_date:
            return datetime.fromtimestamp(int(internal_date) / 1000, tz=timezone.utc)
        return datetime.now(timezone.utc)

    def _body(self, payload: dict) -> str:
        if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
            return self._decode(payload["body"]["data"])

        for part in payload.get("parts", []) or []:
            if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                return self._decode(part["body"]["data"])
            nested = self._body(part)
            if nested:
                return nested

        return ""

    def _decode(self, data: str) -> str:
        return base64.urlsafe_b64decode(data.encode()).decode("utf-8", errors="replace")

    def _first_address(self, raw: str) -> tuple[str | None, str | None]:
        addresses = getaddresses([raw])
        if not addresses:
            return None, None
        name, email = addresses[0]
        return name or email or None, email or None

    def _clean_body(self, body: str) -> str:
        body = re.sub(r"<https?://[^>\s]+>", "", body)
        body = re.sub(r"https?://\S+", "", body)
        body = re.sub(r"\s+", " ", body)
        return body.strip()

    def _is_relevant_email(self, subject: str, body: str, sender: str) -> bool:
        sender_lower = sender.lower()
        if any(excluded in sender_lower for excluded in self.excluded_senders):
            return False

        searchable = f"{subject} {body}".lower()
        return any(term in searchable for term in self.project_terms)

    def _csv(self, value: str) -> list[str]:
        return [item.strip().lower() for item in value.split(",") if item.strip()]
