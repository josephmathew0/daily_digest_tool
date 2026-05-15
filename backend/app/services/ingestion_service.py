from app.models.communication_event import CommunicationEvent
from app.services.ingestion.source_factory import build_sources


class IngestionService:
    def fetch_all(self) -> list[CommunicationEvent]:
        events: list[CommunicationEvent] = []
        for source in build_sources():
            events.extend(source.fetch_events())
        return sorted(events, key=lambda event: event.timestamp)
