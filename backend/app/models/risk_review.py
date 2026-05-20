from pydantic import BaseModel, Field


class RiskCheck(BaseModel):
    """A proactive hardware risk check suggested from industry patterns."""

    id: str
    title: str
    why_it_matters: str
    suggested_question: str
    related_entity_ids: list[str] = Field(default_factory=list)


class RiskReviewResponse(BaseModel):
    """Suggested risk checks plus OpenAI availability for follow-up questions."""

    project: str
    phase: str
    openai_configured: bool
    ai_followup_enabled: bool
    disabled_reason: str | None = None
    checks: list[RiskCheck] = Field(default_factory=list)


class RiskQuestionRequest(BaseModel):
    project: str
    phase: str
    question: str


class RiskQuestionResponse(BaseModel):
    enabled: bool
    answer: str | None = None
    disabled_reason: str | None = None
