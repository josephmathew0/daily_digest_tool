import re
from dataclasses import dataclass

from app.models.communication_event import CommunicationEvent
from app.models.enums import SourceType


# Relevance filtering runs before extraction. It keeps raw events in the
# database for auditability while preventing acknowledgements and account emails
# from becoming digest entities.
RELEVANCE_METADATA_KEY = "relevance"
RELEVANCE_FILTER_VERSION = "relevance_rules_v1"

LOW_SIGNAL_MESSAGES = {
    "ack",
    "acknowledged",
    "ok",
    "okay",
    "got it",
    "thanks",
    "thank you",
    "sounds good",
    "sgtm",
    "yes",
    "no",
}

PROJECT_SIGNAL_TERMS = [
    "action item",
    "approved",
    "blocked",
    "blocking",
    "bom",
    "by friday",
    "cad",
    "cannot proceed",
    "connector",
    "customer demo",
    "deadline",
    "decision",
    "dependency",
    "depends on",
    "demo",
    "dvt",
    "evt",
    "firmware",
    "lead time",
    "milestone",
    "owner:",
    "pcb",
    "pvt",
    "reliability",
    "resolved",
    "risk",
    "sensor",
    "supplier",
    "thermal",
    "tolerance",
    "validation",
    "waiting on",
]

EMAIL_NOISE_TERMS = [
    "add account recovery",
    "choose chrome",
    "continue<http",
    "get chrome",
    "google account settings",
    "privacy and security settings",
    "this email was sent to",
    "unsubscribe",
    "visit help center",
    "welcome to google",
]


@dataclass(frozen=True)
class RelevanceVerdict:
    is_relevant: bool
    score: float
    reason: str
    category: str

    def to_metadata(self) -> dict:
        return {
            "version": RELEVANCE_FILTER_VERSION,
            "is_relevant": self.is_relevant,
            "score": self.score,
            "reason": self.reason,
            "category": self.category,
        }


class RelevanceFilter:
    def assess(self, event: CommunicationEvent) -> RelevanceVerdict:
        text = self._combined_text(event)
        normalized = self._normalize(text)

        if not normalized:
            return RelevanceVerdict(False, 0.0, "empty message", "empty")

        low_signal_key = self._low_signal_key(normalized)
        if low_signal_key in LOW_SIGNAL_MESSAGES:
            return RelevanceVerdict(False, 0.05, "short acknowledgement", "acknowledgement")

        words = low_signal_key.split()
        has_project_signal = any(term in normalized for term in PROJECT_SIGNAL_TERMS)
        if len(words) <= 3 and not has_project_signal:
            return RelevanceVerdict(False, 0.1, "short low-signal message", "low_signal")

        if event.source_type == SourceType.EMAIL and self._looks_like_account_or_marketing_email(normalized):
            return RelevanceVerdict(False, 0.1, "account or marketing email", "email_noise")

        if has_project_signal:
            return RelevanceVerdict(True, 0.9, "project execution signal", "project_signal")

        if event.source_type == SourceType.EMAIL and self._looks_like_external_project_email(event, normalized):
            return RelevanceVerdict(True, 0.65, "project email with participants", "project_email")

        return RelevanceVerdict(False, 0.25, "no project execution signal", "low_signal")

    def annotate(self, event: CommunicationEvent) -> CommunicationEvent:
        verdict = self.assess(event)
        metadata = dict(event.metadata)
        # Store the verdict on the event so the frontend can show ignored source
        # evidence and the backend can skip extraction deterministically.
        metadata[RELEVANCE_METADATA_KEY] = verdict.to_metadata()
        return event.model_copy(update={"metadata": metadata})

    def annotate_many(self, events: list[CommunicationEvent]) -> list[CommunicationEvent]:
        return [self.annotate(event) for event in events]

    def is_relevant(self, event: CommunicationEvent) -> bool:
        metadata = event.metadata.get(RELEVANCE_METADATA_KEY)
        if isinstance(metadata, dict) and metadata.get("version") == RELEVANCE_FILTER_VERSION:
            return bool(metadata.get("is_relevant"))
        # Older events without a verdict are assessed on demand instead of
        # forcing a database migration.
        return self.assess(event).is_relevant

    def _combined_text(self, event: CommunicationEvent) -> str:
        return f"{event.title or ''} {event.text or ''}"

    def _normalize(self, text: str) -> str:
        normalized = text.lower()
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip()

    def _low_signal_key(self, normalized: str) -> str:
        key = re.sub(r"[^a-z0-9\s]", "", normalized)
        return re.sub(r"\s+", " ", key).strip()

    def _looks_like_account_or_marketing_email(self, normalized: str) -> bool:
        noise_hits = sum(1 for term in EMAIL_NOISE_TERMS if term in normalized)
        return noise_hits >= 2

    def _looks_like_external_project_email(self, event: CommunicationEvent, normalized: str) -> bool:
        has_participants = bool(event.recipients or event.author_email)
        has_subject = bool(event.title and len(event.title.split()) >= 3)
        return has_participants and has_subject and "unsubscribe" not in normalized
