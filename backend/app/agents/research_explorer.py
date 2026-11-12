from app.agents.base import BaseAgent
from app.schemas import AgentTask


class ResearchExplorerAgent(BaseAgent):
    identifier = "research_explorer"
    name = "Research Explorer"
    description = "Finds candidate sources."
    system_instructions = "Explore only; report source URLs, not unsupported conclusions."

    async def run(self, task: AgentTask) -> dict[str, object]:
        return await self.foundation_run(task)
