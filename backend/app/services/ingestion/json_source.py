import json
from pathlib import Path

from app.models.communication_event import CommunicationEvent
from app.services.ingestion.base_source import CommunicationSource


class JsonCommunicationSource(CommunicationSource):
    def __init__(self, path: Path):
        self.path = path

    def fetch_events(self) -> list[CommunicationEvent]:
        payload = json.loads(self.path.read_text())
        return [CommunicationEvent.model_validate(item) for item in payload]
