from app.agents.base import BaseAgent
from app.schemas import AgentTask


class IntelligencePlannerAgent(BaseAgent):
    identifier = "intelligence_planner"
    name = "Intelligence Planner"
    description = "Breaks questions into testable claims."
    system_instructions = "Plan only; do not invent evidence."

    async def run(self, task: AgentTask) -> dict[str, object]:
        return await self.foundation_run(task)
