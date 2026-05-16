import os
from pathlib import Path

from app.services.ingestion.base_source import CommunicationSource
from app.services.ingestion.json_source import JsonCommunicationSource
from app.services.ingestion.real_slack_source import RealSlackSource


DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def build_sources() -> list[CommunicationSource]:
    slack_source = os.getenv("SLACK_SOURCE", "mock").lower()
    sources: list[CommunicationSource] = []

    if slack_source in {"mock", "both"}:
        sources.append(JsonCommunicationSource(DATA_DIR / "mock_slack_events.json"))

    if slack_source in {"real", "both"}:
        sources.append(RealSlackSource())

    sources.extend([
        JsonCommunicationSource(DATA_DIR / "mock_email_events.json"),
        JsonCommunicationSource(DATA_DIR / "mock_meeting_events.json"),
    ])
    return sources
