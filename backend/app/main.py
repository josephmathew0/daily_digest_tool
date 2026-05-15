import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.models.communication_event import CommunicationEvent
from app.services.digest_generator import DigestGenerator
from app.services.ingestion_service import IngestionService
from app.services.state_tracker import StateTracker


DATA_DIR = Path(__file__).resolve().parent / "data"
ADDED_EVENTS_PATH = DATA_DIR / "added_events.json"

app = FastAPI(title="EverCurrent Daily Digest API")
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
    return sorted(IngestionService().fetch_all() + load_added_events(), key=lambda event: event.timestamp)


def all_entities():
    return StateTracker().build_entities(all_events())


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
    events = all_events()
    if project:
        events = [event for event in events if event.project == project]
    return events


@app.post("/events")
def add_event(event: CommunicationEvent):
    current = [item.model_dump(mode="json") for item in load_added_events()]
    current.append(event.model_dump(mode="json"))
    ADDED_EVENTS_PATH.write_text(json.dumps(current, indent=2))
    return {"created": event.id}


@app.post("/sync")
def sync_sources():
    events = all_events()
    entities = all_entities()
    return {"events": len(events), "entities": len(entities)}


@app.get("/digest")
def get_digest(user_id: str, phase: str = "prototype", project: str = "warehouse_robot_v2"):
    users = {user["id"]: user for user in load_json("users.json")}
    user = users.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Unknown user")

    entities = [entity for entity in all_entities() if project in entity.id or True]
    return DigestGenerator().generate(project=project, user=user, phase=phase, entities=entities)
