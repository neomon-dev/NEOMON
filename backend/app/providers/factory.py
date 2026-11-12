from app.providers.base import AIProvider
from app.providers.ollama import OllamaProvider
from app.providers.openai_compatible import OpenAICompatibleProvider
from app.schemas import ProviderConfigRequest, ProviderKind


def create_provider(config: ProviderConfigRequest) -> AIProvider:
    if config.kind is ProviderKind.ollama:
        return OllamaProvider(config)
    if config.kind in (ProviderKind.lm_studio, ProviderKind.openai_compatible):
        return OpenAICompatibleProvider(config)
    raise ValueError(f"Unsupported provider: {config.kind}")
