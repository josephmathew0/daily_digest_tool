from openai import OpenAIError

from app.models.communication_event import CommunicationEvent
from app.models.entities import ProjectEntity
from app.services.extraction.base import ExtractionProvider
from app.services.extraction.openai_provider import OpenAIExtractionProvider
from app.services.extraction.rule_based_provider import RuleBasedExtractionProvider


class HybridExtractionProvider(ExtractionProvider):
    mode = "hybrid"
    version = "hybrid_rules_openai_v1"

    def __init__(self) -> None:
        self.rules = RuleBasedExtractionProvider()
        self.openai = OpenAIExtractionProvider()
        self.model_name = self.openai.model_name

    def extract(self, event: CommunicationEvent) -> list[ProjectEntity]:
        rule_entities = self.rules.extract(event)
        if not rule_entities:
            return []

        try:
            return self.openai.extract(event)
        except OpenAIError:
            return rule_entities
