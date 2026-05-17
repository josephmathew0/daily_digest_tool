from datetime import datetime, timezone

from app.database.repository import (
    entity_fingerprint,
    get_cached_digest,
    get_cached_extraction,
    list_events,
    list_project_entities,
    replace_project_entities,
    save_digest,
    save_extraction,
    upsert_events,
)
from app.models.communication_event import CommunicationEvent
from app.models.digest import DigestResponse
from app.models.entities import ProjectEntity
from app.models.enums import EntityStatus, EntityType, Severity, SourceType


def event(text: str = "PCB thermal rise is blocking EVT validation.") -> CommunicationEvent:
    return CommunicationEvent(
        id="event_1",
        source_type=SourceType.SLACK,
        source_ref="#warehouse-robot-v2",
        author_name="Alex",
        text=text,
        timestamp=datetime(2026, 5, 16, tzinfo=timezone.utc),
        project="warehouse_robot_v2",
    )


def entity() -> ProjectEntity:
    return ProjectEntity(
        id="risk_1",
        entity_type=EntityType.RISK,
        title="PCB thermal risk",
        summary="PCB thermal rise is blocking EVT validation.",
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


def test_upsert_events_tracks_insert_update_unchanged():
    stats = upsert_events([event()])
    assert stats == {"inserted": 1, "updated": 0, "unchanged": 0}

    stats = upsert_events([event()])
    assert stats == {"inserted": 0, "updated": 0, "unchanged": 1}

    stats = upsert_events([event("Updated PCB thermal risk.")])
    assert stats == {"inserted": 0, "updated": 1, "unchanged": 0}
    assert list_events()[0].text == "Updated PCB thermal risk."


def test_extraction_cache_round_trip():
    upsert_events([event()])
    extracted = [entity()]
    event_hash = "hash_1"

    assert get_cached_extraction("event_1", event_hash, "rules", "rules_v1") is None
    save_extraction("event_1", event_hash, extracted, "rules", "rules_v1")

    cached = get_cached_extraction("event_1", event_hash, "rules", "rules_v1")
    assert cached is not None
    assert cached[0].title == "PCB thermal risk"
    assert get_cached_extraction("event_1", "different_hash", "rules", "rules_v1") is None


def test_project_entities_and_digest_cache_round_trip():
    project = "warehouse_robot_v2"
    entities = [entity()]
    replace_project_entities(project, entities)

    persisted = list_project_entities(project)
    assert len(persisted) == 1
    assert persisted[0].id == "risk_1"

    fingerprint = entity_fingerprint(persisted)
    digest = DigestResponse(
        project=project,
        user_id="alex",
        user_name="Alex Rivera",
        role="electrical_engineer",
        phase="EVT",
        team_summary="One high-impact risk is active.",
        sections={},
    )

    assert get_cached_digest(project, "alex", "EVT", fingerprint) is None
    save_digest(project, "alex", "EVT", fingerprint, digest)

    cached = get_cached_digest(project, "alex", "EVT", fingerprint)
    assert cached is not None
    assert cached.team_summary == "One high-impact risk is active."
