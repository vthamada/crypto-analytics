from __future__ import annotations

import abc
import logging
from datetime import datetime

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.models.schemas import Exchange, Ticker, OrderBook, Trade, Kline

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
        retry=retry_if_exception_type((httpx.HTTPStatusError, RateLimitError)),
    )
    async def _request(self, method: str, path: str, **kwargs) -> dict | list:
        client = await self._get_client()
        response = await client.request(method, path, **kwargs)
        if response.status_code == 429:
            logger.warning(f"[{self.exchange}] Rate limit hit on {path}")
            raise RateLimitError(f"Rate limit on {path}")
        response.raise_for_status()
        return response.json()

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
