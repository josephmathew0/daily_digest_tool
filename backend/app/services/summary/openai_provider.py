import os

from app.models.entities import ProjectEntity
from app.services.summary.base import SummaryProvider


class OpenAISummaryProvider(SummaryProvider):
    mode = "openai"

    def __init__(self) -> None:
        from openai import OpenAI

        self.model_name = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def team_summary(self, entities: list[ProjectEntity], phase: str) -> str:
        if not entities:
            return "No execution signals are currently tracked for this project."

        # Summaries are generated from structured entities, not raw emails or
        # Slack text. That keeps prompts smaller and limits exposure of source
        # content once extraction has already identified the project state.
        response = self.client.responses.create(
            model=self.model_name,
            instructions=(
                "You write concise execution intelligence summaries for robotics hardware teams. "
                "Summarize project state from structured entities only. Mention active blockers, "
                "risks, dependencies, decisions, and milestone impact only when present in the entities. "
                "Do not infer or invent mitigation steps, root causes, owners, or dependencies. "
                "Write 2-4 sentences."
            ),
            input=[
                {
                    "role": "user",
                    "content": f"Project phase: {phase}\nEntities:\n{self._entities_prompt(entities)}",
                },
            ],
            max_output_tokens=800,
            reasoning={"effort": "minimal"},
        )
        return response.output_text.strip() or "Unable to generate team summary."

    def _entities_prompt(self, entities: list[ProjectEntity]) -> str:
        lines = []
        for entity in entities[:20]:
            # Bound summary context to the highest-signal entities supplied by
            # the digest pipeline rather than every historical message.
            lines.append(
                "- "
                f"{entity.entity_type.value} | {entity.status.value} | {entity.severity.value} | "
                f"{entity.title}: {entity.summary}"
            )
        return "\n".join(lines)
