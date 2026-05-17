import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from app.models.communication_event import CommunicationEvent
from app.models.digest import DigestResponse
from app.models.entities import ProjectEntity


DB_PATH = Path(__file__).resolve().parent / "app.db"


def set_db_path(path: Path) -> None:
    global DB_PATH
    DB_PATH = path


def connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS communication_events (
                id TEXT PRIMARY KEY,
                event_hash TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_ref TEXT NOT NULL,
                author_name TEXT,
                author_email TEXT,
                author_role TEXT,
                title TEXT,
                text TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                channel TEXT,
                thread_id TEXT,
                recipients_json TEXT NOT NULL,
                attendees_json TEXT NOT NULL,
                reactions_json TEXT NOT NULL,
                project TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_project ON communication_events(project)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON communication_events(timestamp)")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS event_extractions (
                event_id TEXT PRIMARY KEY,
                event_hash TEXT NOT NULL,
                extraction_mode TEXT NOT NULL,
                extractor_version TEXT NOT NULL,
                model_name TEXT,
                entities_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(event_id) REFERENCES communication_events(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_extractions_hash ON event_extractions(event_hash)")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS project_entities (
                id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                status TEXT NOT NULL,
                severity TEXT NOT NULL,
                confidence_score REAL NOT NULL,
                owner TEXT,
                affected_roles_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                resolved_at TEXT,
                due_date TEXT,
                supporting_events_json TEXT NOT NULL,
                keywords_json TEXT NOT NULL,
                project TEXT NOT NULL,
                persisted_at TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_project ON project_entities(project)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_entities_status ON project_entities(status)")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS digest_cache (
                cache_key TEXT PRIMARY KEY,
                project TEXT NOT NULL,
                user_id TEXT NOT NULL,
                phase TEXT NOT NULL,
                entity_fingerprint TEXT NOT NULL,
                digest_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_digest_lookup ON digest_cache(project, user_id, phase)")


def event_hash(event: CommunicationEvent) -> str:
    payload = event.model_dump(mode="json")
    stable_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(stable_json.encode("utf-8")).hexdigest()


def upsert_events(events: Iterable[CommunicationEvent]) -> dict[str, int]:
    init_db()
    inserted = 0
    updated = 0
    unchanged = 0
    now = datetime.now(timezone.utc).isoformat()

    with connection() as conn:
        for event in events:
            next_hash = event_hash(event)
            existing = conn.execute(
                "SELECT event_hash FROM communication_events WHERE id = ?",
                (event.id,),
            ).fetchone()

            if existing and existing["event_hash"] == next_hash:
                unchanged += 1
                continue

            payload = _to_row(event, next_hash, now)
            conn.execute(
                """
                INSERT INTO communication_events (
                    id, event_hash, source_type, source_ref, author_name, author_email,
                    author_role, title, text, timestamp, channel, thread_id,
                    recipients_json, attendees_json, reactions_json, project, metadata_json,
                    created_at, updated_at
                )
                VALUES (
                    :id, :event_hash, :source_type, :source_ref, :author_name, :author_email,
                    :author_role, :title, :text, :timestamp, :channel, :thread_id,
                    :recipients_json, :attendees_json, :reactions_json, :project, :metadata_json,
                    :created_at, :updated_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    event_hash = excluded.event_hash,
                    source_type = excluded.source_type,
                    source_ref = excluded.source_ref,
                    author_name = excluded.author_name,
                    author_email = excluded.author_email,
                    author_role = excluded.author_role,
                    title = excluded.title,
                    text = excluded.text,
                    timestamp = excluded.timestamp,
                    channel = excluded.channel,
                    thread_id = excluded.thread_id,
                    recipients_json = excluded.recipients_json,
                    attendees_json = excluded.attendees_json,
                    reactions_json = excluded.reactions_json,
                    project = excluded.project,
                    metadata_json = excluded.metadata_json,
                    updated_at = excluded.updated_at
                """,
                payload,
            )
            if existing:
                updated += 1
            else:
                inserted += 1

    return {"inserted": inserted, "updated": updated, "unchanged": unchanged}


def list_events(project: str | None = None) -> list[CommunicationEvent]:
    init_db()
    sql = "SELECT * FROM communication_events"
    params: tuple[str, ...] = ()
    if project:
        sql += " WHERE project = ?"
        params = (project,)
    sql += " ORDER BY timestamp ASC"

    with connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_from_row(row) for row in rows]


def event_hashes() -> dict[str, str]:
    init_db()
    with connection() as conn:
        rows = conn.execute("SELECT id, event_hash FROM communication_events").fetchall()
    return {row["id"]: row["event_hash"] for row in rows}


def get_cached_extraction(
    event_id: str,
    next_hash: str,
    extraction_mode: str,
    extractor_version: str,
    model_name: str | None = None,
) -> list[ProjectEntity] | None:
    init_db()
    with connection() as conn:
        row = conn.execute(
            """
            SELECT entities_json FROM event_extractions
            WHERE event_id = ?
              AND event_hash = ?
              AND extraction_mode = ?
              AND extractor_version = ?
              AND COALESCE(model_name, '') = COALESCE(?, '')
            """,
            (event_id, next_hash, extraction_mode, extractor_version, model_name),
        ).fetchone()

    if not row:
        return None
    return [ProjectEntity.model_validate(item) for item in json.loads(row["entities_json"])]


def save_extraction(
    event_id: str,
    next_hash: str,
    entities: list[ProjectEntity],
    extraction_mode: str,
    extractor_version: str,
    model_name: str | None = None,
) -> None:
    init_db()
    now = datetime.now(timezone.utc).isoformat()
    entities_json = json.dumps([entity.model_dump(mode="json") for entity in entities])
    with connection() as conn:
        existing = conn.execute(
            "SELECT created_at FROM event_extractions WHERE event_id = ?",
            (event_id,),
        ).fetchone()
        created_at = existing["created_at"] if existing else now
        conn.execute(
            """
            INSERT INTO event_extractions (
                event_id, event_hash, extraction_mode, extractor_version, model_name,
                entities_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(event_id) DO UPDATE SET
                event_hash = excluded.event_hash,
                extraction_mode = excluded.extraction_mode,
                extractor_version = excluded.extractor_version,
                model_name = excluded.model_name,
                entities_json = excluded.entities_json,
                updated_at = excluded.updated_at
            """,
            (
                event_id,
                next_hash,
                extraction_mode,
                extractor_version,
                model_name,
                entities_json,
                created_at,
                now,
            ),
        )


def replace_project_entities(project: str, entities: list[ProjectEntity]) -> None:
    init_db()
    now = datetime.now(timezone.utc).isoformat()
    with connection() as conn:
        conn.execute("DELETE FROM project_entities WHERE project = ?", (project,))
        for entity in entities:
            conn.execute(
                """
                INSERT INTO project_entities (
                    id, entity_type, title, summary, status, severity, confidence_score,
                    owner, affected_roles_json, created_at, updated_at, resolved_at, due_date,
                    supporting_events_json, keywords_json, project, persisted_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entity.id,
                    entity.entity_type.value,
                    entity.title,
                    entity.summary,
                    entity.status.value,
                    entity.severity.value,
                    entity.confidence_score,
                    entity.owner,
                    json.dumps(entity.affected_roles),
                    entity.created_at.isoformat(),
                    entity.updated_at.isoformat(),
                    entity.resolved_at.isoformat() if entity.resolved_at else None,
                    entity.due_date.isoformat() if entity.due_date else None,
                    json.dumps(entity.supporting_events),
                    json.dumps(entity.keywords),
                    project,
                    now,
                ),
            )


def list_project_entities(project: str | None = None) -> list[ProjectEntity]:
    init_db()
    sql = "SELECT * FROM project_entities"
    params: tuple[str, ...] = ()
    if project:
        sql += " WHERE project = ?"
        params = (project,)
    sql += " ORDER BY updated_at DESC"

    with connection() as conn:
        rows = conn.execute(sql, params).fetchall()

    return [_entity_from_row(row) for row in rows]


def entity_fingerprint(entities: list[ProjectEntity]) -> str:
    payload = [
        {
            "id": entity.id,
            "status": entity.status.value,
            "severity": entity.severity.value,
            "summary": entity.summary,
            "updated_at": entity.updated_at.isoformat(),
            "supporting_events": sorted(entity.supporting_events),
        }
        for entity in sorted(entities, key=lambda item: item.id)
    ]
    stable_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(stable_json.encode("utf-8")).hexdigest()


def digest_cache_key(project: str, user_id: str, phase: str, fingerprint: str) -> str:
    return hashlib.sha256(f"{project}:{user_id}:{phase}:{fingerprint}".encode("utf-8")).hexdigest()


def get_cached_digest(project: str, user_id: str, phase: str, fingerprint: str) -> DigestResponse | None:
    init_db()
    key = digest_cache_key(project, user_id, phase, fingerprint)
    with connection() as conn:
        row = conn.execute(
            "SELECT digest_json FROM digest_cache WHERE cache_key = ?",
            (key,),
        ).fetchone()
    if not row:
        return None
    return DigestResponse.model_validate(json.loads(row["digest_json"]))


def save_digest(project: str, user_id: str, phase: str, fingerprint: str, digest: DigestResponse) -> None:
    init_db()
    key = digest_cache_key(project, user_id, phase, fingerprint)
    now = datetime.now(timezone.utc).isoformat()
    digest_json = json.dumps(digest.model_dump(mode="json"))
    with connection() as conn:
        existing = conn.execute(
            "SELECT created_at FROM digest_cache WHERE cache_key = ?",
            (key,),
        ).fetchone()
        created_at = existing["created_at"] if existing else now
        conn.execute(
            """
            INSERT INTO digest_cache (
                cache_key, project, user_id, phase, entity_fingerprint,
                digest_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(cache_key) DO UPDATE SET
                digest_json = excluded.digest_json,
                updated_at = excluded.updated_at
            """,
            (key, project, user_id, phase, fingerprint, digest_json, created_at, now),
        )


def _to_row(event: CommunicationEvent, next_hash: str, now: str) -> dict:
    return {
        "id": event.id,
        "event_hash": next_hash,
        "source_type": event.source_type.value,
        "source_ref": event.source_ref,
        "author_name": event.author_name,
        "author_email": event.author_email,
        "author_role": event.author_role,
        "title": event.title,
        "text": event.text,
        "timestamp": event.timestamp.isoformat(),
        "channel": event.channel,
        "thread_id": event.thread_id,
        "recipients_json": json.dumps(event.recipients),
        "attendees_json": json.dumps(event.attendees),
        "reactions_json": json.dumps(event.reactions),
        "project": event.project,
        "metadata_json": json.dumps(event.metadata),
        "created_at": now,
        "updated_at": now,
    }


def _from_row(row: sqlite3.Row) -> CommunicationEvent:
    return CommunicationEvent(
        id=row["id"],
        source_type=row["source_type"],
        source_ref=row["source_ref"],
        author_name=row["author_name"],
        author_email=row["author_email"],
        author_role=row["author_role"],
        title=row["title"],
        text=row["text"],
        timestamp=datetime.fromisoformat(row["timestamp"]),
        channel=row["channel"],
        thread_id=row["thread_id"],
        recipients=json.loads(row["recipients_json"]),
        attendees=json.loads(row["attendees_json"]),
        reactions=json.loads(row["reactions_json"]),
        project=row["project"],
        metadata=json.loads(row["metadata_json"]),
    )


def _entity_from_row(row: sqlite3.Row) -> ProjectEntity:
    return ProjectEntity(
        id=row["id"],
        entity_type=row["entity_type"],
        title=row["title"],
        summary=row["summary"],
        status=row["status"],
        severity=row["severity"],
        confidence_score=row["confidence_score"],
        owner=row["owner"],
        affected_roles=json.loads(row["affected_roles_json"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        resolved_at=datetime.fromisoformat(row["resolved_at"]) if row["resolved_at"] else None,
        due_date=datetime.fromisoformat(row["due_date"]) if row["due_date"] else None,
        supporting_events=json.loads(row["supporting_events_json"]),
        keywords=json.loads(row["keywords_json"]),
    )
