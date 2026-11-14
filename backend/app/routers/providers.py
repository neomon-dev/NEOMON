from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.config import get_settings
from app.errors import BackendError
from app.models import User
from app.providers import create_provider
from app.providers.base import ProviderRequestError, validate_provider_endpoint
from app.research.providers import TavilyProvider
from app.research.telemetry import tavily_telemetry
from app.schemas import (
    ProviderConfigRequest,
    ProviderStatus,
    TavilyStatusResponse,
    TavilyTestRequest,
    TavilyTestResponse,
)

router = APIRouter(prefix="/providers", tags=["providers"])


@router.post("/test", response_model=ProviderStatus)
async def test_provider(
    config: ProviderConfigRequest,
    user: User = Depends(get_current_user),
) -> ProviderStatus:
    try:
        await validate_provider_endpoint(
            config.endpoint,
            config.kind,
            allow_local_runtime=config.allow_local_runtime,
        )
    except ProviderRequestError as exc:
        raise BackendError(str(exc), 422, "invalid_provider_endpoint") from exc
    provider = create_provider(config)
    try:
        return await provider.test_connection()
    finally:
        await provider.close()


@router.post("/tavily/test", response_model=TavilyTestResponse)
async def test_tavily(
    request: TavilyTestRequest,
    user: User = Depends(get_current_user),
) -> TavilyTestResponse:
    provider = TavilyProvider(api_key=request.api_key, search_depth=request.search_depth)
    try:
        result = await provider.test_connection(api_key=request.api_key, search_depth=request.search_depth)
        return TavilyTestResponse(**result)
    finally:
        await provider.close()


@router.get("/tavily/status", response_model=TavilyStatusResponse)
async def get_tavily_status(
    user: User = Depends(get_current_user),
) -> TavilyStatusResponse:
    settings = get_settings()
    return TavilyStatusResponse(
        provider="tavily",
        enabled=settings.tavily_enabled,
        api_key_configured=bool(settings.tavily_api_key),
        search_depth=settings.tavily_search_depth,
        max_results=settings.tavily_max_results,
        include_domains=list(settings.tavily_include_domains),
        exclude_domains=list(settings.tavily_exclude_domains),
        telemetry=tavily_telemetry.get_summary(),
    )

