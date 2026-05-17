from datetime import datetime, timezone

from app.models.entities import ProjectEntity
from app.models.enums import EntityStatus, EntityType, Severity
from app.services.digest_generator import DigestGenerator


def risk(entity_id: str, status: EntityStatus, updated_hour: int) -> ProjectEntity:
    timestamp = datetime(2026, 5, 16, updated_hour, tzinfo=timezone.utc)
    return ProjectEntity(
        id=entity_id,
        entity_type=EntityType.RISK,
        title=entity_id,
        summary=f"{entity_id} summary",
        status=status,
        severity=Severity.HIGH,
        confidence_score=0.8,
        owner="Alex",
        affected_roles=["mechanical_engineer"],
        created_at=timestamp,
        updated_at=timestamp,
        resolved_at=timestamp if status == EntityStatus.RESOLVED else None,
        supporting_events=[entity_id],
        keywords=["assembly"],
    )


def test_digest_orders_unresolved_items_before_resolved_items(monkeypatch):
    monkeypatch.setattr(
        "app.services.digest_generator.build_summary_provider",
        lambda: type("Summary", (), {"team_summary": lambda self, entities, phase: "Summary"})(),
    )
    user = {"id": "maya", "name": "Maya Chen", "role": "mechanical_engineer"}
    digest = DigestGenerator().generate(
        project="warehouse_robot_v2",
        user=user,
        phase="prototype",
        entities=[
            risk("resolved_high_score", EntityStatus.RESOLVED, 12),
            risk("blocked_lower_score", EntityStatus.BLOCKED, 9),
            risk("pending_middle", EntityStatus.PENDING, 10),
        ],
    )

    section = digest.sections["Risks"]

    assert [item.entity.status for item in section] == [
        EntityStatus.BLOCKED,
        EntityStatus.PENDING,
        EntityStatus.RESOLVED,
    ]
