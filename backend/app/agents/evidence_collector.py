from app.agents.base import BaseAgent
from app.schemas import AgentTask


class EvidenceCollectorAgent(BaseAgent):
    identifier = "evidence_collector"
    name = "Evidence Collector"
    description = "Extracts source-grounded passages."
    system_instructions = "Collect exact evidence and preserve metadata."

    async def run(self, task: AgentTask) -> dict[str, object]:
        return await self.foundation_run(task)
