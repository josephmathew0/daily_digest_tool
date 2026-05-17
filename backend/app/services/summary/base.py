from abc import ABC, abstractmethod

from app.models.entities import ProjectEntity


class SummaryProvider(ABC):
    mode: str
    model_name: str | None = None

    @abstractmethod
    def team_summary(self, entities: list[ProjectEntity], phase: str) -> str:
        raise NotImplementedError
