from datetime import datetime, timezone

from app.models.entities import ProjectEntity
from app.models.enums import EntityStatus, EntityType, ReadinessStatus, Severity
from app.models.readiness import BuildReadinessResponse, ReadinessItem


class ReadinessService:
    """Summarize project entities into a hardware milestone readiness view."""

    def assess(self, *, project: str, phase: str, entities: list[ProjectEntity]) -> BuildReadinessResponse:
        blockers = self._blockers(entities)
        risks = self._risks(entities, blockers)
        resolved = self._resolved(entities)
        missing_confirmations = self._missing_confirmations(entities)
        status = self._status(blockers, risks)

        return BuildReadinessResponse(
            project=project,
            phase=phase,
            status=status,
            summary=self._summary(phase, status, blockers, risks, missing_confirmations),
            blockers=[self._item(entity) for entity in blockers],
            risks=[self._item(entity) for entity in risks],
            resolved=[self._item(entity) for entity in resolved],
            missing_confirmations=[self._item(entity) for entity in missing_confirmations],
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    def _blockers(self, entities: list[ProjectEntity]) -> list[ProjectEntity]:
        return self._top(
            [
                entity for entity in entities
                if entity.status == EntityStatus.BLOCKED
                or (
                    entity.entity_type == EntityType.DEPENDENCY
                    and entity.status != EntityStatus.RESOLVED
                )
                or (
                    entity.entity_type == EntityType.ISSUE
                    and entity.status != EntityStatus.RESOLVED
                    and entity.severity in {Severity.HIGH, Severity.CRITICAL}
                )
            ]
        )

    def _risks(self, entities: list[ProjectEntity], blockers: list[ProjectEntity]) -> list[ProjectEntity]:
        blocker_ids = {entity.id for entity in blockers}
        return self._top(
            [
                entity for entity in entities
                if entity.id not in blocker_ids
                and entity.status != EntityStatus.RESOLVED
                and entity.entity_type in {EntityType.RISK, EntityType.MILESTONE}
                and entity.severity in {Severity.HIGH, Severity.CRITICAL}
            ]
        )

    def _resolved(self, entities: list[ProjectEntity]) -> list[ProjectEntity]:
        return self._top(
            [
                entity for entity in entities
                if entity.status == EntityStatus.RESOLVED
                and entity.entity_type in {
                    EntityType.ISSUE,
                    EntityType.RISK,
                    EntityType.DEPENDENCY,
                    EntityType.ACTION_ITEM,
                    EntityType.MILESTONE,
                }
            ]
        )

    def _missing_confirmations(self, entities: list[ProjectEntity]) -> list[ProjectEntity]:
        confirmation_terms = [
            "confirm",
            "validate",
            "waiting on",
            "needs",
            "pending",
            "must",
            "by friday",
            "owner:",
        ]
        return self._top(
            [
                entity for entity in entities
                if entity.status != EntityStatus.RESOLVED
                and entity.entity_type in {EntityType.ACTION_ITEM, EntityType.DEPENDENCY, EntityType.DECISION}
                and any(term in self._text(entity) for term in confirmation_terms)
            ]
        )

    def _status(
        self,
        blockers: list[ProjectEntity],
        risks: list[ProjectEntity],
    ) -> ReadinessStatus:
        if blockers:
            return ReadinessStatus.BLOCKED
        if risks:
            return ReadinessStatus.AT_RISK
        return ReadinessStatus.READY

    def _summary(
        self,
        phase: str,
        status: ReadinessStatus,
        blockers: list[ProjectEntity],
        risks: list[ProjectEntity],
        missing_confirmations: list[ProjectEntity],
    ) -> str:
        label = phase.replace("_", " ").title()
        if status == ReadinessStatus.BLOCKED:
            return (
                f"{label} readiness is blocked by {len(blockers)} item(s). "
                f"{len(risks)} high-impact risk(s) and "
                f"{len(missing_confirmations)} missing confirmation(s) need review."
            )
        if status == ReadinessStatus.AT_RISK:
            return (
                f"{label} readiness is at risk. "
                f"{len(risks)} high-impact risk(s) should be resolved before proceeding."
            )
        return f"{label} readiness looks ready based on current tracked project entities."

    def _item(self, entity: ProjectEntity) -> ReadinessItem:
        return ReadinessItem(
            entity_id=entity.id,
            title=entity.title,
            summary=entity.summary,
            status=entity.status.value,
            severity=entity.severity.value,
            updated_at=entity.updated_at.isoformat(),
            supporting_events=entity.supporting_events,
        )

    def _top(self, entities: list[ProjectEntity], limit: int = 5) -> list[ProjectEntity]:
        return sorted(entities, key=self._sort_key)[:limit]

    def _sort_key(self, entity: ProjectEntity) -> tuple[int, int, float]:
        status_rank = {
            EntityStatus.BLOCKED: 0,
            EntityStatus.PENDING: 1,
            EntityStatus.ACTIVE: 2,
            EntityStatus.RESOLVED: 3,
        }
        severity_rank = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1,
            Severity.MEDIUM: 2,
            Severity.LOW: 3,
        }
        return (
            status_rank.get(entity.status, 2),
            severity_rank.get(entity.severity, 3),
            -entity.updated_at.timestamp(),
        )

    def _text(self, entity: ProjectEntity) -> str:
        return f"{entity.title} {entity.summary} {' '.join(entity.keywords)}".lower()
