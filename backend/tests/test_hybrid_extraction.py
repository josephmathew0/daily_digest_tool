from datetime import datetime, timezone

from app.models.communication_event import CommunicationEvent
from app.models.entities import ProjectEntity
from app.models.enums import EntityStatus, EntityType, Severity, SourceType
from app.services.extraction.base import ExtractionProvider
from app.services.extraction.hybrid_provider import HybridExtractionProvider
from app.services.extraction.openai_provider import ExtractionResponse, ExtractedEntity, OpenAIExtractionProvider


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


class FakeResponses:
    def __init__(self, parsed: ExtractionResponse) -> None:
        self.parsed = parsed
        self.kwargs = None

    def parse(self, **kwargs):
        self.kwargs = kwargs
        return type("Response", (), {"output_parsed": self.parsed})()


class FakeOpenAIClient:
    def __init__(self, parsed: ExtractionResponse) -> None:
        self.responses = FakeResponses(parsed)


def test_openai_extraction_provider_uses_responses_api_for_ambiguous_resolution():
    parsed = ExtractionResponse(
        is_relevant=True,
        entities=[
            ExtractedEntity(
                entity_type=EntityType.RISK,
                title="PCB thermal risk",
                summary="Thermal chamber run looks acceptable after firmware current limiting; EVT reliability validation can resume.",
                status=EntityStatus.RESOLVED,
                severity=Severity.MEDIUM,
                confidence_score=0.86,
                owner="Alex",
                affected_roles=["electrical_engineer"],
                keywords=["pcb", "thermal", "firmware"],
            )
        ],
    )
    provider = OpenAIExtractionProvider.__new__(OpenAIExtractionProvider)
    provider.model_name = "test-model"
    provider.client = FakeOpenAIClient(parsed)

    result = provider.extract(
        CommunicationEvent(
            id="thermal_resolution",
            source_type=SourceType.SLACK,
            source_ref="#warehouse-robot-v2",
            author_name="Alex",
            text="The latest thermal chamber run looks acceptable after firmware current limiting. Alex says EVT reliability validation can resume tomorrow.",
            timestamp=datetime(2026, 5, 17, tzinfo=timezone.utc),
            project="warehouse_robot_v2",
        )
    )

    assert result[0].status == EntityStatus.RESOLVED
    assert result[0].resolved_at == datetime(2026, 5, 17, tzinfo=timezone.utc)
    assert result[0].keywords == ["firmware", "pcb", "thermal"]
    assert provider.client.responses.kwargs["text_format"] == ExtractionResponse
    assert provider.client.responses.kwargs["reasoning"] == {"effort": "minimal"}
    assert provider.client.responses.kwargs["max_output_tokens"] == 1200
