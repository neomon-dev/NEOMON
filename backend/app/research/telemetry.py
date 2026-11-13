from dataclasses import dataclass, field
import time
from typing import Any


@dataclass
class TavilyTelemetry:
    queries_submitted: int = 0
    search_requests_completed: int = 0
    search_requests_failed: int = 0
    results_discovered: int = 0
    results_retained: int = 0
    sources_accepted: int = 0
    sources_rejected: int = 0
    full_text_successes: int = 0
    full_text_failures: int = 0
    evidence_passages_extracted: int = 0
    total_latency_ms: float = 0.0
    last_latency_ms: float = 0.0
    error_categories: dict[str, int] = field(
        default_factory=lambda: {
            "auth": 0,
            "rate_limit": 0,
            "timeout": 0,
            "network": 0,
            "validation": 0,
            "other": 0,
        }
    )

    def record_request_start(self) -> float:
        self.queries_submitted += 1
        return time.perf_counter()

    def record_request_success(self, start_time: float, result_count: int) -> None:
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        self.search_requests_completed += 1
        self.results_discovered += result_count
        self.total_latency_ms += duration_ms
        self.last_latency_ms = round(duration_ms, 2)

    def record_request_failure(self, start_time: float, category: str) -> None:
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        self.search_requests_failed += 1
        self.total_latency_ms += duration_ms
        self.last_latency_ms = round(duration_ms, 2)
        if category in self.error_categories:
            self.error_categories[category] += 1
        else:
            self.error_categories["other"] += 1

    @property
    def avg_latency_ms(self) -> float:
        total_reqs = self.search_requests_completed + self.search_requests_failed
        return round(self.total_latency_ms / max(1, total_reqs), 2)

    def get_summary(self) -> dict[str, Any]:
        return {
            "queries_submitted": self.queries_submitted,
            "search_requests_completed": self.search_requests_completed,
            "search_requests_failed": self.search_requests_failed,
            "results_discovered": self.results_discovered,
            "results_retained": self.results_retained,
            "sources_accepted": self.sources_accepted,
            "sources_rejected": self.sources_rejected,
            "full_text_successes": self.full_text_successes,
            "full_text_failures": self.full_text_failures,
            "evidence_passages_extracted": self.evidence_passages_extracted,
            "last_latency_ms": self.last_latency_ms,
            "avg_latency_ms": self.avg_latency_ms,
            "error_categories": dict(self.error_categories),
        }

    def reset(self) -> None:
        self.queries_submitted = 0
        self.search_requests_completed = 0
        self.search_requests_failed = 0
        self.results_discovered = 0
        self.results_retained = 0
        self.sources_accepted = 0
        self.sources_rejected = 0
        self.full_text_successes = 0
        self.full_text_failures = 0
        self.evidence_passages_extracted = 0
        self.total_latency_ms = 0.0
        self.last_latency_ms = 0.0
        for k in self.error_categories:
            self.error_categories[k] = 0


tavily_telemetry = TavilyTelemetry()
