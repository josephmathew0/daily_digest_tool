from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
import app.main as main_module
from app.database.repository import list_events, list_project_entities
from app.models.communication_event import CommunicationEvent
from app.models.enums import SourceType


def test_sync_persists_and_reuses_extractions(monkeypatch):
    source_event = CommunicationEvent(
        id="slack_test_1",
        source_type=SourceType.SLACK,
        source_ref="#warehouse-robot-v2",
        author_name="Alex",
        text="PCB thermal rise is 12C over target and EVT reliability remains at risk.",
        timestamp=datetime(2026, 5, 16, tzinfo=timezone.utc),
        project="warehouse_robot_v2",
    )

    monkeypatch.setattr(
        "app.main.IngestionService.fetch_all",
        lambda self: [source_event],
    )
    monkeypatch.setattr("app.main.load_added_events", lambda: [])

    client = TestClient(app)

    first = client.post("/sync").json()
    assert first["events"] == 1
    assert first["inserted"] == 1
    assert first["extracted"] == 1
    assert first["reused_extractions"] == 0

    second = client.post("/sync").json()
    assert second["events"] == 1
    assert second["unchanged"] == 1
    assert second["extracted"] == 0
    assert second["reused_extractions"] == 1

    digest = client.get("/digest?user_id=alex&phase=EVT&project=warehouse_robot_v2")
    assert digest.status_code == 200
    first_digest = digest.json()
    assert first_digest["user_id"] == "alex"
    assert first_digest["generated_at"]
    assert first_digest["cache_hit"] is False

    cached_digest = client.get("/digest?user_id=alex&phase=EVT&project=warehouse_robot_v2").json()
    assert cached_digest["generated_at"] == first_digest["generated_at"]
    assert cached_digest["cache_hit"] is True

    readiness = client.get("/readiness?phase=EVT&project=warehouse_robot_v2")
    assert readiness.status_code == 200
    readiness_payload = readiness.json()
    assert readiness_payload["project"] == "warehouse_robot_v2"
    assert readiness_payload["phase"] == "EVT"
    assert readiness_payload["status"] in {"ready", "at_risk", "blocked"}
    assert readiness_payload["generated_at"]

    system_status = client.get("/system-status").json()
    assert system_status["summary_mode"]
    assert system_status["extraction_mode"]
    assert system_status["last_sync_at"]
    assert system_status["events"] == 1
    assert system_status["ignored_events"] == 0


def test_events_response_exposes_relevance_metadata(monkeypatch):
    source_event = CommunicationEvent(
        id="slack_ack_1",
        source_type=SourceType.SLACK,
        source_ref="#warehouse-robot-v2",
        author_name="Alex",
        text="Acknowledged.",
        timestamp=datetime(2026, 5, 16, tzinfo=timezone.utc),
        project="warehouse_robot_v2",
    )

    monkeypatch.setattr(
        "app.main.IngestionService.fetch_all",
        lambda self: [source_event],
    )
    monkeypatch.setattr("app.main.load_added_events", lambda: [])

    client = TestClient(app)
    sync = client.post("/sync").json()
    assert sync["ignored_events"] == 1
    assert sync["skipped_irrelevant"] == 1

    events = client.get("/events?project=warehouse_robot_v2").json()
    assert events[0]["is_relevant"] is False
    assert events[0]["relevance_score"] == 0.05
    assert events[0]["relevance_reason"] == "short acknowledgement"
    assert events[0]["relevance_category"] == "acknowledgement"


def test_system_status_derives_persisted_counts_after_restart(monkeypatch):
    source_event = CommunicationEvent(
        id="slack_restart_1",
        source_type=SourceType.SLACK,
        source_ref="#warehouse-robot-v2",
        author_name="Alex",
        text="PCB thermal rise is 12C over target and EVT reliability remains at risk.",
        timestamp=datetime(2026, 5, 16, tzinfo=timezone.utc),
        project="warehouse_robot_v2",
    )

    monkeypatch.setattr(
        "app.main.IngestionService.fetch_all",
        lambda self: [source_event],
    )
    monkeypatch.setattr("app.main.load_added_events", lambda: [])

    client = TestClient(app)
    client.post("/sync")

    assert len(list_events()) == 1
    assert len(list_project_entities()) == 1

    main_module.LAST_SYNC_STATUS.update(
        {
            "last_sync_at": None,
            "events": 0,
            "relevant_events": 0,
            "ignored_events": 0,
            "entities": 0,
            "extracted": 0,
            "reused_extractions": 0,
            "skipped_irrelevant": 0,
        }
    )

    status = client.get("/system-status").json()

    assert status["last_sync_at"] is None
    assert status["events"] == 1
    assert status["relevant_events"] == 1
    assert status["ignored_events"] == 0
    assert status["entities"] == 1
