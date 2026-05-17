from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import EntityStatus, EntityType, Severity


class ProjectEntity(BaseModel):
    """Durable project state extracted from one or more communication events."""

    id: str
    entity_type: EntityType
    title: str
    summary: str
    status: EntityStatus = EntityStatus.ACTIVE
    severity: Severity = Severity.MEDIUM
    confidence_score: float = 0.65
    owner: str | None = None
    affected_roles: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None
    due_date: datetime | None = None
    supporting_events: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
