from app.models.communication_event import CommunicationEvent
from app.models.entities import ProjectEntity
from app.services.extraction.base import ExtractionProvider


class FallbackExtractionProvider(ExtractionProvider):
    def __init__(self, primary: ExtractionProvider, fallback: ExtractionProvider) -> None:
        self.primary = primary
        self.fallback = fallback
        self.mode = primary.mode
        self.version = f"{primary.version}_with_fallback"
        self.model_name = primary.model_name

    def extract(self, event: CommunicationEvent) -> list[ProjectEntity]:
        try:
            return self.primary.extract(event)
        except Exception:
            return self.fallback.extract(event)
