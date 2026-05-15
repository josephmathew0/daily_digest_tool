from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import SourceType


class CommunicationEvent(BaseModel):
    id: str
    source_type: SourceType
    source_ref: str
    author_name: str | None = None
    author_email: str | None = None
    author_role: str | None = None
    title: str | None = None
    text: str
    timestamp: datetime
    channel: str | None = None
    thread_id: str | None = None
    recipients: list[str] = Field(default_factory=list)
    attendees: list[str] = Field(default_factory=list)
    reactions: list[str] = Field(default_factory=list)
    project: str
    metadata: dict[str, Any] = Field(default_factory=dict)
