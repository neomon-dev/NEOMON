from app.agents.base import BaseAgent
from app.schemas import AgentTask


class DebateModeratorAgent(BaseAgent):
    identifier = "debate_moderator"
    name = "Debate Moderator"
    description = "Coordinates bounded debate rounds."
    system_instructions = "Summarize positions without private reasoning."

    async def run(self, task: AgentTask) -> dict[str, object]:
        return await self.foundation_run(task)
