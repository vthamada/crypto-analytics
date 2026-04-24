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
    async def fake_scannable_pairs(self):
        return {Exchange.BINANCE: ["BTC_BRL"]}

    monkeypatch.setattr(
        Scanner,
        "_get_scannable_pairs_by_exchange",
        fake_scannable_pairs,
    )
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
    assert opportunities[0].bid_notional_top_n is not None
    assert opportunities[0].ask_notional_top_n is not None
    assert opportunities[0].total_notional_top_n is not None
    assert opportunities[0].estimated_buy_slippage_bps is not None
    assert opportunities[0].estimated_sell_slippage_bps is not None
    assert opportunities[0].fillable_notional_within_slippage_cap is not None
    assert opportunities[0].executability_score is not None
    assert opportunities[0].executability_band is not None
    assert opportunities[0].interesting_signal is True
    assert opportunities[0].operable_signal in {True, False}
    assert opportunities[0].movement_regime is not None
    assert opportunities[0].movement_persistence_score is not None
    assert opportunities[0].baseline_order_notional_brl is not None
    assert opportunities[0].duration_minutes > 0


def test_scan_all_uses_workspace_operability_thresholds(monkeypatch, sample_ticker, sample_order_book, sample_klines):
    monkeypatch.setattr(Scanner, "_init_providers", lambda self: None)

    async def fake_scannable_pairs(self):
        return {Exchange.BINANCE: ["BTC_BRL"]}

    monkeypatch.setattr(Scanner, "_get_scannable_pairs_by_exchange", fake_scannable_pairs)
    strict_config = AppConfig(
        enabled_exchanges=[Exchange.BINANCE],
        enabled_pairs=["BTC_BRL"],
        min_quote_volume_brl=500000.0,
        max_entry_slippage_bps=500.0,
        max_exit_slippage_bps=500.0,
    )
    scanner = Scanner(strict_config)
    scanner._providers = {
        Exchange.BINANCE: FakeProvider(sample_ticker, sample_order_book, sample_klines)
    }

    import asyncio

    opportunities = asyncio.run(scanner.scan_all())

    assert len(opportunities) == 1
    assert opportunities[0].interesting_signal is True
    assert opportunities[0].operable_signal is False


def test_scan_all_enriches_cross_exchange_context(monkeypatch, sample_order_book, sample_klines):
    monkeypatch.setattr(Scanner, "_init_providers", lambda self: None)
    async def fake_scannable_pairs(self):
        return {
            Exchange.BINANCE: ["BTC_BRL"],
            Exchange.NOVADAX: ["BTC_BRL"],
        }

    monkeypatch.setattr(
        Scanner,
        "_get_scannable_pairs_by_exchange",
        fake_scannable_pairs,
    )
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


def test_scan_all_skips_pairs_unavailable_for_provider(monkeypatch, sample_ticker, sample_order_book, sample_klines):
    monkeypatch.setattr(Scanner, "_init_providers", lambda self: None)
    async def fake_scannable_pairs(self):
        return {Exchange.BINANCE: ["BTC_BRL"]}

    monkeypatch.setattr(
        Scanner,
        "_get_scannable_pairs_by_exchange",
        fake_scannable_pairs,
    )
    config = AppConfig(enabled_exchanges=[Exchange.BINANCE], enabled_pairs=["BTC_BRL", "DOGE_BRL"])
    scanner = Scanner(config)

    calls: list[str] = []

    class TrackingFakeProvider(FakeProvider):
        async def get_ticker(self, pair: str):
            calls.append(pair)
            return await super().get_ticker(pair)

    scanner._providers = {
        Exchange.BINANCE: TrackingFakeProvider(sample_ticker, sample_order_book, sample_klines)
    }

    import asyncio

    opportunities = asyncio.run(scanner.scan_all())

    assert len(opportunities) == 1
    assert calls == ["BTC_BRL"]


def test_scan_all_captures_lower_slippage_for_deeper_book(monkeypatch, sample_ticker, sample_klines):
    monkeypatch.setattr(Scanner, "_init_providers", lambda self: None)

    async def fake_scannable_pairs(self):
        return {
            Exchange.BINANCE: ["BTC_BRL"],
            Exchange.NOVADAX: ["BTC_BRL"],
        }

    monkeypatch.setattr(Scanner, "_get_scannable_pairs_by_exchange", fake_scannable_pairs)
    config = AppConfig(
        enabled_exchanges=[Exchange.BINANCE, Exchange.NOVADAX],
        enabled_pairs=["BTC_BRL"],
        thresholds={
            "min_volatility_pct": 2.0,
            "min_volume_brl": 10000.0,
            "min_volume_brl_small": 3000.0,
            "min_liquidity_units": 1.0,
            "max_spread_pct": 2.0,
        },
    )
    scanner = Scanner(config)

    deep_book = OrderBook(
        exchange=Exchange.BINANCE,
        pair="BTC_BRL",
        bids=[
            {"price": 119.95, "quantity": 100},
            {"price": 119.90, "quantity": 100},
        ],
        asks=[
            {"price": 120.00, "quantity": 100},
            {"price": 120.05, "quantity": 100},
        ],
    )
    shallow_book = OrderBook(
        exchange=Exchange.NOVADAX,
        pair="BTC_BRL",
        bids=[
            {"price": 119.50, "quantity": 2},
            {"price": 119.00, "quantity": 2},
        ],
        asks=[
            {"price": 120.00, "quantity": 2},
            {"price": 121.00, "quantity": 2},
        ],
    )

    class DeepProvider(FakeProvider):
        exchange = Exchange.BINANCE

    class ShallowProvider(FakeProvider):
        exchange = Exchange.NOVADAX

    scanner._providers = {
        Exchange.BINANCE: DeepProvider(sample_ticker, deep_book, sample_klines),
        Exchange.NOVADAX: ShallowProvider(
            Ticker(
                exchange=Exchange.NOVADAX,
                pair="BTC_BRL",
                last_price=sample_ticker.last_price,
                high_24h=sample_ticker.high_24h,
                low_24h=sample_ticker.low_24h,
                volume_24h=sample_ticker.volume_24h,
                quote_volume_24h=sample_ticker.quote_volume_24h,
                change_pct_24h=sample_ticker.change_pct_24h,
            ),
            shallow_book,
            sample_klines,
        ),
    }

    import asyncio

    opportunities = asyncio.run(scanner.scan_all())
    by_exchange = {opportunity.exchange: opportunity for opportunity in opportunities}

    assert by_exchange[Exchange.BINANCE].estimated_buy_slippage_bps is not None
    assert by_exchange[Exchange.NOVADAX].estimated_buy_slippage_bps is None
    assert by_exchange[Exchange.BINANCE].total_notional_top_n > by_exchange[Exchange.NOVADAX].total_notional_top_n
    assert by_exchange[Exchange.BINANCE].executability_score > by_exchange[Exchange.NOVADAX].executability_score
    assert by_exchange[Exchange.BINANCE].operable_signal is True
    assert by_exchange[Exchange.NOVADAX].operable_signal is False
