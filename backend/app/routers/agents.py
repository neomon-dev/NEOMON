from fastapi import APIRouter, Depends

from app.agents.definitions import AGENT_DEFINITIONS
from app.auth.dependencies import get_current_user
from app.config import get_settings
from app.models import User
from app.schemas import AgentSummary

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentSummary])
async def list_agents(
    user: User = Depends(get_current_user),
) -> list[AgentSummary]:
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
