from app.providers.base import AIProvider, ProviderRequestError


class OllamaProvider(AIProvider):
    async def discover_models(self) -> list[str]:
        response = await self._request("GET", "/api/tags")
        data = response.json()
        return [model["name"] for model in data.get("models", []) if isinstance(model, dict)]

    async def complete(self, messages: list[dict[str, str]], model: str | None = None) -> dict[str, object]:
        async with self._inference_slot(model) as lease:
            response = await self._request(
                "POST",
                "/api/chat",
                json={"model": model or self.config.model, "messages": messages, "stream": False, "format": "json"},
            )
        data = response.json()
        message = data.get("message") or {}
        content = message.get("content")
        if not isinstance(content, str):
            raise ProviderRequestError("Ollama returned no structured message content.")
        return {
            "content": content,
            "model": data.get("model") or model or self.config.model,
            "queue_wait_seconds": round(lease.wait_seconds, 3),
            "usage": {
                "prompt_tokens": data.get("prompt_eval_count"),
                "completion_tokens": data.get("eval_count"),
            },
        }
