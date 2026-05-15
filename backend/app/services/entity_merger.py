from app.models.entities import ProjectEntity
from app.models.enums import EntityStatus, Severity


SEVERITY_RANK = {
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}


class EntityMerger:
    def merge(self, entities: list[ProjectEntity]) -> list[ProjectEntity]:
        merged: dict[str, ProjectEntity] = {}
        for entity in entities:
            existing = merged.get(entity.id)
            if not existing:
                merged[entity.id] = entity
                continue

            if entity.updated_at >= existing.updated_at:
                existing.summary = entity.summary
                existing.updated_at = entity.updated_at
                existing.status = entity.status
                existing.owner = entity.owner or existing.owner
                existing.resolved_at = entity.resolved_at or existing.resolved_at

            if SEVERITY_RANK[entity.severity] > SEVERITY_RANK[existing.severity]:
                existing.severity = entity.severity

            if existing.status != EntityStatus.RESOLVED and entity.status == EntityStatus.RESOLVED:
                existing.status = EntityStatus.RESOLVED
                existing.resolved_at = entity.resolved_at

            existing.confidence_score = max(existing.confidence_score, entity.confidence_score)
            existing.supporting_events = sorted(set(existing.supporting_events + entity.supporting_events))
            existing.affected_roles = sorted(set(existing.affected_roles + entity.affected_roles))
            existing.keywords = sorted(set(existing.keywords + entity.keywords))

        return sorted(merged.values(), key=lambda item: item.updated_at, reverse=True)
