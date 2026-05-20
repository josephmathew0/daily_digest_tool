from datetime import datetime, timezone

from app.models.entities import ProjectEntity
from app.models.enums import EntityStatus, EntityType, ReadinessStatus, Severity
from app.services.readiness_service import ReadinessService


def entity(
    *,
    entity_id: str,
    entity_type: EntityType,
    status: EntityStatus,
    severity: Severity,
    title: str,
    summary: str = "summary",
    updated_hour: int = 12,
) -> ProjectEntity:
    timestamp = datetime(2026, 5, 16, updated_hour, tzinfo=timezone.utc)
    return ProjectEntity(
        id=entity_id,
        entity_type=entity_type,
        title=title,
        summary=summary,
        status=status,
        severity=severity,
        confidence_score=0.8,
        owner="Alex",
        affected_roles=["engineering_manager"],
        created_at=timestamp,
        updated_at=timestamp,
        resolved_at=timestamp if status == EntityStatus.RESOLVED else None,
        supporting_events=[f"event_{entity_id}"],
        keywords=[],
    )


def assess(entities: list[ProjectEntity]):
    return ReadinessService().assess(
        project="warehouse_robot_v2",
        phase="prototype",
        entities=entities,
    )


def test_blocked_dependency_makes_readiness_blocked():
    readiness = assess([
        entity(
            entity_id="dependency_connector",
            entity_type=EntityType.DEPENDENCY,
            status=EntityStatus.BLOCKED,
            severity=Severity.MEDIUM,
            title="Connector clearance depends on final motor mount CAD",
        )
    ])

    assert readiness.status == ReadinessStatus.BLOCKED
    assert [item.entity_id for item in readiness.blockers] == ["dependency_connector"]


def test_high_unresolved_risk_without_blockers_makes_readiness_at_risk():
    readiness = assess([
        entity(
            entity_id="risk_thermal",
            entity_type=EntityType.RISK,
            status=EntityStatus.ACTIVE,
            severity=Severity.HIGH,
            title="PCB thermal margin is above EVT target",
        )
    ])

    assert readiness.status == ReadinessStatus.AT_RISK
    assert [item.entity_id for item in readiness.risks] == ["risk_thermal"]


def test_ready_when_only_low_or_resolved_entities_remain():
    readiness = assess([
        entity(
            entity_id="decision_scope",
            entity_type=EntityType.DECISION,
            status=EntityStatus.ACTIVE,
            severity=Severity.LOW,
            title="Keep customer demo scope focused",
        ),
        entity(
            entity_id="risk_thermal",
            entity_type=EntityType.RISK,
            status=EntityStatus.RESOLVED,
            severity=Severity.HIGH,
            title="PCB thermal margin resolved",
        ),
    ])

    assert readiness.status == ReadinessStatus.READY
    assert readiness.resolved[0].entity_id == "risk_thermal"


def test_missing_confirmations_include_validation_and_waiting_language():
    readiness = assess([
        entity(
            entity_id="action_connector",
            entity_type=EntityType.ACTION_ITEM,
            status=EntityStatus.PENDING,
            severity=Severity.MEDIUM,
            title="Alex must validate connector clearance by Friday",
            summary="Alex needs to validate connector clearance by Friday.",
        ),
        entity(
            entity_id="dependency_bom",
            entity_type=EntityType.DEPENDENCY,
            status=EntityStatus.ACTIVE,
            severity=Severity.MEDIUM,
            title="Waiting on finalized BOM before placing bracket order",
        ),
    ])

    assert readiness.status == ReadinessStatus.BLOCKED
    assert {item.entity_id for item in readiness.missing_confirmations} == {
        "action_connector",
        "dependency_bom",
    }
