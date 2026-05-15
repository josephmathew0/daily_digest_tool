from app.models.entities import ProjectEntity
from app.models.enums import EntityType


class DependencyEngine:
    def find_dependencies(self, entities: list[ProjectEntity]) -> list[ProjectEntity]:
        return [entity for entity in entities if entity.entity_type == EntityType.DEPENDENCY]
