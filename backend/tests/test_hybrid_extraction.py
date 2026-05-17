from datetime import datetime, timezone

from app.models.communication_event import CommunicationEvent
from app.models.entities import ProjectEntity
from app.models.enums import EntityStatus, EntityType, Severity, SourceType
from app.services.extraction.base import ExtractionProvider
from app.services.extraction.hybrid_provider import HybridExtractionProvider


def event() -> CommunicationEvent:
    return CommunicationEvent(
        id="event_1",
        source_type=SourceType.SLACK,
        source_ref="#warehouse-robot-v2",
        author_name="Alex",
        text="Thermal concern may affect EVT reliability.",
        timestamp=datetime(2026, 5, 16, tzinfo=timezone.utc),
        project="warehouse_robot_v2",
    )


def entity(confidence_score: float) -> ProjectEntity:
    now = datetime(2026, 5, 16, tzinfo=timezone.utc)
    return ProjectEntity(
        id=f"risk_{confidence_score}",
        entity_type=EntityType.RISK,
        title="Thermal concern",
        summary="Thermal concern may affect EVT reliability.",
        status=EntityStatus.ACTIVE,
        severity=Severity.MEDIUM,
        confidence_score=confidence_score,
        owner="Alex",
        affected_roles=["electrical_engineer"],
        created_at=now,
        updated_at=now,
        supporting_events=["event_1"],
        keywords=["thermal"],
    )


class FakeProvider(ExtractionProvider):
    mode = "fake"
    version = "fake_v1"

    def __init__(self, entities: list[ProjectEntity]) -> None:
        self.entities = entities
        self.calls = 0

    def extract(self, event: CommunicationEvent) -> list[ProjectEntity]:
        self.calls += 1
        return self.entities


def hybrid(rules: FakeProvider, openai: FakeProvider) -> HybridExtractionProvider:
    provider = HybridExtractionProvider.__new__(HybridExtractionProvider)
    provider.rules = rules
    provider.openai = openai
    provider.model_name = "test-model"
    return provider


def test_hybrid_skips_openai_when_rules_are_confident():
    rules = FakeProvider([entity(0.9)])
    openai = FakeProvider([entity(0.95)])

    result = hybrid(rules, openai).extract(event())

    assert result == rules.entities
    assert rules.calls == 1
    assert openai.calls == 0


def test_hybrid_calls_openai_when_rules_are_uncertain():
    rules = FakeProvider([entity(0.55)])
    openai = FakeProvider([entity(0.95)])

    result = hybrid(rules, openai).extract(event())

    assert result == openai.entities
    assert rules.calls == 1
    assert openai.calls == 1
