from app.models.communication_event import CommunicationEvent
from app.services.ingestion.source_factory import build_sources


class IngestionService:
    def fetch_all(self) -> list[CommunicationEvent]:
        events: list[CommunicationEvent] = []
        for source in build_sources():
            # Sources normalize Slack, Gmail, meetings, and mock JSON into the
            # same CommunicationEvent model before downstream processing.
            events.extend(source.fetch_events())
        return sorted(events, key=lambda event: event.timestamp)
