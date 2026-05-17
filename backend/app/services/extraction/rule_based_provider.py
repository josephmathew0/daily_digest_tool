from app.models.communication_event import CommunicationEvent
from app.models.entities import ProjectEntity
from app.services.extraction.base import ExtractionProvider
from app.services.extractor import Extractor


class RuleBasedExtractionProvider(ExtractionProvider):
    mode = "rules"
    version = "rules_v1"
    model_name = None

    def __init__(self) -> None:
        self.extractor = Extractor()

    def extract(self, event: CommunicationEvent) -> list[ProjectEntity]:
        return self.extractor.extract(event)
