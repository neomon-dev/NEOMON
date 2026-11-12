from app.agents.base import BaseAgent
from app.schemas import AgentTask


class ReportIntelligenceAgent(BaseAgent):
    identifier = "report_intelligence"
    name = "Report Intelligence"
    description = "Assembles transparent reports."
    system_instructions = "Include limitations and unresolved issues."

    async def run(self, task: AgentTask) -> dict[str, object]:
        return await self.foundation_run(task)
