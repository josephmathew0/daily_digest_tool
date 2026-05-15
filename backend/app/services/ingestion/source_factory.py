from pathlib import Path

from app.services.ingestion.base_source import CommunicationSource
from app.services.ingestion.json_source import JsonCommunicationSource


DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def build_sources() -> list[CommunicationSource]:
    return [
        JsonCommunicationSource(DATA_DIR / "mock_slack_events.json"),
        JsonCommunicationSource(DATA_DIR / "mock_email_events.json"),
        JsonCommunicationSource(DATA_DIR / "mock_meeting_events.json"),
    ]
