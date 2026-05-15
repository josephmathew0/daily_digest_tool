from enum import Enum


class SourceType(str, Enum):
    SLACK = "slack"
    EMAIL = "email"
    MEETING = "meeting"


class EntityType(str, Enum):
    ISSUE = "issue"
    RISK = "risk"
    DECISION = "decision"
    DEPENDENCY = "dependency"
    ACTION_ITEM = "action_item"
    MILESTONE = "milestone"


class EntityStatus(str, Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    PENDING = "pending"
    BLOCKED = "blocked"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ProjectPhase(str, Enum):
    DESIGN = "design"
    PROTOTYPE = "prototype"
    EVT = "EVT"
    DVT = "DVT"
    PVT = "PVT"
    PRODUCTION = "production"
