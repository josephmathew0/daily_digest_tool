from datetime import datetime, timezone

from app.models.entities import ProjectEntity
from app.models.enums import EntityStatus, EntityType, Severity
from app.models.project_memory import ProjectMemory


class MemoryManager:
    def build(self, project: str, entities: list[ProjectEntity]) -> ProjectMemory:
        active = [
            entity for entity in entities
            if entity.status in {EntityStatus.ACTIVE, EntityStatus.BLOCKED, EntityStatus.PENDING}
        ]
        recent = [
            entity for entity in entities
            if entity.status == EntityStatus.RESOLVED or entity.entity_type == EntityType.MILESTONE
        ][:10]
        long_term = [
            entity for entity in entities
            if entity.entity_type == EntityType.DECISION or entity.severity in {Severity.HIGH, Severity.CRITICAL}
        ][:15]
        return ProjectMemory(project=project, active_context=active, recent_changes=recent, long_term_memory=long_term)
