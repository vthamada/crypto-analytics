from __future__ import annotations

from datetime import datetime, timedelta, timezone

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

    async def get_light_ticker(self, pair: str):
        return await self.get_ticker(pair)

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
    assert opportunities[0].estimated_trade_margin_pct is not None
    assert opportunities[0].operational_friction_pct is not None
    assert opportunities[0].estimated_net_trade_edge_pct is not None
    assert opportunities[0].trade_margin_score is not None
    assert opportunities[0].opportunity_type in {"trade", "hold", "observe", "avoid"}
    assert opportunities[0].interesting_signal is True
    assert opportunities[0].operable_signal in {True, False}
    assert opportunities[0].movement_regime is not None
    assert opportunities[0].movement_phase is not None
    assert opportunities[0].alert_moment_type is not None
    assert opportunities[0].operational_range_quality is not None
    assert opportunities[0].operational_range_margin_pct is not None
    assert opportunities[0].capital_capacity_estimate_brl is not None
    assert opportunities[0].movement_persistence_score is not None
    assert opportunities[0].baseline_order_notional_brl is not None
    assert [item.notional_brl for item in opportunities[0].order_size_simulations] == [25.0, 300.0, 1000.0, 5000.0, 10000.0]
    assert opportunities[0].max_operable_order_notional_brl is not None
    assert opportunities[0].operability_size_label in {"not_operable", "small_test_only", "medium_operation", "large_operation"}
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


def test_scan_all_marks_extended_phase_as_late_entry(monkeypatch, sample_order_book):
    monkeypatch.setattr(Scanner, "_init_providers", lambda self: None)

    async def fake_scannable_pairs(self):
        return {Exchange.BINANCE: ["LAB_BRL"]}

    monkeypatch.setattr(Scanner, "_get_scannable_pairs_by_exchange", fake_scannable_pairs)

    from datetime import datetime, timedelta, timezone
    from app.models.schemas import Kline

    now = datetime.now(timezone.utc)
    extended_klines = [
        Kline(
            open_time=now + timedelta(minutes=index * 5),
            open=open_price,
            high=close_price * 1.01,
            low=open_price * 0.99,
            close=close_price,
            volume=2000 + index * 100,
        )
        for index, (open_price, close_price) in enumerate(
            [(10, 10.4), (10.4, 11.2), (11.2, 12.9), (12.9, 14.8), (14.8, 17.0)]
        )
    ]
    ticker = Ticker(
        exchange=Exchange.BINANCE,
        pair="LAB_BRL",
        last_price=17.0,
        high_24h=17.2,
        low_24h=9.8,
        volume_24h=30000,
        quote_volume_24h=500000,
        change_pct_24h=70.0,
    )
    scanner = Scanner(AppConfig(enabled_exchanges=[Exchange.BINANCE], enabled_pairs=["LAB_BRL"]))
    scanner._providers = {
        Exchange.BINANCE: FakeProvider(ticker, sample_order_book, extended_klines)
    }

    import asyncio

    opportunities = asyncio.run(scanner.scan_all())

    assert len(opportunities) == 1
    assert opportunities[0].movement_phase == "extended"
    assert opportunities[0].is_late_entry_risk is True
    assert opportunities[0].is_profit_zone_candidate is True


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


def test_scan_all_uses_light_triage_before_expensive_requests(monkeypatch, sample_order_book, sample_klines):
    monkeypatch.setattr(Scanner, "_init_providers", lambda self: None)

    async def fake_scannable_pairs(self):
        return {Exchange.BINANCE: ["BTC_BRL", "DEAD_BRL"]}

    monkeypatch.setattr(Scanner, "_get_scannable_pairs_by_exchange", fake_scannable_pairs)

    class TriageProvider:
        exchange = Exchange.BINANCE

        def __init__(self):
            self.deep_calls: list[str] = []

        async def get_light_ticker(self, pair: str):
            if pair == "DEAD_BRL":
                return Ticker(
                    exchange=Exchange.BINANCE,
                    pair=pair,
                    last_price=1.0,
                    high_24h=1.01,
                    low_24h=0.99,
                    volume_24h=10.0,
                    quote_volume_24h=20.0,
                    change_pct_24h=0.1,
                )
            return Ticker(
                exchange=Exchange.BINANCE,
                pair=pair,
                last_price=120.0,
                high_24h=125.0,
                low_24h=98.0,
                volume_24h=1500.0,
                quote_volume_24h=250000.0,
                change_pct_24h=4.2,
            )

        async def get_order_book(self, pair: str):
            self.deep_calls.append(pair)
            return sample_order_book

        async def get_klines(self, pair: str, interval: str = "5m", limit: int = 100):
            self.deep_calls.append(pair)
            return sample_klines

        async def close(self):
            return None

    provider = TriageProvider()
    scanner = Scanner(AppConfig(enabled_exchanges=[Exchange.BINANCE], enabled_pairs=["BTC_BRL", "DEAD_BRL"]))
    scanner._providers = {Exchange.BINANCE: provider}

    import asyncio

    opportunities = asyncio.run(scanner.scan_all())

    assert [opportunity.pair for opportunity in opportunities] == ["BTC_BRL"]
    assert provider.deep_calls == ["BTC_BRL", "BTC_BRL"]
    assert scanner.scan_diagnostics["total_pairs"] == 2
    assert scanner.scan_diagnostics["light_requests"] == 2
    assert scanner.scan_diagnostics["light_candidates"] == 1
    assert scanner.scan_diagnostics["light_discards"] == 1
    assert scanner.scan_diagnostics["light_discard_reasons"]["volume_below_minimum"] == 1
    assert scanner.scan_diagnostics["deep_candidates"] == 1
    assert scanner.scan_diagnostics["opportunities"] == 1
    assert any(
        event["pair"] == "DEAD_BRL"
        and event["stage"] == "light_scan"
        and event["status"] == "discarded"
        and event["reason"] == "volume_below_minimum"
        for event in scanner.pipeline_events
    )
    assert any(
        event["pair"] == "BTC_BRL"
        and event["stage"] == "ranking"
        and event["status"] == "ranked"
        for event in scanner.pipeline_events
    )


def test_scan_all_records_compact_near_miss_for_close_light_discard(monkeypatch, sample_order_book, sample_klines):
    monkeypatch.setattr(Scanner, "_init_providers", lambda self: None)

    async def fake_scannable_pairs(self):
        return {Exchange.BINANCE: ["DOGE_BRL"]}

    monkeypatch.setattr(Scanner, "_get_scannable_pairs_by_exchange", fake_scannable_pairs)

    ticker = Ticker(
        exchange=Exchange.BINANCE,
        pair="DOGE_BRL",
        last_price=1.0,
        high_24h=1.04,
        low_24h=0.96,
        volume_24h=2500.0,
        quote_volume_24h=2500.0,
        change_pct_24h=2.0,
    )
    scanner = Scanner(AppConfig(enabled_exchanges=[Exchange.BINANCE], enabled_pairs=["DOGE_BRL"]))
    scanner._providers = {Exchange.BINANCE: FakeProvider(ticker, sample_order_book, sample_klines)}

    import asyncio

    opportunities = asyncio.run(scanner.scan_all())

    near_miss_events = [event for event in scanner.pipeline_events if event["event_type"] == "near_miss"]
    assert opportunities == []
    assert scanner.scan_diagnostics["near_misses"] == 1
    assert scanner.scan_diagnostics["near_miss_reasons"]["volume_below_minimum"] == 1
    assert len(near_miss_events) == 1
    assert near_miss_events[0]["stage"] == "light_scan"
    assert near_miss_events[0]["reason"] == "volume_below_minimum"
    assert near_miss_events[0]["details"]["failed_metric"] == "quote_volume_24h"
    assert near_miss_events[0]["details"]["threshold"] == 3000.0


def test_scan_all_skips_cold_pair_until_temperature_interval(monkeypatch, sample_order_book, sample_klines):
    monkeypatch.setattr(Scanner, "_init_providers", lambda self: None)

    async def fake_scannable_pairs(self):
        return {Exchange.BINANCE: ["DEAD_BRL"]}

    monkeypatch.setattr(Scanner, "_get_scannable_pairs_by_exchange", fake_scannable_pairs)

    class ColdProvider:
        exchange = Exchange.BINANCE

        def __init__(self):
            self.light_calls = 0

        async def get_light_ticker(self, pair: str):
            self.light_calls += 1
            return Ticker(
                exchange=Exchange.BINANCE,
                pair=pair,
                last_price=1.0,
                high_24h=1.01,
                low_24h=0.99,
                volume_24h=10.0,
                quote_volume_24h=20.0,
                change_pct_24h=0.1,
            )

        async def get_order_book(self, pair: str):
            return sample_order_book

        async def get_klines(self, pair: str, interval: str = "5m", limit: int = 100):
            return sample_klines

        async def close(self):
            return None

    provider = ColdProvider()
    scanner = Scanner(AppConfig(enabled_exchanges=[Exchange.BINANCE], enabled_pairs=["DEAD_BRL"]))
    scanner._providers = {Exchange.BINANCE: provider}

    import asyncio

    assert asyncio.run(scanner.scan_all()) == []
    assert asyncio.run(scanner.scan_all()) == []

    assert provider.light_calls == 1
    assert scanner.scan_diagnostics["skipped_pairs"] == 1
    assert scanner.scan_diagnostics["skip_reasons"]["temperature_cold"] == 1
    state = scanner._pair_scan_state["binance:DEAD_BRL"]
    assert state.temperature == "cold"
    assert state.last_discard_reason == "volume_below_threshold"


def test_scan_all_applies_cooldown_after_ticker_failure(monkeypatch):
    monkeypatch.setattr(Scanner, "_init_providers", lambda self: None)

    async def fake_scannable_pairs(self):
        return {Exchange.BINANCE: ["FAIL_BRL"]}

    monkeypatch.setattr(Scanner, "_get_scannable_pairs_by_exchange", fake_scannable_pairs)

    class FailingProvider:
        exchange = Exchange.BINANCE

        def __init__(self):
            self.light_calls = 0

        async def get_light_ticker(self, pair: str):
            self.light_calls += 1
            raise RuntimeError("provider unavailable")

        async def get_order_book(self, pair: str):
            raise AssertionError("deep scan should not run")

        async def get_klines(self, pair: str, interval: str = "5m", limit: int = 100):
            raise AssertionError("deep scan should not run")

        async def close(self):
            return None

    provider = FailingProvider()
    scanner = Scanner(AppConfig(enabled_exchanges=[Exchange.BINANCE], enabled_pairs=["FAIL_BRL"]))
    scanner._providers = {Exchange.BINANCE: provider}

    import asyncio

    assert asyncio.run(scanner.scan_all()) == []
    assert asyncio.run(scanner.scan_all()) == []

    assert provider.light_calls == 1
    assert scanner.scan_diagnostics["skipped_pairs"] == 1
    assert scanner.scan_diagnostics["skip_reasons"]["cooldown_active"] == 1
    state = scanner._pair_scan_state["binance:FAIL_BRL"]
    assert state.failure_count == 1
    assert state.cooldown_until is not None
    assert state.last_discard_reason == "ticker_failed"


def test_pair_scan_state_round_trip_preserves_cooldown(monkeypatch):
    monkeypatch.setattr(Scanner, "_init_providers", lambda self: None)

    scanner = Scanner(AppConfig(enabled_exchanges=[Exchange.BINANCE], enabled_pairs=["FAIL_BRL"]))
    now = datetime.now(timezone.utc)
    scanner._record_provider_pair_failure(Exchange.BINANCE, "FAIL_BRL", "ticker_failed", now)

    exported = scanner.export_pair_scan_states()
    restored = Scanner(AppConfig(enabled_exchanges=[Exchange.BINANCE], enabled_pairs=["FAIL_BRL"]))
    restored.load_pair_scan_states(exported)

    state = restored._pair_scan_state["binance:FAIL_BRL"]
    assert state.temperature == "cold"
    assert state.failure_count == 1
    assert state.cooldown_until is not None
    assert state.cooldown_until > now
    assert state.last_discard_reason == "ticker_failed"

    db_like_payload = dict(exported)
    db_like_payload["binance:FAIL_BRL"] = {
        **db_like_payload["binance:FAIL_BRL"],
        "cooldown_until": (now + timedelta(minutes=5)).replace(tzinfo=None),
    }
    restored.load_pair_scan_states(db_like_payload)
    assert restored._pair_scan_state["binance:FAIL_BRL"].cooldown_until.tzinfo is not None


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
