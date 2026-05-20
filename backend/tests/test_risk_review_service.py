from datetime import datetime, timezone

from app.models.entities import ProjectEntity
from app.models.enums import EntityStatus, EntityType, Severity
from app.services.risk_review_service import RiskReviewService


def entity(
    *,
    entity_id: str,
    title: str,
    summary: str,
    keywords: list[str],
) -> ProjectEntity:
    timestamp = datetime(2026, 5, 16, tzinfo=timezone.utc)
    return ProjectEntity(
        id=entity_id,
        entity_type=EntityType.RISK,
        title=title,
        summary=summary,
        status=EntityStatus.ACTIVE,
        severity=Severity.HIGH,
        confidence_score=0.8,
        owner="Maya",
        affected_roles=["mechanical_engineer"],
        created_at=timestamp,
        updated_at=timestamp,
        supporting_events=[f"event_{entity_id}"],
        keywords=keywords,
    )


def test_risk_review_returns_hardware_checks_without_openai(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    review = RiskReviewService().review(
        project="warehouse_robot_v2",
        phase="prototype",
        entities=[],
    )

    assert review.openai_configured is False
    assert len(review.checks) == 5
    assert {check.id for check in review.checks} >= {
        "tolerance_stackup",
        "physical_validation",
        "supplier_capability",
    }


def test_risk_review_marks_openai_available(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("AI_RISK_REVIEW_ENABLED", raising=False)

    review = RiskReviewService().review(
        project="warehouse_robot_v2",
        phase="prototype",
        entities=[],
    )

    assert review.openai_configured is True
    assert review.ai_followup_enabled is False
    assert "AI_RISK_REVIEW_ENABLED=true" in review.disabled_reason


def test_risk_review_marks_ai_followup_enabled(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AI_RISK_REVIEW_ENABLED", "true")

    review = RiskReviewService().review(
        project="warehouse_robot_v2",
        phase="prototype",
        entities=[],
    )

    assert review.openai_configured is True
    assert review.ai_followup_enabled is True
    assert review.disabled_reason is None


def test_risk_review_relates_checks_to_matching_project_entities(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    review = RiskReviewService().review(
        project="warehouse_robot_v2",
        phase="prototype",
        entities=[
            entity(
                entity_id="risk_tolerance",
                title="Motor mount tolerance is blocking assembly",
                summary="Current stackup leaves 2mm interference with the chassis rail.",
                keywords=["tolerance", "assembly", "cad"],
            ),
            entity(
                entity_id="risk_supplier",
                title="Supplier lead time increased to 3 weeks",
                summary="Bracket PO and supplier slot need confirmation.",
                keywords=["supplier", "lead time", "po"],
            ),
        ],
    )

    checks = {check.id: check for check in review.checks}
    assert "risk_tolerance" in checks["tolerance_stackup"].related_entity_ids
    assert "risk_supplier" in checks["supplier_capability"].related_entity_ids


class FakeResponses:
    def __init__(self) -> None:
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return type("Response", (), {"output_text": "Check stack-up and supplier capability before release."})()


class FakeOpenAI:
    instance = None

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key
        self.responses = FakeResponses()
        FakeOpenAI.instance = self


def test_answer_question_uses_structured_context(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    monkeypatch.setattr("openai.OpenAI", FakeOpenAI)

    answer = RiskReviewService().answer_question(
        project="warehouse_robot_v2",
        phase="prototype",
        entities=[
            entity(
                entity_id="risk_tolerance",
                title="Motor mount tolerance is blocking assembly",
                summary="Current stackup leaves 2mm interference with the chassis rail.",
                keywords=["tolerance", "assembly", "cad"],
            )
        ],
        question="What should we check before release?",
    )

    assert answer == "Check stack-up and supplier capability before release."
    assert FakeOpenAI.instance.api_key == "test-key"
    kwargs = FakeOpenAI.instance.responses.kwargs
    assert kwargs["model"] == "test-model"
    assert kwargs["reasoning"] == {"effort": "minimal"}
    assert "Motor mount tolerance is blocking assembly" in kwargs["input"][0]["content"]
