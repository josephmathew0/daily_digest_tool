from pydantic import BaseModel, Field

from app.models.entities import ProjectEntity


class DigestItem(BaseModel):
    """A scored entity plus the explanation shown inside one digest section."""

    entity: ProjectEntity
    score: float
    why_this_matters: list[str] = Field(default_factory=list)
    latest_update: str


class DigestResponse(BaseModel):
    """Role- and phase-specific digest payload returned to the frontend."""

    project: str
    user_id: str
    user_name: str
    role: str
    phase: str
    team_summary: str
    generated_at: str | None = None
    cache_hit: bool = False
    sections: dict[str, list[DigestItem]]
