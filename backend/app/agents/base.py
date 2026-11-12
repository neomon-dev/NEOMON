from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

from app.providers.base import AIProvider
from app.schemas import AgentResult, AgentTask


class BaseAgent(ABC):
    identifier: str
    name: str
    description: str
    system_instructions: str

    def __init__(self, provider: AIProvider | None = None) -> None:
        self.provider = provider
        self.history: list[dict[str, Any]] = []
        self.status = "idle"

    async def execute(self, task: AgentTask) -> AgentResult:
        started_at = datetime.now(UTC)
        self.status = "running"
        try:
            output = await self.run(task)
            self.status = "completed"
            result = AgentResult(agent_id=self.identifier, status=self.status, output=output)
        except Exception as exc:
            self.status = "failed"
            result = AgentResult(agent_id=self.identifier, status=self.status, error=str(exc))
        self.history.append(
            {"started_at": started_at.isoformat(), "status": result.status, "task": task.task}
        )
        return result

    async def foundation_run(self, task: AgentTask) -> dict[str, Any]:
        if self.provider is None:
            return {"mode": "demo", "message": "Agent execution requires a configured provider."}
        return await self.provider.complete(
            [{"role": "system", "content": self.system_instructions}, {"role": "user", "content": task.task}]
        )

    @abstractmethod
    async def run(self, task: AgentTask) -> dict[str, Any]:
        raise NotImplementedError
