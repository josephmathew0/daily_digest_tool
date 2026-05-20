from pydantic import BaseModel, Field

from app.models.enums import ReadinessStatus


class ReadinessItem(BaseModel):
    """One entity-derived reason that affects build or milestone readiness."""

    entity_id: str
    title: str
    summary: str
    status: str
    severity: str
    updated_at: str
    supporting_events: list[str] = Field(default_factory=list)


class BuildReadinessResponse(BaseModel):
    """Go/no-go readiness view for the selected project and phase."""

    project: str
    phase: str
    status: ReadinessStatus
    summary: str
    blockers: list[ReadinessItem] = Field(default_factory=list)
    risks: list[ReadinessItem] = Field(default_factory=list)
    resolved: list[ReadinessItem] = Field(default_factory=list)
    missing_confirmations: list[ReadinessItem] = Field(default_factory=list)
    generated_at: str
