from app.models.communication_event import CommunicationEvent
from app.models.entities import ProjectEntity
from app.database.repository import (
    event_hash,
    get_cached_extraction,
    replace_project_entities,
    save_extraction,
)
from app.services.entity_merger import EntityMerger
from app.services.extraction.factory import build_extraction_provider
from app.services.relevance_filter import RelevanceFilter


class StateTracker:
    def __init__(self) -> None:
        self.extraction_provider = build_extraction_provider()
        self.relevance_filter = RelevanceFilter()
        self.merger = EntityMerger()
        self.last_stats = {"extracted": 0, "reused": 0, "skipped_irrelevant": 0}

    def build_entities(self, events: list[CommunicationEvent]) -> list[ProjectEntity]:
        extracted: list[ProjectEntity] = []
        stats = {"extracted": 0, "reused": 0, "skipped_irrelevant": 0}
        for event in events:
            if not self.relevance_filter.is_relevant(event):
                stats["skipped_irrelevant"] += 1
                continue

            next_hash = event_hash(event)
            cached = get_cached_extraction(
                event.id,
                next_hash,
                self.extraction_provider.mode,
                self.extraction_provider.version,
                self.extraction_provider.model_name,
            )
            if cached is not None:
                extracted.extend(cached)
                stats["reused"] += 1
                continue

            entities = self.extraction_provider.extract(event)
            save_extraction(
                event.id,
                next_hash,
                entities,
                self.extraction_provider.mode,
                self.extraction_provider.version,
                self.extraction_provider.model_name,
            )
            extracted.extend(entities)
            stats["extracted"] += 1

        self.last_stats = stats
        merged = self.merger.merge(extracted)
        for project in sorted({event.project for event in events}):
            replace_project_entities(
                project,
                [
                    entity for entity in merged
                    if any(
                        event.id in entity.supporting_events and event.project == project
                        for event in events
                    )
                ],
            )
        return merged
