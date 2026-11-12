from app.agents.base import BaseAgent
from app.schemas import AgentTask


class ConflictAdjudicatorAgent(BaseAgent):
    identifier = "conflict_adjudicator"
    name = "Conflict Adjudicator"
    description = "Explains credible source disagreement."
    system_instructions = "Do not force consensus."

    async def run(self, task: AgentTask) -> dict[str, object]:
        return await self.foundation_run(task)
