from datetime import datetime, timezone

from app.models.entities import ProjectEntity
from app.models.enums import EntityStatus, EntityType, Severity
from app.services.procurement_service import ProcurementService


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
        owner="Priya",
        affected_roles=["supply_chain"],
        created_at=timestamp,
        updated_at=timestamp,
        supporting_events=[f"event_{entity_id}"],
        keywords=keywords,
    )


def test_procurement_forecast_suggests_matching_items(monkeypatch):
    monkeypatch.delenv("GMAIL_SEND_ENABLED", raising=False)
    forecast = ProcurementService().forecast(
        project="warehouse_robot_v2",
        phase="prototype",
        entities=[
            entity(
                entity_id="risk_bracket",
                title="Supplier says aluminum bracket lead time increased",
                summary="Bracket PO and supplier slot need confirmation.",
                keywords=["bracket", "supplier", "po"],
            ),
            entity(
                entity_id="risk_connector",
                title="Connector clearance depends on final motor mount CAD",
                summary="Harness route and connector envelope need validation.",
                keywords=["connector", "harness", "clearance"],
            ),
        ],
    )

    items = {item.id: item for item in forecast.items}
    assert forecast.gmail_send_configured is False
    assert "prototype_brackets" in items
    assert "connector_harness_samples" in items
    assert items["prototype_brackets"].related_entity_ids == ["risk_bracket"]


def test_procurement_forecast_only_returns_related_items():
    forecast = ProcurementService().forecast(
        project="warehouse_robot_v2",
        phase="prototype",
        entities=[],
    )

    assert forecast.items == []


def test_procurement_forecast_marks_gmail_send_configured(monkeypatch):
    monkeypatch.setenv("GMAIL_SEND_ENABLED", "true")

    forecast = ProcurementService().forecast(
        project="warehouse_robot_v2",
        phase="prototype",
        entities=[],
    )

    assert forecast.gmail_send_configured is True


def test_procurement_draft_email_disabled_without_openai(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    response = ProcurementService().draft_email(
        project="warehouse_robot_v2",
        phase="prototype",
        item_id="prototype_brackets",
        recipient_email="vendor@example.com",
        entities=[
            entity(
                entity_id="risk_bracket",
                title="Supplier says aluminum bracket lead time increased",
                summary="Bracket PO and supplier slot need confirmation.",
                keywords=["bracket", "supplier", "po"],
            ),
        ],
    )

    assert response.enabled is False
    assert "OPENAI_API_KEY" in response.disabled_reason


def test_procurement_draft_email_uses_forecast_item(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def fake_openai_draft(self, **kwargs):
        assert kwargs["item"].id == "prototype_brackets"
        assert kwargs["related_entities"][0].id == "risk_bracket"
        return "RFQ for prototype brackets", "Please quote prototype brackets."

    monkeypatch.setattr(ProcurementService, "_openai_draft", fake_openai_draft)

    response = ProcurementService().draft_email(
        project="warehouse_robot_v2",
        phase="prototype",
        item_id="prototype_brackets",
        recipient_email="vendor@example.com",
        entities=[
            entity(
                entity_id="risk_bracket",
                title="Supplier says aluminum bracket lead time increased",
                summary="Bracket PO and supplier slot need confirmation.",
                keywords=["bracket", "supplier", "po"],
            ),
        ],
    )

    assert response.enabled is True
    assert response.recipient_email == "vendor@example.com"
    assert response.subject == "RFQ for prototype brackets"
    assert response.body == "Please quote prototype brackets."


def test_procurement_draft_email_rejects_unmatched_item(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    response = ProcurementService().draft_email(
        project="warehouse_robot_v2",
        phase="prototype",
        item_id="unknown_item",
        recipient_email="vendor@example.com",
        entities=[],
    )

    assert response.enabled is False
    assert "no longer predicted" in response.disabled_reason


def test_procurement_send_email_disabled_by_default(monkeypatch):
    monkeypatch.delenv("GMAIL_SEND_ENABLED", raising=False)

    response = ProcurementService().send_email(
        recipient_email="vendor@example.com",
        subject="RFQ",
        body="Please quote parts.",
    )

    assert response.sent is False
    assert "GMAIL_SEND_ENABLED=true" in response.disabled_reason


def test_procurement_send_email_uses_gmail_sender(monkeypatch):
    monkeypatch.setenv("GMAIL_SEND_ENABLED", "true")

    class FakeSender:
        def send(self, *, recipient_email: str, subject: str, body: str) -> str:
            assert recipient_email == "vendor@example.com"
            assert subject == "RFQ"
            assert body == "Please quote parts."
            return "gmail-message-1"

    monkeypatch.setattr("app.services.procurement_service.GmailSender", FakeSender)

    response = ProcurementService().send_email(
        recipient_email="vendor@example.com",
        subject="RFQ",
        body="Please quote parts.",
    )

    assert response.sent is True
    assert response.message_id == "gmail-message-1"
