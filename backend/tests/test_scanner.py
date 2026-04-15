from __future__ import annotations

from app.models.schemas import AppConfig, Exchange, OrderBook, Ticker
from app.services.scanner import Scanner


class FakeProvider:
    exchange = Exchange.BINANCE

    def __init__(self, ticker: Ticker, order_book: OrderBook, klines):
        self._ticker = ticker
        self._order_book = order_book
        self._klines = klines

    async def get_ticker(self, pair: str):
        return self._ticker

    async def get_order_book(self, pair: str):
        return self._order_book

    async def get_klines(self, pair: str, interval: str = "5m", limit: int = 100):
        return self._klines

    async def close(self):
        return None


def test_scan_all_returns_opportunities(monkeypatch, sample_ticker, sample_order_book, sample_klines):
    monkeypatch.setattr(Scanner, "_init_providers", lambda self: None)
    config = AppConfig(enabled_exchanges=[Exchange.BINANCE], enabled_pairs=["BTC_BRL"])
    scanner = Scanner(config)
    scanner._providers = {
        Exchange.BINANCE: FakeProvider(sample_ticker, sample_order_book, sample_klines)
    }

    import asyncio

    opportunities = asyncio.run(scanner.scan_all())

    assert len(opportunities) == 1
    assert opportunities[0].pair == "BTC_BRL"
    assert opportunities[0].score > 0


def test_scan_all_enriches_cross_exchange_context(monkeypatch, sample_order_book, sample_klines):
    monkeypatch.setattr(Scanner, "_init_providers", lambda self: None)
    config = AppConfig(
        enabled_exchanges=[Exchange.BINANCE, Exchange.NOVADAX],
        enabled_pairs=["BTC_BRL"],
    )
    scanner = Scanner(config)
    scanner._providers = {
        Exchange.BINANCE: FakeProvider(
            Ticker(
                exchange=Exchange.BINANCE,
                pair="BTC_BRL",
                last_price=120.0,
                high_24h=125.0,
                low_24h=118.0,
                volume_24h=2000.0,
                quote_volume_24h=250000.0,
                change_pct_24h=2.0,
            ),
            sample_order_book,
            sample_klines,
        ),
        Exchange.NOVADAX: FakeProvider(
            Ticker(
                exchange=Exchange.NOVADAX,
                pair="BTC_BRL",
                last_price=123.0,
                high_24h=126.0,
                low_24h=119.0,
                volume_24h=1800.0,
                quote_volume_24h=240000.0,
                change_pct_24h=2.3,
            ),
            sample_order_book,
            sample_klines,
        ),
    }

    import asyncio

    opportunities = asyncio.run(scanner.scan_all())

    assert len(opportunities) == 2
    assert all(opportunity.cross_exchange_gap_pct > 0 for opportunity in opportunities)
    assert any(opportunity.arbitrage_available for opportunity in opportunities)
