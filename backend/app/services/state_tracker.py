from app.models.communication_event import CommunicationEvent
from app.models.entities import ProjectEntity
from app.database.repository import event_hash, get_cached_extraction, save_extraction
from app.services.entity_merger import EntityMerger
from app.services.extractor import Extractor


EXTRACTION_MODE = "rules"
EXTRACTOR_VERSION = "rules_v1"


class StateTracker:
    def __init__(self) -> None:
        self.extractor = Extractor()
        self.merger = EntityMerger()
        self.last_stats = {"extracted": 0, "reused": 0}

    def build_entities(self, events: list[CommunicationEvent]) -> list[ProjectEntity]:
        extracted: list[ProjectEntity] = []
        stats = {"extracted": 0, "reused": 0}
        for event in events:
            next_hash = event_hash(event)
            cached = get_cached_extraction(
                event.id,
                next_hash,
                EXTRACTION_MODE,
                EXTRACTOR_VERSION,
            )
            if cached is not None:
                extracted.extend(cached)
                stats["reused"] += 1
                continue

            entities = self.extractor.extract(event)
            save_extraction(
                event.id,
                next_hash,
                entities,
                EXTRACTION_MODE,
                EXTRACTOR_VERSION,
            )
            extracted.extend(entities)
            stats["extracted"] += 1

        self.last_stats = stats
        return self.merger.merge(extracted)
