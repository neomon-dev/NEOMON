import pytest

from app.agents import create_agent
from app.schemas import AgentTask


@pytest.mark.asyncio
async def test_demo_agent_execution_is_explicit():
    agent = create_agent("skeptic")
    result = await agent.execute(AgentTask(task="Review this claim."))
    assert result.status == "completed"
    assert result.output["mode"] == "demo"
    assert agent.history[0]["status"] == "completed"
