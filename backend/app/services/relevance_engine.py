from datetime import datetime, timezone

from app.models.entities import ProjectEntity
from app.models.enums import EntityStatus, ProjectPhase, Severity


ROLE_PRIORITIES = {
    "mechanical_engineer": ["cad", "mount", "tolerance", "assembly", "fixture", "bracket", "vibration"],
    "electrical_engineer": ["pcb", "thermal", "voltage", "sensor", "connector", "wiring", "firmware"],
    "supply_chain": ["supplier", "lead time", "bom", "quote", "inventory", "cost", "vendor"],
    "engineering_manager": ["blocker", "risk", "deadline", "dependency", "milestone", "demo"],
    "product_manager": ["demo", "customer", "scope", "launch", "milestone", "release"],
}

PHASE_PRIORITIES = {
    "design": ["architecture", "requirements", "cad"],
    "prototype": ["blocker", "integration", "assembly", "tolerance", "fixture"],
    "EVT": ["validation", "thermal", "reliability"],
    "DVT": ["compliance", "repeatability", "fit", "finish"],
    "PVT": ["manufacturing", "supplier", "yield", "bom"],
    "production": ["defect", "quality", "field", "cost"],
}

SEVERITY_SCORE = {
    Severity.LOW: 1.0,
    Severity.MEDIUM: 2.0,
    Severity.HIGH: 3.0,
    Severity.CRITICAL: 4.0,
}


class RelevanceEngine:
    def score(self, entity: ProjectEntity, role: str, phase: str) -> tuple[float, list[str]]:
        reasons: list[str] = []
        text = f"{entity.title} {entity.summary} {' '.join(entity.keywords)}".lower()
        score = 0.0

        if role in entity.affected_roles:
            score += 3.0
            reasons.append("Relevant to selected role")

        for term in ROLE_PRIORITIES.get(role, []):
            if term in text:
                score += 0.7

        for term in PHASE_PRIORITIES.get(phase, []):
            if term in text:
                score += 0.8
                reasons.append("Relevant to selected project phase")
                break

        score += SEVERITY_SCORE[entity.severity]
        if entity.severity in {Severity.HIGH, Severity.CRITICAL}:
            reasons.append("High execution impact")

        if entity.status in {EntityStatus.BLOCKED, EntityStatus.PENDING, EntityStatus.ACTIVE}:
            score += 2.0
            reasons.append("Still unresolved")

        if entity.entity_type.value == "dependency":
            score += 1.5
            reasons.append("Cross-functional dependency")

        event_count = len(entity.supporting_events)
        if event_count > 1:
            score += min(event_count * 0.4, 2.0)
            reasons.append("Mentioned by multiple source events")

        age_hours = max((datetime.now(timezone.utc) - entity.updated_at).total_seconds() / 3600, 1)
        score += max(0.0, 2.0 - age_hours / 36)

        return round(score, 2), reasons or ["Included because it affects current project state"]
