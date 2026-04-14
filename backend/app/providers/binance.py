from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.models.schemas import (
    Exchange, Ticker, OrderBook, OrderBookEntry, Trade, Kline,
)
from app.providers.base import ExchangeProvider

logger = logging.getLogger(__name__)


class BinanceProvider(ExchangeProvider):
    exchange = Exchange.BINANCE
    base_url = "https://api.binance.com/api/v3"

    def normalize_pair(self, pair: str) -> str:
        # Internal: BTC_BRL -> Binance: BTCBRL (no separator)
        # Also handle USDT pairs: BTC_USDT -> BTCUSDT
        return pair.replace("_", "").upper()

    async def get_available_pairs(self) -> list[str]:
        try:
            data = await self._request("GET", "/exchangeInfo")
            pairs = []
            for s in data.get("symbols", []):
                symbol = s["symbol"]
                if symbol.endswith("BRL") or symbol.endswith("USDT"):
                    base = s["baseAsset"]
                    quote = s["quoteAsset"]
                    pairs.append(f"{base}_{quote}")
            return pairs
        except Exception as e:
            logger.error(f"[Binance] Failed to get pairs: {e}")
            return []

    async def get_ticker(self, pair: str) -> Ticker:
        symbol = self.normalize_pair(pair)
        data = await self._request("GET", "/ticker/24hr", params={"symbol": symbol})
        return Ticker(
            exchange=self.exchange,
            pair=pair,
            last_price=float(data["lastPrice"]),
            high_24h=float(data["highPrice"]),
            low_24h=float(data["lowPrice"]),
            volume_24h=float(data["volume"]),
            quote_volume_24h=float(data["quoteVolume"]),
            change_pct_24h=float(data["priceChangePercent"]),
            timestamp=datetime.now(timezone.utc),
        )

    async def get_order_book(self, pair: str) -> OrderBook:
        symbol = self.normalize_pair(pair)
        data = await self._request("GET", "/depth", params={"symbol": symbol, "limit": 20})
        return OrderBook(
            exchange=self.exchange,
            pair=pair,
            bids=[OrderBookEntry(price=float(b[0]), quantity=float(b[1])) for b in data.get("bids", [])],
            asks=[OrderBookEntry(price=float(a[0]), quantity=float(a[1])) for a in data.get("asks", [])],
        )

    async def get_trades(self, pair: str, limit: int = 100) -> list[Trade]:
        symbol = self.normalize_pair(pair)
        data = await self._request("GET", "/trades", params={"symbol": symbol, "limit": limit})
        trades = []
        for t in data:
            trades.append(Trade(
                exchange=self.exchange,
                pair=pair,
                price=float(t["price"]),
                quantity=float(t["qty"]),
                side="sell" if t.get("isBuyerMaker") else "buy",
                timestamp=datetime.fromtimestamp(int(t["time"]) / 1000, tz=timezone.utc),
            ))
        return trades

    async def get_klines(self, pair: str, interval: str = "5m", limit: int = 100) -> list[Kline]:
        symbol = self.normalize_pair(pair)
        data = await self._request(
            "GET", "/klines",
            params={"symbol": symbol, "interval": interval, "limit": limit},
        )
        klines = []
        for k in data:
            klines.append(Kline(
                open_time=datetime.fromtimestamp(int(k[0]) / 1000, tz=timezone.utc),
                open=float(k[1]),
                high=float(k[2]),
                low=float(k[3]),
                close=float(k[4]),
                volume=float(k[5]),
                close_time=datetime.fromtimestamp(int(k[6]) / 1000, tz=timezone.utc),
            ))
        return klines
