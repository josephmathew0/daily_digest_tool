import os
from dataclasses import dataclass

from app.models.entities import ProjectEntity
from app.models.procurement import (
    ProcurementDraftResponse,
    ProcurementForecastResponse,
    ProcurementItem,
    ProcurementSendResponse,
)
from app.services.gmail_sender import GmailSender


@dataclass(frozen=True)
class ProcurementPattern:
    id: str
    title: str
    reason: str
    suggested_action: str
    terms: tuple[str, ...]


PROCUREMENT_PATTERNS = [
    ProcurementPattern(
        id="prototype_brackets",
        title="Aluminum prototype brackets",
        reason=(
            "Bracket, supplier, PO, or lead-time signals indicate the team may need "
            "to confirm bracket availability or request a quote."
        ),
        suggested_action="Request quote, lead-time confirmation, and first-article availability for prototype brackets.",
        terms=("bracket", "supplier", "lead time", "po", "bom", "inventory", "vendor"),
    ),
    ProcurementPattern(
        id="connector_harness_samples",
        title="Connector and harness validation samples",
        reason=(
            "Connector clearance and harness routing are affecting validation, so "
            "sample parts may be needed for fit and envelope checks."
        ),
        suggested_action="Request connector and harness samples for physical clearance validation.",
        terms=("connector", "harness", "clearance", "envelope", "wiring"),
    ),
    ProcurementPattern(
        id="motor_mount_spacers",
        title="Motor mount spacer prototype parts",
        reason=(
            "Motor mount tolerance, CAD revision, or spacer-adjustment signals indicate "
            "the team may need prototype spacer parts for assembly validation."
        ),
        suggested_action="Request prototype motor mount spacers or revised mount parts for fit-check builds.",
        terms=("motor mount", "spacer", "tolerance", "cad", "assembly"),
    ),
    ProcurementPattern(
        id="thermal_validation_spares",
        title="PCB and thermal validation spares",
        reason=(
            "Thermal, PCB, EVT, or reliability signals indicate the team may need "
            "spare boards, thermal materials, or test samples for validation runs."
        ),
        suggested_action="Confirm spare PCB/test samples and thermal-interface materials for follow-up validation.",
        terms=("thermal", "pcb", "evt", "reliability", "validation", "firmware", "test"),
    ),
]


class ProcurementService:
    """Forecast likely stock or quote-request needs from project entities."""

    def forecast(self, *, project: str, phase: str, entities: list[ProjectEntity]) -> ProcurementForecastResponse:
        items = [
            self._item(pattern, entities)
            for pattern in self._ranked_patterns(entities)
            if self._related_entities(pattern, entities)
        ]
        return ProcurementForecastResponse(
            project=project,
            phase=phase,
            gmail_send_configured=self._gmail_send_configured(),
            items=items[:4],
        )

    def draft_email(
        self,
        *,
        project: str,
        phase: str,
        item_id: str,
        recipient_email: str,
        entities: list[ProjectEntity],
    ) -> ProcurementDraftResponse:
        if not self._openai_configured():
            return ProcurementDraftResponse(
                enabled=False,
                recipient_email=recipient_email,
                disabled_reason="OpenAI integration is not configured. Add OPENAI_API_KEY and restart the backend.",
            )

        forecast = self.forecast(project=project, phase=phase, entities=entities)
        item = next((candidate for candidate in forecast.items if candidate.id == item_id), None)
        if not item:
            return ProcurementDraftResponse(
                enabled=False,
                recipient_email=recipient_email,
                disabled_reason="The selected procurement item is no longer predicted for the current project state.",
            )

        subject, body = self._openai_draft(
            project=project,
            phase=phase,
            item=item,
            recipient_email=recipient_email,
            related_entities=[
                entity for entity in entities
                if entity.id in set(item.related_entity_ids)
            ],
        )
        return ProcurementDraftResponse(
            enabled=True,
            recipient_email=recipient_email,
            subject=subject,
            body=body,
        )

    def send_email(self, *, recipient_email: str, subject: str, body: str) -> ProcurementSendResponse:
        if not self._gmail_send_configured():
            return ProcurementSendResponse(
                sent=False,
                recipient_email=recipient_email,
                disabled_reason="Gmail sending is disabled. Set GMAIL_SEND_ENABLED=true and restart the backend.",
            )

        try:
            message_id = GmailSender().send(
                recipient_email=recipient_email,
                subject=subject,
                body=body,
            )
        except Exception as error:
            return ProcurementSendResponse(
                sent=False,
                recipient_email=recipient_email,
                disabled_reason=f"Unable to send Gmail message: {error}",
            )

        return ProcurementSendResponse(
            sent=True,
            recipient_email=recipient_email,
            message_id=message_id,
        )

    def _ranked_patterns(self, entities: list[ProjectEntity]) -> list[ProcurementPattern]:
        return sorted(
            PROCUREMENT_PATTERNS,
            key=lambda pattern: (
                -len(self._related_entities(pattern, entities)),
                pattern.id,
            ),
        )

    def _item(self, pattern: ProcurementPattern, entities: list[ProjectEntity]) -> ProcurementItem:
        return ProcurementItem(
            id=pattern.id,
            title=pattern.title,
            reason=pattern.reason,
            suggested_action=pattern.suggested_action,
            related_entity_ids=[entity.id for entity in self._related_entities(pattern, entities)],
        )

    def _related_entities(self, pattern: ProcurementPattern, entities: list[ProjectEntity]) -> list[ProjectEntity]:
        return [
            entity for entity in entities
            if any(term in self._text(entity) for term in pattern.terms)
        ][:5]

    def _text(self, entity: ProjectEntity) -> str:
        return f"{entity.title} {entity.summary} {' '.join(entity.keywords)}".lower()

    def _gmail_send_configured(self) -> bool:
        return os.getenv("GMAIL_SEND_ENABLED", "false").lower() == "true"

    def _openai_configured(self) -> bool:
        return bool(os.getenv("OPENAI_API_KEY"))

    def _openai_draft(
        self,
        *,
        project: str,
        phase: str,
        item: ProcurementItem,
        recipient_email: str,
        related_entities: list[ProjectEntity],
    ) -> tuple[str, str]:
        from openai import OpenAI

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
            instructions=(
                "You draft concise procurement request-for-quote emails for hardware engineering teams. "
                "Use only the provided project context. Do not claim a purchase order has been approved. "
                "Ask for quote, lead time, availability, and any validation details relevant to the item. "
                "Return exactly this format:\nSubject: <subject>\nBody:\n<body>"
            ),
            input=[
                {
                    "role": "user",
                    "content": (
                        f"Project: {project}\n"
                        f"Phase: {phase}\n"
                        f"Recipient: {recipient_email}\n"
                        f"Procurement item: {item.title}\n"
                        f"Reason: {item.reason}\n"
                        f"Suggested action: {item.suggested_action}\n\n"
                        f"Related project entities:\n{self._entities_prompt(related_entities)}"
                    ),
                },
            ],
            max_output_tokens=700,
            reasoning={"effort": "minimal"},
        )
        return self._parse_email_draft(response.output_text.strip())

    def _parse_email_draft(self, text: str) -> tuple[str, str]:
        subject = "Request for quote and availability"
        body = text or "Please provide quote, lead time, and availability for the requested prototype item."
        if text.lower().startswith("subject:"):
            subject_line, _, remainder = text.partition("\n")
            subject = subject_line.replace("Subject:", "", 1).strip() or subject
            body = remainder
            if body.lower().startswith("body:"):
                body = body[5:]
            body = body.strip() or "Please provide quote, lead time, and availability for the requested prototype item."
        return subject, body

    def _entities_prompt(self, entities: list[ProjectEntity]) -> str:
        if not entities:
            return "- No directly related tracked entities."
        return "\n".join(
            "- "
            f"{entity.entity_type.value} | {entity.status.value} | {entity.severity.value} | "
            f"{entity.title}: {entity.summary}"
            for entity in entities[:8]
        )
