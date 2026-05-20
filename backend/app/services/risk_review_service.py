import os
from dataclasses import dataclass

from app.models.entities import ProjectEntity
from app.models.risk_review import RiskCheck, RiskReviewResponse


@dataclass(frozen=True)
class RiskPattern:
    id: str
    title: str
    why_it_matters: str
    suggested_question: str
    terms: tuple[str, ...]


RISK_PATTERNS = [
    RiskPattern(
        id="tolerance_stackup",
        title="Tolerance stack-up before volume order",
        why_it_matters=(
            "Bench prototypes can pass while production parts fail at scale if tolerance "
            "stack-ups are not reviewed before ordering parts."
        ),
        suggested_question="Has the team checked tolerance stack-ups before releasing any volume or long-lead orders?",
        terms=("tolerance", "cad", "assembly", "mount", "connector", "bracket"),
    ),
    RiskPattern(
        id="physical_validation",
        title="Physical validation beyond simulation",
        why_it_matters=(
            "FEA and simulation reduce risk, but hardware teams still learn from rig, drop, "
            "thermal, and reliability testing that exposes real-world failure modes."
        ),
        suggested_question="What physical tests still need to run before the team trusts this design for the milestone?",
        terms=("thermal", "test", "testing", "validation", "reliability", "evt", "dvt", "drop"),
    ),
    RiskPattern(
        id="manufacturing_input",
        title="Manufacturer and tooling input",
        why_it_matters=(
            "Early manufacturing feedback can prevent tooling delays, redesigns, and "
            "late changes after CAD or supplier decisions are already committed."
        ),
        suggested_question="Has a manufacturer or tooling partner reviewed the current CAD and assembly approach?",
        terms=("supplier", "vendor", "tooling", "manufacturing", "bracket", "cad", "assembly"),
    ),
    RiskPattern(
        id="supplier_capability",
        title="Supplier capability and process risk",
        why_it_matters=(
            "Cheap quotes and fast promises can hide capability gaps. Strong suppliers "
            "challenge assumptions and prove they can repeatedly build the part."
        ),
        suggested_question="Has the supplier demonstrated capability for the required tolerance, material, and delivery schedule?",
        terms=("supplier", "vendor", "lead time", "po", "bom", "inventory", "quote"),
    ),
    RiskPattern(
        id="material_tradeoff",
        title="Material, sustainability, and cost tradeoffs",
        why_it_matters=(
            "Material decisions can affect cost, reliability, compliance, brand positioning, "
            "and customer acceptance, not only unit price."
        ),
        suggested_question="Are material choices being reviewed for reliability, compliance, cost, and customer value?",
        terms=("material", "sustainability", "cost", "compliance", "supplier", "battery"),
    ),
]


class RiskReviewService:
    """Suggest proactive hardware risk checks from current project context."""

    def review(self, *, project: str, phase: str, entities: list[ProjectEntity]) -> RiskReviewResponse:
        checks = [self._check(pattern, entities) for pattern in self._ranked_patterns(entities)]
        openai_configured = self._openai_configured()
        ai_followup_enabled = self._ai_followup_enabled()
        return RiskReviewResponse(
            project=project,
            phase=phase,
            openai_configured=openai_configured,
            ai_followup_enabled=ai_followup_enabled,
            disabled_reason=self._disabled_reason(openai_configured, ai_followup_enabled),
            checks=checks[:5],
        )

    def answer_question(self, *, project: str, phase: str, entities: list[ProjectEntity], question: str) -> str:
        from openai import OpenAI

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        checks = [self._check(pattern, entities) for pattern in self._ranked_patterns(entities)][:5]
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
            instructions=(
                "You are an execution-risk advisor for hardware engineering teams. "
                "Answer the user's follow-up using only the structured project entities and suggested checks. "
                "Separate confirmed project facts from suggested checks. Do not claim a risk is present "
                "unless it appears in the project entities. Keep the answer concise and actionable."
            ),
            input=[
                {
                    "role": "user",
                    "content": (
                        f"Project: {project}\n"
                        f"Phase: {phase}\n"
                        f"Question: {question}\n\n"
                        f"Project entities:\n{self._entities_prompt(entities)}\n\n"
                        f"Suggested risk checks:\n{self._checks_prompt(checks)}"
                    ),
                },
            ],
            max_output_tokens=700,
            reasoning={"effort": "minimal"},
        )
        return response.output_text.strip() or "No answer was generated."

    def _ranked_patterns(self, entities: list[ProjectEntity]) -> list[RiskPattern]:
        return sorted(
            RISK_PATTERNS,
            key=lambda pattern: (
                -len(self._related_entities(pattern, entities)),
                pattern.id,
            ),
        )

    def _check(self, pattern: RiskPattern, entities: list[ProjectEntity]) -> RiskCheck:
        return RiskCheck(
            id=pattern.id,
            title=pattern.title,
            why_it_matters=pattern.why_it_matters,
            suggested_question=pattern.suggested_question,
            related_entity_ids=[entity.id for entity in self._related_entities(pattern, entities)],
        )

    def _related_entities(self, pattern: RiskPattern, entities: list[ProjectEntity]) -> list[ProjectEntity]:
        return [
            entity for entity in entities
            if any(term in self._text(entity) for term in pattern.terms)
        ][:5]

    def _text(self, entity: ProjectEntity) -> str:
        return f"{entity.title} {entity.summary} {' '.join(entity.keywords)}".lower()

    def _openai_configured(self) -> bool:
        return bool(os.getenv("OPENAI_API_KEY"))

    def _ai_followup_enabled(self) -> bool:
        return self._openai_configured() and os.getenv("AI_RISK_REVIEW_ENABLED", "false").lower() == "true"

    def _disabled_reason(self, openai_configured: bool, ai_followup_enabled: bool) -> str | None:
        if ai_followup_enabled:
            return None
        if not openai_configured:
            return "OpenAI integration is not configured. Add OPENAI_API_KEY and restart the backend."
        return "AI Risk Review follow-up is disabled. Set AI_RISK_REVIEW_ENABLED=true and restart the backend."

    def _entities_prompt(self, entities: list[ProjectEntity]) -> str:
        if not entities:
            return "- No tracked project entities."
        lines = []
        for entity in entities[:20]:
            lines.append(
                "- "
                f"{entity.entity_type.value} | {entity.status.value} | {entity.severity.value} | "
                f"{entity.title}: {entity.summary}"
            )
        return "\n".join(lines)

    def _checks_prompt(self, checks: list[RiskCheck]) -> str:
        return "\n".join(
            f"- {check.title}: {check.suggested_question}"
            for check in checks
        )
