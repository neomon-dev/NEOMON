import asyncio
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

from app.config import get_settings
from app.schemas import ProviderConfigRequest, ProviderKind

InferenceStateCallback = Callable[[str, dict[str, Any]], Awaitable[None]]

_inference_state_callback: ContextVar[InferenceStateCallback | None] = ContextVar(
    "neomon_inference_state_callback",
    default=None,
)


class ProviderQueueTimeoutError(RuntimeError):
    """Raised when a queued inference request exceeds its queue wait deadline."""


@dataclass(frozen=True)
class ProviderLimiterKey:
    kind: str
    endpoint: str
    model: str


@dataclass(frozen=True)
class QueueLease:
    key: ProviderLimiterKey
    wait_seconds: float
    max_concurrency: int


@asynccontextmanager
async def inference_state_listener(
    callback: InferenceStateCallback | None,
) -> AsyncIterator[None]:
    if callback is None:
        yield
        return
    token = _inference_state_callback.set(callback)
    try:
        yield
    finally:
        _inference_state_callback.reset(token)


def build_limiter_key(
    config: ProviderConfigRequest,
    model: str | None = None,
) -> ProviderLimiterKey:
    normalized_endpoint = config.endpoint.strip().rstrip("/").lower()
    effective_model = (model if model is not None else config.model or "").strip()
    return ProviderLimiterKey(
        kind=config.kind.value,
        endpoint=normalized_endpoint,
        model=effective_model,
    )


def default_concurrency_for(config: ProviderConfigRequest) -> int:
    settings = get_settings()
    if config.kind in {ProviderKind.lm_studio, ProviderKind.ollama}:
        return settings.local_provider_max_concurrency
    return settings.remote_provider_max_concurrency


class ProviderConcurrencyRegistry:
    """Shared per-(kind, endpoint, model) inference limiter using FIFO asyncio semaphores."""

    def __init__(self) -> None:
        self._semaphores: dict[ProviderLimiterKey, tuple[int, asyncio.Semaphore]] = {}

    def get_semaphore(self, key: ProviderLimiterKey, max_concurrency: int) -> asyncio.Semaphore:
        limit = max(1, max_concurrency)
        entry = self._semaphores.get(key)
        if entry is None or entry[0] != limit:
            semaphore = asyncio.Semaphore(limit)
            self._semaphores[key] = (limit, semaphore)
            return semaphore
        return entry[1]

    def reset(self) -> None:
        self._semaphores.clear()

    @asynccontextmanager
    async def acquire(
        self,
        key: ProviderLimiterKey,
        *,
        max_concurrency: int,
        queue_wait_timeout: float | None = None,
        on_state_change: InferenceStateCallback | None = None,
    ) -> AsyncIterator[QueueLease]:
        callback = on_state_change or _inference_state_callback.get()
        semaphore = self.get_semaphore(key, max_concurrency)
        enqueue_time = time.monotonic()
        if callback is not None:
            await callback(
                "waiting_in_queue",
                {"kind": key.kind, "endpoint": key.endpoint, "model": key.model},
            )

        acquire_task = asyncio.create_task(semaphore.acquire())
        acquired = False
        handed_off = False
        try:
            if queue_wait_timeout is not None:
                done, _ = await asyncio.wait({acquire_task}, timeout=queue_wait_timeout)
                if acquire_task not in done:
                    raise ProviderQueueTimeoutError(
                        f"Timed out waiting {queue_wait_timeout:.0f}s in provider queue for {key.kind}."
                    )
                await acquire_task
            else:
                await acquire_task
            acquired = True
            handed_off = True
            wait_seconds = time.monotonic() - enqueue_time
            if callback is not None:
                await callback(
                    "generating",
                    {
                        "kind": key.kind,
                        "endpoint": key.endpoint,
                        "model": key.model,
                        "queue_wait_seconds": round(wait_seconds, 3),
                    },
                )
            yield QueueLease(
                key=key,
                wait_seconds=wait_seconds,
                max_concurrency=max(1, max_concurrency),
            )
        finally:
            if acquired:
                semaphore.release()
            elif not handed_off:
                acquire_task.cancel()

                def _release_if_acquired(task: asyncio.Task[bool]) -> None:
                    if not task.cancelled() and task.exception() is None:
                        semaphore.release()

                acquire_task.add_done_callback(_release_if_acquired)


provider_concurrency_registry = ProviderConcurrencyRegistry()
