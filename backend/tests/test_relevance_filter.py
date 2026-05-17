from datetime import datetime, timezone

from app.models.communication_event import CommunicationEvent
from app.models.enums import SourceType
from app.services.relevance_filter import RelevanceFilter
from app.services.state_tracker import StateTracker


def event(
    text: str,
    *,
    title: str | None = None,
    source_type: SourceType = SourceType.SLACK,
) -> CommunicationEvent:
    return CommunicationEvent(
        id=f"event_{abs(hash((text, title, source_type))) }",
        source_type=source_type,
        source_ref="test",
        author_name="Alex",
        author_email="alex@example.com",
        title=title,
        text=text,
        timestamp=datetime(2026, 5, 16, tzinfo=timezone.utc),
        project="warehouse_robot_v2",
    )


def test_acknowledgement_is_ignored_before_extraction():
    relevance_filter = RelevanceFilter()
    acknowledged = relevance_filter.annotate(event("Acknowledged."))

    assert acknowledged.metadata["relevance"]["is_relevant"] is False

    entities = StateTracker().build_entities([acknowledged])

    assert entities == []


def test_google_welcome_email_is_ignored():
    relevance_filter = RelevanceFilter()
    welcome_email = relevance_filter.annotate(
        event(
            "Welcome to Google. Review your Google Account settings. Choose Chrome. "
            "Visit Help Center. This email was sent to josephtestemail0@gmail.com. Unsubscribe.",
            title="Joseph, review your Google Account settings for your new account",
            source_type=SourceType.EMAIL,
        )
    )

    assert welcome_email.metadata["relevance"]["is_relevant"] is False
    assert welcome_email.metadata["relevance"]["category"] == "email_noise"


def test_project_risk_message_is_kept():
    relevance_filter = RelevanceFilter()
    risk = relevance_filter.annotate(
        event("PCB thermal rise is 12C over target and EVT reliability remains at risk.")
    )

    assert risk.metadata["relevance"]["is_relevant"] is True
    assert risk.metadata["relevance"]["category"] == "project_signal"
