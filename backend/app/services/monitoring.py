from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass
class ProviderStats:
    requests_total: int = 0
    failures_total: int = 0
    rate_limits_total: int = 0
    last_request_at: datetime | None = None
    last_success_at: datetime | None = None
    last_error_at: datetime | None = None
    last_error: str | None = None
    last_latency_ms: float | None = None


@dataclass
class ScanStats:
    cycles_total: int = 0
    cycles_failed: int = 0
    last_started_at: datetime | None = None
    last_completed_at: datetime | None = None
    last_success_at: datetime | None = None
    last_error: str | None = None
    last_duration_ms: float | None = None
    last_opportunities_count: int = 0
    running: bool = False
    providers: dict[str, ProviderStats] = field(default_factory=dict)

    def begin_cycle(self) -> None:
        self.running = True
        self.last_started_at = utcnow()

    def complete_cycle(self, opportunities_count: int, duration_ms: float) -> None:
        self.running = False
        self.cycles_total += 1
        self.last_completed_at = utcnow()
        self.last_success_at = self.last_completed_at
        self.last_duration_ms = round(duration_ms, 2)
        self.last_opportunities_count = opportunities_count
        self.last_error = None

    def fail_cycle(self, error: str, duration_ms: float | None = None) -> None:
        self.running = False
        self.cycles_total += 1
        self.cycles_failed += 1
        self.last_completed_at = utcnow()
        self.last_error = error
        if duration_ms is not None:
            self.last_duration_ms = round(duration_ms, 2)

    def provider(self, exchange: str) -> ProviderStats:
        if exchange not in self.providers:
            self.providers[exchange] = ProviderStats()
        return self.providers[exchange]

    def record_provider_success(self, exchange: str, latency_ms: float) -> None:
        provider = self.provider(exchange)
        provider.requests_total += 1
        provider.last_request_at = utcnow()
        provider.last_success_at = provider.last_request_at
        provider.last_latency_ms = round(latency_ms, 2)

    def record_provider_failure(
        self,
        exchange: str,
        error: str,
        latency_ms: float | None = None,
        *,
        rate_limited: bool = False,
    ) -> None:
        provider = self.provider(exchange)
        provider.requests_total += 1
        provider.failures_total += 1
        provider.last_request_at = utcnow()
        provider.last_error_at = provider.last_request_at
        provider.last_error = error
        if latency_ms is not None:
            provider.last_latency_ms = round(latency_ms, 2)
        if rate_limited:
            provider.rate_limits_total += 1

    def snapshot(self) -> dict:
        return {
            "cycles_total": self.cycles_total,
            "cycles_failed": self.cycles_failed,
            "last_started_at": self.last_started_at.isoformat() if self.last_started_at else None,
            "last_completed_at": self.last_completed_at.isoformat() if self.last_completed_at else None,
            "last_success_at": self.last_success_at.isoformat() if self.last_success_at else None,
            "last_error": self.last_error,
            "last_duration_ms": self.last_duration_ms,
            "last_opportunities_count": self.last_opportunities_count,
            "running": self.running,
            "providers": {
                exchange: {
                    "requests_total": stats.requests_total,
                    "failures_total": stats.failures_total,
                    "rate_limits_total": stats.rate_limits_total,
                    "last_request_at": stats.last_request_at.isoformat() if stats.last_request_at else None,
                    "last_success_at": stats.last_success_at.isoformat() if stats.last_success_at else None,
                    "last_error_at": stats.last_error_at.isoformat() if stats.last_error_at else None,
                    "last_error": stats.last_error,
                    "last_latency_ms": stats.last_latency_ms,
                }
                for exchange, stats in self.providers.items()
            },
        }


scan_monitor = ScanStats()
