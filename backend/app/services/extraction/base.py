from abc import ABC, abstractmethod

from app.models.communication_event import CommunicationEvent
from app.models.entities import ProjectEntity


class ExtractionProvider(ABC):
    mode: str
    version: str
    model_name: str | None = None

    @abstractmethod
    def extract(self, event: CommunicationEvent) -> list[ProjectEntity]:
        raise NotImplementedError
