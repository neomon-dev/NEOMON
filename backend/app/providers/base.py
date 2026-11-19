import asyncio
import ipaddress
import json
import logging
import re
import socket
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import urlsplit

import httpx

from app.config import get_settings
from app.providers.limiter import (
    QueueLease,
    build_limiter_key,
    default_concurrency_for,
    provider_concurrency_registry,
)
from app.schemas import ProviderConfigRequest, ProviderKind, ProviderStatus


logger = logging.getLogger(__name__)
_BEARER_RE = re.compile(r"Bearer\s+\S+", re.IGNORECASE)


def _sanitize_error_text(value: str, limit: int = 500) -> str:
    collapsed = " ".join(value.split())
    redacted = _BEARER_RE.sub("Bearer [REDACTED]", collapsed)
    if len(redacted) > limit:
        return redacted[:limit] + "..."
    return redacted


def _extract_http_error_detail(response: httpx.Response) -> tuple[str | None, str | None, str | None]:
    """Return (error_message, error_type, sanitized_body) from an HTTP error response."""
    raw_text = ""
    try:
        raw_text = response.text or ""
    except Exception:
        return None, None, None
    sanitized_body = _sanitize_error_text(raw_text) if raw_text.strip() else None
    if not sanitized_body:
        return None, None, None
    try:
        parsed = json.loads(raw_text)
    except (ValueError, TypeError):
        return None, None, sanitized_body
    if isinstance(parsed, dict):
        err = parsed.get("error")
        if isinstance(err, dict):
            msg = err.get("message")
            err_type = err.get("type") or err.get("code")
            return (
                _sanitize_error_text(str(msg)) if msg else None,
                _sanitize_error_text(str(err_type), limit=120) if err_type else None,
                sanitized_body,
            )
        msg = parsed.get("message") or parsed.get("detail") or (err if isinstance(err, str) else None)
        err_type = parsed.get("type") or parsed.get("code")
        return (
            _sanitize_error_text(str(msg)) if msg else None,
            _sanitize_error_text(str(err_type), limit=120) if err_type else None,
            sanitized_body,
        )
    return None, None, sanitized_body


class ProviderRequestError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        error_type: str | None = None,
        error_message: str | None = None,
        response_body: str | None = None,
        model: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_type = error_type
        self.error_message = error_message
        self.response_body = response_body
        self.model = model


LOCAL_RUNTIME_PORTS: dict[ProviderKind, set[int]] = {
    ProviderKind.ollama: {11434},
    ProviderKind.lm_studio: {1234},
}

BLOCKED_SSRF_PORTS: set[int] = {
    21,   # FTP
    22,   # SSH
    23,   # Telnet
    25,   # SMTP
    53,   # DNS
    110,  # POP3
    111,  # RPC
    135,  # RPC
    137,  # NetBIOS
    138,  # NetBIOS
    139,  # NetBIOS
    445,  # SMB
}

PRIVATE_LAN_NETWORKS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
)


def _is_private_lan(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Return True if the IP address belongs to standard RFC 1918 private IPv4 networks."""
    if isinstance(ip, ipaddress.IPv4Address):
        return any(ip in net for net in PRIVATE_LAN_NETWORKS)
    return False


def _format_network_error(exc: Exception, endpoint: str, timeout: float) -> str:
    """Format network and timeout exceptions into actionable diagnostic messages."""
    ep_netloc = urlsplit(endpoint).netloc or endpoint
    if isinstance(exc, httpx.ConnectError):
        return (
            f"Connection refused or unreachable at {ep_netloc}. "
            f"Verify the local model server (LM Studio, Ollama, etc.) is running and listening on the configured address and port (e.g., host bound to 0.0.0.0 for LAN access)."
        )
    if isinstance(exc, httpx.ConnectTimeout):
        return (
            f"Connection timed out attempting to reach {ep_netloc}. "
            f"Check host reachability, LAN IP/firewall configuration, and server responsiveness."
        )
    if isinstance(exc, httpx.ReadTimeout):
        return (
            f"Inference request to {ep_netloc} timed out after {timeout:.0f}s. "
            f"The local model may still be loading weights into VRAM/RAM or requires more generation time. Consider increasing inference timeout."
        )
    if isinstance(exc, httpx.WriteTimeout):
        return f"Sending request payload to {ep_netloc} timed out."
    if isinstance(exc, httpx.PoolTimeout):
        return f"Connection pool exhausted waiting to connect to {ep_netloc}."
    if isinstance(exc, httpx.TimeoutException):
        return f"Request to {ep_netloc} timed out after {timeout:.0f}s."
    if isinstance(exc, httpx.NetworkError):
        return f"Network error connecting to {ep_netloc}: {exc}"
    return f"Request to {ep_netloc} failed: {exc}"


def _get_local_interface_ips() -> set[str]:
    """Return non-link-local IP addresses bound to the local host."""
    local_ips: set[str] = set()
    try:
        entries = socket.getaddrinfo(socket.gethostname(), None)
    except OSError:
        return local_ips
    for entry in entries:
        raw_ip = entry[4][0].split("%", 1)[0]
        try:
            ip = ipaddress.ip_address(raw_ip)
        except ValueError:
            continue
        if not (ip.is_link_local or ip.is_multicast or ip.is_unspecified):
            local_ips.add(str(ip).lower())
    return local_ips


async def validate_provider_endpoint(
    endpoint: str,
    kind: ProviderKind,
    *,
    allow_local_runtime: bool = False,
) -> None:
    """Validate provider endpoint against SSRF while allowing explicitly authorized local runtimes."""
    parts = urlsplit(endpoint)
    if parts.scheme not in {"http", "https"}:
        raise ProviderRequestError("Provider endpoint must use http:// or https://.")
    if parts.username is not None or parts.password is not None:
        raise ProviderRequestError("Provider endpoint must not include embedded credentials.")
    hostname = (parts.hostname or "").strip().lower().rstrip(".")
    if not hostname:
        raise ProviderRequestError("Provider endpoint must include a hostname.")
    try:
        explicit_port = parts.port
    except ValueError as exc:
        raise ProviderRequestError("Provider endpoint port is invalid.") from exc
    resolved_port = explicit_port if explicit_port is not None else (443 if parts.scheme == "https" else 80)

    if not (1 <= resolved_port <= 65535):
        raise ProviderRequestError("Provider endpoint port is invalid.")
    if resolved_port in BLOCKED_SSRF_PORTS:
        raise ProviderRequestError(f"Port {resolved_port} is restricted for security reasons.")

    settings = get_settings()
    configured_local_hosts = {
        host.strip().lower().rstrip(".")
        for host in settings.allowed_local_provider_hosts
        if host.strip()
    }
    allowed_local_hosts = configured_local_hosts | _get_local_interface_ips()

    try:
        addresses = await asyncio.to_thread(socket.getaddrinfo, hostname, resolved_port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ProviderRequestError("Provider endpoint hostname could not be resolved.") from exc
    if not addresses:
        raise ProviderRequestError("Provider endpoint hostname did not resolve to any address.")

    for address in addresses:
        raw_ip = address[4][0].split("%", 1)[0]
        ip = ipaddress.ip_address(raw_ip)
        # Never allow link-local (including cloud metadata 169.254.169.254), multicast, or unspecified IPs.
        if ip.is_link_local or ip.is_multicast or ip.is_unspecified:
            raise ProviderRequestError("Link-local, metadata, and multicast provider addresses are not allowed.")
        if ip.is_loopback or ip.is_private:
            if not allow_local_runtime:
                raise ProviderRequestError(
                    "Private and loopback provider addresses are blocked unless explicitly configured for a local runtime."
                )
            if hostname == "localhost" and not ip.is_loopback:
                raise ProviderRequestError(
                    "Localhost provider endpoint resolved to a non-loopback address."
                )
            if not (ip.is_loopback or _is_private_lan(ip) or str(ip).lower() in allowed_local_hosts):
                raise ProviderRequestError(
                    "Local runtime hostname resolved to an unauthorized private address."
                )
        elif ip.is_reserved:
            raise ProviderRequestError("Reserved provider addresses are not allowed.")


def effective_inference_timeout(config: ProviderConfigRequest) -> float:
    if config.inference_timeout_seconds is not None:
        return config.inference_timeout_seconds
    if config.timeout_seconds is not None:
        return config.timeout_seconds
    settings = get_settings()
    if config.kind in {ProviderKind.ollama, ProviderKind.lm_studio} or config.allow_local_runtime:
        return settings.local_inference_timeout_seconds
    return settings.request_timeout_seconds


class GenerationResult:
    def __init__(self, content: str, raw: dict[str, Any]) -> None:
        self.content = content
        self.raw = raw

    def __getitem__(self, item: str) -> Any:
        return self.raw[item]

    def get(self, item: str, default: Any = None) -> Any:
        return self.raw.get(item, default)


class AIProvider(ABC):
    def __init__(self, config: ProviderConfigRequest) -> None:
        self.config = config
        inference_timeout = effective_inference_timeout(config)
        self.inference_timeout_seconds = inference_timeout
        self._client = httpx.AsyncClient(
            base_url=config.endpoint,
            timeout=httpx.Timeout(
                connect=min(30.0, inference_timeout),
                read=inference_timeout,
                write=min(30.0, inference_timeout),
                pool=min(15.0, inference_timeout),
            ),
            headers=self._headers(),
            follow_redirects=False,
        )

    def _normalize_path(self, path: str) -> str:
        """Strip duplicate /v1 or /api path prefix if the client base_url already contains it."""
        ep_parts = urlsplit(self.config.endpoint)
        base_path = ep_parts.path.rstrip("/")
        norm_path = path if path.startswith("/") else "/" + path

        if base_path.endswith("/v1") and (norm_path == "/v1" or norm_path.startswith("/v1/")):
            sub = norm_path[3:]
            return sub if sub.startswith("/") else "/" + sub

        if base_path.endswith("/api") and (norm_path == "/api" or norm_path.startswith("/api/")):
            sub = norm_path[4:]
            return sub if sub.startswith("/") else "/" + sub

        return norm_path

    @asynccontextmanager
    async def _inference_slot(self, model: str | None = None) -> AsyncIterator[QueueLease]:
        settings = get_settings()
        key = build_limiter_key(self.config, model=model)
        queue_timeout = (
            self.config.queue_timeout_seconds
            if self.config.queue_timeout_seconds is not None
            else settings.provider_queue_wait_timeout_seconds
        )
        async with provider_concurrency_registry.acquire(
            key,
            max_concurrency=default_concurrency_for(self.config),
            queue_wait_timeout=queue_timeout,
        ) as lease:
            yield lease

    def _headers(self) -> dict[str, str]:
        if self.config.api_key is None:
            return {}
        return {"Authorization": f"Bearer {self.config.api_key.get_secret_value()}"}

    async def close(self) -> None:
        await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        await validate_provider_endpoint(
            self.config.endpoint,
            self.config.kind,
            allow_local_runtime=self.config.allow_local_runtime,
        )
        target_path = self._normalize_path(path)
        for attempt in range(self.config.retry_count + 1):
            try:
                response = await self._client.request(method, target_path, **kwargs)
                if 300 <= response.status_code < 400:
                    location = response.headers.get("location")
                    if location:
                        target = str(response.url.join(location))
                        await validate_provider_endpoint(
                            target,
                            self.config.kind,
                            allow_local_runtime=self.config.allow_local_runtime,
                        )
                    raise ProviderRequestError(f"Provider redirect ({response.status_code}) is not allowed.")
                if response.status_code >= 500 and attempt < self.config.retry_count:
                    await asyncio.sleep(min(0.25 * (2**attempt), 2))
                    continue
                response.raise_for_status()
                return response
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt >= self.config.retry_count:
                    err_msg = _format_network_error(exc, self.config.endpoint, self.inference_timeout_seconds)
                    raise ProviderRequestError(err_msg) from exc
                await asyncio.sleep(min(0.25 * (2**attempt), 2))
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                err_msg, err_type, body = _extract_http_error_detail(exc.response)
                model_hint = None
                req_json = kwargs.get("json")
                if isinstance(req_json, dict) and isinstance(req_json.get("model"), str):
                    model_hint = req_json["model"]
                detail = err_msg or body
                summary = f"Provider returned HTTP {status}"
                if detail:
                    summary += f": {detail}"
                if err_type:
                    summary += f" (type={err_type})"
                if not summary.endswith("."):
                    summary += "."
                logger.warning(
                    "Provider HTTP error: kind=%s endpoint=%s model=%s status=%s error_type=%s detail=%s",
                    self.config.kind.value,
                    urlsplit(self.config.endpoint).netloc,
                    model_hint or self.config.model,
                    status,
                    err_type,
                    detail or "<empty>",
                )
                raise ProviderRequestError(
                    summary,
                    status_code=status,
                    error_type=err_type,
                    error_message=err_msg,
                    response_body=body,
                    model=model_hint or self.config.model,
                ) from exc
        raise ProviderRequestError("Provider request failed after retries.")

    @abstractmethod
    async def discover_models(self) -> list[str]:
        raise NotImplementedError

    async def test_connection(self) -> ProviderStatus:
        try:
            models = await self.discover_models()
            return ProviderStatus(
                kind=self.config.kind,
                endpoint=self.config.endpoint,
                connected=True,
                models=models,
                api_key_configured=self.config.api_key is not None,
            )
        except ProviderRequestError as exc:
            return ProviderStatus(
                kind=self.config.kind,
                endpoint=self.config.endpoint,
                connected=False,
                error=str(exc),
                api_key_configured=self.config.api_key is not None,
            )

    async def complete(self, messages: list[dict[str, str]], model: str | None = None, **kwargs: Any) -> dict[str, Any]:
        raise ProviderRequestError("Text completion is not enabled in the foundation milestone.")

    async def generate(
        self,
        prompt: str,
        system_instruction: str | None = None,
        model: str | None = None,
    ) -> GenerationResult:
        messages: list[dict[str, str]] = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})
        res = await self.complete(messages, model=model)
        content = res.get("content", "") if isinstance(res, dict) else str(res)
        return GenerationResult(content=content, raw=res if isinstance(res, dict) else {"content": content})
