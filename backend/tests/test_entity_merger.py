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
    entity_type: EntityType = EntityType.RISK,
) -> ProjectEntity:
    timestamp = datetime(2026, 5, 16, updated_hour, tzinfo=timezone.utc)
    return ProjectEntity(
        id=entity_id,
        entity_type=entity_type,
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


def test_resolved_update_marks_existing_related_risk_resolved():
    original = make_entity(
        entity_id="risk_thermal",
        title="PCB thermal risk",
        summary="PCB thermal rise is above EVT target and reliability is at risk.",
        keywords=["pcb", "thermal", "firmware"],
        event_id="event_1",
        updated_hour=9,
        status=EntityStatus.BLOCKED,
    )
    resolved = make_entity(
        entity_id="issue_thermal_resolved",
        title="PCB thermal issue is resolved",
        summary="PCB thermal issue is resolved after firmware current limiting. EVT reliability validation can resume.",
        keywords=["pcb", "thermal", "firmware"],
        event_id="event_2",
        updated_hour=11,
        status=EntityStatus.RESOLVED,
        entity_type=EntityType.ISSUE,
    )

    merged = EntityMerger().merge([original, resolved])

    assert len(merged) == 1
    assert merged[0].entity_type == EntityType.RISK
    assert merged[0].status == EntityStatus.RESOLVED
    assert merged[0].resolved_at == resolved.updated_at
    assert merged[0].summary == resolved.summary
    assert merged[0].supporting_events == ["event_1", "event_2"]


def test_still_blocked_update_does_not_mark_existing_risk_resolved():
    original = make_entity(
        entity_id="risk_connector",
        title="Connector clearance is blocked",
        summary="Connector clearance is blocked by motor mount CAD.",
        keywords=["connector", "motor mount", "cad"],
        event_id="event_1",
        updated_hour=9,
        status=EntityStatus.BLOCKED,
    )
    still_blocked = make_entity(
        entity_id="risk_connector_later",
        title="Connector clearance remains blocked",
        summary="Connector clearance still blocked until the revised motor mount CAD is validated.",
        keywords=["connector", "motor mount", "cad"],
        event_id="event_2",
        updated_hour=11,
        status=EntityStatus.BLOCKED,
    )

    merged = EntityMerger().merge([original, still_blocked])

    assert len(merged) == 1
    assert merged[0].status == EntityStatus.BLOCKED
    assert merged[0].resolved_at is None
    assert merged[0].summary == still_blocked.summary


def test_milestone_resolution_can_close_related_risk():
    original = make_entity(
        entity_id="risk_thermal",
        title="PCB thermal risk",
        summary="PCB thermal rise is above EVT target and reliability is at risk.",
        keywords=["pcb", "thermal", "firmware"],
        event_id="event_1",
        updated_hour=9,
        status=EntityStatus.BLOCKED,
    )
    resolved_milestone = make_entity(
        entity_id="milestone_thermal_resolved",
        title="EVT reliability validation can resume",
        summary="PCB thermal issue is resolved after firmware current limiting. EVT reliability validation can resume.",
        keywords=["pcb", "thermal", "firmware"],
        event_id="event_2",
        updated_hour=11,
        status=EntityStatus.RESOLVED,
        entity_type=EntityType.MILESTONE,
    )

    merged = EntityMerger().merge([original, resolved_milestone])

    assert len(merged) == 1
    assert merged[0].entity_type == EntityType.RISK
    assert merged[0].status == EntityStatus.RESOLVED


def test_procurement_resolution_does_not_close_connector_dependency():
    connector_dependency = make_entity(
        entity_id="dependency_connector",
        title="Connector clearance depends on final motor mount CAD",
        summary="Connector clearance is blocked pending final motor mount CAD validation.",
        keywords=["connector", "motor mount", "cad"],
        event_id="event_1",
        updated_hour=9,
        status=EntityStatus.BLOCKED,
        entity_type=EntityType.DEPENDENCY,
    )
    bracket_resolution = make_entity(
        entity_id="action_bracket_resolved",
        title="Bracket PO is resolved",
        summary="Priya released the aluminum bracket PO after confirming the final BOM. The supplier confirmed the inventory slot, so the bracket procurement action item is resolved.",
        keywords=["bracket", "bom", "supplier"],
        event_id="event_2",
        updated_hour=11,
        status=EntityStatus.RESOLVED,
        entity_type=EntityType.ACTION_ITEM,
    )

    merged = EntityMerger().merge([connector_dependency, bracket_resolution])

    assert len(merged) == 2
    by_id = {entity.id: entity for entity in merged}
    assert by_id["dependency_connector"].status == EntityStatus.BLOCKED
    assert by_id["action_bracket_resolved"].status == EntityStatus.RESOLVED


def test_single_shared_bracket_keyword_does_not_bridge_connector_and_procurement():
    connector_dependency = make_entity(
        entity_id="dependency_connector",
        title="Connector clearance depends on final motor mount CAD",
        summary="Connector clearance depends on final motor mount CAD. EE cannot freeze wiring harness until Maya confirms bracket location.",
        keywords=["motor mount", "cad", "connector", "bracket"],
        event_id="event_1",
        updated_hour=9,
        status=EntityStatus.BLOCKED,
        entity_type=EntityType.DEPENDENCY,
    )
    bracket_resolution = make_entity(
        entity_id="action_bracket_resolved",
        title="Bracket PO is resolved",
        summary="Priya released the aluminum bracket PO after confirming the final BOM. The supplier confirmed the inventory slot, so the bracket procurement action item is resolved.",
        keywords=["bom", "bracket"],
        event_id="event_2",
        updated_hour=11,
        status=EntityStatus.RESOLVED,
        entity_type=EntityType.ACTION_ITEM,
    )

    merged = EntityMerger().merge([connector_dependency, bracket_resolution])

    assert len(merged) == 2


def test_acceptable_thermal_run_resolves_related_reliability_risk():
    original = make_entity(
        entity_id="risk_thermal",
        title="Warehouse Robot V2 PCB thermal risk follow-up",
        summary="PCB thermal rise is still 12C over target during the warehouse robot drive cycle. EVT reliability remains at risk.",
        keywords=["pcb", "thermal", "reliability"],
        event_id="event_1",
        updated_hour=9,
        status=EntityStatus.PENDING,
    )
    resolution = make_entity(
        entity_id="action_resume_validation",
        title="Resume EVT reliability validation",
        summary="The latest thermal chamber run looks acceptable after firmware current limiting. Alex says EVT reliability validation can resume tomorrow.",
        keywords=["thermal", "firmware", "reliability", "validation"],
        event_id="event_2",
        updated_hour=11,
        status=EntityStatus.RESOLVED,
        entity_type=EntityType.ACTION_ITEM,
    )

    merged = EntityMerger().merge([original, resolution])

    assert len(merged) == 1
    assert merged[0].entity_type == EntityType.RISK
    assert merged[0].status == EntityStatus.RESOLVED
    assert merged[0].summary == resolution.summary
    assert merged[0].supporting_events == ["event_1", "event_2"]
