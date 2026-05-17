import os
from datetime import datetime, timezone
from hashlib import sha1

from pydantic import BaseModel, Field

from app.models.communication_event import CommunicationEvent
from app.models.entities import ProjectEntity
from app.models.enums import EntityStatus, EntityType, Severity
from app.services.extraction.base import ExtractionProvider


class ExtractedEntity(BaseModel):
    entity_type: EntityType
    title: str
    summary: str
    status: EntityStatus
    severity: Severity
    confidence_score: float = Field(ge=0, le=1)
    owner: str | None = None
    affected_roles: list[str] = Field(default_factory=list)
    due_date: str | None = None
    keywords: list[str] = Field(default_factory=list)


class ExtractionResponse(BaseModel):
    is_relevant: bool
    entities: list[ExtractedEntity] = Field(default_factory=list)


class OpenAIExtractionProvider(ExtractionProvider):
    mode = "openai"
    version = "openai_structured_v1"

    def __init__(self) -> None:
        from openai import OpenAI

        self.model_name = os.getenv("OPENAI_MODEL", "gpt-5-mini")
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def extract(self, event: CommunicationEvent) -> list[ProjectEntity]:
        response = self.client.responses.parse(
            model=self.model_name,
            instructions=(
                "You extract execution intelligence for robotics hardware engineering teams. "
                "Return only project-relevant entities. Ignore acknowledgements, greetings, "
                "marketing/system emails, and generic notifications. Entities must be one of: "
                "issue, risk, decision, dependency, action_item, milestone. Evidence messages are "
                "not the entity; the entity is the durable project state implied by the message. "
                "If the text indicates testing can resume, validation passed, or a risk is no longer blocking, "
                "mark the relevant entity resolved."
            ),
            input=[
                {
                    "role": "user",
                    "content": self._event_prompt(event),
                },
            ],
            text_format=ExtractionResponse,
            reasoning={"effort": "minimal"},
            max_output_tokens=1200,
        )

        parsed = response.output_parsed
        if not parsed or not parsed.is_relevant:
            return []

        return [self._to_project_entity(event, item) for item in parsed.entities]

    def _event_prompt(self, event: CommunicationEvent) -> str:
        return (
            f"Event ID: {event.id}\n"
            f"Source: {event.source_type.value} / {event.source_ref}\n"
            f"Author: {event.author_name or event.author_email or 'unknown'}\n"
            f"Project: {event.project}\n"
            f"Timestamp: {event.timestamp.isoformat()}\n"
            f"Title: {event.title or ''}\n"
            f"Text:\n{event.text[:4000]}"
        )

    def _to_project_entity(self, event: CommunicationEvent, item: ExtractedEntity) -> ProjectEntity:
        now = event.timestamp
        resolved_at = now if item.status == EntityStatus.RESOLVED else None
        return ProjectEntity(
            id=self._stable_id(event, item),
            entity_type=item.entity_type,
            title=item.title[:120],
            summary=item.summary,
            status=item.status,
            severity=item.severity,
            confidence_score=item.confidence_score,
            owner=item.owner or event.author_name,
            affected_roles=sorted(set(item.affected_roles)),
            created_at=now,
            updated_at=now,
            resolved_at=resolved_at,
            due_date=None,
            supporting_events=[event.id],
            keywords=sorted(set(item.keywords)),
        )

    def _stable_id(self, event: CommunicationEvent, item: ExtractedEntity) -> str:
        key = f"{event.project}:{item.entity_type.value}:{item.title.lower()}:{','.join(sorted(item.keywords))}"
        digest = sha1(key.encode("utf-8")).hexdigest()[:10]
        return f"{item.entity_type.value}_{digest}"
