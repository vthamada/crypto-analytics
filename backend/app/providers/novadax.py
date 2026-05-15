from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.models.schemas import (
    Exchange, Ticker, OrderBook, OrderBookEntry, Trade, Kline,
)
from app.providers.base import ExchangeProvider

logger = logging.getLogger(__name__)


class NovaDaxProvider(ExchangeProvider):
    exchange = Exchange.NOVADAX
    base_url = "https://api.novadax.com/v1"

    _INACTIVE_STATUSES = {
        "OFFLINE",
        "DISABLED",
        "SUSPENDED",
        "CLOSED",
        "MAINTENANCE",
        "DELISTED",
        "HALT",
        "HALTED",
        "BREAK",
    }
    _QUOTE_SUFFIXES = ("BRL", "USDT", "USD", "BTC", "ETH")

    def normalize_pair(self, pair: str) -> str:
        # Internal: BTC_BRL -> NovaDAX: BTC_BRL. Accept compact symbols too.
        return self._normalize_symbol(pair) or pair.upper()

    @classmethod
    def _normalize_symbol(cls, symbol: str | None) -> str | None:
        if not symbol:
            return None
        normalized = str(symbol).strip().upper().replace("/", "_").replace("-", "_")
        normalized = "_".join(part for part in normalized.split("_") if part)
        if not normalized:
            return None
        if "_" in normalized:
            base, quote, *_ = normalized.split("_")
            if base and quote:
                return f"{base}_{quote}"
            return None
        for quote in cls._QUOTE_SUFFIXES:
            if normalized.endswith(quote) and len(normalized) > len(quote):
                return f"{normalized[:-len(quote)]}_{quote}"
        return normalized

    @staticmethod
    def _extract_field(payload: dict, names: tuple[str, ...]) -> str | None:
        lower_lookup = {str(key).lower(): value for key, value in payload.items()}
        for name in names:
            value = lower_lookup.get(name.lower())
            if value not in (None, ""):
                return str(value)
        return None

    @classmethod
    def _extract_symbol_from_payload(cls, payload: dict) -> str | None:
        direct_symbol = cls._extract_field(payload, ("symbol", "name", "code"))
        normalized_symbol = cls._normalize_symbol(direct_symbol)
        if normalized_symbol:
            return normalized_symbol

        base = cls._extract_field(payload, ("baseCurrency", "base_currency", "base", "baseAsset"))
        quote = cls._extract_field(payload, ("quoteCurrency", "quote_currency", "quote", "quoteAsset"))
        if base and quote:
            return cls._normalize_symbol(f"{base}_{quote}")
        return None

    @classmethod
    def _is_symbol_active(cls, payload: dict) -> bool:
        raw_status = cls._extract_field(payload, ("status", "state", "tradeStatus"))
        if raw_status in (None, ""):
            return True
        return raw_status.strip().upper() not in cls._INACTIVE_STATUSES

    @staticmethod
    def _extract_kline_timestamp(payload: dict) -> int | None:
        for field in ("timestamp", "time", "ts", "t", "score"):
            raw_value = payload.get(field)
            if raw_value in (None, ""):
                continue
            try:
                return int(raw_value)
            except (TypeError, ValueError):
                continue
        return None

    async def get_available_pairs(self) -> list[str]:
        data = await self._request("GET", "/common/symbols")
        raw_items = data.get("data", []) if isinstance(data, dict) else data
        pairs = []
        for item in raw_items or []:
            if not isinstance(item, dict) or not self._is_symbol_active(item):
                continue
            symbol = self._extract_symbol_from_payload(item)
            if symbol and symbol.endswith("_BRL"):
                pairs.append(symbol)
        return sorted(set(pairs))

    async def get_ticker(self, pair: str) -> Ticker:
        symbol = self.normalize_pair(pair)
        data = await self._request("GET", "/market/ticker", params={"symbol": symbol})
        d = data["data"]
        last_price = float(d["lastPrice"])
        open_24h = float(d.get("open24h") or 0)
        change_pct_24h = (
            float(d["change24h"] or 0) * 100
            if "change24h" in d
            else ((last_price - open_24h) / open_24h * 100 if open_24h > 0 else 0.0)
        )
        return Ticker(
            exchange=self.exchange,
            pair=pair,
            last_price=last_price,
            high_24h=float(d["high24h"]),
            low_24h=float(d["low24h"]),
            volume_24h=float(d["baseVolume24h"]),
            quote_volume_24h=float(d["quoteVolume24h"]),
            change_pct_24h=change_pct_24h,
            timestamp=datetime.now(timezone.utc),
        )

    async def get_order_book(self, pair: str) -> OrderBook:
        symbol = self.normalize_pair(pair)
        data = await self._request("GET", "/market/depth", params={"symbol": symbol, "limit": 20})
        d = data["data"]
        return OrderBook(
            exchange=self.exchange,
            pair=pair,
            bids=[OrderBookEntry(price=float(b[0]), quantity=float(b[1])) for b in d.get("bids", [])],
            asks=[OrderBookEntry(price=float(a[0]), quantity=float(a[1])) for a in d.get("asks", [])],
        )

    async def get_trades(self, pair: str, limit: int = 100) -> list[Trade]:
        symbol = self.normalize_pair(pair)
        data = await self._request(
            "GET", "/market/trades", params={"symbol": symbol, "limit": limit}
        )
        trades = []
        for t in data.get("data", []):
            trades.append(Trade(
                exchange=self.exchange,
                pair=pair,
                price=float(t["price"]),
                quantity=float(t["amount"]),
                side=t.get("side", "buy").lower(),
                timestamp=datetime.fromtimestamp(int(t["timestamp"]) / 1000, tz=timezone.utc),
            ))
        return trades

    async def get_klines(self, pair: str, interval: str = "5m", limit: int = 100) -> list[Kline]:
        symbol = self.normalize_pair(pair)
        # NovaDAX KlineUnitEnum: ONE_MIN, FIVE_MIN, FIFTEEN_MIN, HALF_HOU, ONE_HOU, ONE_DAY, ONE_WEE, ONE_MON
        unit_map = {
            "1m": "ONE_MIN", "5m": "FIVE_MIN", "15m": "FIFTEEN_MIN",
            "30m": "HALF_HOU", "1h": "ONE_HOU", "1d": "ONE_DAY",
        }
        unit = unit_map.get(interval, "FIVE_MIN")
        interval_seconds = {
            "1m": 60, "5m": 300, "15m": 900, "30m": 1800, "1h": 3600, "1d": 86400,
        }.get(interval, 300)

        import time
        to_ts = int(time.time())
        from_ts = to_ts - interval_seconds * limit

        try:
            data = await self._request(
                "GET", "/market/kline/history",
                params={
                    "symbol": symbol,
                    "unit": unit,
                    "period": 1,
                    "from": from_ts,
                    "to": to_ts,
                },
            )
        except Exception as e:
            logger.debug(f"[NovaDAX] klines {pair} failed: {e}")
            return []

        klines = []
        for k in data.get("data", []):
            timestamp = self._extract_kline_timestamp(k)
            if timestamp is None:
                logger.debug("[NovaDAX] skipping kline without timestamp for %s: %s", pair, k)
                continue
            klines.append(Kline(
                open_time=datetime.fromtimestamp(timestamp, tz=timezone.utc),
                open=float(k["openPrice"]),
                high=float(k["highPrice"]),
                low=float(k["lowPrice"]),
                close=float(k["closePrice"]),
                volume=float(k.get("vol", k.get("amount", 0))),
            ))
        return klines
