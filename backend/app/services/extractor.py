import re
from datetime import datetime
from hashlib import sha1

from app.models.communication_event import CommunicationEvent
from app.models.entities import ProjectEntity
from app.models.enums import EntityStatus, EntityType, Severity


ROLE_KEYWORDS = {
    "mechanical_engineer": ["cad", "mount", "tolerance", "assembly", "fixture", "bracket", "vibration"],
    "electrical_engineer": ["pcb", "thermal", "voltage", "sensor", "connector", "wiring", "firmware"],
    "supply_chain": ["supplier", "lead time", "bom", "quote", "inventory", "cost"],
    "engineering_manager": ["blocker", "risk", "deadline", "dependency", "escalation", "milestone"],
    "product_manager": ["demo", "customer", "scope", "launch", "milestone", "release"],
}


class Extractor:
    def extract(self, event: CommunicationEvent) -> list[ProjectEntity]:
        text = f"{event.title or ''} {event.text}".lower()
        entity_type = self._entity_type(text)
        severity = self._severity(text)
        status = self._status(text)
        title = self._title(event, entity_type)
        keywords = self._keywords(text)
        affected_roles = [
            role for role, terms in ROLE_KEYWORDS.items() if any(term in text for term in terms)
        ] or ["engineering_manager"]

        entity_id = self._stable_id(event.project, entity_type.value, keywords or [title.lower()])
        resolved_at = event.timestamp if status == EntityStatus.RESOLVED else None

        return [
            ProjectEntity(
                id=entity_id,
                entity_type=entity_type,
                title=title,
                summary=event.text,
                status=status,
                severity=severity,
                confidence_score=self._confidence(text),
                owner=event.author_name,
                affected_roles=affected_roles,
                created_at=event.timestamp,
                updated_at=event.timestamp,
                resolved_at=resolved_at,
                supporting_events=[event.id],
                keywords=keywords,
            )
        ]

    def _entity_type(self, text: str) -> EntityType:
        if any(term in text for term in ["decision:", "decided", "approved", "proceed with"]):
            return EntityType.DECISION
        if any(term in text for term in ["action item", "todo", "by friday", "owner:"]):
            return EntityType.ACTION_ITEM
        if any(term in text for term in ["waiting on", "blocked by", "depends on", "dependency"]):
            return EntityType.DEPENDENCY
        if any(term in text for term in ["risk", "might", "concern", "slip"]):
            return EntityType.RISK
        if any(term in text for term in ["milestone", "demo", "evt", "dvt", "pvt"]):
            return EntityType.MILESTONE
        return EntityType.ISSUE

    def _severity(self, text: str) -> Severity:
        if any(term in text for term in ["critical", "customer demo blocked", "cannot proceed"]):
            return Severity.CRITICAL
        if any(term in text for term in ["blocked", "blocking", "lead time", "thermal", "deadline"]):
            return Severity.HIGH
        if any(term in text for term in ["risk", "concern", "waiting"]):
            return Severity.MEDIUM
        return Severity.LOW

    def _status(self, text: str) -> EntityStatus:
        if any(term in text for term in ["resolved", "closed", "fixed", "approved"]):
            return EntityStatus.RESOLVED
        if any(term in text for term in ["blocked", "blocking", "waiting on", "blocked by"]):
            return EntityStatus.BLOCKED
        if any(term in text for term in ["pending", "needs", "action item"]):
            return EntityStatus.PENDING
        return EntityStatus.ACTIVE

    def _confidence(self, text: str) -> float:
        if any(term in text for term in ["blocked", "decision:", "action item", "resolved"]):
            return 0.9
        if any(term in text for term in ["risk", "waiting on", "depends on"]):
            return 0.75
        return 0.55

    def _keywords(self, text: str) -> list[str]:
        candidates = [
            "motor mount", "tolerance", "cad", "connector", "thermal", "pcb",
            "sensor calibration", "bom", "lead time", "customer demo", "bracket",
            "assembly", "firmware", "vendor", "battery", "milestone",
        ]
        return [term for term in candidates if term in text]

    def _title(self, event: CommunicationEvent, entity_type: EntityType) -> str:
        if event.title:
            return event.title
        first_sentence = re.split(r"[.!?]", event.text.strip())[0]
        return first_sentence[:72] or entity_type.value.replace("_", " ").title()

    def _stable_id(self, project: str, entity_type: str, parts: list[str]) -> str:
        digest = sha1(f"{project}:{entity_type}:{':'.join(sorted(parts))}".encode()).hexdigest()[:10]
        return f"{entity_type}_{digest}"
