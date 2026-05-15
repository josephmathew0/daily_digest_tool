from abc import ABC, abstractmethod

from app.models.communication_event import CommunicationEvent


class CommunicationSource(ABC):
    @abstractmethod
    def fetch_events(self) -> list[CommunicationEvent]:
        raise NotImplementedError
