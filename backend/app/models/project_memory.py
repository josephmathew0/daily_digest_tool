from pydantic import BaseModel, Field

from app.models.entities import ProjectEntity


class ProjectMemory(BaseModel):
    project: str
    active_context: list[ProjectEntity] = Field(default_factory=list)
    recent_changes: list[ProjectEntity] = Field(default_factory=list)
    long_term_memory: list[ProjectEntity] = Field(default_factory=list)
