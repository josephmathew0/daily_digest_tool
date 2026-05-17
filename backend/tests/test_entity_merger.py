from datetime import datetime, timezone

from app.models.entities import ProjectEntity
from app.models.enums import EntityStatus, EntityType, Severity
from app.services.entity_merger import EntityMerger


def make_entity(
    *,
    entity_id: str,
    title: str,
    summary: str,
    keywords: list[str],
    event_id: str,
    updated_hour: int,
    status: EntityStatus = EntityStatus.ACTIVE,
) -> ProjectEntity:
    timestamp = datetime(2026, 5, 16, updated_hour, tzinfo=timezone.utc)
    return ProjectEntity(
        id=entity_id,
        entity_type=EntityType.RISK,
        title=title,
        summary=summary,
        status=status,
        severity=Severity.HIGH,
        confidence_score=0.8,
        owner="Alex",
        affected_roles=["electrical_engineer"],
        created_at=timestamp,
        updated_at=timestamp,
        resolved_at=timestamp if status == EntityStatus.RESOLVED else None,
        supporting_events=[event_id],
        keywords=keywords,
    )


def test_merges_related_entities_with_keyword_overlap():
    first = make_entity(
        entity_id="risk_a",
        title="PCB thermal rise is 12C over target",
        summary="PCB thermal rise is 12C over target during drive cycle.",
        keywords=["pcb", "thermal", "firmware"],
        event_id="event_1",
        updated_hour=9,
    )
    second = make_entity(
        entity_id="risk_b",
        title="PCB thermal instability remains an EVT risk",
        summary="Firmware tuning reduced thermal rise but EVT reliability remains at risk.",
        keywords=["pcb", "thermal", "firmware"],
        event_id="event_2",
        updated_hour=10,
    )

    merged = EntityMerger().merge([first, second])

    assert len(merged) == 1
    assert merged[0].id == "risk_a"
    assert merged[0].summary == second.summary
    assert merged[0].supporting_events == ["event_1", "event_2"]


def test_keeps_unrelated_entities_separate():
    thermal = make_entity(
        entity_id="risk_thermal",
        title="PCB thermal risk",
        summary="PCB thermal rise is above EVT target.",
        keywords=["pcb", "thermal"],
        event_id="event_1",
        updated_hour=9,
    )
    bracket = make_entity(
        entity_id="risk_bracket",
        title="Bracket lead time risk",
        summary="Supplier bracket lead time increased to 3 weeks.",
        keywords=["bracket", "lead time", "vendor"],
        event_id="event_2",
        updated_hour=10,
    )

    merged = EntityMerger().merge([thermal, bracket])

    assert len(merged) == 2
