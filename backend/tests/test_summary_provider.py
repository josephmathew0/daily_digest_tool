from datetime import datetime, timezone

from app.models.entities import ProjectEntity
from app.models.enums import EntityStatus, EntityType, Severity
from app.services.summary.base import SummaryProvider
from app.services.summary.fallback_provider import FallbackSummaryProvider
from app.services.summary.openai_provider import OpenAISummaryProvider
from app.services.summary.rule_based_provider import RuleBasedSummaryProvider


def test_rule_based_summary_mentions_focus_and_blockers():
    entity = project_entity()

    summary = RuleBasedSummaryProvider().team_summary([entity], "EVT")

    assert "1 active execution items" in summary
    assert "1 are high-impact" in summary
    assert "pcb" in summary
    assert "blocking or dependency-related" in summary


def project_entity() -> ProjectEntity:
    return ProjectEntity(
        id="risk_thermal",
        entity_type=EntityType.RISK,
        title="PCB thermal risk",
        summary="PCB thermal rise remains above EVT target.",
        status=EntityStatus.BLOCKED,
        severity=Severity.HIGH,
        confidence_score=0.9,
        owner="Alex",
        affected_roles=["electrical_engineer"],
        created_at=datetime(2026, 5, 16, tzinfo=timezone.utc),
        updated_at=datetime(2026, 5, 16, tzinfo=timezone.utc),
        supporting_events=["event_1"],
        keywords=["pcb", "thermal"],
    )


class FailingSummaryProvider(SummaryProvider):
    mode = "openai"
    model_name = "test-model"

    def team_summary(self, entities: list[ProjectEntity], phase: str) -> str:
        raise RuntimeError("OpenAI unavailable")


def test_summary_fallback_uses_rules_when_openai_fails():
    entity = project_entity()

    summary = FallbackSummaryProvider(
        FailingSummaryProvider(),
        RuleBasedSummaryProvider(),
    ).team_summary([entity], "EVT")

    assert "1 active execution items" in summary
    assert "thermal" in summary


class FakeResponses:
    def __init__(self) -> None:
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return type("Response", (), {"output_text": "Thermal risk is blocking EVT readiness."})()


class FakeClient:
    def __init__(self) -> None:
        self.responses = FakeResponses()


def test_openai_summary_provider_uses_responses_api_without_raw_events():
    provider = OpenAISummaryProvider.__new__(OpenAISummaryProvider)
    provider.model_name = "test-model"
    provider.client = FakeClient()

    summary = provider.team_summary([project_entity()], "EVT")

    assert summary == "Thermal risk is blocking EVT readiness."
    assert provider.client.responses.kwargs["model"] == "test-model"
    assert provider.client.responses.kwargs["max_output_tokens"] == 800
    assert provider.client.responses.kwargs["reasoning"] == {"effort": "minimal"}
    prompt = provider.client.responses.kwargs["input"][0]["content"]
    assert "PCB thermal risk" in prompt
    assert "event_1" not in prompt
