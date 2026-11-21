from typing import Any, Dict
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth.dependencies import get_current_user
from app.hardware.telemetry import (
    HardwareTelemetryResponse,
    MemoryProfile,
    hardware_service,
)
from app.models import User

router = APIRouter(prefix="/hardware", tags=["hardware"])


class ProfileUpdateRequest(BaseModel):
    profile: MemoryProfile


@router.get("/telemetry", response_model=HardwareTelemetryResponse)
async def get_hardware_telemetry() -> HardwareTelemetryResponse:
    return hardware_service.get_telemetry()


@router.post("/profile", response_model=Dict[str, Any])
async def update_hardware_profile(
    req: ProfileUpdateRequest,
    user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    return hardware_service.set_profile(req.profile)
