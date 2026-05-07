from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.filters.operational_range import calculate_operational_range_metrics
from app.models.schemas import Kline, MovementPhase, OrderBook, OrderBookEntry


def make_kline(index: int, open_price: float, close_price: float) -> Kline:
    now = datetime.now(timezone.utc)
    return Kline(
        open_time=now + timedelta(minutes=index * 5),
        open=open_price,
        high=max(open_price, close_price) * 1.02,
        low=min(open_price, close_price) * 0.98,
        close=close_price,
        volume=1000 + index * 100,
    )


def test_operational_range_identifies_reusable_large_trade_range():
    klines = [
        make_kline(0, 6.0, 6.5),
        make_kline(1, 6.4, 7.2),
        make_kline(2, 7.0, 7.8),
        make_kline(3, 7.5, 8.0),
        make_kline(4, 8.1, 11.8),
    ]
    book = OrderBook(
        exchange="novadax",
        pair="LAB_BRL",
        bids=[OrderBookEntry(price=11.6, quantity=900), OrderBookEntry(price=11.4, quantity=700)],
        asks=[OrderBookEntry(price=11.8, quantity=900), OrderBookEntry(price=12.0, quantity=700)],
    )

    metrics = calculate_operational_range_metrics(
        klines,
        order_book=book,
        movement_phase=MovementPhase.EARLY_BREAKOUT,
        fillable_notional_within_slippage_cap=12_000,
    )

    assert metrics["operational_buy_zone_low"] < metrics["operational_buy_zone_high"]
    assert metrics["operational_sell_zone_high"] > metrics["operational_buy_zone_high"]
    assert metrics["operational_range_margin_pct"] > 20
    assert metrics["capital_capacity_estimate_brl"] >= 10_000
    assert metrics["operational_range_quality"] in {"valid_large_trade", "high_quality_reusable_range"}


def test_operational_range_returns_none_for_flat_low_margin_range():
    klines = [
        make_kline(0, 10.0, 10.1),
        make_kline(1, 10.1, 10.0),
        make_kline(2, 10.0, 10.15),
        make_kline(3, 10.1, 10.05),
    ]
    book = OrderBook(
        exchange="novadax",
        pair="BTC_BRL",
        bids=[OrderBookEntry(price=10.0, quantity=10)],
        asks=[OrderBookEntry(price=10.2, quantity=10)],
    )

    metrics = calculate_operational_range_metrics(
        klines,
        order_book=book,
        movement_phase=MovementPhase.NEUTRAL,
        fillable_notional_within_slippage_cap=100,
    )

    assert metrics["operational_range_quality"] == "none"
    assert metrics["operational_range_margin_pct"] < 5
