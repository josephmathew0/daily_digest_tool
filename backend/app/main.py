import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.database.repository import (
    entity_fingerprint,
    get_cached_digest,
    init_db,
    list_events,
    list_project_entities,
    save_digest,
    upsert_events,
)
from app.models.communication_event import CommunicationEvent
from app.services.digest_generator import DigestGenerator
from app.services.ingestion_service import IngestionService
from app.services.relevance_filter import RelevanceFilter
from app.services.state_tracker import StateTracker


DATA_DIR = Path(__file__).resolve().parent / "data"
ADDED_EVENTS_PATH = DATA_DIR / "added_events.json"
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
DIGEST_CACHE_VERSION = "digest_v5"
LAST_SYNC_STATUS: dict = {
    "last_sync_at": None,
    "events": 0,
    "relevant_events": 0,
    "ignored_events": 0,
    "entities": 0,
    "extracted": 0,
    "reused_extractions": 0,
    "skipped_irrelevant": 0,
}


class EventResponse(BaseModel):
    id: str
    source_type: str
    source_ref: str
    author_name: str | None = None
    author_email: str | None = None
    author_role: str | None = None
    title: str | None = None
    text: str
    timestamp: str
    channel: str | None = None
    thread_id: str | None = None
    recipients: list[str]
    attendees: list[str]
    reactions: list[str]
    project: str
    metadata: dict
    is_relevant: bool
    relevance_score: float
    relevance_reason: str
    relevance_category: str


class SystemStatusResponse(BaseModel):
    summary_mode: str
    extraction_mode: str
    openai_model: str | None
    openai_configured: bool
    last_sync_at: str | None
    events: int
    relevant_events: int
    ignored_events: int
    entities: int
    extracted: int
    reused_extractions: int
    skipped_irrelevant: int


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="EverCurrent Daily Digest API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_json(name: str):
    return json.loads((DATA_DIR / name).read_text())


def load_added_events() -> list[CommunicationEvent]:
    if not ADDED_EVENTS_PATH.exists():
        return []
    return [CommunicationEvent.model_validate(item) for item in json.loads(ADDED_EVENTS_PATH.read_text())]


def all_events() -> list[CommunicationEvent]:
    events = list_events()
    if events:
        return events

    source_events = sorted(IngestionService().fetch_all() + load_added_events(), key=lambda event: event.timestamp)
    source_events = RelevanceFilter().annotate_many(source_events)
    upsert_events(source_events)
    return list_events()


def all_entities():
    return StateTracker().build_entities(all_events())


def event_response(event: CommunicationEvent) -> EventResponse:
    relevance_filter = RelevanceFilter()
    relevance = event.metadata.get("relevance")
    if not isinstance(relevance, dict):
        relevance = relevance_filter.assess(event).to_metadata()
    return EventResponse(
        id=event.id,
        source_type=event.source_type.value,
        source_ref=event.source_ref,
        author_name=event.author_name,
        author_email=event.author_email,
        author_role=event.author_role,
        title=event.title,
        text=event.text,
        timestamp=event.timestamp.isoformat(),
        channel=event.channel,
        thread_id=event.thread_id,
        recipients=event.recipients,
        attendees=event.attendees,
        reactions=event.reactions,
        project=event.project,
        metadata=event.metadata,
        is_relevant=bool(relevance.get("is_relevant")),
        relevance_score=float(relevance.get("score", 0.0)),
        relevance_reason=str(relevance.get("reason", "not assessed")),
        relevance_category=str(relevance.get("category", "unknown")),
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/users")
def get_users():
    return load_json("users.json")


@app.get("/projects")
def get_projects():
    return load_json("projects.json")


@app.get("/events")
def get_events(project: str | None = None):
    if not list_events():
        all_events()
    return [event_response(event) for event in list_events(project)]


@app.get("/system-status")
def get_system_status():
    return SystemStatusResponse(
        summary_mode=os.getenv("SUMMARY_MODE", "rules"),
        extraction_mode=os.getenv("EXTRACTION_MODE", "rules"),
        openai_model=os.getenv("OPENAI_MODEL"),
        openai_configured=bool(os.getenv("OPENAI_API_KEY")),
        **LAST_SYNC_STATUS,
    )


@app.post("/events")
def add_event(event: CommunicationEvent):
    event = RelevanceFilter().annotate(event)
    current = [item.model_dump(mode="json") for item in load_added_events()]
    current.append(event.model_dump(mode="json"))
    ADDED_EVENTS_PATH.write_text(json.dumps(current, indent=2))
    upsert_events([event])
    return {"created": event.id}


@app.post("/sync")
def sync_sources():
    events = sorted(IngestionService().fetch_all() + load_added_events(), key=lambda event: event.timestamp)
    relevance_filter = RelevanceFilter()
    events = relevance_filter.annotate_many(events)
    stats = upsert_events(events)
    events = list_events()
    tracker = StateTracker()
    entities = tracker.build_entities(events)
    response = {
        "events": len(events),
        "relevant_events": sum(1 for event in events if relevance_filter.is_relevant(event)),
        "ignored_events": sum(1 for event in events if not relevance_filter.is_relevant(event)),
        "entities": len(entities),
        **stats,
        "extracted": tracker.last_stats["extracted"],
        "reused_extractions": tracker.last_stats["reused"],
        "skipped_irrelevant": tracker.last_stats["skipped_irrelevant"],
    }
    LAST_SYNC_STATUS.update(
        {
            "last_sync_at": datetime.now(timezone.utc).isoformat(),
            "events": response["events"],
            "relevant_events": response["relevant_events"],
            "ignored_events": response["ignored_events"],
            "entities": response["entities"],
            "extracted": response["extracted"],
            "reused_extractions": response["reused_extractions"],
            "skipped_irrelevant": response["skipped_irrelevant"],
        }
    )
    return response


@app.get("/digest")
def get_digest(user_id: str, phase: str = "prototype", project: str = "warehouse_robot_v2"):
    users = {user["id"]: user for user in load_json("users.json")}
    user = users.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Unknown user")

    entities = list_project_entities(project)
    if not entities:
        entities = [
            entity for entity in all_entities()
            if any(event.id in entity.supporting_events and event.project == project for event in all_events())
        ]
    fingerprint = ":".join([
        entity_fingerprint(entities),
        os.getenv("SUMMARY_MODE", "rules"),
        os.getenv("OPENAI_MODEL", ""),
        DIGEST_CACHE_VERSION,
    ])
    cached = get_cached_digest(project, user_id, phase, fingerprint)
    if cached:
        return cached

    digest = DigestGenerator().generate(project=project, user=user, phase=phase, entities=entities)
    save_digest(project, user_id, phase, fingerprint, digest)
    return digest
