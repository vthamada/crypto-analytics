from __future__ import annotations

import abc
import logging
import time

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.models.schemas import Exchange, Ticker, OrderBook, Trade, Kline
from app.services.monitoring import scan_monitor

logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    pass


class ExchangeProvider(abc.ABC):
    """Base class for exchange data providers."""

    exchange: Exchange
    base_url: str

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(15.0),
                headers={"User-Agent": "CryptoAnalytics/1.0"},
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError, RateLimitError)),
    )
    async def _request(self, method: str, path: str, **kwargs) -> dict | list:
        client = await self._get_client()
        started = time.perf_counter()

        try:
            response = await client.request(method, path, **kwargs)
            latency_ms = (time.perf_counter() - started) * 1000

            if response.status_code == 429:
                scan_monitor.record_provider_failure(
                    self.exchange.value,
                    f"Rate limit on {path}",
                    latency_ms,
                    rate_limited=True,
                )
                logger.warning("[%s] rate_limit path=%s latency_ms=%.2f", self.exchange.value, path, latency_ms)
                raise RateLimitError(f"Rate limit on {path}")

            response.raise_for_status()
            scan_monitor.record_provider_success(self.exchange.value, latency_ms)
            logger.debug("[%s] request_ok path=%s latency_ms=%.2f", self.exchange.value, path, latency_ms)
            return response.json()
        except httpx.HTTPStatusError as exc:
            latency_ms = (time.perf_counter() - started) * 1000
            status_code = exc.response.status_code if exc.response else "unknown"
            scan_monitor.record_provider_failure(
                self.exchange.value,
                f"HTTP {status_code} on {path}",
                latency_ms,
            )
            logger.warning(
                "[%s] request_http_error path=%s status=%s latency_ms=%.2f",
                self.exchange.value,
                path,
                status_code,
                latency_ms,
            )
            raise
        except httpx.RequestError as exc:
            latency_ms = (time.perf_counter() - started) * 1000
            scan_monitor.record_provider_failure(
                self.exchange.value,
                f"{exc.__class__.__name__} on {path}",
                latency_ms,
            )
            logger.warning(
                "[%s] request_transport_error path=%s error=%s latency_ms=%.2f",
                self.exchange.value,
                path,
                exc.__class__.__name__,
                latency_ms,
            )
            raise

    @abc.abstractmethod
    async def get_ticker(self, pair: str) -> Ticker: ...

    @abc.abstractmethod
    async def get_order_book(self, pair: str) -> OrderBook: ...

    @abc.abstractmethod
    async def get_trades(self, pair: str, limit: int = 100) -> list[Trade]: ...

    @abc.abstractmethod
    async def get_klines(self, pair: str, interval: str = "5m", limit: int = 100) -> list[Kline]: ...

    @abc.abstractmethod
    def normalize_pair(self, pair: str) -> str:
        """Convert our internal pair format (BTC_BRL) to exchange-specific format."""
        ...

    @abc.abstractmethod
    async def get_available_pairs(self) -> list[str]:
        """Return list of available pairs in internal format."""
        ...
