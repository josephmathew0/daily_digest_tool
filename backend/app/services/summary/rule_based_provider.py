from collections import Counter

from app.models.entities import ProjectEntity
from app.models.enums import EntityStatus, EntityType, Severity
from app.services.summary.base import SummaryProvider


class RuleBasedSummaryProvider(SummaryProvider):
    mode = "rules"
    model_name = None

    def team_summary(self, entities: list[ProjectEntity], phase: str) -> str:
        # The rules summary is deterministic and free to run, so it is the safe
        # default when OpenAI credits or network access are unavailable.
        unresolved = [entity for entity in entities if entity.status != EntityStatus.RESOLVED]
        high_impact = [
            entity for entity in unresolved
            if entity.severity in {Severity.HIGH, Severity.CRITICAL}
        ]
        recently_resolved = [entity for entity in entities if entity.status == EntityStatus.RESOLVED]

        if not entities:
            return "No execution signals are currently tracked for this project."

        focus = self._focus_areas(high_impact or unresolved)
        blockers = [
            entity for entity in unresolved
            if entity.status == EntityStatus.BLOCKED or entity.entity_type == EntityType.DEPENDENCY
        ]

        sentence = (
            f"{len(unresolved)} active execution items are tracked for the {phase} phase. "
            f"{len(high_impact)} are high-impact risks or blockers"
        )
        if focus:
            sentence += f", concentrated around {focus}"
        sentence += "."

        if blockers:
            sentence += f" {len(blockers)} items are blocking or dependency-related and need follow-up."
        if recently_resolved:
            sentence += f" {len(recently_resolved)} recent items are resolved and should be monitored for regressions."

        return sentence

    def _focus_areas(self, entities: list[ProjectEntity]) -> str:
        keywords = Counter(keyword for entity in entities for keyword in entity.keywords)
        if not keywords:
            return ""
        top = [keyword for keyword, _ in keywords.most_common(3)]
        if len(top) == 1:
            return top[0]
        return ", ".join(top[:-1]) + f", and {top[-1]}"
