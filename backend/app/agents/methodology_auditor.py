from app.agents.base import BaseAgent
from app.schemas import AgentTask


class MethodologyAuditorAgent(BaseAgent):
    identifier = "methodology_auditor"
    name = "Methodology Auditor"
    description = "Reviews study and source methods."
    system_instructions = "Identify design and reproducibility limitations."

    async def run(self, task: AgentTask) -> dict[str, object]:
        return await self.foundation_run(task)
