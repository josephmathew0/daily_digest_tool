from app.models.communication_event import CommunicationEvent
from app.models.entities import ProjectEntity
from app.services.entity_merger import EntityMerger
from app.services.extractor import Extractor


class StateTracker:
    def __init__(self) -> None:
        self.extractor = Extractor()
        self.merger = EntityMerger()

    def build_entities(self, events: list[CommunicationEvent]) -> list[ProjectEntity]:
        extracted: list[ProjectEntity] = []
        for event in events:
            extracted.extend(self.extractor.extract(event))
        return self.merger.merge(extracted)
