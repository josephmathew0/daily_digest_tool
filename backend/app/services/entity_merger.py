import re

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
            existing = merged.get(entity.id) or self._find_related(entity, list(merged.values()))
            if not existing:
                merged[entity.id] = entity
                continue

            self._merge_into(existing, entity)

        return sorted(merged.values(), key=lambda item: item.updated_at, reverse=True)

    def _merge_into(self, existing: ProjectEntity, entity: ProjectEntity) -> None:
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

    def _find_related(self, entity: ProjectEntity, candidates: list[ProjectEntity]) -> ProjectEntity | None:
        for candidate in candidates:
            if candidate.entity_type != entity.entity_type:
                continue
            if self._keyword_overlap(candidate, entity) >= 0.5:
                return candidate
            if self._title_overlap(candidate.title, entity.title) >= 0.55:
                return candidate
        return None

    def _keyword_overlap(self, first: ProjectEntity, second: ProjectEntity) -> float:
        first_keywords = set(first.keywords)
        second_keywords = set(second.keywords)
        if not first_keywords or not second_keywords:
            return 0.0
        return len(first_keywords & second_keywords) / min(len(first_keywords), len(second_keywords))

    def _title_overlap(self, first: str, second: str) -> float:
        first_words = self._important_words(first)
        second_words = self._important_words(second)
        if not first_words or not second_words:
            return 0.0
        return len(first_words & second_words) / min(len(first_words), len(second_words))

    def _important_words(self, text: str) -> set[str]:
        stopwords = {
            "a", "an", "and", "are", "as", "at", "by", "for", "from", "in", "is",
            "it", "of", "on", "or", "the", "to", "with", "over", "under",
        }
        words = re.findall(r"[a-z0-9]+", text.lower())
        return {word for word in words if len(word) > 2 and word not in stopwords}
