from typing import Any

from app.providers.base import AIProvider, ProviderRequestError
from app.schemas import ProviderConfigRequest


class OllamaProvider(AIProvider):
    def __init__(self, config: ProviderConfigRequest) -> None:
        ep = config.endpoint.rstrip("/")
        if ep.endswith("/v1"):
            clean_endpoint = ep[:-3]
            config = config.model_copy(update={"endpoint": clean_endpoint})
        super().__init__(config)
        self._cached_models: list[str] = []

    async def discover_models(self) -> list[str]:
        data = None
        try:
            response = await self._request("GET", "/api/tags")
            data = response.json()
        except ProviderRequestError as exc:
            if exc.status_code == 404:
                try:
                    response = await self._request("GET", "/v1/models")
                    data = response.json()
                except ProviderRequestError:
                    if self.config.model:
                        return [self.config.model]
                    raise
            else:
                raise

        models: list[str] = []
        if isinstance(data, dict):
            raw_models = data.get("models") or data.get("data") or []
        elif isinstance(data, list):
            raw_models = data
        else:
            raw_models = []

        if isinstance(raw_models, list):
            for model in raw_models:
                if isinstance(model, dict):
                    name = model.get("name") or model.get("model") or model.get("id")
                    if isinstance(name, str) and name.strip():
                        models.append(name.strip())
                elif isinstance(model, str) and model.strip():
                    models.append(model.strip())

        unique_models = list(dict.fromkeys(models))
        if self.config.model and self.config.model not in unique_models:
            unique_models.insert(0, self.config.model)
        self._cached_models = unique_models
        return unique_models

    async def complete(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        **kwargs: Any,
    ) -> dict[str, object]:
        effective_model = model or self.config.model
        if not effective_model:
            if self._cached_models:
                effective_model = self._cached_models[0]
            else:
                try:
                    discovered = await self.discover_models()
                    if discovered:
                        effective_model = discovered[0]
                except Exception:
                    pass
        if not effective_model:
            raise ProviderRequestError("No model specified and could not discover models from Ollama.")

        req_body: dict[str, Any] = {
            "model": effective_model,
            "messages": messages,
            "stream": False,
        }
        if "format" in kwargs and kwargs["format"] is not None:
            req_body["format"] = kwargs["format"]
        elif "response_schema" in kwargs and kwargs["response_schema"] is not None:
            req_body["format"] = kwargs["response_schema"]
        else:
            req_body["format"] = "json"

        async with self._inference_slot(effective_model) as lease:
            try:
                response = await self._request("POST", "/api/chat", json=req_body)
            except ProviderRequestError as exc:
                if exc.status_code in {400, 422} and "format" in req_body:
                    req_body.pop("format", None)
                    response = await self._request("POST", "/api/chat", json=req_body)
                else:
                    raise

        data = response.json()
        message = data.get("message") or {}
        content = message.get("content")
        if not isinstance(content, str):
            content = data.get("response") or data.get("text")
        if not isinstance(content, str):
            raise ProviderRequestError("Ollama returned no structured message content.")
        return {
            "content": content,
            "model": data.get("model") or effective_model,
            "queue_wait_seconds": round(lease.wait_seconds, 3),
            "usage": {
                "prompt_tokens": data.get("prompt_eval_count"),
                "completion_tokens": data.get("eval_count"),
            },
        }
