from pydantic import BaseModel, Field


class ProcurementItem(BaseModel):
    """A predicted stock or procurement need derived from project state."""

    id: str
    title: str
    reason: str
    suggested_action: str
    related_entity_ids: list[str] = Field(default_factory=list)


class ProcurementForecastResponse(BaseModel):
    """Procurement forecast for demo quote-request workflows."""

    project: str
    phase: str
    gmail_send_configured: bool
    items: list[ProcurementItem] = Field(default_factory=list)


class ProcurementDraftRequest(BaseModel):
    """Request to draft a procurement email for one forecasted item."""

    project: str
    phase: str
    item_id: str
    recipient_email: str = "lojosephmathew@gmail.com"


class ProcurementDraftResponse(BaseModel):
    """OpenAI-generated procurement email draft, or a disabled explanation."""

    enabled: bool
    recipient_email: str
    subject: str | None = None
    body: str | None = None
    disabled_reason: str | None = None


class ProcurementSendRequest(BaseModel):
    """Request to send a reviewed procurement email draft."""

    recipient_email: str
    subject: str
    body: str


class ProcurementSendResponse(BaseModel):
    """Result of attempting to send a procurement email through Gmail."""

    sent: bool
    recipient_email: str
    message_id: str | None = None
    disabled_reason: str | None = None
