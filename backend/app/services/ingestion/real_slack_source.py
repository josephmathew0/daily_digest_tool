import os
import ssl
from datetime import datetime, timezone

import certifi
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from app.models.communication_event import CommunicationEvent
from app.models.enums import SourceType
from app.services.ingestion.base_source import CommunicationSource


class RealSlackSource(CommunicationSource):
    def __init__(self) -> None:
        self.token = os.getenv("SLACK_BOT_TOKEN", "")
        self.channel_id = os.getenv("SLACK_CHANNEL_ID", "")
        self.channel_name = os.getenv("SLACK_CHANNEL_NAME", self.channel_id)
        self.project = os.getenv("SLACK_PROJECT", "warehouse_robot_v2")
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        self.client = WebClient(token=self.token, ssl=ssl_context)
        self._user_cache: dict[str, dict[str, str | None]] = {}

    def fetch_events(self) -> list[CommunicationEvent]:
        if not self.token or self.token.startswith("xoxb-your-real-token") or not self.channel_id:
            return []

        events: list[CommunicationEvent] = []
        cursor: str | None = None

        try:
            # Slack history is paginated. We fetch the current channel history
            # into normalized CommunicationEvent objects and let the repository
            # deduplicate by stable Slack timestamp IDs.
            while True:
                response = self.client.conversations_history(
                    channel=self.channel_id,
                    cursor=cursor,
                    limit=100,
                )
                for message in response.get("messages", []):
                    event = self._message_to_event(message)
                    if event:
                        events.append(event)

                metadata = response.get("response_metadata") or {}
                cursor = metadata.get("next_cursor") or None
                if not cursor:
                    break
        except SlackApiError as exc:
            detail = exc.response.get("error", "unknown_error")
            raise RuntimeError(f"Slack fetch failed: {detail}") from exc

        return sorted(events, key=lambda event: event.timestamp)

    def _message_to_event(self, message: dict) -> CommunicationEvent | None:
        text = (message.get("text") or "").strip()
        ts = message.get("ts")
        user_id = message.get("user")
        subtype = message.get("subtype")

        if not text or not ts or subtype in {"channel_join", "bot_message"}:
            return None

        # Slack timestamps are stable per message, so they make good source IDs
        # and preserve message order when converted to datetimes.
        user = self._user(user_id) if user_id else {}
        timestamp = datetime.fromtimestamp(float(ts), tz=timezone.utc)

        return CommunicationEvent(
            id=f"slack_real_{ts.replace('.', '_')}",
            source_type=SourceType.SLACK,
            source_ref=f"#{self.channel_name}",
            author_name=user.get("name"),
            author_email=user.get("email"),
            author_role=None,
            title=None,
            text=text,
            timestamp=timestamp,
            channel=self.channel_name,
            thread_id=message.get("thread_ts"),
            recipients=[],
            attendees=[],
            reactions=[reaction.get("name", "") for reaction in message.get("reactions", [])],
            project=self.project,
            metadata={
                "slack_channel_id": self.channel_id,
                "slack_user_id": user_id,
                "slack_ts": ts,
                "real_source": True,
            },
        )

    def _user(self, user_id: str) -> dict[str, str | None]:
        if user_id in self._user_cache:
            return self._user_cache[user_id]

        try:
            # Cache user profiles because a channel history can contain many
            # messages from the same person.
            response = self.client.users_info(user=user_id)
            profile = response.get("user", {}).get("profile", {})
            user = {
                "name": profile.get("real_name") or profile.get("display_name") or user_id,
                "email": profile.get("email"),
            }
        except SlackApiError:
            user = {"name": user_id, "email": None}

        self._user_cache[user_id] = user
        return user
