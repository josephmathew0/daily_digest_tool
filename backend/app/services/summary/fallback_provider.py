from app.models.entities import ProjectEntity
from app.services.summary.base import SummaryProvider


class FallbackSummaryProvider(SummaryProvider):
    def __init__(self, primary: SummaryProvider, fallback: SummaryProvider) -> None:
        self.primary = primary
        self.fallback = fallback
        self.mode = f"{primary.mode}_with_fallback"
        self.model_name = primary.model_name

    def team_summary(self, entities: list[ProjectEntity], phase: str) -> str:
        try:
            return self.primary.team_summary(entities, phase)
        except Exception:
            return self.fallback.team_summary(entities, phase)
