from app.agents.base import BaseAgent
from app.schemas import AgentTask


class SkepticAgent(BaseAgent):
    identifier = "skeptic"
    name = "Skeptic"
    description = "Challenges claims and evidence."
    system_instructions = "Look for counter-evidence and unsupported assumptions."

    async def run(self, task: AgentTask) -> dict[str, object]:
        return await self.foundation_run(task)
