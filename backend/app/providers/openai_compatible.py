import copy
import logging
from typing import Any

from app.providers.base import AIProvider, ProviderRequestError
from app.schemas import ProviderKind

logger = logging.getLogger(__name__)


def _inline_schema_refs(node: Any, defs: dict[str, Any]) -> Any:
    if isinstance(node, list):
        return [_inline_schema_refs(item, defs) for item in node]
    if not isinstance(node, dict):
        return node
    if "$ref" in node:
        ref = str(node["$ref"])
        prefix = "#/$defs/"
        if ref.startswith(prefix):
            def_name = ref[len(prefix) :]
            if def_name in defs:
                return _inline_schema_refs(copy.deepcopy(defs[def_name]), defs)
    cleaned: dict[str, Any] = {}
    for key, value in node.items():
        if key in {"$defs", "$schema", "title", "default"}:
            continue
        if key == "format" and value == "uuid":
            continue
        cleaned[key] = _inline_schema_refs(value, defs)
    if cleaned.get("type") == "object":
        cleaned.setdefault("additionalProperties", False)
    return cleaned


def sanitize_json_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Inline $defs/$ref and strip metadata unsupported by local JSON-schema compilers."""
    defs = schema.get("$defs")
    defs_map = defs if isinstance(defs, dict) else {}
    return _inline_schema_refs(schema, defs_map)


class OpenAICompatibleProvider(AIProvider):
    def __init__(self, config) -> None:
        super().__init__(config)
        self._supports_json_schema: bool | None = None
        self._supports_json_object: bool | None = None
        self._cached_models: list[str] = []

    async def discover_models(self) -> list[str]:
        data = None
        try:
            response = await self._request("GET", "/v1/models")
            data = response.json()
        except ProviderRequestError as exc:
            if exc.status_code == 404:
                try:
                    response = await self._request("GET", "/models")
                    data = response.json()
                except ProviderRequestError:
                    if self.config.model:
                        return [self.config.model]
                    raise
            else:
                raise

        models: list[str] = []
        if isinstance(data, dict):
            raw_items = data.get("data") or data.get("models") or []
        elif isinstance(data, list):
            raw_items = data
        else:
            raw_items = []

        if isinstance(raw_items, list):
            for item in raw_items:
                if isinstance(item, dict):
                    mid = item.get("id") or item.get("name")
                    if isinstance(mid, str) and mid.strip():
                        models.append(mid.strip())
                elif isinstance(item, str) and item.strip():
                    models.append(item.strip())

        unique_models = list(dict.fromkeys(models))
        if self.config.model and self.config.model not in unique_models:
            unique_models.insert(0, self.config.model)
        self._cached_models = unique_models
        return unique_models

    def _response_format_candidates(
        self,
        *,
        response_schema: dict[str, Any] | None,
        schema_name: str,
    ) -> list[tuple[str, dict[str, Any] | None]]:
        candidates: list[tuple[str, dict[str, Any] | None]] = []
        if response_schema is not None and self._supports_json_schema is not False:
            candidates.append(
                (
                    "json_schema",
                    {
                        "type": "json_schema",
                        "json_schema": {
                            "name": schema_name,
                            "strict": True,
                            "schema": sanitize_json_schema(response_schema),
                        },
                    },
                )
            )
        # LM Studio's OpenAI layer rejects {"type": "json_object"} with HTTP 400.
        if self.config.kind != ProviderKind.lm_studio and self._supports_json_object is not False:
            candidates.append(("json_object", {"type": "json_object"}))
        candidates.append(("prompt_only", None))
        return candidates

    async def complete(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        *,
        response_schema: dict[str, Any] | None = None,
        schema_name: str = "structured_output",
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
            raise ProviderRequestError("No model specified and could not discover models from OpenAI-compatible provider.")

        candidates = self._response_format_candidates(
            response_schema=response_schema,
            schema_name=schema_name,
        )
        response = None
        used_mode = "prompt_only"
        async with self._inference_slot(effective_model) as lease:
            for idx, (mode, response_format) in enumerate(candidates):
                body: dict[str, Any] = {
                    "model": effective_model,
                    "messages": messages,
                }
                if response_format is not None:
                    body["response_format"] = response_format
                try:
                    response = await self._request("POST", "/v1/chat/completions", json=body)
                    used_mode = mode
                    break
                except ProviderRequestError as exc:
                    has_fallback = idx + 1 < len(candidates)
                    if exc.status_code not in {400, 422} or not has_fallback:
                        raise
                    if mode == "json_schema":
                        self._supports_json_schema = False
                    elif mode == "json_object":
                        self._supports_json_object = False
                    logger.warning(
                        "Structured output mode '%s' rejected with HTTP %s for kind=%s model=%s; falling back (%s).",
                        mode,
                        exc.status_code,
                        self.config.kind.value,
                        effective_model,
                        str(exc),
                    )
        assert response is not None
        data = response.json()
        choices = data.get("choices") or []
        content = None
        if choices and isinstance(choices[0], dict):
            first_choice = choices[0]
            msg = first_choice.get("message")
            if isinstance(msg, dict):
                content = msg.get("content")
                if content is None and "reasoning_content" in msg:
                    content = msg.get("reasoning_content")
            elif isinstance(first_choice.get("text"), str):
                content = first_choice.get("text")
        elif isinstance(data.get("content"), str):
            content = data.get("content")
        elif isinstance(data.get("response"), str):
            content = data.get("response")

        if not isinstance(content, str):
            raise ProviderRequestError("OpenAI-compatible provider returned no structured message content.")
        usage = data.get("usage") or {}
        return {
            "content": content,
            "model": data.get("model") or effective_model,
            "response_format_mode": used_mode,
            "queue_wait_seconds": round(lease.wait_seconds, 3),
            "usage": {
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
                "total_tokens": usage.get("total_tokens"),
            },
        }
