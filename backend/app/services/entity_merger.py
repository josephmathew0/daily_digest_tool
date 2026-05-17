import re

from app.models.entities import ProjectEntity
from app.models.enums import EntityStatus, EntityType, Severity


# Entity merging turns message-level extractions into durable project state.
# Most of the complexity here is defensive: related updates should merge, but
# nearby topics such as bracket procurement and connector CAD should not collapse
# into one generic blocker.
SEVERITY_RANK = {
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}
KEYWORD_OVERLAP_THRESHOLD = 0.67
TITLE_OVERLAP_THRESHOLD = 0.55

COMPATIBLE_TYPES = {
    EntityType.ISSUE: {EntityType.ISSUE, EntityType.RISK, EntityType.DEPENDENCY, EntityType.MILESTONE},
    EntityType.RISK: {EntityType.ISSUE, EntityType.RISK, EntityType.DEPENDENCY, EntityType.ACTION_ITEM, EntityType.MILESTONE},
    EntityType.DEPENDENCY: {EntityType.ISSUE, EntityType.RISK, EntityType.DEPENDENCY, EntityType.ACTION_ITEM},
    EntityType.ACTION_ITEM: {EntityType.ACTION_ITEM, EntityType.DEPENDENCY},
    EntityType.DECISION: {EntityType.DECISION},
    EntityType.MILESTONE: {EntityType.MILESTONE, EntityType.RISK},
}

RESOLVED_SIGNALS = [
    "approved",
    "can resume",
    "closed",
    "fixed",
    "looks acceptable",
    "no longer blocking",
    "resolved",
    "testing can resume",
    "unblocked",
    "validation can resume",
    "validated",
]

ACTIVE_SIGNALS = [
    "pending",
    "remains blocked",
    "still at risk",
    "still blocked",
    "waiting on",
]

REGRESSION_SIGNALS = [
    "failed again",
    "reopened",
    "risk returned",
    "still failing",
]

DOMAIN_TERMS = {
    "assembly",
    "bom",
    "bracket",
    "cad",
    "clearance",
    "connector",
    "firmware",
    "inventory",
    "lead time",
    "motor mount",
    "pcb",
    "po",
    "procurement",
    "reliability",
    "supplier",
    "testing",
    "thermal",
    "tolerance",
    "validation",
    "vendor",
}

DOMAIN_GROUPS = {
    "mechanical_electrical": {
        "assembly",
        "cad",
        "clearance",
        "connector",
        "firmware",
        "motor mount",
        "pcb",
        "reliability",
        "testing",
        "thermal",
        "tolerance",
        "validation",
    },
    "procurement": {
        "bom",
        "bracket",
        "inventory",
        "lead time",
        "po",
        "procurement",
        "supplier",
        "vendor",
    },
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
        next_status = self._lifecycle_status(existing, entity)

        if entity.updated_at >= existing.updated_at:
            # Newer evidence becomes the displayed summary, while accumulated
            # supporting events and keywords are preserved below.
            existing.summary = entity.summary
            existing.updated_at = entity.updated_at
            existing.status = next_status
            existing.owner = entity.owner or existing.owner
            existing.resolved_at = entity.updated_at if next_status == EntityStatus.RESOLVED else None
            existing.entity_type = self._preferred_type(existing, entity)

        if SEVERITY_RANK[entity.severity] > SEVERITY_RANK[existing.severity]:
            existing.severity = entity.severity

        if entity.updated_at < existing.updated_at and next_status == EntityStatus.RESOLVED:
            existing.status = EntityStatus.RESOLVED
            existing.resolved_at = entity.resolved_at or entity.updated_at

        existing.confidence_score = max(existing.confidence_score, entity.confidence_score)
        existing.supporting_events = sorted(set(existing.supporting_events + entity.supporting_events))
        existing.affected_roles = sorted(set(existing.affected_roles + entity.affected_roles))
        existing.keywords = sorted(set(existing.keywords + entity.keywords))
        existing.created_at = min(existing.created_at, entity.created_at)

    def _find_related(self, entity: ProjectEntity, candidates: list[ProjectEntity]) -> ProjectEntity | None:
        for candidate in candidates:
            if not self._compatible_type(candidate.entity_type, entity.entity_type):
                continue
            if not self._domain_compatible(candidate, entity):
                continue
            # Resolution messages are often phrased differently from the
            # original issue, so domain overlap is allowed to bridge them.
            if self._is_resolution_update(entity) and self._domain_overlap(candidate, entity) >= 2:
                return candidate
            if self._keyword_overlap(candidate, entity) >= KEYWORD_OVERLAP_THRESHOLD:
                return candidate
            if self._title_overlap(candidate.title, entity.title) >= TITLE_OVERLAP_THRESHOLD:
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

    def _compatible_type(self, first: EntityType, second: EntityType) -> bool:
        return second in COMPATIBLE_TYPES.get(first, {first})

    def _lifecycle_status(self, existing: ProjectEntity, entity: ProjectEntity) -> EntityStatus:
        text = f"{entity.title} {entity.summary}".lower()
        if any(signal in text for signal in REGRESSION_SIGNALS):
            return EntityStatus.ACTIVE
        if any(signal in text for signal in ACTIVE_SIGNALS):
            # "Still blocked" should not accidentally resolve an existing item
            # even if the extractor labeled the new message as resolved.
            return entity.status if entity.status != EntityStatus.RESOLVED else existing.status
        if entity.status == EntityStatus.RESOLVED or any(signal in text for signal in RESOLVED_SIGNALS):
            return EntityStatus.RESOLVED
        return entity.status if entity.updated_at >= existing.updated_at else existing.status

    def _preferred_type(self, existing: ProjectEntity, entity: ProjectEntity) -> EntityType:
        if existing.entity_type == entity.entity_type:
            return existing.entity_type
        if EntityType.RISK in {existing.entity_type, entity.entity_type}:
            return EntityType.RISK
        if EntityType.DEPENDENCY in {existing.entity_type, entity.entity_type}:
            return EntityType.DEPENDENCY
        return existing.entity_type

    def _domain_compatible(self, first: ProjectEntity, second: ProjectEntity) -> bool:
        first_terms = self._domain_terms(first)
        second_terms = self._domain_terms(second)
        if not first_terms or not second_terms:
            return True
        first_group = self._dominant_domain_group(first_terms)
        second_group = self._dominant_domain_group(second_terms)
        if first_group and second_group and first_group != second_group:
            return False
        # Require at least one concrete engineering/procurement term in common
        # to avoid merging items just because both mention "risk" or "blocked".
        return bool(first_terms & second_terms)

    def _domain_terms(self, entity: ProjectEntity) -> set[str]:
        text = f"{entity.title} {entity.summary} {' '.join(entity.keywords)}".lower()
        return {term for term in DOMAIN_TERMS if term in text}

    def _domain_overlap(self, first: ProjectEntity, second: ProjectEntity) -> int:
        return len(self._domain_terms(first) & self._domain_terms(second))

    def _is_resolution_update(self, entity: ProjectEntity) -> bool:
        text = f"{entity.title} {entity.summary}".lower()
        return entity.status == EntityStatus.RESOLVED or any(signal in text for signal in RESOLVED_SIGNALS)

    def _dominant_domain_group(self, terms: set[str]) -> str | None:
        scores = {
            group: len(terms & group_terms)
            for group, group_terms in DOMAIN_GROUPS.items()
        }
        best_group, best_score = max(scores.items(), key=lambda item: item[1])
        if best_score == 0:
            return None
        tied_groups = [group for group, score in scores.items() if score == best_score]
        return best_group if len(tied_groups) == 1 else None
