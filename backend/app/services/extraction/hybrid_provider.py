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
        if self._rules_are_confident(rule_entities):
            return rule_entities

        try:
            # Hybrid mode spends LLM tokens only when rules cannot confidently
            # describe the event. If OpenAI fails, the rule result is still used.
            return self.openai.extract(event)
        except Exception:
            return rule_entities

    def _rules_are_confident(self, entities: list[ProjectEntity]) -> bool:
        return bool(entities) and all(entity.confidence_score >= 0.75 for entity in entities)
