from fastapi import APIRouter

from app.agents import AGENT_DEFINITIONS
from app.config import get_settings
from app.schemas import AgentSummary

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentSummary])
async def list_agents() -> list[AgentSummary]:
    return [
        AgentSummary(
            identifier=definition.identifier,
            name=definition.name,
            description=definition.description,
            status="ready",
            demo_mode=get_settings().demo_mode,
        )
        for definition in AGENT_DEFINITIONS
    ]
