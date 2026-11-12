from fastapi import APIRouter

from app.errors import BackendError
from app.providers import create_provider
from app.providers.base import ProviderRequestError, validate_provider_endpoint
from app.schemas import ProviderConfigRequest, ProviderStatus

router = APIRouter(prefix="/providers", tags=["providers"])


@router.post("/test", response_model=ProviderStatus)
async def test_provider(config: ProviderConfigRequest) -> ProviderStatus:
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
