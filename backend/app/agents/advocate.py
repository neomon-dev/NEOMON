from app.agents.base import BaseAgent
from app.schemas import AgentTask


class AdvocateAgent(BaseAgent):
    identifier = "advocate"
    name = "Advocate"
    description = "Builds the strongest supported argument."
    system_instructions = "Argue only from supplied evidence."

    async def run(self, task: AgentTask) -> dict[str, object]:
        return await self.foundation_run(task)
