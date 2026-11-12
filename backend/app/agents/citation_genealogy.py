from app.agents.base import BaseAgent
from app.schemas import AgentTask


class CitationGenealogyAgent(BaseAgent):
    identifier = "citation_genealogy"
    name = "Citation Genealogy"
    description = "Traces citation dependencies."
    system_instructions = "Only record provenance supported by source metadata."

    async def run(self, task: AgentTask) -> dict[str, object]:
        return await self.foundation_run(task)
