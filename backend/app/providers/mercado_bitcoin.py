from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.models.schemas import (
    Exchange, Ticker, OrderBook, OrderBookEntry, Trade, Kline,
)
from app.providers.base import ExchangeProvider

logger = logging.getLogger(__name__)


class MercadoBitcoinProvider(ExchangeProvider):
    exchange = Exchange.MERCADO_BITCOIN
    base_url = "https://www.mercadobitcoin.net/api"

    def normalize_pair(self, pair: str) -> str:
        # Internal: BTC_BRL -> MB: BTC (just the base currency for v3 API)
        return pair.replace("_BRL", "").upper()

    async def get_available_pairs(self) -> list[str]:
        # MB doesn't have a clean symbols endpoint; return known BRL pairs
        known = ["BTC", "ETH", "SOL", "ADA", "XRP", "DOGE", "DOT", "AVAX", "MATIC", "LINK", "LTC", "UNI"]
        return [f"{c}_BRL" for c in known]

    async def get_ticker(self, pair: str) -> Ticker:
        coin = self.normalize_pair(pair)
        data = await self._request("GET", f"/{coin}/ticker/")
        d = data["ticker"]
        last = float(d["last"])
        high = float(d["high"])
        low = float(d["low"])
        vol = float(d["vol"])
        # MB doesn't directly give 24h change %, calculate from open
        open_price = float(d.get("open", last))
        change_pct = ((last - open_price) / open_price * 100) if open_price else 0.0
        return Ticker(
            exchange=self.exchange,
            pair=pair,
            last_price=last,
            high_24h=high,
            low_24h=low,
            volume_24h=vol,
            quote_volume_24h=vol * last,
            change_pct_24h=change_pct,
            timestamp=datetime.now(timezone.utc),
        )

    async def get_order_book(self, pair: str) -> OrderBook:
        coin = self.normalize_pair(pair)
        data = await self._request("GET", f"/{coin}/orderbook/")
        return OrderBook(
            exchange=self.exchange,
            pair=pair,
            bids=[OrderBookEntry(price=float(b[0]), quantity=float(b[1])) for b in data.get("bids", [])[:20]],
            asks=[OrderBookEntry(price=float(a[0]), quantity=float(a[1])) for a in data.get("asks", [])[:20]],
        )

    async def get_trades(self, pair: str, limit: int = 100) -> list[Trade]:
        coin = self.normalize_pair(pair)
        data = await self._request("GET", f"/{coin}/trades/")
        trades = []
        for t in data[-limit:]:
            trades.append(Trade(
                exchange=self.exchange,
                pair=pair,
                price=float(t["price"]),
                quantity=float(t["amount"]),
                side=t.get("type", "buy").lower(),
                timestamp=datetime.fromtimestamp(int(t["date"]), tz=timezone.utc),
            ))
        return trades

    async def get_klines(self, pair: str, interval: str = "5m", limit: int = 100) -> list[Kline]:
        # MB v3 public API doesn't have klines easily; derive from trades
        trades = await self.get_trades(pair, limit=500)
        if not trades:
            return []

        # Aggregate trades into approximate candles
        interval_seconds = {"1m": 60, "5m": 300, "15m": 900, "30m": 1800, "1h": 3600}.get(interval, 300)
        klines: list[Kline] = []

        if not trades:
            return klines

        trades.sort(key=lambda t: t.timestamp)
        bucket_start = trades[0].timestamp
        bucket_trades: list[Trade] = []

        for trade in trades:
            if (trade.timestamp - bucket_start).total_seconds() < interval_seconds:
                bucket_trades.append(trade)
            else:
                if bucket_trades:
                    klines.append(self._aggregate_candle(bucket_trades, bucket_start))
                bucket_start = trade.timestamp
                bucket_trades = [trade]

        if bucket_trades:
            klines.append(self._aggregate_candle(bucket_trades, bucket_start))

        return klines[-limit:]

    @staticmethod
    def _aggregate_candle(trades: list[Trade], open_time: datetime) -> Kline:
        prices = [t.price for t in trades]
        return Kline(
            open_time=open_time,
            open=prices[0],
            high=max(prices),
            low=min(prices),
            close=prices[-1],
            volume=sum(t.quantity for t in trades),
        )
