from app.agents.base import BaseAgent
from app.schemas import AgentTask


class TemporalIntelligenceAgent(BaseAgent):
    identifier = "temporal_intelligence"
    name = "Temporal Intelligence"
    description = "Checks dates and changing definitions."
    system_instructions = "Flag temporal uncertainty explicitly."

    async def run(self, task: AgentTask) -> dict[str, object]:
        return await self.foundation_run(task)
