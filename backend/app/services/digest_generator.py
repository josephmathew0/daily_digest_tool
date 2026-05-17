from collections import defaultdict

from app.models.digest import DigestItem, DigestResponse
from app.models.entities import ProjectEntity
from app.models.enums import EntityType
from app.services.relevance_engine import RelevanceEngine
from app.services.summary.factory import build_summary_provider


SECTION_NAMES = {
    EntityType.ISSUE: "Active Blockers",
    EntityType.RISK: "Risks",
    EntityType.DECISION: "Decisions",
    EntityType.ACTION_ITEM: "Action Items",
    EntityType.DEPENDENCY: "Dependencies",
    EntityType.MILESTONE: "Milestone Changes",
}


class DigestGenerator:
    def __init__(self) -> None:
        self.relevance = RelevanceEngine()
        self.summary_provider = build_summary_provider()

    def generate(self, *, project: str, user: dict, phase: str, entities: list[ProjectEntity]) -> DigestResponse:
        sections: dict[str, list[DigestItem]] = defaultdict(list)
        for entity in entities:
            score, reasons = self.relevance.score(entity, user["role"], phase)
            item = DigestItem(
                entity=entity,
                score=score,
                why_this_matters=reasons,
                latest_update=entity.summary,
            )
            sections[SECTION_NAMES[entity.entity_type]].append(item)

        sorted_sections = {
            name: sorted(items, key=lambda item: item.score, reverse=True)[:6]
            for name, items in sections.items()
        }
        return DigestResponse(
            project=project,
            user_id=user["id"],
            user_name=user["name"],
            role=user["role"],
            phase=phase,
            team_summary=self.summary_provider.team_summary(entities, phase),
            sections=sorted_sections,
        )
