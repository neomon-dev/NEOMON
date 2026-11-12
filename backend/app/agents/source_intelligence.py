from app.agents.base import BaseAgent
from app.schemas import AgentTask


class SourceIntelligenceAgent(BaseAgent):
    identifier = "source_intelligence"
    name = "Source Intelligence"
    description = "Assesses source reliability."
    system_instructions = "Separate documented source facts from heuristics."

    async def run(self, task: AgentTask) -> dict[str, object]:
        return await self.foundation_run(task)
